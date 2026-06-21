from typing import Callable
from pydantic import BaseModel


_registry: dict[str, dict] = {}

def tool(name: str, description: str, input_schema: type[BaseModel]):
    def decorator(fn: Callable):
        _registry[name] = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "fn": fn,
        }
        return fn
    return decorator

def get_tool(name:str) -> dict | None:
    return _registry.get(name)

def list_tools() -> list[dict]:
    return [
        {
            "name": v["name"],
            "description": v["description"],
            "input_schema": v["input_schema"].model_json_schema(),
        }
        for v in _registry.values()
    ]

async def call_tool(name: str, input_data: dict, db) -> dict:
    entry = _registry.get(name)
    if not entry:
        raise ValueError(f"Unknown tool: {name}")
    validated = entry["input_schema"](**input_data)
    return await entry["fn"](validated, db)
