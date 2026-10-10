"""Export recent T3 Code thread transcripts from the local projection database."""

from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path


def safe_filename(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return value[:80] or "untitled"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(args.database)
    connection.row_factory = sqlite3.Row
    threads = connection.execute(
        """
        SELECT thread_id, title, branch, worktree_path, created_at, updated_at,
               archived_at, deleted_at
        FROM projection_threads
        WHERE project_id = ? AND deleted_at IS NULL
        ORDER BY updated_at DESC, thread_id DESC
        LIMIT ?
        """,
        (args.project_id, args.limit),
    ).fetchall()

    for index, thread in enumerate(threads, start=1):
        messages = connection.execute(
            """
            SELECT role, text, created_at, updated_at
            FROM projection_thread_messages
            WHERE thread_id = ?
            ORDER BY created_at ASC, message_id ASC
            """,
            (thread["thread_id"],),
        ).fetchall()
        filename = f"{index:02d}_{safe_filename(thread['title'])}_{thread['thread_id']}.txt"
        destination = args.output / filename
        with destination.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(f"Thread ID: {thread['thread_id']}\n")
            handle.write(f"Title: {thread['title']}\n")
            handle.write(f"Branch: {thread['branch'] or ''}\n")
            handle.write(f"Worktree: {thread['worktree_path'] or ''}\n")
            handle.write(f"Created: {thread['created_at']}\n")
            handle.write(f"Updated: {thread['updated_at']}\n")
            handle.write(f"Messages: {len(messages)}\n")
            handle.write("\n" + "=" * 80 + "\n\n")
            for message in messages:
                handle.write(
                    f"[{message['created_at']}] {message['role'].upper()}\n"
                    f"{message['text']}\n\n"
                    + "-" * 80
                    + "\n\n"
                )

    print(f"Exported {len(threads)} threads to {args.output}")


if __name__ == "__main__":
    main()
