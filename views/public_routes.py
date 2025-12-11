from flask import (
    Blueprint,
    current_app,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

# 予約データを保存する関数（models/reservation_model.py 側で実装予定）
from models.reservation_model import create_reservation


bp = Blueprint("public", __name__)


def _get_serializer():
    """
    マジックリンク用のトークンを発行・検証するためのシリアライザ。
    SECRET_KEY と salt を使って安全なトークンを生成する。
    """
    secret_key = current_app.config["SECRET_KEY"]
    # salt は任意だが、用途ごとに固定文字列を使うとよい
    return URLSafeTimedSerializer(secret_key, salt="ci-appointment-magic-link")


@bp.route("/")
def index():
    """
    トップページ。
    とりあえずメール入力画面にリダイレクトする。
    """
    return redirect(url_for("public.email_input"))


@bp.route("/reservations/email/", methods=["GET", "POST"])
def email_input():
    """
    患者さんが最初にアクセスする画面：
    メールアドレスを入力し、マジックリンクを送信する。
    """
    if request.method == "POST":
        email = request.form.get("email", "").strip()

        if not email:
            flash("メールアドレスを入力してください。", "error")
            return render_template("email_input.html")

        # トークン生成
        s = _get_serializer()
        token = s.dumps({"email": email})

        # 予約フォームへのマジックリンクを生成
        magic_link = url_for(
            "public.reservation_form",
            token=token,
            _external=True,  # 絶対URL（メールにそのまま記載できる）
        )

        # 本来はここでメール送信を行う。
        # ひとまず開発中はコンソールに出力して動作確認する。
        current_app.logger.info(f"[DEBUG] Magic link for {email}: {magic_link}")

        # TODO: 後でメール送信処理を実装（SMTP や外部サービス利用）

        return render_template("email_sent.html", email=email)

    # GET の場合
    return render_template("email_input.html")


@bp.route("/reservations/form/<token>/", methods=["GET", "POST"])
def reservation_form(token):
    """
    マジックリンクからアクセスされる予約リクエストフォーム。
    トークンからメールアドレスを取り出し、フォーム送信時に DB へ保存する。
    """
    s = _get_serializer()
    try:
        data = s.loads(token, max_age=60 * 60)  # 有効期限 1時間（秒単位）
        email = data.get("email")
    except SignatureExpired:
        # トークンの有効期限切れ
        return render_template("token_invalid.html", reason="expired")
    except BadSignature:
        # 不正なトークン
        return render_template("token_invalid.html", reason="invalid")

    if request.method == "POST":
        # フォームから送信された値を取得
        form = request.form

        reservation_data = {
            "email": email,
            "chart_number": form.get("chart_number", "").strip(),
            "referring_hospital": form.get("referring_hospital", "").strip(),
            "last_name": form.get("last_name", "").strip(),
            "first_name": form.get("first_name", "").strip(),
            "last_name_kana": form.get("last_name_kana", "").strip(),
            "first_name_kana": form.get("first_name_kana", "").strip(),
            "birth_date": form.get("birth_date", "").strip(),
            "sex": form.get("sex", "").strip(),
            "first_choice_date": form.get("first_choice_date", "").strip(),
            "first_choice_time_slot": form.get("first_choice_time_slot", "").strip(),
            "second_choice_date": form.get("second_choice_date", "").strip(),
            "second_choice_time_slot": form.get("second_choice_time_slot", "").strip(),
            "third_choice_date": form.get("third_choice_date", "").strip(),
            "third_choice_time_slot": form.get("third_choice_time_slot", "").strip(),
        }

        # 簡単なバリデーション（必要に応じて強化）
        errors = []
        if not reservation_data["last_name"] or not reservation_data["first_name"]:
            errors.append("お名前（姓・名）を入力してください。")
        if not reservation_data["birth_date"]:
            errors.append("生年月日を入力してください。")
        if not reservation_data["sex"]:
            errors.append("性別を選択してください。")
        if not reservation_data["first_choice_date"]:
            errors.append("第1希望の日付を入力してください。")

        if errors:
            for msg in errors:
                flash(msg, "error")
            # 入力済みの値は reservation_data からテンプレートに渡して再表示する
            return render_template(
                "reservation_form.html",
                email=email,
                form_data=reservation_data,
            )

        # DB へ保存（models/reservation_model.py 側で実装）
        create_reservation(reservation_data)

        # 完了画面へ
        return redirect(url_for("public.reservation_done"))

    # GET の場合：フォーム初期表示
    return render_template("reservation_form.html", email=email, form_data={})


@bp.route("/reservations/done/")
def reservation_done():
    """
    予約リクエスト送信完了画面。
    """
    return render_template("reservation_done.html")