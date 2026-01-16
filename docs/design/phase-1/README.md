# Phase 1: 最小限の骨格（MVP）

## 目標

イベントを受信してAgent Loopが動作することを確認する

## 実行環境

ローカル（Python直接実行）

## 完了条件

- Pingイベントを送信すると、Agent Loopが起動し、ログに記録されて終了する
- 同じidentity_keyのイベントを連続送信すると、最新の1件のみ処理される
- `python -m myao3 --config config.yaml` でローカル実行できる

## タスク一覧

| # | タスク | ファイル | 依存 |
|---|--------|----------|------|
| 01 | プロジェクト基盤セットアップ | [01-project-setup.md](./01-project-setup.md) | - |
| 02 | 設定ファイル読み込み | [02-config.md](./02-config.md) | 01 |
| 03 | ログ出力基盤 | [03-logging.md](./03-logging.md) | 02 |
| 04 | Event エンティティ | [04-event-entity.md](./04-event-entity.md) | 01 |
| 05 | EventQueue | [05-event-queue.md](./05-event-queue.md) | 04 |
| 06 | Agent Loop | [06-agent-loop.md](./06-agent-loop.md) | 01, 02, 03, 05 |
| 07 | アプリケーションエントリポイント | [07-entrypoint.md](./07-entrypoint.md) | 06, 08 |
| 08 | HTTP サーバー（イベント受信） | [08-http-server.md](./08-http-server.md) | 05, 06 |
| 09 | 開発用スクリプト（hack/） | [09-hack-scripts.md](./09-hack-scripts.md) | 08 |
| 10 | GitHub Actions CI 設定 | [10-ci.md](./10-ci.md) | 01 |

## 依存関係図

```
Task 1 (プロジェクト基盤) ──────────────────┐
    │                                       │
    ├──────────────────┬─────────────────┐  │
    ▼                  ▼                 │  │
Task 2 (設定)      Task 4 (Event)       │  │
    │                  │                 │  │
    ▼                  ▼                 │  │
Task 3 (ログ)      Task 5 (EventQueue)  │  │
    │                  │                 │  │
    └──────┬───────────┘                 │  │
           ▼                             │  │
       Task 6 (Agent Loop) ◄─────────────┘  │
           │                                │
           ▼                                │
       Task 8 (HTTP サーバー)               │
           │                                │
           ▼                                │
       Task 7 (エントリポイント)            │
           │                                │
           ▼                                │
       Task 9 (hack スクリプト)             │
           │                                │
           ▼                                │
       Task 10 (CI) ◄───────────────────────┘
```

## 最終ディレクトリ構造

```
myao3/
├── .github/
│   └── workflows/
│       └── ci.yaml
├── docs/
│   └── design/
│       └── phase-1/
│           └── ...
├── hack/
│   ├── README.md
│   └── send_ping.py
├── src/
│   └── myao3/
│       ├── __init__.py
│       ├── __main__.py
│       ├── config/
│       │   ├── __init__.py
│       │   └── loader.py
│       ├── domain/
│       │   ├── __init__.py
│       │   └── entities/
│       │       ├── __init__.py
│       │       └── event.py
│       ├── application/
│       │   ├── __init__.py
│       │   └── services/
│       │       ├── __init__.py
│       │       └── agent_loop.py
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   ├── event_queue.py
│       │   ├── llm/
│       │   │   ├── __init__.py
│       │   │   └── litellm_model.py
│       │   └── logging/
│       │       ├── __init__.py
│       │       └── setup.py
│       └── presentation/
│           ├── __init__.py
│           └── http/
│               ├── __init__.py
│               └── server.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_config.py
│   │   ├── test_event.py
│   │   ├── test_event_queue.py
│   │   └── test_agent_loop.py
│   └── integration/
│       ├── __init__.py
│       └── test_main.py
├── config.yaml.example
├── pyproject.toml
├── .gitignore
└── requirements.md
```

## 決定事項

| 項目 | 選択 | 理由・備考 |
|------|------|-----------|
| HTTP フレームワーク | aiohttp | 軽量で asyncio ネイティブ。Phase 2 の Slack Bolt と共存可能 |
| HTTP デフォルトポート | 8080 | 一般的なアプリケーションポート |
| system_prompt 配置 | config.yaml 内 | 設定と一元管理。環境ごとに切り替え可能 |
| LLM モック方式 | 環境変数で切り替え | MOCK_LLM=true で CI でも実行可能 |
| ログ出力先 | stdout のみ | K8s との相性良好。ファイル保存は外部ツールで |
| シャットダウン | 処理中イベント完了待ち | タイムアウト付き（30秒）でグレースフル |
| EventQueue 上限 | 無制限 | Phase 1 はシンプルに。上限は Phase 2 以降で検討 |
| API エラー形式 | シンプル JSON | `{"error": "message"}` 形式 |
| Event ID 形式 | ULID | ソート可能な一意 ID。ulid-py 依存追加 |
| delay パース形式 | 秒数のみ（整数） | API はシンプルに。CLI は後で拡張可能 |
| Agent 呼び出し | invoke_async | asyncio との統合が自然 |
| LLM 統合 | strands LiteLLMModel | strands-agents が提供するクラスを使用 |
| テスト環境 | pytest-asyncio + pytest-cov | カバレッジ計測も実施 |
| Ping 時の動作 | LLM に判断を委ねる | system_prompt で指示し、実際の動作を確認 |
| API パス | POST /api/v1/events | バージョニング対応 |
| ヘルスチェック | GET /healthz（Liveness のみ） | Phase 1 は Liveness のみ。常に OK を返す |
| config パス | コマンドライン引数 | `python -m myao3 --config /path/to/config.yaml` |
| ドキュメント言語 | 日本語 | requirements.md に合わせる |
| カバレッジ目標 | 設定なし | TDD で自然にカバーされる |
| CI | GitHub Actions | テスト、lint、型チェックを自動化 |
