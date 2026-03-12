import pytest
from PySide6.QtWidgets import QApplication

def test_app_imports_and_startup(qtbot):
    """
    E2E test to ensure that the core application modules and MainWindow
    can be imported and instantiated without throwing ModuleNotFoundError
    or other fatal startup exceptions.
    """
    from src.app import main
    from src.ui.main_window import MainWindow
    
    app = QApplication.instance() or QApplication([])
    
    try:
        window = MainWindow()
        qtbot.addWidget(window)
        assert window is not None
        assert window.windowTitle() == "Jehu Reader"
    except ModuleNotFoundError as e:
        pytest.fail(f"Startup completely failed due to missing module: {e}. Check requirements.txt or pyproject.toml.")
    except Exception as e:
        pytest.fail(f"MainWindow initialization threw an unexpected error: {e}")
