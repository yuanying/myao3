# 04. SlackChannelUpdateEvent

## 概要

Slack チャンネルで更新があったことを通知するイベントを定義する。EventQueue の重複制御機能により、同一チャンネルへの連続した更新は最新のイベントのみが処理される。

## 依存タスク

- 03-slack-message.md（SlackMessage の保存後にイベントが発火されるため）

## 成果物

### ファイル配置

```
src/myao3/domain/entities/
├── __init__.py
└── event.py      # EventType, SlackChannelUpdateEvent 追加
```

### EventType 列挙型への追加

既存の EventType に新しいタイプを追加。

**追加値:**

| 値 | 説明 |
|-----|------|
| SLACK_CHANNEL_UPDATE | Slack チャンネル更新イベント |

### SlackChannelUpdateEvent クラス

Slack チャンネルの更新を表すイベントクラス。

**フィールド:**

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| id | str | ○ | イベント ID（ULID、自動生成） |
| type | EventType | ○ | SLACK_CHANNEL_UPDATE（固定） |
| timestamp | datetime | ○ | イベント発生時刻 |
| source | str | ○ | "slack"（固定） |
| payload | SlackChannelUpdatePayload | ○ | イベント固有データ |
| context | dict[str, Any] \| None | - | 追加コンテキスト |
| created_at | datetime | ○ | イベント作成時刻（自動設定） |

### SlackChannelUpdatePayload

ペイロードのデータ構造。

**フィールド:**

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| channel_id | str | ○ | チャンネル ID |
| is_mention | bool | ○ | Bot へのメンションかどうか |
| trigger_ts | str | ○ | トリガーとなったメッセージの ts |

**設計根拠:**

- `channel_id`: EventQueue での重複制御キー生成に使用
- `is_mention`: 遅延計算の判断に使用（メンション時は即時処理）
- `trigger_ts`: デバッグや監査のため、どのメッセージがトリガーか記録

### get_identity_key() の実装

**戻り値:** `"slack_ch_update:{channel_id}"`

**動作:**
- チャンネル単位でイベントをマージ
- 同一チャンネルへの連続したメッセージは最新のイベントのみ処理

**設計根拠（README.md の決定事項）:**
- identity_key 形式は `slack_ch_update:{channel_id}` を採用
- チャンネル単位でイベントマージすることで、連投されたメッセージを1回の処理で対応

### ファクトリメソッド

イベント生成を簡便にするクラスメソッド。

**create() メソッド:**

| 引数 | 型 | 説明 |
|------|-----|------|
| channel_id | str | チャンネル ID |
| is_mention | bool | メンションかどうか |
| trigger_ts | str | トリガーメッセージの ts |

**戻り値:** SlackChannelUpdateEvent インスタンス

**自動設定される値:**
- `id`: ULID で自動生成
- `type`: EventType.SLACK_CHANNEL_UPDATE
- `timestamp`: 現在時刻
- `source`: "slack"
- `created_at`: 現在時刻

## テストケース

### TC-04-001: イベント生成

**手順:**
1. `SlackChannelUpdateEvent.create()` でイベントを生成

**期待結果:**
- `type` が EventType.SLACK_CHANNEL_UPDATE
- `source` が "slack"
- `id` が ULID 形式
- `payload` に指定した値が設定される

### TC-04-002: identity_key の生成

**手順:**
1. channel_id="C123" でイベントを生成
2. `get_identity_key()` を呼び出し

**期待結果:**
- 戻り値が "slack_ch_update:C123"

### TC-04-003: 同一チャンネルの identity_key

**手順:**
1. 同一 channel_id で2つのイベントを生成
2. 各イベントの `get_identity_key()` を比較

**期待結果:**
- 両方とも同じ identity_key を返す

### TC-04-004: 異なるチャンネルの identity_key

**手順:**
1. 異なる channel_id で2つのイベントを生成
2. 各イベントの `get_identity_key()` を比較

**期待結果:**
- 異なる identity_key を返す

### TC-04-005: is_mention フラグ

**手順:**
1. `is_mention=True` でイベントを生成
2. `is_mention=False` でイベントを生成

**期待結果:**
- 各イベントの `payload.is_mention` が正しく設定される

### TC-04-006: イベントのシリアライズ

**手順:**
1. イベントを生成
2. `model_dump()` でシリアライズ

**期待結果:**
- 全フィールドが dict に変換される
- `type` が文字列 "slack_channel_update" に変換される
- `payload` がネストした dict として含まれる

### TC-04-007: イベントのデシリアライズ

**入力:**
```python
{
    "id": "01HXYZ...",
    "type": "slack_channel_update",
    "timestamp": "2026-01-16T10:00:00Z",
    "source": "slack",
    "payload": {
        "channel_id": "C123",
        "is_mention": True,
        "trigger_ts": "1737000000.000100"
    },
    "created_at": "2026-01-16T10:00:00Z"
}
```

**期待結果:**
- SlackChannelUpdateEvent インスタンスが生成される
- payload が SlackChannelUpdatePayload として復元される

### TC-04-008: EventQueue との統合

**手順:**
1. 同一チャンネルのイベントを2つ連続で EventQueue に追加
2. dequeue でイベントを取得

**期待結果:**
- 最新のイベントのみが取得される
- 古いイベントはマージされる

## 完了条件

- [ ] EventType.SLACK_CHANNEL_UPDATE が追加されている
- [ ] SlackChannelUpdatePayload が定義されている
- [ ] SlackChannelUpdateEvent クラスが定義されている
- [ ] `get_identity_key()` が "slack_ch_update:{channel_id}" を返す
- [ ] `create()` ファクトリメソッドが実装されている
- [ ] シリアライズ/デシリアライズが正しく動作する
- [ ] 全てのテストケースがパスする
