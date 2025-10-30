from fastapi import FastAPI, UploadFile, File, HTTPException
import os, shutil
from db_connection import get_connection
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:5173",  # React local dev
    "http://127.0.0.1:5173",  # Sometimes used by Vite
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          
    allow_credentials=True,
    allow_methods=["*"],            
    allow_headers=["*"],            
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# --- Create table if not exists ---
def init_db():
    conn = get_connection()
    print("Connection object:", conn)
    if not conn:
        print("❌ Could not initialize database: connection failed.")
        return
    
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255),
            filepath VARCHAR(255),
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    conn.close()
    print("✅ Table 'files' is ready in Neon PostgreSQL!")


# Initialize DB when app starts
init_db()


# Allowed extensions
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "txt", "docx"}
MAX_FILE_SIZE = 500 * 1024  # 500 KB


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # --- 1. Check if file type allowed ---
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="❌ File type not allowed. Allowed: pdf, png, jpg, txt, docx")

    # --- 2. Check file size ---
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="❌ File too large. Must be under 500 KB")

    # Reset file pointer after reading
    file.file.seek(0)

    # --- 3. Save file locally ---
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # --- 4. Save file info to DB ---
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO files (filename, filepath) VALUES (%s, %s)",
        (file.filename, file_location)
    )
    conn.commit()
    conn.close()

    return {"message": f"✅ File '{file.filename}' uploaded successfully!"}


# --- Get All Files ---
@app.get("/files")
def get_all_files():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, filepath, uploaded_at FROM files ORDER BY uploaded_at DESC")
    rows = cursor.fetchall()
    conn.close()

    files = [
        {"id": row[0], "filename": row[1], "filepath": row[2], "uploaded_at": str(row[3])}
        for row in rows
    ]
    return files


# --- Get File by ID ---
@app.get("/files/{file_id}")
def get_file(file_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, filepath, uploaded_at FROM files WHERE id = %s", (file_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="File not found")

    return {"id": row[0], "filename": row[1], "filepath": row[2], "uploaded_at": str(row[3])}


# --- Delete File by ID ---
@app.delete("/files/{file_id}")
def delete_file(file_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT filepath FROM files WHERE id = %s", (file_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="File not found")

    file_path = row[0]

    # Delete file from local storage
    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete from DB
    cursor.execute("DELETE FROM files WHERE id = %s", (file_id,))
    conn.commit()
    conn.close()

    return {"message": f"🗑️ File ID {file_id} deleted successfully"}



@app.get("/files")
def get_files():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename FROM files ORDER BY uploaded_at DESC")
    rows = cursor.fetchall()
    conn.close()

    files = [{"id": row[0], "filename": row[1]} for row in rows]
    return JSONResponse(content=files)


@app.delete("/files/{file_id}")
def delete_file(file_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    # Get file path
    cursor.execute("SELECT filepath FROM files WHERE id=%s", (file_id,))
    result = cursor.fetchone()
    if not result:
        return {"error": "File not found"}

    filepath = result[0]

    # Delete from DB
    cursor.execute("DELETE FROM files WHERE id=%s", (file_id,))
    conn.commit()
    conn.close()

    # Delete from disk
    if os.path.exists(filepath):
        os.remove(filepath)

    return {"message": "File deleted successfully!"}
