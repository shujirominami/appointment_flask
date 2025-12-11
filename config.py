import os
from pathlib import Path

# プロジェクトのルートディレクトリ（appointment_flask/）を基準にする
BASE_DIR = Path(__file__).resolve().parent

# SQLite を置く instance/ ディレクトリ
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)  # ディレクトリがなければ作成


class Config:
    """
    全ての環境（開発・本番）で共通の基本設定。
    開発用・本番用のクラスはこれを継承して使います。
    """

    # セッション・CSRF 保護に使うキー
    # 本番では必ず環境変数 SECRET_KEY を設定してください。
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-dev-secret-key")

    # SQLite のファイルパス（例：appointment_flask/instance/appointment.db）
    DATABASE = INSTANCE_DIR / "appointment.db"

    # 後でメール送信などを追加する場合は、ここに共通設定を書く：
    # MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    # MAIL_PORT = int(os.environ.get("MAIL_PORT", 25))


class DevelopmentConfig(Config):
    """
    開発環境用設定。
    ローカルPC上での動作確認・デバッグ用。
    """

    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """
    本番環境用設定。
    外部からアクセスされるサーバーで使う想定。
    """

    DEBUG = False
    TESTING = False

    # 本番では SECRET_KEY は必須（未設定なら起動時にエラーにする）
    SECRET_KEY = os.environ["SECRET_KEY"]