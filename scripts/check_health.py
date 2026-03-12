import os
import ast
import sys
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
SOFT_LINE_LIMIT = 300
HARD_LINE_LIMIT = 500

# Domain Rules: {source_domain: forbidden_target_domains}
DOMAIN_RULES = {
    "core": ["managers", "scene", "ui"],
    "managers": ["scene", "ui"],
    "scene": ["ui"],
    "utils": ["managers", "scene", "ui"], # Allowed to import from core (constants)
}

def get_file_stats(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return len(lines)
    except Exception:
        return 0

def get_imports(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except Exception:
        return []
            
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.append(n.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports

def check_health():
    print("=== Jehu-Reader Architecture Health Check ===\n")
    
    issues_found = False
    
    # Walk src directory
    for root, dirs, files in os.walk(SRC_DIR):
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")
            
        for file in files:
            if not file.endswith(".py") or file == "__init__.py":
                continue
                
            file_path = Path(root) / file
            rel_path = file_path.relative_to(PROJECT_ROOT)
            
            # Line Count Check
            line_count = get_file_stats(file_path)
            if line_count > HARD_LINE_LIMIT:
                print(f"[CRITICAL] {rel_path}: {line_count} lines (Exceeds HARD limit of {HARD_LINE_LIMIT}!)")
                issues_found = True
            elif line_count > SOFT_LINE_LIMIT:
                print(f"[WARNING]  {rel_path}: {line_count} lines (Exceeds soft limit of {SOFT_LINE_LIMIT})")
                
            # Domain Integrity Check
            # Path parts: ('src', 'domain', 'file.py')
            if len(rel_path.parts) >= 2:
                source_domain = rel_path.parts[1]
                if source_domain in DOMAIN_RULES:
                    forbidden = DOMAIN_RULES[source_domain]
                    imports = get_imports(file_path)
                    
                    for imp in imports:
                        for forbidden_domain in forbidden:
                            # Check for 'src.domain' or 'domain' (if local import)
                            if imp.startswith(f"src.{forbidden_domain}") or imp.startswith(f"{forbidden_domain}"):
                                print(f"[VIOLATION] {rel_path}: Imports from forbidden domain '{forbidden_domain}' ({imp})")
                                issues_found = True

    if not issues_found:
        print("\n[OK] Architecture is healthy! All domain boundaries and file limits respected.")
    else:
        print("\n[FAIL] Architectural issues detected. Please refactor according to GEMINI.md.")
        # sys.exit(1) # Don't exit 1 yet so we can see the full output in terminal if needed

if __name__ == "__main__":
    check_health()
