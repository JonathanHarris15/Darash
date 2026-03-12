from src.managers.spellcheck_manager import SpellcheckManager
try:
    sm = SpellcheckManager.get_instance()
    print(f"SpellcheckManager initialized: {sm}")
    print(f"Is 'hello' misspelled? {sm.is_misspelled('hello')}")
    print(f"Is 'hlello' misspelled? {sm.is_misspelled('hlello')}")
except Exception as e:
    print(f"Error: {e}")
