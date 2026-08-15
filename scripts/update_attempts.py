#!/usr/bin/env python3
import sys
import json
import pathlib
import re
import hashlib
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure(encoding='utf-8')

READ_TOOLS = {
    "view_file",
    "grep_search",
    "list_dir",
    "read_resource",
    "list_resources",
    "read_url_content",
    "search_web"
}

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

    return pathlib.Path.cwd() / "docs" / "task_queues" / "active.json"

def normalize_error_message(err_text: str) -> tuple[str, str, str]:
    if not err_text:
        return ("", "", "")
    text = str(err_text).strip()

    # 1. Extract error type if present
    err_type_match = re.search(r'([A-Za-z0-9_]+Error|[A-Za-z0-9_]+Exception):', text)
    err_type = err_type_match.group(1) if err_type_match else "Error"

    # 2. Mask file paths (Windows & Unix)
    masked = re.sub(r'[A-Za-z]:\\[^ \r\n\t:,]+', '<PATH>', text)
    masked = re.sub(r'/[a-zA-Z0-9_\.\-]+(/[a-zA-Z0-9_\.\-]+)+', '<PATH>', masked)

    # 3. Mask timestamps, dates, and times
    masked = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?', '<TIMESTAMP>', masked)
    masked = re.sub(r'\b\d{2}:\d{2}:\d{2}\b', '<TIME>', masked)

    # 4. Mask hex addresses / memory pointers
    masked = re.sub(r'0x[0-9a-fA-F]+', '<HEX_ADDR>', masked)

    # 5. Mask UUIDs
    masked = re.sub(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', '<UUID>', masked)

    # 6. Mask line and column numbers
    masked = re.sub(r'(?:line|lines|Line|Lines)\s+\d+', 'line <NUM>', masked)
    masked = re.sub(r':\d+:\d+', ':<NUM>:<NUM>', masked)
    masked = re.sub(r':\d+', ':<NUM>', masked)

    # 7. Normalize whitespace
    norm = re.sub(r'\s+', ' ', masked).strip()
    signature = hashlib.sha256(norm.encode('utf-8')).hexdigest()

    return (err_type, norm, signature)

def main():
    try:
        raw = sys.stdin.read()
        debug_log = pathlib.Path(r"C:\Users\rikui\Documents\VSCode\agy-hooks\docs\task_queues\debug_hook_stdin.jsonl")
        try:
            with open(debug_log, "a", encoding="utf-8") as f:
                f.write(raw.strip() + "\n")
        except Exception:
            pass

        if not raw.strip():
            print(json.dumps({}))
            return

        data = json.loads(raw)
        active_file = find_active_file(data)

        if not active_file.exists():
            print(json.dumps({}))
            return

        content = active_file.read_text(encoding="utf-8").strip()
        if not content:
            print(json.dumps({}))
            return

        task = json.loads(content)
        current_status = str(task.get("status", "ready")).lower()

        # If already terminal completed, do not override
        if current_status in ("completed",):
            print(json.dumps({}))
            return

        now_str = datetime.now().astimezone().isoformat()
        tool_call = data.get("toolCall") or data.get("tool_call") or {}
        tool_name = str(tool_call.get("name") or data.get("tool_name") or data.get("name") or "").strip()
        args = tool_call.get("args") or data.get("args") or {}

        cmd_val = str(args.get("CommandLine") or args.get("commandLine") or args.get("Instruction") or args.get("TargetFile") or args.get("AbsolutePath") or args.get("Query") or args.get("query") or "").strip()
        if not cmd_val:
            cmd_val = str(args)

        reason_val = str(args.get("Description") or args.get("Instruction") or args.get("description") or args.get("instruction") or data.get("toolSummary") or data.get("toolAction") or "").strip()
        if not reason_val:
            reason_val = f"Execute {tool_name}"

        target_file = str(args.get("TargetFile") or args.get("target_file") or args.get("file") or "").strip()
        target_content = str(args.get("TargetContent") or args.get("target_content") or "").strip()
        replacement_content = str(args.get("ReplacementContent") or args.get("replacement_content") or args.get("CodeContent") or args.get("code_content") or "").strip()

        err_val = data.get("error") or data.get("errorDetail") or data.get("errorMessage") or data.get("reason")
        exit_code = data.get("exitCode") or data.get("exit_code")

        # Extract potential output/result texts from toolResult or data fields
        tool_result = data.get("toolResult") or data.get("tool_result") or {}
        output_text = ""
        if isinstance(tool_result, dict):
            output_text = str(tool_result.get("output") or tool_result.get("content") or tool_result.get("error") or "")
            if exit_code is None:
                exit_code = tool_result.get("exitCode") or tool_result.get("exit_code")
        elif isinstance(tool_result, str):
            output_text = tool_result

        raw_output = str(data.get("output") or data.get("content") or data.get("response") or "")
        combined_text = f"{output_text}\n{raw_output}".strip()

        # Fallback to reading transcriptPath if available and output is empty
        transcript_path_str = data.get("transcriptPath") or data.get("transcript_path")
        if transcript_path_str and pathlib.Path(transcript_path_str).exists():
            try:
                t_lines = pathlib.Path(transcript_path_str).read_text(encoding="utf-8", errors="ignore").strip().splitlines()
                for line in reversed(t_lines[-10:]):
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    t_type = entry.get("type", "")
                    if t_type in ("RUN_COMMAND", "CODE_ACTION", "ERROR_MESSAGE", "TOOL_RESULT") or entry.get("exit_code") is not None:
                        t_content = str(entry.get("content") or "")
                        t_exit_code = entry.get("exit_code")
                        if t_exit_code is not None and exit_code is None:
                            exit_code = t_exit_code
                        if t_content and not combined_text:
                            combined_text = t_content
                        break
            except Exception:
                pass

        # Check for non-zero exit code embedded in text
        if exit_code is None:
            m = re.search(r'exited with code\s+([1-9]\d*)', combined_text, re.IGNORECASE)
            if m:
                exit_code = int(m.group(1))

        # Check for error indicator, traceback, or non-zero exit code
        if not err_val:
            if "Traceback (most recent call last):" in combined_text or "Error:" in combined_text or "Exception:" in combined_text:
                err_val = combined_text
            elif exit_code is not None and int(exit_code) != 0:
                err_val = f"Command failed with exit code {exit_code}\n{combined_text}".strip()
            elif re.search(r'\b(FAILED|FATAL ERROR)\b', combined_text, re.IGNORECASE):
                err_val = combined_text

        has_error = bool(err_val or (exit_code is not None and int(exit_code) != 0))

        # Check if the failure is actually an intentional interception from a PreToolUse guard hook
        guard_indicators = [
            "[plan mode guard]",
            "[diagnosis-gate]",
            "[diagnosis-required]",
            "[loop-limit-blocked]",
            "[loop-limit-exceeded]",
            "[diff oscillation detected]",
            "denied with reason:",
            "tool call denied"
        ]
        is_guard_denial = any(ind in combined_text.lower() for ind in guard_indicators)
        if is_guard_denial:
            has_error = False
            err_val = None

        err_type, norm_err, err_sig = ("", "", "")
        if has_error:
            err_type, norm_err, err_sig = normalize_error_message(str(err_val))

        max_attempts = task.get("max_attempts", 3)
        last_sig = task.get("last_error_signature")
        consecutive_errors = task.get("consecutive_error_count", 0)

        if has_error:
            task["attempts"] = task.get("attempts", 0) + 1
            if last_sig == err_sig and err_sig != "":
                consecutive_errors += 1
                task["consecutive_error_count"] = consecutive_errors
            else:
                task["last_error_signature"] = err_sig
                task["consecutive_error_count"] = 1

            if task["attempts"] >= max_attempts:
                task["status"] = "failed"
            else:
                task["status"] = "diagnosis"
        elif not is_guard_denial:
            # Success
            if tool_name in READ_TOOLS:
                # Read tool executed -> opens diagnosis gate back to ready
                if current_status == "diagnosis":
                    task["status"] = "ready"
            elif tool_name == "run_command":
                # Command succeeded -> resets error signature and counter
                task["last_error_signature"] = None
                task["consecutive_error_count"] = 0
                if current_status == "diagnosis":
                    task["status"] = "ready"
            else:
                # File edit / modification succeeded -> opens diagnosis gate back to ready
                if current_status == "diagnosis":
                    task["status"] = "ready"

        task["last_executed_at"] = now_str
        if "description" not in task or not task["description"]:
            task["description"] = "Execute task and govern attempt limits"

        history = task.get("history", [])
        history_item = {
            "step": len(history) + 1,
            "timestamp": now_str,
            "tool_name": tool_name,
            "command": cmd_val,
            "reason": reason_val,
            "has_error": has_error,
            "error_message": str(err_val) if err_val else None,
            "error_signature": err_sig if err_sig else None,
            "target_file": target_file if target_file else None,
            "target_content": target_content if target_content else None,
            "replacement_content": replacement_content if replacement_content else None
        }
        history.append(history_item)
        task["history"] = history

        active_file.write_text(json.dumps(task, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({}))
    except Exception:
        print(json.dumps({}))

if __name__ == "__main__":
    main()
