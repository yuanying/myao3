# 01. 設定ファイル拡張

## 概要

Phase-2 で必要となる Slack 連携設定とデータベース設定を追加する。既存の設定モデルを拡張し、`config.yaml.example` を更新する。

## 依存タスク

なし（Phase-2 最初のタスク）

## 成果物

### ファイル配置

```
src/myao3/config/
├── __init__.py
├── loader.py      # 既存（変更なし）
└── models.py      # SlackConfig, DatabaseConfig 追加
```

### SlackConfig クラス

Slack 連携に必要な設定を保持する Pydantic モデル。

**フィールド:**

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| bot_token | str | ○ | - | Slack Bot Token (`xoxb-` で始まる) |
| app_token | str | ○ | - | Slack App Token (`xapp-` で始まる、Socket Mode 用) |
| response_delay | float | - | 480.0 | 非メンション時の基本遅延（秒） |
| response_delay_jitter | float | - | 240.0 | ジッター範囲（秒） |
| context_messages | int | - | 30 | LLM に渡すチャンネルメッセージ数 |
| thread_messages | int | - | 10 | スレッド内の展開メッセージ数 |

**設計根拠:**

- `response_delay`: README.md の決定事項に基づき、非メンション時は自然な応答タイミングを実現するためデフォルト 8 分
- `response_delay_jitter`: ランダム性を持たせるためのジッター範囲、デフォルト 4 分
- `context_messages`: LLM コンテキストウィンドウを考慮し、適切な文脈量を保持
- `thread_messages`: スレッドの展開は過去分を制限してコンテキスト節約

### DatabaseConfig クラス

データベース接続設定を保持する Pydantic モデル。

**フィールド:**

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| url | str | ○ | - | SQLAlchemy 形式の接続 URL |

**接続 URL 形式:**

```
sqlite+aiosqlite:///path/to/database.db
```

**設計根拠:**

- aiosqlite を使用するため `sqlite+aiosqlite://` プレフィックスが必要
- 相対パス・絶対パス両方に対応

### AppConfig への統合

既存の `AppConfig` に新しい設定を追加。

**追加フィールド:**

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| slack | SlackConfig \| None | - | Slack 設定（未設定時は Slack 機能無効） |
| database | DatabaseConfig \| None | - | データベース設定（未設定時は永続化無効） |

### config.yaml.example 更新

既存の設定ファイルテンプレートに Slack と Database セクションを追加。

**追加セクション:**

```yaml
# Slack settings (optional - enables Slack integration)
slack:
  bot_token: ${SLACK_BOT_TOKEN}      # Bot User OAuth Token
  app_token: ${SLACK_APP_TOKEN}      # App-Level Token for Socket Mode
  response_delay: 480.0              # Base delay for non-mention responses (seconds)
  response_delay_jitter: 240.0       # Jitter range (seconds)
  context_messages: 30               # Number of channel messages for LLM context
  thread_messages: 10                # Number of thread messages to expand

# Database settings (optional - enables persistence)
database:
  url: "sqlite+aiosqlite:///data/myao3.db"
```

## テストケース

### TC-01-001: SlackConfig の必須フィールド検証

**手順:**
1. `bot_token` を省略して SlackConfig を生成

**期待結果:**
- ValidationError が発生する

### TC-01-002: SlackConfig のデフォルト値

**手順:**
1. 必須フィールドのみ指定して SlackConfig を生成
2. オプションフィールドの値を確認

**期待結果:**
- `response_delay` が 480.0
- `response_delay_jitter` が 240.0
- `context_messages` が 30
- `thread_messages` が 10

### TC-01-003: DatabaseConfig の必須フィールド検証

**手順:**
1. `url` を省略して DatabaseConfig を生成

**期待結果:**
- ValidationError が発生する

### TC-01-004: 環境変数の展開

**手順:**
1. 環境変数 `SLACK_BOT_TOKEN=xoxb-test` を設定
2. `bot_token: ${SLACK_BOT_TOKEN}` を含む設定を読み込み

**期待結果:**
- `slack.bot_token` が `xoxb-test` に展開される

### TC-01-005: Slack 設定なしでの起動

**手順:**
1. `slack` セクションなしの設定ファイルを読み込み
2. AppConfig を生成

**期待結果:**
- `config.slack` が None
- エラーなく設定が読み込まれる

### TC-01-006: Database 設定なしでの起動

**手順:**
1. `database` セクションなしの設定ファイルを読み込み
2. AppConfig を生成

**期待結果:**
- `config.database` が None
- エラーなく設定が読み込まれる

### TC-01-007: 完全な設定ファイルの読み込み

**手順:**
1. Slack と Database 両方を含む設定ファイルを読み込み

**期待結果:**
- 全てのフィールドが正しく設定される
- `config.slack` が SlackConfig インスタンス
- `config.database` が DatabaseConfig インスタンス

## 完了条件

- [ ] SlackConfig クラスが定義されている
- [ ] DatabaseConfig クラスが定義されている
- [ ] AppConfig に slack, database フィールドが追加されている
- [ ] config.yaml.example が更新されている
- [ ] 環境変数展開が正しく動作する
- [ ] オプショナルな設定（slack, database）が未設定でも起動できる
- [ ] 全てのテストケースがパスする
