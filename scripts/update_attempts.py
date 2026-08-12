import sys, json, pathlib

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

        # ツール実行時にエラーが発生した場合のみ、試行回数を加算して3回制限をチェック
        if data.get("error") and active_file.exists():
            content = active_file.read_text(encoding="utf-8").strip()
            if content:
                task = json.loads(content)
                task["attempts"] = task.get("attempts", 0) + 1
                if task["attempts"] >= task.get("max_attempts", 3):
                    task["status"] = "failed"
                active_file.write_text(json.dumps(task, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({}))
    except Exception:
        print(json.dumps({}))

if __name__ == "__main__":
    main()
