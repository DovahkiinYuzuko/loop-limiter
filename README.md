# plugin-loop-limiter

タスク状態管理JSONと連携し、ステートマシン制御、エラーシグネチャ高速失敗（Fast-Fail）、診断フェーズゲート、差分振動検知、および/somebody-help-me自動誘導を提供するエージェントガードプラグイン / AI Agent guard plugin providing state machine control, error signature fast-fail, diagnosis phase gating, diff oscillation detection, and automatic escalation to /somebody-help-me via task state JSON.

[![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square&logo=opensourceinitiative&logoColor=white)](LICENSE.MIT)

[日本語](#日本語) | [English](#english)

---

## 日本語

`plugin-loop-limiter` は、Google Antigravity 等のAIエージェント開発環境における無限ループや無駄な試行の反復を防止するための強化型ガードプラグインです。タスク状態管理ファイル（`docs/task_queues/active.json`）と連携し、以下の制御を自動的に適用します。

### 主な機能

1. **有限状態マシン（FSM）制御**:
   - `ready`: 初期状態または待機状態。
   - `in_progress`: ツール実行進行中。
   - `diagnosis`: コマンドまたはツール実行エラー時に移行。読み取り専用フェーズとして直接のファイル書き換えを禁止。
   - `blocked_loop`: 同一エラー連続発生（2回）、差分振動、または試行上限到達時に移行。ツール実行を遮断。
   - `failed`: 試行上限（デフォルト3回）到達による失敗。
   - `completed`: タスク完了。

2. **エラーシグネチャ高速失敗（Fast-Fail）**:
   - ツールエラー出力を正規化（ファイルパス、タイムスタンプ、行番号、メモリポインタ、UUIDをマスク）してSHA-256シグネチャを生成。
   - 同一のエラーシグネチャが2回連続で発生した場合、直ちに `blocked_loop` に移行してループを中断し、`/somebody-help-me` へのエスカレーションを案内します。

3. **診断フェーズゲート（Read-Only Phase Gating）**:
   - エラー発生直後の `diagnosis` 状態では、ファイル変更ツール（`replace_file_content`, `write_to_file`, `multi_replace_file_content`, `delete_file`）の実行を遮断（`decision: "deny"`）。
   - 調査ツール（`view_file`, `grep_search`, `list_dir`）を実行することで原因分析が行われたとみなし、ゲートを解除して `ready` 状態へ復帰します。

4. **差分振動およびジッター検知（Diff Oscillation & Jitter Detection）**:
   - 直近の編集履歴と比較し、直前の変更をそのまま元に戻す反転編集（ピンポン現象）や、失敗した変更と90%以上類似する微細な書き換えの繰り返しを検知して遮断します。

5. **フォールバックとエスカレーション**:
   - 実行停止時にはユーザーへの相談と `/somebody-help-me` スキルを用いた原因整理・支援要請を自動通知します。

### ディレクトリ構成

- `plugin.json`: プラグインのマニフェスト。
- `hooks.json`: エージェントフック定義（`UserMessage`, `PreToolUse`, `PostToolUse`, `Stop`）。
- `scripts/`:
  - `init_or_reset_queue.py`: ユーザーメッセージ受信時のキュー初期化・リセット。
  - `check_pre_tool.py`: ツール実行前の診断ゲート・試行上限・差分振動検証。
  - `update_attempts.py`: ツール実行後のシグネチャ生成・試行回数更新・ゲート解除。
  - `check_stop_condition.py`: 停止時の状態判定およびエスカレーション通知。
  - `manage_task.py`: タスクキュー管理CLI（作成・ステータス確認・完了・リセット）。
  - `create_queue.py`: 新規タスクキュー作成スクリプト。
  - `test_enhanced_guard.py`: 強化型ガードの網羅的単体テスト。
- `skills/loop-limiter/SKILL.md`: スキル仕様ドキュメント。

### 導入方法

#### Agent Plugins CLI (汎用標準・推奨)
```bash
npx plugins add DovahkiinYuzuko/loop-limiter
```

#### Antigravity CLI (ローカル配置からのインストール)
```bash
git clone https://github.com/DovahkiinYuzuko/loop-limiter.git
agy plugin install ./loop-limiter
```

### LICENSE

[MIT](./LICENSE.MIT)

---

## English

`plugin-loop-limiter` is an enhanced guard plugin designed for AI agent platforms such as Google Antigravity. It prevents runaway execution loops, unguided trial-and-error edits, and oscillations by synchronizing with `docs/task_queues/active.json`.

### Key Features

1. **Finite State Machine (FSM) Governance**:
   - `ready`: Ready for task execution.
   - `in_progress`: Actively running tools.
   - `diagnosis`: Triggered upon failure. Direct file mutations are blocked until read tools are executed.
   - `blocked_loop`: Fast-fail triggered by 2 consecutive identical errors, diff oscillation, or max attempts reached.
   - `failed`: Hard limit exceeded.
   - `completed`: Successfully resolved.

2. **Error Signature Fast-Fail**:
   - Normalizes error output (masks paths, timestamps, line numbers, memory pointers, UUIDs) and creates a SHA-256 hash.
   - 2 consecutive identical signatures immediately switch state to `blocked_loop` and guide escalation to `/somebody-help-me`.

3. **Read-Only Phase Gating (Diagnosis Gate)**:
   - File mutation tools (`replace_file_content`, `write_to_file`, `multi_replace_file_content`, `delete_file`) are blocked during `diagnosis`.
   - Executing inspection tools (`view_file`, `grep_search`, `list_dir`) unlocks the gate back to `ready`.

4. **Diff Oscillation & Jitter Detection**:
   - Identifies and blocks ping-pong edit reversals ($A \to B \to A$) and repetitive micro-edits ($> 90\%$ similarity on failed attempts).

5. **Fallback & Escalation**:
   - Automatically recommends `/somebody-help-me` upon halting.

### Directory Structure

- `plugin.json`: Plugin manifest.
- `hooks.json`: Agent hook definitions (`UserMessage`, `PreToolUse`, `PostToolUse`, `Stop`).
- `scripts/`:
  - `init_or_reset_queue.py`: Queue initialization and reset on user messages.
  - `check_pre_tool.py`: PreToolUse validation (diagnosis gating, limit enforcement, diff oscillation).
  - `update_attempts.py`: PostToolUse updates (error normalization, signature hashing, gate unlocking).
  - `check_stop_condition.py`: Stop hook evaluating terminal states.
  - `manage_task.py`: CLI management tool.
  - `create_queue.py`: Queue initializer script.
  - `test_enhanced_guard.py`: Full unit test suite.
- `skills/loop-limiter/SKILL.md`: Skill specification.

### Installation

#### Agent Plugins CLI (Universal Standard / Recommended)
```bash
npx plugins add DovahkiinYuzuko/loop-limiter
```

#### Antigravity CLI (Install from Local Directory)
```bash
git clone https://github.com/DovahkiinYuzuko/loop-limiter.git
agy plugin install ./loop-limiter
```

### LICENSE

[MIT](./LICENSE.MIT)
