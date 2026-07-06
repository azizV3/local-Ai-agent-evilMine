from openai import OpenAI 
import json
import os
import importlib
import re
from pathlib import Path

from tools import *


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

SAVE_DIR = PROJECT_ROOT / "saves"
HISTORY_FILE = PROJECT_ROOT / "chat_history.json"
SCRATCHPAD_FILE = PROJECT_ROOT / "scratchpad.txt"
MAX_CONTEXT_TOKENS = 16000
AUTONOMOUS_MODE = True
ENABLE_LOOP_DETECTOR = True
CONSECUTIVE_LOOPS = 0
ALLOW_PARALLEL_TOOLS = False
VAR_CURRENT_TEMP = 0.2

client = OpenAI(
    base_url='http://localhost:11434/v1/',
    api_key='ollama'  
)
def get_system_instruction(allow_parallel):
    base_prompt = (
        "You are an autonomous AI agent equipped with tools to assist the user. "
        "Analyze the user's request and naturally interweave conversational text with your tool requests. "
        "always test a tool before integrating it. "
    )
    if allow_parallel:
        constraint = (
            "STRUCTURAL RULE: You can call multiple JSON tool blocks in a single turn if the actions "
            "are independent. Output each tool block completely enclosed in its own curly braces."
        )
    else:
        constraint = (
            "CRITICAL STRUCTURAL RULE: You can only call exactly ONE JSON tool block per turn. "
            "If a multi-step task requires calling tools multiple times, execute the first tool block now "
            "and wait for the tool response. Do not output multiple JSON blocks."
        )
    
    
    return base_prompt + constraint


def create_new_save(number):
    # Ensure directory exists
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    
    file_path = SAVE_DIR / f"save{number}.json"
    
    if file_path.is_file():
        print("Save already exists!")
    else:
        # Open in write mode, and initialize with an empty JSON array
        with open(file_path, "w") as f:
            json.dump([{
            "role": "system", 
            "content": get_system_instruction(ALLOW_PARALLEL_TOOLS)
        }], f)
        print(f"Created new save: {file_path.name}")


def load_history():
    """Loads chat history from local JSON log file, or initializes standard system prompt."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print("[System Warning]: History file corrupted. Starting fresh.")
    
    # Default fallback setup
    return [
        {
            "role": "system", 
            "content": get_system_instruction(ALLOW_PARALLEL_TOOLS)
        }
    ]


def save_history(messages):
    """Saves raw input/output history array objects back to JSON file."""
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(messages, f, indent=4)
    except IOError as e:
        print(f"[System Error]: Failed to persist chat log: {e}")




def estimate_tokens(messages):
    """Approximates total payload tokens based on character count (1 token ≈ 4 characters)."""
    total_chars = 0
    for msg in messages:
        if "content" in msg and msg["content"]:
            total_chars += len(msg["content"])
        if "tool_calls" in msg and msg["tool_calls"]:
            total_chars += len(json.dumps(msg["tool_calls"]))
    return total_chars // 4

def trim_context(messages, max_tokens=MAX_CONTEXT_TOKENS):
    if estimate_tokens(messages) <= max_tokens:
        return messages

    system_message = messages[0] if messages[0]["role"] == "system" else None
    pool = messages[1:] if system_message else messages

    while estimate_tokens(messages) > max_tokens and len(pool) > 1:
        # Instead of pop(0), remove items until you clear a full logical turn
        # Ensure we don't leave an orphaned 'tool' or 'assistant' tool_call message
        pool.pop(0)

        # EXTRA GUARDRAIL: Checks for broken assistant text or tool execution layouts
        while pool and pool[0].get("role") in ["tool", "assistant"] and "tool_calls" not in pool[0]:
            pool.pop(0)
            
        # Checks for tool blocks whose matching assistant calls were just deleted
        while pool and pool[0].get("role") == "tool":
            pool.pop(0)

        messages = [system_message] + pool if system_message else pool
        
    return messages

def check_for_loops(text_content, tool_detected, current_func, current_args, messages):
    
    #Returns True if the agent is stuck in a text loop or repeating the same tool call.
    
    
    cleaned_text = text_content.strip()
    if len(cleaned_text) > 20 and cleaned_text in [m.get("content", "") for m in messages[-4:]]:
        return "Text-Phrase"

    
    if tool_detected and messages:
        # Look at the very last message in history pool
        last_msg = messages[-1]
        if last_msg.get("role") == "assistant" and "tool_calls" in last_msg:
            last_call = last_msg["tool_calls"][0]["function"]
            
            # Compare current function call to the last one saved
            if last_call["name"] == current_func and last_call["arguments"] == json.dumps(current_args):
                return "Tool-Spam"

    return None

'''def rescan_and_rebind_tools():
    """Rescans tools.json and extendedtoolmap.json to cleanly rebuild live schemas and pointers."""
    print("[Engine Rescan] Re-syncing tool maps directly from disk...")
    try:
        import importlib
        import sys
        import json
        
        # 1. Reset standard framework schemas from tools.py baseline
        import tools as base_tools_mod
        tools.clear()
        
        # Keep only the core built-in framework tools to avoid duplicate stacking
        core_names = ["finish_conversation", "let_user_decide", "write_to_file", "read_scratchpad", "update_scratchpad"]
        tools.extend([t for t in base_tools_mod.tools if t["function"]["name"] in core_names])
        
        # 2. Rescan the raw tools.json file for custom model schemas
        if TOOLS_DEFINITION_PATH.is_file():
            with open(TOOLS_DEFINITION_PATH, "r", encoding="utf-8") as f:
                generated_schemas = json.load(f)
                if isinstance(generated_schemas, list):
                    tools.extend(generated_schemas)
                    
        # 3. Reset core execution mapping pointers
        tools_map.clear()
        tools_map.update({
            "finish_conversation": base_tools_mod.finish_conversation,
            "let_user_decide": base_tools_mod.let_user_decide,
            "write_to_file": base_tools_mod.write_to_file,
            "read_scratchpad": base_tools_mod.read_scratchpad,
            "update_scratchpad": base_tools_mod.update_scratchpad,
            "integrate_new_tool": base_tools_mod.tools_map.get("integrate_new_tool"), 
            "test_tool_autonomously": base_tools_mod.tools_map.get("test_tool_autonomously")
        })
        
        # 4. Rescan extendedtoolmap.json and pull pointers explicitly file-by-file
        if TOOLS_MAP_PATH.is_file():
            with open(TOOLS_MAP_PATH, "r", encoding="utf-8") as f:
                generated_map = json.load(f)
                
            if isinstance(generated_map, dict):
                importlib.invalidate_caches() # Tells Python to check the directory for brand new files
                
                for func_name in generated_map.keys():
                    try:
                        module_name = f"extendedtoolsscripts.{func_name}"
                        
                        # Evict old cached version if it exists
                        if module_name in sys.modules:
                            del sys.modules[module_name]
                            
                        # Target and load the raw python file dynamically
                        mod = importlib.import_module(module_name)
                        tools_map[func_name] = getattr(mod, func_name)
                    except Exception as e:
                        print(f"[Warning] Failed loading dynamic pointer for '{func_name}': {e}")
                        
        print(f"[Engine Rescan] Success! {len(tools)} tools now active in system memory.")
    except Exception as total_err:
        print(f"[Critical Error] Rescan failed: {total_err}")'''


# Iterates through the directory and filters for files
if SAVE_DIR.exists():
    for item in SAVE_DIR.iterdir():
        if item.is_file():
            print(item.name)
else:
    print(r"Save directory does not exist yet.")

choice = str(input("Load save (L) or Create new (N) or summarize save (S): ")).strip().upper()

if choice == "L":
    name = str(input("Enter save name (e.g., save1.json): ")).strip()
    # Safely combine paths using Path division /
    target_path = SAVE_DIR / name
    if target_path.is_file():
        HISTORY_FILE = str(target_path)
    else:
        print("File not found. Falling back to default chat_history.json")
elif choice == "N":
    n = int(input("Enter new save number: "))
    create_new_save(n)
    HISTORY_FILE = str(SAVE_DIR / f"save{n}.json")
elif choice =="S":
    name = str(input("Enter save name (e.g., save1.json): ")).strip()
    # Safely combine paths using Path division /
    target_path = SAVE_DIR / name
    if target_path.is_file():
        HISTORY_FILE = str(target_path)
    else:
        print("File not found. Falling back to default chat_history.json")
    messages = load_history()
    messages.append({"role": "system", "content":"summarize the previous chat"})
    response = client.chat.completions.create(
        model="qwen2.5-coder:14b",
        messages=messages
    )
    summary = [{"role": "assistant", "content":response.choices[0].message.content}]
    HISTORY_FILE= str(SAVE_DIR / f"{name[:-5]}_summary.json")
    save_history(summary)
    exit()
else: 
    print("Invalid choice. Exiting.")
    exit() # Added parentheses to actually terminate



# Initialize messages list from existing persistent JSON file
messages = load_history()




max_iterations = 30
run = True

while run:
    say = str(input("you:"))
    if say == "exit":
        exit()
        
    messages.append({"role": "user", "content": say})
    save_history(messages)  # Persist user entry
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- [Agent Turn {iteration}: Thinking Process] ---")

        # Context safety layer check executed prior to executing LLM inferences
        messages = trim_context(messages)

        stream = client.chat.completions.create(
            model="qwen2.5-coder:14b",
            messages=messages,
            tools=tools,
            parallel_tool_calls=ALLOW_PARALLEL_TOOLS,
            temperature=VAR_CURRENT_TEMP,
            stream=True
        )
        
        collected_content_iteration = ""
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                print(delta, end="", flush=True) 
                collected_content_iteration += delta
        print("\n-------------------------------------------")
        VAR_CURRENT_TEMP = 0.2
        text_content = collected_content_iteration.strip()

        tool_call_detected = False
        function_name = None
        arguments = None
        tool_call_id = f"call_local_{iteration}" 
        maybe_json = None

        # MULTI-JSON PARSER

        detected_tools = []
        idx = 0
        
        while idx < len(text_content):
            if text_content[idx] == "{":
                start_idx = idx
                brace_count = 0
                end_idx = -1
                
                # Scan ahead to find the balancing closing bracket
                for scan_idx in range(start_idx, len(text_content)):
                    if text_content[scan_idx] == "{":
                        brace_count += 1
                    elif text_content[scan_idx] == "}":
                        brace_count -= 1
                        
                    if brace_count == 0:
                        end_idx = scan_idx + 1
                        break
                
                # If a complete balanced block was found, try to parse it
                if end_idx != -1:
                    maybe_json = text_content[start_idx:end_idx]
                    try:
                        parsed_json = json.loads(maybe_json)
                        if "name" in parsed_json and "arguments" in parsed_json:
                            args = parsed_json["arguments"]
                            if isinstance(args, str):
                                args = json.loads(args)
                            
                            # Store the valid tool call details
                            detected_tools.append({
                                "name": parsed_json["name"],
                                "arguments": args
                            })
                    except (json.JSONDecodeError, AttributeError):
                        pass  
                    
                    # Jump the main pointer past this parsed JSON block
                    idx = end_idx - 1
            idx += 1

        tool_call_detected = len(detected_tools) > 0
        if tool_call_detected and not ALLOW_PARALLEL_TOOLS:
              #Truncate the array to only look at the first discovered tool call
              detected_tools = [detected_tools[0]]



        if ENABLE_LOOP_DETECTOR:
            function_name = detected_tools[0]["name"]
            arguments = detected_tools[0]["arguments"]
            
            loop_type = check_for_loops(text_content, tool_call_detected, function_name, arguments, messages)

            if loop_type:
                CONSECUTIVE_LOOPS += 1    
                VAR_CURRENT_TEMP = 1.5           
                if CONSECUTIVE_LOOPS >= 3:
                    CONSECUTIVE_LOOPS = 0  
                    break


                print(f"\n {loop_type} loop detected!")
                
                # Setup valid API history frames so the next turn doesn't crash
                if tool_call_detected:
                    messages.append({
                        "role": "assistant", 
                        "content": text_content[:end_idx] if end_idx != -1 else text_content, 
                        "tool_calls": [{"id": tool_call_id, "type": "function", "function": {"name": function_name, "arguments": json.dumps(arguments)}}]
                    })
                    messages.append({"role": "tool", "tool_call_id": tool_call_id, "content": '{"error": "Loop detected by runtime security guard."}'})
                else:
                    messages.append({"role": "assistant", "content": text_content})
                
                
                messages.append({
                    "role": "system",
                    "content": "CRITICAL NOTICE: You are repeating your previous actions or statements. Break this pattern, change your approach, and try a completely new strategy now."
                })
                save_history(messages)
                continue  
            else:
                CONSECUTIVE_LOOPS = 0



#EXECUTION LAYER 
        if tool_call_detected:
            # Check for immediate control breaks (using the first tool's intent as priority)
            primary_func = detected_tools[0]["name"]
            if primary_func == "finish_conversation":
                messages.append({"role": "assistant", "content": collected_content_iteration})
                messages.append({"role": "system", "content": "you finish the task"})
                save_history(messages)
                break
            elif primary_func == "let_user_decide":
                messages.append({"role": "assistant", "content": collected_content_iteration})
                messages.append({"role": "system", "content": "you let the user decide"})
                save_history(messages)
                break




            # Build the tool_calls list for the assistant message structure
            api_tool_calls = []
            for t_idx, tool in enumerate(detected_tools):
                api_tool_calls.append({
                    "id": f"call_local_{iteration}_{t_idx}",
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "arguments": json.dumps(tool["arguments"])
                    }
                })

            # Append assistant message containing the structural tool intents
            messages.append({
                "role": "assistant",
                "content": collected_content_iteration,
                "tool_calls": api_tool_calls
            })

            # Execute each discovered tool sequentially
            for t_idx, tool in enumerate(detected_tools):
                t_name = tool["name"]
                t_args = tool["arguments"]
                t_id = f"call_local_{iteration}_{t_idx}"
                
                print(f"Model requested: {t_name}({t_args})")
                
                if t_name in tools_map:
                    selected_func = tools_map[t_name]
                    if t_args is None or t_args == {}:
                        result = selected_func()
                    else:
                        result = selected_func(**t_args)

                    # Append individual tool response frame
                    messages.append({
                        "role": "tool",
                        "tool_call_id": t_id,
                        "content": json.dumps(result)
                    })
                else:
                    print(f"[System Error]: Tool '{t_name}' is missing from tools_map.")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": t_id,
                        "content": f'{{"error": "The tool \'{t_name}\' is missing from tools_map."}}'
                    })
                if primary_func == "integrate_new_tool":
                    rescan_and_rebind_tools()
            save_history(messages)
        else:
            # No tool was called. The agent generated plain text.
            messages.append({"role": "assistant", "content": collected_content_iteration})
            save_history(messages)

            if not AUTONOMOUS_MODE:
                # METHOD 1: Clean Break. Hand control straight back to the human.
                print("\n[System]: Awaiting user input...")
                break
            else:
                # METHOD 2: Autonomous Routing. Force the model to decide its next step.
                messages.append({
                    "role": "system", 
                    "content": (
                        "[System Routing Directive]: You have presented text but have not called a concluding tool. "
                        " If you are completely finished speaking to the user, you MUST output a JSON call for 'finish_conversation'. "
                        " If you need user input, you MUST call 'let_user_decide'. "
                        " If you have a remaining autonomous step (like saving data), execute that JSON block now."
                    )
                })
                save_history(messages)
    iteration = 0