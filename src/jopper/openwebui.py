"""OpenWebUI API client for knowledge base management.

Provides methods to interact with OpenWebUI's knowledge base API.
"""

import logging

import requests

from jopper.config import OpenWebUIConfig

logger = logging.getLogger(__name__)


class OpenWebUIClient:
    """Client for OpenWebUI API operations."""

    def __init__(self, config: OpenWebUIConfig):
        """Initialize OpenWebUI client.

        Args:
            config: OpenWebUI configuration.
        """
        self.config = config
        self.base_url = config.url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Accept": "application/json",
        }
        self.knowledge_base_id: str | None = None

    def list_collections(self) -> list[dict]:
        """List available knowledge collections.

        Returns:
            List of collection dictionaries.
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/knowledge",
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()

            # Check if response is JSON (some OpenWebUI versions return HTML)
            if "application/json" in response.headers.get("Content-Type", ""):
                return response.json()
            else:
                logger.debug(
                    "Knowledge collections API not available (returns HTML). "
                    "Files will be uploaded successfully - organize them in collections via the UI."
                )
                return []

        except requests.exceptions.RequestException as e:
            logger.debug(f"Could not list collections: {e}")
            return []

    def get_or_prompt_collection(self) -> str | None:
        """Get collection ID from config or return None.

        Returns:
            Collection ID if configured, None otherwise.
        """
        if self.knowledge_base_id:
            return self.knowledge_base_id

        # Use collection ID from config if provided
        if self.config.collection_id:
            self.knowledge_base_id = self.config.collection_id
            logger.info(
                f"Using configured collection: {self.config.knowledge_base_name} "
                f"(ID: {self.config.collection_id})"
            )
            return self.knowledge_base_id

        # No collection ID configured
        logger.debug(
            "No collection ID configured. Files will be uploaded without a collection. "
            "Set 'collection_id' in config to organize files into a collection."
        )
        return None

    def upload_file(
        self, filename: str, content: str, collection_id: str | None = None
    ) -> str | None:
        """Upload a file to OpenWebUI.

        Args:
            filename: Name of the file to upload.
            content: File content.
            collection_id: Optional collection ID to associate file with.

        Returns:
            File ID or None if upload failed.
        """
        try:
            files = {"file": (filename, content.encode("utf-8"), "text/markdown")}

            # Prepare form data for collection if provided
            data = {}
            if collection_id:
                data["collection_name"] = self.config.knowledge_base_name

            response = requests.post(
                f"{self.base_url}/api/v1/files/",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Accept": "application/json",
                },
                files=files,
                data=data if data else None,
                timeout=30,
            )
            response.raise_for_status()

            file_data = response.json()
            file_id = file_data.get("id")
            logger.info(f"Uploaded file: {filename} -> {file_id}")
            return file_id

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to upload file {filename}: {e}")
            return None

    def add_file_to_collection(self, file_id: str, collection_id: str) -> bool:
        """Add a file to a knowledge collection.

        Args:
            file_id: ID of the uploaded file.
            collection_id: ID of the collection.

        Returns:
            True if successful, False otherwise.
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/knowledge/{collection_id}/file/add",
                headers=self.headers,
                json={"file_id": file_id},
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"Added file {file_id} to collection {collection_id}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to add file {file_id} to collection: {e}")
            return False

    def delete_file(self, file_id: str) -> bool:
        """Delete a file from OpenWebUI.

        Args:
            file_id: ID of the file to delete.

        Returns:
            True if successful, False otherwise.
        """
        try:
            response = requests.delete(
                f"{self.base_url}/api/v1/files/{file_id}",
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"Deleted file: {file_id}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False

    def sync_note(self, note_id: str, title: str, content: str) -> str | None:
        """Sync a note to OpenWebUI.

        Uploads the file and optionally adds it to a collection if one exists.

        Args:
            note_id: Joplin note ID (used for filename).
            title: Note title.
            content: Note content in markdown.

        Returns:
            File ID if successful, None otherwise.
        """
        # Create a filename from note_id and title
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
        filename = f"{note_id}_{safe_title[:50]}.md"

        # Get collection ID if available
        collection_id = self.get_or_prompt_collection()

        # Upload file
        file_id = self.upload_file(filename, content, collection_id)
        if not file_id:
            return None

        # If we have a collection, try to add the file to it
        if collection_id:
            # Try to add to collection, but don't fail if it doesn't work
            # (file is already uploaded and usable)
            self.add_file_to_collection(file_id, collection_id)

        return file_id
