# 05. EventQueue

## 概要

重複制御と遅延エンキューをサポートするインメモリイベントキューを実装する。asyncio.Queue をベースにし、identity_key による重複制御を行う。

## 依存タスク

- 04-event-entity.md

## 成果物

### ファイル配置

```
src/myao3/infrastructure/
├── __init__.py
└── event_queue.py    # EventQueue 実装
```

### EventQueue クラス

**内部状態:**

| フィールド | 型 | 説明 |
|-----------|-----|------|
| _queue | asyncio.Queue[Event] | イベントキュー本体 |
| _pending | dict[str, Event] | 待機中イベント（identity_key → Event） |
| _processing | dict[str, Event] | 処理中イベント（event.id → Event） |
| _delay_tasks | dict[str, asyncio.Task] | 遅延エンキュータスク |

**メソッド:**

| メソッド | 引数 | 戻り値 | 説明 |
|---------|------|--------|------|
| enqueue | event, delay=None | None | イベントをキューに追加 |
| dequeue | - | Event | 次のイベントを取得 |
| mark_done | event | None | イベントの処理完了を記録 |
| pending_count | - | int | 待機中イベント数（プロパティ） |
| processing_count | - | int | 処理中イベント数（プロパティ） |

### 重複制御の仕組み

同じ identity_key を持つイベントが連続してエンキューされた場合、古いイベントは破棄され、新しいイベントのみが処理される。

**処理フロー:**

1. `enqueue(event)` 呼び出し
2. identity_key を取得
3. 同じ key の遅延タスクがあればキャンセル
4. `_pending[key] = event` で上書き
5. キューにイベントを追加

6. `dequeue()` 呼び出し
7. キューからイベントを取得
8. `_pending[key]` が取得したイベントと同一か確認
9. 同一でなければスキップ（古いイベント）
10. 同一なら `_pending` から削除し、`_processing` に移動
11. イベントを返す

### 遅延エンキュー

delay パラメータで指定した秒数後にイベントをキューに追加する。

**処理フロー:**

1. `enqueue(event, delay=30)` 呼び出し
2. 非同期タスクを作成し、`_delay_tasks[key]` に保存
3. タスク内で `await asyncio.sleep(delay)`
4. スリープ後、`_pending[key] = event` を設定
5. キューにイベントを追加

**遅延中のキャンセル:**

同じ identity_key で新しいイベントがエンキューされた場合、既存の遅延タスクはキャンセルされる。

### 処理状態トラッキング

処理中のイベントを追跡し、同じ key の新しいイベントをキューに入れられるようにする。

**処理フロー:**

1. `dequeue()` でイベント取得時、`_processing[event.id] = event` に記録
2. Agent Loop が処理を実行
3. `mark_done(event)` で `_processing` から削除

**同じ key のイベントが処理中に来た場合:**

- 新しいイベントは `_pending` に追加される
- 処理中のイベントは影響を受けない
- 新しいイベントは即座に dequeue 可能（複数イベントの同時処理をサポート）

## テストケース

### TC-05-001: 基本的な enqueue/dequeue

**手順:**
1. EventQueue を作成
2. PingEvent をエンキュー
3. dequeue で取得

**期待結果:**
- エンキューしたイベントが取得できる

### TC-05-002: 重複イベントのスキップ

**手順:**
1. EventQueue を作成
2. PingEvent①をエンキュー
3. PingEvent②をエンキュー（同じ identity_key）
4. dequeue を2回呼び出し

**期待結果:**
- 1回目の dequeue で②が返される
- 2回目の dequeue はブロック（待機状態）

### TC-05-003: 遅延エンキュー

**手順:**
1. EventQueue を作成
2. delay=0.1 で PingEvent をエンキュー
3. 即座に dequeue を呼び出し（タイムアウト付き）
4. 0.2秒待機後に再度 dequeue

**期待結果:**
- 最初の dequeue はタイムアウト
- 2回目の dequeue でイベントが取得できる

### TC-05-004: 遅延中のキャンセル

**手順:**
1. EventQueue を作成
2. PingEvent①を delay=1.0 でエンキュー
3. 0.1秒後に PingEvent②を delay=0 でエンキュー
4. dequeue で取得

**期待結果:**
- ②が取得される
- ①の遅延タスクはキャンセルされている

### TC-05-005: mark_done の動作

**手順:**
1. EventQueue を作成
2. イベントをエンキュー
3. dequeue で取得
4. processing_count を確認
5. mark_done を呼び出し
6. processing_count を再確認

**期待結果:**
- dequeue 後: processing_count == 1
- mark_done 後: processing_count == 0

### TC-05-006: 処理中に同じ key のイベントが来た場合

**手順:**
1. EventQueue を作成
2. PingEvent①をエンキュー
3. dequeue で①を取得（まだ mark_done しない）
4. PingEvent②をエンキュー
5. dequeue で②を取得
6. 両方 mark_done

**期待結果:**
- ①と②が両方取得できる
- 最終的に processing_count == 0

### TC-05-007: pending_count の確認

**手順:**
1. EventQueue を作成
2. pending_count を確認
3. イベントをエンキュー
4. pending_count を確認
5. dequeue
6. pending_count を確認

**期待結果:**
- 初期: 0
- エンキュー後: 1
- dequeue 後: 0

### TC-05-008: 複数の異なる identity_key

**手順:**
1. EventQueue を作成
2. 異なる identity_key を持つイベント A, B をエンキュー
3. dequeue を2回呼び出し

**期待結果:**
- 両方のイベントが取得できる（順序はエンキュー順）

## 完了条件

- [x] EventQueue クラスが実装されている
- [x] enqueue/dequeue が動作する
- [x] identity_key による重複制御が動作する
- [x] 遅延エンキューが動作する
- [x] 遅延中のキャンセルが動作する
- [x] mark_done で処理完了を記録できる
- [x] pending_count/processing_count が正しく更新される
- [x] 全てのテストケースがパスする
