import sys
import os
import importlib
import threading
import code
import time
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication
from PySide6.QtCore import QFileSystemWatcher, Qt, QTimer
from PySide6.QtGui import QScreen

from src.core.theme import Theme

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
        
        # Apply the project's global theme for high-fidelity debugging
        self.setStyleSheet(Theme.get_global_stylesheet())

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

        # Handle Snapshot Mode
        if "--snapshot" in sys.argv:
            QTimer.singleShot(1000, self._capture_snapshot_and_exit)
        else:
            # Start REPL in a background thread
            self._start_repl()

    def _capture_snapshot_and_exit(self):
        """Captures a screenshot of the component and exits."""
        os.makedirs("docs/snapshots", exist_ok=True)
        filename = f"docs/snapshots/{self.class_name.lower()}.png"
        
        # Grab the window content
        screen = QApplication.primaryScreen()
        screenshot = screen.grabWindow(self.winId())
        screenshot.save(filename, "png")
        
        print(f"Snapshot saved to {filename}")
        QApplication.quit()

    def _start_repl(self):
        """Starts an interactive Python console in a background thread."""
        def run_console():
            local_vars = {
                'harness': self,
                'component': self.component,
                'app': QApplication.instance(),
                'inspect': self.inspect,
                'reload': self.reload_component
            }
            
            banner = (
                f"\n--- Jehu-Reader UI REPL ---\n"
                f"Available globals: harness, component, app, inspect, reload\n"
                f"Target: {self.module_name}.{self.class_name}\n"
            )
            
            console = code.InteractiveConsole(local_vars)
            console.interact(banner=banner)

        # We don't join the thread because we want it to exit with the app
        thread = threading.Thread(target=run_console, daemon=True)
        thread.start()

    def inspect(self, obj=None):
        """Prints public methods and properties of an object."""
        target = obj or self.component
        print(f"\n--- Inspecting: {target} ---")
        for attr in sorted(dir(target)):
            if attr.startswith('_'):
                continue
            try:
                val = getattr(target, attr)
                if callable(val):
                    print(f" [M] {attr}()")
                else:
                    print(f" [P] {attr} = {val}")
            except Exception:
                pass

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
