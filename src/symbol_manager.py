import os
import json
import shutil
from typing import Dict, Optional

class SymbolManager:
    """
    Manages a library of symbols, their bindings to the number row (1-9),
    and global display settings like opacity.
    """
    def __init__(self, base_dir: str = "symbols_library"):
        self.base_dir = base_dir
        self.config_path = os.path.join(self.base_dir, "config.json")
        self.symbols_dir = os.path.join(self.base_dir, "images")
        
        if not os.path.exists(self.symbols_dir):
            os.makedirs(self.symbols_dir)
            
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {
                "bindings": {str(i): None for i in range(1, 10)},
                "opacity": 0.6
            }
            self.save_config()

    def save_config(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)

    def add_symbol_to_library(self, file_path: str) -> str:
        """Copies an image to the library and returns its name."""
        file_name = os.path.basename(file_path)
        dest_path = os.path.join(self.symbols_dir, file_name)
        shutil.copy2(file_path, dest_path)
        return file_name

    def remove_symbol_from_library(self, symbol_name: str):
        """Deletes image and clears bindings."""
        path = self.get_symbol_path(symbol_name)
        if os.path.exists(path):
            os.remove(path)
        
        # Clear bindings
        for num, bound_name in self.config["bindings"].items():
            if bound_name == symbol_name:
                self.config["bindings"][num] = None
        self.save_config()

    def get_symbol_path(self, symbol_name: str) -> str:
        return os.path.join(self.symbols_dir, symbol_name)

    def bind_symbol(self, number: str, symbol_name: Optional[str]):
        self.config["bindings"][number] = symbol_name
        self.save_config()

    def get_binding(self, number: str) -> Optional[str]:
        return self.config["bindings"].get(number)

    def set_opacity(self, opacity: float):
        self.config["opacity"] = opacity
        self.save_config()

    def get_opacity(self) -> float:
        return self.config.get("opacity", 0.6)

    def list_symbols(self):
        return os.listdir(self.symbols_dir)
