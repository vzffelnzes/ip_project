import sqlite3

DB_NAME = "banned_words.db"


def init_db():
    """Инициализация базы данных."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS banned_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_word_to_db(word):
    """Добавляет слово в базу данных."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO banned_words (word) VALUES (?)", (word,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Слово уже существует
    finally:
        conn.close()


def get_all_banned_words():
    """Возвращает все запрещённые слова из базы данных."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM banned_words")
    words = [row[0] for row in cursor.fetchall()]
    conn.close()
    return words


def delete_word_from_db(word):
    """Удаляет слово из базы данных."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM banned_words WHERE word = ?", (word,))
    conn.commit()
    conn.close()
