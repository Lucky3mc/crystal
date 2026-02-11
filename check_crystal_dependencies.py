import ast
import importlib
import os
import subprocess
import sys
import sysconfig
from typing import Set

# --- CONFIGURATION ---
SKILLS_PATH = r"C:\Users\user\Documents\crystal_ai\skills"

PROJECT_MODULES = {"crystal"} # Your own project modules to ignore
AUTO_INSTALL = False          # Set True to automatically install missing packages

# --- HELPER FUNCTIONS ---
def find_imports_in_file(file_path: str) -> Set[str]:
    """Parse a Python file and return all top-level imported modules."""
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=file_path)
    
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                modules.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module.split(".")[0])
    return modules

def collect_all_skill_modules(skills_path: str) -> Set[str]:
    """Walk the skills folder and collect all imported modules."""
    all_modules = set()
    for root, dirs, files in os.walk(skills_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                imports = find_imports_in_file(file_path)
                all_modules.update(imports)
    return all_modules

def filter_third_party(modules: Set[str]) -> Set[str]:
    """Remove standard library modules and project modules."""
    stdlib_path = sysconfig.get_paths()["stdlib"]
    std_modules = set(os.listdir(stdlib_path))
    third_party = set()
    for mod in modules:
        if mod in PROJECT_MODULES or mod in std_modules:
            continue
        try:
            importlib.import_module(mod)
        except ImportError:
            third_party.add(mod)
    return third_party

def get_module_version(module_name: str) -> str:
    """Return the version of an installed module, or 'Not installed'."""
    try:
        mod = importlib.import_module(module_name)
        return getattr(mod, "__version__", "Unknown")
    except ImportError:
        return "Not installed"

def check_and_install_modules(modules: Set[str], auto_install: bool = False):
    """Check which modules are missing, report, and optionally install them."""
    missing = []
    for mod in modules:
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(mod)

    print("\n--- Crystal AI Dependency Report ---")
    for mod in modules:
        version = get_module_version(mod)
        status = "✅ Installed" if version != "Not installed" else "❌ Missing"
        print(f"{mod}: {status} (version: {version})")

    if missing:
        print("\n⚠️ Missing modules:", ", ".join(missing))
        if auto_install:
            for mod in missing:
                print(f"🔄 Installing {mod}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", mod])
            print("✅ All missing modules installed.")
    else:
        print("\n✅ All dependencies are installed!")

    return missing

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    all_imports = collect_all_skill_modules(SKILLS_PATH)
    third_party_modules = filter_third_party(all_imports)
    missing_modules = check_and_install_modules(third_party_modules, auto_install=AUTO_INSTALL)
