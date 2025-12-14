# scripts/create_staff_user.py
import sys
from pathlib import Path

# プロジェクトルート（appointment_flask）を sys.path に追加
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

import getpass

from app import create_app
from models.staff_user_model import create_staff_user
from models.staff_user_model import get_staff_user_by_email
from models.reservation_model import init_db
from models.staff_user_model import init_staff_users_table

def main():
    app = create_app()
    with app.app_context():
        # 念のため初期化（既にあれば何もしません）
        init_db(app)
        init_staff_users_table()

        email = input("Email: ").strip().lower()
        name = input("Name: ").strip()
        password = getpass.getpass("Password: ")
        
        # 正規化（全角スペース→半角スペース、前後空白除去）
        email = email.replace("　", " ").strip().lower()
        name = name.replace("　", " ").strip()
        
        while not email:
            print("Emailが空です。もう一度入力してください。")
            email = input("Email: ").replace("　", " ").strip().lower()

        while not name:
            print("Nameが空です。もう一度入力してください。")
            name = input("Name: ").replace("　", " ").strip()

        while not password:
            print("Passwordが空です。もう一度入力してください。")
            password = getpass.getpass("Password: ")

        # 既存チェック（重複防止）
        if get_staff_user_by_email(email) is not None:
            print("That email already exists.")
            return

        try:
            user_id = create_staff_user(email=email, name=name, password=password)
        except Exception as e:
            print(f"[ERROR] Failed to create staff user: {e}")
            return

        print(f"Created staff user id={user_id}")

if __name__ == "__main__":
    main()