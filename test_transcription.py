#!/usr/bin/env python3
"""
Standalone test for Whisper transcription.
Run this OUTSIDE of Streamlit to verify Whisper works.

Usage:
    python test_transcription.py your_audio_file.wav
"""
import sys
import os
import subprocess
import gc
import logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_ffmpeg():
    """Test FFmpeg availability"""
    print("\n" + "="*60)
    print("TEST 1: FFmpeg Check")
    print("="*60)
    
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        print("✅ FFmpeg is installed")
        version_line = result.stdout.split('\n')[0]
        print(f"   {version_line}")
        return True
    except FileNotFoundError:
        print("❌ FFmpeg NOT found")
        print("   Install: apt-get install ffmpeg (Linux)")
        print("   Install: brew install ffmpeg (macOS)")
        return False
    except Exception as e:
        print(f"❌ FFmpeg check failed: {e}")
        return False


def test_whisper_import():
    """Test Whisper import"""
    print("\n" + "="*60)
    print("TEST 2: Whisper Import")
    print("="*60)
    
    try:
        import whisper
        print("✅ Whisper imported successfully")
        print(f"   Location: {whisper.__file__}")
        print(f"   Version: {whisper.__version__ if hasattr(whisper, '__version__') else 'Unknown'}")
        return whisper
    except ImportError as e:
        print(f"❌ Cannot import Whisper")
        print(f"   Error: {e}")
        print("   Install: pip install openai-whisper")
        return None


def test_model_load(whisper):
    """Test loading the tiny model"""
    print("\n" + "="*60)
    print("TEST 3: Model Loading")
    print("="*60)
    
    if not whisper:
        print("⏭️  Skipped (Whisper not available)")
        return None
    
    try:
        gc.collect()
        print("Loading 'tiny' model (first run downloads ~75MB)...")
        model = whisper.load_model("tiny")
        print("✅ Model loaded successfully")
        print(f"   Model type: {type(model).__name__}")
        return model
    except Exception as e:
        print(f"❌ Model load failed: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def test_transcription(model, audio_file):
    """Test actual transcription"""
    print("\n" + "="*60)
    print("TEST 4: Transcription")
    print("="*60)
    
    if not model:
        print("⏭️  Skipped (Model not loaded)")
        return False
    
    if not audio_file:
        print("⏭️  Skipped (No audio file provided)")
        print("   Usage: python test_transcription.py your_audio.wav")
        return False
    
    if not os.path.exists(audio_file):
        print(f"❌ File not found: {audio_file}")
        return False
    
    file_size = os.path.getsize(audio_file)
    print(f"File: {audio_file}")
    print(f"Size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
    
    if file_size == 0:
        print("❌ File is empty (0 bytes)")
        return False
    
    try:
        print("\nTranscribing (this may take 10-30 seconds)...")
        result = model.transcribe(audio_file, fp16=False)
        text = result.get("text", "").strip()
        
        if text:
            print("\n✅ Transcription SUCCESSFUL!")
            print(f"   Length: {len(text)} characters")
            print(f"   Language: {result.get('language', 'unknown')}")
            print("\n" + "-"*60)
            print("TRANSCRIBED TEXT:")
            print("-"*60)
            print(text)
            print("-"*60)
            return True
        else:
            print("⚠️  Transcription returned empty text")
            print("   Possible causes:")
            print("   - Audio file contains no speech")
            print("   - Audio quality too low")
            print("   - Unsupported audio format")
            return False
            
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def main():
    print("="*60)
    print("WHISPER TRANSCRIPTION TEST")
    print("="*60)
    
    # Get audio file from command line
    audio_file = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Run tests
    ffmpeg_ok = test_ffmpeg()
    whisper = test_whisper_import()
    model = test_model_load(whisper) if whisper else None
    transcription_ok = test_transcription(model, audio_file)
    
    # Cleanup
    if model:
        print("\nCleaning up...")
        del model
        gc.collect()
        print("✅ Cleanup complete")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"FFmpeg:        {'✅ PASS' if ffmpeg_ok else '❌ FAIL'}")
    print(f"Whisper:       {'✅ PASS' if whisper else '❌ FAIL'}")
    print(f"Model Load:    {'✅ PASS' if model else '❌ FAIL'}")
    print(f"Transcription: {'✅ PASS' if transcription_ok else '⏭️  SKIP' if not audio_file else '❌ FAIL'}")
    print("="*60)
    
    if all([ffmpeg_ok, whisper, model]):
        if transcription_ok:
            print("\n🎉 ALL TESTS PASSED! Transcription is working.")
            return 0
        elif not audio_file:
            print("\n⚠️  Core components OK. Provide audio file to test transcription:")
            print(f"   python {sys.argv[0]} test_audio.wav")
            return 0
        else:
            print("\n❌ Transcription test FAILED. Check logs above.")
            return 1
    else:
        print("\n❌ TESTS FAILED. Fix issues above before testing transcription.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
