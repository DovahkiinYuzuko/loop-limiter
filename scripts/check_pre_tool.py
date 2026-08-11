import sys, json, pathlib

ACTIVE_FILE = pathlib.Path("docs/task_queues/active.json")

def main():
    try:
        if ACTIVE_FILE.exists():
            data = json.loads(ACTIVE_FILE.read_text(encoding="utf-8"))
            if data.get("status") == "failed" or data.get("attempts", 0) >= data.get("max_attempts", 3):
                print(json.dumps({
                    "decision": "deny",
                    "reason": f"[loop-limit-exceeded] Task '{data.get('id')}' reached max attempts ({data.get('max_attempts')}). Execute fallback plan: {data.get('fallback_plan')}"
                }))
                return
        print(json.dumps({"decision": "allow"}))
    except Exception:
        print(json.dumps({"decision": "allow"}))

if __name__ == "__main__":
    main()
