.PHONY: sync install run run-sync run-daemon lint format check clean docker-build docker-push docker-build-push docker-build-multiarch docker-push-multiarch help

# Container configuration
CONTAINER_TOOL ?= podman
DOCKER_IMAGE ?= quay.io/mangelajo/jopper
DOCKER_TAG ?= latest
DOCKER_FULL_IMAGE = $(DOCKER_IMAGE):$(DOCKER_TAG)
PLATFORMS ?= linux/amd64,linux/arm64

help:  ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

sync:  ## Install dependencies with uv
	uv sync

install:  ## Install package in editable mode
	uv pip install -e .

run:  ## Run jopper CLI (use ARGS="..." to pass arguments)
	uv run jopper $(ARGS)

run-sync:  ## Run one-time sync
	uv run jopper sync

run-daemon:  ## Run daemon mode
	uv run jopper daemon

lint:  ## Run ruff linter
	uv run ruff check src/

format:  ## Format code with ruff
	uv run ruff format src/

check:  ## Run lint + format check (CI mode)
	uv run ruff check src/
	uv run ruff format --check src/

clean:  ## Clean build artifacts
	rm -rf .venv dist *.egg-info __pycache__ .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

docker-build:  ## Build container image (default: quay.io/mangelajo/jopper:latest)
	@echo "Building $(DOCKER_FULL_IMAGE) with $(CONTAINER_TOOL)..."
	$(CONTAINER_TOOL) build -t $(DOCKER_FULL_IMAGE) .
	@echo "✓ Built $(DOCKER_FULL_IMAGE)"

docker-push:  ## Push container image to registry
	@echo "Pushing $(DOCKER_FULL_IMAGE) with $(CONTAINER_TOOL)..."
	$(CONTAINER_TOOL) push $(DOCKER_FULL_IMAGE)
	@echo "✓ Pushed $(DOCKER_FULL_IMAGE)"

docker-build-push: docker-build docker-push  ## Build and push container image

docker-build-multiarch:  ## Build multi-architecture image (amd64, arm64)
	@echo "Building multi-arch $(DOCKER_FULL_IMAGE) for $(PLATFORMS)..."
ifeq ($(CONTAINER_TOOL),docker)
	docker buildx build --platform $(PLATFORMS) -t $(DOCKER_FULL_IMAGE) --load .
else
	podman build --platform $(PLATFORMS) --manifest $(DOCKER_FULL_IMAGE) .
endif
	@echo "✓ Built multi-arch $(DOCKER_FULL_IMAGE)"

docker-push-multiarch:  ## Build and push multi-architecture image
	@echo "Building and pushing multi-arch $(DOCKER_FULL_IMAGE) for $(PLATFORMS)..."
ifeq ($(CONTAINER_TOOL),docker)
	docker buildx build --platform $(PLATFORMS) -t $(DOCKER_FULL_IMAGE) --push .
else
	podman build --platform $(PLATFORMS) --manifest $(DOCKER_FULL_IMAGE) .
	podman manifest push $(DOCKER_FULL_IMAGE)
endif
	@echo "✓ Built and pushed multi-arch $(DOCKER_FULL_IMAGE)"

