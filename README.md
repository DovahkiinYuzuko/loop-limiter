# plugin-loop-limiter

AIエージェントの無駄な試行錯誤や無限ループを防止し、状態管理と高速失敗（Fast-Fail）を提供するガードプラグイン / Guard plugin preventing runaway loops and unguided trial-and-error edits in AI agents via state machine and fast-fail mechanisms.

[![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square&logo=opensourceinitiative&logoColor=white)](LICENSE.MIT)

[日本語](#日本語) | [English](#english)

---

## 日本語

`plugin-loop-limiter` は、Google Antigravity 等のAIエージェント開発環境において、前提の不一致による無限ループや無駄なファイル編集・コマンド実行の反復を防止するための強化型ガードプラグインです。タスク状態管理ファイル（`docs/task_queues/active.json`）と連携し、有限状態マシン（FSM）に基づく自動制御を提供します。

### 主な機能

1. **有限状態マシン（FSM）による制御**:
   - `ready`: 初期状態または実行待機状態。
   - `in_progress`: ツール実行進行中。
   - `diagnosis`: コマンドまたはツール実行エラー時に移行。読み取り専用フェーズとして直接のファイル書き換えを禁止。
   - `blocked_loop`: 同一エラー連続発生（2回）、差分振動、または試行上限到達時に移行。ツール実行を遮断。
   - `failed`: 試行上限（デフォルト3回）到達による失敗。
   - `completed`: タスク正常完了。

2. **エラーシグネチャによる高速失敗（Fast-Fail）**:
   - ツールエラー出力を正規化（ファイルパス、タイムスタンプ、行番号、メモリポインタ、UUIDをマスク）してSHA-256シグネチャを生成します。
   - 同一のエラーシグネチャが2回連続で発生した場合、直ちに `blocked_loop` に移行してループを中断し、`/somebody-help-me` へのエスカレーションを案内します。

3. **診断フェーズゲート（Read-Only Phase Gating）**:
   - エラー発生直後の `diagnosis` 状態では、ファイル変更ツール（`replace_file_content`, `write_to_file`, `multi_replace_file_content`, `delete_file`）の実行を遮断します。
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
  - `test_enhanced_guard.py`: 強化型ガードの網羅的単体テスト（全7ケース検証済み）。
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

### 使用方法

タスクを開始する際は、以下のコマンドでタスクチケットを初期化します。

```bash
python scripts/manage_task.py create --id <task-id> --objective "<task description>"
```

タスク完了時は、ステータスを `completed` に更新します。

```bash
python scripts/manage_task.py complete
```

### LICENSE

[MIT](./LICENSE.MIT)

---

## English

`plugin-loop-limiter` is an enhanced guard plugin designed for AI agent platforms such as Google Antigravity. It prevents runaway execution loops, unguided trial-and-error edits, and oscillations by synchronizing with task state management files (`docs/task_queues/active.json`) under Finite State Machine (FSM) governance.

### Key Features

1. **Finite State Machine (FSM) Governance**:
   - `ready`: Initial or awaiting execution state.
   - `in_progress`: Actively executing tools.
   - `diagnosis`: Entered upon failure. Direct file mutations are blocked until read tools are executed.
   - `blocked_loop`: Fast-fail triggered by 2 consecutive identical errors, diff oscillation, or max attempts reached.
   - `failed`: Hard limit exceeded (default: 3 attempts).
   - `completed`: Successfully resolved.

2. **Error Signature Fast-Fail**:
   - Normalizes error output (masks file paths, timestamps, line numbers, memory pointers, UUIDs) and creates a SHA-256 signature hash.
   - 2 consecutive identical signatures immediately switch state to `blocked_loop` and guide escalation to `/somebody-help-me`.

3. **Read-Only Phase Gating (Diagnosis Gate)**:
   - File mutation tools (`replace_file_content`, `write_to_file`, `multi_replace_file_content`, `delete_file`) are blocked during `diagnosis`.
   - Executing inspection tools (`view_file`, `grep_search`, `list_dir`) unlocks the gate back to `ready`.

4. **Diff Oscillation & Jitter Detection**:
   - Identifies and blocks ping-pong edit reversals ($A \to B \to A$) and repetitive micro-edits ($> 90\%$ similarity on failed attempts).

5. **Fallback & Escalation**:
   - Automatically recommends `/somebody-help-me` upon halting for root cause diagnosis and user consultation.

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
  - `test_enhanced_guard.py`: Full unit test suite (7 cases verified).
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

### Usage

When starting a task, initialize a task ticket with the following command:

```bash
python scripts/manage_task.py create --id <task-id> --objective "<task description>"
```

Upon task resolution, mark the status as completed:

```bash
python scripts/manage_task.py complete
```

### LICENSE

[MIT](./LICENSE.MIT)
