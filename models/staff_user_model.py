import sqlite3
from dataclasses import dataclass
from typing import Optional, List

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

# 既存のDB接続（reservationsと同じDBを使い回す）
from models.reservation_model import get_db


# -----------------------------
# テーブル作成（初期化）
# -----------------------------
def init_staff_users_table() -> None:
    """
    staff_users テーブルが無ければ作成する。
    ※ app起動時（create_app内）で1回呼ぶ想定
    """
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS staff_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    db.commit()


# -----------------------------
# Flask-Login 用のユーザークラス
# -----------------------------
@dataclass
class StaffUser(UserMixin):
    """
    Flask-Login が扱いやすい形のユーザーオブジェクト。
    UserMixin により、is_authenticated 等が自動で用意されます。
    """
    id: int
    email: str
    name: str
    is_active: bool = True

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "StaffUser":
        return cls(
            id=row["id"],
            email=row["email"],
            name=row["name"],
            is_active=bool(row["is_active"]),
        )


# -----------------------------
# 取得系（ログインで必須）
# -----------------------------
def get_staff_user_by_id(user_id: int) -> Optional[StaffUser]:
    db = get_db()
    row = db.execute(
        "SELECT id, email, name, is_active FROM staff_users WHERE id = ?;",
        (user_id,),
    ).fetchone()
    if row is None:
        return None
    return StaffUser.from_row(row)


def get_staff_user_by_email(email: str) -> Optional[sqlite3.Row]:
    """
    ログイン時にメールアドレスで検索したいので、Row（password_hash含む）を返す。
    """
    db = get_db()
    row = db.execute(
        """
        SELECT id, email, name, password_hash, is_active
        FROM staff_users
        WHERE email = ?;
        """,
        (email.strip().lower(),),
    ).fetchone()
    return row


def list_staff_users(limit: int = 200) -> List[sqlite3.Row]:
    db = get_db()
    rows = db.execute(
        """
        SELECT id, email, name, is_active, created_at
        FROM staff_users
        ORDER BY created_at DESC
        LIMIT ?;
        """,
        (limit,),
    ).fetchall()
    return rows


# -----------------------------
# 作成・更新系
# -----------------------------
def create_staff_user(email: str, name: str, password: str) -> int:
    """
    職員ユーザーを作成する（パスワードはハッシュ化して保存）。
    戻り値：作成されたユーザーID
    """
    email_norm = email.strip().lower()
    name = name.strip()

    if not email_norm:
        raise ValueError("email is required")
    if not name:
        raise ValueError("name is required")
    if not password:
        raise ValueError("password is required")

    password_hash = generate_password_hash(password)

    db = get_db()
    cur = db.execute(
        """
        INSERT INTO staff_users (email, name, password_hash)
        VALUES (?, ?, ?);
        """,
        (email_norm, name, password_hash),
    )
    db.commit()
    new_id = cur.lastrowid
    if new_id is None:
        raise RuntimeError("Failed to create staff user (lastrowid is None)")
    return int(new_id)


def set_staff_user_active(user_id: int, is_active: bool) -> None:
    db = get_db()
    db.execute(
        "UPDATE staff_users SET is_active = ? WHERE id = ?;",
        (1 if is_active else 0, user_id),
    )
    db.commit()


# -----------------------------
# 認証（ログイン処理で必須）
# -----------------------------
def verify_staff_password(email: str, password: str) -> Optional[StaffUser]:
    """
    email + password で認証する。
    成功：StaffUser を返す
    失敗：None を返す
    """
    row = get_staff_user_by_email(email)
    if row is None:
        return None
    if not bool(row["is_active"]):
        return None

    if check_password_hash(row["password_hash"], password):
        # Flask-Loginに渡す用に StaffUser を作る（password_hashは含めない）
        return StaffUser(
            id=row["id"],
            email=row["email"],
            name=row["name"],
            is_active=bool(row["is_active"]),
        )

    return None