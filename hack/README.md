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

### test_llm.py

strands-agents + LiteLLM を使用して LLM 設定をテストするスクリプト。

**使用方法:**

```bash
uv run python hack/test_llm.py [オプション]
```

**オプション:**

| オプション | 短縮形 | デフォルト | 説明 |
|-----------|--------|-----------|------|
| --config | -c | config.yaml | 設定ファイルのパス |
| --message | -m | "こんにちは。自己紹介をしてください。" | 送信するメッセージ |
| --system-prompt | -s | 設定ファイルの値 | システムプロンプト |
| --no-system-prompt | | | システムプロンプトを使用しない |
| --verbose | -v | | 詳細な出力を表示 |

**使用例:**

```bash
# 基本的なテスト（設定ファイルの system_prompt を使用）
uv run python hack/test_llm.py

# カスタムメッセージを送信
uv run python hack/test_llm.py -m "Kubernetesについて教えて"

# システムプロンプトなしでテスト
uv run python hack/test_llm.py --no-system-prompt -m "Hello"

# 詳細出力でデバッグ
uv run python hack/test_llm.py -v

# 別の設定ファイルを使用
uv run python hack/test_llm.py -c config.yaml.example
```

**出力例:**

```
Loading config from: config.yaml
Creating LiteLLMModel with model_id: ollama/gpt-oss:120b
Creating Agent...
Sending message: こんにちは。自己紹介をしてください。
----------------------------------------
あの…ニャーはミャオにゃ。クラウドネイティブエンジニアをしてるにゃ…
----------------------------------------
Done.
```

## 注意事項

- `send_ping.py`: 標準ライブラリのみを使用、`python hack/send_ping.py` で実行
- `test_llm.py`: プロジェクトの依存関係が必要、`uv run python hack/test_llm.py` で実行
