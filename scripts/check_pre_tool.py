import sys, json, pathlib

def find_active_file(data: dict) -> pathlib.Path:
    # 1. Use workspacePaths from stdin if present
    ws_paths = data.get("workspacePaths", [])
    if ws_paths:
        ws_root = pathlib.Path(ws_paths[0])
        target = ws_root / "docs" / "task_queues" / "active.json"
        if target.exists():
            return target

    # 2. Check current working directory and parents
    cwd = pathlib.Path.cwd()
    curr = cwd
    for _ in range(5):
        target = curr / "docs" / "task_queues" / "active.json"
        if target.exists():
            return target
        if (curr / ".git").exists():
            break
        if curr.parent == curr:
            break
        curr = curr.parent

    # 3. Fallback default
    return pathlib.Path(r"C:\Users\rikui\Documents\VSCode\agy-hooks\docs\task_queues\active.json")

def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            print(json.dumps({"decision": "allow"}))
            return

        data = json.loads(raw)
        raw_input = raw.lower()

        # 1. Always allow queue management keywords
        if any(kw in raw_input for kw in ["create_queue", "active.json", "task_queues", "check_pre_tool"]):
            print(json.dumps({"decision": "allow"}))
            return

        active_file = find_active_file(data)

        if not active_file.exists():
            print(json.dumps({
                "decision": "deny",
                "reason": "[loop-limiter-missing-task-queue] Active task queue file 'docs/task_queues/active.json' does not exist."
            }))
            return

        data_json = json.loads(active_file.read_text(encoding="utf-8"))
        if data_json.get("status") == "failed" or data_json.get("attempts", 0) >= data_json.get("max_attempts", 3):
            print(json.dumps({
                "decision": "deny",
                "reason": f"[loop-limit-exceeded] Task reached max attempts ({data_json.get('max_attempts')})."
            }))
            return

        print(json.dumps({"decision": "allow"}))
    except Exception:
        print(json.dumps({"decision": "allow"}))

if __name__ == "__main__":
    main()
