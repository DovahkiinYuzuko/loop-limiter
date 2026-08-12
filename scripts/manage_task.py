import sys, json, pathlib

def find_active_file() -> pathlib.Path:
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
    active_file = find_active_file()
    if not active_file.exists():
        print("active.json not found.")
        return

    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    data = json.loads(active_file.read_text(encoding="utf-8"))

    if action == "complete":
        data["status"] = "COMPLETED"
        active_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print("Task marked as COMPLETED.")
    elif action == "fail":
        data["status"] = "FAILED"
        active_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print("Task marked as FAILED.")
    else:
        print(f"Task Status: {data.get('status')}, Attempts: {data.get('attempts')}")

if __name__ == "__main__":
    main()
