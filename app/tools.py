"""Tools the agent can call. Each tool = a JSON schema (for the model) + a Python function."""
import json
import threading
import time
from pathlib import Path

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Search the TokoKita store policy knowledge base (shipping, returns, payment, warranty, store info). "
            "Call this before answering any policy question.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query, in English or Bahasa Indonesia"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Look up an order. Requires the order ID (format TK-12345) and the last 4 digits of the "
            "phone number used for the order. Ask the customer for both if missing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "phone_last4": {"type": "string", "description": "Last 4 digits of the customer's phone number"},
                },
                "required": ["order_id", "phone_last4"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_handoff_ticket",
            "description": "Hand the conversation to a human agent. Use when the customer asks for a human, requests a "
            "refund or return, reports a damaged or wrong item, or the issue cannot be solved.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": ["return_refund", "damaged_item", "complaint", "other"]},
                    "summary": {"type": "string", "description": "One-sentence summary of the issue, in English"},
                    "order_id": {"type": "string", "description": "Order ID if known"},
                },
                "required": ["category", "summary"],
            },
        },
    },
]


class ToolBox:
    def __init__(self, data_dir: Path, retriever):
        self.retriever = retriever
        self.orders = {o["order_id"]: o for o in json.loads((data_dir / "orders.json").read_text(encoding="utf-8"))}
        self.ticket_path = data_dir / "tickets.jsonl"
        self._lock = threading.Lock()

    def search_knowledge(self, query: str) -> dict:
        hits = self.retriever.search(query, k=3)
        if not hits:
            return {"found": False, "results": []}
        return {"found": True, "results": [{"source": c.source, "text": c.text} for c, _ in hits]}

    def get_order_status(self, order_id: str, phone_last4: str) -> dict:
        # Return the same error for "unknown order" and "wrong phone", so nobody can probe which orders exist.
        # TODO(S4): look up the order and verify the phone number before revealing anything
        raise NotImplementedError("TODO(S4): look up the order and verify the phone number before revealing anything")

    def create_handoff_ticket(self, category: str, summary: str, order_id: str = "") -> dict:
        ticket_id = f"HD-{int(time.time() * 1000) % 10_000_000:07d}"
        record = {"ticket_id": ticket_id, "category": category, "summary": summary, "order_id": order_id,
                  "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        with self._lock, self.ticket_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return {"ok": True, "ticket_id": ticket_id, "message": "A human agent will reply within 1 business day."}

    def run(self, name: str, arguments: str) -> dict:
        """Execute a tool call from the model. Bad input becomes an error the model can read."""
        fn = {"search_knowledge": self.search_knowledge,
              "get_order_status": self.get_order_status,
              "create_handoff_ticket": self.create_handoff_ticket}.get(name)
        if fn is None:
            return {"ok": False, "error": f"Unknown tool: {name}"}
        try:
            args = json.loads(arguments or "{}")
            return fn(**args)
        except (json.JSONDecodeError, TypeError) as e:
            return {"ok": False, "error": f"Invalid arguments: {e}"}
