import sqlite3
import uuid
import json

# Database file name
DB_FILE = "chats_history.db"

def load_ch_db():
    """
    Initializes the SQLite database and ensures the 'chats' table exi
    Returns:
    sqlite3.connection: Connection object to the SQLite database
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # reate the 'chats' table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            user_id TEXT NOT NULL,
            session_id INTEGER PRIMARY KEY,
            session_name TEXT,
            messages TEXT,
            first_interaction DATETIME,
            last_interaction DATETIME
        )
    ''')
    conn.commit()
    return conn



def load_user_chats(user: str) -> dict:
    """
    Retrieves all chat sessions for a given user.
    Args:
    user (str): The user ID.
    Returns:
    lict: Dictionary containing 'session_id' and 'sessior
    """
    conn= load_ch_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT session_id, session_name
        FROM chats
        WHERE user_id =?
        ORDER BY first_interaction DESC
    ''',(user,))
    rows = cursor.fetchall()
    conn.close()

    chats_dict ={
        "session_id": [row[0] for row in rows],
        "session_name": [row[1] for row in rows]
    }
    return chats_dict


def add_messages(user_id: str, session_id: int, session_name: str, messages, first_interaction, last_interaction):
    """
    Adds messages to an existing session or creates new session if it doesn't exist
    Args:
    user_id (str): The user ID.
    session_id (int): The session ID.
    session_name (str): The name of the session.
    messages: The list of messages to add (JSON-serializable)
    first_interaction (datetime): Timestamp of the first interaction
    last_interaction (datetime): Timestamp of the last interaction.
    """
    conn = load_ch_db()
    cursor = conn.cursor()

    # check if the session id exists
    cursor.execute('''
    SELECT session_id FROM chats WHERE session_id = ?
                   ''',(session_id,))
    result = cursor.fetchone()

    # Convert messages list to JSON string
    messages_json = json.dumps(messages)

    if result:
    #Update existing session with new messages and last interaction time
        sql_exec= '''
        UPDATE chats
        SET messages = ?, last_interaction = ?
        WHERE session_id = ?
        '''
        cursor.execute(sql_exec, (messages_json, last_interaction, int(session_id)))
    else:
        # Insert a new session into the chats table
        sql_exec = '''
        INSERT INTO chats (user_id, session_id, session_name, messages, first_interaction, last_interaction)
        VALUES (?, ?, ?, ?, ?, ?)
        '''
        cursor.execute(sql_exec, (user_id, session_id, session_name, messages_json, first_interaction, last_interaction))

    conn.commit()
    conn.close()
               

def generate_random_session_id() -> str:
    """
    Generates a unique session ID using UUID.
    Returns:
    str: A unique session ID as a UUID string.
    """
    return str(uuid.uuid4())

def get_messages_by_session_id(session_id: int) -> list:
    """
    Retrieves messages for a given session_id.
    Args:
    session id (int): The session ID.
    Returns:
    list: List of messages or an empty list if not found
    """
    conn = load_ch_db()
    cursor = conn.cursor()

    cursor.execute('SELECT messages FROM chats WHERE session_id = ?', (session_id,))
    result = cursor.fetchone()
    conn.close()

    if result and result[0]:
        try:
            messages= json.loads(result[0])
            if isinstance(messages, list):
                return messages
            else:
                return [messages]
        except json.JSONDecodeError:
            return []
    else:
        return []

def delete_session(session_id: int) -> bool:
    """
    Deletes a session by its session_id.
    Args:
    session_id (int): The session ID to delete
    Returns:
    bool: True if the session was deleted, False otherwise.
    """
    conn = load_ch_db()
    cursor= conn.cursor()

    # Check if the session exists
    cursor.execute('SELECT 1 FROM chats WHERE session_id = ?', (session_id,))
    exists = cursor.fetchone()

    if exists:
        cursor.execute('DELETE FROM chats WHERE session_id = ?', (session_id,))
        conn.commit()
        conn.close()
        return True
    else:
        conn.close()
        return False

def edit_session_name(session_id: int, new_name: str) -> bool:
    """
    Updates the session_name for a given session_ id.
    Args:
    session_id (int): The session ID.
    new_name (str): The new name for the session.
    Returns:
    bool: True if the session name was updated, False otherwise.
    """
    conn= load_ch_db()
    cursor = conn.cursor()

    # Check if the session exists
    cursor.execute('SELECT 1 FROM chats WHERE session_id - ?', (session_id,))
    exists = cursor.fetchone()

    if exists:
        cursor.execute('''
            UPDATE chats
            SET session_name = ?
            WHERE session_id = ?
        ''', (new_name, session_id))
        conn. commit()
        conn.close()
        return True
    else:
        conn.close()
        return False
