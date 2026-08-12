import sys, json, pathlib

ACTIVE_FILE = pathlib.Path("docs/task_queues/active.json")

def main():
    try:
        raw_input = sys.stdin.read().lower()

        # 1. Always allow create_queue, active.json, task_queues, and check_pre_tool operations
        if any(kw in raw_input for kw in ["create_queue", "active.json", "task_queues", "check_pre_tool"]):
            print(json.dumps({"decision": "allow"}))
            return

        # 2. If active.json does not exist, require running create_queue.py
        if not ACTIVE_FILE.exists():
            print(json.dumps({
                "decision": "deny",
                "reason": "[loop-limiter-missing-task-queue] Active task queue file 'docs/task_queues/active.json' does not exist. Please run 'python plugins/plugin-loop-limiter/scripts/create_queue.py' to initialize the task queue first."
            }))
            return

        # 3. Check attempt limits
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

