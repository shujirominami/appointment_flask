from flask import Flask
from config import DevelopmentConfig
from dotenv import load_dotenv
from extensions import mail, login_manager

# モデルの初期化関数（DB 作成）
from models.reservation_model import init_db
from models.staff_user_model import init_staff_users_table, get_staff_user_by_id

def create_app(config_class=DevelopmentConfig):
    """
    Flask アプリケーションのファクトリ関数。
    開発用・本番用どちらでも config_class を渡して使える。
    """
    app = Flask(__name__, instance_relative_config=True)
    # .env を読み込む
    load_dotenv()

    # 設定ファイルを読み込む
    app.config.from_object(config_class)
    
    # Flask-Mail 初期化（設定が入った後）
    mail.init_app(app)
    
    # Flask-Login 初期化
    login_manager.init_app(app)

    # 未ログイン時に飛ばす先（職員ログイン画面のエンドポイント名）
    login_manager.login_view = "staff.login"
    login_manager.login_message = "職員ログインが必要です。"
    login_manager.login_message_category = "error"
    
    @login_manager.user_loader
    def load_user(user_id: str):
    # Flask-Login は user_id を文字列で渡すので int に変換
        try:
            return get_staff_user_by_id(int(user_id))
        except (ValueError, TypeError):
            return None
        
    # ✅ ここに追加（health check）
    @app.get("/healthz")
    def healthz():
        return "ok", 200    
        
    # SQLite のファイルは instance/ 配下に置くので、フォルダを作成しておく
    try:
        import os
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # DB 初期化（テーブル作成など）
    init_db(app)
    
    # 職員ユーザー用テーブル作成（staff_users）
    with app.app_context():        #（current_app を使える状態にする）
        init_staff_users_table()

    # Blueprints（ルーティング）を登録
    from views.public_routes import bp as public_bp
    app.register_blueprint(public_bp)

    from views.staff_routes import bp as staff_bp
    app.register_blueprint(staff_bp, url_prefix="/staff")

    return app


if __name__ == "__main__":
    # ローカル実行時：DevelopmentConfig で起動
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)