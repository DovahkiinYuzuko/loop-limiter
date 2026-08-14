#!/usr/bin/env python3
import unittest
import subprocess
import json
import sys
import tempfile
import pathlib
import shutil

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent

class TestEnhancedLoopGuard(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="loop_limiter_test_")
        self.ws_root = pathlib.Path(self.temp_dir)
        self.queue_dir = self.ws_root / "docs" / "task_queues"
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.active_file = self.queue_dir / "active.json"

        # Initialize standard active.json
        self.initial_data = {
            "task_id": "test-task",
            "id": "test-task",
            "description": "Test Task for Loop Limiter",
            "status": "ready",
            "attempts": 0,
            "max_attempts": 3,
            "last_error_signature": None,
            "consecutive_error_count": 0,
            "fallback_plan": "/somebody-help-me",
            "history": []
        }
        self.write_active(self.initial_data)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def write_active(self, data: dict):
        self.active_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def read_active(self) -> dict:
        return json.loads(self.active_file.read_text(encoding="utf-8"))

    def run_pre_tool(self, payload: dict) -> dict:
        payload["workspacePaths"] = [str(self.ws_root)]
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "check_pre_tool.py")],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=str(self.ws_root)
        )
        self.assertEqual(proc.returncode, 0, f"check_pre_tool crashed: {proc.stderr}")
        return json.loads(proc.stdout.strip())

    def run_post_tool(self, payload: dict) -> dict:
        payload["workspacePaths"] = [str(self.ws_root)]
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "update_attempts.py")],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=str(self.ws_root)
        )
        self.assertEqual(proc.returncode, 0, f"update_attempts crashed: {proc.stderr}")
        return json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}

    def run_stop_hook(self, payload: dict = None) -> dict:
        if payload is None:
            payload = {}
        payload["workspacePaths"] = [str(self.ws_root)]
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "check_stop_condition.py")],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=str(self.ws_root)
        )
        self.assertEqual(proc.returncode, 0, f"check_stop_condition crashed: {proc.stderr}")
        return json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}

    # 1. Fast-Fail on Two Consecutive Identical Errors
    def test_fast_fail_consecutive_identical_errors(self):
        # Error 1 with specific path, line number, memory addr
        err1 = "ValueError: Invalid syntax in C:\\Users\\test\\file.py line 45 at 0x7fff5fbff"
        self.run_post_tool({
            "toolCall": {"name": "run_command", "args": {"CommandLine": "pytest"}},
            "error": err1,
            "exitCode": 1
        })

        active = self.read_active()
        self.assertEqual(active["status"], "diagnosis")
        self.assertEqual(active["consecutive_error_count"], 1)
        self.assertIsNotNone(active["last_error_signature"])

        # Error 2 with different path, line number, memory addr (but same normalized signature)
        err2 = "ValueError: Invalid syntax in /opt/project/other.py line 99 at 0xdeadbeef"
        self.run_post_tool({
            "toolCall": {"name": "run_command", "args": {"CommandLine": "pytest"}},
            "error": err2,
            "exitCode": 1
        })

        active = self.read_active()
        self.assertEqual(active["status"], "blocked_loop")
        self.assertEqual(active["consecutive_error_count"], 2)

        # Verify PreToolUse denies further actions
        res_pre = self.run_pre_tool({
            "toolCall": {"name": "run_command", "args": {"CommandLine": "pytest"}}
        })
        self.assertEqual(res_pre["decision"], "deny")
        self.assertIn("somebody-help-me", res_pre["reason"])

        # Verify Stop Hook notifies escalation
        res_stop = self.run_stop_hook()
        self.assertEqual(res_stop.get("decision"), "continue")
        self.assertIn("somebody-help-me", res_stop.get("reason", ""))

    # 2. Read-Only Phase Gating (Diagnosis Gate)
    def test_diagnosis_gate_and_unlock(self):
        # Trigger an initial failure to enter diagnosis mode
        self.run_post_tool({
            "toolCall": {"name": "run_command", "args": {"CommandLine": "npm test"}},
            "error": "Error: Test suite failed",
            "exitCode": 1
        })

        active = self.read_active()
        self.assertEqual(active["status"], "diagnosis")

        # Mutating file tool MUST be denied
        res_mutate = self.run_pre_tool({
            "toolCall": {
                "name": "replace_file_content",
                "args": {
                    "TargetFile": str(self.ws_root / "src" / "index.js"),
                    "TargetContent": "const x = 1;",
                    "ReplacementContent": "const x = 2;"
                }
            }
        })
        self.assertEqual(res_mutate["decision"], "deny")
        self.assertIn("diagnosis-gate", res_mutate["reason"])

        # Read tool MUST be allowed
        res_read = self.run_pre_tool({
            "toolCall": {
                "name": "view_file",
                "args": {"AbsolutePath": str(self.ws_root / "src" / "index.js")}
            }
        })
        self.assertEqual(res_read["decision"], "allow")

        # Execute read tool post hook -> unlocks diagnosis gate
        self.run_post_tool({
            "toolCall": {
                "name": "view_file",
                "args": {"AbsolutePath": str(self.ws_root / "src" / "index.js")}
            },
            "error": None
        })

        active_after_read = self.read_active()
        self.assertEqual(active_after_read["status"], "ready")

        # Now mutating tool MUST be allowed
        res_mutate_after = self.run_pre_tool({
            "toolCall": {
                "name": "replace_file_content",
                "args": {
                    "TargetFile": str(self.ws_root / "src" / "index.js"),
                    "TargetContent": "const x = 1;",
                    "ReplacementContent": "const x = 2;"
                }
            }
        })
        self.assertEqual(res_mutate_after["decision"], "allow")

    # 3. Diff Reversal & Oscillation Detection
    def test_diff_reversal_and_oscillation_detection(self):
        target_file = str(self.ws_root / "src" / "app.py")

        # Step 1: Perform Edit A -> B
        self.run_post_tool({
            "toolCall": {
                "name": "replace_file_content",
                "args": {
                    "TargetFile": target_file,
                    "TargetContent": "def add(a, b): return a",
                    "ReplacementContent": "def add(a, b): return a + b"
                }
            },
            "error": None
        })

        # Step 2: Attempt exact reversal B -> A
        res_reversal = self.run_pre_tool({
            "toolCall": {
                "name": "replace_file_content",
                "args": {
                    "TargetFile": target_file,
                    "TargetContent": "def add(a, b): return a + b",
                    "ReplacementContent": "def add(a, b): return a"
                }
            }
        })
        self.assertEqual(res_reversal["decision"], "deny")
        self.assertIn("Diff Oscillation Detected", res_reversal["reason"])
        self.assertIn("exactly reverses", res_reversal["reason"])

        # Step 3: Test Jitter / High-Similarity on Failed Edit
        failed_snippet = "def calculate_total(items):\n    sum_val = 0\n    for x in items:\n        sum_val += x\n    return sum_val"
        self.run_post_tool({
            "toolCall": {
                "name": "write_to_file",
                "args": {
                    "TargetFile": target_file,
                    "CodeContent": failed_snippet
                }
            },
            "error": "SyntaxError: unexpected indent",
            "exitCode": 1
        })

        # Unlock diagnosis by reading file
        self.run_post_tool({
            "toolCall": {"name": "view_file", "args": {"AbsolutePath": target_file}},
            "error": None
        })

        # Attempt almost identical edit (> 90% similarity) on the failed edit
        near_identical_snippet = "def calculate_total(items):\n    sum_val = 0\n    for x in items:\n        sum_val += x\n    return sum_val "
        res_jitter = self.run_pre_tool({
            "toolCall": {
                "name": "write_to_file",
                "args": {
                    "TargetFile": target_file,
                    "CodeContent": near_identical_snippet
                }
            }
        })
        self.assertEqual(res_jitter["decision"], "deny")
        self.assertIn("Diff Oscillation Detected", res_jitter["reason"])
        self.assertIn("similar", res_jitter["reason"])

    # 4. Multi-step Normal Workflow without False Positives
    def test_multi_step_normal_workflow(self):
        # Step 1: view file
        pre1 = self.run_pre_tool({"toolCall": {"name": "view_file", "args": {"AbsolutePath": "main.py"}}})
        self.assertEqual(pre1["decision"], "allow")
        self.run_post_tool({"toolCall": {"name": "view_file", "args": {"AbsolutePath": "main.py"}}, "error": None})

        # Step 2: replace content
        pre2 = self.run_pre_tool({
            "toolCall": {
                "name": "replace_file_content",
                "args": {
                    "TargetFile": "main.py",
                    "TargetContent": "OLD_CODE_1",
                    "ReplacementContent": "NEW_CODE_1"
                }
            }
        })
        self.assertEqual(pre2["decision"], "allow")
        self.run_post_tool({
            "toolCall": {
                "name": "replace_file_content",
                "args": {
                    "TargetFile": "main.py",
                    "TargetContent": "OLD_CODE_1",
                    "ReplacementContent": "NEW_CODE_1"
                }
            },
            "error": None
        })

        # Step 3: run command
        pre3 = self.run_pre_tool({"toolCall": {"name": "run_command", "args": {"CommandLine": "python main.py"}}})
        self.assertEqual(pre3["decision"], "allow")
        self.run_post_tool({"toolCall": {"name": "run_command", "args": {"CommandLine": "python main.py"}}, "error": None})

        active = self.read_active()
        self.assertEqual(active["status"], "ready")
        self.assertEqual(active["attempts"], 0)
        self.assertEqual(len(active["history"]), 3)

    # 5. Success resets error signature and consecutive count
    def test_success_resets_error_state(self):
        # Fail once
        self.run_post_tool({
            "toolCall": {"name": "run_command", "args": {"CommandLine": "pytest"}},
            "error": "AssertionError: 1 != 2",
            "exitCode": 1
        })
        active = self.read_active()
        self.assertEqual(active["consecutive_error_count"], 1)
        self.assertIsNotNone(active["last_error_signature"])

        # Succeed next
        self.run_post_tool({
            "toolCall": {"name": "run_command", "args": {"CommandLine": "pytest"}},
            "error": None,
            "exitCode": 0
        })
        active = self.read_active()
        self.assertEqual(active["consecutive_error_count"], 0)
        self.assertIsNone(active["last_error_signature"])
    # 6. Antigravity toolResult output text format error detection
    def test_antigravity_output_payload_error_detection(self):
        # Simulate Antigravity PostToolUse payload with exit code inside output string
        self.run_post_tool({
            "toolCall": {"name": "run_command", "args": {"CommandLine": "python fail.py"}},
            "toolResult": {
                "output": "The command exited with code 1.\nTraceback (most recent call last):\n  File 'fail.py', line 1\nRuntimeError: deliberate-fail-1"
            }
        })
        active = self.read_active()
        self.assertEqual(active["status"], "diagnosis")
        self.assertEqual(active["consecutive_error_count"], 1)
        self.assertIsNotNone(active["last_error_signature"])
    # 7. File edit between same error does not clear signature, so Fast-Fail triggers on 2nd command failure
    def test_file_edit_does_not_clear_error_signature_so_fast_fail_triggers(self):
        # Step 1: 1st command failure
        self.run_post_tool({
            "toolCall": {"name": "run_command", "args": {"CommandLine": "python fail.py"}},
            "error": "RuntimeError: deliberate-fail-1",
            "exitCode": 1
        })
        active1 = self.read_active()
        self.assertEqual(active1["status"], "diagnosis")
        self.assertEqual(active1["consecutive_error_count"], 1)
        sig1 = active1["last_error_signature"]

        # Step 2: Read tool to investigate
        self.run_post_tool({
            "toolCall": {"name": "view_file", "args": {"AbsolutePath": "fail.py"}},
            "error": None
        })
        active2 = self.read_active()
        self.assertEqual(active2["status"], "ready")
        self.assertEqual(active2["last_error_signature"], sig1)

        # Step 3: File edit (modifying file to attempt fix)
        self.run_post_tool({
            "toolCall": {
                "name": "write_to_file",
                "args": {
                    "TargetFile": "fail.py",
                    "CodeContent": "print('patched code')"
                }
            },
            "error": None
        })
        active3 = self.read_active()
        self.assertEqual(active3["status"], "ready")
        # Ensure signature is NOT cleared by file edit
        self.assertEqual(active3["last_error_signature"], sig1)

        # Step 4: 2nd command failure with SAME error (patch didn't solve root cause)
        self.run_post_tool({
            "toolCall": {"name": "run_command", "args": {"CommandLine": "python fail.py"}},
            "error": "RuntimeError: deliberate-fail-1",
            "exitCode": 1
        })
        active4 = self.read_active()
        # Fast-Fail MUST trigger and block the loop!
        self.assertEqual(active4["status"], "blocked_loop")
        self.assertEqual(active4["consecutive_error_count"], 2)

        # Step 5: Next tool is blocked with loop-limit-blocked
        pre_blocked = self.run_pre_tool({
            "toolCall": {"name": "write_to_file", "args": {"TargetFile": "fail.py", "CodeContent": "retry"}}
        })
        self.assertEqual(pre_blocked["decision"], "deny")
        self.assertIn("loop-limit-blocked", pre_blocked["reason"])
        self.assertIn("/somebody-help-me", pre_blocked["reason"])

if __name__ == "__main__":
    unittest.main()
