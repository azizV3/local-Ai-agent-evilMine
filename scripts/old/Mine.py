from openai import AsyncOpenAI
import json
import os
import asyncio
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
ALLOW_PARALLEL_TOOLS = False
AUTONOMOUS_MODE = True
ENABLE_LOOP_DETECTOR = True
CONSECUTIVE_LOOPS = 0

VAR_CURRENT_TEMP = 0.2

client = AsyncOpenAI(
    base_url='http://localhost:11434/v1/',
    api_key='ollama'  
)
class AsyncAgentManager:
    def __init__(self, history_file=HISTORY_FILE):
        self.history_file = Path(history_file)
        self.messages = self.load_history()
        self.consecutive_loops = 0
        self.var_current_temp = 0.2


    """def get_system_instruction(self, allow_parallel):
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
        
        
        return base_prompt + constraint"""





    def load_history(self):
        #Loads chat history from local JSON log file, or initializes standard system prompt.
        if self.history_file.is_file():
            try:
                with open(self.history_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                print("[System Warning]: History file corrupted. Starting fresh.")
        



    def save_history(self):
        """Saves raw input/output history array objects back to JSON file."""
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.messages, f, indent=4)
        except IOError as e:
            print(f"[System Error]: Failed to persist chat log: {e}")




    def estimate_tokens(self, messages):
        """Approximates total payload tokens based on character count (1 token ≈ 4 characters)."""
        total_chars = 0
        for msg in messages:
            if "content" in msg and msg["content"]:
                total_chars += len(msg["content"])
            if "tool_calls" in msg and msg["tool_calls"]:
                total_chars += len(json.dumps(msg["tool_calls"]))
        return total_chars // 4

    def trim_context(self, messages, max_tokens=MAX_CONTEXT_TOKENS):
        if self.estimate_tokens(messages) <= max_tokens:
            return messages

        system_message = messages[0] if messages[0]["role"] == "system" else None
        pool = messages[1:] if system_message else messages

        while self.estimate_tokens(messages) > max_tokens and len(pool) > 1:
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

    def check_for_loops(self, text_content, tool_detected, current_func, current_args, messages):
        
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








 

    async def run_turn(self, user_input: str, on_token, on_status, on_tool):
        max_iterations = 30
        iteration = 0
        self.messages.append({"role": "user", "content": user_input})
        self.save_history()

        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            await on_status(f"Turn {iteration}: Thinking Process ")   
            # Context safety layer check executed prior to executing LLM inferences
            self.messages = self.trim_context(self.messages)

            stream = await client.chat.completions.create(
                model="qwen2.5-coder:14b",
                messages=self.messages,
                tools=tools,
                parallel_tool_calls=ALLOW_PARALLEL_TOOLS,
                temperature=self.var_current_temp,
                stream=True
            )
            
            print(f"DEBUG: Actual payload:")
            collected_content_iteration = ""
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    
                    collected_content_iteration += delta
                    print(delta)
                    await on_token(delta)
            
            self.var_current_temp = 0.2
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
                if tool_call_detected:
                    function_name = detected_tools[0]["name"]
                    arguments = detected_tools[0]["arguments"]
                else:
                    function_name= ""
                    arguments=""
                
                loop_type = self.check_for_loops(text_content, tool_call_detected, function_name, arguments, self.messages)

                if loop_type:
                    self.consecutive_loops += 1    
                    self.var_current_temp = 1.5           
                    if self.consecutive_loops >= 3:
                        self.consecutive_loops = 0  
                        await on_status("Loop Guard Exception: Maximum consecutive threshold reached.")
                        break


                    await on_status(f"Security Warning: {loop_type} loop detected! Recalibrating context temperature...")                    
                    # Setup valid API history frames so the next turn doesn't crash
                    if tool_call_detected:
                        self.messages.append({
                            "role": "assistant", 
                            "content": text_content[:end_idx] if end_idx != -1 else text_content, 
                            "tool_calls": [{"id": tool_call_id, "type": "function", "function": {"name": function_name, "arguments": json.dumps(arguments)}}]
                        })
                        self.messages.append({"role": "tool", "tool_call_id": tool_call_id, "content": '{"error": "Loop detected by runtime security guard."}'})
                    else:
                        self.messages.append({"role": "assistant", "content": text_content})
                    
                    
                    self.messages.append({
                        "role": "system",
                        "content": "CRITICAL NOTICE: You are repeating your previous actions or statements. Break this pattern, change your approach, and try a completely new strategy now."
                    })
                    self.save_history()
                    continue  
                else:
                    self.consecutive_loops = 0



    #EXECUTION LAYER 
            if tool_call_detected:
                # Check for immediate control breaks (using the first tool's intent as priority)
                primary_func = detected_tools[0]["name"]
                if primary_func == "finish_conversation":
                    self.messages.append({"role": "assistant", "content": collected_content_iteration})
                    self.messages.append({"role": "system", "content": "you finish the task"})
                    self.save_history()
                    await on_status("Conversation concluded by Agent.")
                    break
                elif primary_func == "let_user_decide":
                    self.messages.append({"role": "assistant", "content": collected_content_iteration})
                    self.messages.append({"role": "system", "content": "you let the user decide"})
                    
                    self.save_history()
                    await on_status("Control suspended: Awaiting User decision.")
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
                self.messages.append({
                    "role": "assistant",
                    "content": collected_content_iteration,
                    "tool_calls": api_tool_calls
                })

                # Execute each discovered tool sequentially
                for t_idx, tool in enumerate(detected_tools):
                    t_name = tool["name"]
                    t_args = tool["arguments"]
                    t_id = f"call_local_{iteration}_{t_idx}"
                    
                    await on_status(f"Executing Tool Call: {t_name}")                    
                    if t_name in tools_map:
                        loop = asyncio.get_running_loop()
                        selected_func = tools_map[t_name]
                        if t_args is None or t_args == {}:
                            result = await loop.run_in_executor(None, selected_func)
                        else:
                            result = await loop.run_in_executor(None, lambda: selected_func(**t_args))

                        # Append individual tool response frame
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": t_id,
                            "content": json.dumps(result)
                        })
                        await on_tool({"tool": t_name, "result": result})
                    else:
                        
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": t_id,
                            "content": f'{{"error": "The tool \'{t_name}\' is missing from tools_map."}}'
                        })
                        await on_tool({"tool": t_name, "result":{"error": f"The tool '{t_name}' is missing from tools_map."}})
                    if primary_func == "integrate_new_tool":
                        globals()["rescan_and_rebind_tools"]()
            
            else:
                # No tool was called. The agent generated plain text.
                self.messages.append({"role": "assistant", "content": collected_content_iteration})
                

                if not AUTONOMOUS_MODE:
                    break
                else:
                    self.messages.append({
                        "role": "system", 
                        "content": (
                            "[System Routing Directive]: You have presented text but have not called a concluding tool. "
                            " If you are completely finished speaking to the user, you MUST output a JSON call for 'finish_conversation'. "
                            " If you need user input, you MUST call 'let_user_decide'. "
                            " If you have a remaining autonomous step (like saving data), execute that JSON block now."
                        )
                    })
            self.save_history()
        iteration = 0