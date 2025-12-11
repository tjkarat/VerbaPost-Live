import ui_main
import ai_engine
import letter_format
import inspect

def test_critical_functions():
    print("🔍 Starting System Integrity Check...")

    # 1. Check PDF Logic
    if "is_standard" not in letter_format.create_pdf.__code__.co_varnames:
        raise AssertionError("❌ PDF Logic Regression: Standard tier address logic missing!")
    
    # 2. Check AI Engine (Robust to spacing)
    src = inspect.getsource(ai_engine.load_whisper_model_cached)
    # Remove all spaces to match 'device="cpu"' regardless of formatting
    clean_src = src.replace(" ", "")
    
    if 'device="cpu"' not in clean_src:
        raise AssertionError("❌ AI Engine Regression: CPU force missing! (Check ai_engine.py)")
    
    # 3. Check UI Reset Logic
    if not hasattr(ui_main, "reset_app"):
        raise AssertionError("❌ UI Regression: reset_app function missing!")
    
    print("✅ System Integrity Verified: Core logic is intact.")

if __name__ == "__main__":
    try:
        test_critical_functions()
    except AssertionError as e:
        print(e)
        exit(1)
