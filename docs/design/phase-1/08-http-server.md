# 08. HTTP サーバー（イベント受信）

## 概要

aiohttp を使用した HTTP サーバーを実装する。イベント受信エンドポイントとヘルスチェックエンドポイントを提供する。

## 依存タスク

- 05-event-queue.md
- 06-agent-loop.md

## 成果物

### ファイル配置

```
src/myao3/presentation/http/
├── __init__.py
└── server.py     # HTTP サーバー実装
```

### エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| POST | /api/v1/events | イベント受信 |
| GET | /healthz | Liveness チェック |

### POST /api/v1/events

**リクエストボディ:**

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| type | string | ○ | イベントタイプ（"ping"） |
| payload | object | - | イベント固有データ |
| delay | integer | - | 遅延秒数（デフォルト: 0） |

**リクエスト例:**

```json
{
  "type": "ping",
  "payload": {},
  "delay": 0
}
```

**成功レスポンス（200 OK）:**

```json
{
  "event_id": "01HXYZ7W2Q4J5N6M8R9T0V1B3C"
}
```

**エラーレスポンス（400 Bad Request）:**

```json
{
  "error": "Invalid event type: unknown"
}
```

**エラーレスポンス（500 Internal Server Error）:**

```json
{
  "error": "Failed to enqueue event"
}
```

### GET /healthz

Kubernetes Liveness Probe 用のエンドポイント。

**レスポンス（200 OK）:**

```json
{
  "status": "ok"
}
```

**特性:**

- 常に 200 OK を返す
- アプリケーションが起動していることを確認するのみ
- Readiness チェックは Phase 2 以降で検討

### HTTPServer クラス

**コンストラクタ引数:**

| 引数 | 型 | 説明 |
|------|-----|------|
| config | ServerConfig | サーバー設定 |
| event_queue | EventQueue | イベントキュー |
| logger | Logger | ロガー |

**メソッド:**

| メソッド | 引数 | 戻り値 | 説明 |
|---------|------|--------|------|
| start | - | None | サーバー起動 |
| stop | - | None | サーバー停止 |

### イベント生成

リクエストから Event オブジェクトを生成する。

**処理フロー:**

1. リクエストボディをパース
2. type からイベントクラスを決定
3. Event を生成（ID は自動生成）
4. EventQueue にエンキュー

**サポートするイベントタイプ（Phase 1）:**

| type | クラス |
|------|--------|
| "ping" | PingEvent |

### エラーハンドリング

| エラー | ステータス | メッセージ |
|--------|-----------|-----------|
| JSON パースエラー | 400 | "Invalid JSON" |
| 必須フィールド欠落 | 400 | "Missing required field: type" |
| 無効なイベントタイプ | 400 | "Invalid event type: {type}" |
| エンキュー失敗 | 500 | "Failed to enqueue event" |

## テストケース

### TC-08-001: Ping イベントの受信

**手順:**
1. HTTP サーバーを起動
2. POST /api/v1/events に {"type": "ping"} を送信
3. レスポンスを確認

**期待結果:**
- ステータス 200 OK
- event_id が含まれる
- イベントが EventQueue に追加される

### TC-08-002: delay 付きイベントの受信

**手順:**
1. HTTP サーバーを起動
2. {"type": "ping", "delay": 10} を送信
3. レスポンスとキューの状態を確認

**期待結果:**
- ステータス 200 OK
- イベントが遅延エンキューされる

### TC-08-003: payload 付きイベントの受信

**手順:**
1. HTTP サーバーを起動
2. {"type": "ping", "payload": {"key": "value"}} を送信
3. キューのイベントを確認

**期待結果:**
- イベントの payload に {"key": "value"} が含まれる

### TC-08-004: 無効な JSON

**手順:**
1. HTTP サーバーを起動
2. 無効な JSON を送信

**期待結果:**
- ステータス 400 Bad Request
- "Invalid JSON" エラー

### TC-08-005: type フィールドの欠落

**手順:**
1. HTTP サーバーを起動
2. {"payload": {}} を送信

**期待結果:**
- ステータス 400 Bad Request
- "Missing required field: type" エラー

### TC-08-006: 無効なイベントタイプ

**手順:**
1. HTTP サーバーを起動
2. {"type": "unknown"} を送信

**期待結果:**
- ステータス 400 Bad Request
- "Invalid event type: unknown" エラー

### TC-08-007: ヘルスチェック

**手順:**
1. HTTP サーバーを起動
2. GET /healthz を送信

**期待結果:**
- ステータス 200 OK
- {"status": "ok"}

### TC-08-008: サーバー起動と停止

**手順:**
1. HTTP サーバーを起動
2. リクエストが処理されることを確認
3. サーバーを停止
4. リクエストが拒否されることを確認

**期待結果:**
- 起動中はリクエストが処理される
- 停止後はリクエストが拒否される

### TC-08-009: 設定からのホスト・ポート読み込み

**手順:**
1. host=127.0.0.1, port=9000 で ServerConfig を作成
2. HTTP サーバーを起動
3. 127.0.0.1:9000 にリクエスト

**期待結果:**
- 指定したホスト・ポートでサーバーが起動する

### TC-08-010: Content-Type の確認

**手順:**
1. HTTP サーバーを起動
2. レスポンスの Content-Type を確認

**期待結果:**
- Content-Type: application/json

## 完了条件

- [ ] aiohttp を使用した HTTP サーバーが実装されている
- [ ] POST /api/v1/events でイベントを受信できる
- [ ] GET /healthz でヘルスチェックできる
- [ ] delay パラメータで遅延エンキューできる
- [ ] エラーが適切な JSON 形式で返される
- [ ] 全てのテストケースがパスする
