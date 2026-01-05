# Jopper Kubernetes Deployment Checklist

Follow this checklist to deploy Jopper to your Kubernetes cluster.

## Pre-Deployment Checklist

- [ ] Kubernetes cluster is accessible (`kubectl cluster-info`)
- [ ] Joplin is running and Web Clipper is enabled
- [ ] OpenWebUI is accessible
- [ ] Knowledge collection created in OpenWebUI (optional but recommended)

## Step 1: Gather Information

- [ ] **Joplin API Token**: _________________________
  - Tools > Options > Web Clipper > Advanced Options
  
- [ ] **Joplin Host**: _________________________
  - Hostname or IP where Joplin is accessible from cluster
  
- [ ] **OpenWebUI URL**: _________________________
  - Full URL with protocol (e.g., `https://ai.example.com`)
  
- [ ] **OpenWebUI API Key**: _________________________
  - Settings > Account > Generate API Key
  
- [ ] **Collection ID** (optional): _________________________
  - Copy from URL: `/workspace/knowledge/<ID>`

## Step 2: Configure Kubernetes Resources

### Create Namespace (Optional)

```bash
kubectl create namespace jopper
# Update all YAML files to use namespace: jopper
```

### Update ConfigMap

```bash
cd k8s/
# Edit configmap.yaml with your values
```

Edit these values:
- [ ] `JOPPER_JOPLIN_HOST`
- [ ] `JOPPER_JOPLIN_PORT`
- [ ] `JOPPER_OPENWEBUI_URL`
- [ ] `JOPPER_OPENWEBUI_COLLECTION_ID`
- [ ] `JOPPER_SYNC_MODE`
- [ ] `JOPPER_SYNC_INTERVAL`

### Create Secret

```bash
kubectl create secret generic jopper-secrets \
  --from-literal=joplin-token='YOUR_TOKEN' \
  --from-literal=openwebui-api-key='YOUR_KEY' \
  --namespace=default
```

Or edit secret.yaml and apply:
```bash
kubectl apply -f secret.yaml
```

## Step 3: Deploy Resources

### Deploy in Order

```bash
# 1. Create PVC first
kubectl apply -f pvc.yaml

# 2. Wait for PVC to be bound
kubectl get pvc jopper-data
# Should show STATUS: Bound

# 3. Apply ConfigMap
kubectl apply -f configmap.yaml

# 4. Verify ConfigMap
kubectl get configmap jopper-config

# 5. Deploy application
kubectl apply -f deployment.yaml
```

## Step 4: Verify Deployment

### Check Pod Status

```bash
# Watch pod starting
kubectl get pods -l app=jopper -w

# Pod should show Running after ~30-60 seconds
```

### Check Logs

```bash
# View startup logs
kubectl logs -f deployment/jopper

# Look for:
# ✓ "Starting sync operation..."
# ✓ "Using configured collection: Joplin Notes (ID: ...)"
# ✓ "Fetching all notes from Joplin..."
# ✓ "Sync complete: X new, Y updated, 0 deleted, 0 errors"
```

### Check Configuration

```bash
# Verify configuration is loaded correctly
kubectl exec deployment/jopper -- jopper config

# Check status
kubectl exec deployment/jopper -- jopper status
```

### Verify Sync

```bash
# Run manual sync to test
kubectl exec deployment/jopper -- jopper sync

# Check OpenWebUI
# Go to Workspace > Knowledge > Your Collection
# Verify notes are appearing
```

## Step 5: Monitor

### Check Sync Status

```bash
# View sync statistics
kubectl exec deployment/jopper -- jopper status

# View recent logs
kubectl logs deployment/jopper --tail=50

# Follow live logs
kubectl logs -f deployment/jopper
```

### Verify Probes

```bash
# Check liveness and readiness
kubectl describe pod -l app=jopper | grep -A 5 "Liveness\|Readiness"
```

## Troubleshooting

If something goes wrong, run through this checklist:

- [ ] Secret exists: `kubectl get secret jopper-secrets`
- [ ] ConfigMap exists: `kubectl get configmap jopper-config`
- [ ] PVC is bound: `kubectl get pvc jopper-data`
- [ ] Pod is running: `kubectl get pods -l app=jopper`
- [ ] No error logs: `kubectl logs deployment/jopper | grep -i error`
- [ ] Configuration valid: `kubectl exec deployment/jopper -- jopper config`
- [ ] Joplin reachable: Test from within pod
  ```bash
  kubectl exec deployment/jopper -- curl http://JOPLIN_HOST:41184/ping
  ```
- [ ] OpenWebUI reachable: Test from within pod
  ```bash
  kubectl exec deployment/jopper -- curl -I OPENWEBUI_URL
  ```

## Maintenance

### Update Configuration

```bash
# Edit ConfigMap
kubectl edit configmap jopper-config

# Restart to pick up changes
kubectl rollout restart deployment/jopper
```

### Update Secrets

```bash
# Delete old secret
kubectl delete secret jopper-secrets

# Create new secret
kubectl create secret generic jopper-secrets \
  --from-literal=joplin-token='NEW_TOKEN' \
  --from-literal=openwebui-api-key='NEW_KEY'

# Restart to pick up changes
kubectl rollout restart deployment/jopper
```

### Update Image

```bash
# Update to new version
kubectl set image deployment/jopper jopper=quay.io/mangelajo/jopper:v1.0.0

# Or edit deployment.yaml and reapply
kubectl apply -f deployment.yaml
```

### View Sync History

```bash
# Check state database
kubectl exec deployment/jopper -- sqlite3 /data/state.db \
  "SELECT * FROM sync_log ORDER BY timestamp DESC LIMIT 10"
```

## Cleanup

To remove Jopper from your cluster:

```bash
kubectl delete -f deployment.yaml
kubectl delete -f configmap.yaml
kubectl delete -f secret.yaml
kubectl delete -f pvc.yaml

# Warning: This will delete the sync state database!
# If you want to preserve it, backup the PVC first
```

## Success Criteria

Your deployment is successful when:

- ✅ Pod is in Running state
- ✅ Logs show successful syncs
- ✅ `jopper status` shows synced notes
- ✅ Notes appear in OpenWebUI knowledge collection
- ✅ No error messages in logs
- ✅ Liveness and readiness probes passing

