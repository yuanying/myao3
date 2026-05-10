# Phase 1 技術設計

## アーキテクチャ

Phase 1 は単一プロセスの非同期 pipeline として構成する。

```text
local Ping input
  -> Event
  -> EventQueue
  -> Agent Loop
  -> strands-agents Agent
  -> real LLM
  -> JSON logs
```

Phase 1 では、外部プラットフォーム adapter、database、persistent Session、
tool execution は扱わない。

## コンポーネント

### ローカルエントリポイント

`python -m myao3` を標準のローカルエントリポイントにする。

エントリポイントの責務:

- 設定を読み込む。
- EventQueue を作成する。
- Phase 1 のローカル入力経路から Ping event を作成する。
- Ping を enqueue する。
- Ping が処理されるまで event processor を実行する。
- 成功または制御された失敗を反映した process exit code を返す。

unit test では GitHub Actions secrets を要求しない。実 LLM 検証は手動で行う。

### 設定

Phase 1 の設定は YAML とする。

必須の論理構造:

```yaml
llm:
  agent:
    model_id: "provider/model"
    params: {}
    client_args: {}
```

`params` と `client_args` は pass-through map とする。現在把握している provider option だけに
制限してはならない。

環境変数展開は文字列値の `${ENV_VAR}` syntax を使う。未定義の環境変数は起動エラーにする。

### イベントモデル

Phase 1 の event model は次の field を持つ。

| Field | 要件 |
| --- | --- |
| `id` | unique event identifier |
| `type` | Phase 1 では `ping` |
| `timestamp` | event 発生時刻 |
| `source` | local source name |
| `payload` | event 固有 data。Ping では空または最小 |
| `context` | optional runtime context |
| `created_at` | local creation time |

Ping event は `get_identity_key()` で `ping` を返す。

### EventQueue

EventQueue は `asyncio.Queue` ベースのインメモリ queue とする。

保持する状態:

- `_pending: dict[str, Event]`
- `_processing: dict[str, Event]`
- `_delay_tasks: dict[str, asyncio.Task[None]]`

挙動:

- delay なし enqueue は event を `_pending` に保存し、queue に投入する。
- delay 付き enqueue は delayed task を作成する。
- 同じ `identity_key` の新 event は、古い pending または delayed event を置き換える。
- dequeue は、identity key が `_pending` 上で該当 event を指していない stale queued event を skip する。
- current event を dequeue したら、`_pending` から `_processing` に移す。
- `mark_done(event)` は、同一 event object が processing として記録されている場合だけ
  `_processing` から削除する。

処理は逐次実行する。Phase 1 では parallel worker は不要。

### Agent Loop

Agent Loop の処理順:

1. dequeued event を受け取る。
2. Phase 1 用の最小 system prompt を構築する。
3. Ping query prompt を構築する。
4. event ごとに strands-agents `Agent` を作成する。
5. `llm.agent` から Agent を設定する。
6. Agent を invoke する。
7. 結果を正規化する。
8. 成功または制御された失敗をログに出す。
9. event を done にする。

Phase 1 Agent の制約:

- tools は持たない。
- persistent Session manager は持たない。
- external message restoration は行わない。
- memory injection は行わない。
- outbound platform action は行わない。

Agent は event ごとに作成する。後続要件で model、tools、runtime context、prompt が
event scope になるため、この形に合わせる。

### strands-agents と LLM 設定

Phase 1 では Agent framework として strands-agents を使う。

リポジトリ側の LLM 設定は provider-neutral に保つ。

- `model_id` は設定済み model を識別する。
- `params` は invocation parameter を保持する。
- `client_args` は provider または client 初期化 parameter を保持する。

実装では、この設定を選択した strands-agents model integration に合わせて変換する。
integration が LiteLLM-compatible model wrapper を要求する場合、その adapter は
event model や queue ではなく Agent construction boundary に置く。

Agent Loop は unit test 用に fake 可能な境界を公開し、CI が外部 provider を呼ばないようにする。

### Prompt

Phase 1 では最小 system prompt と Ping query prompt だけを使う。

system prompt に含める内容:

- この process が myao3 Phase 1 であること。
- Agent が system Ping を処理していること。
- tools を持たないこと。
- 外部プラットフォームへ接触したと主張してはならないこと。
- 簡潔な status response を返すこと。

Ping query prompt は、system Ping を受信したことを伝え、Agent に operational status の報告を求める。

prompt file composition、Dynamic Notes、memory prompt、safety prompt expansion、
self-improvement prompt editing は後続フェーズで扱う。

### ログ

ログは JSON record として出力する。

必須 log event:

- `event.received`
- `queue.enqueued`
- `queue.dequeued`
- `queue.skipped_stale`
- `agent.started`
- `llm.succeeded`
- `llm.failed`
- `event.completed`

共通 field:

- `event_id`
- `event_type`
- `identity_key`
- `source`
- `model_id`
- `duration_ms`
- `error_type`
- `error_message`

secret 値は絶対にログに出さない。`client_args` 全体もログに出さない。

### エラーハンドリング

設定エラーは起動時に失敗させる。

queue エラーは application bug として扱い、test で検出する。

LLM error は制御された runtime failure として扱う。手動 Ping run では process が
non-zero exit になってもよいが、その前に構造化 failure record をログに出す。

想定する LLM failure:

- 認証情報不足または不正。
- provider API error。
- model not found または unsupported model。
- timeout。
- network failure。

### GitHub Actions

CI は project skeleton の直後に導入する。

CI の要件:

- pull request と push で実行する。
- Python 3.12 を使う。
- project dependencies を再現可能な形でインストールする。
- unit test を実行する。
- static check が設定されている場合は実行する。
- 実 LLM call は実行しない。

provider credential がない場合、LLM 依存 test が skip、fake、または mock されることを
CI で確認してもよい。

### テストマトリクス

必須 automated test:

| 領域 | scenario |
| --- | --- |
| Config | valid YAML、`llm.agent.model_id` 不足、env expansion、undefined env |
| Event | Ping creation、timestamp、`identity_key=ping` |
| Queue | replace pending、skip stale、delayed enqueue、cancel delayed、mark done |
| Agent Loop | prompt construction、fake Agent invocation、success result |
| LLM failure | fake provider error、timeout-style error、controlled log fields |
| CLI | fake Agent と外部認証情報なしの startup path |

手動 E2E 検証:

1. YAML file が参照する provider API key を export する。
2. Phase 1 config を指定して `python -m myao3` を実行する。
3. log に `agent.started`、`llm.succeeded`、`event.completed` が含まれることを確認する。
4. duplicate Ping scenario または queue test で、最新の pending Ping だけが処理されることを確認する。
5. 無効な credential で実行し、credential を出力せずに `llm.failed` が記録されることを確認する。
