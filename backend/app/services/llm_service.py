import json
import ollama as ol

MODEL = "qwen2.5:7b"


def chat(message: list[dict]) -> str:
    response = ol.chat(model=MODEL, messages=message)
    return response.message.content

def parse_tool_call(content: str) -> dict | None:
    try:
        data = json.loads(content.strip())
        if "tool" in data and "input" in data:
            return data
    except (json.JSONDecodeError, KeyError):
        pass
    return None