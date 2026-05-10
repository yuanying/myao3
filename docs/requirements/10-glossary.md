## 7. 用語集

| 用語 | 定義 |
|------|------|
| Agent Loop | イベントを受けてLLMが思考し、ツールを呼び出すまでの一連の処理サイクル |
| Working Memory | 単一のAgent Loop内でのみ有効な一時的な記憶 |
| Short-term Memory | 会話単位の Strands Session に保持され、日次整理で Long-term Memory に反映される中期的な記憶 |
| Long-term Memory | 永続的に保持される長期的な記憶 |
| ツール | ボットが外部世界と相互作用するための明示的なインターフェース |
| イベント | 外部世界からボットに届く情報の単位 |
| identity_key | イベントの重複制御に使用するキー。同じキーのイベントはマージされる |
| EventQueue | 重複制御と遅延エンキューをサポートするインメモリキュー |
| 遅延イベント | `enqueue(event, delay=...)` で遅延指定されたイベント |
| 自己発火 | ボット自身が `emit_event` ツールで新しいイベントを生成すること |
| invocation_state | strands-agentsのツール間で共有される状態オブジェクト |
| CopilotKit UI | Slack連携前に記憶とコミュニケーションを検証するための独自チャットUI |
| Message Store | 外部Eventで受信した生メッセージをSQLModel / aiosqliteで保存するSQLite DB。SlackMessageなどプラットフォーム別テーブルで構成し、Session未収録メッセージの復元に使う |
| SessionExternalCursor | 外部メッセージソースごとに、Sessionへ反映済みの最後のメッセージ位置を保持するカーソル |
| system_prompt | Markdownプロンプト群 + Dynamic Notes + Short-term要約 + 実行時コンテキストを固定順で合成したLLMへの指示 |
| query_prompt | イベントタイプに応じて生成されるユーザークエリ |
| LLM Wiki | ファイルシステム上の Markdown ファイル群で構成される Long-term Memory |
| 段階的開示 | LLM が必要な時だけ wiki ツールで情報を取得する方式（一括埋め込みしない） |
| 夜間整理 | 毎日深夜に会話Sessionと notes/ から long-term ページと index.md を更新するプロセス |
| canonical_slug | 人物ページのファイル名（例: alice, taro-yamada） |
| Prompt Mode | 用途に応じて system_prompt の含有セクションを切り替えるモード（full / minimal / none） |
| Dynamic Notes | 自己改善で追加され、system_prompt 合成時に限定的に注入される行動メモ |

---
