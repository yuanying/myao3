## 8. 変更履歴

| バージョン | 日付 | 変更内容 |
|------------|------|----------|
| 0.1.0 | 2026-01-16 | 初版作成 |
| 0.2.0 | 2026-01-16 | ツール命名規則、自己改善範囲、記憶プライバシーポリシー、クロスプラットフォーム統合を追加 |
| 0.3.0 | 2026-01-16 | LLM設定（LiteLLM kwargs形式）を追加 |
| 0.4.0 | 2026-01-16 | プロジェクト名をmyao3に変更、PersonMemoryを単一strに簡素化、自己改善の承認フロー削除（ログ出力のみ）、遅延イベント・自己発火機能を追加 |
| 0.5.0 | 2026-01-16 | ツール定義をstrands-agents形式（@toolデコレータ、docstring、type hints）に修正 |
| 0.6.0 | 2026-01-16 | Phase 1をローカル実行のみに変更、Docker/K8sはPhase 2に移動 |
| 0.7.0 | 2026-01-16 | 単一インスタンス・逐次処理に簡素化（同時処理数1、複数インスタンス非対応） |
| 0.8.0 | 2026-01-16 | Agent Loop処理フロー詳細化（system_prompt構成、build_query_prompt、invocation_state、session manager不使用） |
| 0.9.0 | 2026-01-16 | Event.identity_keyによる重複制御、EventQueue（重複マージ、遅延エンキュー、処理状態トラッキング）を追加 |
| 0.10.0 | 2026-01-16 | Event.delayフィールドを削除（delayはenqueue時のパラメータとして指定） |
| 0.11.0 | 2026-05-04 | Long-term Memory を LLM Wiki 2段階方式に全面改訂（FR-MEMORY-001/002改訂、FR-MEMORY-004/005追加）、update_person_memory を write_wiki_page 等に置き換え、Section 2.1/3.2/5.2 更新 |
| 0.12.0 | 2026-05-10 | system_prompt をMarkdownプロンプト群の固定順合成方式へ変更し、自己改善を全文置換から限定的なprompt patch / dynamic note方式へ改訂 |
| 0.13.0 | 2026-05-10 | Agent Loop を会話単位の Strands Session 使用に変更し、DB/SQLite を技術スタックから削除。Slack は workspace_id を含む channel Session 単位で管理 |
| 0.14.0 | 2026-05-10 | 要求仕様書を docs/requirements/ に意味単位で分割し、requirements.md を入口ページに変更 |

---
