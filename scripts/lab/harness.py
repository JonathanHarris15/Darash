import sys
import os
import importlib
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PySide6.QtCore import QFileSystemWatcher, Qt

class HotReloadHarness(QMainWindow):
    """
    A standalone window harness that watches a source file and reloads
    its component whenever the file is saved.
    """
    def __init__(self, module_name, class_name, factory_func, watch_paths=None):
        super().__init__()
        self.module_name = module_name
        self.class_name = class_name
        self.factory_func = factory_func
        self.component = None
        
        self.setWindowTitle(f"Lab: {class_name} (Hot Reload Active)")
        self.resize(400, 700)
        self.setStyleSheet("QMainWindow { background-color: #1a1a1a; }")

        # Container for the component
        self.central_container = QWidget()
        self.container_layout = QVBoxLayout(self.central_container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self.central_container)

        # File Watcher
        self.watcher = QFileSystemWatcher()
        if watch_paths:
            self.watcher.addPaths(watch_paths)
        
        # Determine the source file of the module to watch it too
        try:
            spec = importlib.util.find_spec(module_name)
            if spec and spec.origin:
                self.watcher.addPath(spec.origin)
                print(f"Watching: {spec.origin}")
        except Exception as e:
            print(f"Warning: Could not resolve source file for {module_name}: {e}")

        self.watcher.fileChanged.connect(self.reload_component)
        
        # Initial load
        self.reload_component()

    def reload_component(self):
        print(f"\n--- Reloading {self.class_name} ---")
        try:
            # 1. Force remove from sys.modules to ensure a fresh import
            for key in list(sys.modules.keys()):
                if key == self.module_name or key.startswith(f"{self.module_name}."):
                    del sys.modules[key]

            # 2. Re-import
            module = importlib.import_module(self.module_name)
            importlib.reload(module)
            
            # 3. Get the fresh class
            component_class = getattr(module, self.class_name)

            # 4. Clean up old component if it exists
            if self.component:
                self.container_layout.removeWidget(self.component)
                self.component.deleteLater()
                self.component = None

            # 5. Instantiate new component via factory
            self.component = self.factory_func(component_class)
            self.container_layout.addWidget(self.component)
            
            print("Reload successful.")
        except Exception as e:
            print(f"Reload failed: {e}")
            import traceback
            traceback.print_exc()
