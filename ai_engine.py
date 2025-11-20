import whisper
import sys
import re

# Load model once
model = whisper.load_model("base")

def transcribe_audio(filename):
    print(f"🎧 Transcribing {filename}...")
    result = model.transcribe(filename)
    return result["text"]

def polish_text(text):
    """
    Basic AI Cleanup: Removes filler words.
    """
    fillers = ["um", "uh", "ah", "like, you know", "you know"]
    polished = text
    for filler in fillers:
        pattern = re.compile(re.escape(filler), re.IGNORECASE)
        polished = pattern.sub("", polished)
    polished = " ".join(polished.split())
    return polished
