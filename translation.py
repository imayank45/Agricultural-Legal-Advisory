from googletrans import Translator

# List of Indian languages supported by googletrans
INDIAN_LANGUAGES = {
    'as': 'Assamese',
    'bn': 'Bengali',
    'gu': 'Gujarati',
    'hi': 'Hindi',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'mr': 'Marathi',
    'ne': 'Nepali',  # Though Nepali is primarily spoken in Nepal, it's spoken in some Indian states
    'or': 'Odia',
    'pa': 'Punjabi',
    'sa': 'Sanskrit',
    'ta': 'Tamil',
    'te': 'Telugu',
    'ur': 'Urdu'
}

translator = Translator()

def translate_text(text, target_lang="hi"):  # Default to Hindi
    try:
        if target_lang not in INDIAN_LANGUAGES:
            return "Error: Target language not in supported Indian languages."
        translated = translator.translate(text, dest=target_lang)
        return translated.text
    except Exception as e:
        return f"Error during translation: {str(e)}"

def get_supported_languages():
    return INDIAN_LANGUAGES
