# server.py
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from Mine import AsyncAgentManager, SAVE_DIR, client, ALLOW_PARALLEL_TOOLS
import tools
import filetools.filereadtools as filereadtools


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















app = FastAPI()
generation_lock = asyncio.Lock()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global dictionary or single active instanced target pointer 
current_session = {"manager": AsyncAgentManager()}


#data schemas using Pydantic FastAPI uses these to validate the data incoming from the user. 
class SaveConfig(BaseModel):
    name: str

class InitConfig(BaseModel):
    action: str  # "L" (Load), "N" (Create New)
    value: str   # filename or save number string

class DirectoryConfig(BaseModel):
    directory_path: str

@app.get("/saves") 
def get_available_saves():
    if SAVE_DIR.exists():
        return [item.name for item in SAVE_DIR.iterdir() if item.is_file()]
    return []

@app.post("/saves/initialize")
def initialize_save_session(config: InitConfig):
    global current_session
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    
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
                json.dump([{"role": "system", "content": get_system_instruction(ALLOW_PARALLEL_TOOLS)}], f)
        
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

@app.post("/saves/directory")
def update_session_directory(config: DirectoryConfig):
    global current_session
    manager = current_session.get("manager")
    
    if not manager:
        return {"status": "Error: No active session loaded."}
    
    # Hot-swap the workspace path for the AI tools script
    filereadtools.TARGET_DIRECTORY = config.directory_path
    
    # Save it to the active session object for persistence
    if hasattr(manager, "project_directory"):
        manager.project_directory = config.directory_path
    filereadtools.search_directory_index(query=None) #indexes the current directory
    return {"status": f"Workspace directory updated to: {config.directory_path}"}


@app.websocket("/ws/agent")
async def agent_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    manager: AsyncAgentManager = current_session["manager"]
    
    try:
        while True:
            raw_data = await websocket.receive_text()
            payload = json.loads(raw_data)
            user_input = payload.get("message", "")
            
            async def token_callback(token: str):
                await websocket.send_json({"type": "token", "data": token})
                
            async def status_callback(status: str):
                await websocket.send_json({"type": "status", "data": status})
                
            async def tool_callback(execution_frame: dict):
                await websocket.send_json({"type": "tool_result", "data": execution_frame})

            #Wrap the turn routine execution block inside the lock
            async with generation_lock:  # ◄ Forces single-file sequential execution 
                await manager.run_turn(
                    user_input=user_input,
                    on_token=token_callback,
                    on_status=status_callback,
                    on_tool=tool_callback
                )
            
            await websocket.send_json({"type": "turn_complete"})
            
    except WebSocketDisconnect:
        print("[Socket Log]: React runtime interface connection severed cleanly.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)