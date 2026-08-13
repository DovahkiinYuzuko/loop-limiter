import sys, json, pathlib

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure(encoding='utf-8')

def find_active_file(data: dict) -> pathlib.Path:
    # 1. Use workspacePaths from stdin if present
    ws_paths = data.get("workspacePaths", [])
    ws_root = pathlib.Path(ws_paths[0]) if ws_paths else pathlib.Path.cwd()
    target = ws_root / "docs" / "task_queues" / "active.json"
    if target.exists():
        return target

    # 2. Check current working directory and parents
    cwd = pathlib.Path.cwd()
    curr = cwd
    for _ in range(5):
        t = curr / "docs" / "task_queues" / "active.json"
        if t.exists():
            return t
        if (curr / ".git").exists():
            break
        if curr.parent == curr:
            break
        curr = curr.parent

    # 3. Auto-initialize active.json in target workspace
    try:
        t_dir = ws_root / "docs" / "task_queues"
        t_dir.mkdir(parents=True, exist_ok=True)
        target_file = t_dir / "active.json"
        if not target_file.exists():
            target_file.write_text(json.dumps({
                "task_id": "auto_initialized_task",
                "status": "in_progress",
                "attempts": 0,
                "max_attempts": 3,
                "history": []
            }, indent=2), encoding="utf-8")
        return target_file
    except Exception:
        return target

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
            print(json.dumps({"decision": "allow"}))
            return

        data_json = json.loads(active_file.read_text(encoding="utf-8"))
        if data_json.get("status") == "failed" or data_json.get("attempts", 0) >= data_json.get("max_attempts", 3):
            print(json.dumps({
                "decision": "deny",
                "reason": f"[loop-limit-exceeded] Task reached max attempts ({data_json.get('max_attempts', 3)}). Stopped for User guidance."
            }))
            return

        print(json.dumps({"decision": "allow"}))
    except Exception:
        print(json.dumps({"decision": "allow"}))

if __name__ == "__main__":
    main()
