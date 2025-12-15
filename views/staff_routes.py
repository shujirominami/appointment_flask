from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    flash,
)
from flask import current_app
from flask_mail import Message
from extensions import mail
from utils.tokens import issue_token
from flask_login import login_user, logout_user, login_required, current_user
from models.staff_user_model import verify_staff_password

from models.reservation_model import (
    get_pending_reservations,
    get_all_reservations,
    get_reservation_by_id,
    update_reservation_status,
)

bp = Blueprint("staff", __name__)

@bp.route("/login/", methods=["GET", "POST"])
def login():
    # すでにログインしているなら staffトップへ
    if current_user.is_authenticated:
        return redirect(url_for("staff.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = verify_staff_password(email, password)
        if user is None:
            flash("メールアドレスまたはパスワードが正しくありません。", "error")
            return render_template("staff/login.html", email=email)

        # ログイン成功：セッションにユーザー情報が保存される
        login_user(user)

        flash("ログインしました。", "success")

        # ログイン後に元のページへ戻したい場合は next を使う
        next_url = request.args.get("next")
        return redirect(next_url or url_for("staff.index"))

    # GET：ログイン画面表示
    return render_template("staff/login.html", email="")

@bp.route("/logout/")
@login_required
def logout():
    logout_user()
    flash("ログアウトしました。", "success")
    return redirect(url_for("staff.login"))

@bp.route("/")
def index():
    """
    /staff/ にアクセスされたら、予約一覧（ダッシュボード）へリダイレクト。
    """
    return redirect(url_for("staff.reservation_list"))


@bp.route("/reservations/")
@login_required
def reservation_list():
    """
    職員用ダッシュボード：
    - 未処理（pending）の予約一覧
    - 最近の予約一覧（全ステータス）を表示する想定
    """
    pending = get_pending_reservations()
    recent = get_all_reservations(limit=50)  # 必要に応じて件数調整

    return render_template(
        "staff/dashboard.html",
        pending_reservations=pending,
        recent_reservations=recent,
    )


@bp.route("/reservations/<int:reservation_id>/", methods=["GET", "POST"])
@login_required
def reservation_detail(reservation_id: int):
    """
    個別予約の詳細画面：
    - GET：予約内容を表示
    - POST：ステータス更新（確定・再調整・キャンセル等）
    """
    reservation = get_reservation_by_id(reservation_id)
    if reservation is None:
        flash("指定された予約が見つかりません。", "error")
        return redirect(url_for("staff.reservation_list"))
    
    before_status = reservation["status"]

    if request.method == "POST":
        # フォームからの値を取得
        status = request.form.get("status", "").strip()  # 'confirmed', 'need_reschedule', 'cancelled' など
        confirmed_datetime = request.form.get("confirmed_datetime", "").strip()
        staff_note = request.form.get("staff_note", "").strip()
        handled_by = request.form.get("handled_by", "").strip()

        if not status:
            flash("ステータスを選択してください。", "error")
            return render_template("staff/reservation_detail.html", reservation=reservation)

        # 予約ステータスの更新
        update_reservation_status(
            reservation_id=reservation_id,
            status=status,
            confirmed_datetime=confirmed_datetime or None,
            staff_note=staff_note or None,
            handled_by=handled_by or None,
        )
        
        # --- ここから：確定メール送信（confirmedに変わった時だけ） ---
        if before_status != "confirmed" and status == "confirmed" and confirmed_datetime:
            updated = get_reservation_by_id(reservation_id)
            if updated is not None:
                to_email = updated["email"]

                subject = "【人工内耳センター】ご予約日時が確定しました"
                body = f"""ご予約日時が確定しました。

【確定日時】
{confirmed_datetime}

【ご注意】
本メールにお心当たりがない場合は破棄してください。
"""
                sender = current_app.config.get("MAIL_FROM")
                msg = Message(
                    subject=subject,
                    recipients=[to_email],
                    body=body,
                    sender=sender,
                )

                try:
                    mail.send(msg)
                    current_app.logger.info(f"[MAIL] Sent confirmation mail to {to_email}")
                except Exception:
                    current_app.logger.exception("[MAIL] Failed to send confirmation mail")
                    flash("予約は更新しましたが、確定メールの送信に失敗しました。", "error")
        # --- ここまで：確定メール送信 ---
        
        # 再調整なら再入力リンクを送る
        if status == "need_reschedule":
            patient_email = reservation["email"]

            # 再入力リンク用トークン（email + reservation_id を入れておくと後で追跡しやすい）
            reschedule_token = issue_token({
                "email": patient_email,
                "reservation_id": reservation_id,
            })

            reschedule_link = url_for(
                "public.reschedule",
                token=reschedule_token,
                _external=True,
            )

            subject = "【人工内耳センター】予約日程の再入力のお願い"
            body = f"""ご入力いただいた候補日程では調整が難しいため、恐れ入りますが再度ご希望日程をご入力ください。

再入力用リンク（有効期限：48時間）：
{reschedule_link}

このメールに心当たりがない場合は破棄してください。
"""

            msg = Message(
                subject=subject,
                sender=current_app.config.get("MAIL_FROM"),
                recipients=[patient_email],
                body=body,
            )

            try:
                mail.send(msg)
            except Exception:
                current_app.logger.exception("[MAIL] Failed to send reschedule link")
                flash("再入力依頼メールの送信に失敗しました（ログを確認してください）。", "error")
                # ここでreturnしない（DB更新は成功しているため）

    # GET の場合：詳細画面を表示
    return render_template("staff/reservation_detail.html", reservation=reservation)