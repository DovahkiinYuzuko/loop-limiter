import sys, json, argparse, pathlib

TASKS_DIR = pathlib.Path("docs/task_queues")
ACTIVE_FILE = TASKS_DIR / "active.json"

def get_active_task():
    if ACTIVE_FILE.exists():
        return json.loads(ACTIVE_FILE.read_text(encoding="utf-8"))
    return None

def save_active_task(data):
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="Task Queue CLI Manager")
    subparsers = parser.add_subparsers(dest="action")

    # Create task
    create_p = subparsers.add_parser("create")
    create_p.add_argument("--id", required=True)
    create_p.add_argument("--objective", required=True)
    create_p.add_argument("--fallback", default="/somebody-help-me")

    # Increment / Complete
    subparsers.add_parser("increment")
    subparsers.add_parser("complete")

    args = parser.parse_args()

    if args.action == "create":
        task_data = {
            "id": args.id,
            "objective": args.objective,
            "attempts": 0,
            "max_attempts": 3,
            "status": "in_progress",
            "fallback_plan": args.fallback
        }
        save_active_task(task_data)
        print(f"Task '{args.id}' created and activated.")

    elif args.action == "increment":
        task = get_active_task()
        if task and task["status"] == "in_progress":
            task["attempts"] += 1
            if task["attempts"] >= task["max_attempts"]:
                task["status"] = "failed"
            save_active_task(task)
            print(f"Task '{task['id']}' attempts incremented to {task['attempts']}.")

    elif args.action == "complete":
        task = get_active_task()
        if task:
            task["status"] = "success"
            save_active_task(task)
            print(f"Task '{task['id']}' marked as success.")

if __name__ == "__main__":
    main()
