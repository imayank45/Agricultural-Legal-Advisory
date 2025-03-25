from transformers import DistilBertTokenizer, DistilBertForSequenceClassification, pipeline
from peft import PeftModel
import re

# Define base model
base_model_name = "distilbert-base-uncased"

# Load base model
model = DistilBertForSequenceClassification.from_pretrained(base_model_name)

# Load LoRA adapter
adapter_path = "models/fine_tuned_distilbert_lora/checkpoint-675"
peft_model = PeftModel.from_pretrained(model, adapter_path)

# Extract the base model for pipeline compatibility
base_model = peft_model.get_base_model()

# Load tokenizer
tokenizer = DistilBertTokenizer.from_pretrained(base_model_name)

# Initialize classification pipeline with the base model
classifier = pipeline("text-classification", model=base_model, tokenizer=tokenizer, max_length=512)

# Function to extract all clauses based on document structure
def extract_clauses(text):
    # Replace newlines with spaces to handle multi-line sentences
    text = text.replace("\n", " ").strip()
    
    clauses = []
    
    # Step 1: Extract preamble clauses (e.g., "Whereas", "Now, therefore")
    # Find the start of numbered sections
    numbered_section_start = re.search(r'\d+\.\s+[A-Z]', text)
    if numbered_section_start:
        preamble = text[:numbered_section_start.start()].strip()
        # Split preamble into clauses based on sentence-ending punctuation followed by a capital letter
        preamble_clauses = re.split(r'(?<=\.)\s+(?=[A-Z][a-z]+,)', preamble)
        for clause in preamble_clauses:
            clause = clause.strip()
            if clause and (clause.lower().startswith("whereas") or clause.lower().startswith("now, therefore")):
                clauses.append(clause)
    
    # Step 2: Extract party definitions (e.g., "1. mr. vinay sharma", "2. mr. arvind mehta")
    party_pattern = r'(\d+\.\s+mr\.\s+[a-z\s]+,\s+son\s+of\s+mr\.\s+[a-z\s]+,\s+residing\s+at\s+[^,]+,\s+[^,]+,\s+india,\s+hereinafter\s+referred\s+to\s+as\s+[^)]+\))'
    parties = re.finditer(party_pattern, text, re.IGNORECASE)
    for party in parties:
        clause = party.group(1).strip()
        if clause:
            clauses.append(clause)
    
    # Step 3: Remove the party definitions from the text to avoid duplication
    remaining_text = re.sub(party_pattern, '', text, flags=re.IGNORECASE).strip()
    
    # Step 4: Extract numbered sections (e.g., "1. Lease Term and Rent", "2. Purpose of Lease")
    section_pattern = r'(\d+\.\s+[A-Z][A-Za-z\s&]+)(.*?)(?=\d+\.\s+[A-Z]|$)'
    sections = re.finditer(section_pattern, remaining_text)
    
    for section in sections:
        section_title = section.group(1).strip()  # e.g., "1. Lease Term and Rent"
        section_content = section.group(2).strip()  # Content under the section
        
        # Step 5: Extract sub-clauses within the section (e.g., "1.1", "1.2")
        sub_clause_pattern = r'(\d+\.\d+\s+.*?)(?=\d+\.\d+|\d+\.\s+[A-Z]|$)'
        sub_clauses = re.finditer(sub_clause_pattern, section_content)
        
        for sub_clause in sub_clauses:
            clause_text = sub_clause.group(1).strip()
            if clause_text:
                # Include the section title for context
                clauses.append(f"{section_title}: {clause_text}")
        
        # If no sub-clauses, add the section content as a single clause
        if not re.search(sub_clause_pattern, section_content) and section_content:
            clauses.append(f"{section_title}: {section_content}")
    
    return [clause for clause in clauses if clause]

# Function to split text into chunks
def chunk_text(text, max_tokens=512, overlap=50):
    tokens = tokenizer.tokenize(text)
    chunks = []
    for i in range(0, len(tokens), max_tokens - overlap):
        chunk_tokens = tokens[i:i + max_tokens]
        chunk = tokenizer.convert_tokens_to_string(chunk_tokens)
        chunks.append(chunk)
    return chunks

# Function to classify risk for each clause with a confidence threshold
def classify_risk(text):
    if not text or len(text.strip()) < 10:
        return "Text is too short or empty to classify."

    risks = []
    try:
        # Extract clauses
        clauses = extract_clauses(text)
        
        if not clauses:
            return [{"clause": "No clauses found in the document.", "risk": "UNKNOWN", "score": 0.0, "explanation": "No clauses detected."}]

        for clause in clauses:  # Process all clauses, not limited to 5
            chunks = chunk_text(clause)
            for chunk in chunks:
                # Get the model's prediction
                result = classifier(chunk)
                score = result[0]["score"]
                # Apply a confidence threshold: only mark as RISKY if score > 0.7
                label = "RISKY" if result[0]["label"] == "LABEL_1" and score > 0.7 else "SAFE"
                explanation = "Classified by the fine-tuned DistilBERT model."
                if label == "RISKY" and score <= 0.7:
                    explanation += " Overridden to SAFE due to low confidence score."
                risks.append({"clause": chunk, "risk": label, "score": score, "explanation": explanation})
        
        return risks
    except Exception as e:
        return f"Error during classification: {str(e)}"