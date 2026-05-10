# myao3 要求仕様書

**バージョン**: 0.14.0  
**作成日**: 2026-01-16  
**ステータス**: Draft

このディレクトリは myao3 の要求仕様書を意味単位で分割したものです。全体を読む場合は以下の順に参照してください。

## ドキュメント一覧

| 順序 | ドキュメント | 内容 |
|------|--------------|------|
| 1 | [概要](01-overview.md) | 目的、ビジョン、基本原則 |
| 2 | [システムコンセプト](02-system-concept.md) | 世界認識モデル、コア設計思想 |
| 3 | [イベント処理](03-events.md) | イベント型、EventQueue、遅延イベント、Ping |
| 4 | [Agent Loop](04-agent-loop.md) | Session、system_prompt、query_prompt、ツール呼び出し |
| 5 | [記憶システム](05-memory.md) | Session、LLM Wiki、個人認識、日次整理、プライバシー |
| 6 | [自己改善](06-self-improvement.md) | prompt patch、Dynamic Notes、自己改善制約 |
| 7 | [非機能要件](07-non-functional-requirements.md) | 性能、可用性、拡張性、セキュリティ、運用性 |
| 8 | [技術スタック](08-technology-stack.md) | コア技術、インフラ、外部連携、LLM設定 |
| 9 | [実装フェーズ](09-implementation-phases.md) | Phase 1 から Phase 4 以降のスコープ |
| 10 | [用語集](10-glossary.md) | 主要用語の定義 |
| 11 | [変更履歴](11-changelog.md) | バージョンごとの変更内容 |
| 12 | [未決定事項](12-tbd.md) | TBD項目 |

## 原則

- `requirements.md` は入口だけを残し、本文はこのディレクトリで管理する。
- 機能要件は大きくなりやすいため、イベント、Agent Loop、記憶、自己改善に分ける。
- 変更履歴は [変更履歴](11-changelog.md) に集約する。
