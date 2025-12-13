from flask import Flask
from config import DevelopmentConfig
from dotenv import load_dotenv
from extensions import mail

# モデルの初期化関数（DB 作成）
from models.reservation_model import init_db


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

    # SQLite のファイルは instance/ 配下に置くので、フォルダを作成しておく
    try:
        import os
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # DB 初期化（テーブル作成など）
    init_db(app)

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