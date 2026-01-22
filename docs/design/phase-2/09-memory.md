# 09. 三層記憶システム

## 概要

Bot の記憶システムの基本概念を定義する。Phase-2 では概念定義とスタブ実装のみを行い、詳細な実装は後日追加要件確定後に行う。

**Note:** このタスクは基本構造のみを定義する。詳細実装は後回しとする。

## 依存タスク

- 02-database.md
- 08-person.md

## 三層記憶の概念

CLAUDE.md で定義された三層記憶システム:

| 層 | 説明 | 特性 | Phase-2 での実装 |
|----|------|------|-----------------|
| Working Memory | 現在の会話コンテキスト | 揮発性、Agent Loop 内で保持 | query_prompt 内で表現 |
| Short-term Memory | 最近のやり取り | 数時間〜数日保持 | SlackMessage で代替 |
| Long-term Memory | 永続的な記憶 | 永続保持、検索可能 | 後回し |

### Working Memory（Phase-2 実装）

**定義:**
- 現在処理中のイベントに関連する一時的なコンテキスト
- Agent Loop の1回の実行中のみ保持

**Phase-2 での表現:**
- `query_prompt` 内のメッセージ履歴として表現
- ツール呼び出しの結果も一時的に保持

**実装:**
- 特別なエンティティは不要
- SlackChannelUpdateHandler が構築する query_prompt がこれに相当

### Short-term Memory（Phase-2 実装）

**定義:**
- 最近の会話やインタラクションの記憶
- 数時間から数日間保持

**Phase-2 での表現:**
- SlackMessage エンティティで代替
- データベースに保存されたメッセージ履歴

**実装:**
- SlackMessage リポジトリの `get_by_channel()` で取得
- `context_messages` 件数で制限

### Long-term Memory（後回し）

**定義:**
- 永続的に保持すべき重要な記憶
- 人々の情報、学んだこと、重要な出来事

**将来の実装方針:**
- ベクトルデータベースによる類似検索
- Person との関連付け
- 自動要約・統合

## 成果物

### ファイル配置

```
src/myao3/
├── domain/
│   └── entities/
│       └── memory.py           # Memory 関連の型定義（スタブ）
└── application/
    └── services/
        └── memory_service.py   # MemoryService（スタブ）
```

### Memory 関連の型定義

**MemoryType 列挙型:**

| 値 | 説明 |
|-----|------|
| WORKING | Working Memory |
| SHORT_TERM | Short-term Memory |
| LONG_TERM | Long-term Memory |

### MemoryService Protocol

将来の記憶サービスのインターフェース定義。

**Phase-2 で定義するメソッド（スタブ）:**

| メソッド | 引数 | 戻り値 | 説明 |
|---------|------|--------|------|
| `get_relevant_memories` | context: str, limit: int | list[Memory] | 関連する記憶を取得 |
| `store_memory` | content: str, memory_type: MemoryType | None | 記憶を保存 |

**Phase-2 での実装:**
- 全てのメソッドは空実装（pass）または空リストを返す
- 将来の拡張ポイントとして定義のみ

### 将来の Memory エンティティ（Phase-2 では実装しない）

**想定フィールド:**

| フィールド | 型 | 説明 |
|-----------|-----|------|
| id | str | 記憶 ID（ULID） |
| content | str | 記憶の内容 |
| memory_type | MemoryType | 記憶の種類 |
| person_id | str \| None | 関連する Person |
| embedding | list[float] | ベクトル埋め込み |
| created_at | datetime | 作成時刻 |
| expires_at | datetime \| None | 有効期限 |

## Phase-2 における記憶の流れ

```
Slack Message 受信
        │
        ▼
┌─────────────────────────────┐
│ SlackMessage として保存      │
│ (Short-term Memory として機能) │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ SlackChannelUpdateHandler   │
│ がメッセージを取得           │
│ (Working Memory を構築)      │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ query_prompt として LLM に渡す │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ LLM が応答を生成            │
│ (Working Memory を使用)      │
└─────────────────────────────┘
```

## 将来の拡張計画

### Phase 3+ での実装予定

| 機能 | 説明 |
|------|------|
| Long-term Memory エンティティ | 永続記憶の保存 |
| ベクトル検索 | 類似記憶の検索 |
| 自動要約 | 会話の自動要約・統合 |
| Person との関連付け | 人物ごとの記憶管理 |
| 記憶の重要度判定 | 保存すべき記憶の自動判定 |

### 拡張ポイント

1. **query_prompt への記憶注入**
   - `SlackChannelUpdateHandler.build_query()` で Long-term Memory を取得
   - 関連する記憶を query_prompt に追加

2. **応答後の記憶保存**
   - Agent Loop 完了後に重要な情報を Long-term Memory に保存
   - LLM による重要度判定

3. **記憶の整理**
   - 定期的な記憶の要約・統合
   - 古い記憶の削除/アーカイブ

## テストケース

### TC-09-001: MemoryType 列挙型

**手順:**
1. MemoryType の各値にアクセス

**期待結果:**
- WORKING, SHORT_TERM, LONG_TERM が定義されている

### TC-09-002: MemoryService スタブ

**手順:**
1. MemoryService のスタブ実装を呼び出し

**期待結果:**
- エラーなく実行される
- `get_relevant_memories()` は空リストを返す

### TC-09-003: Working Memory としての query_prompt

**手順:**
1. SlackChannelUpdateHandler でメッセージを取得
2. query_prompt を生成

**期待結果:**
- メッセージ履歴が query_prompt に含まれる
- これが Working Memory として機能する

### TC-09-004: Short-term Memory としての SlackMessage

**手順:**
1. Slack メッセージを保存
2. 後から `get_by_channel()` で取得

**期待結果:**
- 保存したメッセージが取得できる
- これが Short-term Memory として機能する

## 完了条件

- [ ] MemoryType 列挙型が定義されている
- [ ] MemoryService Protocol が定義されている
- [ ] スタブ実装が作成されている
- [ ] Working Memory の概念が query_prompt で表現されている
- [ ] Short-term Memory が SlackMessage で代替されている
- [ ] 将来の拡張ポイントが明確に定義されている
- [ ] 全てのテストケースがパスする

**Note:** 詳細設計は後日追加要件確定後に作成する。
