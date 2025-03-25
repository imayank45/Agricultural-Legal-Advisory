from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline
from peft import PeftModel
import re

# Define base model
base_model_name = "facebook/bart-large-cnn"

# Load base model
model = AutoModelForSeq2SeqLM.from_pretrained(base_model_name)

# Load LoRA adapter
adapter_path = "models/fine_tuned_bart_lora/checkpoint-675"
peft_model = PeftModel.from_pretrained(model, adapter_path)

# Extract the base model for pipeline compatibility
base_model = peft_model.get_base_model()

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(base_model_name)

# Initialize summarization pipeline with the base model
summarizer = pipeline("summarization", model=base_model, tokenizer=tokenizer, max_length=512)

# Function to clean the text by removing irrelevant parts
def clean_text(text):
    # Remove signatures and witness statements
    text = re.sub(r'(?i)(witness|signature|signed|20th century).*?(?=\n|$)', '', text, flags=re.DOTALL)
    # Remove "customizeThis" or similar artifacts
    text = re.sub(r'customizeThis', '', text, flags=re.IGNORECASE)
    # Remove extra spaces and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Function to split long text into chunks
def chunk_text(text, max_tokens=512, overlap=50):
    tokens = tokenizer.tokenize(text)
    chunks = []
    for i in range(0, len(tokens), max_tokens - overlap):
        chunk_tokens = tokens[i:i + max_tokens]
        chunk = tokenizer.convert_tokens_to_string(chunk_tokens)
        chunks.append(chunk)
    return chunks

# Function to extract key information for structured summary
def extract_key_info(text):
    info = {
        "parties": "",
        "land_details": "",
        "lease_term": "",
        "rent": "",
        "purpose": ""
    }
    
    # Extract parties
    parties_match = re.search(r'between\s*:\s*(.+?)(?=\s*whereas|\s*now,|\s*\d+\.)', text, re.IGNORECASE)
    if parties_match:
        info["parties"] = parties_match.group(1).strip()
    
    # Extract land details
    land_match = re.search(r'land bearing survey no\.?\s*(\d+),\s*measuring\s*([\d\s\w]+),\s*situated at\s*([^.]+)', text, re.IGNORECASE)
    if land_match:
        info["land_details"] = f"Survey No. {land_match.group(1)}, measuring {land_match.group(2)}, situated at {land_match.group(3)}"
    
    # Extract lease term
    lease_term_match = re.search(r'lease term shall be\s*(\d+\s*years),\s*commencing from\s*([^,]+),\s*and ending on\s*([^.]+)', text, re.IGNORECASE)
    if lease_term_match:
        info["lease_term"] = f"{lease_term_match.group(1)}, starting from {lease_term_match.group(2)} and ending on {lease_term_match.group(3)}"
    
    # Extract rent
    rent_match = re.search(r'annual lease rent of\s*inr\s*([\d,]+)\s*\(([^)]+)\)', text, re.IGNORECASE)
    if rent_match:
        info["rent"] = f"INR {rent_match.group(1)} ({rent_match.group(2)})"
    
    # Extract purpose
    purpose_match = re.search(r'for\s*agricultural\s*purposes', text, re.IGNORECASE)
    if purpose_match:
        info["purpose"] = "agricultural purposes"
    
    return info

# Function to summarize long text by processing in chunks and structuring the output
def summarize_contract(text):
    if not text or len(text.strip()) < 10:
        return "Text is too short or empty to summarize."
    
    try:
        # Clean the text
        text = clean_text(text)
        
        # Extract key information
        key_info = extract_key_info(text)
        
        # Split the text into chunks
        chunks = chunk_text(text)
        summaries = []
        for chunk in chunks:
            input_length = len(chunk.split())
            min_length = min(50, max(10, input_length // 2))
            max_length = max(min_length + 10, min(150, input_length * 2))
            summary = summarizer(chunk, max_length=max_length, min_length=min_length, do_sample=False)
            summaries.append(summary[0]["summary_text"])
        
        # Combine all summarized chunks
        combined_summary = " ".join(summaries)
        
        # If the summary is too long, summarize it further
        if len(combined_summary.split()) > 500:
            combined_summary = summarizer(combined_summary, max_length=150, min_length=50, do_sample=False)[0]["summary_text"]
        
        # Structure the summary using key information
        structured_summary = "This agricultural land lease agreement involves the following key points:\n"
        if key_info["parties"]:
            structured_summary += f"- Parties Involved: {key_info['parties']}\n"
        if key_info["land_details"]:
            structured_summary += f"- Land Details: {key_info['land_details']}\n"
        if key_info["lease_term"]:
            structured_summary += f"- Lease Term: {key_info['lease_term']}\n"
        if key_info["rent"]:
            structured_summary += f"- Annual Rent: {key_info['rent']}\n"
        if key_info["purpose"]:
            structured_summary += f"- Purpose: The land is leased for {key_info['purpose']}.\n"
        
        # If no key information is extracted, fall back to the combined summary
        if structured_summary == "This agricultural land lease agreement involves the following key points:\n":
            structured_summary += f"- Details: {combined_summary}"
        
        return structured_summary
    except Exception as e:
        return f"Error during summarization: {str(e)}"