# 05. Slack Bolt 統合

## 概要

Slack Bolt（AsyncApp）と Socket Mode を使用して Slack からのイベントを受信し、メッセージの保存と SlackChannelUpdateEvent の発火を行う。

## 依存タスク

- 01-config-extension.md（SlackConfig）
- 03-slack-message.md（SlackMessage エンティティ、リポジトリ）

## 成果物

### ファイル配置

```
src/myao3/infrastructure/slack/
├── __init__.py
├── client.py       # SlackClient クラス
├── session.py      # SlackSession クラス
└── handlers.py     # イベントハンドラー関数
```

### 依存パッケージ追加

pyproject.toml に以下を追加:

| パッケージ | 用途 |
|-----------|------|
| slack-bolt | Slack アプリフレームワーク |
| slack-sdk | Slack API クライアント |

### SlackClient クラス

Slack との接続を管理するクラス。

**コンストラクタ引数:**

| 引数 | 型 | 説明 |
|------|-----|------|
| config | SlackConfig | Slack 設定 |
| message_repository | SlackMessageRepository | メッセージリポジトリ |
| event_queue | EventQueue | イベントキュー |

**属性:**

| 属性 | 型 | 説明 |
|------|-----|------|
| app | AsyncApp | Slack Bolt アプリ |
| handler | AsyncSocketModeHandler | Socket Mode ハンドラー |
| config | SlackConfig | Slack 設定 |
| message_repository | SlackMessageRepository | メッセージリポジトリ |
| event_queue | EventQueue | イベントキュー |
| session | SlackSession \| None | 認証情報（start() 後に設定） |

**メソッド:**

| メソッド | 戻り値 | 説明 |
|---------|--------|------|
| `async start()` | None | Socket Mode 接続を開始 |
| `async stop()` | None | 接続を終了 |
| `async post_message(channel, text, thread_ts)` | dict | メッセージを投稿 |
| `async add_reaction(channel, timestamp, emoji)` | dict | リアクションを追加 |
| `async fetch_parent_message(channel, thread_ts)` | SlackMessage \| None | 親メッセージを API で取得 |

### SlackSession クラス

Slack 認証情報を保持するデータクラス。`auth.test` API のレスポンスから生成される。

**フィールド:**

| フィールド | 型 | 説明 |
|-----------|-----|------|
| bot_id | str | Bot の User ID（`U` で始まる） |
| bot_user_id | str | Bot のユーザー ID（通常 bot_id と同一） |
| team_id | str | ワークスペースの Team ID |

**設計根拠:**

- `bot_id` は設定ファイルから削除し、`auth.test` API で動的に取得（レビュー指摘による変更）
- 将来のマルチワークスペース対応に備えて `team_id` も保持

### AsyncApp 設定

**初期化パラメータ:**

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| token | config.bot_token | Bot User OAuth Token |
| signing_secret | 不要 | Socket Mode では不要 |

**設計根拠（README.md の決定事項）:**
- Socket Mode を使用するため signing_secret は不要
- NAT 内部からも接続可能

### イベントハンドラー登録

`@app.event("message")` デコレータでメッセージイベントを処理。

**処理対象イベント:**

| イベントタイプ | 処理 |
|---------------|------|
| message | 通常メッセージ |
| message (subtype=message_changed) | メッセージ編集（無視） |
| message (subtype=message_deleted) | メッセージ削除（無視） |

### メッセージイベント処理フロー

```
Slack Message Event
       │
       ├─── subtype チェック ──→ message_changed/deleted → 無視
       │
       ▼
┌─────────────────────────────┐
│ 1. SlackMessage エンティティ │
│    に変換                    │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 2. リポジトリで DB 保存      │
│    (upsert)                  │
└────────────┬────────────────┘
             │
             ├─── Bot 自身のメッセージ → 終了（イベント発火なし）
             │
             ▼
┌─────────────────────────────┐
│ 3. メンション判定            │
│    - text に @bot_id が含まれるか │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 4. 遅延計算                  │
│    - メンション: 0           │
│    - その他: base + jitter   │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 5. SlackChannelUpdateEvent  │
│    を EventQueue に追加      │
└─────────────────────────────┘
```

### SlackMessage への変換

Slack イベントから SlackMessage エンティティを生成。

**フィールドマッピング:**

| SlackMessage | Slack Event | 備考 |
|--------------|-------------|------|
| id | `{channel}:{ts}` | 複合キー |
| channel_id | event["channel"] | |
| user_id | event["user"] | Bot の場合は bot_id |
| text | event["text"] | |
| thread_ts | event.get("thread_ts") | スレッド返信時のみ |
| ts | event["ts"] | |
| is_bot | event.get("bot_id") is not None | |
| is_read | False | 新規メッセージは未読 |
| reply_count | 0 | 新規メッセージは返信なし |
| timestamp | ts から変換 | Unix timestamp → datetime |
| raw_event | event | 生データ保存 |
| created_at | 現在時刻 | |

### メンション判定

**判定ロジック:**

1. メッセージテキストに `<@{session.bot_id}>` が含まれるかチェック
2. 含まれる場合は `is_mention = True`

**Note:** `bot_id` は `auth.test` API で取得した `SlackSession.bot_id` を使用する。

**設計根拠（README.md の決定事項）:**
- メンション判定は @bot名 のみ
- 明確な呼びかけのみ即時対応

### 遅延計算

**計算式:**

```python
if is_mention:
    delay = 0.0
else:
    delay = config.response_delay + random.uniform(0, config.response_delay_jitter)
```

**設計根拠（README.md の決定事項）:**
- メンション時は即時発火（delay=0）
- 非メンション時は `base_delay + random(0, jitter)` で自然な応答タイミング

### ループ防止

**処理:**
- Bot 自身のメッセージ（`is_bot = True` かつ `user_id == session.bot_id`）ではイベントを発火しない

**設計根拠（README.md の決定事項）:**
- Bot のメッセージではイベントを発火しない
- シンプルで確実なループ防止

### start() の動作

1. `auth.test` API を呼び出して認証情報を取得
2. レスポンスから `SlackSession` を作成して `self.session` に設定
3. AsyncSocketModeHandler を作成
4. `handler.start_async()` で接続開始
5. 接続完了をログ出力

**auth.test レスポンス例:**

```json
{
  "ok": true,
  "url": "https://example.slack.com/",
  "team": "Example Team",
  "user": "bot",
  "team_id": "T01234567",
  "user_id": "U01234567",
  "bot_id": "B01234567"
}
```

**SlackSession 生成:**

```python
session = SlackSession(
    bot_id=response["user_id"],    # Bot の User ID
    bot_user_id=response["user_id"],
    team_id=response["team_id"],
)
```

**Note:** `bot_id` フィールドは Bot のアプリ ID であり、メンション判定には `user_id` を使用する。

### stop() の動作

1. `handler.close_async()` で接続終了
2. 終了をログ出力

### スレッド返信時の reply_count 更新

スレッド返信（`thread_ts` あり）を受信した際、親メッセージの `reply_count` をインクリメントする。

**処理フロー:**

```
スレッド返信イベント受信（thread_ts あり）
       │
       ▼
┌─────────────────────────────┐
│ 1. 返信メッセージを保存      │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 2. 親メッセージの reply_count│
│    をインクリメント          │
│    increment_reply_count()  │
└────────────┬────────────────┘
             │
             ├─── 成功（True） ──→ 処理続行
             │
             └─── 失敗（False）──→ 親メッセージを API で取得
                                  │
                                  ▼
                            ┌─────────────────────────────┐
                            │ fetch_parent_message() で   │
                            │ conversations.replies を呼出 │
                            └────────────┬────────────────┘
                                         │
                                         ▼
                            ┌─────────────────────────────┐
                            │ 親メッセージを保存           │
                            │ （reply_count = 1）         │
                            └─────────────────────────────┘
```

### fetch_parent_message() の動作

1. `conversations.replies(channel=channel_id, ts=thread_ts, limit=1)` を呼び出し
2. レスポンスの最初の要素（親メッセージ）を取得
3. `SlackMessage` エンティティに変換して返す（`reply_count = 1`）
4. エラー時は `None` を返す

## テストケース

### TC-05-001: SlackClient 初期化

**手順:**
1. 必要な依存関係を注入して SlackClient を生成

**期待結果:**
- エラーなく初期化される
- AsyncApp が作成される

### TC-05-002: メッセージイベント処理

**手順:**
1. メッセージイベントをシミュレート
2. ハンドラーが呼び出される

**期待結果:**
- SlackMessage が保存される
- SlackChannelUpdateEvent が EventQueue に追加される

### TC-05-003: Bot メッセージのループ防止

**手順:**
1. Bot 自身のメッセージイベントをシミュレート

**期待結果:**
- SlackMessage は保存される
- SlackChannelUpdateEvent は追加されない

### TC-05-004: メンション判定 - メンションあり

**手順:**
1. `<@{bot_id}>` を含むメッセージイベントをシミュレート

**期待結果:**
- `is_mention = True` のイベントが作成される
- `delay = 0` で EventQueue に追加される

### TC-05-005: メンション判定 - メンションなし

**手順:**
1. Bot へのメンションを含まないメッセージイベントをシミュレート

**期待結果:**
- `is_mention = False` のイベントが作成される
- `delay > 0` で EventQueue に追加される

### TC-05-006: 遅延計算の範囲

**手順:**
1. 非メンションメッセージを複数回シミュレート
2. 各遅延値を記録

**期待結果:**
- 全ての遅延が `response_delay` 以上
- 全ての遅延が `response_delay + response_delay_jitter` 以下
- 値にばらつきがある（ランダム性）

### TC-05-007: スレッド返信の処理

**手順:**
1. `thread_ts` を持つメッセージイベントをシミュレート

**期待結果:**
- SlackMessage の `thread_ts` が正しく設定される
- イベントが正しく発火される

### TC-05-008: message_changed の無視

**手順:**
1. subtype="message_changed" のイベントをシミュレート

**期待結果:**
- SlackMessage は保存されない
- イベントは発火されない

### TC-05-009: message_deleted の無視

**手順:**
1. subtype="message_deleted" のイベントをシミュレート

**期待結果:**
- 処理がスキップされる

### TC-05-010: post_message の呼び出し

**手順:**
1. `post_message()` を呼び出し

**期待結果:**
- Slack API が呼び出される
- レスポンスが返される

### TC-05-011: add_reaction の呼び出し

**手順:**
1. `add_reaction()` を呼び出し

**期待結果:**
- Slack API が呼び出される
- レスポンスが返される

### TC-05-012: ts から datetime への変換

**手順:**
1. Slack ts "1737000000.000100" を変換

**期待結果:**
- 正しい datetime オブジェクトに変換される

### TC-05-013: auth.test による SlackSession 作成

**手順:**
1. `start()` を呼び出し
2. `session` 属性を確認

**期待結果:**
- `session` が設定されている
- `session.bot_id` が正しい値
- `session.team_id` が正しい値

### TC-05-014: スレッド返信時の reply_count インクリメント

**手順:**
1. 親メッセージを保存（reply_count = 0）
2. スレッド返信イベントをシミュレート

**期待結果:**
- 親メッセージの `reply_count` が 1 になる

### TC-05-015: 親メッセージ未存在時の API 取得

**手順:**
1. 親メッセージが DB に存在しない状態でスレッド返信イベントをシミュレート

**期待結果:**
- `conversations.replies` API が呼び出される
- 親メッセージが DB に保存される（reply_count = 1）

### TC-05-016: fetch_parent_message の動作

**手順:**
1. `fetch_parent_message()` を呼び出し

**期待結果:**
- `conversations.replies` API が呼び出される
- SlackMessage が返される

## 完了条件

- [ ] slack-bolt, slack-sdk が依存関係に追加されている
- [ ] SlackSession クラスが実装されている
- [ ] SlackClient クラスが実装されている
- [ ] `start()` で `auth.test` を呼び出して SlackSession を作成する
- [ ] AsyncApp が正しく初期化される
- [ ] message イベントハンドラーが登録されている
- [ ] メッセージが SlackMessage として保存される
- [ ] スレッド返信時に親メッセージの `reply_count` がインクリメントされる
- [ ] 親メッセージ未存在時に API で取得される
- [ ] Bot メッセージではイベントが発火されない
- [ ] メンション判定が `session.bot_id` を使用する
- [ ] 遅延計算が正しく動作する
- [ ] start()/stop() で接続管理ができる
- [ ] 全てのテストケースがパスする
