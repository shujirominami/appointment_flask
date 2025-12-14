import sqlite3
from typing import Dict, Any, List, Optional

from flask import current_app, g


# --------------------------------------
# DB接続まわり
# --------------------------------------

def get_db() -> sqlite3.Connection:
    """
    リクエストごとに1つのDBコネクションを使い回す。
    Flaskのgオブジェクトに保持する。
    """
    if "db" not in g:
        db_path = current_app.config["DATABASE"]
        # config.DATABASE が Path の場合に備えて str() で文字列に
        g.db = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row  # 辞書のように扱える行オブジェクト
    return g.db


def close_db(e: Optional[BaseException] = None) -> None:
    """
    リクエスト終了時にコネクションをクローズする。
    app.teardown_appcontext から呼ばれる前提。
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()


# --------------------------------------
# 初期化（テーブル作成）
# --------------------------------------

def init_db(app) -> None:
    """
    アプリ起動時に呼び出される初期化関数。
    reservations テーブルがなければ作成する。
    """
    app.teardown_appcontext(close_db)

    with app.app_context():
        db = get_db()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                -- 患者側入力
                email TEXT NOT NULL,
                chart_number TEXT,                -- 診察券番号（任意）
                referring_hospital TEXT,          -- 紹介元医療機関
                last_name TEXT,
                first_name TEXT,
                last_name_kana TEXT,
                first_name_kana TEXT,
                birth_date TEXT,                  -- YYYY-MM-DD などの文字列として扱う
                sex TEXT,                         -- 'M', 'F', 'O' など

                first_choice_date TEXT,
                first_choice_time_slot TEXT,
                second_choice_date TEXT,
                second_choice_time_slot TEXT,
                third_choice_date TEXT,
                third_choice_time_slot TEXT,

                -- 職員側で利用する項目
                status TEXT DEFAULT 'pending',    -- 'pending', 'confirmed', 'need_reschedule', 'cancelled' など
                confirmed_datetime TEXT,          -- 確定した診察日時
                staff_note TEXT,                  -- 職員メモ（再調整理由など）
                handled_by TEXT,                  -- 対応した職員ID/名前

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        db.commit()


# --------------------------------------
# 予約作成（患者側）
# --------------------------------------

def create_reservation(data: Dict[str, Any]) -> int:
    """
    患者側フォームから送信された予約リクエストをDBに保存する。
    戻り値として作成された予約IDを返す。
    """
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO reservations (
            email,
            chart_number,
            referring_hospital,
            last_name,
            first_name,
            last_name_kana,
            first_name_kana,
            birth_date,
            sex,
            first_choice_date,
            first_choice_time_slot,
            second_choice_date,
            second_choice_time_slot,
            third_choice_date,
            third_choice_time_slot,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.get("email"),
            data.get("chart_number"),
            data.get("referring_hospital"),
            data.get("last_name"),
            data.get("first_name"),
            data.get("last_name_kana"),
            data.get("first_name_kana"),
            data.get("birth_date"),
            data.get("sex"),
            data.get("first_choice_date"),
            data.get("first_choice_time_slot"),
            data.get("second_choice_date"),
            data.get("second_choice_time_slot"),
            data.get("third_choice_date"),
            data.get("third_choice_time_slot"),
            "pending",  # 新規は常に pending から開始
        ),
    )
    db.commit()
    return cursor.lastrowid


# --------------------------------------
# 職員側で使う取得系
# --------------------------------------

def get_pending_reservations() -> List[sqlite3.Row]:
    """
    未処理（pending）の予約リクエストを受付順に取得。
    職員側ダッシュボード（一覧表示）で使用する想定。
    """
    db = get_db()
    rows = db.execute(
        """
        SELECT
            id,
            email,
            last_name,
            first_name,
            referring_hospital,
            first_choice_date,
            first_choice_time_slot,
            created_at,
            status
        FROM reservations
        WHERE status = 'pending'
        ORDER BY created_at ASC;
        """
    ).fetchall()
    return rows


def get_reservation_by_id(reservation_id: int) -> Optional[sqlite3.Row]:
    """
    予約IDから単一の予約レコードを取得。
    職員側の詳細画面で使用する。
    """
    db = get_db()
    row = db.execute(
        """
        SELECT *
        FROM reservations
        WHERE id = ?;
        """,
        (reservation_id,),
    ).fetchone()
    return row


def get_all_reservations(limit: int = 100) -> List[sqlite3.Row]:
    """
    予約一覧を新しい順に取得。
    ステータスを問わず最近100件などを確認したい場合に利用。
    """
    db = get_db()
    rows = db.execute(
        """
        SELECT
            id,
            email,
            last_name,
            first_name,
            referring_hospital,
            first_choice_date,
            first_choice_time_slot,
            status,
            confirmed_datetime,
            handled_by,
            created_at,
            updated_at
        FROM reservations
        ORDER BY created_at DESC
        LIMIT ?;
        """,
        (limit,),
    ).fetchall()
    return rows


# --------------------------------------
# 職員側で使う更新系
# --------------------------------------

def update_reservation_choices(
    reservation_id: int,
    first_choice_date: str,
    first_choice_time_slot: str,
    second_choice_date: Optional[str] = None,
    second_choice_time_slot: Optional[str] = None,
    third_choice_date: Optional[str] = None,
    third_choice_time_slot: Optional[str] = None,
) -> None:
    """
    予約の「希望日程」だけを更新する関数。
    再調整（再入力）時に使う想定で、status を pending に戻す。
    """
    db = get_db()
    db.execute(
        """
        UPDATE reservations
        SET
            first_choice_date = ?,
            first_choice_time_slot = ?,
            second_choice_date = ?,
            second_choice_time_slot = ?,
            third_choice_date = ?,
            third_choice_time_slot = ?,
            status = 'pending',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?;
        """,
        (
            first_choice_date,
            first_choice_time_slot,
            second_choice_date,
            second_choice_time_slot,
            third_choice_date,
            third_choice_time_slot,
            reservation_id,
        ),
    )
    db.commit()


def update_reservation_status(
    reservation_id: int,
    status: str,
    confirmed_datetime: Optional[str] = None,
    staff_note: Optional[str] = None,
    handled_by: Optional[str] = None,
) -> None:
    """
    予約のステータスや確定日時、職員メモなどを更新する。
    職員用画面から「予約確定」「再調整」「キャンセル」などを操作する際に利用。
    """
    db = get_db()
    db.execute(
        """
        UPDATE reservations
        SET
            status = ?,
            confirmed_datetime = ?,
            staff_note = ?,
            handled_by = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?;
        """,
        (status, confirmed_datetime, staff_note, handled_by, reservation_id),
    )
    db.commit()