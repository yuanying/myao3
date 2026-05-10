# myao3 要求仕様書

**バージョン**: 0.13.0
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
│  │  - read_wiki_page(page_path)                    │   │
│  │  - write_wiki_page(page_path, content)          │   │
│  │  - search_wiki(query)                           │   │
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
post_slack_message(workspace_id, channel, text)
add_slack_reaction(workspace_id, channel, timestamp, emoji)
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
   - system_prompt = Markdownプロンプト群 + Short-term要約 + 実行時コンテキスト
   - tools = 利用可能なツール一覧
   - query_prompt = イベントタイプに応じたクエリ生成
3. 会話単位のSessionを取得または作成
4. Agent生成・実行
5. Sessionへ会話履歴を保存
6. 結果をログに記録
7. 完了
```

**実装イメージ**:

```python
async def process(event: Event) -> None:
    # 1. system_prompt構築
    #    - Markdownプロンプト群: prompts/*.md から固定順で読み込み
    #    - Dynamic Notes: prompts/dynamic/*.md から読み込み
    #    - 実行時コンテキスト: workspace, timezone, event metadata など
    #    - 記憶: Short-term は要約のみ、Long-term は Wiki ツールで段階的取得
    system_prompt = build_system_prompt(event)
    
    # 2. ツール一覧
    tools = get_available_tools()
    
    # 3. イベントタイプごとのクエリ生成
    #    - Slack MESSAGEならメッセージ内容を含むクエリ
    #    - PINGなら単純な起動通知
    query_prompt = build_query_prompt(event)
    
    # 4. 会話単位のSession取得
    #    - Slack channel: slack:{workspace_id}:channel:{channel_id}
    #    - その他チャット: {source}:{conversation_id}
    session_id = build_session_id(event)
    session_manager = get_session_manager(session_id)

    # 5. Agent生成（Agentインスタンスは処理ごとに作成し、会話履歴はSessionから復元）
    agent = Agent(
        model=model_id,
        system_prompt=system_prompt,
        tools=tools,
        session_manager=session_manager,
    )
    
    # 6. 実行（toolのstateを渡す）
    result = await agent.invoke_async(query_prompt, **invocation_state)
    
    # 7. ログ記録
    logger.info(f"Event {event.id} processed", result=result)
```

**設計上の決定事項**:

| 項目 | 決定 | 理由 |
|------|------|------|
| Agent生成 | 処理ごとにインスタンス生成 | モデル・ツール・実行時コンテキストをイベントごとに構築するため |
| Session Manager | 会話単位で使用 | Slack channel やチャット会話ごとに履歴を継続するため |
| Session ID | source + conversation scope | 複数Slack Workspaceや複数チャットを混同しないため |
| 記憶の注入 | Long-term はツール呼び出しで段階的取得 | コンテキストウィンドウ節約、LLMが必要な情報を自律判断 |

**Session ID の例**:

| 会話 | session_id |
|------|------------|
| Slack channel | `slack:{workspace_id}:channel:{channel_id}` |
| Discord channel | `discord:{guild_id}:channel:{channel_id}` |
| Email thread | `email:{thread_id}` |

Slack の `channel_id` や `user_id` は workspace 内で解釈する。複数の Slack Workspace に属する場合があるため、Slack由来の session_id と記憶メモには必ず `workspace_id` を含める。SlackではSession粒度をchannelに固定し、スレッド内の会話も channel Session に含める。

**system_prompt の構成**:

system_prompt は、管理者が直接読めて編集できる Markdown ファイル群を固定順で合成して生成する。DBに巨大な完成済みプロンプト全文や有効/無効付きのプロンプト断片を保存しない。プロンプトの原本は常にプレーンテキストファイルとする。

```
┌─────────────────────────────────────────┐
│           system_prompt                 │
├─────────────────────────────────────────┤
│ 1. Core Prompt                          │
│    - 不変の役割、Agent Loop、外部出力制約 │
├─────────────────────────────────────────┤
│ 2. Personality / Soul                   │
│    - myao3 の人格、口調、距離感          │
├─────────────────────────────────────────┤
│ 3. Behavior Policy                      │
│    - 反応判断、沈黙、遅延、会話深度      │
├─────────────────────────────────────────┤
│ 4. Tooling                              │
│    - 利用可能ツールと使用ルール          │
├─────────────────────────────────────────┤
│ 5. Memory Policy                        │
│    - Short-term は要約のみ注入           │
│    - Long-term は Wiki ツールで段階的取得 │
├─────────────────────────────────────────┤
│ 6. Safety                               │
│    - 権限、プライバシー、過剰介入防止    │
├─────────────────────────────────────────┤
│ 7. Dynamic Notes                        │
│    - 自己改善で追加された限定的な行動メモ │
├─────────────────────────────────────────┤
│ 8. Runtime Context                      │
│    - workspace, timezone, event metadata │
└─────────────────────────────────────────┘
```

**プロンプトファイル構成**:

```text
prompts/
  core.md          # 不変の基本原則、内部思考、ツール経由でのみ行動
  soul.md          # myao3 の人格、口調、「みんなの友達」としての振る舞い
  behavior.md      # 反応する/しない、遅延、沈黙、リアクション判断
  tools.md         # ツール使用方針、禁止事項、ツール選択基準
  memory.md        # 記憶ツールの使い方、長期記憶を直接注入しない方針
  safety.md        # 権限、プライバシー、危険操作、過剰介入防止
  self_update.md   # 自己改善の対象、手順、制限
  runtime.md.tmpl  # 実行時コンテキストのテンプレート
  dynamic/
    behavior_notes.md  # 自己改善で追記される短い行動メモ
```

**合成ルール**:

| 項目 | ルール | 理由 |
|------|--------|------|
| セクション順 | 固定 | モデル入力を安定させ、差分確認を容易にする |
| 原本 | Markdownファイル | 管理者が直接読めて編集できる |
| 自己改善 | 許可されたMarkdownファイルを直接変更 | プレーンテキストを唯一の原本にする |
| 変更履歴 | 構造化ログに記録 | DBを使わず、後から理由と差分を確認できるようにする |
| Long-term Memory | system_promptに一括注入しない | コンテキストウィンドウ節約、必要時取得 |
| Short-term Memory | 直近文脈の要約のみ注入 | 会話連続性とサイズ制御の両立 |
| Skills/専門手順 | 一覧のみ注入し、本文は必要時に読む | base promptを小さく保つ |
| 変動情報 | 必要最小限のみ注入 | prompt cacheと再現性を保つ |

**Prompt Mode**:

| mode | 用途 | 含める内容 |
|------|------|------------|
| `full` | 通常のAgent Loop | 全セクション、Dynamic Notes、Short-term要約 |
| `minimal` | sub-agent、単発の補助処理 | Core、Tooling、Safety、Runtime Contextのみ |
| `none` | デバッグ、特殊用途 | 最小限のidentity行のみ |

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
- Workspace: {payload['workspace_name']} ({payload['workspace_id']})
- From: {payload['user_name']} ({payload['user_id']})
- Channel: {payload['channel_name']} ({payload['channel_id']})
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
def post_slack_message(workspace_id: str, channel: str, text: str) -> str:
    """Post a message to a Slack channel.

    Args:
        workspace_id: Slack workspace/team ID
        channel: The channel ID or name to post to
        text: The message text to post
    """
    # 実装
    client = slack_client_for(workspace_id)
    result = client.chat_postMessage(channel=channel, text=text)
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
def post_slack_message(workspace_id: str, channel: str, text: str) -> str:
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
def post_slack_message(workspace_id: str, channel: str, text: str) -> ToolResult:
    """Post a message to a Slack channel.

    Args:
        workspace_id: Slack workspace/team ID
        channel: The channel ID or name to post to
        text: The message text to post
    """
    try:
        client = slack_client_for(workspace_id)
        result = client.chat_postMessage(channel=channel, text=text)
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
        read_wiki_page,
        write_wiki_page,
        search_wiki,
        list_wiki_pages,
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

| 層 | 保持期間 | 容量 | 用途 | 実装 |
|----|----------|------|------|------|
| Working Memory | 単一Agent Loop内 | 制限なし | 現在の処理コンテキスト | LLMのコンテキストウィンドウ |
| Short-term Memory | 数時間〜数日 | 制限あり | 最近の会話、一時的な文脈 | Strands Session（会話単位） |
| Long-term Memory | 永続 | 制限あり | 個人の特徴、重要な出来事、学習内容 | LLM Wiki（ファイルシステム） |

**Session → Long-term Memory 2段階方式**:

```
ループ内（随時）
  → 会話単位の Strands Session にメッセージ、tool call、tool result を保存

毎日夜中（日次整理）
  → 前日分の Session を読み、notes/YYYY-MM-DD.md に要約・重要事項を保存
  → notes/ を読み、people/, topics/, communities/, self.md を更新
  → index.md を最新状態に更新
```

#### FR-MEMORY-002: 個人認識

| 項目 | 内容 |
|------|------|
| 概要 | 複数コミュニティを跨いで個人を認識・記憶する |
| 優先度 | 高 |
| フェーズ | Phase 2 |

**データモデル（Wiki ページ）**:

人物情報は `people/{canonical_slug}.md` が canonical source。人物認識のためのDBモデルは持たない。

```markdown
# Person: alice

## Identity
- Slack: U1234567 (@alice)
- Discord: alice_dev (確認: 2026-05-04)
- ※未確認候補: matrix上の @alice:example.org

## Personality & Communication Style
（LLM 自由記述）

## Interests & Expertise
（LLM 自由記述）

## Relationship
（このボットとの関係）

## Conversation Summaries
### 2026-05-04
（その日の会話の要点）

## Notes
（秘密・特記事項など）
```

**Person 識別の考え方**:

```
初回遭遇（Slack で @alice に会う）
  → notes/YYYY-MM-DD.md に "Slack U1234567 @alice: ..." を記録

夜間整理
  → people/alice.md を作成（なければ）
  → ## Identity に "Slack: U1234567 (@alice)" を追記
  → index.md の People セクションを更新

別プラットフォームで alice_dev として遭遇
  → notes/ に記録 → 夜間整理で同一人物と判断 → ## Identity に追記
```

**方針**:
- 人物情報はファイルベース、プラットフォーム非依存
- 複数アカウントは ## Identity セクションに列挙
- 同一人物判定・マージは夜間整理で LLM が実施

#### FR-MEMORY-004: LLM Wiki

| 項目 | 内容 |
|------|------|
| 概要 | Long-term Memory をファイルシステム上の Markdown Wiki として実装する |
| 優先度 | 高 |
| フェーズ | Phase 2 |

**段階的開示（Progressive Disclosure）**:

Wiki コンテンツは system_prompt に一括埋め込みしない。LLM がツールで「必要な情報を必要な時だけ」取得する。

```
Agent Loop 開始
        │
        ├─ [system_prompt] 「長期記憶が必要なときは
        │   read_wiki_page("index") から始めて
        │   必要なページを読んでください」
        │
        ├─ read_wiki_page("index")      ← 誰・何を知っているかの概要
        │     → 今の文脈に関係ありそうな人物・話題を確認
        │
        ├─ read_wiki_page("people/alice")  ← alice に言及された場合のみ
        │
        └─ read_wiki_page("topics/kubernetes")  ← Kubernetes が話題の場合のみ
```

**Wiki ディレクトリ構造**:

```
data/wiki/
├── index.md                    # エントリーポイント（夜間整理で更新）
├── notes/                      # 短期メモ（ループ内で随時更新）
│   └── YYYY-MM-DD.md           # 日付ごとの出来事・プラットフォーム ID を含む生メモ
├── people/                     # 長期記憶: 人物ページ（プラットフォーム非依存）
│   └── {canonical_slug}.md     # e.g. alice.md, taro-yamada.md
├── topics/                     # 長期記憶: 話題・概念
│   └── {slug}.md
├── communities/                # 長期記憶: コミュニティ
│   └── slack/
│       ├── index.md
│       └── {channel_id}.md
└── self.md                     # ボット自身の人格・成長記録
```

**ツール定義**:

```python
@tool
def read_wiki_page(page_path: str) -> str:
    """Read a wiki page for long-term memory recall.
    Start with "index" to see what knowledge is available.
    Args:
        page_path: Path within wiki (e.g., "index", "people/alice", "notes/2026-05-04")
    """

@tool
def write_wiki_page(page_path: str, content: str) -> str:
    """Write or update a wiki page to store memory.
    Args:
        page_path: Path within wiki
        content: Full markdown content
    """

@tool
def search_wiki(query: str, category: str | None = None) -> str:
    """Search wiki pages for relevant information.
    Args:
        query: Search keywords
        category: Optional filter ("people", "topics", "communities", "notes")
    """

@tool
def list_wiki_pages(category: str | None = None) -> str:
    """List wiki pages, optionally filtered by category."""
```

#### FR-MEMORY-005: 日次記憶整理

| 項目 | 内容 |
|------|------|
| 概要 | 毎日深夜に会話Sessionを整理し、notes/・長期記憶ページ・index.md を更新する |
| 優先度 | 高 |
| フェーズ | Phase 2 |

**仕組み**:

FR-EVENT-004（遅延イベント・自己発火）を活用し、毎日 0:00 に `memory_consolidation` イベントを発火する。

```
日次整理フロー:
  1. 前日分の会話Sessionを読む
  2. notes/YYYY-MM-DD.md に会話要約・重要事項・未整理の観測を保存
  3. 関連する long-term ページを読む
  4. 同一人物判定 → 必要ならページをマージ
  5. people/, topics/, communities/, self.md を更新
  6. index.md を最新状態に更新
```

**index.md フォーマット**:

```markdown
# Wiki Index

*Last updated: 2026-05-04*

## Self
My personality and growth log → [self](self.md)

## People I Know
- [alice](people/alice.md) (Slack: @alice)
- [taro-yamada](people/taro-yamada.md) (Slack: @taro)

## Topics
- [kubernetes](topics/kubernetes.md)

## Communities
- [Slack workspace](communities/slack/index.md)

## Recent Notes
- [2026-05-04](notes/2026-05-04.md)
```

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
- **管理者は Session ファイルと Wiki ファイルを通じて全ての記憶を閲覧可能**

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

### 5.2 インフラ

| 領域 | 技術 | 備考 |
|------|------|------|
| コンテナ | Docker | アプリケーションパッケージング |
| オーケストレーション | Kubernetes | ホームクラスタにデプロイ |
| ストレージ (Session) | ファイルシステム (Longhorn PVC) | 会話単位の Strands Session 永続化 |
| ストレージ (Wiki) | ファイルシステム (Longhorn PVC) | Long-term Memory（Wiki）の永続化 |
| ストレージ (Prompt) | ファイルシステム (Longhorn PVC) | Markdownプロンプト原本の永続化 |

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
- 同じSlack channelやチャット会話のSessionを継続し、文脈を踏まえて返答できる
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
| Short-term Memory | 会話単位の Strands Session に保持され、日次整理で Long-term Memory に反映される中期的な記憶 |
| Long-term Memory | 永続的に保持される長期的な記憶 |
| ツール | ボットが外部世界と相互作用するための明示的なインターフェース |
| イベント | 外部世界からボットに届く情報の単位 |
| identity_key | イベントの重複制御に使用するキー。同じキーのイベントはマージされる |
| EventQueue | 重複制御と遅延エンキューをサポートするインメモリキュー |
| 遅延イベント | `enqueue(event, delay=...)` で遅延指定されたイベント |
| 自己発火 | ボット自身が `emit_event` ツールで新しいイベントを生成すること |
| invocation_state | strands-agentsのツール間で共有される状態オブジェクト |
| system_prompt | Markdownプロンプト群 + Dynamic Notes + Short-term要約 + 実行時コンテキストを固定順で合成したLLMへの指示 |
| query_prompt | イベントタイプに応じて生成されるユーザークエリ |
| LLM Wiki | ファイルシステム上の Markdown ファイル群で構成される Long-term Memory |
| 段階的開示 | LLM が必要な時だけ wiki ツールで情報を取得する方式（一括埋め込みしない） |
| 夜間整理 | 毎日深夜に会話Sessionと notes/ から long-term ページと index.md を更新するプロセス |
| canonical_slug | 人物ページのファイル名（例: alice, taro-yamada） |
| Prompt Mode | 用途に応じて system_prompt の含有セクションを切り替えるモード（full / minimal / none） |
| Dynamic Notes | 自己改善で追加され、system_prompt 合成時に限定的に注入される行動メモ |

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
| 0.10.0 | 2026-01-16 | Event.delayフィールドを削除（delayはenqueue時のパラメータとして指定） |
| 0.11.0 | 2026-05-04 | Long-term Memory を LLM Wiki 2段階方式に全面改訂（FR-MEMORY-001/002改訂、FR-MEMORY-004/005追加）、update_person_memory を write_wiki_page 等に置き換え、Section 2.1/3.2/5.2 更新 |
| 0.12.0 | 2026-05-10 | system_prompt をMarkdownプロンプト群の固定順合成方式へ変更し、自己改善を全文置換から限定的なprompt patch / dynamic note方式へ改訂 |
| 0.13.0 | 2026-05-10 | Agent Loop を会話単位の Strands Session 使用に変更し、DB/SQLite を技術スタックから削除。Slack は workspace_id を含む channel Session 単位で管理 |

---

## 9. 未決定事項（TBD）

- [ ] 記憶の容量制限の具体的な数値
- [ ] Wiki ページの最大サイズ・ページ数制限
- [ ] 同一人物の自動判定精度（夜間整理での LLM 判断のチューニング）
