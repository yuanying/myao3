## 6. 実装フェーズ

### Phase 1: 最小限の骨格（MVP）

**目標**: イベントを受信してAgent Loopが動作することを確認する

**実行環境**: ローカル（Python直接実行）

**スコープ**:
- [ ] イベント受信基盤（Pingのみ）
- [ ] EventQueue（重複制御、遅延エンキュー）
- [ ] 基本Agent Loop（ツールなし）
- [ ] ログ出力
- [ ] 設定ファイル読み込み（YAML）

**完了条件**:
- Pingイベントを送信すると、Agent Loopが起動し、ログに記録されて終了する
- 同じidentity_keyのイベントを連続送信すると、最新の1件のみ処理される
- `python -m myao3` でローカル実行できる

### Phase 2: CopilotKit UIでの記憶とコミュニケーション

**目標**: Slack連携の前に、CopilotKitを使った独自UIで記憶を持つ会話体験を実装する

**実行環境**: ローカル → Kubernetes

**スコープ**:
- [ ] CopilotKit を使った独自チャットUI
- [ ] UI会話単位の Strands Session
- [ ] 三層記憶システム
- [ ] 個人認識
- [ ] LLM Wiki 参照・更新ツール
- [ ] 日次記憶整理
- [ ] Dockerイメージ作成
- [ ] Kubernetes Deployment

**完了条件**:
- 独自UIから myao3 と会話できる
- 同じUI会話のSessionを継続し、文脈を踏まえて返答できる
- 会話内容が日次整理で notes/ と Long-term Memory に反映される
- Slack API や Slack App 設定なしで記憶とコミュニケーションを検証できる

### Phase 3: Slack連携

**目標**: Slackでメッセージを受信し、記憶を持ち、返答できる

**実行環境**: ローカル → Kubernetes

**スコープ**:
- [ ] Slack連携（メッセージ受信）
- [ ] Message Store（SQLModel / aiosqlite、SlackMessageテーブル）
- [ ] Slack channel 単位の Strands Session
- [ ] Session未収録SlackメッセージのDB復元
- [ ] メッセージ送信ツール
- [ ] リアクションツール
- [ ] Dockerイメージ作成
- [ ] Kubernetes Deployment

**完了条件**:
- Slackでメンションされると、文脈を踏まえた返答ができる
- Slack Event受信時にメッセージがDBへ冪等に保存される
- Agent処理時にSession未収録のSlackメッセージがDBから読み込まれ、入力メッセージに含まれる
- 同じSlack channelやチャット会話のSessionを継続し、文脈を踏まえて返答できる
- Kubernetesクラスタ上で稼働している

### Phase 4: 自律性の向上

**目標**: より自律的に判断し、自己改善の基盤を持つ

**スコープ**:
- [ ] Presenceイベント（オンライン/オフライン検知）
- [ ] スケジュールイベント（定期的な自己振り返り）
- [ ] 記憶の自動整理
- [ ] 自己改善フレームワーク（基盤のみ）

**完了条件**:
- ボットが自発的に（メンションなしで）会話を始めることがある
- 定期的に記憶を整理し、重要な情報を長期記憶に移行する

### Phase 5以降: 拡張

- 複数プラットフォーム対応
- 高度な自己改善
- 感情認識
- グループダイナミクスの理解

---
