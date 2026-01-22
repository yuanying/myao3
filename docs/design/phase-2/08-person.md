# 08. Person エンティティ

## 概要

コミュニティに存在する人々を表す Person エンティティの基本構造を定義する。Phase-2 では最小限のフィールドのみ実装し、詳細な属性や関係は後日追加要件確定後に拡張する。

**Note:** このタスクは基本構造のみを定義する。詳細実装は後回しとする。

## 依存タスク

- 02-database.md

## 成果物

### ファイル配置

```
src/myao3/
├── domain/
│   ├── entities/
│   │   └── person.py           # Person エンティティ
│   └── repositories/
│       └── person_repository.py  # リポジトリ Protocol
└── infrastructure/
    └── persistence/
        └── person_repository.py  # リポジトリ実装（後回し可）
```

### Person エンティティ

SQLModel を継承した Person エンティティ。

**Phase-2 で実装するフィールド:**

| フィールド | 型 | PK/Index | 説明 |
|-----------|-----|----------|------|
| id | str | PK | 内部 ID（ULID） |
| slack_user_id | str \| None | Unique Index | Slack User ID |
| display_name | str | - | 表示名 |
| created_at | datetime | - | レコード作成時刻 |
| updated_at | datetime | - | レコード更新時刻 |

**将来拡張予定のフィールド（Phase-2 では実装しない）:**

| フィールド | 型 | 説明 | フェーズ |
|-----------|-----|------|---------|
| discord_user_id | str \| None | Discord User ID | Phase 3+ |
| profile | dict | プロフィール情報 | Phase 3+ |
| preferences | dict | ユーザー設定 | Phase 3+ |
| last_seen_at | datetime | 最終活動時刻 | Phase 3+ |

**設計方針:**
- 内部 ID と外部プラットフォーム ID を分離
- 将来のマルチプラットフォーム対応を考慮
- 最小限のフィールドで開始

### PersonRepository Protocol

リポジトリのインターフェース定義（Protocol）。

**Phase-2 で実装するメソッド:**

| メソッド | 引数 | 戻り値 | 説明 |
|---------|------|--------|------|
| `save` | person: Person | None | Person を保存（upsert） |
| `get_by_id` | id: str | Person \| None | 内部 ID で取得 |
| `get_by_slack_user_id` | slack_user_id: str | Person \| None | Slack User ID で取得 |
| `get_or_create_by_slack_user_id` | slack_user_id: str, display_name: str | Person | 取得または作成 |

### get_or_create_by_slack_user_id() の動作

1. `slack_user_id` で既存の Person を検索
2. 存在すれば返却
3. 存在しなければ新規作成して返却

**使用シーン:**
- Slack メッセージ処理時にユーザーを Person と紐付け
- 初見ユーザーの自動登録

### Slack との連携

**Phase-2 での使用方法:**

現時点では SlackMessage の `user_id` から Person への紐付けは行わない。将来的に以下の連携を想定:

1. メッセージ受信時に `get_or_create_by_slack_user_id()` で Person を取得/作成
2. Person ID を使った履歴検索
3. Person 単位での記憶管理

### 将来の拡張ポイント

| 拡張 | 説明 | 実装時期 |
|------|------|---------|
| マルチプラットフォーム | Discord など他プラットフォームの ID を追加 | Phase 3+ |
| プロフィール | 名前、役割、興味などの属性 | Phase 3+ |
| 関係性 | Person 間の関係（同僚、友人など） | Phase 4+ |
| アクティビティ | 活動履歴、最終活動時刻 | Phase 3+ |

## テストケース

### TC-08-001: Person 作成

**手順:**
1. 必須フィールドを指定して Person を作成
2. データベースに保存

**期待結果:**
- `id` が ULID 形式で自動生成される
- `created_at` が設定される
- レコードが保存される

### TC-08-002: Slack User ID での検索

**手順:**
1. Person を保存
2. `get_by_slack_user_id()` で検索

**期待結果:**
- 正しい Person が返される

### TC-08-003: 存在しない Slack User ID での検索

**手順:**
1. 存在しない Slack User ID で `get_by_slack_user_id()` を呼び出し

**期待結果:**
- None が返される

### TC-08-004: get_or_create - 新規作成

**手順:**
1. 存在しない Slack User ID で `get_or_create_by_slack_user_id()` を呼び出し

**期待結果:**
- 新しい Person が作成される
- 指定した `display_name` が設定される

### TC-08-005: get_or_create - 既存取得

**手順:**
1. Person を保存
2. 同じ Slack User ID で `get_or_create_by_slack_user_id()` を呼び出し

**期待結果:**
- 既存の Person が返される
- 新規作成されない

### TC-08-006: Slack User ID の一意性

**手順:**
1. 同じ `slack_user_id` で2つの Person を保存しようとする

**期待結果:**
- 一意性制約違反エラー、または upsert で更新される

### TC-08-007: updated_at の更新

**手順:**
1. Person を保存
2. フィールドを変更して再度保存
3. `updated_at` を確認

**期待結果:**
- `updated_at` が更新される
- `created_at` は変わらない

## 完了条件

- [ ] Person エンティティが SQLModel テーブルとして定義されている
- [ ] 最小限のフィールド（id, slack_user_id, display_name, created_at, updated_at）が実装されている
- [ ] PersonRepository Protocol が定義されている
- [ ] `get_by_slack_user_id()` が実装されている
- [ ] `get_or_create_by_slack_user_id()` が実装されている
- [ ] Slack User ID に一意性制約がある
- [ ] 全てのテストケースがパスする

**Note:** 詳細実装は後回し可能。Phase-2 では基本構造のみ。
