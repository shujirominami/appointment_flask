import os
from pathlib import Path

# プロジェクトのルートディレクトリ（appointment_flask/）を基準にする
BASE_DIR = Path(__file__).resolve().parent

# SQLite を置く instance/ ディレクトリ
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)  # ディレクトリがなければ作成

# -------------------------
# 環境変数ヘルパー（初心者向け）
# -------------------------
def env_str(key: str, default: str | None = None) -> str | None:
    """環境変数を文字列として取得（無ければdefault）"""
    return os.environ.get(key, default)

def env_bool(key: str, default: bool = False) -> bool:
    """環境変数を真偽値として取得（true/1/yes/on などを True）"""
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "y", "on")

def env_int(key: str, default: int) -> int:
    """環境変数を整数として取得（無ければdefault）"""
    val = os.environ.get(key)
    return int(val) if val is not None else default

class Config:
    """
    全ての環境（開発・本番）で共通の基本設定。
    開発用・本番用のクラスはこれを継承して使います。
    """

    # セッション・CSRF 保護に使うキー
    # 本番では必ず環境変数 SECRET_KEY を設定してください。
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-dev-secret-key")

    # DB: 環境変数 DATABASE があればそれを優先、無ければ instance/appointment.db
    DATABASE = env_str("DATABASE", str(INSTANCE_DIR / "appointment.db"))

    # メール設定（Xserver SMTP想定）
    MAIL_SERVER = env_str("MAIL_SERVER")
    MAIL_PORT = env_int("MAIL_PORT", 465)
    MAIL_USE_SSL = env_bool("MAIL_USE_SSL", True)
    MAIL_USE_TLS = env_bool("MAIL_USE_TLS", False)
    MAIL_USERNAME = env_str("MAIL_USERNAME")
    MAIL_PASSWORD = env_str("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = env_str("MAIL_DEFAULT_SENDER", MAIL_USERNAME)
    
    MAIL_SUPPRESS_SEND = env_bool("MAIL_SUPPRESS_SEND", False)

    # メールに載せるリンクのベースURL（本番は Render のURL）
    APP_BASE_URL = env_str("APP_BASE_URL", "http://127.0.0.1:5000")


class DevelopmentConfig(Config):
    """
    開発環境用設定。
    ローカルPC上での動作確認・デバッグ用。
    """

    DEBUG = True
    TESTING = False
    MAIL_SUPPRESS_SEND = False  # 本当に送る場合


class ProductionConfig(Config):
    """
    本番環境用設定。
    外部からアクセスされるサーバーで使う想定。
    """

    DEBUG = False
    TESTING = False

    @classmethod
    def validate(cls):
        """
        本番起動時に必須環境変数が揃っているかチェック
        """
        if "SECRET_KEY" not in os.environ:
            raise RuntimeError(
                "SECRET_KEY is not set. "
                "Please define it as an environment variable."
            )