# myao3 要求仕様書

**バージョン**: 0.10.0  
**作成日**: 2026-01-16  
**ステータス**: Draft

---

## 1. 概要

### 1.1 目的

本ドキュメントは、イベント駆動で動作し、自律的に環境へ適応していく「みんなの友達」ボット（以下、myao3）の要求仕様を定義する。

### 1.2 ビジョン

myao3は、複数のコミュニティに存在し、そこにいる人々を認識し、適切なタイミングで適切な形で関わる存在である。押し付けがましくなく、しかし必要なときにはそこにいる——そのような「友達」としての振る舞いを目指す。

### 1.3 基本原則

| 原則 | 説明 |
|------|------|
| **自律性** | いつ・何を・どのように行動するかはボット自身が判断する |
| **透明性** | 内部思考は外部に漏れず、意図した行動のみが表出する |
| **適応性** | 経験を通じて自己を改善し、環境に適応していく |
| **漸進性** | 機能は段階的に拡張され、最初は最小限から始まる |

---

## 2. システムコンセプト

### 2.1 世界認識モデル

```
┌─────────────────────────────────────────────────────────┐
│                      外部世界                            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │
│  │  Slack  │  │ Discord │  │  Email  │  │   ...   │    │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘    │
│       │            │            │            │          │
│       ▼            ▼            ▼            ▼          │
│  ┌─────────────────────────────────────────────────┐   │
│  │              イベントストリーム                   │   │
│  │   (Ping, Message, Reaction, Presence, ...)      │   │
│  └─────────────────────┬───────────────────────────┘   │
└────────────────────────┼───────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                       myao3                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │                 Agent Loop                       │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐   │   │
│  │  │   認識    │→│   思考    │→│   判断    │   │   │
│  │  └───────────┘  └───────────┘  └─────┬─────┘   │   │
│  │         ↑                            │          │   │
│  │         │         （内部で完結）       │          │   │
│  │         └────────────────────────────┘          │   │
│  └─────────────────────────┬───────────────────────┘   │
│                            │                            │
│  ┌─────────────────────────▼───────────────────────┐   │
│  │                   ツール層                       │   │
│  │  唯一の外部世界へのインターフェース              │   │
│  │  - post_message(channel, text)                  │   │
│  │  - send_email(to, subject, body)                │   │
│  │  - update_memory(...)                           │   │
│  │  - modify_self(...)  ※将来                      │   │
│  └─────────────────────────┬───────────────────────┘   │
│                            │                            │
│  ┌─────────────────────────▼───────────────────────┐   │
│  │                  記憶システム                    │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────────┐     │   │
│  │  │ Working │  │ Short-  │  │  Long-term  │     │   │
│  │  │ Memory  │  │  term   │  │   Memory    │     │   │
│  │  └─────────┘  └─────────┘  └─────────────┘     │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 コア設計思想

#### 2.2.1 閉じたAgent Loop

Agent Loopで生成される全ての中間出力（思考、推論、計画）は外部に漏れない。ボットが外部世界に影響を与える唯一の手段は、明示的に定義されたツールの呼び出しである。

```
イベント受信 → [認識 → 思考 → 判断]（内部） → ツール呼び出し（任意） → 完了
                    ↑                              │
                    └──────── 記憶参照/更新 ────────┘
```

#### 2.2.2 ツールによる世界との接点

ボットは以下の方法でのみ外部世界と相互作用する：

- **出力ツール**: メッセージ送信、リアクション追加など
- **記憶ツール**: 経験の永続化、想起
- **自己改善ツール**: システムプロンプトの調整（将来実装）

**ツール命名規則**:

ツールは具体的なプラットフォーム名を含む命名とする。これによりボットは「自分が何を使って世界と関わっているか」を明示的に認識できる。

```
# 良い例（採用）
post_slack_message(channel, text)
add_slack_reaction(channel, timestamp, emoji)
send_discord_message(channel_id, text)
send_email(to, subject, body)

# 悪い例（不採用）
post_message(platform, channel, text)  # 抽象的すぎる
communicate(intent, target)            # 何をしているか不明瞭
```

#### 2.2.3 自律的判断

ボットは全てのイベントに対して反応する義務を持たない。以下を自律的に判断する：

- 反応すべきかどうか
- 反応するならいつ（即座に/遅延して/しない）
- どのような形式で（メッセージ/リアクション/沈黙）
- どの程度の深さで（軽い挨拶/深い会話/傾聴）

---

## 3. 機能要件

### 3.1 イベント処理

#### FR-EVENT-001: イベント受信基盤

| 項目 | 内容 |
|------|------|
| 概要 | 様々なソースからイベントを受信し、統一的に処理する |
| 優先度 | 必須 |
| フェーズ | Phase 1 |

**イベント型定義**:

```python
class EventType(Enum):
    PING = "ping"                    # Phase 1
    MESSAGE = "message"              # Phase 2
    REACTION = "reaction"            # Phase 2
    PRESENCE = "presence"            # Phase 3
    SCHEDULED = "scheduled"          # Phase 3
    SELF_TRIGGERED = "self_triggered"  # ボット自身が発火
    CHANNEL_UPDATE = "channel_update"  # チャンネル情報更新
    # 拡張可能...

class Event(BaseModel):
    id: str                          # イベント一意識別子
    type: EventType
    timestamp: datetime              # イベント発生時刻
    source: str                      # "slack", "discord", "self", etc.
    payload: dict                    # イベント固有データ
    context: Optional[dict] = None   # 追加コンテキスト
    created_at: datetime             # イベント作成時刻

    def get_identity_key(self) -> str:
        """重複制御用のキーを返す。
        
        同じidentity_keyを持つイベントは、古いものがキャンセルされ
        新しいものに置き換えられる。
        """
        # デフォルトはイベントIDそのもの（重複なし）
        # サブクラスでオーバーライドして重複制御を実現
        return self.id
```

**イベントタイプ別のidentity_key例**:

| イベントタイプ | identity_key | 説明 |
|----------------|--------------|------|
| PING | `ping` | 常に同一キー（連続Pingは最新のみ処理） |
| MESSAGE | `msg:{message_id}` | メッセージごとに一意 |
| CHANNEL_UPDATE | `ch_update:{channel_id}` | チャンネルごとにマージ |
| PRESENCE | `presence:{user_id}` | ユーザーごとにマージ |
| SELF_TRIGGERED | `self:{event_id}` | 通常は一意 |

```python
# 例: SlackChannelUpdateEvent
class SlackChannelUpdateEvent(Event):
    def get_identity_key(self) -> str:
        return f"slack_ch_update:{self.payload['channel_id']}"
```

#### FR-EVENT-003: イベントキュー

| 項目 | 内容 |
|------|------|
| 概要 | 重複制御と遅延エンキューをサポートするインメモリキュー |
| 優先度 | 必須 |
| フェーズ | Phase 1 |

**機能**:

| 機能 | 説明 |
|------|------|
| 重複制御 | 同じidentity_keyのイベントが来たら、古いイベントをキャンセルして新しいものに置き換え |
| 遅延エンキュー | delay指定でキューへの追加を遅延できる |
| 処理状態トラッキング | 処理中のイベントを追跡し、同じキーの新イベントをキューに入れられる |

**実装**:

```python
class EventQueue:
    """In-memory event queue with duplicate control and delayed enqueue."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        # Pending events waiting in queue (identity_key -> Event)
        self._pending: dict[str, Event] = {}
        # Events currently being processed (identity_key -> Event)
        self._processing: dict[str, Event] = {}
        # Delayed enqueue tasks (identity_key -> Task)
        self._delay_tasks: dict[str, asyncio.Task[None]] = {}

    async def enqueue(self, event: Event, delay: float | None = None) -> None:
        """Add an event to the queue.

        If an event with the same identity key is already pending or scheduled,
        it will be cancelled and replaced by this event.
        """
        identity_key = event.get_identity_key()

        # Cancel any existing delayed enqueue task for this identity key
        if identity_key in self._delay_tasks:
            task = self._delay_tasks.pop(identity_key)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Replace pending event with same key
        if identity_key in self._pending:
            # Mark as replaced by updating _pending
            # When dequeued, we'll check if it's current
            pass

        if delay is not None and delay > 0:
            task = asyncio.create_task(self._delayed_enqueue(event, delay))
            self._delay_tasks[identity_key] = task
        else:
            self._pending[identity_key] = event
            await self._queue.put(event)

    async def dequeue(self) -> Event:
        """Get the next event to process.
        
        Skips events that have been replaced by newer ones.
        """
        while True:
            event = await self._queue.get()
            identity_key = event.get_identity_key()
            
            # Check if this event is still the current one
            if self._pending.get(identity_key) is event:
                del self._pending[identity_key]
                self._processing[identity_key] = event
                return event
            # Otherwise, this event was replaced; skip it

    def mark_done(self, event: Event) -> None:
        """Mark an event as done processing."""
        identity_key = event.get_identity_key()
        if self._processing.get(identity_key) is event:
            del self._processing[identity_key]
```

**重複制御のシーケンス例**:

```
時刻  アクション
─────────────────────────────────────────────────
0ms   チャンネルA更新イベント① enqueue (key=ch:A)
      → _pending["ch:A"] = ①, キューに①追加
      
50ms  チャンネルA更新イベント② enqueue (key=ch:A)
      → _pending["ch:A"] = ② に上書き, キューに②追加
      
100ms dequeue() → キューから①取り出し
      → _pending["ch:A"] は② なので①はスキップ
      
100ms dequeue() → キューから②取り出し
      → _pending["ch:A"] は② なので処理開始
      
結果: イベント②のみ処理される（①はスキップ）
```

#### FR-EVENT-004: 遅延イベントと自己発火

| 項目 | 内容 |
|------|------|
| 概要 | ボットが自分自身でイベントを発火でき、遅延実行を指定できる |
| 優先度 | 高 |
| フェーズ | Phase 2 |

**遅延イベントの仕組み**:

```
現在時刻: 10:00
ボットが delay=30分 でイベントを発火
  → EventQueueに delay=1800秒 で enqueue
  → 10:30 にキューに追加され処理される
```

**ツール定義**:

```python
from strands import tool
from typing import Optional

@tool
def emit_event(
    event_type: str,
    payload: str,
    delay: Optional[str] = None,
    identity_key: Optional[str] = None,
) -> str:
    """Emit a new event to be processed later.

    Use this to schedule future actions or remind yourself to do something.
    If identity_key is provided and an event with the same key is pending,
    the old event will be cancelled and replaced.

    Args:
        event_type: Type of event (e.g., "self_triggered", "reminder")
        payload: JSON string containing event data
        delay: Optional delay before processing (e.g., "30m", "2h", "1d")
        identity_key: Optional key for duplicate control
    """
    event = create_event(event_type, payload, identity_key)
    delay_seconds = parse_delay(delay) if delay else None
    await event_queue.enqueue(event, delay=delay_seconds)
    
    if delay:
        return f"Event {event.id} scheduled to fire in {delay}"
    else:
        return f"Event {event.id} emitted immediately"
```

**ユースケース例**:

| シナリオ | delay | identity_key | 説明 |
|----------|-------|--------------|------|
| 「後で声かけよう」 | 2h | `remind:{user_id}` | 2時間後にリマインド（重複はマージ） |
| 「明日確認しよう」 | 1d | `check:{topic}` | 翌日に自己発火 |
| 「少し間を置いて返信」 | 5m | `reply:{channel}` | 自然な間を作る |
| 定期的な振り返り | - | `reflect` | スケジューラーから定期発火 |

#### FR-EVENT-002: Pingイベント処理

| 項目 | 内容 |
|------|------|
| 概要 | 最小限のイベント処理として、Pingを受信し処理する |
| 優先度 | 必須 |
| フェーズ | Phase 1 |

**受け入れ条件**:
- Pingイベントを受信できる
- Agent Loopが起動する
- ツールがない場合、何も出力せずに終了する
- 処理完了がログに記録される

### 3.2 Agent Loop

#### FR-AGENT-001: 基本Agent Loop

| 項目 | 内容 |
|------|------|
| 概要 | イベントを受けて思考し、必要に応じてツールを呼び出す |
| 優先度 | 必須 |
| フェーズ | Phase 1 |

**処理フロー**:

```
1. イベント受信
2. コンテキスト構築
   - system_prompt = 固定プロンプト（設定ファイル） + 動的プロンプト（DB） + 記憶
   - tools = 利用可能なツール一覧
   - query_prompt = イベントタイプに応じたクエリ生成
3. Agent生成・実行
4. 結果をログに記録
5. 完了
```

**実装イメージ**:

```python
async def process(event: Event) -> None:
    # 1. system_prompt構築
    #    - 固定プロンプト: 設定ファイルから読み込み
    #    - 動的プロンプト: DBから読み込み（自己改善で変更される部分）
    #    - 記憶: 三層メモリ（working, short-term, long-term）の内容
    system_prompt = build_system_prompt(event)
    
    # 2. ツール一覧
    tools = get_available_tools()
    
    # 3. イベントタイプごとのクエリ生成
    #    - Slack MESSAGEならメッセージ内容を含むクエリ
    #    - PINGなら単純な起動通知
    query_prompt = build_query_prompt(event)
    
    # 4. Agent生成（毎回新規作成、session managerは使用しない）
    agent = Agent(
        model=model_id,
        system_prompt=system_prompt,
        tools=tools,
    )
    
    # 5. 実行（toolのstateを渡す）
    result = await agent.invoke_async(query_prompt, **invocation_state)
    
    # 6. ログ記録
    logger.info(f"Event {event.id} processed", result=result)
```

**設計上の決定事項**:

| 項目 | 決定 | 理由 |
|------|------|------|
| Agent生成 | 毎回新規作成 | Working Memoryを単一Loop内に限定するため |
| Session Manager | 使用しない | 状態管理はDB + toolのstateで行う |
| 記憶の注入 | system_promptに含める | LLMが常に記憶を参照できるようにするため |

**system_prompt の構成**:

```
┌─────────────────────────────────────────┐
│           system_prompt                 │
├─────────────────────────────────────────┤
│ 1. 固定プロンプト（設定ファイル）         │
│    - ボットの基本的な性格・役割          │
│    - 行動指針                           │
│    - ツールの使い方ガイド               │
├─────────────────────────────────────────┤
│ 2. 動的プロンプト（DB）                  │
│    - 自己改善で追加/変更された指示       │
├─────────────────────────────────────────┤
│ 3. 記憶（三層メモリ）                    │
│    - Long-term: 永続的な知識・人物情報   │
│    - Short-term: 最近の会話文脈          │
│    - Working: 現在の処理に必要な情報     │
└─────────────────────────────────────────┘
```

**build_query_prompt の構造**:

```python
def build_query_prompt(event: Event) -> str:
    """イベントタイプに応じたクエリを生成する"""
    handler = get_handler(event.type)
    return handler.build_query(event)

# ハンドラの例
class PingEventHandler:
    def build_query(self, event: Event) -> str:
        return "System ping received. Check your status and decide if any action is needed."

class SlackMessageEventHandler:
    def build_query(self, event: Event) -> str:
        payload = event.payload
        return f"""
New message received:
- From: {payload['user_name']} ({payload['user_id']})
- Channel: {payload['channel_name']}
- Text: {payload['text']}

Respond appropriately based on the context and your memory of this person.
"""
```

#### FR-AGENT-002: ツール呼び出し

| 項目 | 内容 |
|------|------|
| 概要 | Agent Loopからツールを呼び出し、外部世界と相互作用する |
| 優先度 | 必須 |
| フェーズ | Phase 2 |

**ツール定義方式（strands-agents）**:

strands-agentsでは `@tool` デコレータを使用してツールを定義する。docstringとtype hintsから自動的にツール仕様が生成される。

```python
from strands import tool

@tool
def post_slack_message(channel: str, text: str) -> str:
    """Post a message to a Slack channel.

    Args:
        channel: The channel ID or name to post to
        text: The message text to post
    """
    # 実装
    result = slack_client.chat_postMessage(channel=channel, text=text)
    return f"Message posted at {result['ts']}"
```

**デコレータの仕様**:

| 要素 | 抽出元 | 説明 |
|------|--------|------|
| ツール名 | 関数名 | `post_slack_message` |
| 説明 | docstring最初の段落 | LLMがツールを理解するために使用 |
| パラメータ | type hints + Args セクション | 型と説明を自動抽出 |

**名前・説明のオーバーライド**:

```python
@tool(name="slack_post", description="Slackにメッセージを投稿する")
def post_slack_message(channel: str, text: str) -> str:
    ...
```

**戻り値の形式**:

単純な値を返すと自動的にテキストレスポンスに変換される。詳細な制御が必要な場合は `ToolResult` 形式の辞書を返す:

```python
from typing import TypedDict, Literal

class ToolResultContent(TypedDict, total=False):
    text: str
    json: dict

class ToolResult(TypedDict):
    status: Literal["success", "error"]
    content: list[ToolResultContent]

@tool
def post_slack_message(channel: str, text: str) -> ToolResult:
    """Post a message to a Slack channel.

    Args:
        channel: The channel ID or name to post to
        text: The message text to post
    """
    try:
        result = slack_client.chat_postMessage(channel=channel, text=text)
        return {
            "status": "success",
            "content": [{"text": f"Message posted at {result['ts']}"}]
        }
    except Exception as e:
        return {
            "status": "error",
            "content": [{"text": f"Failed to post: {e}"}]
        }
```

**Agentへの登録**:

```python
from strands import Agent

agent = Agent(
    tools=[
        post_slack_message,
        add_slack_reaction,
        update_person_memory,
        emit_event,
    ]
)
```

### 3.3 記憶システム

#### FR-MEMORY-001: 三層記憶アーキテクチャ

| 項目 | 内容 |
|------|------|
| 概要 | Working / Short-term / Long-term の三層で記憶を管理する |
| 優先度 | 必須 |
| フェーズ | Phase 2 |

**各層の定義**:

| 層 | 保持期間 | 容量 | 用途 |
|----|----------|------|------|
| Working Memory | 単一Agent Loop内 | 制限なし | 現在の処理コンテキスト |
| Short-term Memory | 数時間〜数日 | 制限あり | 最近の会話、一時的な文脈 |
| Long-term Memory | 永続 | 制限あり | 個人の特徴、重要な出来事、学習内容 |

#### FR-MEMORY-002: 個人認識

| 項目 | 内容 |
|------|------|
| 概要 | 複数コミュニティを跨いで個人を認識・記憶する |
| 優先度 | 高 |
| フェーズ | Phase 2 |

**データモデル**:

```python
class Person(BaseModel):
    id: str                              # 内部識別子
    identities: list[Identity]           # 各プラットフォームでのID
    name: Optional[str] = None           # 認識している名前
    first_seen: datetime
    last_seen: datetime
    memory: str = ""                     # この人に関するメモ（自由記述）

class Identity(BaseModel):
    platform: str                        # "slack", "discord", etc.
    platform_user_id: str
    display_name: Optional[str] = None
```

**メモリ設計の考え方**:

`memory` フィールドは単一の文字列として、LLMが自由に編集できる形式とする。

```
# 例: Person.memory の内容
"""
- ソフトウェアエンジニア、Kubernetes好き
- 朝型で早朝によく発言する
- 猫を飼っている（名前は聞いていない）
- 2026-01-10: 転職活動中と言っていた（他の人には言わないでと頼まれた）
- 2026-01-15: 新しい仕事が決まったと報告
"""
```

**利点**:
- LLMが自然言語で記憶を管理できる
- 構造化されすぎず、柔軟な情報を保持できる
- 秘密情報も文脈として記載し、LLMが判断して扱う

**記憶更新ツール**:

```python
from strands import tool

@tool
def update_person_memory(person_id: str, new_memory: str) -> str:
    """Update the memory notes for a person.

    The memory is a free-form text that you can edit however you want.
    Include things you learn about this person, their preferences,
    and any confidential information they shared (note it as confidential).

    Args:
        person_id: The unique identifier of the person
        new_memory: The complete new memory text (replaces existing)
    """
    # 実装
    update_memory_in_db(person_id, new_memory)
    return f"Memory updated for person {person_id}"
```

**クロスプラットフォーム統合**:

同一人物が複数プラットフォームに存在する場合、記憶を統合する。

```
例: 
  SlackのユーザーA と DiscordのユーザーB が同一人物と判明
  → Person.identities に両方を登録
  → 記憶は統合され、どちらのプラットフォームでも活用される
```

統合の判断基準（将来的に自動化を検討）:
- 管理者による明示的な紐付け
- 同一のメールアドレス
- 本人による申告

#### FR-MEMORY-003: 記憶プライバシーポリシー

| 項目 | 内容 |
|------|------|
| 概要 | 記憶の取り扱いに関するポリシーを定義する |
| 優先度 | 高 |
| フェーズ | Phase 2 |

**基本方針**:

- ボットはパブリックな場（チャンネル等）での発言を対象とする
- プライベートチャット機能は提供しない
- 記憶に制限は設けず、観測した情報は記憶の対象となる

**秘密の取り扱い**:

- ユーザーが「他の人に言わないで」等と依頼した場合、その旨をメモリに記載
- LLMはメモリの文脈から秘密情報を判断し、他のユーザーとの会話で出力しない
- **管理者はデータベースを通じて全ての記憶を閲覧可能**

**管理者の権限**:

| 権限 | 説明 |
|------|------|
| 記憶の閲覧 | 全ユーザーの全記憶を閲覧可能 |
| 記憶の編集 | 任意の記憶を直接編集可能 |
| 記憶の削除 | 任意の記憶を削除可能 |
| 統計の確認 | 記憶の量、傾向などを確認可能 |

### 3.4 自己改善

#### FR-IMPROVE-001: 自己改善フレームワーク

| 項目 | 内容 |
|------|------|
| 概要 | ボットがシステムプロンプトを調整することで振る舞いを改善する |
| 優先度 | 中 |
| フェーズ | Phase 3 |

**改善可能な対象**:
- システムプロンプトの調整（口調、反応傾向、判断基準など）

**改善対象外**（コード変更は行わない）:
- ツールの実装変更
- 記憶システムのロジック変更
- イベント処理の変更

**自己改善の仕組み**:

```python
class SelfImprovement(BaseModel):
    """ボットによるプロンプト調整の記録"""
    id: str
    target: Literal["system_prompt"]
    previous_value: str
    new_value: str
    reason: str                      # なぜこの変更が必要か
    trigger_event_id: Optional[str]  # きっかけとなったイベント
    applied_at: datetime
```

**運用フロー**:

1. ボットが改善を実行
2. 変更内容がログに出力される
3. 管理者は必要に応じてログを確認
4. 問題のある改善は管理者がDBを直接編集して介入

```
# ログ出力例
[2026-01-16 10:30:00] SELF_IMPROVEMENT: system_prompt updated
  reason: "挨拶が堅すぎると感じたため、よりカジュアルな口調に調整"
  diff: -"こんにちは。何かお手伝いできることはありますか？"
        +"やあ！何か手伝おうか？"
```

**ツール定義**:

```python
from strands import tool

@tool
def update_system_prompt(new_prompt: str, reason: str) -> str:
    """Update your own system prompt to improve your behavior.

    Use this when you notice patterns in your interactions that could be improved.
    Changes are applied immediately and logged for administrator review.

    Args:
        new_prompt: The complete new system prompt text
        reason: Explanation of why this change is needed
    """
    # 実装: 変更を適用しログに記録
    apply_prompt_update(new_prompt, reason)
    return f"System prompt updated. Reason: {reason}"
```

---

## 4. 非機能要件

### 4.1 性能

| ID | 要件 | 目標値 |
|----|------|--------|
| NFR-PERF-001 | イベント処理開始までの遅延 | < 100ms |
| NFR-PERF-002 | 単純なAgent Loop完了時間 | < 5s |
| NFR-PERF-003 | 同時処理可能イベント数 | 1（シングルスレッド） |

**設計方針**:
- 単一インスタンスで動作（複数インスタンスは想定しない）
- イベントは逐次処理（同時処理なし）
- シンプルさを優先し、スケーラビリティは将来の課題とする

### 4.2 可用性

| ID | 要件 | 目標値 |
|----|------|--------|
| NFR-AVAIL-001 | システム稼働率 | 99%（月間） |
| NFR-AVAIL-002 | 計画外停止からの復旧 | < 5分 |

### 4.3 拡張性

| ID | 要件 |
|----|------|
| NFR-EXT-001 | 新しいイベントタイプを追加可能 |
| NFR-EXT-002 | 新しいツールをプラグインとして追加可能 |
| NFR-EXT-003 | 新しいプラットフォーム（Slack以外）を追加可能 |

### 4.4 セキュリティ

| ID | 要件 |
|----|------|
| NFR-SEC-001 | 認証情報は環境変数またはSecretで管理 |
| NFR-SEC-002 | 記憶データは暗号化して保存 |
| NFR-SEC-003 | ツール実行は権限チェックを経由 |

### 4.5 運用性

| ID | 要件 |
|----|------|
| NFR-OPS-001 | 構造化ログ出力（JSON形式） |
| NFR-OPS-002 | ヘルスチェックエンドポイント提供 |
| NFR-OPS-003 | メトリクス公開（Prometheus形式） |

---

## 5. 技術スタック

### 5.1 コア技術

| 領域 | 技術 | 用途 |
|------|------|------|
| 言語 | Python 3.12+ | メイン実装言語 |
| 非同期 | asyncio | イベント駆動処理 |
| Agent Framework | strands-agents | LLMエージェント実装 |
| LLM Gateway | LiteLLM | 複数LLMプロバイダ対応 |
| ORM | SQLModel | データモデル定義 |
| Database Driver | aiosqlite | 非同期SQLite |

### 5.2 インフラ

| 領域 | 技術 | 備考 |
|------|------|------|
| コンテナ | Docker | アプリケーションパッケージング |
| オーケストレーション | Kubernetes | ホームクラスタにデプロイ |
| ストレージ | SQLite (Longhorn PVC) | 記憶の永続化 |

### 5.3 外部連携

| プラットフォーム | SDK/API | フェーズ |
|------------------|---------|----------|
| Slack | slack-sdk (async) | Phase 2 |
| Discord | discord.py | 将来 |
| Email | aiosmtplib | 将来 |

### 5.4 LLM設定

LLMの設定はLiteLLMに渡すパラメータをそのまま記述できる形式とする。これにより、LiteLLMがサポートする任意のプロバイダ・モデルを利用可能。

**設定ファイル形式** (YAML):

```yaml
llm:
  # Agent Loopで使用するメインLLM
  agent:
    model_id: "anthropic/claude-sonnet-4-20250514"
    params:
      temperature: 0.7
      max_tokens: 4096
    client_args:
      api_key: ${ANTHROPIC_API_KEY}

  # 記憶の要約・整理に使用するLLM（コスト最適化用に分離可能）
  memory:
    model_id: "openai/gpt-4o-mini"
    params:
      temperature: 0.3
      max_tokens: 2048
    client_args:
      api_key: ${OPENAI_API_KEY}

  # 自己改善の提案生成に使用するLLM
  improvement:
    model_id: "anthropic/claude-sonnet-4-20250514"
    params:
      temperature: 0.5
      max_tokens: 4096
    client_args:
      api_key: ${ANTHROPIC_API_KEY}
```

**設定項目**:

| 項目 | 必須 | 説明 |
|------|------|------|
| `model_id` | ✓ | LiteLLM形式のモデル識別子 (`provider/model`) |
| `params` | | LLM呼び出し時のパラメータ (`temperature`, `max_tokens`, etc.) |
| `client_args` | | LiteLLMクライアント初期化時の引数 (`api_key`, `api_base`, etc.) |

**環境変数展開**:

`${ENV_VAR}` 形式で環境変数を参照可能。これによりSecretとの連携が容易になる。

**実装イメージ**:

```python
from litellm import acompletion

class LLMConfig(BaseModel):
    model_id: str
    params: dict = {}
    client_args: dict = {}

async def call_llm(config: LLMConfig, messages: list[dict]) -> str:
    response = await acompletion(
        model=config.model_id,
        messages=messages,
        **config.params,
        **config.client_args,
    )
    return response.choices[0].message.content
```

**用途別LLM分離の理由**:

| 用途 | 要件 | 推奨 |
|------|------|------|
| Agent Loop | 高い推論能力、ツール呼び出し | 高性能モデル |
| 記憶処理 | 要約・分類、大量処理 | コスト効率の良いモデル |
| 自己改善 | 慎重な判断、自己認識 | 高性能モデル |

---

## 6. 実装フェーズ

### Phase 1: 最小限の骨格（MVP）

**目標**: イベントを受信してAgent Loopが動作することを確認する

**実行環境**: ローカル（Python直接実行）

**スコープ**:
- [ ] イベント受信基盤（Pingのみ）
- [ ] EventQueue（重複制御、遅延エンキュー）
- [ ] 基本Agent Loop（ツールなし）
- [ ] ログ出力
- [ ] 設定ファイル読み込み（YAML）

**完了条件**:
- Pingイベントを送信すると、Agent Loopが起動し、ログに記録されて終了する
- 同じidentity_keyのイベントを連続送信すると、最新の1件のみ処理される
- `python -m myao3` でローカル実行できる

### Phase 2: 記憶とコミュニケーション

**目標**: Slackでメッセージを受信し、記憶を持ち、返答できる

**実行環境**: ローカル → Kubernetes

**スコープ**:
- [ ] Slack連携（メッセージ受信）
- [ ] 三層記憶システム
- [ ] 個人認識
- [ ] メッセージ送信ツール
- [ ] リアクションツール
- [ ] Dockerイメージ作成
- [ ] Kubernetes Deployment

**完了条件**:
- Slackでメンションされると、文脈を踏まえた返答ができる
- 同じ人との会話履歴を記憶している
- Kubernetesクラスタ上で稼働している

### Phase 3: 自律性の向上

**目標**: より自律的に判断し、自己改善の基盤を持つ

**スコープ**:
- [ ] Presenceイベント（オンライン/オフライン検知）
- [ ] スケジュールイベント（定期的な自己振り返り）
- [ ] 記憶の自動整理
- [ ] 自己改善フレームワーク（基盤のみ）

**完了条件**:
- ボットが自発的に（メンションなしで）会話を始めることがある
- 定期的に記憶を整理し、重要な情報を長期記憶に移行する

### Phase 4以降: 拡張

- 複数プラットフォーム対応
- 高度な自己改善
- 感情認識
- グループダイナミクスの理解

---

## 7. 用語集

| 用語 | 定義 |
|------|------|
| Agent Loop | イベントを受けてLLMが思考し、ツールを呼び出すまでの一連の処理サイクル |
| Working Memory | 単一のAgent Loop内でのみ有効な一時的な記憶 |
| Short-term Memory | 数時間から数日保持される中期的な記憶 |
| Long-term Memory | 永続的に保持される長期的な記憶 |
| ツール | ボットが外部世界と相互作用するための明示的なインターフェース |
| イベント | 外部世界からボットに届く情報の単位 |
| identity_key | イベントの重複制御に使用するキー。同じキーのイベントはマージされる |
| EventQueue | 重複制御と遅延エンキューをサポートするインメモリキュー |
| 遅延イベント | `enqueue(event, delay=...)` で遅延指定されたイベント |
| 自己発火 | ボット自身が `emit_event` ツールで新しいイベントを生成すること |
| invocation_state | strands-agentsのツール間で共有される状態オブジェクト |
| system_prompt | 固定プロンプト + 動的プロンプト + 記憶を合成したLLMへの指示 |
| query_prompt | イベントタイプに応じて生成されるユーザークエリ |

---

## 8. 変更履歴

| バージョン | 日付 | 変更内容 |
|------------|------|----------|
| 0.1.0 | 2026-01-16 | 初版作成 |
| 0.2.0 | 2026-01-16 | ツール命名規則、自己改善範囲、記憶プライバシーポリシー、クロスプラットフォーム統合を追加 |
| 0.3.0 | 2026-01-16 | LLM設定（LiteLLM kwargs形式）を追加 |
| 0.4.0 | 2026-01-16 | プロジェクト名をmyao3に変更、PersonMemoryを単一strに簡素化、自己改善の承認フロー削除（ログ出力のみ）、遅延イベント・自己発火機能を追加 |
| 0.5.0 | 2026-01-16 | ツール定義をstrands-agents形式（@toolデコレータ、docstring、type hints）に修正 |
| 0.6.0 | 2026-01-16 | Phase 1をローカル実行のみに変更、Docker/K8sはPhase 2に移動 |
| 0.7.0 | 2026-01-16 | 単一インスタンス・逐次処理に簡素化（同時処理数1、複数インスタンス非対応） |
| 0.8.0 | 2026-01-16 | Agent Loop処理フロー詳細化（system_prompt構成、build_query_prompt、invocation_state、session manager不使用） |
| 0.9.0 | 2026-01-16 | Event.identity_keyによる重複制御、EventQueue（重複マージ、遅延エンキュー、処理状態トラッキング）を追加 |
| 0.10.0 | 2026-01-16 | Event.delayフィールドを削除（delayはenqueue時のパラメータとして指定） | |

---

## 9. 未決定事項（TBD）

- [ ] 記憶の容量制限の具体的な数値
- [ ] 同一人物の自動判定アルゴリズム（Phase 2以降で検討）
