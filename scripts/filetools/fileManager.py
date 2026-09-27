import os
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
TARGET_DIRECTORY =   PROJECT_ROOT / "evilDiary"

TARGET_DIRECTORY.mkdir(parents=True, exist_ok=True) #so it dosent crash 

LOG_FILE_PATH = Path(__file__).resolve().parent.parent.parent / "logs" / "filelogs.txt"
LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_safe_path(filename: str) -> Path:
    """
    Resolves the target path and ensures it stays strictly 
    within TARGET_DIRECTORY bounds.
    """
    base_dir = Path(TARGET_DIRECTORY).resolve()
    
    # Strip leading slashes so pathlib doesn't reset to the drive root (C:\)
    clean_filename = filename.lstrip("/\\")
    
    target_path = (base_dir / clean_filename).resolve()

    try:
        target_path.relative_to(base_dir)
    except ValueError:
        raise PermissionError(f"Access Denied: Path '{filename}' attempts to escape workspace.")

    return target_path


def write_to_file(file_name, content):
    try:
        target_path = get_safe_path(file_name)

        with open(target_path, "w", encoding="utf-8") as file:
            content = content.replace('\\n', '\n').replace('\\"', '"') #could corrupt code, to check !!!
            file.write(content)

            #update log
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(LOG_FILE_PATH, "a", encoding="utf-8") as lfile:
                lfile.write(f"***************** {now} ***************** \n new file created | path: {target_path}  content:  {content} \n")
        return f"sucess"
    except Exception as e:
        return f"[System Error]: Failed to write file '{target_path}'. Reason: {str(e)}"


def read_file(filename):
    """
    Reads a text file and returns its content as a string.
    """
    target_path = get_safe_path(filename)
    try:
        with open(target_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return f"Error: The file '{target_path}' does not exist."





def edit_file_content(filename: str = None, file_path: str = None, old_text: str = "", new_text: str = ""):
    path_input = filename or file_path
    if not path_input:
        return "Error: No filename or file_path provided."

    try:
        target_path = get_safe_path(path_input)
        
        with open(target_path, "r", encoding="utf-8") as file:
            content = file.read()
        
        
        if old_text not in content:
            return f"Error: Could not edit file. The text '{old_text}' was not found in '{path_input}'. Ensure line endings and spaces match."
        
        
        updated_content = content.replace(old_text, new_text)
        
        with open(target_path, "w", encoding="utf-8") as file:
            file.write(updated_content)
        
        
        #update log file
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as lfile:
            lfile.write(f"***************** {now} *****************\n"
            f" target path:{target_path}\n"
            f"| old content:  {old_text}\n"
            f"| new edited content: {new_text}\n"
            )   

        return f"Success: Modified '{path_input}'. Replaced occurrence of targeted text."
        
    except FileNotFoundError:
        return f"Error: The file '{path_input}' does not exist."
    except Exception as e:
        return f"[System Error]: Failed to edit '{path_input}'. Reason: {str(e)}"

def get_file_size(filename):
    try:
        target_path = get_safe_path(filename)
        return(os.path.getsize(target_path))
    except:
        return(0)