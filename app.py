from flask import Flask, request, jsonify, render_template
import os
import re
import fitz  # PyMuPDF
from summarization import summarize_contract
from risk_analysis import classify_risk, extract_clauses
from translation import translate_text, get_supported_languages
from tts import text_to_speech

# Initialize Flask app
app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def clean_text(text):
    """Cleans extracted text by removing witness/signature sections, names, and unnecessary symbols."""
    exclusion_patterns = [
        r"witness(?:es)?:?\s*\n?.*",
        r"signature\s*\n?.*",
        r"lessor\s*:.*",
        r"lessee\s*:.*",
        r"date\s*:\s*\d{1,2}(st|nd|rd|th)?\s+[a-zA-Z]+\s+\d{4}",
        r"(shri|smt)\.\s*\w+\s+\w+",
        r"\b[A-Za-z]+\s*\(\s*_+\s*\)",
        r"\d+\.\s*\w+\s*:\s*,\s*\w+,\s*\w+",
        r"in the presence of the following.*"
    ]

    for pattern in exclusion_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n+', '\n', text).strip()
    return text

@app.route("/", methods=["GET"])
def index():
    languages = get_supported_languages()
    return render_template("index.html", languages=languages)

@app.route("/analyze", methods=["POST"])
def analyze_contract():
    if "contract" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["contract"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    doc = None
    try:
        doc = fitz.open(file_path)
        clauses_with_pages = []

        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            cleaned_text = clean_text(text)
            clauses = extract_clauses(cleaned_text, page_num)  # Pass page number

            clauses_with_pages.extend(clauses)  # Store clause with page number
        
        if not clauses_with_pages:
            return jsonify({"error": "Failed to extract text from the file"}), 400
        
        summary = summarize_contract("\n".join([c[0] for c in clauses_with_pages]))
        risks = classify_risk(clauses_with_pages)

        return jsonify({
            "summary": summary,
            "risks": risks
        })
    except Exception as e:
        return jsonify({"error": f"Error during analysis: {str(e)}"}), 500
    finally:
        if doc is not None:
            doc.close()
        if os.path.exists(file_path):
            os.remove(file_path)

@app.route("/translate_and_speak", methods=["POST"])
def translate_and_speak():
    data = request.get_json()
    summary = data.get("summary", "")
    lang = data.get("lang", "hi")  # Default to Hindi
    
    supported_languages = get_supported_languages()
    if lang not in supported_languages:
        return jsonify({"error": "Selected language is not supported."}), 400
    
    translated_summary = translate_text(summary, target_lang=lang)
    
    audio_file = text_to_speech(translated_summary, lang=lang)
    if "Error" in audio_file:
        return jsonify({"error": audio_file}), 500
    
    return jsonify({"translated_summary": translated_summary, "audio_file": audio_file})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
