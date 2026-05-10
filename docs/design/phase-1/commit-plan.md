# Phase 1 コミット計画

Phase 1 は 7 コミットに分割して実装する。各コミットは、それ単体で
作業ツリーを動作可能な状態に保ち、レビュー可能な粒度にする。

## 1. project-skeleton

Python プロジェクト骨格を作成する。

実装要件:

- Python 3.12+ のプロジェクトメタデータを追加する。
- `myao3` package を追加する。
- `python -m myao3` をローカル実行エントリポイントとして追加する。
- 初期テスト構成を追加する。
- strands-agents、YAML parser、必要に応じた構造化ログ補助、テストツールなど、
  Phase 1 に必要な依存を追加する。
- 骨格実行に必要な最小 README または利用メモを追加する。

受け入れ条件:

- `python -m myao3` が起動する。
- 必須設定が不足している場合、回避可能な validation 不足による traceback ではなく、
  明確なメッセージで終了する。
- テストコマンドを実行でき、少なくとも 1 つの smoke test が成功する。
- このコミットでは外部 LLM 認証情報を要求しない。

## 2. github-actions

プロジェクト骨格の直後に CI を追加し、以降のコミットを常に検証できる状態にする。

実装要件:

- pull request と push で実行される GitHub Actions workflow を追加する。
- Python 3.12 をセットアップする。
- project と test dependencies をインストールする。
- リポジトリの unit test コマンドを実行する。
- project skeleton で静的チェックを定義する場合は、それも実行する。

受け入れ条件:

- workflow が provider API key なしで実行できる。
- test failure で workflow が失敗する。
- 実 LLM を使う E2E 検証は workflow で実行しない。
- 選択した project tooling に基づき、依存インストールが再現可能である。

## 3. config-loading

YAML 設定読み込みを実装する。

実装要件:

- ローカル実行パスから YAML config file を読み込む。
- `llm.agent` の typed configuration を定義する。
- 文字列値の `${ENV_VAR}` 展開に対応する。
- 未定義の環境変数を拒否する。
- secret 値をログや例外メッセージに含めない。
- provider 固有 option を渡せるように、任意の LLM `params` と `client_args` を保持する。

受け入れ条件:

- 有効な config から `llm.agent.model_id`、`params`、`client_args` を読み込める。
- ネストした環境変数参照を展開できる。
- `llm.agent.model_id` がない場合は validation に失敗する。
- 未定義の `${ENV_VAR}` は、secret 値を出さずに変数名を含む起動エラーになる。
- 有効な読み込み、必須項目不足、未定義環境変数を unit test で確認する。

## 4. event-model-and-ping-input

Phase 1 のイベントモデルとローカル Ping 入力を実装する。

実装要件:

- `EventType.PING` を定義する。
- `id`、`type`、`timestamp`、`source`、`payload`、`context`、`created_at` を持つ
  `Event` model を定義する。
- event に `get_identity_key()` を定義する。
- Ping の identity key は `ping` にする。
- `python -m myao3` 用に Ping event を作成するローカル経路を追加する。

受け入れ条件:

- Ping event が unique な event `id` を持つ。
- Ping event が `type=ping` を持つ。
- Ping event の `source` が Phase 1 の local source になる。
- Ping event が `identity_key=ping` を返す。
- Ping の構築と identity key 挙動を unit test で確認する。

## 5. event-queue

インメモリ EventQueue を実装する。

実装要件:

- 逐次イベント処理に `asyncio.Queue` を使う。
- pending event を `identity_key` ごとに追跡する。
- processing event を `identity_key` ごとに追跡する。
- delayed enqueue task を `identity_key` ごとに追跡する。
- 同じ identity key の新しい event が enqueue された場合、古い pending または delayed event を置き換える。
- dequeue 時に stale な queued event を skip する。
- delayed enqueue の cancellation と replacement に対応する。
- processing event を完了扱いにする `mark_done` 相当の完了経路を提供する。

受け入れ条件:

- 2 つの pending Ping event を enqueue した場合、新しい Ping だけが処理される。
- stale な queued Ping が skip される。
- delayed Ping は delay 前に取得できない。
- delayed Ping を置き換えると、古い delayed task が cancel される。
- すでに processing 中の Ping があっても、新しい Ping を pending にできる。
- replacement、stale skip、delayed enqueue、mark-done を unit test で確認する。

## 6. agent-loop-with-strands-and-llm

strands-agents と実 LLM 呼び出しを使う Phase 1 Agent Loop を実装する。

実装要件:

- Phase 1 用の最小 system prompt を構築する。
- Ping 用 query prompt を構築する。
- 処理 event ごとに strands-agents `Agent` を作成する。
- `llm.agent` から Agent を設定する。
- Phase 1 では tools を付与しない。
- Phase 1 では persistent Session storage を有効化しない。
- 選択した strands-agents integration で最も自然な API を使って Agent を invoke する。
- event processor に返す結果を正規化する。
- LLM/provider failure を制御された application error に変換し、構造化ログ field を付与する。

受け入れ条件:

- 有効な model 設定と認証情報がある場合、Ping 処理が strands-agents 経由で実 LLM を呼び出す。
- LLM response content、または安全に要約された response が logging に渡される。
- Phase 1 Agent に tools がない。
- Phase 1 Agent に Session persistence がない。
- unit test では Agent/LLM 境界を fake に置き換えられ、API key なしで実行できる。
- 手動 E2E 検証で実 provider call の成功を確認できる。

## 7. logging-and-phase1-verification

構造化ログと Phase 1 検証手順を仕上げる。

実装要件:

- JSON 構造化ログを出力する。
- event receipt、enqueue、dequeue、stale skip、Agent start、LLM success、
  LLM failure、event completion をログに残す。
- 必要に応じて `event_id`、`event_type`、`identity_key`、`source`、`model_id`、
  `duration_ms` などの安定 field を含める。
- API key、raw secret、provider credential 全体をログに出さない。
- ローカル検証コマンド列を文書化する。
- 成功時と失敗時に確認すべき signal を文書化する。

受け入れ条件:

- 成功した Ping run で queue processing、Agent execution、LLM success、completion がログに出る。
- duplicate Ping test で stale event skip 挙動を出力または assert できる。
- 無効な credential または provider error で controlled failure log が出る。
- 依存インストール後の clean checkout から、文書化された検証手順を実行できる。
- GitHub Actions が外部 LLM 認証情報なしで引き続き成功する。
