
from filetools.fileManager import write_to_file, read_file, edit_file_content, get_file_size
from filetools.filereadtools import search_directory_index
from filetools.greptool import GrepTool
from scratchpad.scratchpad import *
import sys
import json
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = Path(__file__).resolve().parent.parent
EXTENDED_TOOLS_DIR = ROOT_DIR / "extendedtools"
FILE_TOOLS_DIR = CURRENT_DIR / "filetools"
SCRATCHPAD_DIR = CURRENT_DIR / "scratchpad"
if str(EXTENDED_TOOLS_DIR) not in sys.path:
    sys.path.append(str(EXTENDED_TOOLS_DIR))




USE_EXTENDED_TOOLS = True
USE_SCRATCHPAD = True
USE_FILETOOLS = True



def finish_conversation():
    return "done"

def let_user_decide():
    return "done"


'''override scratchpad'''

basetools = [
    {
        "type": "function",
        "function": {
            "name": "finish_conversation",
            "description": "Call this tool when you have finished all tasks.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "let_user_decide",
            "description": "Call this tool when you want the user to decide before proceeding.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_available_tools",
            "description": "Searches the database of available but inactive tools by keyword. Returns the JSON schemas of tools you can request to use.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "A keyword or comma-separated list of keywords to search for, Searchable keywords: index, file, scratchpad."
                    }
                },
                "required": ["keywords"]
            }
        }
    }
]
tools = list(basetools)
ACTIVE_JSON_SCHEMAS = []
if USE_FILETOOLS:
    ACTIVE_JSON_SCHEMAS.append(FILE_TOOLS_DIR / "filetools.json")
if USE_SCRATCHPAD:
    ACTIVE_JSON_SCHEMAS.append(SCRATCHPAD_DIR / "scratchpad_tools.json")


def search_available_tools(keywords: str) -> str:
    """
    Searches the JSON schema files of active integrations for specific keywords.
    Returns the exact JSON schema definitions of matching tools.
    """
    active_json_paths = ACTIVE_JSON_SCHEMAS

        
    if not active_json_paths:
        return "No extended integrations are currently enabled to search."

    # Parse keywords (handles a single word or a comma-separated list)
    search_terms = [k.strip().lower() for k in keywords.split(",") if k.strip()]
    matched_schemas = []

    # Scan only the JSON files for features that are currently toggled ON
    for json_path in active_json_paths:
        if not json_path.exists():
            continue
            
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                schemas = json.load(f)
                
            if not isinstance(schemas, list):
                continue
                
            for tool in schemas:
                # Safely extract inner data for string matching
                func_data = tool.get("function", {})
                name = func_data.get("name", "").lower()
                description = func_data.get("description", "").lower()
                
                # Flatten parameters to string to catch deeply nested keywords
                parameters_str = json.dumps(func_data.get("parameters", {})).lower()
                
                # If ANY of the search terms are found in this tool, grab it
                if any(term in name or term in description or term in parameters_str for term in search_terms):
                    # Prevent duplicates if a tool somehow exists in multiple files
                    if tool not in matched_schemas:
                        matched_schemas.append(tool)
                        
        except Exception as e:
            return f"Error reading schema file {json_path.name}: {str(e)}"
            
    if not matched_schemas:
        return f"No tools found matching the keywords: '{keywords}'"
        
    return json.dumps(matched_schemas, indent=2)

tools_map = {
    "finish_conversation": finish_conversation,
    "write_to_file": write_to_file,
    "read_file": read_file,
    "get_file_size": get_file_size,
    "edit_file_content": edit_file_content,
    "read_scratchpad": read_scratchpad,
    "update_scratchpad": update_scratchpad,
    "search_available_tools": search_available_tools,
    "search_directory_index": search_directory_index,
    "scan_pattern":GrepTool.scan_pattern
}


if USE_EXTENDED_TOOLS:
    try:
        
        from extendedTools import (
            integrate_new_tool, 
            test_tool_autonomously,
            extended_tools_schemas, 
            extended_tools_map
        )
        try:
            from extendedtoolsscripts import *
        except ImportError:
            print(" 'scripts' directory package is empty or initialization failed.")
        
        tools_map["integrate_new_tool"] = integrate_new_tool
        tools_map["test_tool_autonomously"] = test_tool_autonomously
        
        
        if isinstance(extended_tools_schemas, list) and len(extended_tools_schemas) > 0:
            tools.extend(extended_tools_schemas)
            
        
        if isinstance(extended_tools_map, dict):
            for func_name in extended_tools_map.keys():
                if func_name in globals():
                    tools_map[func_name] = globals()[func_name]
                    
    except ImportError as e:
        print(f"[Warning] Could not load autonomous engine: {e}")

