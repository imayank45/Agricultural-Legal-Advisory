from gtts import gTTS
import os

def text_to_speech(text, lang="hi", output_file="static/audio/summary.mp3"):
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        tts.save(output_file)
        return output_file
    except Exception as e:
        return f"Error during TTS: {str(e)}"