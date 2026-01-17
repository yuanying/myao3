# CLAUDE.md

## プロジェクト概要

myao3 - イベント駆動で動作し、自律的に環境へ適応していく「みんなの友達」ボット

### ビジョン

複数のコミュニティに存在し、そこにいる人々を認識し、適切なタイミングで適切な形で関わる存在。押し付けがましくなく、しかし必要なときにはそこにいる——そのような「友達」としての振る舞いを目指す。

### 基本原則

| 原則 | 説明 |
|------|------|
| 自律性 | いつ・何を・どのように行動するかはボット自身が判断 |
| 透明性 | 内部思考は外部に漏れず、意図した行動のみが表出 |
| 適応性 | 経験を通じて自己を改善し、環境に適応 |
| 漸進性 | 機能は段階的に拡張、最初は最小限から |

### 設計ポリシー

- **閉じたAgent Loop**: 中間出力（思考、推論、計画）は外部に漏れない。外部世界への影響は明示的なツール呼び出しのみ
- **ツール命名規則**: 具体的なプラットフォーム名を含む（例: `post_slack_message`）
- **三層記憶**: Working Memory / Short-term Memory / Long-term Memory

## 技術スタック

- **言語**: Python 3.12+
- **パッケージ管理**: uv
- **LLM**: LiteLLM
- **Linter**: ruff
- **型チェック**: ty
- **永続化**: SQLite
- **ORM**: SQLModel

## 開発コマンド

```bash
# 依存関係のインストール
uv sync

# Linter実行
uv run ruff check .
uv run ruff format .

# 型チェック
uv run ty check

# テスト実行
uv run pytest

# アプリケーション起動
uv run python -m myao3
```

## アーキテクチャ

クリーンアーキテクチャ / DDD / Dependency Injection を採用

```
src/myao2/
├── domain/              # ドメイン層
│   ├── entities/        # エンティティ
│   ├── repositories/    # リポジトリインターフェース（Protocol）
│   └── services/        # ドメインサービスインターフェース（Protocol）
├── application/         # アプリケーション層
│   ├── use_cases/       # ユースケース
│   └── services/        # アプリケーションサービス
├── infrastructure/      # インフラ層（リポジトリ実装、外部サービス）
│   ├── llm/             # LLM携
│   └── persistence/     # SQLite永続化
├── presentation/        # プレゼンテーション層
└── config/              # 設定管理
```

### レイヤー間の依存関係

- domain は他のレイヤーに依存しない
- application は domain にのみ依存
- infrastructure は domain, application に依存
- presentation は application に依存

## 設計ドキュメント

フェーズごとの詳細設計書が `docs/design` ディレクトリに配置されている:
各フェーズの README.md に全体概要、個別の `.md` ファイルにタスクごとの詳細設計がある。

## コーディング規約

### 型ヒント
- すべての関数に型ヒントを付ける
- `Any` の使用は最小限に

### docstring
- 公開APIにはdocstringを記載
- Google styleを使用

### テスト
- TDDで開発を進める
- テストファイルは `tests/` ディレクトリに配置
- ファイル名は `test_*.py` 形式

### インポート
- 標準ライブラリ、サードパーティ、ローカルの順で記載
- ruffによる自動ソート

## 設定ファイル

- `config.yaml` - アプリケーション設定
- `config.yaml.example` - 設定テンプレート
- `.env` - 環境変数（機密情報）

**重要**: 設定項目を追加・変更した場合は、必ず `config.yaml.example` も同期して更新すること。

環境変数は `${VAR_NAME}` 形式で config.yaml から参照可能

## 重要な注意事項

- ドメイン層は特定プラットフォームに依存しない設計とする（将来のマルチプラットフォーム対応のため）
- LLM設定はLiteLLMのcompletion関数に渡すdict形式で定義
- 機密情報（トークン等）は必ず環境変数経由で注入
