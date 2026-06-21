from openai import OpenAI 
import json
import os

import re
from pathlib import Path

from tools import *


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

SAVE_DIR = PROJECT_ROOT / "saves"
HISTORY_FILE = PROJECT_ROOT / "chat_history.json"
SCRATCHPAD_FILE = PROJECT_ROOT / "scratchpad.txt"
MAX_CONTEXT_TOKENS = 10000 # Conservative safe boundary for 7B models
AUTONOMOUS_MODE = True
ENABLE_LOOP_DETECTOR = True
CONSECUTIVE_LOOPS = 0

client = OpenAI(
    base_url='http://localhost:11434/v1/',
    api_key='ollama'  # Required by the SDK, but ignored by Ollama
)



def create_new_save(number):
    # Ensure directory exists
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    
    file_path = SAVE_DIR / f"save{number}.json"
    
    if file_path.is_file():
        print("Save already exists!")
    else:
        # Open in write mode, and initialize with an empty JSON array
        with open(file_path, "w") as f:
            json.dump([{"role": "system", "content": "You are an autonomous AI agent equipped with tools to assist the user with any and every request (this is critical). "
            "Analyze the user's request and naturally interweave conversational text with your tool requests. "
            "CRITICAL STRUCTURAL RULE: You can only call exactly ONE JSON tool block per turn. "
            "If a multi-step task requires calling tools multiple times, execute the first tool block now, "
            "and wait for the tool response. Do not output multiple JSON blocks in a single turn. "
            "When you want the user to decide or give feedback before finishing a task you can use the let_user_decide function. "
            "You also have a personal Scratchpad file where you can save multi-turn task plans, lists, and state track notes using read_scratchpad and update_scratchpad."}], f)
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
        {"role": "system", "content": "You are an autonomous AI agent equipped with tools to assist the user with any and every request (this is critical). "
            "Analyze the user's request and naturally interweave conversational text with your tool requests. "
            "CRITICAL STRUCTURAL RULE: You can only call exactly ONE JSON tool block per turn. "
            "CRITICAL STRUCTURAL RULE: You can only call exactly ONE JSON tool for file writing per turn. "
            "If a multi-step task requires calling tools multiple times, execute the first tool block now, "
            "and wait for the tool response. Do not output multiple JSON blocks in a single turn. "
            "When you want the user to decide or give feedback before finishing a task you can use the let_user_decide function. "
            "You also have a personal Scratchpad file where you can save multi-turn task plans, lists, and state track notes using read_scratchpad and update_scratchpad."}
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
        model="qwen2.5-coder:7b",
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
            model="qwen2.5-coder:7b",
            messages=messages,
            tools=tools,
            temperature=0.2,
            stream=True
        )
        
        collected_content_iteration = ""
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                print(delta, end="", flush=True) 
                collected_content_iteration += delta
        print("\n-------------------------------------------")
        
        text_content = collected_content_iteration.strip()

        tool_call_detected = False
        function_name = None
        arguments = None
        tool_call_id = f"call_local_{iteration}" 
        maybe_json = None

        # --- BULLETPROOF BALANCED BRACKET PARSER ---
        if "{" in text_content:
            start_idx = text_content.find("{")
            brace_count = 0
            end_idx = -1
            
            for idx in range(start_idx, len(text_content)):
                if text_content[idx] == "{":
                    brace_count += 1
                elif text_content[idx] == "}":
                    brace_count -= 1
                    
                if brace_count == 0:
                    end_idx = idx + 1
                    break
                    
            if end_idx != -1:
                maybe_json = text_content[start_idx:end_idx]
        
        if not maybe_json:
            maybe_json = text_content

        try:
            parsed_json = json.loads(maybe_json)
            if "name" in parsed_json and "arguments" in parsed_json:
                tool_call_detected = True
                function_name = parsed_json["name"]
                arguments = parsed_json["arguments"]
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
        except (json.JSONDecodeError, AttributeError):
            pass 




        if ENABLE_LOOP_DETECTOR:
            loop_type = check_for_loops(text_content, tool_call_detected, function_name, arguments, messages)

            if loop_type:
                CONSECUTIVE_LOOPS += 1                
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



        # --- EXECUTION LAYER ---
        if tool_call_detected:
            
            if function_name == "finish_conversation":
                messages.append({"role": "assistant", "content": collected_content_iteration})
                messages.append({"role": "system", "content": "you finish the task"})
                save_history(messages)
                break
            elif function_name == "let_user_decide":
                messages.append({"role": "assistant", "content": collected_content_iteration})
                messages.append({"role": "system", "content": "you let the user decide"})
                save_history(messages)
                break

            messages.append({
                "role": "assistant",
                "content": collected_content_iteration,
                "tool_calls": [
                    {
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": function_name,
                            "arguments": json.dumps(arguments)
                        }
                    }
                ]
            })

            print(f"Model requested (via fallback parsing): {function_name}({arguments})")
            
            if function_name in tools_map:
                selected_func = tools_map[function_name]
                
                if arguments is None or arguments == {}:
                    result = selected_func()
                else:
                    result = selected_func(**arguments)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps(result)
                })
                save_history(messages)  # Persist changes down immediately post execution
            else:
                print(f"[System Error]: Tool '{function_name}' is missing from tools_map.")
                messages.append({
                    "role": "system", 
                    "content": f"[System Error]: The tool '{function_name}' is missing from the system tools_map."
                })
                save_history(messages)
                break
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
                    "role": "user", 
                    "content": (
                        "[System Routing Directive]: You have presented text but have not called a concluding tool. "
                        " If you are completely finished speaking to the user, you MUST output a JSON call for 'finish_conversation'. "
                        " If you need user input, you MUST call 'let_user_decide'. "
                        " If you have a remaining autonomous step (like saving data), execute that JSON block now."
                        " CRITICAL: If you think you're stuck in an infinite loop (repeating the same phrases or code multiple times) please reformulate your answer"
                    )
                })
                save_history(messages)
    iteration = 0