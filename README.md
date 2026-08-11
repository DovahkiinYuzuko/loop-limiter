# plugin-loop-limiter

タスク状態管理JSONと連携し、3回試行上限ストッパーおよび/somebody-help-me自動起動を制御するプラグイン / Plugin for controlling the 3-attempt hard limit stopper and automatic activation of /somebody-help-me in integration with task state management JSON

![Antigravity](https://img.shields.io/badge/Antigravity-Plugin-blue?style=flat-square&logo=google&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat-square&logo=python&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square&logo=opensourceinitiative&logoColor=white)](LICENSE.MIT)

[日本語](#日本語) | [English](#english)

## 日本語

`plugin-loop-limiter` は、Google Antigravity 等のエージェント開発プラットフォーム向けのフックプラグインです。タスク状態管理ファイル（`docs/task_queues/active.json`）と連携し、試行回数の上限超過チェックおよび自動制御を行います。

### 主な機能

- **PreToolUse チェック**: ツール実行前に試行回数を検証し、上限（デフォルト3回）に達している場合は実行を拒否（deny）します。
- **PostToolUse 更新**: ツール実行でエラーが発生した場合、タスクの試行回数をインクリメントし状態を更新します。
- **Stop 条件判定**: タスクが失敗状態になった場合、停止時にフォールバックプランの実行を促す通知を出力します。

### ディレクトリ構成

- `plugin.json`: プラグインのマニフェストファイルです。
- `hooks.json`: エージェントフック（`PreToolUse`, `PostToolUse`, `Stop`）の定義ファイルです。
- `scripts/`: フックから呼び出される Python スクリプト群です。
  - `check_pre_tool.py`: ツール実行前の判定を行います。
  - `update_attempts.py`: ツール実行後の試行回数更新を行います。
  - `check_stop_condition.py`: 停止時の状態判定を行います。

### LICENSE

[MIT](./LICENSE.MIT)

---

## English

`plugin-loop-limiter` is a hook plugin designed for AI agent development platforms such as Google Antigravity. It integrates with the task state management file (`docs/task_queues/active.json`) to enforce attempt limits and automate fallback execution control.

### Features

- **PreToolUse Verification**: Validates the attempt count prior to tool execution and denies execution if the maximum limit (default: 3) has been reached.
- **PostToolUse State Update**: Increments the attempt count and updates the task status when an error occurs during tool execution.
- **Stop Condition Evaluation**: Triggers notifications prompting the execution of a fallback plan when a task enters a failed state.

### Directory Structure

- `plugin.json`: Manifest file for the plugin.
- `hooks.json`: Definition file for agent hooks (`PreToolUse`, `PostToolUse`, `Stop`).
- `scripts/`: Python scripts executed by the hooks.
  - `check_pre_tool.py`: Pre-execution validation script.
  - `update_attempts.py`: Post-execution attempt counter update script.
  - `check_stop_condition.py`: Stop condition evaluation script.

### LICENSE

[MIT](./LICENSE.MIT)
