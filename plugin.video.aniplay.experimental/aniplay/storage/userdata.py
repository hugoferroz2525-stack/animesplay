"""Migração transacional dos dados pessoais criados até a versão 2.6.4."""
from pathlib import Path
import sqlite3

TABLES = ('library', 'searches', 'opening', 'tmdb_choice', 'audio_preferences')


def connect(cache_path):
    db = sqlite3.connect(Path(cache_path).with_name('userdata.sqlite'), timeout=15)
    try:
        if db.execute('PRAGMA user_version').fetchone()[0]:
            return db
        db.execute('ATTACH DATABASE ? AS legacy', (str(cache_path),))
        with db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('PRAGMA main.user_version').fetchone()[0]:
                for table in TABLES:
                    schema = db.execute("SELECT sql FROM legacy.sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
                    if schema:
                        db.execute(schema[0])
                        db.execute(f'INSERT INTO main.{table} SELECT * FROM legacy.{table}')
                        db.execute(f'DROP TABLE legacy.{table}')
                db.execute('PRAGMA main.user_version=1')
        db.execute('DETACH DATABASE legacy')
        return db
    except Exception:
        db.close()
        raise
