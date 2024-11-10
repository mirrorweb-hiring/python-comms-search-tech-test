from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
import sqlite3
from typing import Optional
from auth import validate_session, create_session, delete_session, verify_password
import time
import uvicorn
import asyncio
import random

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

    try:
        login_request = LoginRequest.model_validate(data)
    except ValidationError:
        raise HTTPException(status_code=400, detail="Bad Request")

    cursor = db.cursor()
    cursor.execute("SELECT * FROM user WHERE email = ?", (login_request.email,))
    user = cursor.fetchone()

    if not user or not verify_password(user[3], login_request.password):
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
async def get_messages(request: Request, db: sqlite3.Connection = Depends(get_db)):
    session_id = get_cookie(request, 'comms_auth')
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    session, user = validate_session(db, session_id)
    if not session or not user:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    order = request.query_params.get("order", "asc")

    try:
        page_size = int(request.query_params.get("page_size", 10))
        page = int(request.query_params.get("page", 1))
    except ValueError:
        raise HTTPException(status_code=400, detail="page and page_numbers should be integers.")


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
        ORDER BY m.created_at {order.upper()}
        LIMIT {page_size}
        OFFSET {(page-1)*page_size}
        """
    )
    messages = cursor.fetchall()

    if page > 1 and len(messages) == 0:
        raise HTTPException(status_code=400, detail="page is out of range")

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
    return JSONResponse(content={"message": "Message updated"})

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
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) as total FROM message
        WHERE created_at >= ? AND created_at < ?
        """,
        (int(time.mktime(time.strptime("2024-06-01", "%Y-%m-%d"))), int(time.mktime(time.strptime("2024-07-01", "%Y-%m-%d"))))
    )
    current_month = cursor.fetchone()
    cursor.execute(
        """
        SELECT COUNT(*) as total FROM message
        WHERE created_at >= ? AND created_at < ?
        """,
        (int(time.mktime(time.strptime("2024-05-01", "%Y-%m-%d"))), int(time.mktime(time.strptime("2024-06-01", "%Y-%m-%d"))))
    )
    previous_month = cursor.fetchone()
    return JSONResponse(content={"currentMonth": current_month[0], "previousMonth": previous_month[0]})

@app.get("/stats/total-message-actions")
async def total_message_actions(request: Request, db: sqlite3.Connection = Depends(get_db)):
    session_id = get_cookie(request, 'comms_auth')
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    session, user = validate_session(db, session_id)
    if not session or not user:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) as total FROM message
        WHERE created_at >= ? AND created_at < ? AND status IS NOT NULL
        """,
        (int(time.mktime(time.strptime("2024-06-01", "%Y-%m-%d"))), int(time.mktime(time.strptime("2024-07-01", "%Y-%m-%d"))))
    )
    current_month = cursor.fetchone()
    cursor.execute(
        """
        SELECT COUNT(*) as total FROM message
        WHERE created_at >= ? AND created_at < ? AND status IS NOT NULL
        """,
        (int(time.mktime(time.strptime("2024-05-01", "%Y-%m-%d"))), int(time.mktime(time.strptime("2024-06-01", "%Y-%m-%d"))))
    )
    previous_month = cursor.fetchone()
    return JSONResponse(content={"currentMonth": current_month[0], "previousMonth": previous_month[0]})

if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8080, reload=True)