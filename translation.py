from googletrans import Translator, LANGUAGES

translator = Translator()

def translate_text(text, target_lang="hi"):  # Default to Hindi
    try:
        translated = translator.translate(text, dest=target_lang)
        return translated.text
    except Exception as e:
        return f"Error during translation: {str(e)}"

def get_supported_languages():
    return LANGUAGES