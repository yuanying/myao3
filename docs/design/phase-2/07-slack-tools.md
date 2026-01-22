# 07. Slack ツール

## 概要

LLM が Slack へアクションを実行するためのツールを実装する。`post_slack_message` でメッセージ投稿、`add_slack_reaction` でリアクション追加を行う。

## 依存タスク

- 05-slack-bolt.md（SlackClient）

## 成果物

### ファイル配置

```
src/myao3/infrastructure/slack/
├── __init__.py
├── client.py       # SlackClient（既存）
├── handlers.py     # イベントハンドラー（既存）
└── tools.py        # ツール定義
```

### ツール定義方式

strands-agents の `@tool` デコレータを使用してツールを定義。

**ツール注入方式:**
- `invocation_state` 経由で SlackClient を注入
- Agent 作成時に tools パラメータで登録

**設計根拠（README.md の決定事項）:**
- ツール注入方式は `invocation_state` を採用
- strands-agents の推奨パターンに従う

### post_slack_message ツール

Slack チャンネルにメッセージを投稿する。

**パラメータ:**

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| channel | str | ○ | チャンネル ID |
| text | str | ○ | メッセージ本文 |
| thread_ts | str | - | スレッド返信時の親メッセージ ts |

**戻り値:**

| フィールド | 型 | 説明 |
|-----------|-----|------|
| ok | bool | 成功/失敗 |
| ts | str | 投稿されたメッセージの ts |
| channel | str | チャンネル ID |
| message | dict | 投稿されたメッセージ情報 |

**エラー時:**

| フィールド | 型 | 説明 |
|-----------|-----|------|
| ok | bool | False |
| error | str | エラーメッセージ |

**処理フロー:**

1. `invocation_state` から SlackClient を取得
2. `client.post_message(channel, text, thread_ts)` を呼び出し
3. Slack API レスポンスを返却

**使用例（LLM から）:**

```
# 新規メッセージ
post_slack_message(channel="C123", text="Hello!")

# スレッド返信
post_slack_message(channel="C123", text="Reply!", thread_ts="1737000000.000100")
```

### add_slack_reaction ツール

Slack メッセージにリアクションを追加する。

**パラメータ:**

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| channel | str | ○ | チャンネル ID |
| timestamp | str | ○ | 対象メッセージの ts |
| emoji | str | ○ | リアクション絵文字名（コロンなし） |

**戻り値:**

| フィールド | 型 | 説明 |
|-----------|-----|------|
| ok | bool | 成功/失敗 |

**エラー時:**

| フィールド | 型 | 説明 |
|-----------|-----|------|
| ok | bool | False |
| error | str | エラーメッセージ |

**処理フロー:**

1. `invocation_state` から SlackClient を取得
2. `client.add_reaction(channel, timestamp, emoji)` を呼び出し
3. Slack API レスポンスを返却

**使用例（LLM から）:**

```
add_slack_reaction(channel="C123", timestamp="1737000000.000100", emoji="thumbsup")
```

**絵文字名の形式:**
- コロンなしで指定（例: `thumbsup`、`heart`、`smile`）
- カスタム絵文字も名前で指定可能

### ツール登録

**Agent への登録:**

```python
agent = Agent(
    model=model,
    system_prompt=system_prompt,
    tools=[post_slack_message, add_slack_reaction],
)
```

**invocation_state の設定:**

```python
result = await agent.invoke_async(
    query,
    invocation_state={"slack_client": slack_client}
)
```

### エラーハンドリング

**Slack API エラー:**

| エラー | 対処 |
|--------|------|
| channel_not_found | エラーをそのまま返却 |
| not_in_channel | エラーをそのまま返却 |
| is_archived | エラーをそのまま返却 |
| msg_too_long | エラーをそのまま返却 |
| no_text | エラーをそのまま返却 |
| invalid_auth | ログ出力してエラーを返却 |
| already_reacted | ok=True として返却（重複は許容） |

**設計方針:**
- API エラーは LLM に伝えて判断を委ねる
- `already_reacted` は成功として扱う（べき等性）

### ツール命名規則

**設計根拠（CLAUDE.md の設計ポリシー）:**
- 具体的なプラットフォーム名を含む
- 例: `post_slack_message`（`post_message` ではなく）

**理由:**
- 将来的なマルチプラットフォーム対応を考慮
- ツール名から対象プラットフォームが明確

## テストケース

### TC-07-001: post_slack_message - 新規メッセージ

**手順:**
1. `post_slack_message(channel="C123", text="Hello!")` を呼び出し

**期待結果:**
- Slack API `chat.postMessage` が呼び出される
- `thread_ts` が指定されていない
- 成功レスポンスが返される

### TC-07-002: post_slack_message - スレッド返信

**手順:**
1. `post_slack_message(channel="C123", text="Reply!", thread_ts="1737...")` を呼び出し

**期待結果:**
- Slack API に `thread_ts` が含まれる
- スレッドに返信される

### TC-07-003: post_slack_message - エラーハンドリング

**手順:**
1. 存在しないチャンネルに投稿を試みる

**期待結果:**
- `ok=False` と `error` が返される
- 例外が発生しない

### TC-07-004: add_slack_reaction - 成功

**手順:**
1. `add_slack_reaction(channel="C123", timestamp="1737...", emoji="thumbsup")` を呼び出し

**期待結果:**
- Slack API `reactions.add` が呼び出される
- 成功レスポンスが返される

### TC-07-005: add_slack_reaction - already_reacted

**手順:**
1. 同じメッセージに同じリアクションを2回追加

**期待結果:**
- 2回目も `ok=True` が返される
- エラーとして扱われない

### TC-07-006: add_slack_reaction - エラーハンドリング

**手順:**
1. 存在しないメッセージにリアクションを試みる

**期待結果:**
- `ok=False` と `error` が返される
- 例外が発生しない

### TC-07-007: invocation_state からの SlackClient 取得

**手順:**
1. ツールを `invocation_state` なしで呼び出し

**期待結果:**
- 適切なエラーメッセージが返される

### TC-07-008: ツールスキーマの検証

**手順:**
1. ツールのスキーマを取得
2. パラメータ定義を確認

**期待結果:**
- channel, text が必須
- thread_ts がオプション
- 適切な型定義がある

### TC-07-009: 絵文字名のバリデーション

**手順:**
1. コロン付きの絵文字名 `:thumbsup:` で呼び出し

**期待結果:**
- エラーが返される、またはコロンが除去される

### TC-07-010: 長いメッセージの投稿

**手順:**
1. Slack の制限を超える長さのメッセージを投稿

**期待結果:**
- `msg_too_long` エラーが返される

### TC-07-011: Agent との統合

**手順:**
1. Agent に両ツールを登録
2. ツール呼び出しを含む応答を生成

**期待結果:**
- Agent がツールを正しく呼び出せる
- 結果が Agent に返される

## 完了条件

- [ ] post_slack_message ツールが実装されている
- [ ] add_slack_reaction ツールが実装されている
- [ ] @tool デコレータで定義されている
- [ ] invocation_state から SlackClient を取得する
- [ ] 新規メッセージ投稿が動作する
- [ ] スレッド返信が動作する
- [ ] リアクション追加が動作する
- [ ] エラーハンドリングが適切
- [ ] already_reacted が成功として扱われる
- [ ] Agent に登録して使用できる
- [ ] 全てのテストケースがパスする
