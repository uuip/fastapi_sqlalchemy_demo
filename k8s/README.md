# Kubernetes 部署配置
---

## 前提准备：Secret 管理

### 创建 Secret

```bash
# 从项目根目录的 .env 文件生成 secret.yaml（不直接提交到仓库）
kubectl create secret generic backend-secret \
  --from-env-file=.env \
  --namespace=ailink-debot \
  --dry-run=client -o yaml > k8s/secret.yaml

# 应用到集群
kubectl apply -f k8s/secret.yaml
```

### 验证 Secret

```bash
kubectl get secret backend-secret --namespace=ailink-debot
```

### 更新 Secret 后滚动重启

```bash
openssl rand -hex 32
kubectl apply -f k8s/secret.yaml
kubectl rollout restart deployment backend -n ailink-debot
```

---

## 代码挂载

代码挂载用于开发/调试时将宿主机或网络存储的代码实时挂入容器，无需重新构建镜像。

### 单节点集群

单节点集群可以直接使用 `hostPath`，无需 `nodeSelector`，在 `kustomization.yaml` 的 `patches`
中配置对应的 `hostPath` 即可。

### 多节点集群

多节点集群中 Pod 可能调度到任意节点，`hostPath` 不再可靠，推荐以下两种方案：

#### 方案 1：NFS（推荐）

NFS 存储对所有节点可见，Pod 可自由调度。

**1. 创建 PVC 并查看 NFS 挂载路径**

```bash
kubectl apply -f k8s/code-pvc.yaml
kubectl get pvc -n ailink-debot
kubectl describe pvc backend-code-pvc -n ailink-debot
```

查看输出中的 `Volume` 字段，得到 PV 名称后进一步查看实际路径：

```bash
kubectl describe pv <pv-name>
# 查看 Source.Path 字段，即为 NFS 实际挂载路径
```

**2. 上传代码到 NFS 路径**

**3. 重启 Deployment 使代码生效**

```bash
kubectl rollout restart deployment/backend -n ailink-debot

# 查看滚动更新状态
kubectl rollout status deployment/backend -n ailink-debot
```

#### 方案 2：hostPath + nodeSelector 固定节点

不使用 NFS 时，可通过 `nodeSelector` 将 Pod 固定到特定节点，再使用该节点的 `hostPath`。

在 `kustomization.yaml` 的 patch 中，于 `spec.template.spec` 下添加：

```yaml
nodeSelector:
  kubernetes.io/hostname: master  # 替换为实际节点名
```

查看可用节点名：

```bash
kubectl get nodes
```

---

## 撤销部署

### 撤销代码挂载（保留 Deployment）

编辑 `kustomization.yaml`，注释或删除 `patches:` 及其下内容，然后重新 apply：

```bash
kubectl apply -k k8s/
```
