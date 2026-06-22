import json
import ollama as ol
from ollama import AsyncClient

MODEL = "qwen2.5:7b"


def chat(message: list[dict]) -> str:
    response = ol.chat(model=MODEL, messages=message)
    return response.message.content


async def chat_stream(messages: list[dict]):
    async for chunk in await AsyncClient().chat(model=MODEL, messages=messages, stream=True):
        yield chunk.message.content


def parse_tool_call(content: str) -> dict | None:
    try:
        data = json.loads(content.strip())
        if "tool" in data and "input" in data:
            return data
    except (json.JSONDecodeError, KeyError):
        pass
    return None
