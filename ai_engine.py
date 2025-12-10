import streamlit as st
import logging
import os
import tempfile
import secrets_manager
import subprocess
import gc
import traceback
import sys

# Configure Logging - CRITICAL: Use stdout for Streamlit visibility
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- 1. ROBUST TRANSCRIPTION ENGINE ---
def load_and_transcribe(audio_path_or_file):
    """
    Self-contained transcription function.
    Loads Whisper, processes audio, and dumps memory immediately.
    
    Returns: tuple (success: bool, result: str)
    """
    model = None
    whisper = None
    
    try:
        logger.info("[TRANSCRIBE] Step 1: Starting garbage collection")
        gc.collect()
        
        logger.info("[TRANSCRIBE] Step 2: Lazy-importing Whisper module")
        try:
            import whisper as whisper_module
            whisper = whisper_module
            logger.info("[TRANSCRIBE] Whisper imported successfully")
        except ImportError as ie:
            logger.error(f"[TRANSCRIBE] FAILED to import Whisper: {ie}")
            return False, "Error: openai-whisper not installed. Run: pip install openai-whisper"
        
        # Validate file exists
        if isinstance(audio_path_or_file, str):
            if not os.path.exists(audio_path_or_file):
                logger.error(f"[TRANSCRIBE] File not found: {audio_path_or_file}")
                return False, f"Error: Audio file not found at {audio_path_or_file}"
            
            file_size = os.path.getsize(audio_path_or_file)
            logger.info(f"[TRANSCRIBE] File size: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
            
            if file_size == 0:
                logger.error("[TRANSCRIBE] File is empty (0 bytes)")
                return False, "Error: Audio file is empty"
            
            if file_size > 25 * 1024 * 1024:  # 25MB limit
                logger.error(f"[TRANSCRIBE] File too large: {file_size / 1024 / 1024:.2f} MB")
                return False, "Error: Audio file too large (max 25MB)"
        
        # Load TINY model (Safe for Cloud)
        logger.info("[TRANSCRIBE] Step 3: Loading Whisper 'tiny' model")
        try:
            model = whisper.load_model("tiny")
            logger.info("[TRANSCRIBE] Model loaded successfully")
        except Exception as model_err:
            logger.error(f"[TRANSCRIBE] Model load FAILED: {model_err}")
            logger.error(traceback.format_exc())
            return False, f"Error: Failed to load Whisper model - {str(model_err)}"
        
        # Transcribe
        logger.info(f"[TRANSCRIBE] Step 4: Transcribing audio file: {audio_path_or_file}")
        try:
            result = model.transcribe(
                audio_path_or_file,
                fp16=False,  # CPU-safe mode
                language=None,  # Auto-detect
                task='transcribe'
            )
            logger.info("[TRANSCRIBE] Transcription completed")
        except Exception as trans_err:
            logger.error(f"[TRANSCRIBE] Transcription FAILED: {trans_err}")
            logger.error(traceback.format_exc())
            
            # Specific error handling
            error_str = str(trans_err).lower()
            if "ffmpeg" in error_str:
                return False, "Error: FFmpeg error - audio format may be unsupported"
            elif "cuda" in error_str or "gpu" in error_str:
                return False, "Error: GPU error (should not happen with fp16=False)"
            elif "memory" in error_str or "oom" in error_str:
                return False, "Error: Out of memory - try a shorter audio file"
            else:
                return False, f"Error: Transcription failed - {str(trans_err)}"
        
        # Extract and validate text
        text = result.get("text", "").strip()
        
        if not text:
            logger.warning("[TRANSCRIBE] WARNING: Transcription returned EMPTY text")
            logger.warning(f"[TRANSCRIBE] Full result object: {result}")
            return False, "Error: No speech detected in audio (empty transcription)"
        
        logger.info(f"[TRANSCRIBE] SUCCESS! Transcribed {len(text)} characters")
        logger.info(f"[TRANSCRIBE] Preview: '{text[:100]}{'...' if len(text) > 100 else ''}'")
        
        return True, text

    except Exception as e:
        logger.error(f"[TRANSCRIBE] UNEXPECTED ERROR: {str(e)}")
        logger.error(traceback.format_exc())
        return False, f"Error: Unexpected transcription failure - {str(e)}"
        
    finally:
        # AGGRESSIVE CLEANUP
        logger.info("[TRANSCRIBE] Step 5: Cleaning up memory")
        if model is not None:
            try:
                del model
                logger.debug("[TRANSCRIBE] Model deleted")
            except:
                pass
        
        if whisper is not None:
            try:
                # Clear Whisper's model cache
                if hasattr(whisper, '_MODELS'):
                    whisper._MODELS.clear()
                    logger.debug("[TRANSCRIBE] Whisper cache cleared")
            except:
                pass
        
        gc.collect()
        logger.info("[TRANSCRIBE] Memory cleanup complete")


def transcribe_audio(audio_input):
    """
    Main entry point called by UI. Handles file management.
    
    Returns: Transcribed text (str) or error message starting with "Error:"
    """
    logger.info("="*60)
    logger.info("[TRANSCRIBE AUDIO] NEW TRANSCRIPTION REQUEST")
    logger.info("="*60)
    
    # 1. FFmpeg Check
    logger.info("[TRANSCRIBE AUDIO] Checking FFmpeg availability")
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL, 
            check=True,
            timeout=5
        )
        logger.info("[TRANSCRIBE AUDIO] FFmpeg check PASSED")
    except subprocess.TimeoutExpired:
        logger.error("[TRANSCRIBE AUDIO] FFmpeg check TIMEOUT")
        return "Error: FFmpeg not responding (timeout)"
    except FileNotFoundError:
        logger.error("[TRANSCRIBE AUDIO] FFmpeg NOT FOUND")
        return "Error: FFmpeg not installed. Add 'ffmpeg' to packages.txt and redeploy"
    except Exception as ffmpeg_err:
        logger.error(f"[TRANSCRIBE AUDIO] FFmpeg check FAILED: {ffmpeg_err}")
        return f"Error: FFmpeg check failed - {str(ffmpeg_err)}"

    tmp_path = None
    try:
        # Handle file upload vs filepath
        if isinstance(audio_input, str):
            logger.info(f"[TRANSCRIBE AUDIO] Input type: File path string")
            logger.info(f"[TRANSCRIBE AUDIO] Path: {audio_input}")
            success, result = load_and_transcribe(audio_input)
            
            if success:
                logger.info("[TRANSCRIBE AUDIO] Transcription SUCCESS")
                return result
            else:
                logger.error(f"[TRANSCRIBE AUDIO] Transcription FAILED: {result}")
                return result
        
        else:
            # Streamlit UploadedFile object
            logger.info("[TRANSCRIBE AUDIO] Input type: Uploaded file object")
            
            # Determine file extension
            suffix = ".wav"
            if hasattr(audio_input, "name") and audio_input.name:
                file_ext = audio_input.name.split('.')[-1].lower()
                suffix = f".{file_ext}"
                logger.info(f"[TRANSCRIBE AUDIO] Detected file extension: {suffix}")
            
            # Get file size
            if hasattr(audio_input, 'size'):
                size_mb = audio_input.size / (1024 * 1024)
                logger.info(f"[TRANSCRIBE AUDIO] Upload size: {size_mb:.2f} MB")
                
                if size_mb > 25:
                    logger.error(f"[TRANSCRIBE AUDIO] File TOO LARGE: {size_mb:.2f} MB")
                    return "Error: File too large (max 25MB). Please use a shorter recording."
            
            # Create temp file
            logger.info("[TRANSCRIBE AUDIO] Creating temporary file")
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode='wb') as tmp:
                    file_bytes = audio_input.getvalue()
                    
                    if len(file_bytes) == 0:
                        logger.error("[TRANSCRIBE AUDIO] Uploaded file is EMPTY")
                        return "Error: Uploaded file is empty (0 bytes)"
                    
                    tmp.write(file_bytes)
                    tmp_path = tmp.name
                    logger.info(f"[TRANSCRIBE AUDIO] Temp file created: {tmp_path}")
                    logger.info(f"[TRANSCRIBE AUDIO] Wrote {len(file_bytes)} bytes")
            except Exception as tmp_err:
                logger.error(f"[TRANSCRIBE AUDIO] Failed to create temp file: {tmp_err}")
                return f"Error: Failed to save uploaded file - {str(tmp_err)}"
            
            # Verify temp file exists
            if not os.path.exists(tmp_path):
                logger.error(f"[TRANSCRIBE AUDIO] Temp file does NOT exist: {tmp_path}")
                return "Error: Failed to create temporary file (filesystem issue)"
            
            # Transcribe
            success, result = load_and_transcribe(tmp_path)
            
            if success:
                logger.info("[TRANSCRIBE AUDIO] Transcription SUCCESS")
                return result
            else:
                logger.error(f"[TRANSCRIBE AUDIO] Transcription FAILED: {result}")
                return result

    except Exception as e:
        logger.error(f"[TRANSCRIBE AUDIO] UNEXPECTED ERROR in file handling: {e}")
        logger.error(traceback.format_exc())
        return f"Error: File processing failed - {str(e)}"
    
    finally:
        # Clean up the temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                logger.info(f"[TRANSCRIBE AUDIO] Temp file deleted: {tmp_path}")
            except Exception as cleanup_err:
                logger.warning(f"[TRANSCRIBE AUDIO] Could not delete temp file: {cleanup_err}")


# --- 2. TEXT REFINEMENT (OPTIONAL) ---
def refine_text(text, style="Professional"):
    """
    Uses OpenAI GPT to refine transcribed text.
    This is separate from transcription and optional.
    """
    try:
        import openai
        
        api_key = secrets_manager.get_secret("openai.api_key") or secrets_manager.get_secret("OPENAI_API_KEY")
        
        if not api_key:
            try: 
                api_key = st.secrets["openai"]["api_key"]
            except: 
                pass
            
        if not api_key: 
            logger.warning("[REFINE] No OpenAI API key found. Skipping refinement.")
            return text 

        client = openai.OpenAI(api_key=api_key)
        
        logger.info(f"[REFINE] Refining text with style: {style}")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": f"Rewrite the following text to be {style}. Preserve meaning but improve clarity. No preamble."
                },
                {"role": "user", "content": text}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        refined = response.choices[0].message.content.strip()
        logger.info(f"[REFINE] Refinement complete: {len(refined)} characters")
        return refined
        
    except Exception as e:
        logger.error(f"[REFINE] Error: {e}")
        return text