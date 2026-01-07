"""Sync engine for synchronizing Joplin notes to OpenWebUI.

Handles the core logic for detecting changes and syncing notes.
"""

import logging

from jopper.config import Config
from jopper.joplin import JoplinClient
from jopper.openwebui import OpenWebUIClient
from jopper.state import StateManager

logger = logging.getLogger(__name__)


class SyncEngine:
    """Manages synchronization between Joplin and OpenWebUI."""

    def __init__(self, config: Config):
        """Initialize sync engine.

        Args:
            config: Application configuration.
        """
        self.config = config
        self.joplin = JoplinClient(config.joplin)
        self.openwebui = OpenWebUIClient(config.openwebui)
        self.state = StateManager(config.state_db_path)

    def sync(self) -> dict:
        """Perform a sync operation.

        Returns:
            Dictionary with sync statistics.
        """
        logger.info("Starting sync operation...")

        # Check for available collections (optional - files can be uploaded without them)
        collection_id = self.openwebui.get_or_prompt_collection()
        if collection_id:
            logger.info(f"Using collection: {self.config.openwebui.knowledge_base_name}")

        # Get notes from Joplin based on sync mode
        if self.config.sync.mode == "tagged":
            if not self.config.sync.tags:
                logger.warning("Sync mode is 'tagged' but no tags specified. Nothing to sync.")
                return {
                    "success": True,
                    "notes_synced": 0,
                    "notes_updated": 0,
                    "notes_deleted": 0,
                    "errors": 0,
                }
            logger.info(f"Fetching notes with tags: {self.config.sync.tags}")
            notes = self.joplin.get_notes_by_tags(self.config.sync.tags)
        else:
            logger.info("Fetching all notes from Joplin...")
            notes = self.joplin.get_all_notes()

        logger.info(f"Found {len(notes)} notes in Joplin")

        # Track current note IDs
        current_note_ids = {note["id"] for note in notes}

        # Get previously synced note IDs
        synced_note_ids = self.state.get_all_synced_note_ids()

        # Find notes that were deleted from Joplin
        deleted_note_ids = synced_note_ids - current_note_ids

        # Sync statistics
        notes_synced = 0
        notes_updated = 0
        notes_deleted = 0
        errors = 0

        # Process each note
        for note in notes:
            note_id = note["id"]
            title = note.get("title", "Untitled")
            body = note.get("body", "")

            # Create full content with metadata
            content = self._format_note_content(note)

            try:
                # Check if note needs to be synced
                if self.state.has_note_changed(note_id, content):
                    is_new = note_id not in synced_note_ids

                    # Get existing state to check for file_id
                    existing_state = self.state.get_note_state(note_id)

                    # Delete old file if it exists
                    if existing_state and existing_state.openwebui_file_id:
                        logger.info(f"Deleting old version of note: {title}")
                        self.openwebui.delete_file(existing_state.openwebui_file_id)

                    # Sync to OpenWebUI
                    logger.info(f"{'Syncing new' if is_new else 'Updating'} note: {title}")
                    file_id = self.openwebui.sync_note(note_id, title, content)

                    if file_id:
                        # Save state
                        self.state.save_note_state(note_id, title, content, file_id)

                        if is_new:
                            notes_synced += 1
                        else:
                            notes_updated += 1
                    else:
                        logger.error(f"Failed to sync note: {title}")
                        errors += 1
                else:
                    logger.debug(f"Note unchanged, skipping: {title}")

            except Exception as e:
                logger.error(f"Error processing note {title}: {e}")
                errors += 1

        # Handle deleted notes
        for note_id in deleted_note_ids:
            try:
                state = self.state.get_note_state(note_id)
                if state and state.openwebui_file_id:
                    logger.info(f"Deleting note from OpenWebUI: {state.title}")
                    if self.openwebui.delete_file(state.openwebui_file_id):
                        self.state.delete_note_state(note_id)
                        notes_deleted += 1
                    else:
                        logger.error(f"Failed to delete file: {state.title}")
                        errors += 1
                else:
                    # Note was deleted but no file_id, just remove state
                    self.state.delete_note_state(note_id)
                    notes_deleted += 1

            except Exception as e:
                logger.error(f"Error deleting note {note_id}: {e}")
                errors += 1

        # Log sync operation
        self.state.log_sync(notes_synced, notes_updated, notes_deleted, errors)

        result = {
            "success": True,
            "notes_synced": notes_synced,
            "notes_updated": notes_updated,
            "notes_deleted": notes_deleted,
            "errors": errors,
        }

        logger.info(
            f"Sync complete: {notes_synced} new, {notes_updated} updated, "
            f"{notes_deleted} deleted, {errors} errors"
        )

        return result

    def _format_note_content(self, note: dict) -> str:
        """Format note content with metadata.

        Args:
            note: Joplin note dictionary.

        Returns:
            Formatted markdown content.
        """
        title = note.get("title") or "Untitled"
        body = note.get("body") or ""
        updated_time = note.get("updated_time") or ""

        # Add title as H1 if not already in body
        if not body.strip().startswith(f"# {title}"):
            content = f"# {title}\n\n"
        else:
            content = ""

        content += body

        # Add metadata footer
        if updated_time:
            content += f"\n\n---\n*Last updated: {updated_time}*\n"

        # Add notebook info if available
        if note.get("parent_id"):
            notebook_title = self.joplin.get_notebook_title(note["parent_id"])
            if notebook_title:
                content += f"*Notebook: {notebook_title}*\n"

        return content

    def get_status(self) -> dict:
        """Get current sync status and statistics.

        Returns:
            Dictionary with status information.
        """
        stats = self.state.get_stats()
        return {
            "config": {
                "joplin_host": f"{self.config.joplin.host}:{self.config.joplin.port}",
                "openwebui_url": self.config.openwebui.url,
                "knowledge_base_name": self.config.openwebui.knowledge_base_name,
                "sync_mode": self.config.sync.mode,
                "sync_tags": self.config.sync.tags,
                "sync_interval": self.config.sync.interval_minutes,
            },
            "stats": stats,
        }
