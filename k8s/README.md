# Kubernetes Deployment for Jopper

> 📖 **Complete Deployment Guide:** [`../KUBERNETES_GUIDE.md`](../KUBERNETES_GUIDE.md)
>
> All documentation has been unified into a single comprehensive guide. See the link above for:
> - Architecture overview
> - Step-by-step deployment
> - Configuration reference  
> - Troubleshooting
> - Migration guides

This directory contains Kubernetes manifests for deploying Jopper.

## Files

- `secret.yaml` - Stores sensitive credentials (Joplin token, OpenWebUI API key, Joplin config)
- `configmap.yaml` - Configuration settings as environment variables
- `pvc.yaml` - PersistentVolumeClaims for storing sync state and Joplin data
- `deployment.yaml` - Main deployment configuration (single container with integrated Joplin)

## Prerequisites

1. A running Kubernetes cluster
2. `kubectl` configured to access your cluster
3. Joplin instance accessible from the cluster
4. OpenWebUI instance accessible from the cluster
5. Docker image of Jopper pushed to a registry

## Build and Push Container Image

### Single Architecture

```bash
# Build and push to quay.io (default, uses podman)
cd ..  # Go back to project root
make docker-build-push

# Use docker instead of podman
make docker-build-push CONTAINER_TOOL=docker
```

### Multi-Architecture (Recommended for Kubernetes)

For Kubernetes clusters with mixed architectures (Intel nodes, ARM nodes, etc.):

```bash
# Build and push multi-arch image (amd64 + arm64)
cd ..  # Go back to project root
make docker-push-multiarch

# With docker
make docker-push-multiarch CONTAINER_TOOL=docker

# Custom configuration
make docker-push-multiarch \
  DOCKER_IMAGE=your-registry/jopper \
  DOCKER_TAG=v1.0.0 \
  PLATFORMS=linux/amd64,linux/arm64
```

The default image is `quay.io/mangelajo/jopper:latest`. Multi-arch images automatically work on both AMD64 and ARM64 nodes.

To use a different registry, update `deployment.yaml`:

```yaml
image: your-registry/jopper:latest
```

## Configuration

### 1. Get Your Credentials

#### Joplin API Token

1. Open Joplin application
2. Go to **Tools** > **Options** (or **Preferences** on macOS)
3. Select **Web Clipper** tab
4. Ensure **Enable Web Clipper Service** is checked
5. Under **Advanced Options**, copy the **Authorization token**

#### OpenWebUI API Key

1. Log into OpenWebUI
2. Go to **Settings** > **Account**
3. Find **API Keys** section
4. Click **Generate API Key** or **Create new secret key**
5. Copy the generated key (shown only once!)

#### OpenWebUI Collection ID (Recommended)

1. In OpenWebUI, go to **Workspace** > **Knowledge**
2. Create a collection named "Joplin Notes" (or your preferred name)
3. Click on the collection to view it
4. Copy the **Collection ID** from the URL:
   ```
   https://your-openwebui.com/workspace/knowledge/ab3e1c1f-3ef7-4ad2-9c5d-144538056ddb
                                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                    This is your Collection ID
   ```

### 2. Create Secret

**Option A: Using kubectl (Recommended)**

```bash
kubectl create secret generic jopper-secrets \
  --from-literal=joplin-token='YOUR_JOPLIN_TOKEN_HERE' \
  --from-literal=openwebui-api-key='YOUR_OPENWEBUI_API_KEY_HERE' \
  --namespace=default
```

**Option B: Edit secret.yaml**

Edit `secret.yaml` and replace the placeholder values, then apply:

```bash
kubectl apply -f secret.yaml
```

### 3. Update ConfigMap

Edit `configmap.yaml` or use `configmap.example.yaml` as a template. Key settings:

| Setting | Description | Example |
|---------|-------------|---------|
| `JOPPER_JOPLIN_HOST` | Joplin server hostname/IP | `192.168.1.100` or `joplin-service` |
| `JOPPER_JOPLIN_PORT` | Joplin API port | `41184` (default) |
| `JOPPER_OPENWEBUI_URL` | OpenWebUI base URL | `https://ai.example.com` |
| `JOPPER_OPENWEBUI_KB_NAME` | Collection display name | `Joplin Notes` |
| `JOPPER_OPENWEBUI_COLLECTION_ID` | Collection UUID | `ab3e1c1f-3ef7-4ad2-9c5d-144538056ddb` |
| `JOPPER_SYNC_MODE` | Sync mode | `all` or `tagged` |
| `JOPPER_SYNC_TAGS` | Tags to sync (if mode=tagged) | `work,docs` |
| `JOPPER_SYNC_INTERVAL_MINUTES` | Minutes between syncs | `60` (default) |

## Deployment

Apply all manifests:

```bash
# Create namespace (optional)
kubectl create namespace jopper

# Apply all manifests
kubectl apply -f k8s/

# Or apply individually
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment.yaml
```

## Verify Deployment

```bash
# Check pod status
kubectl get pods -l app=jopper

# View logs
kubectl logs -f deployment/jopper

# Check persistent volume
kubectl get pvc jopper-data
```

## Update Configuration

If you need to update configuration:

```bash
# Update ConfigMap
kubectl edit configmap jopper-config

# Restart deployment to pick up changes
kubectl rollout restart deployment/jopper
```

## Troubleshooting

### Common Issues

#### 1. Pod Not Starting

```bash
# Check pod status
kubectl get pods -l app=jopper

# Get detailed information
kubectl describe pod -l app=jopper

# Common causes:
# - Secret not created or incorrect name
# - ConfigMap not created or incorrect name
# - PVC not bound
```

#### 2. Configuration Errors

```bash
# View current configuration
kubectl exec deployment/jopper -- jopper config

# Check environment variables
kubectl exec deployment/jopper -- env | grep JOPPER

# Common causes:
# - Missing JOPPER_JOPLIN_TOKEN or JOPPER_OPENWEBUI_API_KEY
# - Invalid URLs or hostnames
# - Incorrect collection ID format
```

#### 3. Sync Failures

```bash
# View logs
kubectl logs -f deployment/jopper --tail=100

# Check sync status
kubectl exec deployment/jopper -- jopper status

# Run manual sync to test
kubectl exec deployment/jopper -- jopper sync

# Common causes:
# - Joplin server not reachable (check JOPPER_JOPLIN_HOST)
# - OpenWebUI server not reachable (check JOPPER_OPENWEBUI_URL)
# - Invalid API credentials
# - Collection ID doesn't exist
```

#### 4. Liveness/Readiness Probe Failures

```bash
# Check probe status
kubectl describe pod -l app=jopper | grep -A 10 "Liveness\|Readiness"

# Test probes manually
kubectl exec deployment/jopper -- pgrep -f jopper
kubectl exec deployment/jopper -- test -f /data/state.db && echo "OK"

# Common causes:
# - Initial sync taking longer than initialDelaySeconds
# - Process crashed (check logs)
# - PVC not mounted correctly
```

### Useful Commands

```bash
# Get detailed pod information
kubectl describe pod -l app=jopper

# View logs (live tail)
kubectl logs -f deployment/jopper

# View logs (last 100 lines)
kubectl logs deployment/jopper --tail=100

# View logs from previous pod (if crashed)
kubectl logs deployment/jopper --previous

# Execute command in pod
kubectl exec -it deployment/jopper -- jopper status
kubectl exec -it deployment/jopper -- jopper config
kubectl exec -it deployment/jopper -- jopper sync

# Check events
kubectl get events --sort-by='.lastTimestamp' | grep jopper

# View ConfigMap
kubectl get configmap jopper-config -o yaml

# View Secret (base64 encoded)
kubectl get secret jopper-secrets -o yaml

# Open a shell in the pod
kubectl exec -it deployment/jopper -- /bin/sh

# Check PVC status
kubectl get pvc jopper-data
kubectl describe pvc jopper-data
```

### Debug Mode

To run with verbose logging, edit the deployment and add:

```yaml
containers:
- name: jopper
  command: ["jopper", "--verbose", "daemon"]
```

Then restart:

```bash
kubectl rollout restart deployment/jopper
```

## Cleanup

To remove all resources:

```bash
kubectl delete -f k8s/
```

## Notes

- The deployment runs with 1 replica to avoid concurrent syncs
- State is persisted in a PersistentVolume
- Adjust resource limits based on your needs
- Consider using a StorageClass for dynamic provisioning


