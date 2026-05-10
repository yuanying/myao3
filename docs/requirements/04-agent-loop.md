## 3.2 Agent Loop

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
