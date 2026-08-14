#!/usr/bin/env python3
import subprocess
import json
import sys
import pathlib

def main():
    scripts_dir = pathlib.Path(__file__).resolve().parent
    manage_script = str(scripts_dir / "manage_task.py")
    check_pre = str(scripts_dir / "check_pre_tool.py")
    update_att = str(scripts_dir / "update_attempts.py")
    check_stop = str(scripts_dir / "check_stop_condition.py")

    # 1. Create Task via CLI
    subprocess.run([sys.executable, manage_script, "create", "--id", "test-task-1", "--objective", "Fix build issue"], check=True)
    print("=== Step 1: Task Created ===")

    # 2. Check PreToolUse (Attempt 0 -> Allowed)
    proc = subprocess.run([sys.executable, check_pre], input="{}", text=True, capture_output=True)
    print("PreToolUse Output (Attempt 0):", proc.stdout.strip())

    # 3. Simulate 2 identical Errors (Triggers Fast-Fail)
    for i in range(2):
        subprocess.run([sys.executable, update_att], input=json.dumps({"error": "build failed", "exitCode": 1}), text=True, capture_output=True)
    print("=== Step 2: 2 Identical Errors Simulated (Fast-Fail) ===")

    # 4. Check PreToolUse (Fast-Fail -> Denied)
    proc_pre = subprocess.run([sys.executable, check_pre], input="{}", text=True, capture_output=True)
    print("PreToolUse Output (Blocked Loop):", proc_pre.stdout.strip())

    # 5. Check Stop Hook (Blocked Loop -> Continue with Fallback Injection)
    proc_stop = subprocess.run([sys.executable, check_stop], input="{}", text=True, capture_output=True)
    print("Stop Hook Output (Blocked Loop):", proc_stop.stdout.strip())

    # Clean up
    subprocess.run([sys.executable, manage_script, "reset"], check=True)

if __name__ == "__main__":
    main()
