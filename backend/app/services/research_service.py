import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.llm_service import chat, chat_stream, parse_tool_call
from app.tools.registry import list_tools, call_tool
import app.tools.financial_tools  # noqa: F401
import app.tools.document_tools   # noqa: F401
import hashlib
from app.core.cache import cache_get, cache_set

MAX_TURNS = 3


def _system_prompt() -> str:
    tools = list_tools()
    tool_lines = "\n".join(
        f"- {t['name']}: {t['description']}"
        for t in tools
    )
    return f"""You are a financial research assistant with access to these tools:

{tool_lines}

To call a tool, respond with ONLY valid JSON, nothing else:
{{"tool": "get_company_metrics", "input": {{"ticker": "AAPL"}}}}

To finish, respond with ONLY:
{{"done": true}}

IMPORTANT: You MUST use one of these exact tool names: get_company_metrics, search_filings, embed_filings, search_document_chunks
Do NOT invent tool names. Do NOT add any text outside the JSON."""


async def run_research(
    db: AsyncSession,
    question: str,
    ticker: str,
    context: list[dict] | None = None,
    workflow_run_id: int | None = None,
) -> dict:
    cache_key = f"research:{ticker.upper()}:{hashlib.md5(question.encode()).hexdigest()}"
    if not context:
        cached_result = await cache_get(cache_key)
        if cached_result is not None:
            return cached_result

    context_text = ""
    if context:
        prior = context[-3:]
        lines = []
        for c in prior:
            lines.append(f"Q: {c['question']}\nA: {c['report'][:600]}")
        context_text = "Prior research in this session:\n" + "\n\n".join(lines) + "\n\n"

    messages = [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": f"{context_text}Research question: {question}\nTicker: {ticker}"},
    ]

    observations = []

    for turn in range(MAX_TURNS):
        response = chat(messages)
        messages.append({"role": "assistant", "content": response})

        tool_call = parse_tool_call(response)

        if tool_call is None or tool_call.get("done"):
            break

        tool_name = tool_call["tool"]
        tool_input = tool_call["input"]

        try:
            result = await call_tool(tool_name, tool_input, db)
        except Exception as e:
            await db.rollback()
            result = {"error": str(e)}

        observation = f"Tool: {tool_name}\nInput: {json.dumps(tool_input)}\nResult: {json.dumps(result)}"
        observations.append(observation)
        messages.append({"role": "user", "content": f"Tool result:\n{observation}\n\nContinue researching or respond with {{\"done\": true}} if you have enough information."})

    observations_text = "\n\n".join(observations) if observations else "No data was retrieved."
    synthesis_messages = [
        {
            "role": "user",
            "content": (
                f"You are a financial analyst. Here is research data collected about {ticker}:\n\n"
                f"{observations_text}\n\n"
                f"Write a comprehensive analysis in plain English paragraphs answering: {question}\n\n"
                f"Do not use JSON. Do not call any tools. Write your analysis directly."
            ),
        }
    ]

    report_chunks: list[str] = []
    if workflow_run_id:
        from app.core.redis_client import publish_workflow_event
        async for token in chat_stream(synthesis_messages):
            report_chunks.append(token)
            await publish_workflow_event(workflow_run_id, {"type": "chunk", "content": token})
    else:
        report_chunks.append(chat(synthesis_messages))

    report = "".join(report_chunks)

    result = {"question": question, "ticker": ticker, "turns": turn + 1, "observations": observations, "report": report}
    if not context:
        await cache_set(cache_key, result, ttl=21600)
    return result
