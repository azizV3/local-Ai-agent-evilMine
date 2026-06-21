from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

SAVE_DIR = PROJECT_ROOT / "saves"
HISTORY_FILE = PROJECT_ROOT / "chat_history.json"
SCRATCHPAD_FILE = PROJECT_ROOT / "scratchpad.txt"

def read_scratchpad():
    """Reads current multi-step agent notes from scratchpad text file."""
    if not os.path.exists(SCRATCHPAD_FILE):
        return "Scratchpad is empty. Use update_scratchpad to organize your thoughts or plan."
    with open(SCRATCHPAD_FILE, "r") as f:
        return f.read()

def update_scratchpad(content):
    """Overwrites persistent scratchpad file with updated state metrics or execution logs."""
    with open(SCRATCHPAD_FILE, "w") as f:
        f.write(content)
    return "Scratchpad updated successfully."

