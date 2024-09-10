import datetime
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import sqlite3
from typing import Optional
from auth import validate_session, create_session, delete_session, verify_password
import time
import uvicorn
import asyncio
import random
import pytz

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
def get_db():
    conn = sqlite3.connect('db/comms.db', check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

# Utility functions
def get_cookie(request: Request, name: str) -> Optional[str]:
    return request.cookies.get(name)

def set_cookie(response: Response, name: str, value: str, max_age: int = None):
    response.set_cookie(key=name, value=value, domain='localhost', httponly=False, max_age=3600, samesite='lax')

# Models
class User(BaseModel):
    id: int
    email: str
    password_hash: str

class Message(BaseModel):
    id: int
    subject: str
    content: str
    status: Optional[str]
    created_at: int
    from_email: str
    to_email: str

class LoginRequest(BaseModel):
    email: str
    password: str

class UpdateMessageRequest(BaseModel):
    status: str

# Routes
@app.get("/me")
async def get_me(request: Request, db: sqlite3.Connection = Depends(get_db)):
    session_id = get_cookie(request, 'comms_auth')
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    session, user = validate_session(db, session_id)
    if not session or not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return JSONResponse(content={"user": user})

@app.post("/login")
async def login(request: Request, response: Response, db: sqlite3.Connection = Depends(get_db)):
    data = await request.json()
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Bad Request")
    cursor = db.cursor()
    cursor.execute(f"SELECT * FROM user WHERE email = '{email}'")
    user = cursor.fetchone()
    if not user or not verify_password(user[3], password):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    session_id = create_session(db, user[0])
    set_cookie(response, 'comms_auth', session_id)
    return True

@app.get("/logout")
async def logout(request: Request, response: Response, db: sqlite3.Connection = Depends(get_db)):
    session_id = get_cookie(request, 'comms_auth')
    if not session_id:
        raise HTTPException(status_code=400, detail="Bad request")
    delete_session(db, session_id)
    set_cookie(response, 'comms_auth', '', max_age=0)
    return JSONResponse(content={"message": "Logged out"})

@app.get("/messages")
async def get_messages(request: Request, db: sqlite3.Connection = Depends(get_db), page: int = 1, page_size: int = 10 ):
    session_id = get_cookie(request, 'comms_auth')
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    session, user = validate_session(db, session_id)
    if not session or not user:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    
    # Validate page and page_sizes values
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail= "Page and page size must be greater than zero")
    

    order = request.query_params.get("order", "asc").upper()
    if order not in ["ASC", "DESC"]:
        raise HTTPException(status_code=400, detail="Invalid order value")
    
     # Calculate the offset for pagination
    offset = (page - 1) * page_size

    cursor = db.cursor()
    cursor.execute(
        f"""
        SELECT
            m.id, m.subject, m.content, m.status, m.created_at,
            from_identity.email as from_email, to_identity.email as to_email
        FROM
            message m
        JOIN
            identity from_identity ON m."from" = from_identity.id
        JOIN
            identity to_identity ON m."to" = to_identity.id
        ORDER BY m.created_at {order}
        LIMIT ? OFFSET ?
        """, (page_size, offset)
    )
    messages = cursor.fetchall()
    formatted_messages = [
        {
            "id": message[0],
            "subject": message[1],
            "content": message[2],
            "status": message[3],
            "created_at": time_ago(message[4]),
            "from_email": message[5],
            "to_email": message[6]
        }
        for message in messages
    ]

    # Calculate the total number of messages for pagination metadata
    cursor.execute("SELECT COUNT(*) FROM message")
    total_messages = cursor.fetchone()[0]
    total_pages = (total_messages // page_size) + (1 if total_messages % page_size > 0 else 0)
    
    return JSONResponse({
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "total_messages": total_messages,
        "messages": formatted_messages
    })

def time_ago(timestamp):
    now = datetime.utcnow()
    timestamp = datetime.utcfromtimestamp(timestamp)
    delta = now - timestamp

    if delta < datetime.timedelta(minutes=1):
        return "Just now"
    elif delta < datetime.timedelta(hours=1):
        minutes = int(delta.total_seconds() // 60)
        return f"{minutes} minutes ago"
    elif delta < datetime.timedelta(days=1):
        hours = int(delta.total_seconds() // 3600)
        return f"{hours} hours ago"
    else:
        days = int(delta.total_seconds() // 86400)
        return f"{days} days ago"
    
@app.get("/messages/{id}")
async def get_message(id: str, request: Request, db: sqlite3.Connection = Depends(get_db)):
    session_id = get_cookie(request, 'comms_auth')
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    session, user = validate_session(db, session_id)
    if not session or not user:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    cursor = db.cursor()
    cursor.execute(
        f"""
        SELECT
            m.id, m.subject, m.content, m.status, m.created_at,
            from_identity.email as from_email, to_identity.email as to_email
        FROM
            message m
        JOIN
            identity from_identity ON m."from" = from_identity.id
        JOIN
            identity to_identity ON m."to" = to_identity.id
        WHERE
            m.id = '{id}'
        """
    )
    message = cursor.fetchone()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message_dict = {
        "id": message[0],
        "subject": message[1],
        "content": message[2],
        "status": message[3],
        "created_at": message[4],
        "from_email": message[5],
        "to_email": message[6]
    }
    
    return JSONResponse(message_dict)

@app.put("/messages/{id}")
async def update_message(id: int, request: Request, db: sqlite3.Connection = Depends(get_db)):
    session_id = get_cookie(request, 'comms_auth')
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    session, user = validate_session(db, session_id)
    if not session or not user:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    data = await request.json()
    status = data.get("status")
    if not status or status not in ["compliant", "non_compliant"]:
        raise HTTPException(status_code=400, detail="Please provide a valid status")
    cursor = db.cursor()
    cursor.execute("UPDATE message SET status = ? WHERE id = ?", (status, id))
    db.commit()
    return JSONResponse(content={"message": "Message updated", "new_status": status})

@app.get("/search")
async def search_messages(request: Request, db: sqlite3.Connection = Depends(get_db)):
    session_id = get_cookie(request, 'comms_auth')
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    session, user = validate_session(db, session_id)
    if not session or not user:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    query = request.query_params.get("q")
    if not query:
        raise HTTPException(status_code=400, detail="Please provide a search query")
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT
            m.id, m.subject, m.content, m.status, m.created_at,
            from_identity.email as from_email, to_identity.email as to_email
        FROM
            message m
        JOIN
            identity from_identity ON m."from" = from_identity.id
        JOIN
            identity to_identity ON m."to" = to_identity.id
        WHERE
            m.subject LIKE ? OR m.content LIKE ?
        ORDER BY m.created_at DESC
        """,
        (f"%{query}%", f"%{query}%")
    )
    messages = cursor.fetchall()
    formatted_messages = [
        {
            "id": message[0],
            "subject": message[1],
            "content": message[2],
            "status": message[3],
            "created_at": message[4],
            "from_email": message[5],
            "to_email": message[6]
        }
        for message in messages
    ]
    
    return JSONResponse(formatted_messages)


@app.get("/stats/total-messages")
async def total_messages(request: Request, db: sqlite3.Connection = Depends(get_db)):
    await asyncio.sleep(random.uniform(0, 4))
    session_id = get_cookie(request, 'comms_auth')
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    session, user = validate_session(db, session_id)
    if not session or not user:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    now = datetime.now(pytz.UTC)
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_month_start = (current_month_start - datetime.timedelta(days=1)).replace(day=1)
    
    current_month_start_ts = int(current_month_start.timestamp())
    previous_month_start_ts = int(previous_month_start.timestamp())
    current_month_end_ts = int((current_month_start + datetime.timedelta(days=31)).timestamp())

    try:
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT 
                SUM(CASE WHEN created_at >= ? AND created_at < ? THEN 1 ELSE 0 END) AS current_month,
                SUM(CASE WHEN created_at >= ? AND created_at < ? THEN 1 ELSE 0 END) AS previous_month
            FROM message
            """,
            (current_month_start_ts, current_month_end_ts, previous_month_start_ts, current_month_start_ts)
        )
        result = cursor.fetchone()
        return JSONResponse(content={"currentMonth": result[0], "previousMonth": result[1]})
    
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/stats/total-message-actions")
async def total_message_actions(request: Request, db: sqlite3.Connection = Depends(get_db)):
    session_id = get_cookie(request, 'comms_auth')
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    session, user = validate_session(db, session_id)
    if not session or not user:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    now = datetime.utcnow()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_month_start = (current_month_start - datetime.timedelta(days=1)).replace(day=1)
    
    current_month_start_ts = int(current_month_start.timestamp())
    previous_month_start_ts = int(previous_month_start.timestamp())
    current_month_end_ts = int((current_month_start + datetime.timedelta(days=31)).timestamp())

    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                """
                SELECT
                    SUM(CASE WHEN created_at >= ? AND created_at < ? AND status IS NOT NULL THEN 1 ELSE 0 END) AS current_month,
                    SUM(CASE WHEN created_at >= ? AND created_at < ? AND status IS NOT NULL THEN 1 ELSE 0 END) AS previous_month
                FROM message
                """,
                (current_month_start_ts, current_month_end_ts, previous_month_start_ts, current_month_start_ts)
            )
            result = await cursor.fetchone()
            return JSONResponse(content={"currentMonth": result[0], "previousMonth": result[1]})
    
    except aiosqlite.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)