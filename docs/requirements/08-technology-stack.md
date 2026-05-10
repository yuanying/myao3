## 5. 技術スタック

### 5.1 コア技術

| 領域 | 技術 | 用途 |
|------|------|------|
| 言語 | Python 3.12+ | メイン実装言語 |
| 非同期 | asyncio | イベント駆動処理 |
| Agent Framework | strands-agents | LLMエージェント実装 |
| LLM Gateway | LiteLLM | 複数LLMプロバイダ対応 |
| Frontend | React / TypeScript | 独自UI実装 |
| Agentic UI | CopilotKit | チャットUI、Generative UI、Agent接続 |

### 5.2 インフラ

| 領域 | 技術 | 備考 |
|------|------|------|
| コンテナ | Docker | アプリケーションパッケージング |
| オーケストレーション | Kubernetes | ホームクラスタにデプロイ |
| ストレージ (Session) | ファイルシステム (Longhorn PVC) | 会話単位の Strands Session 永続化 |
| ストレージ (Wiki) | ファイルシステム (Longhorn PVC) | Long-term Memory（Wiki）の永続化 |
| ストレージ (Prompt) | ファイルシステム (Longhorn PVC) | Markdownプロンプト原本の永続化 |

### 5.3 外部連携

| プラットフォーム | SDK/API | フェーズ |
|------------------|---------|----------|
| 独自UI | CopilotKit | Phase 2 |
| Slack | slack-sdk (async) | Phase 3 |
| Discord | discord.py | 将来 |
| Email | aiosmtplib | 将来 |

### 5.4 LLM設定

LLMの設定はLiteLLMに渡すパラメータをそのまま記述できる形式とする。これにより、LiteLLMがサポートする任意のプロバイダ・モデルを利用可能。

**設定ファイル形式** (YAML):

```yaml
llm:
  # Agent Loopで使用するメインLLM
  agent:
    model_id: "anthropic/claude-sonnet-4-20250514"
    params:
      temperature: 0.7
      max_tokens: 4096
    client_args:
      api_key: ${ANTHROPIC_API_KEY}

  # 記憶の要約・整理に使用するLLM（コスト最適化用に分離可能）
  memory:
    model_id: "openai/gpt-4o-mini"
    params:
      temperature: 0.3
      max_tokens: 2048
    client_args:
      api_key: ${OPENAI_API_KEY}

  # 自己改善の提案生成に使用するLLM
  improvement:
    model_id: "anthropic/claude-sonnet-4-20250514"
    params:
      temperature: 0.5
      max_tokens: 4096
    client_args:
      api_key: ${ANTHROPIC_API_KEY}
```

**設定項目**:

| 項目 | 必須 | 説明 |
|------|------|------|
| `model_id` | ✓ | LiteLLM形式のモデル識別子 (`provider/model`) |
| `params` | | LLM呼び出し時のパラメータ (`temperature`, `max_tokens`, etc.) |
| `client_args` | | LiteLLMクライアント初期化時の引数 (`api_key`, `api_base`, etc.) |

**環境変数展開**:

`${ENV_VAR}` 形式で環境変数を参照可能。これによりSecretとの連携が容易になる。

**実装イメージ**:

```python
from litellm import acompletion

class LLMConfig(BaseModel):
    model_id: str
    params: dict = {}
    client_args: dict = {}

async def call_llm(config: LLMConfig, messages: list[dict]) -> str:
    response = await acompletion(
        model=config.model_id,
        messages=messages,
        **config.params,
        **config.client_args,
    )
    return response.choices[0].message.content
```

**用途別LLM分離の理由**:

| 用途 | 要件 | 推奨 |
|------|------|------|
| Agent Loop | 高い推論能力、ツール呼び出し | 高性能モデル |
| 記憶処理 | 要約・分類、大量処理 | コスト効率の良いモデル |
| 自己改善 | 慎重な判断、自己認識 | 高性能モデル |

---
