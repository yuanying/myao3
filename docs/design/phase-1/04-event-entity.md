# 04. Event エンティティ

## 概要

イベント駆動アーキテクチャの基盤となる Event エンティティを定義する。Phase 1 では PING イベントのみ実装する。

## 依存タスク

- 01-project-setup.md

## 成果物

### ファイル配置

```
src/myao3/domain/entities/
├── __init__.py
└── event.py      # Event 関連クラス
```

### EventType 列挙型

Phase 1 で定義するイベントタイプ:

| 値 | 説明 |
|-----|------|
| PING | システム Ping イベント |

将来追加されるイベントタイプ（Phase 2 以降）:

| 値 | 説明 | フェーズ |
|-----|------|---------|
| MESSAGE | メッセージ受信 | Phase 2 |
| REACTION | リアクション | Phase 2 |
| PRESENCE | プレゼンス変更 | Phase 3 |
| SCHEDULED | スケジュールイベント | Phase 3 |
| SELF_TRIGGERED | 自己発火イベント | Phase 2 |

### Event ベースクラス

Pydantic BaseModel を継承した抽象基底クラス。

**フィールド:**

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| id | str | ○ | イベント一意識別子（ULID） |
| type | EventType | ○ | イベントタイプ |
| timestamp | datetime | ○ | イベント発生時刻 |
| source | str | ○ | イベントソース（"api", "slack" 等） |
| payload | dict[str, Any] | - | イベント固有データ |
| context | dict[str, Any] \| None | - | 追加コンテキスト |
| created_at | datetime | ○ | イベント作成時刻（自動設定） |

**メソッド:**

| メソッド | 戻り値 | 説明 |
|---------|--------|------|
| get_identity_key() | str | 重複制御用キーを返す（デフォルトは id） |

### PingEvent クラス

Ping イベント専用のサブクラス。

**特性:**

| 項目 | 値 |
|------|-----|
| type | EventType.PING |
| source | "api" |
| identity_key | "ping"（固定） |

**get_identity_key() の動作:**

Ping イベントは常に同じ identity_key ("ping") を返す。これにより、連続した Ping イベントは最新の1件のみが処理される。

### Event ID 生成

ULID（Universally Unique Lexicographically Sortable Identifier）を使用。

**特性:**

- 時刻順でソート可能
- 128 ビットの一意識別子
- Base32 エンコード（26 文字）

**生成例:**

```
01HXYZ7W2Q4J5N6M8R9T0V1B3C
```

## テストケース

### TC-04-001: Event ID の自動生成

**手順:**
1. PingEvent を生成
2. id フィールドを確認

**期待結果:**
- id が ULID 形式（26 文字の英数字）
- 複数生成しても全て異なる

### TC-04-002: created_at の自動設定

**手順:**
1. PingEvent を生成
2. created_at フィールドを確認

**期待結果:**
- created_at が現在時刻付近
- datetime 型

### TC-04-003: PingEvent の identity_key

**手順:**
1. PingEvent を2つ生成
2. 各イベントの get_identity_key() を呼び出し

**期待結果:**
- 両方とも "ping" を返す

### TC-04-004: Event のシリアライズ

**手順:**
1. PingEvent を生成
2. model_dump() でシリアライズ

**期待結果:**
- 全フィールドが dict に変換される
- datetime は ISO 形式の文字列

### TC-04-005: Event のデシリアライズ

**入力:**
```python
{
    "id": "01HXYZ...",
    "type": "ping",
    "timestamp": "2026-01-16T10:00:00Z",
    "source": "api",
    "payload": {},
    "created_at": "2026-01-16T10:00:00Z"
}
```

**期待結果:**
- PingEvent インスタンスが生成される
- 全フィールドが正しく設定される

### TC-04-006: Event ベースクラスの identity_key

**手順:**
1. Event ベースクラスのインスタンスを生成（テスト用サブクラス）
2. get_identity_key() を呼び出し

**期待結果:**
- イベントの id がそのまま返される

### TC-04-007: payload のデフォルト値

**手順:**
1. payload を指定せずに PingEvent を生成
2. payload フィールドを確認

**期待結果:**
- payload が空の dict `{}`

## 完了条件

- [x] EventType 列挙型が定義されている
- [x] Event ベースクラスが定義されている
- [x] PingEvent クラスが定義されている
- [x] Event ID が ULID で自動生成される
- [x] get_identity_key() メソッドが実装されている
- [x] 全てのテストケースがパスする
