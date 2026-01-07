"""Joplin server lifecycle management.

Manages starting and stopping the Joplin CLI server process.
"""

import json
import logging
import os
import socket
import subprocess
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


class JoplinServerManager:
    """Manages the Joplin CLI server process."""

    def __init__(self, config_dict: dict, port: int = 41184, profile_dir: str = None):
        """Initialize Joplin server manager.

        Args:
            config_dict: Joplin configuration dictionary.
            port: Port for Joplin Data API (default: 41184).
            profile_dir: Profile directory for Joplin data (default: ~/.config/joplin).
        """
        self.config_dict = config_dict
        self.port = port
        self.profile_dir = profile_dir or os.path.expanduser("~/.config/joplin")
        self.process = None
        self._setup_profile_dir()

    def _setup_profile_dir(self):
        """Ensure profile directory exists and ensure settings are correct."""
        profile_path = Path(self.profile_dir)
        profile_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using Joplin profile directory: {self.profile_dir}")
        
        # Always write/update settings.json to ensure token is correct
        settings_file = profile_path / "settings.json"
        
        # Check if settings need to be updated
        needs_update = True
        if settings_file.exists():
            try:
                existing_settings = json.loads(settings_file.read_text())
                existing_token = existing_settings.get("api.token")
                configured_token = self.config_dict.get("api.token")
                
                if existing_token == configured_token:
                    logger.debug("Joplin settings file exists with correct token")
                    needs_update = False
                else:
                    logger.info(f"Joplin token mismatch - updating settings file")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not read existing settings: {e}, will recreate")
        
        if needs_update:
            logger.info("Writing Joplin settings file with configured token")
            settings_file.write_text(json.dumps(self.config_dict, indent=2))

    def _is_port_listening(self) -> bool:
        """Check if the configured port is already listening.

        Returns:
            True if port is listening, False otherwise.
        """
        try:
            # Try to connect to the port
            with socket.create_connection(("localhost", self.port), timeout=1):
                # Port is listening, verify it's actually Joplin
                try:
                    url = f"http://localhost:{self.port}/ping"
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        logger.info(f"Joplin server already running on port {self.port}")
                        return True
                except requests.exceptions.RequestException:
                    # Port is open but not responding to /ping
                    logger.warning(
                        f"Port {self.port} is in use but not responding as Joplin server"
                    )
                    return False
        except (socket.error, ConnectionRefusedError, TimeoutError):
            # Port is not listening
            return False
        return False

    def start(self, timeout: int = 60, sync_first: bool = True) -> bool:
        """Start the Joplin server.

        Args:
            timeout: Maximum time to wait for server to be ready (seconds).
            sync_first: Whether to sync with Joplin Server before starting (default: True).

        Returns:
            True if server started successfully, False otherwise.
        """
        # Check if our managed process is already running
        if self.process and self.process.poll() is None:
            logger.info("Joplin server process already running (managed by us)")
            return True

        # Check if the port is already listening (e.g., external Joplin instance)
        if self._is_port_listening():
            logger.info(
                f"Joplin server already available on port {self.port}, skipping start"
            )
            return True

        # Sync with Joplin Server first to get latest notes
        if sync_first:
            logger.info("Syncing with Joplin Server to fetch latest notes...")
            if not self.trigger_sync():
                logger.warning("Joplin sync failed, continuing with cached notes")

        logger.info(f"Starting Joplin server on port {self.port}...")

        # Set up environment with Joplin configuration
        env = os.environ.copy()
        env["JOPLIN_CONFIG_JSON"] = json.dumps(self.config_dict)
        
        # Always set HOME explicitly (required for Joplin to find config directory)
        # Infer HOME from profile_dir (e.g., /home/node/.config/joplin -> /home/node)
        home_dir = str(Path(self.profile_dir).parent.parent)
        env["HOME"] = home_dir
        logger.info(f"Setting HOME={home_dir} for Joplin process")

        try:
            # Start Joplin server as a subprocess with --profile flag
            self.process = subprocess.Popen(
                ["joplin", "server", "start", "--profile", self.profile_dir],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            logger.info(f"Joplin server process started (PID: {self.process.pid})")

            # Wait for server to be ready
            if not self._wait_for_ready(timeout):
                logger.error("Joplin server failed to become ready")
                self.stop()
                return False

            logger.info(f"Joplin server is ready on port {self.port}")
            return True

        except FileNotFoundError:
            logger.error(
                "Joplin CLI not found. Make sure 'joplin' command is available in PATH"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to start Joplin server: {e}")
            if self.process:
                self.stop()
            return False

    def _wait_for_ready(self, timeout: int) -> bool:
        """Wait for Joplin server to be ready.

        Args:
            timeout: Maximum time to wait (seconds).

        Returns:
            True if server is ready, False otherwise.
        """
        start_time = time.time()
        url = f"http://localhost:{self.port}/ping"

        logger.info("Waiting for Joplin server to be ready...")

        while time.time() - start_time < timeout:
            # Check if process is still running
            if self.process and self.process.poll() is not None:
                logger.error("Joplin server process died unexpectedly")
                # Print stderr if available
                if self.process.stderr:
                    stderr = self.process.stderr.read()
                    if stderr:
                        logger.error(f"Joplin stderr: {stderr}")
                return False

            try:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass  # Server not ready yet

            time.sleep(2)

        return False

    def stop(self):
        """Stop the Joplin server."""
        if not self.process:
            return

        logger.info("Stopping Joplin server...")
        try:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("Joplin server did not stop gracefully, killing...")
                self.process.kill()
                self.process.wait()
        except Exception as e:
            logger.error(f"Error stopping Joplin server: {e}")
        finally:
            self.process = None

        logger.info("Joplin server stopped")

    def is_running(self) -> bool:
        """Check if Joplin server is running.

        Returns:
            True if server is running, False otherwise.
        """
        if not self.process:
            return False
        return self.process.poll() is None

    def trigger_sync(self) -> bool:
        """Trigger a Joplin sync to fetch latest notes from server.

        Returns:
            True if sync succeeded, False otherwise.
        """
        logger.info("Triggering Joplin sync to fetch latest notes...")

        # Set up environment with Joplin configuration
        env = os.environ.copy()
        env["JOPLIN_CONFIG_JSON"] = json.dumps(self.config_dict)
        
        # Always set HOME explicitly (required for Joplin to find config directory)
        # Infer HOME from profile_dir (e.g., /home/node/.config/joplin -> /home/node)
        home_dir = str(Path(self.profile_dir).parent.parent)
        env["HOME"] = home_dir
        logger.debug(f"Setting HOME={home_dir} for Joplin sync")

        try:
            # Run joplin sync command with --profile flag
            result = subprocess.run(
                ["joplin", "sync", "--profile", self.profile_dir],
                env=env,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout for sync
            )

            if result.returncode == 0:
                logger.info("Joplin sync completed successfully")
                return True
            else:
                logger.error(f"Joplin sync failed with code {result.returncode}")
                if result.stderr:
                    logger.error(f"Joplin sync error: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Joplin sync timed out after 5 minutes")
            return False
        except FileNotFoundError:
            logger.error("Joplin CLI not found. Cannot trigger sync.")
            return False
        except Exception as e:
            logger.error(f"Failed to trigger Joplin sync: {e}")
            return False

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

