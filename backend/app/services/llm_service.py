import json
from groq import Groq, AsyncGroq
from app.core.config import settings

MODEL = "openai/gpt-oss-120b"


def chat(message: list[dict]) -> str:
    client = Groq(api_key=settings.groq_api_key)
    response = client.chat.completions.create(model=MODEL, messages=message)
    return response.choices[0].message.content


async def chat_stream(messages: list[dict]):
    client = AsyncGroq(api_key=settings.groq_api_key)
    stream = await client.chat.completions.create(model=MODEL, messages=messages, stream=True)
    async for chunk in stream:
        yield chunk.choices[0].delta.content or ""


def extract_tickers(question: str) -> list[str]:
    prompt = (
        "Extract stock ticker symbols from this investment research query.\n"
        "Rules:\n"
        "- Resolve company names to primary US exchange tickers (Apple→AAPL, Nvidia→NVDA, Alphabet→GOOGL)\n"
        "- Return ONLY valid JSON: {\"tickers\": [\"AAPL\"]}\n"
        "- If no companies are mentioned return {\"tickers\": []}\n"
        "- Maximum 5 tickers\n\n"
        f"Query: {question}\n\n"
        "JSON only, no explanation:"
    )
    try:
        import re
        raw = chat([{"role": "user", "content": prompt}])
        match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return [t.upper().strip() for t in data.get("tickers", []) if isinstance(t, str)][:5]
    except Exception:
        pass
    return []


def parse_tool_call(content: str) -> dict | None:
    try:
        data = json.loads(content.strip())
        if "tool" in data and "input" in data:
            return data
    except (json.JSONDecodeError, KeyError):
        pass
    return None
