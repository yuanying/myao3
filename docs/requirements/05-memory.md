## 3.3 記憶システム

#### FR-MEMORY-001: 三層記憶アーキテクチャ

| 項目 | 内容 |
|------|------|
| 概要 | Working / Short-term / Long-term の三層で記憶を管理する |
| 優先度 | 必須 |
| フェーズ | Phase 2 |

**各層の定義**:

| 層 | 保持期間 | 容量 | 用途 | 実装 |
|----|----------|------|------|------|
| Working Memory | 単一Agent Loop内 | 制限なし | 現在の処理コンテキスト | LLMのコンテキストウィンドウ |
| Short-term Memory | 数時間〜数日 | 制限あり | 最近の会話、一時的な文脈 | Strands Session（会話単位） |
| Long-term Memory | 永続 | 制限あり | 個人の特徴、重要な出来事、学習内容 | LLM Wiki（ファイルシステム） |

**Session → Long-term Memory 2段階方式**:

```
ループ内（随時）
  → 会話単位の Strands Session にメッセージ、tool call、tool result を保存

毎日夜中（日次整理）
  → 前日分の Session を読み、notes/YYYY-MM-DD.md に要約・重要事項を保存
  → notes/ を読み、people/, topics/, communities/, self.md を更新
  → index.md を最新状態に更新
```

#### FR-MEMORY-002: 個人認識

| 項目 | 内容 |
|------|------|
| 概要 | 複数コミュニティを跨いで個人を認識・記憶する |
| 優先度 | 高 |
| フェーズ | Phase 2 |

**データモデル（Wiki ページ）**:

人物情報は `people/{canonical_slug}.md` が canonical source。人物認識のためのDBモデルは持たない。

```markdown
# Person: alice

## Identity
- Slack: U1234567 (@alice)
- Discord: alice_dev (確認: 2026-05-04)
- ※未確認候補: matrix上の @alice:example.org

## Personality & Communication Style
（LLM 自由記述）

## Interests & Expertise
（LLM 自由記述）

## Relationship
（このボットとの関係）

## Conversation Summaries
### 2026-05-04
（その日の会話の要点）

## Notes
（秘密・特記事項など）
```

**Person 識別の考え方**:

```
初回遭遇（Slack で @alice に会う）
  → notes/YYYY-MM-DD.md に "Slack U1234567 @alice: ..." を記録

夜間整理
  → people/alice.md を作成（なければ）
  → ## Identity に "Slack: U1234567 (@alice)" を追記
  → index.md の People セクションを更新

別プラットフォームで alice_dev として遭遇
  → notes/ に記録 → 夜間整理で同一人物と判断 → ## Identity に追記
```

**方針**:
- 人物情報はファイルベース、プラットフォーム非依存
- 複数アカウントは ## Identity セクションに列挙
- 同一人物判定・マージは夜間整理で LLM が実施

#### FR-MEMORY-004: LLM Wiki

| 項目 | 内容 |
|------|------|
| 概要 | Long-term Memory をファイルシステム上の Markdown Wiki として実装する |
| 優先度 | 高 |
| フェーズ | Phase 2 |

**段階的開示（Progressive Disclosure）**:

Wiki コンテンツは system_prompt に一括埋め込みしない。LLM がツールで「必要な情報を必要な時だけ」取得する。

```
Agent Loop 開始
        │
        ├─ [system_prompt] 「長期記憶が必要なときは
        │   read_wiki_page("index") から始めて
        │   必要なページを読んでください」
        │
        ├─ read_wiki_page("index")      ← 誰・何を知っているかの概要
        │     → 今の文脈に関係ありそうな人物・話題を確認
        │
        ├─ read_wiki_page("people/alice")  ← alice に言及された場合のみ
        │
        └─ read_wiki_page("topics/kubernetes")  ← Kubernetes が話題の場合のみ
```

**Wiki ディレクトリ構造**:

```
data/wiki/
├── index.md                    # エントリーポイント（夜間整理で更新）
├── notes/                      # 短期メモ（ループ内で随時更新）
│   └── YYYY-MM-DD.md           # 日付ごとの出来事・プラットフォーム ID を含む生メモ
├── people/                     # 長期記憶: 人物ページ（プラットフォーム非依存）
│   └── {canonical_slug}.md     # e.g. alice.md, taro-yamada.md
├── topics/                     # 長期記憶: 話題・概念
│   └── {slug}.md
├── communities/                # 長期記憶: コミュニティ
│   └── slack/
│       ├── index.md
│       └── {channel_id}.md
└── self.md                     # ボット自身の人格・成長記録
```

**ツール定義**:

```python
@tool
def read_wiki_page(page_path: str) -> str:
    """Read a wiki page for long-term memory recall.
    Start with "index" to see what knowledge is available.
    Args:
        page_path: Path within wiki (e.g., "index", "people/alice", "notes/2026-05-04")
    """

@tool
def write_wiki_page(page_path: str, content: str) -> str:
    """Write or update a wiki page to store memory.
    Args:
        page_path: Path within wiki
        content: Full markdown content
    """

@tool
def search_wiki(query: str, category: str | None = None) -> str:
    """Search wiki pages for relevant information.
    Args:
        query: Search keywords
        category: Optional filter ("people", "topics", "communities", "notes")
    """

@tool
def list_wiki_pages(category: str | None = None) -> str:
    """List wiki pages, optionally filtered by category."""
```

#### FR-MEMORY-005: 日次記憶整理

| 項目 | 内容 |
|------|------|
| 概要 | 毎日深夜に会話Sessionを整理し、notes/・長期記憶ページ・index.md を更新する |
| 優先度 | 高 |
| フェーズ | Phase 2 |

**仕組み**:

FR-EVENT-004（遅延イベント・自己発火）を活用し、毎日 0:00 に `memory_consolidation` イベントを発火する。

```
日次整理フロー:
  1. 前日分の会話Sessionを読む
  2. notes/YYYY-MM-DD.md に会話要約・重要事項・未整理の観測を保存
  3. 関連する long-term ページを読む
  4. 同一人物判定 → 必要ならページをマージ
  5. people/, topics/, communities/, self.md を更新
  6. index.md を最新状態に更新
```

**index.md フォーマット**:

```markdown
# Wiki Index

*Last updated: 2026-05-04*

## Self
My personality and growth log → [self](self.md)

## People I Know
- [alice](people/alice.md) (Slack: @alice)
- [taro-yamada](people/taro-yamada.md) (Slack: @taro)

## Topics
- [kubernetes](topics/kubernetes.md)

## Communities
- [Slack workspace](communities/slack/index.md)

## Recent Notes
- [2026-05-04](notes/2026-05-04.md)
```

#### FR-MEMORY-003: 記憶プライバシーポリシー

| 項目 | 内容 |
|------|------|
| 概要 | 記憶の取り扱いに関するポリシーを定義する |
| 優先度 | 高 |
| フェーズ | Phase 2 |

**基本方針**:

- ボットはパブリックな場（チャンネル等）での発言を対象とする
- プライベートチャット機能は提供しない
- 記憶に制限は設けず、観測した情報は記憶の対象となる

**秘密の取り扱い**:

- ユーザーが「他の人に言わないで」等と依頼した場合、その旨をメモリに記載
- LLMはメモリの文脈から秘密情報を判断し、他のユーザーとの会話で出力しない
- **管理者は Session ファイルと Wiki ファイルを通じて全ての記憶を閲覧可能**

**管理者の権限**:

| 権限 | 説明 |
|------|------|
| 記憶の閲覧 | 全ユーザーの全記憶を閲覧可能 |
| 記憶の編集 | 任意の記憶を直接編集可能 |
| 記憶の削除 | 任意の記憶を削除可能 |
| 統計の確認 | 記憶の量、傾向などを確認可能 |
