"""SQLite 기반 사용자 DB"""
import sqlite3, hashlib
from pathlib import Path

DB_PATH = Path(__file__).parent / "users.db"

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    """테이블 생성 + 테스트 계정"""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            pw_hash TEXT NOT NULL,
            nickname TEXT,
            birth_year INTEGER, birth_month INTEGER,
            birth_day INTEGER, birth_hour INTEGER,
            gender TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            top1_region TEXT, top1_country TEXT, top1_score REAL,
            final_vec TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    # 테스트 계정
    try:
        conn.execute("INSERT INTO users(username,pw_hash,nickname) VALUES(?,?,?)",
                     ("starplace", _hash("star1234"), "테스트유저"))
        conn.commit()
    except Exception:
        pass
    conn.close()

def register(username, pw, nickname):
    conn = get_db()
    try:
        conn.execute("INSERT INTO users(username,pw_hash,nickname) VALUES(?,?,?)",
                     (username, _hash(pw), nickname or username))
        conn.commit()
        conn.close()
        return True, "가입 완료!"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "이미 사용 중인 아이디입니다."

def login(username, pw):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE username=? AND pw_hash=?",
        (username, _hash(pw))).fetchone()
    conn.close()
    return dict(row) if row else None

def get_user(username):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None

def save_birth(user_id, y, m, d, h, g):
    conn = get_db()
    conn.execute("UPDATE users SET birth_year=?,birth_month=?,birth_day=?,birth_hour=?,gender=? WHERE id=?",
                 (y, m, d, h, g, user_id))
    conn.commit()
    conn.close()

def save_result(user_id, region, country, score, vec_json):
    conn = get_db()
    conn.execute("INSERT INTO results(user_id,top1_region,top1_country,top1_score,final_vec) VALUES(?,?,?,?,?)",
                 (user_id, region, country, score, vec_json))
    conn.commit()
    conn.close()

def get_my_result(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM results WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
        (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
