# server.py
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

from Mine import AsyncAgentManager, SAVE_DIR, client, ALLOW_PARALLEL_TOOLS
import tools
from tools import search_available_tools
import filetools.fileManager as filemanager
import filetools.filereadtools as filereadtools
from modes import WEBMODEPROMPT
PROJECT_MODE = False
CURRENT_MODE = ""

def get_system_instruction(allow_parallel, curr_mode):
        base_prompt = (
            "You are an autonomous AI agent equipped with tools to assist the user. "
            "Analyze the user's request and naturally interweave conversational text with your tool requests. "
            "always test a tool before integrating it. "
            "you are equipped with a multitued of tools [file manipulation, indexing, scratchpad] you will need to use search_available_tools to find out how they work"
            "If you are completely finished speaking to the user, you MUST output a JSON call for 'finish_conversation'.  If you need user input, you MUST call 'let_user_decide'."
        )
        if curr_mode == 'webmode':
            mode = WEBMODEPROMPT
            


            base_prompt += mode
        if allow_parallel:
            constraint = (
                "STRUCTURAL RULE: You can call multiple JSON tool blocks in a single turn if the actions "
                "are independent. Output each tool block completely enclosed in its own curly braces."
                "1. TOOL DISCOVERY: Use 'search_available_tools' to find tool schemas before calling them. If no tools match, retry with alternate keywords (e.g., 'file', 'read', 'edit', 'directory')."
                "2. SCHEMA ADHERENCE: Use EXACT parameter names and types from tool schemas. Do not invent or guess arguments."
                "3. GROUNDED EXECUTION: Base actions and responses ONLY on actual tool outputs. If a tool fails or crashes, read the error, adjust arguments, and try again. Never invent file content or code snippets."
            )
        else:
            constraint = (
                "CRITICAL STRUCTURAL RULE: You can only call exactly ONE JSON tool block per turn. "
                "If a multi-step task requires calling tools multiple times, execute the first tool block now "
                "and wait for the tool response. Do not output multiple JSON blocks."
                "1. TOOL DISCOVERY: Use 'search_available_tools' to find tool schemas before calling them. If no tools match, retry with alternate keywords (e.g., 'file', 'read', 'edit', 'directory')."
                "2. SCHEMA ADHERENCE: Use EXACT parameter names and types from tool schemas. Do not invent or guess arguments."
                "3. GROUNDED EXECUTION: Base actions and responses ONLY on actual tool outputs. If a tool fails or crashes, read the error, adjust arguments, and try again. Never invent file content or code snippets."
            )
        if curr_mode == 'webmode':
            constraint += search_available_tools('index,file,edit,scratchpad')
        
        base_prompt += constraint

        
        return base_prompt















app = FastAPI()
generation_lock = asyncio.Lock()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global dictionary 
current_session = {"manager": AsyncAgentManager()}



class SaveConfig(BaseModel):
    name: str

class InitConfig(BaseModel):
    action: str  # "L" (Load), "N" (Create New)
    value: str   # filename or save number string

class DirectoryConfig(BaseModel):
    directory_path: str
    project_mode: bool = False
class ModeConfig(BaseModel):
    mode: str
    
@app.get("/saves") 
def get_available_saves():
    if SAVE_DIR.exists():
        return [item.name for item in SAVE_DIR.iterdir() if item.is_file()]
        
    return []

@app.post("/saves/initialize")
def initialize_save_session(config: InitConfig):
    global current_session
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    print("initiating save session")
    if config.action == "L":
        target = SAVE_DIR / config.value
        if target.is_file():
            manager = AsyncAgentManager(history_file=target)
            current_session["manager"] = manager
            return {
                "status": f"Loaded save file: {config.value}",
                "messages": manager.messages  # <-- Returns historical chat logs to React
            }
        return {"status": "File not found", "messages": []}
        
    elif config.action == "N":
        file_path = SAVE_DIR / f"save{config.value}.json"
        if not file_path.is_file():
            with open(file_path, "w") as f:
                json.dump([{"role": "system", "content": get_system_instruction(ALLOW_PARALLEL_TOOLS,CURRENT_MODE)}], f)
        
        manager = AsyncAgentManager(history_file=file_path)
        current_session["manager"] = manager
        return {
            "status": f"Created session: {file_path.name}",
            "messages": manager.messages  
        }

@app.post("/saves/summarize")
async def summarize_save_file(config: SaveConfig):
    """Asynchronous conversion of your original option 'S' summary task."""
    target_path = SAVE_DIR / config.name
    if not target_path.is_file():
        return {"error": "Target save file matrix not found"}
        
    temp_manager = AsyncAgentManager(history_file=target_path)
    messages = temp_manager.load_history()
    messages.append({"role": "system", "content": "summarize the previous chat"})
    
    response = await client.chat.completions.create(
        model="qwen2.5-coder:14b",
        messages=messages
    )
    
    summary_payload = [{"role": "assistant", "content": response.choices[0].message.content}]
    summary_path = SAVE_DIR / f"{config.name[:-5]}_summary.json"
    
    with open(summary_path, "w") as f:
        json.dump(summary_payload, f, indent=4)
        
    return {"status": f"Summary file stored completely at {summary_path.name}"}

@app.post("/mode/switch")

def switchmode(config: ModeConfig):
    global CURRENT_MODE
    CURRENT_MODE = config.mode
    manager = current_session.get("manager")
    
    
    if manager and hasattr(manager, "messages") and manager.messages is not None:
        if CURRENT_MODE == "webmode":
            manager.messages.append({
                "role": "system", 
                "content": modes.WEBMODEPROMPT
            })
        return {"status": f"Mode switched to {CURRENT_MODE} for active session."}
    # fallback
    return {"status": f"Default mode set to {CURRENT_MODE} for upcoming sessions."}

    

@app.post("/saves/directory")
def update_session_directory(config: DirectoryConfig):
    global current_session
    manager = current_session.get("manager")
    
    if not manager:
        return {"status": "Error: No active session loaded."}
    
    # swap the workspace path for the AI tools script /// to change !!
    filereadtools.TARGET_DIRECTORY = config.directory_path
    filemanager.TARGET_DIRECTORY = config.directory_path

    if config.project_mode:
        project_instruction = (
            f"PROJECT MODE ACTIVE: You are operating directly within a main project directory workspace:"
            "When analyzing, modifying, or creating files, you MUST use the indexing tools 'search_directory_index' to navigate "
            "the project structure and search/manipulation tools (you are equipped with grep, read_file, edit_file, write_to_file tools) to accurately query and edit "
            "files within the main project directory."
            "example: if the indexed directory shows project/file.txt you only need to pass in file.txt in the function parameters e.g read_file(file.txt)"
        )
        if CURRENT_MODE !='webmode':
            project_instruction += search_available_tools('index,file,edit,scratchpad')
        

        manager.messages.append({"role": "system", "content": project_instruction})
    

    
    if hasattr(manager, "project_directory"):
        manager.project_mode = config.project_mode
        manager.project_directory = config.directory_path
    filereadtools.search_directory_index(query=None) 
    
    return {"status": f"Workspace directory updated to: {config.directory_path} "}


@app.websocket("/ws/agent")
async def agent_websocket_endpoint(websocket: WebSocket):
    #future wait var would force the waiting code to sit in a loop constantly rechecking
    #pending_edits: dict[str, asyncio.Future] = {}
    await websocket.accept()
    manager: AsyncAgentManager = current_session["manager"]
    
    async def token_callback(token: str):
        await websocket.send_json({"type": "token", "data": token})
        
    async def status_callback(status: str):
        await websocket.send_json({"type": "status", "data": status})
        
    async def tool_callback(execution_frame: dict):
        await websocket.send_json({"type": "tool_result", "data": execution_frame})
    '''async def edit_confirmation(edit_content: dict) -> bool:
        edit_id = edit_content["edit_id"]
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        pending_edits[edit_id] = future
        await websocket.send_json({"type": "edit_confirmation", "data": edit_content})
        try:
            return await asyncio.wait_for(future, timeout=300)
        except asyncio.TimeoutError:
            return False
        finally:
            pending_edits.pop(edit_id, None)'''

    try:
        while True:
            raw_data = await websocket.receive_text()
            payload = json.loads(raw_data)
            user_input = payload.get("message", "")
            


            #Wrap the turn routine execution block inside the lock
            async with generation_lock:  # Forces single-file sequential execution 
                await manager.run_turn(
                    user_input=user_input,
                    on_token=token_callback,
                    on_status=status_callback,
                    on_tool=tool_callback,
                    #on_edit=edit_confirmation
                )
            
            await websocket.send_json({"type": "turn_complete"})
            
    except WebSocketDisconnect:
        print("[Socket Log]: React runtime interface connection severed cleanly.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)