#!/usr/bin/env python3
import sys
import json
import pathlib
import argparse
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure(encoding='utf-8')

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

    target = cwd / "docs" / "task_queues" / "active.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    return target

def main():
    parser = argparse.ArgumentParser(description="Manage Loop-Limiter task queues.")
    subparsers = parser.add_subparsers(dest="action")

    # create
    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("--id", "-i", default="auto_initialized_task", help="Task identifier")
    create_parser.add_argument("--objective", "-o", default="Execute task", help="Task objective/description")
    create_parser.add_argument("--max-attempts", "-m", type=int, default=3, help="Max attempts allowed")

    # complete
    subparsers.add_parser("complete")

    # fail
    subparsers.add_parser("fail")

    # reset
    subparsers.add_parser("reset")

    # status
    subparsers.add_parser("status")

    args, unknown = parser.parse_known_args()
    active_file = find_active_file()

    if args.action == "create":
        data = {
            "id": args.id,
            "task_id": args.id,
            "description": args.objective,
            "status": "ready",
            "attempts": 0,
            "max_attempts": args.max_attempts,
            "last_error_signature": None,
            "consecutive_error_count": 0,
            "fallback_plan": "/somebody-help-me",
            "history": []
        }
        active_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Task created: {args.id} (Status: ready, Max Attempts: {args.max_attempts})")
        return

    if not active_file.exists():
        print(json.dumps({"error": "active.json not found"}))
        return

    data = json.loads(active_file.read_text(encoding="utf-8"))

    if args.action == "complete":
        data["status"] = "completed"
        data["last_executed_at"] = datetime.now().astimezone().isoformat()
        active_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print("Task marked as completed.")
    elif args.action == "fail":
        data["status"] = "failed"
        data["last_executed_at"] = datetime.now().astimezone().isoformat()
        active_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print("Task marked as failed.")
    elif args.action == "reset":
        data["status"] = "ready"
        data["attempts"] = 0
        data["last_error_signature"] = None
        data["consecutive_error_count"] = 0
        data["last_executed_at"] = datetime.now().astimezone().isoformat()
        active_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print("Task state reset to ready.")
    else:
        print(f"Task Status: {data.get('status')}, Attempts: {data.get('attempts')}/{data.get('max_attempts')}, Consecutive Errors: {data.get('consecutive_error_count', 0)}")

if __name__ == "__main__":
    main()
