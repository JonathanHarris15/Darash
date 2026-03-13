import sys
import os

# Add src to path
sys.path.append(os.getcwd())

try:
    print("Testing SpellcheckManager initialization...")
    from src.managers.spellcheck_manager import SpellcheckManager
    sm = SpellcheckManager.get_instance()
    print("SpellcheckManager initialized successfully.")
    print(f"Is 'beginning' misspelled? {sm.is_misspelled('beginning')}")
    print(f"Is 'beggining' misspelled? {sm.is_misspelled('beggining')}")
except Exception as e:
    print(f"Error during SpellcheckManager test: {e}")
    import traceback
    traceback.print_exc()
