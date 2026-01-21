# hack/

開発・テスト用スクリプト集。

## スクリプト一覧

### send_ping.py

HTTP 経由で Ping イベントをサーバーに送信するスクリプト。

**使用方法:**

```bash
python hack/send_ping.py [オプション]
```

**オプション:**

| オプション | 短縮形 | デフォルト | 説明 |
|-----------|--------|-----------|------|
| --host | -H | localhost | サーバーホスト |
| --port | -p | 8080 | サーバーポート |
| --delay | -d | 0 | 遅延秒数 |
| --count | -n | 1 | 送信回数 |
| --interval | -i | 0.0 | 送信間隔（秒） |

**使用例:**

```bash
# 基本的な Ping 送信
python hack/send_ping.py

# 10秒遅延で Ping 送信
python hack/send_ping.py --delay 10

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

## 注意事項

- 標準ライブラリのみを使用しているため、追加の依存関係なしで実行可能
- 常に `python hack/send_ping.py` で明示的に実行する
