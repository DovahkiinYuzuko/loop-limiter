import sys, json, pathlib

ACTIVE_FILE = pathlib.Path("docs/task_queues/active.json")

def main():
    try:
        data = json.load(sys.stdin)
        tool_call = data.get("toolCall", {})
        args = tool_call.get("args", {})
        target_file = args.get("TargetFile") or args.get("AbsolutePath") or ""

        # If the tool is acting directly on the task queue file itself, allow it to be created/updated
        if target_file and pathlib.Path(target_file).resolve() == ACTIVE_FILE.resolve():
            print(json.dumps({"decision": "allow"}))
            return

        if not ACTIVE_FILE.exists():
            print(json.dumps({
                "decision": "deny",
                "reason": "[loop-limiter-missing-task-queue] Active task queue file 'docs/task_queues/active.json' does not exist. You must create and initialize 'docs/task_queues/active.json' first to manage task loops."
            }))
            return

        data_json = json.loads(ACTIVE_FILE.read_text(encoding="utf-8"))
        if data_json.get("status") == "failed" or data_json.get("attempts", 0) >= data_json.get("max_attempts", 3):
            print(json.dumps({
                "decision": "deny",
                "reason": f"[loop-limit-exceeded] Task '{data_json.get('id')}' reached max attempts ({data_json.get('max_attempts')}). Execute fallback plan: {data_json.get('fallback_plan')}"
            }))
            return

        print(json.dumps({"decision": "allow"}))
    except Exception:
        print(json.dumps({"decision": "allow"}))

if __name__ == "__main__":
    main()

