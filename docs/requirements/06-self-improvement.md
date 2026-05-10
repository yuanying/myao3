## 3.5 自己改善

#### FR-IMPROVE-001: 自己改善フレームワーク

| 項目 | 内容 |
|------|------|
| 概要 | ボットがシステムプロンプトを調整することで振る舞いを改善する |
| 優先度 | 中 |
| フェーズ | Phase 4 |

**改善可能な対象**:
- `prompts/soul.md` の限定的な調整（口調、距離感など）
- `prompts/behavior.md` の限定的な調整（反応傾向、判断基準など）
- `prompts/memory.md` の限定的な調整（記憶取得・記憶整理の方針など）
- `prompts/dynamic/*.md` への行動メモ追加

**改善対象外**:
- `prompts/core.md` の変更
- `prompts/tools.md` の変更
- `prompts/safety.md` の変更
- 完成済みsystem_prompt全文の置き換え
- ツールの実装変更
- 記憶システムのロジック変更
- イベント処理の変更

**自己改善の仕組み**:

```python
class SelfImprovement(BaseModel):
    """ボットによるプロンプト改善の監査ログ"""
    id: str
    target_file: Literal[
        "prompts/soul.md",
        "prompts/behavior.md",
        "prompts/memory.md",
        "prompts/dynamic/behavior_notes.md",
    ]
    change_type: Literal["patch", "append_note"]
    previous_excerpt: str | None
    new_excerpt: str
    reason: str                      # なぜこの変更が必要か
    trigger_event_id: Optional[str]  # きっかけとなったイベント
    applied_at: datetime
```

**運用フロー**:

1. ボットが改善対象ファイルと変更内容を限定して改善を実行
2. 許可された Markdown ファイルへ変更を直接適用する
3. 変更内容が監査ログに出力される
4. 管理者は必要に応じてログを確認
5. 問題のある改善は管理者が Markdown ファイルを直接編集する、またはファイル履歴から戻す

```
# ログ出力例
[2026-01-16 10:30:00] SELF_IMPROVEMENT: prompts/behavior.md patched
  reason: "挨拶が堅すぎると感じたため、よりカジュアルな口調に調整"
  diff: -"こんにちは。何かお手伝いできることはありますか？"
        +"やあ！何か手伝おうか？"
```

**制約**:

| 制約 | 説明 |
|------|------|
| 全文置換禁止 | system_prompt全体や保護ファイル全体を置き換えてはならない |
| 変更対象の限定 | 自己改善ツールは許可されたMarkdownファイルだけを変更できる |
| 重要指示の保護 | Core、Tooling、Safetyは管理者のみが変更できる |
| 差分記録 | 変更理由、差分、きっかけイベントを必ず保存する |
| ロールバック | 問題のある改善はMarkdownファイルの再編集またはファイル履歴で戻す |

**ツール定義**:

```python
from strands import tool

@tool
def propose_prompt_patch(
    target_file: Literal["prompts/soul.md", "prompts/behavior.md", "prompts/memory.md"],
    patch: str,
    reason: str,
) -> str:
    """Patch an allowed prompt Markdown file to improve your behavior.

    Use this only for small, focused changes to personality, behavior, or memory policy.
    Core, tooling, and safety prompts cannot be changed by this tool.

    Args:
        target_file: The allowed prompt file to patch
        patch: A unified diff or equivalent small patch
        reason: Explanation of why this change is needed
    """
    # 実装: patchを検証し、許可されたファイルにのみ適用し、監査ログを記録
    apply_prompt_patch(target_file, patch, reason)
    return f"Prompt patch applied to {target_file}. Reason: {reason}"


@tool
def append_behavior_note(
    category: Literal["tone", "timing", "reaction", "memory"],
    note: str,
    reason: str,
) -> str:
    """Append a short dynamic behavior note.

    Use this when a full patch is unnecessary and a small behavioral reminder is enough.
    Notes are appended to prompts/dynamic/behavior_notes.md and injected in the Dynamic Notes section.

    Args:
        category: The behavior category
        note: A concise behavior note
        reason: Explanation of why this note is needed
    """
    # 実装: prompts/dynamic/behavior_notes.mdへ追記し、監査ログを記録
    append_dynamic_note(category, note, reason)
    return f"Behavior note appended. Reason: {reason}"
```

---
