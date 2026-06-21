from products import get_product_info, list_all_products, funny_function
from fileManager import write_to_file
from mainToolsScript import *
from scratchpad import *

tools_map = {
    "finish_conversation": finish_conversation,
    "write_to_file": write_to_file,
    "read_scratchpad": read_scratchpad,
    "update_scratchpad": update_scratchpad
    
}
'''override scratchpad'''

tools = [
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
            "name": "write_to_file",
            "description": "this function writes the text to any file format, make sure to get the format correct with the file_name, this is different from the scratchpad because it stores the text files of any format permenantly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_name": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["file_name", "content"]
            }
        }
    },
    # Scratchpad Tool Schema Definitions For Model Awareness
    {
        "type": "function",
        "function": {
            "name": "read_scratchpad",
            "description": "Read your long-term planning thoughts, notes, and task progress trackers from the dynamic text file.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_scratchpad",
            "description": "Overwrite the scratchpad text file with completely updated planning notes, workflows, or sub-task checkmarks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The entire new structured text content block to write into scratchpad."
                    }
                },
                "required": ["content"]
            }
        }
    }
]

