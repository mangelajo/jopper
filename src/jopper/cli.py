"""Command-line interface for Jopper.

Provides CLI commands for syncing Joplin notes to OpenWebUI.
"""

import json
import logging
import sys
import time
from pathlib import Path

import click
import schedule

from jopper.config import load_config
from jopper.sync import SyncEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


@click.group()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to config file (default: ~/.config/jopper/config.yaml)",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def main(ctx, config, verbose):
    """Jopper - Synchronize Joplin notes to OpenWebUI knowledge base."""
    if verbose:
        logging.getLogger("jopper").setLevel(logging.DEBUG)

    # Store config path in context
    ctx.ensure_object(dict)
    ctx.obj["config_file"] = config


@main.command()
@click.pass_context
def sync(ctx):
    """Run a one-time sync operation."""
    try:
        # Load configuration
        config_file = ctx.obj.get("config_file")
        config = load_config(config_file)

        # Create sync engine and run sync
        engine = SyncEngine(config)
        result = engine.sync()

        # Display results
        if result["success"]:
            click.echo(click.style("✓ Sync completed successfully!", fg="green"))
            click.echo(f"  New notes synced: {result['notes_synced']}")
            click.echo(f"  Notes updated: {result['notes_updated']}")
            click.echo(f"  Notes deleted: {result['notes_deleted']}")
            if result["errors"] > 0:
                click.echo(click.style(f"  Errors: {result['errors']}", fg="yellow"))
        else:
            click.echo(click.style(f"✗ Sync failed: {result.get('error')}", fg="red"))
            sys.exit(1)

    except ValueError as e:
        click.echo(click.style(f"Configuration error: {e}", fg="red"))
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during sync")
        click.echo(click.style(f"Error: {e}", fg="red"))
        sys.exit(1)


@main.command()
@click.pass_context
def daemon(ctx):
    """Run continuous sync at configured intervals."""
    try:
        # Load configuration
        config_file = ctx.obj.get("config_file")
        config = load_config(config_file)

        # Create sync engine
        engine = SyncEngine(config)

        interval = config.sync.interval_minutes
        click.echo(
            click.style(f"Starting daemon mode (sync every {interval} minutes)...", fg="blue")
        )
        click.echo("Press Ctrl+C to stop")

        # Run initial sync
        click.echo("\nRunning initial sync...")
        result = engine.sync()
        _display_sync_result(result)

        # Schedule periodic syncs
        schedule.every(interval).minutes.do(lambda: _scheduled_sync(engine))

        # Run scheduler loop
        while True:
            schedule.run_pending()
            time.sleep(1)

    except KeyboardInterrupt:
        click.echo("\n" + click.style("Daemon stopped by user", fg="yellow"))
        sys.exit(0)
    except ValueError as e:
        click.echo(click.style(f"Configuration error: {e}", fg="red"))
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error in daemon mode")
        click.echo(click.style(f"Error: {e}", fg="red"))
        sys.exit(1)


def _scheduled_sync(engine: SyncEngine):
    """Run a scheduled sync and display results."""
    click.echo(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Running scheduled sync...")
    result = engine.sync()
    _display_sync_result(result)


def _display_sync_result(result: dict):
    """Display sync result in a compact format."""
    if result["success"]:
        click.echo(
            click.style(
                f"✓ Synced: {result['notes_synced']} new, "
                f"{result['notes_updated']} updated, "
                f"{result['notes_deleted']} deleted",
                fg="green",
            )
        )
        if result["errors"] > 0:
            click.echo(click.style(f"  Errors: {result['errors']}", fg="yellow"))
    else:
        click.echo(click.style(f"✗ Sync failed: {result.get('error')}", fg="red"))


@main.command()
@click.pass_context
def status(ctx):
    """Show sync status and statistics."""
    try:
        # Load configuration
        config_file = ctx.obj.get("config_file")
        config = load_config(config_file)

        # Create sync engine and get status
        engine = SyncEngine(config)
        status_info = engine.get_status()

        # Display configuration
        click.echo(click.style("Configuration:", fg="blue", bold=True))
        config_data = status_info["config"]
        click.echo(f"  Joplin: {config_data['joplin_host']}")
        click.echo(f"  OpenWebUI: {config_data['openwebui_url']}")
        click.echo(f"  Knowledge Base: {config_data['knowledge_base_name']}")
        click.echo(
            f"  Sync Mode: {config_data['sync_mode']}"
            + (
                f" (tags: {', '.join(config_data['sync_tags'])})"
                if config_data["sync_tags"]
                else ""
            )
        )
        click.echo(f"  Sync Interval: {config_data['sync_interval']} minutes")

        # Display statistics
        click.echo("\n" + click.style("Statistics:", fg="blue", bold=True))
        stats = status_info["stats"]
        click.echo(f"  Total notes synced: {stats.get('total_notes', 0)}")

        if "last_sync_time" in stats:
            click.echo(f"\n  Last sync: {stats['last_sync_time']}")
            click.echo(f"    New: {stats['last_sync_new']}")
            click.echo(f"    Updated: {stats['last_sync_updated']}")
            click.echo(f"    Deleted: {stats['last_sync_deleted']}")
            if stats["last_sync_errors"] > 0:
                click.echo(click.style(f"    Errors: {stats['last_sync_errors']}", fg="yellow"))
        else:
            click.echo("  No sync operations recorded yet")

    except ValueError as e:
        click.echo(click.style(f"Configuration error: {e}", fg="red"))
        sys.exit(1)
    except Exception as e:
        logger.exception("Error getting status")
        click.echo(click.style(f"Error: {e}", fg="red"))
        sys.exit(1)


@main.command()
@click.option("--format", "-f", type=click.Choice(["text", "json"]), default="text")
@click.pass_context
def config(ctx, format):
    """Show current configuration."""
    try:
        # Load configuration
        config_file = ctx.obj.get("config_file")
        config_obj = load_config(config_file)

        config_data = {
            "joplin": {
                "host": config_obj.joplin.host,
                "port": config_obj.joplin.port,
                "token": "***" + config_obj.joplin.token[-4:] if config_obj.joplin.token else "***",
            },
            "openwebui": {
                "url": config_obj.openwebui.url,
                "api_key": "***" + config_obj.openwebui.api_key[-4:]
                if config_obj.openwebui.api_key
                else "***",
                "knowledge_base_name": config_obj.openwebui.knowledge_base_name,
            },
            "sync": {
                "mode": config_obj.sync.mode,
                "tags": config_obj.sync.tags,
                "interval_minutes": config_obj.sync.interval_minutes,
            },
            "state_db_path": str(config_obj.state_db_path),
        }

        if format == "json":
            click.echo(json.dumps(config_data, indent=2))
        else:
            click.echo(click.style("Current Configuration:", fg="blue", bold=True))
            click.echo("\nJoplin:")
            click.echo(f"  Host: {config_data['joplin']['host']}")
            click.echo(f"  Port: {config_data['joplin']['port']}")
            click.echo(f"  Token: {config_data['joplin']['token']}")

            click.echo("\nOpenWebUI:")
            click.echo(f"  URL: {config_data['openwebui']['url']}")
            click.echo(f"  API Key: {config_data['openwebui']['api_key']}")
            click.echo(f"  Knowledge Base: {config_data['openwebui']['knowledge_base_name']}")

            click.echo("\nSync:")
            click.echo(f"  Mode: {config_data['sync']['mode']}")
            click.echo(
                f"  Tags: {', '.join(config_data['sync']['tags']) if config_data['sync']['tags'] else '(none)'}"
            )
            click.echo(f"  Interval: {config_data['sync']['interval_minutes']} minutes")

            click.echo(f"\nState DB: {config_data['state_db_path']}")

    except ValueError as e:
        click.echo(click.style(f"Configuration error: {e}", fg="red"))
        sys.exit(1)
    except Exception as e:
        logger.exception("Error loading config")
        click.echo(click.style(f"Error: {e}", fg="red"))
        sys.exit(1)


if __name__ == "__main__":
    main(obj={})
