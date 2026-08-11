import sys, json, pathlib

ACTIVE_FILE = pathlib.Path("docs/task_queues/active.json")

def main():
    try:
        data = json.load(sys.stdin)
        # Check if the tool execution resulted in an error
        if data.get("error"):
            if ACTIVE_FILE.exists():
                task = json.loads(ACTIVE_FILE.read_text(encoding="utf-8"))
                if task.get("status") == "in_progress":
                    task["attempts"] += 1
                    if task["attempts"] >= task["max_attempts"]:
                        task["status"] = "failed"
                    ACTIVE_FILE.write_text(json.dumps(task, indent=2), encoding="utf-8")
        print(json.dumps({}))
    except Exception:
        print(json.dumps({}))

if __name__ == "__main__":
    main()
