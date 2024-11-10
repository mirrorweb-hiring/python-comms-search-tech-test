from datetime import datetime, timedelta, timezone
import secrets
import bcrypt
import sqlite3



def verify_password(password_hash: str, password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), str(password_hash).encode('utf-8'))

def create_session(db: sqlite3.Connection, user_id: int):
    session_id = secrets.token_hex(16)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)  # 1 week
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO session (id, user_id, expires_at) VALUES (?, ?, ?)',
        (session_id, user_id, int(expires_at.timestamp()))
    )
    db.commit()
    return {
        'id': session_id,
        'user_id': user_id,
        'expires_at': expires_at,
    }

def validate_session(db: sqlite3.Connection, session_id: str):
    session = get_session(db, session_id)
    if not session:
        return {'session': None, 'user': None}
    user = get_user_from_session(db, session_id)
    if not user:
        delete_session(db, session_id)
        return {'session': None, 'user': None}
    if is_session_expired(session['expires_at']):
        delete_session(db, session_id)
        return {'session': None, 'user': None}
    return {'session': session, 'user': user}

def get_session(db: sqlite3.Connection, session_id: str):
    cursor = db.cursor()
    cursor.execute('SELECT * FROM session WHERE id = ?', (session_id,))
    result = cursor.fetchone()
    if not result:
        return None
    return {
        'id': result[0],
        'user_id': result[1],
        'expires_at': datetime.fromtimestamp(result[2], tz=timezone.utc),
    }

def delete_session(db: sqlite3.Connection, session_id: str):
    cursor = db.cursor()
    cursor.execute('DELETE FROM session WHERE id = ?', (session_id,))
    db.commit()

def get_user_from_session(db: sqlite3.Connection, session_id: str):
    cursor = db.cursor()
    cursor.execute(
        '''
        SELECT user.* FROM session
        INNER JOIN user ON user.id = session.user_id
        WHERE session.id = ?
        ''',
        (session_id,)
    )
    result = cursor.fetchone()
    if not result:
        return None
    return {
        'id': result[0],
        'email': result[1],
        'password_hash': result[2],
        'created_at': datetime.fromtimestamp(result[3], tz=timezone.utc),
    }

def get_user_by_email(db: sqlite3.Connection, email: str):
    cursor = db.cursor()
    cursor.execute('SELECT * FROM user WHERE email = ?', (email,))
    result = cursor.fetchone()
    if not result:
        return None
    return {
        'id': result[0],
        'email': result[1],
        'password_hash': result[2],
        'created_at': datetime.fromtimestamp(result[3], tz=timezone.utc),
    }

def is_session_expired(expires_at: datetime) -> bool:
    return expires_at < datetime.now(timezone.utc)