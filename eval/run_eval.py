"""Run the acceptance test set against a running agent.

    python eval/run_eval.py --url http://<your-server-ip>     # deployed agent (acceptance)
    python eval/run_eval.py --url http://127.0.0.1:8000       # local server
    python eval/run_eval.py --local                           # in-process, no server needed

Writes eval/report-<timestamp>.json and prints the pass rate. Target: >= 80%.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import httpx
import yaml

HERE = Path(__file__).parent


def check(case: dict, reply: str, tools: list[str]) -> list[str]:
    problems = []
    low = reply.lower()
    for t in case.get("expect_tools", []):
        if t not in tools:
            problems.append(f"expected tool {t} not called")
    for t in case.get("forbid_tools", []):
        if t in tools:
            problems.append(f"tool {t} should not be called")
    for group in case.get("must_include", []):
        if not any(p.lower() in low for p in group):
            problems.append(f"reply missing one of {group}")
    for p in case.get("must_not_include", []):
        if p.lower() in low:
            problems.append(f"reply must not contain {p!r}")
    return problems


def run_case(client: httpx.Client, url: str, case: dict) -> dict:
    session_id, tools, reply = None, [], ""
    for turn in case["turns"]:
        r = client.post(f"{url}/api/chat", json={"message": turn, "session_id": session_id})
        r.raise_for_status()
        data = r.json()
        session_id, reply = data["session_id"], data["reply"]
        tools += data["tools_used"]
    problems = check(case, reply, tools)
    return {"id": case["id"], "passed": not problems, "problems": problems, "tools": tools, "reply": reply}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="Base URL of the agent, e.g. http://1.2.3.4")
    ap.add_argument("--local", action="store_true", help="Load app.main in this process instead of calling a URL")
    ap.add_argument("--cases", default=str(HERE / "cases.yaml"))
    args = ap.parse_args()
    if not args.url and not args.local:
        ap.error("give --url or --local")
    cases = yaml.safe_load(Path(args.cases).read_text(encoding="utf-8"))
    results = []
    if args.local:
        sys.path.insert(0, str(HERE.parent))
        from fastapi.testclient import TestClient
        from app.main import app
        url, client_ctx = "", TestClient(app)
    else:
        url, client_ctx = args.url.rstrip("/"), httpx.Client(timeout=90)
    with client_ctx as client:
        health = client.get(f"{url}/healthz").json()
        print(f"healthz: {health}")
        for case in cases:
            try:
                res = run_case(client, url, case)
            except httpx.HTTPError as e:
                res = {"id": case["id"], "passed": False, "problems": [f"HTTP error: {e}"], "tools": [], "reply": ""}
            results.append(res)
            mark = "PASS" if res["passed"] else "FAIL"
            print(f"[{mark}] {res['id']:<11} tools={res['tools']}  {'; '.join(res['problems'])}")
    passed = sum(r["passed"] for r in results)
    rate = passed / len(results)
    report = {"url": url or "local", "healthz": health, "passed": passed, "total": len(results), "pass_rate": round(rate, 3),
              "results": results}
    out = HERE / f"report-{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nPass rate: {passed}/{len(results)} = {rate:.0%}   report: {out}")
    return 0 if rate >= 0.8 else 1


if __name__ == "__main__":
    sys.exit(main())
