from gtts import gTTS
import os

# List of supported Indian languages in gTTS
INDIAN_LANGUAGES = {"hi", "bn", "ta", "te", "mr", "gu", "pa", "ur", "kn", "ml"}

def text_to_speech(text, lang="hi", output_file="static/audio/summary.mp3"):
    try:
        if lang not in INDIAN_LANGUAGES:
            return f"Error: Language '{lang}' is not supported for TTS."
        
        tts = gTTS(text=text, lang=lang, slow=False)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        tts.save(output_file)
        return output_file
    except Exception as e:
        return f"Error during TTS: {str(e)}"
