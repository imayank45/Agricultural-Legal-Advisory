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

# Initialize summarization pipeline
summarizer = pipeline("summarization", model=base_model, tokenizer=tokenizer, max_length=512)

# Function to clean text
def clean_text(text):
    text = re.sub(r'(?i)(witness|signature|signed|20th century).*?(?=\n|$)', '', text, flags=re.DOTALL)
    text = re.sub(r'customizeThis', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Function to extract risk-related clauses
def extract_risk_clauses(text):
    risk_clauses = re.findall(r'(Clause \d+:.*?)Risk:\s*(\w+)\s*\(Score:\s*([0-9\.]+)\)', text, re.DOTALL)
    return [(clause.strip(), risk, float(score)) for clause, risk, score in risk_clauses]

# Function to split text into chunks
def chunk_text(text, max_tokens=512, overlap=50):
    tokens = tokenizer.tokenize(text)
    chunks = []
    for i in range(0, len(tokens), max_tokens - overlap):
        chunk_tokens = tokens[i:i + max_tokens]
        chunk = tokenizer.convert_tokens_to_string(chunk_tokens)
        chunks.append(chunk)
    return chunks

# Function to summarize text
def summarize_contract(text):
    if not text or len(text.strip()) < 10:
        return "Text is too short or empty to summarize."
    
    try:
        text = clean_text(text)
        risk_clauses = extract_risk_clauses(text)
        chunks = chunk_text(text)
        summaries = []
        
        for chunk in chunks:
            input_length = len(chunk.split())
            min_length = min(50, max(10, input_length // 2))
            max_length = max(min_length + 10, min(150, input_length * 2))
            summary = summarizer(chunk, max_length=max_length, min_length=min_length, do_sample=False)
            summaries.append(summary[0]["summary_text"])
        
        combined_summary = " ".join(summaries)
        
        if len(combined_summary.split()) > 500:
            combined_summary = summarizer(combined_summary, max_length=150, min_length=50, do_sample=False)[0]["summary_text"]
        
        structured_summary = "Summary: This agricultural land lease agreement involves the following key points -\n"
        structured_summary += f"{combined_summary}\n"
        if risk_clauses:
            structured_summary += "- Clauses with Risk:\n"
            for clause, risk, score in risk_clauses:
                structured_summary += f"  - {clause} (Risk: {risk}, Score: {score})\n"
        
        return structured_summary
    except Exception as e:
        return f"Error during summarization: {str(e)}"