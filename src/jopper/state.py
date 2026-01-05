"""State management for tracking synchronized notes.

Uses SQLite to store information about synced notes, including content hashes
to detect changes.
"""

import hashlib
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class NoteState:
    """State information for a synced note."""

    note_id: str
    title: str
    content_hash: str
    last_synced: str
    openwebui_file_id: Optional[str] = None


class StateManager:
    """Manages sync state in a SQLite database."""

    def __init__(self, db_path: Path):
        """Initialize state manager.

        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Create database and tables if they don't exist."""
        # Create parent directory if needed
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                note_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                last_synced TEXT NOT NULL,
                openwebui_file_id TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                notes_synced INTEGER NOT NULL,
                notes_updated INTEGER NOT NULL,
                notes_deleted INTEGER NOT NULL,
                errors INTEGER NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute SHA256 hash of content.

        Args:
            content: Content to hash.

        Returns:
            Hex string of hash.
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get_note_state(self, note_id: str) -> Optional[NoteState]:
        """Get state for a specific note.

        Args:
            note_id: Joplin note ID.

        Returns:
            NoteState or None if not found.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            "SELECT note_id, title, content_hash, last_synced, openwebui_file_id FROM notes WHERE note_id = ?",
            (note_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return NoteState(
                note_id=row[0],
                title=row[1],
                content_hash=row[2],
                last_synced=row[3],
                openwebui_file_id=row[4],
            )

        return None

    def has_note_changed(self, note_id: str, content: str) -> bool:
        """Check if a note's content has changed.

        Args:
            note_id: Joplin note ID.
            content: Current note content.

        Returns:
            True if note is new or content has changed.
        """
        state = self.get_note_state(note_id)
        if not state:
            return True

        current_hash = self.compute_hash(content)
        return state.content_hash != current_hash

    def save_note_state(
        self, note_id: str, title: str, content: str, openwebui_file_id: Optional[str] = None
    ):
        """Save or update note state.

        Args:
            note_id: Joplin note ID.
            title: Note title.
            content: Note content.
            openwebui_file_id: OpenWebUI file ID (if uploaded).
        """
        content_hash = self.compute_hash(content)
        timestamp = datetime.utcnow().isoformat()

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO notes (note_id, title, content_hash, last_synced, openwebui_file_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (note_id, title, content_hash, timestamp, openwebui_file_id),
        )

        conn.commit()
        conn.close()
        logger.debug(f"Saved state for note: {note_id}")

    def get_all_synced_note_ids(self) -> set[str]:
        """Get all note IDs that have been synced.

        Returns:
            Set of note IDs.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT note_id FROM notes")
        rows = cursor.fetchall()
        conn.close()

        return {row[0] for row in rows}

    def delete_note_state(self, note_id: str):
        """Delete state for a note (when note is deleted from Joplin).

        Args:
            note_id: Joplin note ID.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("DELETE FROM notes WHERE note_id = ?", (note_id,))

        conn.commit()
        conn.close()
        logger.debug(f"Deleted state for note: {note_id}")

    def log_sync(self, notes_synced: int, notes_updated: int, notes_deleted: int, errors: int):
        """Log a sync operation.

        Args:
            notes_synced: Number of new notes synced.
            notes_updated: Number of notes updated.
            notes_deleted: Number of notes deleted.
            errors: Number of errors encountered.
        """
        timestamp = datetime.utcnow().isoformat()

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO sync_log (timestamp, notes_synced, notes_updated, notes_deleted, errors)
            VALUES (?, ?, ?, ?, ?)
            """,
            (timestamp, notes_synced, notes_updated, notes_deleted, errors),
        )

        conn.commit()
        conn.close()

    def get_stats(self) -> dict:
        """Get sync statistics.

        Returns:
            Dictionary with statistics.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Count total notes
        cursor.execute("SELECT COUNT(*) FROM notes")
        total_notes = cursor.fetchone()[0]

        # Get last sync info
        cursor.execute(
            "SELECT timestamp, notes_synced, notes_updated, notes_deleted, errors FROM sync_log ORDER BY timestamp DESC LIMIT 1"
        )
        last_sync = cursor.fetchone()

        conn.close()

        stats = {"total_notes": total_notes}

        if last_sync:
            stats.update(
                {
                    "last_sync_time": last_sync[0],
                    "last_sync_new": last_sync[1],
                    "last_sync_updated": last_sync[2],
                    "last_sync_deleted": last_sync[3],
                    "last_sync_errors": last_sync[4],
                }
            )

        return stats
