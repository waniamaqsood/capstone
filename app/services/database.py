import sqlite3; from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_PATH = BASE_DIR / "content_repurposer.db"

def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def init_db():
    connection = get_connection()
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

            FOREIGN KEY (post_id)
                REFERENCES posts(id)
        )
        """
    )
    connection.commit()
    connection.close()

def create_post(content: str, source_type: str, source_url: str | None = None,) -> int:
    connection = get_connection()
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
    connection.close()

    return post_id

def create_variant(post_id: int, platform: str, content: str, status: str = "draft",) -> int:
    connection = get_connection()
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
    connection.close()

    return variant_id


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
    return post

def get_variants_for_post(post_id: int):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT *
        FROM variants
        WHERE post_id = ?
        ORDER BY created_at ASC
        """,
        (post_id,),
    )

    variants = cursor.fetchall()

    connection.close()

    return variants

if __name__ == "__main__":
    init_db()
    print(f"Database initialized at: {DATABASE_PATH}")