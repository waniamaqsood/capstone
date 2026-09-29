from pathlib import Path; import sqlite3; from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "content_repurposer.db"

def get_connection():
    connection = sqlite3.connect(
        DB_PATH,
        timeout=30,
    )
    connection.row_factory = sqlite3.Row
    return connection

def init_db():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url TEXT,
                content TEXT NOT NULL,
                source_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS variants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                variant_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                scheduled_at TIMESTAMP NOT NULL,
                idempotency_key TEXT UNIQUE,
                FOREIGN KEY (variant_id) REFERENCES variants(id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS publish_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                variant_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                idempotency_key TEXT NOT NULL,
                result TEXT NOT NULL,
                error_message TEXT,
                FOREIGN KEY (variant_id) REFERENCES variants(id)
            )
            """
        )

        connection.commit()

    finally:
        connection.close()

def create_post(content: str, source_type: str, source_url: str | None = None,) -> int:
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO posts (
                source_url,
                content,
                source_type
            )
            VALUES (?, ?, ?)
            """,
            (
                source_url,
                content,
                source_type,
            ),
        )

        post_id = cursor.lastrowid

        connection.commit()

        return post_id

    finally:
        connection.close()

def get_post(post_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM posts
        WHERE id = ?
        """,
        (post_id,),
    )

    post = cursor.fetchone()

    connection.close()

    return dict(post) if post else None


def create_variant(post_id: int, platform: str, content: str, status: str = "draft",) -> int:
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO variants (
                post_id,
                platform,
                content,
                status
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                post_id,
                platform,
                content,
                status,
            ),
        )

        variant_id = cursor.lastrowid

        connection.commit()

        return variant_id

    finally:
        connection.close()

def update_variant(variant_id: int, content: str | None = None, status: str | None = None,):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        fields = []
        values = []

        if content is not None:
            fields.append("content = ?")
            values.append(content)

        if status is not None:
            fields.append("status = ?")
            values.append(status)

        if not fields:
            return

        values.append(variant_id)

        query = f"""
            UPDATE variants
            SET {", ".join(fields)}
            WHERE id = ?
        """

        cursor.execute(query, values)

        connection.commit()

    finally:
        connection.close()

def get_variant(variant_id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM variants
            WHERE id = ?
            """,
            (variant_id,),
        )

        variant = cursor.fetchone()

        return dict(variant) if variant else None

    finally:
        connection.close()

def update_variant(
    variant_id: int,
    content: str | None = None,
    status: str | None = None,
):
    connection = get_connection()
    cursor = connection.cursor()

    fields = []
    values = []

    if content is not None:
        fields.append("content = ?")
        values.append(content)

    if status is not None:
        fields.append("status = ?")
        values.append(status)

    if not fields:
        connection.close()
        return

    values.append(variant_id)

    query = f"""
        UPDATE variants
        SET {", ".join(fields)}
        WHERE id = ?
    """

    cursor.execute(query, values)

    connection.commit()
    connection.close()


def create_schedule(variant_id: int, platform: str, scheduled_at: datetime,idempotency_key: str,) -> int:
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO schedules (
                variant_id,
                platform,
                scheduled_at,
                idempotency_key
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                variant_id,
                platform,
                scheduled_at,
                idempotency_key,
            ),
        )

        schedule_id = cursor.lastrowid

        connection.commit()

        return schedule_id

    finally:
        connection.close()

def get_schedule(schedule_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM schedules
        WHERE id = ?
        """,
        (schedule_id,),
    )

    schedule = cursor.fetchone()

    connection.close()

    return dict(schedule) if schedule else None


def get_schedules_for_variant(variant_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM schedules
        WHERE variant_id = ?
        ORDER BY id
        """,
        (variant_id,),
    )

    schedules = cursor.fetchall()

    connection.close()

    return [dict(schedule) for schedule in schedules]


def get_schedule_by_variant(
    variant_id: int,
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM schedules
        WHERE variant_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (variant_id,),
    )

    schedule = cursor.fetchone()

    connection.close()

    return dict(schedule) if schedule else None


def create_publish_history(variant_id: int, platform: str, idempotency_key: str, result: str, error_message: str | None = None,) -> int:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO publish_history (
            variant_id,
            platform,
            idempotency_key,
            result,
            error_message
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            variant_id,
            platform,
            idempotency_key,
            result,
            error_message,
        ),
    )

    history_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return history_id


def get_publish_history_by_key(
    idempotency_key: str,
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM publish_history
        WHERE idempotency_key = ?
        AND result = 'success'
        LIMIT 1
        """,
        (idempotency_key,),
    )

    history = cursor.fetchone()

    connection.close()

    return dict(history) if history else None


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at: {DB_PATH}")