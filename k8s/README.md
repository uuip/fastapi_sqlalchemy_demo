# Kubernetes 部署配置
---

## Secret 管理

### 创建或更新 Secret

从项目根目录的 `.env` 创建：

```bash
kubectl create secret generic backend-secret \
  --from-env-file=.env \
  --namespace=honey \
  --dry-run=client -o yaml | kubectl apply -f -
```

或手动传入必要变量：

```bash
kubectl create secret generic backend-secret \
  --from-literal=DB_URL='postgresql://user:password@host:5432/dbname' \
  --from-literal=SECRET_KEY='your-secret-key' \
  --namespace=honey \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 验证 Secret

```bash
kubectl get secret backend-secret --namespace=honey
```

### 变更 Secret 后重启 Deployment

```bash
openssl rand -hex 32
# 使用新值重新执行上面的创建或更新命令后，让 Pod 读取新配置
kubectl rollout restart deployment backend -n honey
```

---

## 代码挂载

代码挂载仅建议用于开发/调试，当前示例通过 `kustomization.yaml` 挂载 `app/main.py`，无需重新构建镜像。

### 单节点集群

单节点集群可直接使用 `hostPath`。在 `kustomization.yaml` 中启用 `hostPath`
patch，并确认路径存在后执行：

```bash
kubectl apply -k k8s/
```

### 多节点集群

多节点集群中 Pod 可能调度到任意节点，`hostPath` 不可靠，推荐使用 NFS；无法使用 NFS 时再固定节点。

#### 方案 1：NFS（推荐）

NFS 存储对所有节点可见，Pod 可自由调度：

```bash
kubectl apply -f k8s/code-pvc.yaml
kubectl get pvc -n honey
kubectl describe pvc backend-code-pvc -n honey
```

如需确认实际路径，查看 PVC 输出中的 `Volume` 字段，再描述对应 PV：

```bash
kubectl describe pv <pv-name>
# 查看 Source.Path 字段
```

上传代码到 NFS 后应用配置：

```bash
kubectl apply -k k8s/
```

#### 方案 2：hostPath + nodeSelector 固定节点

不使用 NFS 时，可通过 `nodeSelector` 将 Pod 固定到特定节点，再使用该节点的 `hostPath`
。先查看节点名：

```bash
kubectl get nodes
```

在 `kustomization.yaml` 的 patch 中，于 `spec.template.spec` 下添加：

```yaml
nodeSelector:
  kubernetes.io/hostname: master  # 替换为实际节点名
```

配置完成后执行：

```bash
kubectl apply -k k8s/
```

---

## 撤销部署

撤销代码挂载但保留 Deployment：编辑 `kustomization.yaml`，注释或删除 `patches:`
及其下内容，然后重新应用：

```bash
kubectl apply -k k8s/
```
