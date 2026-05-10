## 3.3 CopilotKit 独自UI

#### FR-UI-001: CopilotKit による独自チャットUI

| 項目 | 内容 |
|------|------|
| 概要 | Slack連携の前段階として、CopilotKitを使った独自UIで myao3 と会話できる |
| 優先度 | 高 |
| フェーズ | Phase 2 |

**目的**:

Slack連携に入る前に、外部プラットフォーム依存の少ない独自UIで、記憶とコミュニケーションの基本体験を検証する。CopilotKit は React ベースのチャットUI、Generative UI、共有state、Agent接続を提供するため、myao3 の Agent Loop と記憶システムを人間が直接試す入口として利用する。

**スコープ**:

| 項目 | 内容 |
|------|------|
| チャットUI | ユーザーが myao3 にメッセージを送り、応答を受け取れる |
| Session連携 | UI会話ごとに Strands Session を作成・継続する |
| 記憶参照 | Agent Loop が必要に応じて LLM Wiki を読む |
| 記憶保存 | 日次整理で UI Session を notes/ と Long-term Memory に反映する |
| 状態共有 | UI上の選択状態や表示中コンテキストを Agent に渡せる |
| Generative UI | 必要に応じて記憶・人物・話題などを専用コンポーネントとして表示できる |

**Session ID**:

```text
copilotkit:{user_id}:conversation:{conversation_id}
```

`conversation_id` はUI上の会話単位で発行する。Slack channel Session とは別系統にし、Slack連携前でも記憶と会話の動作を検証できるようにする。

**非スコープ**:

| 非スコープ | 理由 |
|------------|------|
| Slackイベント受信 | Slack連携は次フェーズで扱う |
| Slackメッセージ送信 | 独自UIでは CopilotKit のチャット応答を使う |
| 複数ユーザーの権限管理 | 初期UIでは管理者または単一ユーザー利用を前提にする |

**受け入れ条件**:

- 独自UIからメッセージを送ると Agent Loop が起動する
- 同じUI会話を開き直しても Session によって文脈が継続する
- 会話内容が日次整理で `notes/YYYY-MM-DD.md` に要約される
- 重要な人物・話題・関係性が Long-term Memory に反映される
- Slack API や Slack App 設定なしで記憶とコミュニケーションを検証できる

