"""Thin wrapper around an OpenAI-compatible endpoint (Alibaba Cloud Model Studio)."""
from openai import OpenAI

from app.config import Settings


class LLMClient:
    def __init__(self, settings: Settings):
        if not settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY is not set. Put your Model Studio API key in the env file.")
        self.settings = settings
        self.client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key, timeout=60)
        # Qwen3-based models on Model Studio accept enable_thinking. A support bot
        # does not need long reasoning, and turning it off keeps latency low.
        aliyun = "aliyuncs.com" in settings.llm_base_url
        self._extra_body = {"enable_thinking": False} if aliyun else None

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """Return the assistant message as a plain dict, plus token usage."""
        kwargs = {"model": self.settings.llm_model, "messages": messages, "temperature": 0.3}
        if tools:
            kwargs["tools"] = tools
        if self._extra_body:
            kwargs["extra_body"] = self._extra_body
        resp = self.client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        out = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            out["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"},
                }
                for tc in msg.tool_calls
            ]
        usage = resp.usage
        out["_usage"] = {
            "prompt_tokens": getattr(usage, "prompt_tokens", 0),
            "completion_tokens": getattr(usage, "completion_tokens", 0),
        }
        return out

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), 10):  # Model Studio accepts up to 10 inputs per call
            resp = self.client.embeddings.create(model=self.settings.embed_model, input=texts[i : i + 10])
            vectors.extend(d.embedding for d in resp.data)
        return vectors
