# Jopper

**Synchronize Joplin notes to OpenWebUI knowledge base**

Jopper is a Python tool that automatically syncs your Joplin notes to OpenWebUI's knowledge base, keeping your information up-to-date with configurable filtering and scheduling options.

## Features

- 🔄 **Automatic Sync** - One-time or continuous daemon mode
- 🏷️ **Flexible Filtering** - Sync all notes or filter by tags
- 🐳 **Container Ready** - Docker and Kubernetes support
- ⚙️ **Environment Variables** - Full configuration via env vars for K8s deployment
- 📊 **Change Detection** - Only syncs modified notes (content hash comparison)
- 🗄️ **State Tracking** - SQLite database tracks sync history
- 🎯 **Multiple Modes** - CLI, scheduled, or daemon operation

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) for package management
- Joplin with Web Clipper service enabled
- OpenWebUI instance with API access

## Installation

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and Setup

```bash
git clone <repository-url>
cd jopper
make sync
```

This will install all dependencies using uv.

## Configuration

### Joplin Setup

1. Open Joplin
2. Go to **Tools** > **Options** (or **Preferences** on macOS)
3. Select the **Web Clipper** tab
4. Ensure **Enable Web Clipper Service** is checked
5. Under **Advanced Options**, copy the **Authorization token**

### OpenWebUI Setup

1. Navigate to your OpenWebUI instance
2. Go to **Settings** > **Account**
3. Find the **API Key** section
4. Click **Generate API Key** and copy it

#### Optional: Create and Configure a Knowledge Collection

To organize your Joplin notes in OpenWebUI:

1. In OpenWebUI, go to **Workspace** > **Knowledge**
2. Click **Create Collection** (or **+** button)
3. Name it "Joplin Notes" (or your preferred name)
4. Click on the collection to view it
5. Copy the **Collection ID** from the URL
   - Example URL: `https://your-openwebui.com/workspace/knowledge/ab3e1c1f-3ef7-4ad2-9c5d-144538056ddb`
   - Collection ID: `ab3e1c1f-3ef7-4ad2-9c5d-144538056ddb`
6. Add the collection ID to your `config.yaml`:

```yaml
openwebui:
  url: "http://localhost:3000"
  api_key: "your-api-key"
  knowledge_base_name: "Joplin Notes"
  collection_id: "ab3e1c1f-3ef7-4ad2-9c5d-144538056ddb"  # Your collection ID here
```

**Note:** If no collection ID is configured, Jopper will still upload files successfully. You can manually add them to collections via the OpenWebUI UI later.

### Configuration File

Create a config file at `~/.config/jopper/config.yaml`:

```bash
mkdir -p ~/.config/jopper
cp config.example.yaml ~/.config/jopper/config.yaml
```

Edit the file and add your credentials:

```yaml
joplin:
  token: "your-joplin-token-here"
  host: "localhost"
  port: 41184

openwebui:
  url: "http://localhost:3000"
  api_key: "your-openwebui-api-key-here"
  knowledge_base_name: "Joplin Notes"

sync:
  mode: "all"  # "all" or "tagged"
  tags: []     # Tags to filter when mode is "tagged"
  interval_minutes: 60
```

### Environment Variables

All configuration can be set via environment variables (useful for containers):

| Variable | Description | Default |
|----------|-------------|---------|
| `JOPPER_JOPLIN_TOKEN` | Joplin API authorization token | (required) |
| `JOPPER_JOPLIN_HOST` | Joplin API host | `localhost` |
| `JOPPER_JOPLIN_PORT` | Joplin API port | `41184` |
| `JOPPER_OPENWEBUI_URL` | OpenWebUI base URL | (required) |
| `JOPPER_OPENWEBUI_API_KEY` | OpenWebUI API key | (required) |
| `JOPPER_OPENWEBUI_KB_NAME` | Knowledge base name | `Joplin Notes` |
| `JOPPER_OPENWEBUI_COLLECTION_ID` | Knowledge collection ID | (empty) |
| `JOPPER_SYNC_MODE` | Sync mode: `all` or `tagged` | `all` |
| `JOPPER_SYNC_TAGS` | Comma-separated tags | (empty) |
| `JOPPER_SYNC_INTERVAL_MINUTES` | Sync interval in minutes | `60` |
| `JOPPER_STATE_DB_PATH` | Path to SQLite state database | `~/.local/share/jopper/state.db` |
| `JOPPER_CONFIG_FILE` | Path to YAML config file | `~/.config/jopper/config.yaml` |

**Priority:** Environment variables > YAML config file > defaults

## Usage

### CLI Commands

```bash
# Run one-time sync
make run-sync
# or
jopper sync

# Run in daemon mode (continuous sync)
make run-daemon
# or
jopper daemon

# Show sync status and statistics
jopper status

# Display current configuration
jopper config

# Display configuration in JSON format
jopper config --format json

# Use custom config file
jopper --config /path/to/config.yaml sync

# Enable verbose logging
jopper --verbose sync
```

### Development

```bash
# Install dependencies
make sync

# Install in editable mode
make install

# Lint code
make lint

# Format code
make format

# Run linting and format check (CI)
make check

# Clean build artifacts
make clean
```

### Building and Pushing Container Images

The Makefile uses `podman` by default, but you can use `docker` by setting `CONTAINER_TOOL=docker`.

#### Single Architecture Build

```bash
# Build container image (default: quay.io/mangelajo/jopper:latest with podman)
make docker-build

# Push to registry
make docker-push

# Build and push in one command
make docker-build-push

# Use docker instead of podman
make docker-build-push CONTAINER_TOOL=docker

# Use custom image name and tag
make docker-build DOCKER_IMAGE=myregistry/jopper DOCKER_TAG=v1.0.0
make docker-push DOCKER_IMAGE=myregistry/jopper DOCKER_TAG=v1.0.0
```

#### Multi-Architecture Build (AMD64 + ARM64)

**⚠️ Note**: Cross-platform builds using QEMU emulation may fail with segmentation faults. For reliable multi-arch builds, use the GitHub Actions workflow (see below) or build on native hardware for each architecture.

##### For Local Development (Single Architecture)

Build only for your current platform:

```bash
# On Apple Silicon / ARM - builds ARM64 only
make docker-build

# On Intel/AMD - builds AMD64 only
make docker-build
```

##### Using GitHub Actions (Recommended for Multi-Arch)

The repository includes a GitHub Actions workflow (`.github/workflows/build-multiarch.yaml`) that builds for both AMD64 and ARM64 using native GitHub runners.

**Setup:**

1. Add Quay.io credentials to GitHub Secrets:
   - Go to repository **Settings** > **Secrets and variables** > **Actions**
   - Add `QUAY_USERNAME` (your Quay.io username)
   - Add `QUAY_PASSWORD` (your Quay.io password or robot token)

2. Push to main branch or create a tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

3. The workflow automatically builds and pushes multi-arch images to `quay.io/mangelajo/jopper`

**Workflow triggers:**
- Push to `main` branch → builds `:latest` and `:main` tags
- Push tags matching `v*` → builds version tags (`:v1.0.0`, `:1.0`, etc.)
- Pull requests → builds but doesn't push

##### Manual Multi-Arch Build (Advanced)

If you have Docker Buildx configured and QEMU emulation works on your system:

```bash
# With docker buildx
make docker-push-multiarch CONTAINER_TOOL=docker

# Custom platforms
make docker-push-multiarch CONTAINER_TOOL=docker PLATFORMS=linux/amd64,linux/arm64
```

**Prerequisites:**
- **Docker**: Requires Docker Buildx (included in Docker Desktop)
  ```bash
  docker buildx create --use  # One-time setup
  ```

## Docker Deployment

### Build Image

```bash
docker build -t jopper:latest .
```

### Run Container

```bash
docker run -d \
  --name jopper \
  -e JOPPER_JOPLIN_TOKEN="your-joplin-token" \
  -e JOPPER_JOPLIN_HOST="host.docker.internal" \
  -e JOPPER_OPENWEBUI_URL="http://host.docker.internal:3000" \
  -e JOPPER_OPENWEBUI_API_KEY="your-api-key" \
  -e JOPPER_SYNC_INTERVAL="60" \
  -v jopper-data:/data \
  jopper:latest
```

### Docker Compose Example

```yaml
version: '3.8'

services:
  jopper:
    build: .
    environment:
      JOPPER_JOPLIN_TOKEN: "your-joplin-token"
      JOPPER_JOPLIN_HOST: "joplin"
      JOPPER_OPENWEBUI_URL: "http://openwebui:3000"
      JOPPER_OPENWEBUI_API_KEY: "your-api-key"
      JOPPER_SYNC_INTERVAL: "60"
    volumes:
      - jopper-data:/data
    restart: unless-stopped

volumes:
  jopper-data:
```

## Kubernetes Deployment

See [k8s/README.md](k8s/README.md) for detailed Kubernetes deployment instructions.

Quick start:

```bash
# Update secrets and config
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment.yaml

# Check logs
kubectl logs -f deployment/jopper
```

## How It Works

1. **Fetch Notes** - Retrieves notes from Joplin via REST API
2. **Change Detection** - Compares content hashes to detect modifications
3. **Sync to OpenWebUI** - Uploads new/modified notes as markdown files
4. **Add to Knowledge Base** - Links files to OpenWebUI knowledge base
5. **Track State** - Records sync status in SQLite database
6. **Handle Deletions** - Removes files from OpenWebUI when notes are deleted in Joplin

### Sync Modes

- **All Notes** (`mode: all`) - Syncs every note from Joplin
- **Tagged Notes** (`mode: tagged`) - Only syncs notes with specified tags

### Change Detection

Jopper uses SHA256 content hashes to detect changes:
- New notes are always synced
- Modified notes are re-uploaded
- Unchanged notes are skipped
- Deleted notes are removed from OpenWebUI

## Project Structure

```
jopper/
├── src/jopper/
│   ├── cli.py          # Command-line interface
│   ├── config.py       # Configuration management
│   ├── joplin.py       # Joplin API client
│   ├── openwebui.py    # OpenWebUI API client
│   ├── sync.py         # Sync engine
│   └── state.py        # State tracking
├── k8s/                # Kubernetes manifests
├── Dockerfile          # Container image
├── Makefile           # Development tasks
└── pyproject.toml     # Project configuration
```

## Troubleshooting

### Joplin Connection Issues

```bash
# Test Joplin API access
curl http://localhost:41184/ping?token=YOUR_TOKEN

# Check if Web Clipper is enabled
# Tools > Options > Web Clipper > Enable Web Clipper Service
```

### OpenWebUI Connection Issues

```bash
# Test OpenWebUI API access
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:3000/api/v1/knowledge

# Verify API key in Settings > Account
```

### View Logs

```bash
# Run with verbose logging
jopper --verbose sync

# Check state database
sqlite3 ~/.local/share/jopper/state.db "SELECT * FROM notes;"
```

### Reset State

```bash
# Delete state database to force full re-sync
rm ~/.local/share/jopper/state.db
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

[Add your license here]

## Acknowledgments

- [Joppy](https://github.com/marph91/joppy) - Python library for Joplin API
- [OpenWebUI](https://github.com/open-webui/open-webui) - Web UI for LLMs
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager


