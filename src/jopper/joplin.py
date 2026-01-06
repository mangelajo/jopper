"""Joplin API client wrapper.

Provides a convenient interface to interact with Joplin notes via the REST API.
"""

import dataclasses

from joppy.client_api import ClientApi

from jopper.config import JoplinConfig


class JoplinClient:
    """Wrapper around the Joppy library for Joplin API access."""

    def __init__(self, config: JoplinConfig):
        """Initialize Joplin client.

        Args:
            config: Joplin configuration.
        """
        self.config = config
        self.api = ClientApi(token=config.token, url=config.url)

    def get_all_notes(self) -> list[dict]:
        """Get all notes from Joplin.

        Returns:
            List of note dictionaries with id, title, body, etc.
        """
        # Request specific fields including body content
        notes = self.api.get_all_notes(
            fields="id,title,body,updated_time,is_todo,todo_completed,parent_id"
        )
        # Convert NoteData objects to dictionaries
        return [dataclasses.asdict(note) for note in notes]

    def get_notes_by_tags(self, tag_names: list[str]) -> list[dict]:
        """Get notes filtered by tags.

        Args:
            tag_names: List of tag names to filter by.

        Returns:
            List of note dictionaries that have any of the specified tags.
        """
        if not tag_names:
            return []

        # Get all tags and find matching tag IDs
        all_tags = self.api.get_all_tags()
        # Convert TagData objects to dicts for easier access
        all_tags_dicts = [dataclasses.asdict(tag) for tag in all_tags]
        tag_ids = [tag["id"] for tag in all_tags_dicts if tag.get("title") in tag_names]

        if not tag_ids:
            return []

        # Get all notes and filter by tag
        all_notes = self.api.get_all_notes(
            fields="id,title,body,updated_time,is_todo,todo_completed,parent_id"
        )
        filtered_notes = []

        for note in all_notes:
            # Get tags for this note
            note_tags = self.api.get_tags(note.id)
            note_tags_dicts = [dataclasses.asdict(tag) for tag in note_tags]
            note_tag_ids = [tag["id"] for tag in note_tags_dicts]

            # Check if note has any of the requested tags
            if any(tag_id in note_tag_ids for tag_id in tag_ids):
                filtered_notes.append(dataclasses.asdict(note))

        return filtered_notes

    def get_note(self, note_id: str) -> dict | None:
        """Get a specific note by ID.

        Args:
            note_id: Joplin note ID.

        Returns:
            Note dictionary or None if not found.
        """
        try:
            note = self.api.get_note(
                note_id, fields="id,title,body,updated_time,is_todo,todo_completed,parent_id"
            )
            return dataclasses.asdict(note)
        except Exception:
            return None

    def get_notebook_title(self, notebook_id: str) -> str:
        """Get notebook title by ID.

        Args:
            notebook_id: Notebook ID.

        Returns:
            Notebook title or empty string if not found.
        """
        try:
            notebook = self.api.get_notebook(notebook_id, fields="id,title")
            notebook_dict = dataclasses.asdict(notebook)
            return notebook_dict.get("title", "")
        except Exception:
            return ""
