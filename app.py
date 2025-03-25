from flask import Flask, request, jsonify, render_template
import os
from summarization import summarize_contract
from risk_analysis import classify_risk
from translation import translate_text, get_supported_languages
from tts import text_to_speech

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
        # Extract text
        import fitz
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        
        if not text.strip():
            return jsonify({"error": "Failed to extract text from the file"}), 400

        # Summarize
        summary = summarize_contract(text)
        # Identify risks
        risks = classify_risk(text)
        return jsonify({
            "summary": summary,
            "risks": risks
        })
    except Exception as e:
        return jsonify({"error": f"Error during analysis: {str(e)}"}), 500
    finally:
        # Ensure the document is closed before deleting the file
        if doc is not None:
            doc.close()
        if os.path.exists(file_path):
            os.remove(file_path)

@app.route("/translate_and_speak", methods=["POST"])
def translate_and_speak():
    data = request.get_json()
    summary = data.get("summary", "")
    lang = data.get("lang", "hi")  # Default to Hindi

    # Translate
    translated_summary = translate_text(summary, target_lang=lang)
    # Generate speech
    audio_file = text_to_speech(translated_summary, lang=lang)
    if "Error" in audio_file:
        return jsonify({"error": audio_file}), 500
    return jsonify({"translated_summary": translated_summary, "audio_file": audio_file})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)