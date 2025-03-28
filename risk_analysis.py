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
def extract_clauses(text, page_num):
    text = text.replace("\n", " ").strip()
    
    clauses = []
    
    numbered_section_start = re.search(r'\d+\.\s+[A-Z]', text)
    if numbered_section_start:
        preamble = text[:numbered_section_start.start()].strip()
        preamble_clauses = re.split(r'(?<=\.)\s+(?=[A-Z][a-z]+,)', preamble)
        for clause in preamble_clauses:
            clause = clause.strip()
            if clause and (clause.lower().startswith("whereas") or clause.lower().startswith("now, therefore")):
                clauses.append((clause, page_num))
    
    party_pattern = r'(\d+\.\s+mr\.\s+[a-z\s]+,\s+son\s+of\s+mr\.\s+[a-z\s]+,\s+residing\s+at\s+[^,]+,\s+[^,]+,\s+india,\s+hereinafter\s+referred\s+to\s+as\s+[^)]+\))'
    parties = re.finditer(party_pattern, text, re.IGNORECASE)
    for party in parties:
        clause = party.group(1).strip()
        if clause:
            clauses.append((clause, page_num))
    
    remaining_text = re.sub(party_pattern, '', text, flags=re.IGNORECASE).strip()
    
    section_pattern = r'(\d+\.\s+[A-Z][A-Za-z\s&]+)(.*?)(?=\d+\.\s+[A-Z]|$)'
    sections = re.finditer(section_pattern, remaining_text)
    
    for section in sections:
        section_title = section.group(1).strip()
        section_content = section.group(2).strip()
        
        sub_clause_pattern = r'(\d+\.\d+\s+.*?)(?=\d+\.\d+|\d+\.\s+[A-Z]|$)'
        sub_clauses = re.finditer(sub_clause_pattern, section_content)
        
        for sub_clause in sub_clauses:
            clause_text = sub_clause.group(1).strip()
            if clause_text:
                clauses.append((f"{section_title}: {clause_text}", page_num))
        
        if not re.search(sub_clause_pattern, section_content) and section_content:
            clauses.append((f"{section_title}: {section_content}", page_num))
    
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

# Function to classify risk for each clause with page numbers
def classify_risk(clauses_with_pages):
    risks = []
    try:
        if not clauses_with_pages:
            return [{"clause": "No clauses found in the document.", "risk": "UNKNOWN", "score": 0.0, "page": None}]
        
        for clause, page_num in clauses_with_pages:
            chunks = chunk_text(clause)
            for chunk in chunks:
                result = classifier(chunk)
                score = result[0]["score"]
                label = "RISKY" if result[0]["label"] == "LABEL_1" and score > 0.7 else "SAFE"

                # ✅ Keep RISKY clauses regardless of score
                # ✅ Filter SAFE clauses only if score < 0.85
                if label == "RISKY" or (label == "SAFE" and score >= 0.85):
                    risks.append({"clause": chunk, "page": page_num, "risk": label, "score": score})

        return risks
    except Exception as e:
        return f"Error during classification: {str(e)}"
