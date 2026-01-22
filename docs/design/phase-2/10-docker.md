# 10. Docker イメージ

## 概要

myao3 アプリケーションをコンテナ化するための Dockerfile を作成する。マルチステージビルドで効率的なイメージを構築し、Kubernetes での運用に対応する。

## 依存タスク

- 01-config-extension.md
- 02-database.md
- 03-slack-message.md
- 04-slack-channel-update-event.md
- 05-slack-bolt.md
- 06-slack-channel-update-handler.md
- 07-slack-tools.md

## 成果物

### ファイル配置

```
myao3/
├── Dockerfile
└── .dockerignore
```

### Dockerfile 設計

マルチステージビルドを採用し、最終イメージサイズを最小化。

**ステージ構成:**

| ステージ | ベースイメージ | 目的 |
|---------|---------------|------|
| builder | python:3.12-slim | 依存関係のインストール |
| runtime | python:3.12-slim | アプリケーション実行 |

### builder ステージ

**処理内容:**

1. uv のインストール
2. pyproject.toml, uv.lock のコピー
3. `uv sync --frozen` で依存関係をインストール
4. 仮想環境を `/app/.venv` に作成

**ポイント:**
- `--frozen` で lock ファイルに完全一致する依存関係をインストール
- 仮想環境を明示的なパスに作成して runtime ステージにコピー可能に

### runtime ステージ

**処理内容:**

1. 必要なシステムパッケージのインストール（最小限）
2. builder から仮想環境をコピー
3. アプリケーションコードをコピー
4. 非 root ユーザーの作成
5. エントリポイントの設定

**ポイント:**
- 開発依存関係を含まない
- 非 root ユーザーで実行（セキュリティ）
- 不要なファイルを含まない

### Dockerfile 概要

```dockerfile
# ============================================
# Builder Stage
# ============================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (production only)
RUN uv sync --frozen --no-dev

# ============================================
# Runtime Stage
# ============================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ ./src/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1

# Create directories for volumes
RUN mkdir -p /config /data && chown -R appuser:appuser /app /config /data

# Switch to non-root user
USER appuser

# Health check endpoint
EXPOSE 8080

# Entry point
CMD ["python", "-m", "myao3", "--config", "/config/config.yaml"]
```

### ボリュームマウントポイント

| パス | 目的 | 必須 |
|------|------|------|
| /config | 設定ファイル（config.yaml） | ○ |
| /data | SQLite データベース | ○（永続化する場合） |

### 環境変数

**コンテナ内で設定される環境変数:**

| 変数 | 値 | 説明 |
|------|-----|------|
| PATH | /app/.venv/bin:$PATH | 仮想環境の有効化 |
| PYTHONPATH | /app/src | アプリケーションコード |
| PYTHONUNBUFFERED | 1 | ログのバッファリング無効化 |

**実行時に注入が必要な環境変数:**

| 変数 | 説明 |
|------|------|
| SLACK_BOT_TOKEN | Slack Bot Token |
| SLACK_APP_TOKEN | Slack App Token |

### .dockerignore

**除外パターン:**

```
# Git
.git/
.gitignore

# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.coverage
htmlcov/
*.egg-info/

# Development
.venv/
.env
.env.*
*.md
docs/

# IDE
.vscode/
.idea/

# Tests (production image doesn't need tests)
tests/

# Kubernetes manifests
k8s/

# Local config
config.yaml
```

### イメージビルド

**ビルドコマンド:**

```bash
docker build -t myao3:latest .
```

**タグ付け:**

```bash
docker tag myao3:latest myao3:v0.2.0
```

### ローカル実行

**実行コマンド:**

```bash
docker run -d \
  --name myao3 \
  -v $(pwd)/config.yaml:/config/config.yaml:ro \
  -v $(pwd)/data:/data \
  -e SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN} \
  -e SLACK_APP_TOKEN=${SLACK_APP_TOKEN} \
  -p 8080:8080 \
  myao3:latest
```

### ヘルスチェック

**エンドポイント:** `/health`

**Dockerfile での設定:**

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1
```

**Note:** curl がベースイメージに含まれていない場合は、python スクリプトで代替可能。

## テストケース

### TC-10-001: イメージビルド

**手順:**
1. `docker build -t myao3:test .` を実行

**期待結果:**
- エラーなくビルドが完了する
- イメージが作成される

### TC-10-002: イメージサイズ

**手順:**
1. イメージをビルド
2. `docker images myao3:test` でサイズを確認

**期待結果:**
- 合理的なサイズ（500MB 以下を目安）
- 開発依存関係が含まれていない

### TC-10-003: コンテナ起動

**手順:**
1. 設定ファイルを用意
2. コンテナを起動

**期待結果:**
- コンテナが正常に起動する
- ログが出力される

### TC-10-004: 非 root ユーザー実行

**手順:**
1. コンテナを起動
2. `docker exec <container> whoami` を実行

**期待結果:**
- `appuser` が返される

### TC-10-005: ボリュームマウント - config

**手順:**
1. ホストの config.yaml を /config にマウント
2. コンテナを起動

**期待結果:**
- 設定ファイルが読み込まれる

### TC-10-006: ボリュームマウント - data

**手順:**
1. ホストのディレクトリを /data にマウント
2. コンテナを起動
3. メッセージを保存

**期待結果:**
- SQLite ファイルがホストに作成される
- データが永続化される

### TC-10-007: 環境変数の注入

**手順:**
1. 環境変数を設定してコンテナを起動
2. Slack 接続を確認

**期待結果:**
- 環境変数が正しく読み込まれる
- Slack に接続できる

### TC-10-008: ヘルスチェック

**手順:**
1. コンテナを起動
2. `docker inspect --format='{{.State.Health.Status}}' <container>` を確認

**期待結果:**
- `healthy` が返される

### TC-10-009: グレースフルシャットダウン

**手順:**
1. コンテナを起動
2. `docker stop <container>` を実行
3. ログを確認

**期待結果:**
- SIGTERM を受けて正常終了する
- 終了ログが出力される

### TC-10-010: .dockerignore の動作

**手順:**
1. イメージをビルド
2. コンテナ内で `ls /app` を実行

**期待結果:**
- tests/ が含まれていない
- .git/ が含まれていない
- docs/ が含まれていない

## 完了条件

- [ ] Dockerfile が作成されている
- [ ] マルチステージビルドが実装されている
- [ ] 非 root ユーザーで実行される
- [ ] /config, /data のボリュームマウントポイントがある
- [ ] 環境変数で機密情報を注入できる
- [ ] .dockerignore が作成されている
- [ ] イメージがビルドできる
- [ ] コンテナが正常に起動する
- [ ] 全てのテストケースがパスする
