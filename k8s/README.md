# Kubernetes Deployment for Jopper

This directory contains Kubernetes manifests for deploying Jopper in a Kubernetes cluster.

## Files

- `secret.yaml` - Stores sensitive credentials (Joplin token, OpenWebUI API key)
- `configmap.yaml` - Configuration settings as environment variables
- `pvc.yaml` - PersistentVolumeClaim for storing sync state
- `deployment.yaml` - Main deployment configuration

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

### 1. Update Secret

Edit `secret.yaml` and add your actual credentials:

```bash
# Get your Joplin token from: Tools > Options > Web Clipper > Advanced Options
# Get your OpenWebUI API key from: Settings > Account > Generate API Key

kubectl create secret generic jopper-secrets \
  --from-literal=joplin-token='YOUR_JOPLIN_TOKEN' \
  --from-literal=openwebui-api-key='YOUR_OPENWEBUI_API_KEY' \
  --dry-run=client -o yaml > secret.yaml
```

### 2. Update ConfigMap

Edit `configmap.yaml` and update the following:

- `JOPPER_JOPLIN_HOST` - Your Joplin service host/IP
- `JOPPER_JOPLIN_PORT` - Joplin API port (default: 41184)
- `JOPPER_OPENWEBUI_URL` - Your OpenWebUI service URL
- `JOPPER_SYNC_MODE` - "all" or "tagged"
- `JOPPER_SYNC_TAGS` - Comma-separated tags (if mode is "tagged")
- `JOPPER_SYNC_INTERVAL` - Sync interval in minutes

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

```bash
# Get detailed pod information
kubectl describe pod -l app=jopper

# Get logs with more context
kubectl logs -f deployment/jopper --tail=100

# Execute command in pod
kubectl exec -it deployment/jopper -- jopper status

# Check events
kubectl get events --sort-by='.lastTimestamp'
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


