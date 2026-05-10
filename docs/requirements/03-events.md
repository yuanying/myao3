## 3.1 イベント処理

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
