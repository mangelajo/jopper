# GitHub Actions Workflows

## Build Multi-Arch Container

The `build-multiarch.yaml` workflow automatically builds container images for both AMD64 and ARM64 architectures.

### Setup

1. **Create a Quay.io Robot Account** (recommended) or use your personal credentials:
   - Go to https://quay.io/repository/mangelajo/jopper?tab=settings
   - Click **Robot Accounts** > **Create Robot Account**
   - Name it (e.g., `jopper_builder`)
   - Grant **Write** permissions to the repository

2. **Add GitHub Secrets**:
   - Go to your repository on GitHub
   - Navigate to **Settings** > **Secrets and variables** > **Actions**
   - Click **New repository secret** and add:
     - Name: `QUAY_USERNAME`
       Value: Your Quay.io username or robot account name (e.g., `mangelajo+jopper_builder`)
     - Name: `QUAY_PASSWORD`
       Value: Your Quay.io password or robot token

### Workflow Triggers

| Trigger | Action | Tags Created |
|---------|--------|--------------|
| Push to `main` | Build and push | `latest`, `main` |
| Push tag `v1.2.3` | Build and push | `v1.2.3`, `1.2`, `latest` |
| Pull request | Build only (no push) | - |
| Manual dispatch | Build and push | Based on branch |

### Manual Trigger

You can manually trigger the workflow from the Actions tab:

1. Go to **Actions** > **Build Multi-Arch Container**
2. Click **Run workflow**
3. Select the branch
4. Click **Run workflow**

### Testing Locally

To test the Docker build locally without pushing:

```bash
# Single architecture (your native platform)
make docker-build

# View the workflow file
cat .github/workflows/build-multiarch.yaml
```

### Troubleshooting

**Problem**: Workflow fails with authentication error
- **Solution**: Verify your QUAY_USERNAME and QUAY_PASSWORD secrets are correct
- Check that the robot account has write permissions

**Problem**: Build succeeds but image not visible on Quay.io
- **Solution**: Make sure the repository exists and is public/private as expected
- Check repository permissions for the robot account

**Problem**: Want to use a different registry (e.g., Docker Hub, GHCR)
- **Solution**: Edit `build-multiarch.yaml`:
  - Change `REGISTRY` environment variable
  - Update the login action credentials
  - Update `IMAGE_NAME` to match your registry format

