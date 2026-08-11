import subprocess, json, sys, pathlib

def main():
    manage_script = "plugins/plugin-loop-limiter/scripts/manage_task.py"
    check_pre = "plugins/plugin-loop-limiter/scripts/check_pre_tool.py"
    update_att = "plugins/plugin-loop-limiter/scripts/update_attempts.py"
    check_stop = "plugins/plugin-loop-limiter/scripts/check_stop_condition.py"

    # 1. Create Task via CLI
    subprocess.run([sys.executable, manage_script, "create", "--id", "test-task-1", "--objective", "Fix build issue"], check=True)
    print("=== Step 1: Task Created ===")

    # 2. Check PreToolUse (Attempt 0 -> Allowed)
    proc = subprocess.run([sys.executable, check_pre], input="{}", text=True, capture_output=True)
    print("PreToolUse Output (Attempt 0):", proc.stdout.strip())

    # 3. Simulate 3 Errors
    for i in range(3):
        subprocess.run([sys.executable, update_att], input=json.dumps({"error": "build failed"}), text=True, capture_output=True)
    print("=== Step 2: 3 Errors Simulated ===")

    # 4. Check PreToolUse (Attempt 3 -> Denied)
    proc_pre = subprocess.run([sys.executable, check_pre], input="{}", text=True, capture_output=True)
    print("PreToolUse Output (Attempt 3):", proc_pre.stdout.strip())

    # 5. Check Stop Hook (Attempt 3 -> Continue with Fallback Injection)
    proc_stop = subprocess.run([sys.executable, check_stop], input="{}", text=True, capture_output=True)
    print("Stop Hook Output (Attempt 3):", proc_stop.stdout.strip())

if __name__ == "__main__":
    main()
