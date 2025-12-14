from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    flash,
)

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

        flash("予約情報を更新しました。", "success")
        return redirect(url_for("staff.reservation_detail", reservation_id=reservation_id))

    # GET の場合：詳細画面を表示
    return render_template("staff/reservation_detail.html", reservation=reservation)