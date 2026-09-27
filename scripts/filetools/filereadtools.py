import os
import json
from pathlib import Path


# Configuration
TARGET_DIRECTORY = "./my_project"  # The folder you want to index
INDEX_FILE_PATH = "index_map.json"

# Files/Directories to skip to avoid cluttering the index
IGNORE_LIST = {".git", "node_modules", "__pycache__", ".DS_Store", "venv", ".env"}
SUPPORTED_EXTENSIONS = {".txt", ".md", ".py", ".js", ".json", ".csv", ".html", ".css", ".yml", ".yaml"}

def should_ignore(path: Path) -> bool:
    """Checks if any part of the path is in our ignore list."""
    return any(part in IGNORE_LIST for part in path.parts)

def build_index(directory_path: str) -> dict:
    """
    Crawls every directory, subdirectory, and file recursively.
    Returns a dictionary structure of the entire directory tree.
    """
    root = Path(directory_path)
    
    # Error handling: Stop immediately if the directory doesn't exist
    if not root.exists():
        raise FileNotFoundError(f"The target directory '{directory_path}' does not exist.")
    if not root.is_dir():
        raise NotADirectoryError(f"The path '{directory_path}' is not a directory.")

    index = {
        "directory_root": ".",
        "subdirectories": [],
        "files": []
    }
    
    # rglob("*") recursively finds files AND folders at ANY depth (nested sub-sub-directories)
    for path in root.rglob("*"):
        if should_ignore(path):
            continue
            
        # Format as /subfolder/file.ext with posix slashes
        relative_path = path.relative_to(root).as_posix()
        
        if path.is_dir():
            index["subdirectories"].append(str(relative_path))
            
        elif path.is_file():
            file_info = {
                "relative_path": str(relative_path),
                "extension": path.suffix,
                "size_kb": round(path.stat().st_size / 1024, 2),
                "preview": ""
            }
            
            # Extract a quick preview for the agent
            if path.suffix in SUPPORTED_EXTENSIONS:
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(200).strip().replace("\n", " ")
                        file_info["preview"] = content[:150] + "..." if len(content) > 150 else content
                except Exception as e:
                    file_info["preview"] = f"[Error reading file preview: {str(e)}]"
            
            index["files"].append(file_info)
            
    return index


#bug:  TypeError: search_directory_index() got an unexpected keyword argument 'directory_path'

def search_directory_index(query: str = None) -> str:
    """
    Searches the directory index.
    If the index file doesn't exist, it auto-generates it first.
    If the target directory doesn't exist, returns a clean error.
    """
    # 1. Check if the index needs to be built/rebuilt // TO CHANGE !!!!
    #if not os.path.exists(INDEX_FILE_PATH):
    try:
            print(f"Index file '{INDEX_FILE_PATH}' not found. Generating now...")
            project_index = build_index(TARGET_DIRECTORY)
            
            #maybe use getsafepath

            with open(INDEX_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(project_index, f, indent=2)
            print("Index generated successfully.")
            
    except (FileNotFoundError, NotADirectoryError) as e:
            return f"Error: Cannot build index. {str(e)}"
    except Exception as e:
            return f"Error building index: {str(e)}"

    # 2. Load the existing index
    try:
        with open(INDEX_FILE_PATH, "r") as f:
            index = json.load(f)
    except Exception as e:
        return f"Error reading index file: {str(e)}"
    
    # 3. Return results (filtered or complete)
    if not query:
        return json.dumps(index, indent=2)
    
    query = query.lower()
    filtered_files = [
        f for f in index.get("files", [])
        if query in f["relative_path"].lower() or query in f["preview"].lower()
    ]
    
    filtered_dirs = [
        d for d in index.get("subdirectories", [])
        if query in d.lower()
    ]
    
    result = {
        "directory_root": index["directory_root"],
        "subdirectories": filtered_dirs,
        "files": filtered_files
    }
    return json.dumps(result, indent=2)