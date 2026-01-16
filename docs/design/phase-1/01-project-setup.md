# 01. プロジェクト基盤セットアップ

## 概要

myao3 プロジェクトの基盤となるファイル・ディレクトリ構造を作成する。

## 依存タスク

なし（最初のタスク）

## 成果物

### pyproject.toml

**依存関係:**

| パッケージ | 用途 |
|-----------|------|
| strands-agents | Agent フレームワーク |
| litellm | LLM プロバイダ抽象化 |
| pydantic | 設定・データモデル |
| pyyaml | YAML 設定ファイル読み込み |
| structlog | 構造化ログ |
| aiohttp | HTTP サーバー |
| ulid-py | Event ID 生成 |

**dev 依存関係:**

| パッケージ | 用途 |
|-----------|------|
| pytest | テストフレームワーク |
| pytest-asyncio | 非同期テストサポート |
| pytest-cov | カバレッジ計測 |
| ruff | Linter / Formatter |
| ty | 型チェック |

**設定:**

- Python バージョン: 3.12+
- パッケージ名: myao3
- ソースディレクトリ: src/myao3
- テストディレクトリ: tests/

### ディレクトリ構造

```
src/myao3/
├── __init__.py
├── config/
│   └── __init__.py
├── domain/
│   ├── __init__.py
│   └── entities/
│       └── __init__.py
├── application/
│   ├── __init__.py
│   └── services/
│       └── __init__.py
├── infrastructure/
│   ├── __init__.py
│   ├── llm/
│   │   └── __init__.py
│   └── logging/
│       └── __init__.py
└── presentation/
    ├── __init__.py
    └── http/
        └── __init__.py

tests/
├── __init__.py
├── conftest.py
├── unit/
│   └── __init__.py
└── integration/
    └── __init__.py
```

### config.yaml.example

Phase 1 で必要な最小限の設定項目を定義したテンプレート。

**必須項目:**

| 項目 | 説明 |
|------|------|
| agent.system_prompt | Agent の system prompt |
| agent.llm.model_id | LiteLLM 形式のモデル ID |
| server.host | HTTP サーバーのホスト（デフォルト: 0.0.0.0） |
| server.port | HTTP サーバーのポート（デフォルト: 8080） |

**オプション項目:**

| 項目 | 説明 |
|------|------|
| agent.llm.params | LLM パラメータ（temperature 等） |
| agent.llm.client_args | LLM クライアント引数（api_key 等） |
| logging.level | ログレベル（デフォルト: INFO） |
| logging.format | ログフォーマット（デフォルト: json） |

### .gitignore

Python プロジェクト向けの標準的な .gitignore。

**含めるパターン:**

- `__pycache__/`
- `*.pyc`
- `.venv/`
- `*.egg-info/`
- `.pytest_cache/`
- `.coverage`
- `htmlcov/`
- `.ruff_cache/`
- `config.yaml`（実際の設定ファイルは除外）
- `.env`

## テストケース

### TC-01-001: ディレクトリ構造の確認

**前提条件:** プロジェクトがセットアップ済み

**手順:**
1. 必要なディレクトリが存在することを確認

**期待結果:** 全てのディレクトリが存在する

### TC-01-002: 依存関係のインストール

**前提条件:** pyproject.toml が存在する

**手順:**
1. `uv sync` を実行

**期待結果:** エラーなく依存関係がインストールされる

### TC-01-003: テストの実行

**前提条件:** 依存関係がインストール済み

**手順:**
1. `uv run pytest` を実行

**期待結果:** テストが実行される（初期状態では 0 tests）

### TC-01-004: Linter の実行

**前提条件:** 依存関係がインストール済み

**手順:**
1. `uv run ruff check .` を実行
2. `uv run ruff format --check .` を実行

**期待結果:** エラーなく完了する

### TC-01-005: 型チェックの実行

**前提条件:** 依存関係がインストール済み

**手順:**
1. `uv run ty check` を実行

**期待結果:** 型エラーがない

## 完了条件

- [ ] pyproject.toml が作成され、`uv sync` が成功する
- [ ] ディレクトリ構造が作成されている
- [ ] config.yaml.example が作成されている
- [ ] .gitignore が作成されている
- [ ] `uv run pytest` が実行できる
- [ ] `uv run ruff check .` がエラーなく完了する
- [ ] `uv run ty check` がエラーなく完了する
