# db_helpers.py
import sqlite3
import hashlib
import json
from datetime import datetime
import os

DB_PATH = "symptom_checker.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    
    # Sessions table (updated - removed end_time)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_hash TEXT UNIQUE NOT NULL,
            start_time TIMESTAMP NOT NULL,
            age INTEGER,
            gender TEXT,
            patient_name TEXT
        )
    ''')
    
    # Messages table for conversation history
    conn.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL,  -- 'user', 'bot', or 'meta'
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id)
        )
    ''')
    
    # Results table for analysis results
    conn.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            api_name TEXT NOT NULL,
            result TEXT NOT NULL,  -- JSON stored as text
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def create_session(start_time, age=None, gender=None, patient_name=None):
    session_hash = hashlib.md5(f"{start_time}{age}{gender}{patient_name}".encode()).hexdigest()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO sessions (session_hash, start_time, age, gender, patient_name)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_hash, start_time, age, gender, patient_name))
        
        session_id = cursor.lastrowid
        conn.commit()
        return session_id
        
    except sqlite3.IntegrityError:
        # Session already exists, return existing ID
        cursor.execute('SELECT id FROM sessions WHERE session_hash = ?', (session_hash,))
        result = cursor.fetchone()
        return result[0] if result else None
        
    finally:
        conn.close()

def update_session_patient_info(session_id, age=None, gender=None, patient_name=None):
    conn = get_db_connection()
    
    # Build update query dynamically based on provided fields
    updates = []
    params = []
    
    if age is not None:
        updates.append("age = ?")
        params.append(age)
    
    if gender is not None:
        updates.append("gender = ?")
        params.append(gender)
        
    if patient_name is not None:
        updates.append("patient_name = ?")
        params.append(patient_name)
    
    if updates:
        params.append(session_id)
        query = f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?"
        
        conn.execute(query, params)
        conn.commit()
    
    conn.close()

def log_message(session_id, role, content):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO messages (session_id, role, content)
        VALUES (?, ?, ?)
    ''', (session_id, role, content))
    conn.commit()
    conn.close()

def log_result(session_id, api_name, result):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO results (session_id, api_name, result)
        VALUES (?, ?, ?)
    ''', (session_id, api_name, json.dumps(result)))
    conn.commit()
    conn.close()

def close_session(session_id):
    # With the new schema, we don't need to do anything special to close a session
    # This function is kept for backward compatibility
    pass

def get_sessions(limit=100):
    conn = get_db_connection()
    cursor = conn.execute('''
        SELECT id, session_hash, start_time, age, gender, patient_name
        FROM sessions 
        ORDER BY start_time DESC 
        LIMIT ?
    ''', (limit,))
    sessions = cursor.fetchall()
    conn.close()
    return sessions

def get_messages_for_session(session_id):
    conn = get_db_connection()
    cursor = conn.execute('''
        SELECT role, content, timestamp
        FROM messages 
        WHERE session_id = ?
        ORDER BY timestamp ASC
    ''', (session_id,))
    messages = cursor.fetchall()
    conn.close()
    return messages

def get_results_for_session(session_id):
    conn = get_db_connection()
    cursor = conn.execute('''
        SELECT api_name, result, timestamp
        FROM results 
        WHERE session_id = ?
        ORDER BY timestamp DESC
    ''', (session_id,))
    results = []
    for row in cursor.fetchall():
        try:
            result_data = json.loads(row[1])
            results.append({
                'api_name': row[0],
                'result': result_data,
                'timestamp': row[2]
            })
        except json.JSONDecodeError:
            continue
    conn.close()
    return results

def get_conversation_history(session_id):
    """Get complete conversation history for a session"""
    conn = get_db_connection()
    
    # Get messages
    cursor = conn.execute('''
        SELECT role, content, timestamp
        FROM messages 
        WHERE session_id = ?
        ORDER BY timestamp ASC
    ''', (session_id,))
    messages = [dict(row) for row in cursor.fetchall()]
    
    # Get analysis results
    cursor = conn.execute('''
        SELECT api_name, result, timestamp
        FROM results 
        WHERE session_id = ?
        ORDER BY timestamp ASC
    ''', (session_id,))
    
    analyses = []
    for row in cursor.fetchall():
        try:
            result_data = json.loads(row[1])
            analyses.append({
                'api_name': row[0],
                'result': result_data,
                'timestamp': row[2]
            })
        except json.JSONDecodeError:
            continue
    
    conn.close()
    
    return {
        'messages': messages,
        'analyses': analyses
    }