# 09. 開発用スクリプト（hack/）

## 概要

開発・テスト用のスクリプトを hack/ ディレクトリに配置する。Phase 1 では Ping イベントを HTTP 経由で送信するスクリプトを実装する。

## 依存タスク

- 08-http-server.md

## 成果物

### ファイル配置

```
hack/
├── README.md         # hack/ ディレクトリの説明
└── send_ping.py      # Ping イベント発行スクリプト
```

### hack/README.md

hack/ ディレクトリの目的と使い方を説明する。

**内容:**

- ディレクトリの目的（開発・テスト用スクリプト）
- 各スクリプトの説明
- 使用例

### hack/send_ping.py

HTTP POST で Ping イベントを送信するスクリプト。

**コマンドライン引数:**

| 引数 | 短縮形 | デフォルト | 説明 |
|------|--------|-----------|------|
| --host | -H | localhost | サーバーホスト |
| --port | -p | 8080 | サーバーポート |
| --delay | -d | 0 | 遅延秒数 |
| --count | -n | 1 | 送信回数 |
| --interval | -i | 0.0 | 送信間隔（秒） |

**使用例:**

```bash
# 即座に Ping を送信（デフォルト: localhost:8080）
python hack/send_ping.py

# 30秒後に Ping を送信
python hack/send_ping.py --delay 30

# 3回連続で Ping を送信（重複制御テスト用）
python hack/send_ping.py --count 3 --interval 0.1

# 別ポートで起動中のアプリに送信
python hack/send_ping.py --port 9000

# 複数オプションを組み合わせ
python hack/send_ping.py -H 192.168.1.100 -p 9000 -d 10
```

**出力例:**

```
Sending ping to http://localhost:8080/api/v1/events...
[1/1] Event ID: 01HXYZ7W2Q4J5N6M8R9T0V1B3C (delay: 0s)
Done.
```

**エラー時の出力:**

```
Sending ping to http://localhost:8080/api/v1/events...
Error: Connection refused
```

### 機能

**基本機能:**

- HTTP POST で /api/v1/events に Ping イベントを送信
- レスポンスの event_id を表示
- エラー時は適切なメッセージを表示

**テスト支援機能:**

- 複数回連続送信（--count）: 重複制御のテストに使用
- 送信間隔（--interval）: 連続送信時の間隔を調整
- 遅延送信（--delay）: 遅延エンキューのテストに使用

### 依存関係

**標準ライブラリのみ使用:**

- argparse: コマンドライン引数
- http.client: HTTP リクエスト
- json: JSON 処理
- time: スリープ

**理由:**

- hack/ スクリプトは開発者が手軽に使えるべき
- 追加の依存関係インストールなしで実行可能

## テストケース

### TC-09-001: 基本的な Ping 送信

**前提条件:** アプリケーションが localhost:8080 で起動中

**手順:**
1. `python hack/send_ping.py` を実行

**期待結果:**
- 成功メッセージと event_id が表示される
- アプリケーション側でイベントが処理される

### TC-09-002: delay オプション

**前提条件:** アプリケーションが起動中

**手順:**
1. `python hack/send_ping.py --delay 10` を実行
2. アプリケーションのログを確認

**期待結果:**
- 即座にレスポンスが返る
- 10秒後にイベントが処理される

### TC-09-003: count オプション

**前提条件:** アプリケーションが起動中

**手順:**
1. `python hack/send_ping.py --count 3` を実行

**期待結果:**
- 3回のリクエストが送信される
- 各リクエストの結果が表示される

### TC-09-004: interval オプション

**前提条件:** アプリケーションが起動中

**手順:**
1. `python hack/send_ping.py --count 3 --interval 1.0` を実行
2. 送信タイミングを確認

**期待結果:**
- 各リクエストの間に1秒の間隔がある

### TC-09-005: 接続エラー

**前提条件:** アプリケーションが停止中

**手順:**
1. `python hack/send_ping.py` を実行

**期待結果:**
- 接続エラーメッセージが表示される
- スクリプトが正常に終了する（クラッシュしない）

### TC-09-006: host/port オプション

**前提条件:** アプリケーションが 192.168.1.100:9000 で起動中

**手順:**
1. `python hack/send_ping.py --host 192.168.1.100 --port 9000` を実行

**期待結果:**
- 指定したホスト・ポートにリクエストが送信される

### TC-09-007: ヘルプ表示

**手順:**
1. `python hack/send_ping.py --help` を実行

**期待結果:**
- 使用方法とオプションの説明が表示される

### TC-09-008: 重複制御のテスト

**前提条件:** アプリケーションが起動中

**手順:**
1. `python hack/send_ping.py --count 5 --interval 0.01` を実行
2. アプリケーションのログを確認

**期待結果:**
- 5回リクエストが送信される
- 処理されるのは最後の1件のみ（identity_key="ping" の重複制御）

## 完了条件

- [x] hack/README.md が作成されている
- [x] hack/send_ping.py が実装されている
- [x] 標準ライブラリのみで動作する
- [x] 全てのコマンドラインオプションが動作する
- [x] エラー時に適切なメッセージが表示される
- [ ] 全てのテストケースがパスする
