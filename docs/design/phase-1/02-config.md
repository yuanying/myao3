# 02. 設定ファイル読み込み

## 概要

YAML 形式の設定ファイルを読み込み、環境変数を展開して Pydantic モデルに変換する機能を実装する。

## 依存タスク

- 01-project-setup.md

## 成果物

### ファイル配置

```
src/myao3/config/
├── __init__.py
├── loader.py      # 設定読み込み
└── models.py      # Pydantic モデル定義
```

### Pydantic 設定モデル

**LLMConfig:**

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| model_id | str | ○ | LiteLLM 形式のモデル ID |
| params | dict[str, Any] | - | LLM パラメータ |
| client_args | dict[str, Any] | - | クライアント引数 |

**AgentConfig:**

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| system_prompt | str | ○ | Agent の system prompt |
| llm | LLMConfig | ○ | LLM 設定 |

**ServerConfig:**

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| host | str | - | "0.0.0.0" | HTTP サーバーホスト |
| port | int | - | 8080 | HTTP サーバーポート |

**LoggingConfig:**

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| level | str | - | "INFO" | ログレベル |
| format | str | - | "json" | ログフォーマット |

**AppConfig:**

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| agent | AgentConfig | ○ | Agent 設定 |
| server | ServerConfig | - | サーバー設定 |
| logging | LoggingConfig | - | ログ設定 |

### 設定ローダー

**機能:**

1. YAML ファイルの読み込み
2. 環境変数展開（`${VAR_NAME}` 形式）
3. Pydantic モデルへの変換とバリデーション

**環境変数展開のルール:**

- `${VAR_NAME}` 形式で環境変数を参照
- 存在しない環境変数はエラー
- ネストした dict/list 内も再帰的に展開

## テストケース

### TC-02-001: 正常な設定ファイルの読み込み

**前提条件:** 有効な YAML 設定ファイルが存在する

**入力:**
```yaml
agent:
  system_prompt: "You are a helpful assistant."
  llm:
    model_id: "anthropic/claude-sonnet-4-20250514"
server:
  port: 9000
```

**期待結果:**
- AppConfig が正しく生成される
- agent.system_prompt が "You are a helpful assistant."
- agent.llm.model_id が "anthropic/claude-sonnet-4-20250514"
- server.port が 9000
- server.host がデフォルト値 "0.0.0.0"

### TC-02-002: 環境変数の展開

**前提条件:** 環境変数 `API_KEY=test-key` が設定されている

**入力:**
```yaml
agent:
  system_prompt: "Test"
  llm:
    model_id: "test/model"
    client_args:
      api_key: ${API_KEY}
```

**期待結果:**
- agent.llm.client_args.api_key が "test-key"

### TC-02-003: 存在しない環境変数でエラー

**前提条件:** 環境変数 `UNDEFINED_VAR` が設定されていない

**入力:**
```yaml
agent:
  system_prompt: ${UNDEFINED_VAR}
  llm:
    model_id: "test/model"
```

**期待結果:** 環境変数が見つからないエラーが発生

### TC-02-004: 必須フィールドが欠落している場合のエラー

**入力:**
```yaml
server:
  port: 8080
```

**期待結果:** agent フィールドが必須というバリデーションエラー

### TC-02-005: 無効な YAML 形式

**入力:**
```
invalid: yaml: format:
```

**期待結果:** YAML パースエラー

### TC-02-006: ファイルが存在しない場合

**入力:** 存在しないファイルパス

**期待結果:** ファイルが見つからないエラー

## 完了条件

- [ ] Pydantic 設定モデルが定義されている
- [ ] YAML ファイルを読み込める
- [ ] 環境変数（`${VAR_NAME}` 形式）が展開される
- [ ] バリデーションエラーが適切に報告される
- [ ] 全てのテストケースがパスする
