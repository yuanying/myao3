# 11. Kubernetes Deployment

## 概要

myao3 を Kubernetes クラスタ上で運用するためのマニフェストを作成する。Deployment、Service、PersistentVolumeClaim、ConfigMap、Secret の各リソースを定義する。

## 依存タスク

- 10-docker.md

## 成果物

### ファイル配置

```
k8s/
├── namespace.yaml          # Namespace 定義
├── configmap.yaml          # ConfigMap（config.yaml）
├── secret.yaml.example     # Secret テンプレート
├── pvc.yaml                # PersistentVolumeClaim
├── deployment.yaml         # Deployment
└── service.yaml            # Service
```

### Namespace

**リソース名:** `myao3`

アプリケーション専用の Namespace を作成し、リソースを分離。

### ConfigMap

**リソース名:** `myao3-config`

config.yaml をマウントするための ConfigMap。

**マウント先:** `/config/config.yaml`

**内容:**
- Slack 設定（トークン以外）
- データベース設定
- ログ設定
- Agent 設定

**Note:** 機密情報（トークン等）は Secret で管理し、環境変数として注入。

### Secret

**リソース名:** `myao3-secrets`

機密情報を格納する Secret。

**キー:**

| キー | 説明 |
|------|------|
| SLACK_BOT_TOKEN | Slack Bot Token |
| SLACK_APP_TOKEN | Slack App Token |

**secret.yaml.example:**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: myao3-secrets
  namespace: myao3
type: Opaque
stringData:
  SLACK_BOT_TOKEN: "xoxb-your-bot-token"
  SLACK_APP_TOKEN: "xapp-your-app-token"
```

**Note:** 実際の secret.yaml は .gitignore に追加し、Git にコミットしない。

### PersistentVolumeClaim

**リソース名:** `myao3-data`

SQLite データベースの永続化用 PVC。

**スペック:**

| 項目 | 値 | 説明 |
|------|-----|------|
| accessModes | ReadWriteOnce | 単一ノードからの読み書き |
| storage | 1Gi | 初期サイズ |
| storageClassName | （環境依存） | 省略時はデフォルト |

**マウント先:** `/data`

**設計根拠:**
- SQLite は単一プロセスからのアクセスを想定
- replicas: 1 のため ReadWriteOnce で十分

### Deployment

**リソース名:** `myao3`

**スペック:**

| 項目 | 値 | 説明 |
|------|-----|------|
| replicas | 1 | SQLite 使用のため単一レプリカ |
| strategy | Recreate | ダウンタイム許容、DB ロック回避 |

**Pod テンプレート:**

| 項目 | 値 |
|------|-----|
| image | myao3:latest |
| imagePullPolicy | IfNotPresent |

**ボリュームマウント:**

| ボリューム | マウント先 | 読み取り専用 |
|-----------|-----------|-------------|
| config | /config | ○ |
| data | /data | - |

**環境変数:**
- Secret から `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN` を注入

**リソース制限:**

| リソース | requests | limits |
|----------|----------|--------|
| cpu | 100m | 500m |
| memory | 256Mi | 512Mi |

**ヘルスチェック:**

| 項目 | 値 |
|------|-----|
| livenessProbe | HTTP GET /health |
| readinessProbe | HTTP GET /health |
| initialDelaySeconds | 10 |
| periodSeconds | 30 |

### Service

**リソース名:** `myao3`

**スペック:**

| 項目 | 値 | 説明 |
|------|-----|------|
| type | ClusterIP | クラスタ内部のみ |
| port | 80 | Service ポート |
| targetPort | 8080 | コンテナポート |

**Note:** Socket Mode 使用のため、外部からの Ingress は不要。ヘルスチェック用途のみ。

### Deployment 戦略

**Recreate を選択する理由:**
- SQLite は同時に複数プロセスからの書き込みをサポートしない
- RollingUpdate だと新旧 Pod が同時に DB にアクセスする可能性
- Recreate により、常に1つの Pod のみがアクティブ

**トレードオフ:**
- デプロイ時に短時間のダウンタイムが発生
- メッセージは Slack 側でバッファされ、再接続後に処理可能

### マニフェスト適用順序

```bash
# 1. Namespace 作成
kubectl apply -f k8s/namespace.yaml

# 2. Secret 作成（事前に secret.yaml を準備）
kubectl apply -f k8s/secret.yaml

# 3. ConfigMap 作成
kubectl apply -f k8s/configmap.yaml

# 4. PVC 作成
kubectl apply -f k8s/pvc.yaml

# 5. Deployment & Service 作成
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

**一括適用:**

```bash
kubectl apply -f k8s/
```

### 運用コマンド

**ログ確認:**

```bash
kubectl logs -f deployment/myao3 -n myao3
```

**Pod 状態確認:**

```bash
kubectl get pods -n myao3
```

**Pod 再起動:**

```bash
kubectl rollout restart deployment/myao3 -n myao3
```

**設定更新:**

```bash
kubectl apply -f k8s/configmap.yaml
kubectl rollout restart deployment/myao3 -n myao3
```

## テストケース

### TC-11-001: マニフェスト構文検証

**手順:**
1. `kubectl apply --dry-run=client -f k8s/` を実行

**期待結果:**
- 全マニフェストが構文的に正しい
- エラーが発生しない

### TC-11-002: Namespace 作成

**手順:**
1. `kubectl apply -f k8s/namespace.yaml` を実行
2. `kubectl get ns myao3` を確認

**期待結果:**
- Namespace が作成される

### TC-11-003: PVC 作成

**手順:**
1. `kubectl apply -f k8s/pvc.yaml` を実行
2. `kubectl get pvc -n myao3` を確認

**期待結果:**
- PVC が Bound 状態になる

### TC-11-004: Deployment 作成

**手順:**
1. Secret, ConfigMap, PVC を事前作成
2. `kubectl apply -f k8s/deployment.yaml` を実行
3. Pod 状態を確認

**期待結果:**
- Pod が Running 状態になる
- レプリカ数が 1

### TC-11-005: ヘルスチェック

**手順:**
1. Deployment を作成
2. Pod が Running になるまで待機
3. `kubectl describe pod` で Probe 状態を確認

**期待結果:**
- livenessProbe, readinessProbe が成功

### TC-11-006: 環境変数の注入

**手順:**
1. Secret を作成
2. Deployment を作成
3. Pod 内で `env | grep SLACK` を実行

**期待結果:**
- 環境変数が正しく設定されている

### TC-11-007: ボリュームマウント - config

**手順:**
1. ConfigMap を作成
2. Deployment を作成
3. Pod 内で `cat /config/config.yaml` を実行

**期待結果:**
- 設定ファイルが正しくマウントされている

### TC-11-008: ボリュームマウント - data

**手順:**
1. PVC を作成
2. Deployment を作成
3. アプリケーションでデータを保存
4. Pod を再起動
5. データが永続化されていることを確認

**期待結果:**
- データが永続化される

### TC-11-009: Service の動作

**手順:**
1. Deployment と Service を作成
2. クラスタ内から `curl http://myao3.myao3.svc.cluster.local/health` を実行

**期待結果:**
- ヘルスチェックが成功

### TC-11-010: Recreate 戦略の動作

**手順:**
1. Deployment を作成
2. イメージを更新してロールアウト
3. Pod の状態遷移を観察

**期待結果:**
- 古い Pod が終了してから新しい Pod が起動
- 同時に2つの Pod が Running にならない

### TC-11-011: リソース制限

**手順:**
1. Deployment を作成
2. `kubectl describe pod` でリソース設定を確認

**期待結果:**
- requests と limits が設定されている

## 完了条件

- [ ] k8s/ ディレクトリが作成されている
- [ ] namespace.yaml が作成されている
- [ ] configmap.yaml が作成されている
- [ ] secret.yaml.example が作成されている
- [ ] pvc.yaml が作成されている
- [ ] deployment.yaml が作成されている
- [ ] service.yaml が作成されている
- [ ] replicas: 1 で設定されている
- [ ] strategy: Recreate で設定されている
- [ ] ヘルスチェックが設定されている
- [ ] ボリュームマウントが正しく設定されている
- [ ] 環境変数が Secret から注入される
- [ ] 全てのテストケースがパスする
