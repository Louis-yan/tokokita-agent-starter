"""Runtime settings, read from environment variables.

Never hard-code API keys. On the cloud server they live in an env file
(see deploy/agent.env.example) that is readable only by root.
"""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Model Studio (Singapore). The Base URL is workspace-specific:
#   https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
# Replace YOUR_WORKSPACE_ID with the ID from the Model Studio console, or set LLM_BASE_URL.
DEFAULT_BASE_URL = "https://YOUR_WORKSPACE_ID.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"


@dataclass(frozen=True)
class Settings:
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    embed_model: str
    retriever: str  # "embedding" or "keyword"
    data_dir: Path
    max_tool_rounds: int
    max_history_turns: int
    auto_retrieve: bool


def load_settings() -> Settings:
    return Settings(
        llm_base_url=os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        llm_api_key=os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY", ""),
        llm_model=os.getenv("LLM_MODEL", "qwen-plus"),
        embed_model=os.getenv("EMBED_MODEL", "text-embedding-v3"),
        retriever=os.getenv("RETRIEVER", "embedding"),
        data_dir=Path(os.getenv("DATA_DIR", str(ROOT / "data"))),
        max_tool_rounds=int(os.getenv("MAX_TOOL_ROUNDS", "4")),
        max_history_turns=int(os.getenv("MAX_HISTORY_TURNS", "8")),
        auto_retrieve=os.getenv("AUTO_RETRIEVE", "true").lower() == "true",
    )
