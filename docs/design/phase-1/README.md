# Phase 1 詳細設計

## 目的

Phase 1 では、myao3 の最小実行骨格を作る。

ローカルの Python プロセスが Ping イベントを受け取り、EventQueue で
重複制御し、Agent Loop を起動し、strands-agents 経由で実 LLM を呼び出し、
構造化ログを出力して正常に終了できることを確認する。

## スコープ

Phase 1 に含めるもの:

- Python 3.12+ のプロジェクト骨格
- `python -m myao3` のローカル実行エントリポイント
- 依存インストール、静的チェック、テストを実行する GitHub Actions
- `${ENV_VAR}` 展開に対応した YAML 設定読み込み
- Phase 1 の Agent Loop 用 `llm.agent` 設定
- Ping イベントモデルとローカル Ping 入力経路
- 重複制御と遅延 enqueue に対応したインメモリ EventQueue
- strands-agents を使ったツールなし Agent Loop
- Ping 処理時の実 LLM 呼び出し
- イベントライフサイクル、キュー判断、Agent 実行、LLM 成功、LLM 失敗を
  記録する JSON 構造化ログ
- Phase 1 全体フローの単体テストと手動検証手順

Phase 1 に含めないもの:

- Slack、Discord、Email などの外部プラットフォーム連携
- CopilotKit UI
- Docker と Kubernetes
- Message Store と SQLModel 永続化
- Strands Session 永続化
- 記憶システム、Wiki ツール、自己改善ツール、外部出力ツール

## Phase 1 完了条件

以下をすべて満たしたら Phase 1 完了とする。

- `python -m myao3` をローカルで実行できる。
- ローカル入力経路から Ping イベントを作成できる。
- Ping の `identity_key` が常に `ping` になる。
- 複数の pending Ping イベントを送った場合、最新の pending Ping だけが処理される。
- Ping イベントに対して Agent Loop が起動し、Ping 用 query prompt を構築する。
- Agent Loop がツールなしの strands-agents `Agent` を作成する。
- 有効な `llm.agent` 設定と認証情報がある場合、Agent が実 LLM を呼び出して応答を受け取る。
- イベント受信、queue enqueue、queue dequeue、Agent 開始、LLM 結果、イベント完了が
  JSON 構造化ログに出力される。
- LLM の認証エラー、provider エラー、timeout、API エラーが制御された失敗としてログに残る。
- GitHub Actions が外部 LLM 認証情報なしで成功する。

## 実行モデル

Phase 1 は単一のローカル Python プロセスとして動作する。

イベントは逐次処理する。複数 worker、複数アプリケーションインスタンス、
webhook、HTTP server、永続ストレージ、バックグラウンド scheduler は
Phase 1 では扱わない。

必須のイベントソースはローカル Ping 入力経路だけである。入力経路は CLI flag、
subcommand、またはデフォルト起動動作のいずれでもよいが、検証手順に明記する。

## LLM 方針

Phase 1 では実 LLM 呼び出しを必須にする。

単体テストと CI は外部認証情報に依存させない。テストでは Agent/LLM 境界を
fake または mock にする。手動 E2E 検証では実認証情報と設定済み provider を使う。

設定された LLM は Agent Loop のみに使う。記憶、自己改善、ツール専用 LLM の分離は
後続フェーズで扱う。

## 設定方針

設定ファイルは YAML とする。Phase 1 では次の論理構造を必須にする。

```yaml
llm:
  agent:
    model_id: "provider/model"
    params:
      temperature: 0.7
      max_tokens: 1024
    client_args:
      api_key: ${PROVIDER_API_KEY}
```

Phase 1 では provider を固定しない。選択した strands-agents の model integration で
扱え、上記の設定構造から表現できる provider であればよい。

`${ENV_VAR}` で参照された環境変数が未定義の場合、起動時に明確なエラーとして失敗する。
Secret はログに出力しない。

## 関連要件

- `docs/requirements/03-events.md`
- `docs/requirements/04-agent-loop.md`
- `docs/requirements/07-non-functional-requirements.md`
- `docs/requirements/08-technology-stack.md`
- `docs/requirements/09-implementation-phases.md`
