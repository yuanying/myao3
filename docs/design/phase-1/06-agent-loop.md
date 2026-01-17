# 06. Agent Loop

## 概要

strands-agents と LiteLLM を使用した Agent Loop を実装する。イベントを受け取り、system_prompt と query_prompt を構築して LLM を呼び出す。Phase 1 ではツールなしで動作確認のみ行う。

## 依存タスク

- 01-project-setup.md
- 02-config.md
- 03-logging.md
- 05-event-queue.md

## 成果物

### ファイル配置

```
src/myao3/application/services/
├── __init__.py
└── agent_loop.py       # AgentLoop 実装

src/myao3/infrastructure/llm/
├── __init__.py
└── litellm_model.py    # LiteLLM モデルラッパー

src/myao3/application/handlers/
├── __init__.py
└── event_handlers.py   # EventHandler 実装
```

### AgentLoop クラス

**責務:**

- イベントを受け取り、LLM を呼び出す
- system_prompt と query_prompt を構築
- 結果をログに記録

**コンストラクタ引数:**

| 引数 | 型 | 説明 |
|------|-----|------|
| config | AgentConfig | Agent 設定 |
| logger | Logger | ロガー |

**メソッド:**

| メソッド | 引数 | 戻り値 | 説明 |
|---------|------|--------|------|
| process | event: Event | None | イベントを処理する |

### EventHandler パターン

イベントタイプごとに query_prompt を生成するハンドラーを実装する。

**EventHandler プロトコル:**

| メソッド | 引数 | 戻り値 | 説明 |
|---------|------|--------|------|
| build_query | event: Event | str | query_prompt を生成 |

**PingEventHandler:**

Ping イベント用のハンドラー。

**生成する query_prompt:**

```
System ping received. Check your status and decide if any action is needed.
```

### LLM 統合

strands-agents の Agent クラスと LiteLLMModel を使用する。

**Agent 生成:**

| 項目 | 値 |
|------|-----|
| model | LiteLLMModel（設定から構築） |
| system_prompt | config.yaml の agent.system_prompt |
| tools | []（Phase 1 はツールなし） |

**呼び出し:**

`agent.invoke_async(query_prompt)` で非同期実行。

### LLM モック機能

CI やテストで実際の LLM を呼び出さないよう、モック機能を提供する。

**環境変数:**

| 変数 | 値 | 説明 |
|------|-----|------|
| MOCK_LLM | true | モックモードを有効化 |

**モック時の動作:**

- 固定のレスポンスを返す
- API 呼び出しは行わない
- レスポンス例: "Mock LLM response for event: {event_id}"

## テストケース

### TC-06-001: AgentLoop の初期化

**手順:**
1. AgentConfig を作成
2. AgentLoop を初期化

**期待結果:**
- エラーなく初期化される

### TC-06-002: PingEvent の処理

**前提条件:** MOCK_LLM=true

**手順:**
1. AgentLoop を初期化
2. PingEvent を作成
3. process() を呼び出し

**期待結果:**
- エラーなく完了する
- ログに処理結果が記録される

### TC-06-003: PingEventHandler の query_prompt 生成

**手順:**
1. PingEventHandler を作成
2. PingEvent を作成
3. build_query() を呼び出し

**期待結果:**
- "System ping received..." という文字列が返される

### TC-06-004: LLM モックの動作

**前提条件:** MOCK_LLM=true

**手順:**
1. AgentLoop を初期化
2. イベントを処理
3. レスポンスを確認

**期待結果:**
- モック用の固定レスポンスが返される
- 実際の API 呼び出しは行われない

### TC-06-005: system_prompt の設定

**手順:**
1. config に system_prompt を設定
2. AgentLoop を初期化
3. Agent の system_prompt を確認

**期待結果:**
- config で指定した system_prompt が Agent に設定される

### TC-06-006: ログ出力の確認

**前提条件:** MOCK_LLM=true

**手順:**
1. AgentLoop を初期化（ログをキャプチャ）
2. イベントを処理
3. ログ内容を確認

**期待結果:**
- イベント処理開始のログが出力される
- イベント処理完了のログが出力される
- event_id がログに含まれる

### TC-06-007: 例外発生時のログ

**前提条件:** LLM 呼び出しで例外が発生する設定

**手順:**
1. AgentLoop を初期化
2. イベントを処理

**期待結果:**
- 例外がログに記録される
- 例外が適切に伝播される

### TC-06-008: EventHandler のディスパッチ

**手順:**
1. 異なるイベントタイプ用のハンドラーを登録
2. 各イベントタイプで process() を呼び出し

**期待結果:**
- 各イベントタイプに対応するハンドラーが呼び出される

## 完了条件

- [x] AgentLoop クラスが実装されている
- [x] PingEventHandler が実装されている
- [x] strands-agents の Agent を使用して LLM を呼び出せる
- [x] MOCK_LLM=true でモック動作する
- [x] 処理結果がログに記録される
- [x] 全てのテストケースがパスする
