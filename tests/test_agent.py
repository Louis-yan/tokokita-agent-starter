"""Offline tests: no API key needed. A scripted fake model drives the agent loop."""
import json
from pathlib import Path

import pytest

from app.agent import FALLBACK_REPLY, Agent, clean_reply, detect_language
from app.knowledge import KeywordRetriever, cosine, load_chunks
from app.tools import ToolBox

DATA = Path(__file__).resolve().parent.parent / "data"


class FakeLLM:
    """Returns pre-scripted assistant messages, one per call, and records what it was sent."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def chat(self, messages, tools=None):
        self.calls.append([dict(m) for m in messages])
        return dict(self.script.pop(0))


def tool_call(name, args, cid="c1"):
    return {"role": "assistant", "content": "",
            "tool_calls": [{"id": cid, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}


@pytest.fixture
def toolbox(tmp_path):
    for f in ["orders.json"]:
        (tmp_path / f).write_text((DATA / f).read_text(encoding="utf-8"), encoding="utf-8")
    return ToolBox(tmp_path, KeywordRetriever(load_chunks(DATA / "knowledge")))


def test_knowledge_base_loads_all_sections():
    chunks = load_chunks(DATA / "knowledge")
    assert len(chunks) >= 18
    assert all(c.source.count("#") == 1 for c in chunks)


def test_keyword_retriever_finds_indonesian_query():
    r = KeywordRetriever(load_chunks(DATA / "knowledge"))
    top = r.search("berapa ongkos kirim, ada gratis ongkir?")[0][0]
    assert top.source == "shipping.md#Shipping fee"


def test_cosine():
    assert cosine([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine([0, 0], [1, 1]) == 0.0


def test_order_lookup_requires_matching_phone(toolbox):
    ok = toolbox.get_order_status("tk-10232", "2222")
    assert ok["ok"] and ok["tracking_no"] == "JT7788990011"
    wrong_phone = toolbox.get_order_status("TK-10232", "9999")
    missing = toolbox.get_order_status("TK-99999", "2222")
    assert wrong_phone == missing == {"ok": False, "error": "Order not found or phone number does not match."}


def test_handoff_ticket_is_written(toolbox, tmp_path):
    res = toolbox.create_handoff_ticket("damaged_item", "Screen cracked on arrival", "TK-10231")
    assert res["ticket_id"].startswith("HD-")
    line = json.loads((tmp_path / "tickets.jsonl").read_text().strip())
    assert line["order_id"] == "TK-10231"


def test_bad_tool_arguments_become_readable_error(toolbox):
    assert toolbox.run("get_order_status", "{not json")["ok"] is False
    assert toolbox.run("get_order_status", json.dumps({"order_id": "TK-10232"}))["ok"] is False
    assert toolbox.run("delete_all_orders", "{}")["error"].startswith("Unknown tool")


def test_agent_runs_tool_then_answers(toolbox):
    llm = FakeLLM([
        tool_call("get_order_status", {"order_id": "TK-10232", "phone_last4": "2222"}),
        {"role": "assistant", "content": "Your order is on the way with J&T, tracking JT7788990011."},
    ])
    res = Agent(llm, toolbox, auto_retrieve=False).chat([], "Where is TK-10232? phone 2222")
    assert "JT7788990011" in res.reply
    assert [c["name"] for c in res.tool_calls] == ["get_order_status"]
    tool_msg = llm.calls[1][-1]  # second model call must see the tool result
    assert tool_msg["role"] == "tool" and "JT7788990011" in tool_msg["content"]


def test_agent_stops_after_too_many_tool_rounds(toolbox):
    llm = FakeLLM([tool_call("search_knowledge", {"query": "x"}, cid=f"c{i}") for i in range(10)])
    res = Agent(llm, toolbox, max_tool_rounds=2, auto_retrieve=False).chat([], "loop forever")
    assert res.reply == FALLBACK_REPLY
    assert len(llm.calls) == 3


def test_history_is_passed_to_model(toolbox):
    llm = FakeLLM([{"role": "assistant", "content": "ok"}])
    history = [{"role": "user", "content": "Cek pesanan TK-10234"}, {"role": "assistant", "content": "Akhiran HP?"}]
    Agent(llm, toolbox).chat(history, "4444")
    sent = llm.calls[0]
    assert sent[0]["role"] == "system" and sent[1]["content"] == "Cek pesanan TK-10234" and sent[-1]["content"] == "4444"


def test_detect_language():
    assert detect_language("How long does delivery take?") == "English"
    assert detect_language("Ongkirnya berapa kalau belanja 200 ribu?") == "Bahasa Indonesia"
    assert detect_language("Bisa bayar COD?") == "Bahasa Indonesia"
    assert detect_language("4444") is None


def test_auto_retrieval_and_language_hint_are_injected(toolbox):
    llm = FakeLLM([{"role": "assistant", "content": "Free shipping from Rp 150.000."}])
    res = Agent(llm, toolbox).chat([], "Is shipping free?")
    sent = llm.calls[0]
    hints = [m["content"] for m in sent if m["role"] == "system"][1:]
    assert any("Reply in English" in h for h in hints)
    assert any("shipping.md#Shipping fee" in h for h in hints)
    assert res.tool_calls[0]["name"] == "search_knowledge"


def test_clean_reply_strips_markdown():
    assert clean_reply("Tiket: **HD-123**.\n## Info\nOk") == "Tiket: HD-123.\nInfo\nOk"


def test_language_hint_comes_after_the_customer_message(toolbox):
    llm = FakeLLM([{"role": "assistant", "content": "6 months."}])
    history = [{"role": "user", "content": "Cek pesanan TK-10236"}, {"role": "assistant", "content": "Akhiran HP?"}]
    Agent(llm, toolbox).chat(history, "How long is the warranty?")
    sent = llm.calls[0]
    assert sent[-2] == {"role": "user", "content": "How long is the warranty?"}
    assert sent[-1]["role"] == "system" and "Reply in English" in sent[-1]["content"]
