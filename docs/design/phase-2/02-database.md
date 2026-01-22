# 02. データベース基盤

## 概要

SQLite + SQLModel + aiosqlite による非同期データベース基盤を構築する。Phase-2 以降の永続化（SlackMessage、Person 等）の基盤となる。

## 依存タスク

- 01-config-extension.md

## 成果物

### ファイル配置

```
src/myao3/infrastructure/persistence/
├── __init__.py
└── database.py    # Database クラス
```

### 依存パッケージ追加

pyproject.toml に以下を追加:

| パッケージ | 用途 |
|-----------|------|
| sqlmodel | ORM（SQLAlchemy + Pydantic ベース） |
| aiosqlite | SQLite 非同期ドライバ |

### Database クラス

非同期データベース接続を管理するクラス。

**コンストラクタ引数:**

| 引数 | 型 | 説明 |
|------|-----|------|
| url | str | SQLAlchemy 形式の接続 URL |

**属性:**

| 属性 | 型 | 説明 |
|------|-----|------|
| url | str | 接続 URL |
| engine | AsyncEngine | 非同期エンジン（初期化後） |

**メソッド:**

| メソッド | 戻り値 | 説明 |
|---------|--------|------|
| `async initialize()` | None | エンジンを作成し、テーブルを初期化 |
| `async close()` | None | エンジンを破棄 |
| `get_session()` | AsyncContextManager[AsyncSession] | セッションを取得（コンテキストマネージャ） |

### initialize() の動作

1. `create_async_engine()` でエンジンを作成
2. `SQLModel.metadata.create_all()` でテーブルを作成（存在しない場合のみ）

**エンジン作成オプション:**

| オプション | 値 | 理由 |
|-----------|-----|------|
| echo | False | 本番環境でのログ抑制 |
| future | True | SQLAlchemy 2.0 スタイル |

### get_session() の動作

`async_sessionmaker` を使用してセッションを提供するコンテキストマネージャを返す。

**使用例:**

```python
async with database.get_session() as session:
    result = await session.exec(select(SlackMessage))
    messages = result.all()
```

### close() の動作

1. `engine.dispose()` でコネクションプールを解放

### ディレクトリ自動作成

SQLite ファイルパスの親ディレクトリが存在しない場合、自動で作成する。

**処理フロー:**

1. URL から SQLite ファイルパスを抽出
2. 親ディレクトリが存在しない場合、`os.makedirs()` で作成
3. エンジンを作成

### エラーハンドリング

| エラー種別 | 対処 |
|-----------|------|
| 不正な URL 形式 | ValueError を発生 |
| ディレクトリ作成失敗 | OSError をそのまま伝播 |
| 接続失敗 | SQLAlchemyError をそのまま伝播 |

## テストケース

### TC-02-001: Database 初期化

**手順:**
1. 一時ディレクトリに SQLite ファイルパスを指定
2. `Database.initialize()` を呼び出し

**期待結果:**
- エラーなく完了
- SQLite ファイルが作成される

### TC-02-002: テーブル自動作成

**前提条件:** SQLModel テーブルクラスが定義済み

**手順:**
1. Database を初期化
2. SQLite ファイルのテーブル一覧を確認

**期待結果:**
- 定義された全テーブルが存在する

### TC-02-003: セッション取得

**手順:**
1. Database を初期化
2. `get_session()` でセッションを取得
3. セッション内でクエリを実行

**期待結果:**
- AsyncSession インスタンスが返される
- クエリが実行できる

### TC-02-004: セッションの自動コミット

**手順:**
1. Database を初期化
2. セッション内でレコードを追加
3. コンテキストマネージャを抜ける
4. 新しいセッションでレコードを確認

**期待結果:**
- レコードが永続化されている

### TC-02-005: セッションの自動ロールバック

**手順:**
1. Database を初期化
2. セッション内でレコードを追加
3. 例外を発生させてコンテキストマネージャを抜ける
4. 新しいセッションでレコードを確認

**期待結果:**
- レコードが永続化されていない

### TC-02-006: ディレクトリ自動作成

**手順:**
1. 存在しないディレクトリパスを含む URL を指定
2. Database を初期化

**期待結果:**
- 親ディレクトリが自動作成される
- SQLite ファイルが作成される

### TC-02-007: Database クローズ

**手順:**
1. Database を初期化
2. `close()` を呼び出し
3. セッション取得を試みる

**期待結果:**
- エンジンが破棄される
- 以降のセッション取得はエラー

### TC-02-008: 複数セッションの並行処理

**手順:**
1. Database を初期化
2. 複数の非同期タスクで同時にセッションを取得
3. 各タスクでクエリを実行

**期待結果:**
- デッドロックなく全タスクが完了
- 各タスクのクエリが正しく実行される

## 完了条件

- [ ] sqlmodel, aiosqlite が依存関係に追加されている
- [ ] Database クラスが実装されている
- [ ] `initialize()` でテーブルが自動作成される
- [ ] `get_session()` で AsyncSession が取得できる
- [ ] `close()` でエンジンが破棄される
- [ ] 親ディレクトリが自動作成される
- [ ] 全てのテストケースがパスする
