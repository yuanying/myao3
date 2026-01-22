# 03. SlackMessage エンティティ

## 概要

Slack メッセージを永続化するためのエンティティとリポジトリを実装する。メッセージの保存、取得、既読管理を行う。

## 依存タスク

- 02-database.md

## 成果物

### ファイル配置

```
src/myao3/
├── domain/
│   ├── entities/
│   │   └── slack_message.py    # SlackMessage エンティティ
│   └── repositories/
│       ├── __init__.py
│       └── slack_message_repository.py  # リポジトリ Protocol
└── infrastructure/
    └── persistence/
        └── slack_message_repository.py  # リポジトリ実装
```

### SlackMessage エンティティ

SQLModel を継承した Slack メッセージエンティティ。

**フィールド:**

| フィールド | 型 | PK/Index | 説明 |
|-----------|-----|----------|------|
| id | str | PK | 複合キー `{channel_id}:{ts}` |
| channel_id | str | Index | チャンネル ID |
| user_id | str | Index | 送信者のユーザー ID |
| text | str | - | メッセージ本文 |
| thread_ts | str \| None | Index | 親メッセージの ts（スレッド返信時） |
| ts | str | - | Slack タイムスタンプ |
| is_bot | bool | - | Bot のメッセージかどうか |
| is_read | bool | Index | 既読フラグ |
| reply_count | int | - | スレッド返信数（親メッセージのみ使用、デフォルト 0） |
| timestamp | datetime | Index | メッセージ送信時刻 |
| raw_event | dict | - | Slack イベントの生データ（JSON） |
| created_at | datetime | - | レコード作成時刻 |

**設計根拠:**

- `id`: `channel_id:ts` の複合キーにより Slack メッセージを一意に識別（README.md の決定事項）
- `thread_ts`: 親メッセージの ts を保持することでスレッド構造を表現
- `is_read`: LLM が参照した時点で既読にマーク（README.md の決定事項）
- `reply_count`: スレッド展開時の最適化に使用。`reply_count > 0` の親メッセージのみ `get_thread()` を呼び出すことで、不要な DB クエリを削減
- `raw_event`: 将来の拡張やデバッグのため生データを保持

**インデックス:**

| インデックス | カラム | 用途 |
|-------------|--------|------|
| idx_channel_timestamp | channel_id, timestamp DESC | チャンネル別時系列取得 |
| idx_thread | channel_id, thread_ts, timestamp | スレッド取得 |
| idx_unread | channel_id, is_read | 未読カウント |

### SlackMessageRepository Protocol

リポジトリのインターフェース定義（Protocol）。

**メソッド:**

| メソッド | 引数 | 戻り値 | 説明 |
|---------|------|--------|------|
| `save` | message: SlackMessage | None | メッセージを保存（upsert） |
| `get_by_id` | message_id: str | SlackMessage \| None | ID でメッセージを取得 |
| `get_by_channel` | channel_id: str, limit: int | list[SlackMessage] | チャンネルのメッセージを取得（新しい順） |
| `get_thread` | channel_id: str, thread_ts: str, limit: int | list[SlackMessage] | スレッドのメッセージを取得（古い順） |
| `get_unread_count` | channel_id: str | int | 未読メッセージ数を取得 |
| `mark_as_read` | message_ids: list[str] | None | 指定メッセージを既読にマーク |
| `increment_reply_count` | message_id: str | bool | 指定メッセージの reply_count を +1（成功時 True） |

### SqliteSlackMessageRepository

SQLite 実装のリポジトリ。

**コンストラクタ引数:**

| 引数 | 型 | 説明 |
|------|-----|------|
| database | Database | データベースインスタンス |

### save() の動作

1. 既存レコードを確認
2. 存在すれば更新（upsert）、なければ挿入
3. `raw_event` は JSON シリアライズして保存

**upsert の条件:**
- 同一 `id` のレコードが存在する場合は更新
- `created_at` は最初の挿入時刻を維持

### get_by_channel() の動作

1. 指定チャンネルのメッセージを取得
2. `timestamp` の降順（新しい順）でソート
3. `limit` 件数で制限
4. スレッド返信（`thread_ts` が非 NULL）は除外

**除外理由:**
- 親メッセージのみを取得し、スレッドは別途 `get_thread()` で展開

### get_thread() の動作

1. 指定 `thread_ts` を持つメッセージを取得
2. 親メッセージ（`ts == thread_ts`）も含める
3. `timestamp` の昇順（古い順）でソート
4. `limit` 件数で制限

### mark_as_read() の動作

1. 指定 ID のメッセージを一括更新
2. `is_read = True` に設定
3. バルク UPDATE で効率的に処理

### increment_reply_count() の動作

1. 指定 ID のメッセージの `reply_count` を +1
2. アトミックな UPDATE クエリで実行
3. メッセージが存在しない場合は False を返す

**SQL:**

```sql
UPDATE slack_messages
SET reply_count = reply_count + 1
WHERE id = :message_id
```

## テストケース

### TC-03-001: メッセージ保存

**手順:**
1. SlackMessage インスタンスを作成
2. `save()` で保存
3. データベースを確認

**期待結果:**
- レコードが正しく保存される
- `raw_event` が JSON として保存される

### TC-03-002: メッセージの upsert

**手順:**
1. 同一 ID のメッセージを2回保存（内容を変更）
2. データベースを確認

**期待結果:**
- レコードが1件のみ存在
- 内容が更新されている
- `created_at` は最初の値を維持

### TC-03-003: チャンネルメッセージ取得

**手順:**
1. 複数のメッセージを保存（異なる timestamp）
2. `get_by_channel()` を呼び出し

**期待結果:**
- 新しい順でソートされている
- 指定 limit 以下の件数
- スレッド返信は含まれない

### TC-03-004: スレッドメッセージ取得

**手順:**
1. 親メッセージとスレッド返信を保存
2. `get_thread()` を呼び出し

**期待結果:**
- 親メッセージが含まれる
- 古い順でソートされている
- 指定スレッドのメッセージのみ

### TC-03-005: 未読カウント取得

**手順:**
1. 複数メッセージを保存（一部既読）
2. `get_unread_count()` を呼び出し

**期待結果:**
- 未読メッセージの正確な数が返される

### TC-03-006: 既読マーク

**手順:**
1. 複数の未読メッセージを保存
2. 一部のメッセージ ID で `mark_as_read()` を呼び出し
3. 各メッセージの `is_read` を確認

**期待結果:**
- 指定されたメッセージのみ `is_read = True`
- 他のメッセージは `is_read = False` のまま

### TC-03-007: 空のチャンネル取得

**手順:**
1. 存在しないチャンネル ID で `get_by_channel()` を呼び出し

**期待結果:**
- 空のリストが返される

### TC-03-008: Bot メッセージの保存

**手順:**
1. `is_bot = True` のメッセージを保存
2. データベースを確認

**期待結果:**
- `is_bot` が正しく保存される

### TC-03-009: 複合キーの一意性

**手順:**
1. 同一 `channel_id` で異なる `ts` のメッセージを保存
2. 同一 `ts` で異なる `channel_id` のメッセージを保存

**期待結果:**
- 全てのメッセージが個別に保存される

### TC-03-010: raw_event の JSON シリアライズ

**手順:**
1. ネストした dict を `raw_event` に設定してメッセージを保存
2. メッセージを取得

**期待結果:**
- `raw_event` が正しくデシリアライズされる
- 元の構造が維持されている

### TC-03-011: reply_count のインクリメント

**手順:**
1. 親メッセージを保存（reply_count = 0）
2. `increment_reply_count()` を呼び出し
3. メッセージを取得

**期待結果:**
- `reply_count` が 1 になる
- True が返される

### TC-03-012: 存在しないメッセージの reply_count インクリメント

**手順:**
1. 存在しないメッセージ ID で `increment_reply_count()` を呼び出し

**期待結果:**
- False が返される

### TC-03-013: get_by_id でメッセージ取得

**手順:**
1. メッセージを保存
2. `get_by_id()` で取得

**期待結果:**
- 保存したメッセージが正しく取得される

### TC-03-014: get_by_id で存在しないメッセージ

**手順:**
1. 存在しないメッセージ ID で `get_by_id()` を呼び出し

**期待結果:**
- None が返される

## 完了条件

- [ ] SlackMessage エンティティが SQLModel テーブルとして定義されている
- [ ] `reply_count` フィールドが追加されている
- [ ] SlackMessageRepository Protocol が定義されている
- [ ] SqliteSlackMessageRepository が実装されている
- [ ] `save()` が upsert として動作する
- [ ] `get_by_id()` が単一メッセージを取得する
- [ ] `get_by_channel()` がスレッド返信を除外して取得する
- [ ] `get_thread()` が親メッセージを含めて取得する
- [ ] `mark_as_read()` がバルク更新する
- [ ] `increment_reply_count()` がアトミックに更新する
- [ ] 適切なインデックスが設定されている
- [ ] 全てのテストケースがパスする
