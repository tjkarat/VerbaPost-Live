import ui_main
import ai_engine
import letter_format

def test_critical_functions():
    # 1. Check if the PDF generator still has the address fix
    assert "is_standard" in letter_format.create_pdf.__code__.co_varnames, "❌ PDF Logic Regression: Standard tier address logic missing!"
    
    # 2. Check if AI engine is still forced to CPU
    import inspect
    src = inspect.getsource(ai_engine.load_whisper_model_cached)
    assert 'device="cpu"' in src, "❌ AI Engine Regression: CPU force missing!"
    
    # 3. Check if UI has the reset logic
    assert hasattr(ui_main, "reset_app"), "❌ UI Regression: reset_app function missing!"
    
    print("✅ System Integrity Verified: Core logic is intact.")

if __name__ == "__main__":
    test_critical_functions()
