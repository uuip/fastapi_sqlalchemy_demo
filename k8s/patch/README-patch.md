# K8s 部署说明 - kubectl patch 方案

## 部署步骤

### 1. 使用 patch 添加 volume 挂载

```bash
kubectl patch deployment backend -n ailink-debot --patch-file volume-patch.yaml
```

Patch 执行后会自动触发滚动更新。

## 撤销 volume 挂载: 重新部署原始配置

```bash
kubectl patch deployment backend -n ailink-debot --type=strategic --patch-file k8s/unmount-only.yaml
kubectl patch deployment backend -n ailink-debot --type=strategic --patch-file k8s/unvolume-only.yaml
```