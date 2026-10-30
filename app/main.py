"""Web service: chat API + health check + a small chat page.

Run locally:   uvicorn app.main:app --reload
"""
import json
import logging
import sys
import time
import uuid
from collections import OrderedDict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.agent import Agent
from app.config import load_settings
from app.knowledge import build_retriever
from app.llm import LLMClient
from app.tools import ToolBox

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
log = logging.getLogger("agent")

settings = load_settings()
llm = LLMClient(settings)
retriever = build_retriever(settings, llm)
agent = Agent(llm, ToolBox(settings.data_dir, retriever), settings.max_tool_rounds, settings.auto_retrieve)

# Conversation memory lives in this process. With 2+ servers behind a load balancer
# this must move to a shared store (e.g. Redis / Tair), otherwise sessions break.
SESSIONS: "OrderedDict[str, list[dict]]" = OrderedDict()
MAX_SESSIONS = 1000

app = FastAPI(title="TokoKita Customer Service Agent")
STATIC = Path(__file__).parent / "static"


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    session_id: str | None = None


@app.get("/")
def shop():
    """Storefront with the chat widget."""
    return FileResponse(STATIC / "shop.html")


@app.get("/chat")
def chat_page():
    """Full-page chat, handy for testing the agent on its own."""
    return FileResponse(STATIC / "index.html")


@app.get("/healthz")
def healthz():
    return {"status": "ok", "model": settings.llm_model, "retriever": settings.retriever,
            "auto_retrieve": settings.auto_retrieve, "kb_chunks": len(retriever.chunks)}


@app.post("/api/chat")
def chat(body: ChatIn):
    sid = body.session_id or uuid.uuid4().hex
    history = SESSIONS.get(sid, [])
    started = time.time()
    try:
        result = agent.chat(history, body.message)
    except Exception as e:  # model API down, quota used up, network error...
        log.error(json.dumps({"event": "chat_error", "session": sid, "error": repr(e)[:300]}))
        raise HTTPException(status_code=502, detail="The AI service is temporarily unavailable.")
    history = (history + [{"role": "user", "content": body.message},
                          {"role": "assistant", "content": result.reply}])[-settings.max_history_turns * 2:]
    SESSIONS[sid] = history
    SESSIONS.move_to_end(sid)
    while len(SESSIONS) > MAX_SESSIONS:
        SESSIONS.popitem(last=False)
    log.info(json.dumps({"event": "chat", "session": sid, "latency_ms": int((time.time() - started) * 1000),
                         "tools": [c["name"] for c in result.tool_calls], **result.usage}))
    return {"session_id": sid, "reply": result.reply, "tools_used": [c["name"] for c in result.tool_calls]}
