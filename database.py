import sqlite3

def get_db_connection():
    conn = sqlite3.connect("chat_history.db")
    conn.execute("PRAGMA foreign_keys = ON;")  # Enable foreign key constraints
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Drop existing tables (only if you need to recreate the schema)
    # Be cautious: this will delete existing data
    # cursor.execute("DROP TABLE IF EXISTS messages;")
    # cursor.execute("DROP TABLE IF EXISTS chats;")

    # Create chats table with document_text column
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            document_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Create messages table with ON DELETE CASCADE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
        );
    """)

    conn.commit()
    conn.close()

def load_chat_messages(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content FROM messages
        WHERE chat_id = ?
        ORDER BY timestamp ASC
    """, (chat_id,))
    messages = cursor.fetchall()
    conn.close()
    return [{"role": role, "content": content} for role, content in messages]

def save_message(chat_id, role, content):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)
    """, (chat_id, role, content))
    conn.commit()
    conn.close()

def save_document_text(chat_id, document_text):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE chats SET document_text = ? WHERE id = ?
    """, (document_text, chat_id))
    conn.commit()
    conn.close()

def load_document_text(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT document_text FROM chats WHERE id = ?
    """, (chat_id,))
    result = cursor.fetchone()
    conn.close()
    if result and result[0]:
        return result[0]
    else:
        return ""