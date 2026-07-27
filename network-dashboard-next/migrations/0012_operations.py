from __future__ import annotations

import sqlite3


def upgrade(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS managed_services(
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            unit_name TEXT NOT NULL UNIQUE,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS computer_agents_v2(
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            active INTEGER NOT NULL DEFAULT 1,
            last_seen TEXT NOT NULL DEFAULT '',
            status_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_computer_agents_seen
            ON computer_agents_v2(active DESC,last_seen DESC);

        CREATE TABLE IF NOT EXISTS agent_commands_v2(
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            command_type TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'queued',
            created_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            claimed_at TEXT NOT NULL DEFAULT '',
            completed_at TEXT NOT NULL DEFAULT '',
            result_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(agent_id) REFERENCES computer_agents_v2(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_agent_commands_queue
            ON agent_commands_v2(agent_id,status,created_at);

        CREATE TABLE IF NOT EXISTS homelab_baselines_v2(
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            created_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_homelab_baselines_created
            ON homelab_baselines_v2(created_at DESC);
        """
    )
