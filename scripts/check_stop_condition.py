import sys, json, pathlib

ACTIVE_FILE = pathlib.Path("docs/task_queues/active.json")

def main():
    try:
        if ACTIVE_FILE.exists():
            data = json.loads(ACTIVE_FILE.read_text(encoding="utf-8"))
            if data.get("status") == "failed":
                print(json.dumps({
                    "decision": "continue",
                    "reason": f"[Loop Limit Halting] Task '{data.get('id')}' failed after {data.get('attempts')} attempts. Immediately stop code editing and execute the fallback plan: {data.get('fallback_plan')}"
                }))
                return
        print(json.dumps({}))
    except Exception:
        print(json.dumps({}))

if __name__ == "__main__":
    main()
