# 06. SlackChannelUpdateHandler

## 概要

SlackChannelUpdateEvent を処理し、LLM に渡す query_prompt を構築するハンドラーを実装する。チャンネルのメッセージ履歴を取得し、スレッドを展開して構造化されたプロンプトを生成する。

## 依存タスク

- 04-slack-channel-update-event.md

## 成果物

### ファイル配置

```
src/myao3/application/handlers/
├── __init__.py                       # ハンドラー登録
└── slack_channel_update_handler.py   # ハンドラー実装
```

### SlackChannelUpdateHandler クラス

EventHandler Protocol を実装するハンドラークラス。

**コンストラクタ引数:**

| 引数 | 型 | 説明 |
|------|-----|------|
| message_repository | SlackMessageRepository | メッセージリポジトリ |
| config | SlackConfig | Slack 設定 |

**メソッド:**

| メソッド | 引数 | 戻り値 | 説明 |
|---------|------|--------|------|
| `async build_query(event)` | SlackChannelUpdateEvent | str | query_prompt を構築 |

### build_query() の処理フロー

```
SlackChannelUpdateEvent
         │
         ▼
┌─────────────────────────────┐
│ 1. チャンネルメッセージ取得  │
│    - 最新 N 件              │
│    - スレッド返信除外        │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 2. 各メッセージのスレッド    │
│    展開（最新 M 件）         │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 3. メッセージ ID リスト作成  │
│    （既読マーク用）          │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 4. 既読マーク                │
│    mark_as_read()           │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 5. query_prompt 構築        │
│    テンプレートでフォーマット │
└─────────────────────────────┘
```

### メッセージ取得

**チャンネルメッセージ:**
- `get_by_channel(channel_id, limit=config.context_messages)` で取得
- 新しい順でソート済み
- スレッド返信は除外済み

**スレッド展開:**
- `reply_count > 0` の親メッセージのみ `get_thread(channel_id, ts, limit=config.thread_messages)` で取得
- 古い順でソート済み

**設計根拠（README.md の決定事項）:**
- チャンネルメッセージは最新 N 件（デフォルト 30 件）
- スレッドは最新 M 件のみ展開（デフォルト 10 件）
- `reply_count` による最適化でスレッド返信がないメッセージの DB クエリを削減（レビュー指摘による追加）

### 既読マーク処理

**処理内容:**
1. 取得した全メッセージの ID をリストに収集
2. `mark_as_read(message_ids)` で一括更新

**設計根拠（README.md の決定事項）:**
- LLM がクエリで受け取った時点で既読にマーク
- シンプル、一度見たら既読

### query_prompt フォーマット

README.md で定義されたフォーマットに従う。

**テンプレート:**

```
## Channel: #{channel_name} ({channel_id})

### Recent Messages (newest first)

{formatted_messages}

---

Based on the above conversation, decide if and how you should respond.
Messages marked [UNREAD] have not been addressed yet.

Available actions:
- post_slack_message(channel, text, thread_ts): Post a message
  - To reply in a thread, use the ts of the parent message as thread_ts
  - To post a new message, omit thread_ts
- add_slack_reaction(channel, timestamp, emoji): Add a reaction
  - Use the ts value of the target message as timestamp

You may choose to:
- Respond to one or more messages
- Add reactions
- Do nothing if no response is needed
```

### メッセージフォーマット

**親メッセージ（スレッドなし）:**

```
[{timestamp}] @{user_name} ({user_id}) (ts={ts}): {unread_marker}
{text}
```

**親メッセージ（スレッドあり）:**

```
[{timestamp}] @{user_name} ({user_id}) (ts={ts}): {unread_marker}
{text}

  [Thread - {reply_count} replies, showing latest {shown_count}]
  [{timestamp}] @{user_name} ({user_id}) (ts={ts}): {unread_marker}
  {text}

  [{timestamp}] @{user_name} ({user_id}) (ts={ts}): {unread_marker}
  {text}
```

**フィールド説明:**

| フィールド | 説明 |
|-----------|------|
| timestamp | ISO 形式の日時（例: 2026-01-21 10:05:00） |
| user_name | ユーザーの表示名（Phase-2 では user_id で代替可） |
| user_id | Slack User ID |
| ts | Slack タイムスタンプ（ツール呼び出しで使用） |
| unread_marker | 未読の場合 `[UNREAD]`、既読の場合は空 |
| text | メッセージ本文 |

**設計根拠（README.md の決定事項）:**
- 各メッセージに `(ts=XXX)` を付与
- スレッド返信時に親メッセージの ts を `thread_ts` として使用可能
- リアクション追加時に対象メッセージの ts を `timestamp` として使用可能

### EventHandlerRegistry への登録

**登録内容:**

| EventType | Handler |
|-----------|---------|
| SLACK_CHANNEL_UPDATE | SlackChannelUpdateHandler |

## テストケース

### TC-06-001: 基本的な query_prompt 構築

**手順:**
1. チャンネルに複数メッセージを保存
2. SlackChannelUpdateEvent を作成
3. `build_query()` を呼び出し

**期待結果:**
- 正しいフォーマットの query_prompt が返される
- チャンネル ID が含まれる

### TC-06-002: メッセージの順序

**手順:**
1. 異なるタイムスタンプのメッセージを保存
2. `build_query()` を呼び出し

**期待結果:**
- メッセージが新しい順で表示される

### TC-06-003: スレッド展開

**手順:**
1. 親メッセージとスレッド返信を保存
2. `build_query()` を呼び出し

**期待結果:**
- 親メッセージの下にスレッドが展開される
- スレッド内は古い順で表示される
- Thread ヘッダーに返信数が表示される

### TC-06-004: 未読マーカー

**手順:**
1. 未読メッセージと既読メッセージを保存
2. `build_query()` を呼び出し

**期待結果:**
- 未読メッセージに `[UNREAD]` マーカーが付く
- 既読メッセージにはマーカーがない

### TC-06-005: 既読マーク処理

**手順:**
1. 未読メッセージを保存
2. `build_query()` を呼び出し
3. メッセージの `is_read` を確認

**期待結果:**
- 取得されたメッセージが全て `is_read = True` になる

### TC-06-006: context_messages 制限

**手順:**
1. `context_messages` より多くのメッセージを保存
2. `build_query()` を呼び出し

**期待結果:**
- 取得されるメッセージ数が `context_messages` 以下

### TC-06-007: thread_messages 制限

**手順:**
1. `thread_messages` より多くのスレッド返信を保存
2. `build_query()` を呼び出し

**期待結果:**
- スレッド内の表示メッセージ数が `thread_messages` 以下

### TC-06-008: ts の表示

**手順:**
1. メッセージを保存
2. `build_query()` を呼び出し

**期待結果:**
- 各メッセージに `(ts=XXX)` が含まれる

### TC-06-009: 空のチャンネル

**手順:**
1. メッセージがないチャンネルでイベントを作成
2. `build_query()` を呼び出し

**期待結果:**
- エラーなく query_prompt が返される
- メッセージセクションが空

### TC-06-010: Bot メッセージの表示

**手順:**
1. Bot のメッセージを含むチャンネルでイベントを作成
2. `build_query()` を呼び出し

**期待結果:**
- Bot メッセージも表示される
- 適切にフォーマットされる

### TC-06-011: Available actions セクション

**手順:**
1. `build_query()` を呼び出し

**期待結果:**
- `post_slack_message` の説明が含まれる
- `add_slack_reaction` の説明が含まれる

## 完了条件

- [ ] SlackChannelUpdateHandler クラスが実装されている
- [ ] EventHandler Protocol を実装している
- [ ] チャンネルメッセージを正しく取得する
- [ ] スレッドを正しく展開する
- [ ] 未読マーカーが正しく付与される
- [ ] 取得したメッセージが既読にマークされる
- [ ] ts が各メッセージに表示される
- [ ] README.md のフォーマットに準拠している
- [ ] EventHandlerRegistry に登録されている
- [ ] 全てのテストケースがパスする
