import sys, json, pathlib
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure(encoding='utf-8')

def find_active_file(data: dict) -> pathlib.Path:
    ws_paths = data.get("workspacePaths", [])
    if ws_paths:
        ws_root = pathlib.Path(ws_paths[0])
        target = ws_root / "docs" / "task_queues" / "active.json"
        if target.exists():
            return target

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

    return pathlib.Path(r"C:\Users\rikui\Documents\VSCode\agy-hooks\docs\task_queues\active.json")

def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            print(json.dumps({}))
            return

        data = json.loads(raw)
        active_file = find_active_file(data)

        if active_file.exists():
            content = active_file.read_text(encoding="utf-8").strip()
            if content:
                task = json.loads(content)
                
                # Check status: update only if task is in_progress
                if task.get("status") == "in_progress":
                    now_str = datetime.now().astimezone().isoformat()
                    tool_call = data.get("toolCall", {})
                    tool_name = str(tool_call.get("name", "")).strip()
                    args = tool_call.get("args", {})
                    summary_arg = str(args.get("CommandLine") or args.get("commandLine") or args.get("Instruction") or args.get("TargetFile") or args.get("AbsolutePath") or args.get("query") or "").strip()
                    has_error = bool(data.get("error"))

                    task["attempts"] = task.get("attempts", 0) + 1
                    task["last_executed_at"] = now_str
                    
                    history = task.get("history", [])
                    history_item = {
                        "step": task["attempts"],
                        "timestamp": now_str,
                        "tool_name": tool_name,
                        "summary": summary_arg[:120],
                        "has_error": has_error
                    }
                    history.append(history_item)
                    task["history"] = history

                    if task["attempts"] >= task.get("max_attempts", 3):
                        task["status"] = "failed"

                    active_file.write_text(json.dumps(task, indent=2, ensure_ascii=False), encoding="utf-8")

        print(json.dumps({}))
    except Exception:
        print(json.dumps({}))

if __name__ == "__main__":
    main()
