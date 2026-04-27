from datetime import datetime
from pathlib import Path
import sqlite3

from app.extensions import db


def create_database_backup(app):
    backup_dir = Path(app.config["BACKUP_DIR"])
    backup_dir.mkdir(parents=True, exist_ok=True)

    source_path = Path(db.engine.url.database)
    backup_path = backup_dir / f"ctc_aranha_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

    source_connection = sqlite3.connect(source_path)
    backup_connection = sqlite3.connect(backup_path)
    try:
        source_connection.backup(backup_connection)
    finally:
        backup_connection.close()
        source_connection.close()

    return backup_path


def list_backups(app):
    backup_dir = Path(app.config["BACKUP_DIR"])
    if not backup_dir.exists():
        return []
    return sorted(backup_dir.glob("*.db"), key=lambda item: item.stat().st_mtime, reverse=True)
