from pathlib import Path
import json
import subprocess
import sys
import re

# Align all path constants globally in one spot
SCRIPT_DIR = Path(__file__).resolve().parent
TOOLS_DEFINITION_PATH = SCRIPT_DIR / "tools.json"
TOOLS_MAP_PATH = SCRIPT_DIR / "extendedtoolmap.json"
CUSTOM_TOOLS_DIR = SCRIPT_DIR / "extendedtoolsscripts"

AUTONOMOUS_ENGINE_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "test_tool_autonomously",
            "description": "Writes a temporary python script to test newly generated code. Use this to verify code runs without syntax or runtime errors before integrating it. Make sure to always use this before doing integrate_new_tool. This can also be used to run pip commands",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_script_name": {"type": "string", "description": "Name of the temp file, e.g., temp_test.py"},
                    "test_code": {"type": "string", "description": "The full python code to execute. MUST include standard python imports and print statements for output."}
                },
                "required": ["test_script_name", "test_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "integrate_new_tool",
            "description": "Permanently registers a verified, bug-free python code file into the system so it can be used in future turns. Always use the test_tool_autonomously before this functino If an api key is required, let the user decide.",
            "parameters": {
                "type": "object",
                "properties": {
                    "function_code": {"type": "string", "description": "The raw executable python function def block."},
                    "schema_dict": {"type": "object", "description": "The complete, properly formatted JSON schema for the new tool. It MUST follow the exact outer structure: {'type': 'function', 'function': {'name': '...', 'description': '...', 'parameters': {'type': 'object', 'properties': {}, 'required': []}}}. Do not omit the outer type or function wrapper objects"}
                },
                "required": ["function_code", "schema_dict"]
            }
        }
    }
]

extended_tools_schemas = list(AUTONOMOUS_ENGINE_SCHEMAS)
extended_tools_map = {
    "integrate_new_tool": "integrate_new_tool",
    "test_tool_autonomously": "test_tool_autonomously"
}

def _load_json_safely(file_path: Path):
    """Helper to load JSON files while stripping out python/shell style comments."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Remove standard single-line comments (#...) to avoid JSONDecodeErrors
        cleaned_content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
        return json.loads(cleaned_content) if cleaned_content.strip() else None
    except Exception as e:
        print(f"[Warning] Could not load {file_path.name}: {e}")
        return None

# 2. Load the user-generated tools from disk and aggregate them into the list
if TOOLS_DEFINITION_PATH.is_file():
    generated_schemas = _load_json_safely(TOOLS_DEFINITION_PATH)
    if isinstance(generated_schemas, list):
        extended_tools_schemas.extend(generated_schemas)

# 3. Load the user-generated map from disk and update the dictionary
if TOOLS_MAP_PATH.is_file():
    generated_map = _load_json_safely(TOOLS_MAP_PATH)
    if isinstance(generated_map, dict):
        extended_tools_map.update(generated_map)


def integrate_new_tool(function_code: str, schema_dict: dict) -> str:
    """
    Dynamically integrates a verified tool into the system by writing a dedicated 
    python file, auto-updating the custom_tools/__init__.py, and appending details 
    to tools.json and extendedtoolmap.json.
    """
    try:
        # 1. Clean up LLM string-escaping quirks (\n and \")
        cleaned_code = function_code.replace('\\n', '\n').replace('\\"', '"')
        
        # 2. Extract function name to track duplicates across files
        func_match = re.search(r"def\s+(\w+)\s*\(", cleaned_code)
        if not func_match:
            return "INTEGRATION FAILED: Could not parse a valid Python function definition name."
        
        func_name = func_match.group(1)

        # 3. Step 1: Create sub-directory if it doesn't exist and write individual file

        tool_file_path = CUSTOM_TOOLS_DIR / f"{func_name}.py"
        
        if tool_file_path.is_file():
            return f"INTEGRATION FAILED: Function file '{func_name}.py' already exists."
        
        with open(tool_file_path, "w", encoding="utf-8") as f:
            f.write(cleaned_code)

        # 4. Automatically regenerate __init__.py to handle importing the whole subdirectory
        init_file_path = CUSTOM_TOOLS_DIR / "__init__.py"
        py_modules = [p.stem for p in CUSTOM_TOOLS_DIR.glob("*.py") if p.stem != "__init__"]
        
        with open(init_file_path, "w", encoding="utf-8") as init_f:
            for module in py_modules:
                init_f.write(f"from .{module} import {module}\n")

        # 5. Step 2: Append structural schema array elements to tools.json safely
        schemas = _load_json_safely(TOOLS_DEFINITION_PATH) or []
        if not isinstance(schemas, list):
            schemas = []
            
        # Append only if it isn't already declared in the schema list
        if not any(s.get("function", {}).get("name") == func_name for s in schemas):
            schemas.append(schema_dict)
            with open(TOOLS_DEFINITION_PATH, "w", encoding="utf-8") as f:
                json.dump(schemas, f, indent=4)

        # 6. Step 3: Safely update extendedtoolmap.json as a single cohesive object
        tools_map_dict = _load_json_safely(TOOLS_MAP_PATH) or {}
        if not isinstance(tools_map_dict, dict):
            tools_map_dict = {}

        # Insert entry into our mapping dictionary
        tools_map_dict[func_name] = func_name

        # Completely rewrite the file, keeping the single {} footprint intact
        with open(TOOLS_MAP_PATH, "w", encoding="utf-8") as f:
            json.dump(tools_map_dict, f, indent=4)
            
        return f"SUCCESS: Integrated new tool '{func_name}' into individual file, updated package package initialization, schema array, and map registry."
        
    except Exception as e:
        return f"INTEGRATION SYSTEM ERROR: {str(e)}"




def test_tool_autonomously(test_script_name: str, test_code: str):
    """
    Writes a temporary test file and runs it using a new sub-instance 
    of the current python environment to check for runtime or syntax errors.
    """
    try:
        # 1. Create a temporary test path
        test_file = SCRIPT_DIR / test_script_name
        
        # Ensure string unescaping is handled
        cleaned_test_code = test_code.replace('\\n', '\n').replace('\\"', '"')
        
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(cleaned_test_code)
            
        # 2. Run the code using the current environment's executable (keeps venv active)
        result = subprocess.run(
            [sys.executable, str(test_file)],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        # 3. Clean up the test file right after execution
        if test_file.exists():
            test_file.unlink()
            
        # 4. Return flat text blocks so local LLM parsing is foolproof
        if result.returncode == 0:
            return f"TEST PASSED:\n{result.stdout}"
        else:
            return f"TEST FAILED:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            
    except subprocess.TimeoutExpired:
        if Path(test_script_name).exists():
            Path(test_script_name).unlink()
        return "TEST FAILED: Execution timed out. Potential infinite loop detected."
    except Exception as e:
        return f"TEST SYSTEM ERROR: {str(e)}"