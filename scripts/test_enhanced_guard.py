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

    # 1. 3 Attempts Hard Limit & Escalation
    def test_three_attempts_hard_limit(self):
        for i in range(1, 4):
            self.run_post_tool({
                "toolCall": {"name": "run_command", "args": {"CommandLine": "pytest"}},
                "error": f"AssertionError: test failure {i}",
                "exitCode": 1
            })

        active = self.read_active()
        self.assertEqual(active["attempts"], 3)
        self.assertEqual(active["status"], "failed")

        # Verify PreToolUse denies further actions on 3rd attempt exceeded
        res_pre = self.run_pre_tool({
            "toolCall": {"name": "run_command", "args": {"CommandLine": "pytest"}}
        })
        self.assertEqual(res_pre["decision"], "deny")
        self.assertIn("somebody-help-me", res_pre["reason"])

    # 2. Mutating tools allowed during diagnosis under attempt limit
    def test_mutating_tools_allowed_under_limit(self):
        # Trigger an initial failure
        self.run_post_tool({
            "toolCall": {"name": "run_command", "args": {"CommandLine": "npm test"}},
            "error": "Error: Test suite failed",
            "exitCode": 1
        })

        active = self.read_active()
        self.assertEqual(active["status"], "diagnosis")
        self.assertEqual(active["attempts"], 1)

        # File editing tool is allowed to attempt a fix without being blocked
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
        self.assertEqual(res_mutate["decision"], "allow")

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

        # Succeed next command
        self.run_post_tool({
            "toolCall": {"name": "run_command", "args": {"CommandLine": "pytest"}},
            "error": None,
            "exitCode": 0
        })
        active = self.read_active()
        self.assertEqual(active["consecutive_error_count"], 0)
        self.assertIsNone(active["last_error_signature"])
        self.assertEqual(active["status"], "ready")

    # 6. Antigravity toolResult output text format error detection
    def test_antigravity_output_payload_error_detection(self):
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
        self.assertEqual(active["attempts"], 1)

    # 7. Guard interceptions (e.g. Plan Mode Guard, Diagnosis Gate) are excluded from failure attempts
    def test_guard_policy_interceptions_ignored(self):
        # Emulate a tool call blocked by Plan Mode Guard
        self.run_post_tool({
            "toolCall": {"name": "write_to_file", "args": {"TargetFile": "src/sample.py", "CodeContent": "x = 100"}},
            "toolResult": {
                "error": "model output error: invalid tool call error (invalid_args) tool call denied with reason: [Plan Mode Guard] Currently in Plan mode."
            }
        })
        active = self.read_active()
        self.assertEqual(active["attempts"], 0)
        self.assertEqual(active["consecutive_error_count"], 0)
        self.assertIsNone(active["last_error_signature"])
        self.assertEqual(active["status"], "ready")

if __name__ == "__main__":
    unittest.main()
