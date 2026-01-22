# Phase 2: Slack対応

## 目標

Slackとの連携機能を実装し、メッセージの受信・保存・応答を可能にする

## 実行環境

Kubernetes クラスタ（ローカルでも動作確認可能）

## 完了条件

- [ ] Slackでメンションされると、文脈を踏まえた返答ができる
- [ ] スレッドに対して適切に返信できる
- [ ] リアクションを追加できる
- [ ] 同じidentity_keyのChannelUpdateEventが連続すると最新のみ処理される
- [ ] Kubernetesクラスタ上で稼働している

## 実装シーケンス

```
Slack Message Event
       │
       ▼
┌─────────────────┐
│ Slack Bolt受信   │
│ (AsyncApp)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ DBにメッセージ   │
│ 保存             │
└────────┬────────┘
         │
         ├─── メンション判定
         │
         ▼
┌─────────────────────────────────────────┐
│ ChannelUpdateEvent を EventQueue に追加  │
│ - メンション時: delay=0                  │
│ - その他: delay=base + jitter           │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ EventLoop処理    │
│ (重複マージ)     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ SlackChannelUpdateHandler               │
│ - チャンネルメッセージをDBから取得        │
│ - 親メッセージ+スレッドに構造化          │
│ - query_prompt構築                      │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ Agent Loop      │
│ (LLM呼び出し)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ ツール実行                               │
│ - post_slack_message(channel, text,     │
│   thread_ts)                            │
│ - add_slack_reaction(channel, ts, emoji)│
└─────────────────────────────────────────┘
```

## タスク一覧

| # | タスク | ファイル | 依存 |
|---|--------|----------|------|
| 01 | 設定ファイル拡張 | [01-config-extension.md](./01-config-extension.md) | - |
| 02 | データベース基盤 | [02-database.md](./02-database.md) | 01 |
| 03 | SlackMessageエンティティ | [03-slack-message.md](./03-slack-message.md) | 02 |
| 04 | SlackChannelUpdateEvent | [04-slack-channel-update-event.md](./04-slack-channel-update-event.md) | 03 |
| 05 | Slack Bolt統合 | [05-slack-bolt.md](./05-slack-bolt.md) | 01, 03 |
| 06 | SlackChannelUpdateHandler | [06-slack-channel-update-handler.md](./06-slack-channel-update-handler.md) | 04 |
| 07 | Slackツール | [07-slack-tools.md](./07-slack-tools.md) | 05 |
| 08 | Personエンティティ | [08-person.md](./08-person.md) | 02 |
| 09 | 三層記憶システム | [09-memory.md](./09-memory.md) | 02, 08 |
| 10 | Dockerイメージ | [10-docker.md](./10-docker.md) | 01-07 |
| 11 | K8s Deployment | [11-kubernetes.md](./11-kubernetes.md) | 10 |

**Note:** タスク08-09（個人認識、記憶システム）は基本的な構造のみ定義し、詳細実装は後回しとする。

## 依存関係図

```
Task 01 (設定拡張) ─────────────────────────┐
    │                                       │
    ├─────────────────┐                     │
    ▼                 │                     │
Task 02 (DB基盤)     │                     │
    │                 │                     │
    ├─────────────┐   │                     │
    ▼             │   │                     │
Task 03 (SlackMessage)                      │
    │             │   │                     │
    ├─────────────┼───┤                     │
    ▼             ▼   ▼                     │
Task 04 (Event)  Task 05 (Bolt)            │
    │                 │                     │
    ▼                 ▼                     │
Task 06 (Handler)    Task 07 (Tools)       │
    │                 │                     │
    └────────┬────────┘                     │
             ▼                              │
Task 08 (Person) ◄──────────────────────────┤
    │                                       │
    ▼                                       │
Task 09 (Memory)                            │
    │                                       │
    ▼                                       │
Task 10 (Docker) ◄──────────────────────────┘
    │
    ▼
Task 11 (K8s)
```

## 最終ディレクトリ構造

```
myao3/
├── src/
│   └── myao3/
│       ├── config/
│       │   ├── __init__.py
│       │   ├── loader.py
│       │   └── models.py          # SlackConfig, DatabaseConfig追加
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── entities/
│       │   │   ├── __init__.py
│       │   │   ├── event.py       # SlackChannelUpdateEvent追加
│       │   │   ├── slack_message.py
│       │   │   ├── person.py      # 後回し可能
│       │   │   └── identity.py    # 後回し可能
│       │   └── repositories/
│       │       ├── __init__.py
│       │       ├── slack_message_repository.py
│       │       └── person_repository.py  # 後回し可能
│       ├── application/
│       │   ├── __init__.py
│       │   ├── handlers/
│       │   │   ├── __init__.py
│       │   │   └── slack_channel_update_handler.py
│       │   └── services/
│       │       ├── __init__.py
│       │       ├── agent_loop.py
│       │       └── memory_service.py  # 後回し可能
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   ├── event_queue.py
│       │   ├── llm/
│       │   │   ├── __init__.py
│       │   │   └── litellm_model.py
│       │   ├── logging/
│       │   │   ├── __init__.py
│       │   │   └── setup.py
│       │   ├── persistence/
│       │   │   ├── __init__.py
│       │   │   ├── database.py
│       │   │   └── slack_message_repository.py
│       │   └── slack/
│       │       ├── __init__.py
│       │       ├── client.py
│       │       ├── handlers.py
│       │       └── tools.py
│       └── presentation/
│           ├── __init__.py
│           └── http/
│               ├── __init__.py
│               └── server.py
├── k8s/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── pvc.yaml
├── Dockerfile
├── config.yaml.example
└── ...
```

## query_promptフォーマット例

```
## Channel: #general (C1234567890)

### Recent Messages (newest first)

[2026-01-21 10:05:00] @bob (U002) (ts=1737453900.000200): [UNREAD]
@myao3 Can you help me with something?

[2026-01-21 10:00:00] @alice (U001) (ts=1737453600.000100):
Hello everyone!

  [Thread - 2 replies, showing latest 2]
  [2026-01-21 10:02:00] @charlie (U003) (ts=1737453720.000150): [UNREAD]
  Good morning!

  [2026-01-21 10:01:00] @bob (U002) (ts=1737453660.000120):
  Hi Alice!

[2026-01-21 09:55:00] @dave (U004) (ts=1737453300.000050):
...

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

**Note:** 各メッセージに `(ts=XXX)` を付与することで:
- スレッド返信時に親メッセージのtsを `thread_ts` として使用可能
- リアクション追加時に対象メッセージのtsを `timestamp` として使用可能

## 設定ファイル拡張

`config.yaml.example` に以下を追加:

```yaml
slack:
  bot_token: ${SLACK_BOT_TOKEN}
  app_token: ${SLACK_APP_TOKEN}
  response_delay: 480.0      # 非メンション時の基本遅延（秒）
  response_delay_jitter: 240.0  # ジッター範囲（秒）
  context_messages: 30        # LLMに渡すチャンネルメッセージ数
  thread_messages: 10         # スレッド内の展開メッセージ数

database:
  url: "sqlite+aiosqlite:///data/myao3.db"
```

## SlackMessageエンティティ

```python
class SlackMessage(SQLModel, table=True):
    """Slack message entity with read status."""

    id: str = Field(primary_key=True)  # channel_id:ts の複合キー
    channel_id: str = Field(index=True)
    user_id: str = Field(index=True)
    text: str
    thread_ts: str | None = None  # 親メッセージのts（スレッド用）
    ts: str                        # Slack timestamp
    is_bot: bool = False           # botのメッセージかどうか
    is_read: bool = False          # 既読フラグ
    timestamp: datetime
    raw_event: dict                # 生イベントデータ
    created_at: datetime
```

**リポジトリメソッド:**
- `save(message: SlackMessage) -> None`
- `get_by_channel(channel_id: str, limit: int) -> list[SlackMessage]`
- `get_thread(channel_id: str, thread_ts: str, limit: int) -> list[SlackMessage]`
- `get_unread_count(channel_id: str) -> int`
- `mark_as_read(message_ids: list[str]) -> None`

## 決定事項

### 基本設計

| 項目 | 選択 | 理由・備考 |
|------|------|-----------|
| Slack接続方式 | Socket Mode | NAT内部からも接続可能、webhook不要 |
| 非同期フレームワーク | AsyncApp + AsyncSocketModeHandler | 既存asyncioアーキテクチャと整合 |
| DB接続 | aiosqlite | 非同期対応、SQLModelと互換 |
| ORM | SQLModel | Pydanticベースで型安全 |
| メッセージID | `channel_id:ts` 複合キー | 一意性保証、スレッド関連付けに使用 |
| identity_key形式 | `slack_ch_update:{channel_id}` | チャンネル単位でイベントマージ |
| 遅延計算 | `base_delay + random(0, jitter)` | 自然な応答タイミング |
| ツール注入方式 | invocation_state | strands-agentsの推奨パターン |
| EventType名 | `SLACK_CHANNEL_UPDATE` | Slack固有のイベントであることを明示 |

### メッセージ保存

| 項目 | 決定 | 理由 |
|------|------|------|
| 保存スコープ | botが参加するチャンネルのみ | 必要な文脈のみ保持 |
| botメッセージ | Slackイベントとして受信した自身のメッセージを保存 | 完全な履歴 |
| 未読管理 | メッセージ単位で管理 | 細かい対応状況の追跡 |
| 既読タイミング | LLMがクエリで受け取った時点 | シンプル、一度見たら既読 |

### イベント発火

| 項目 | 決定 | 理由 |
|------|------|------|
| 発火条件 | 全メッセージで発火（botのメッセージを除く） | 重複制御でマージ |
| メンション判定 | @bot名 のみ | 明確な呼びかけのみ即時対応 |
| ループ防止 | botのメッセージではイベントを発火しない | シンプルで確実 |

### LLMコンテキスト

| 項目 | 決定 | デフォルト値 |
|------|------|-------------|
| チャンネルメッセージ | 最新N件（未読/既読問わず） | N=30 |
| スレッド展開 | 最新M件のみ展開 | M=10 |
| 未読表示 | [UNREAD]マーカーを付与 | - |
| ts表示 | 各メッセージに(ts=XXX)を付与 | スレッド返信・リアクション用 |
| 返信判断 | LLMが任意に判断（必須ではない） | - |

### 遅延設定

| 項目 | デフォルト値 | 備考 |
|------|-------------|------|
| response_delay | 480秒（8分） | 非メンション時の基本遅延 |
| response_delay_jitter | 240秒（4分） | ジッター範囲 |
| メンション時 | 0秒 | 即時発火 |

## 検証方法

### ローカルテスト

```bash
# 起動
python -m myao3 --config config.yaml

# 検証項目
# - Slackでボットにメンションして返答を確認
# - スレッド内でメンションして、スレッド返信を確認
# - リアクション追加の動作確認
```

### Kubernetesテスト

```bash
# Deploymentをapply
kubectl apply -f k8s/

# Pod内でログを確認
kubectl logs -f deployment/myao3

# Slackで動作確認
```
