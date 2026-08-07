

from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BASE_DIR1 = PROJECT_ROOT / "evilDiary"

BASE_DIR1.mkdir(parents=True, exist_ok=True) #so it dosent crash 

def write_to_file(file_name, content):
    try:
        target_path = file_name

        with open(target_path, "w", encoding="utf-8") as file:
            content = content.replace('\\n', '\n').replace('\\"', '"')
            file.write(content)
        return f"sucess"
    except Exception as e:
        return f"[System Error]: Failed to write file '{file_name}'. Reason: {str(e)}"


def read_file(filename):
    """
    Reads a text file and returns its content as a string.
    """
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return f"Error: The file '{filename}' does not exist."





def edit_file_content(filename, old_text, new_text):
    """
    Finds specific text inside a file and replaces it with new text.
    """
    try:
        # Step 1: Read the existing content
        with open(filename, "r", encoding="utf-8") as file:
            content = file.read()
        
        # Step 2: Modify the content in memory
        updated_content = content.replace(old_text, new_text)
        
        # Step 3: Write the updated content back to the file
        with open(filename, "w", encoding="utf-8") as file:
            file.write(updated_content)
            
        print("File edited successfully.")
        
    except FileNotFoundError:
        print(f"Error: The file '{filename}' does not exist.")


