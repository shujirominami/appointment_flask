from flask import (
    Blueprint,
    current_app,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

from flask_mail import Message
from extensions import mail
from utils.tokens import issue_token, verify_token

# 予約データを保存する関数（models/reservation_model.py 側で実装予定）
from models.reservation_model import create_reservation, get_reservation_by_id


bp = Blueprint("public", __name__)




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
        token = issue_token({"email": email})

        # 予約フォームへのマジックリンクを生成
        magic_link = url_for(
            "public.reservation_form",
            token=token,
            _external=True,  # 絶対URL（メールにそのまま記載できる）
        )

        # --- ここからメール送信 ---
        subject = "【予約フォーム】入力用リンク（有効期限：1時間）"
        body = f"""予約フォームへのリンクです（有効期限：1時間）：
        {magic_link}

        このメールに心当たりがない場合は破棄してください。
        """

        msg = Message(
            subject=subject,
            sender=current_app.config.get("MAIL_FROM"),
            recipients=[email],
            body=body,
        )
        try:
            mail.send(msg)
            current_app.logger.info(f"[MAIL] Sent magic link to {email}")
        except Exception:
            # 送信失敗の詳細はログに出す
            current_app.logger.exception("[MAIL] Failed to send magic link")
            flash("メール送信に失敗しました。しばらくしてから再度お試しください。", "error")
            return render_template("email_input.html")
        # --- ここまでメール送信 ---

        return render_template("email_sent.html", email=email)

    # GET の場合
    return render_template("email_input.html")


@bp.route("/reservations/form/<token>/", methods=["GET", "POST"])
def reservation_form(token):
    """
    マジックリンクからアクセスされる予約リクエストフォーム。
    トークンからメールアドレスを取り出し、フォーム送信時に DB へ保存する。
    """
    data, err = verify_token(token, max_age_seconds=60 * 60)

    if err == "expired":
        return render_template("token_invalid.html", reason="expired")
    if err == "invalid" or data is None:
        return render_template("token_invalid.html", reason="invalid")

    email = data.get("email")
    if not email:
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
        
        # 氏名
        if not reservation_data["last_name"] or not reservation_data["first_name"]:
            errors.append("お名前（姓・名）を入力してください。")
            
        # 生年月日・性別
        if not reservation_data["birth_date"]:
            errors.append("生年月日を入力してください。")
        if not reservation_data["sex"]:
            errors.append("性別を選択してください。")
            
        # 第1希望（必須：日付＋スロット）
        if not reservation_data["first_choice_date"]:
            errors.append("第1希望の日付を入力してください。")
        if not reservation_data["first_choice_time_slot"]:
            errors.append("第1希望の時間帯を選択してください。")

        # 第2希望（任意だが、日付とスロットはセット）
        if reservation_data["second_choice_date"] and not reservation_data["second_choice_time_slot"]:
            errors.append("第2希望は日付を入れた場合、時間帯も選択してください。")
        if reservation_data["second_choice_time_slot"] and not reservation_data["second_choice_date"]:
            errors.append("第2希望は時間帯を選んだ場合、日付も入力してください。")
        # 第3希望（任意だが、日付とスロットはセット）
        if reservation_data["third_choice_date"] and not reservation_data["third_choice_time_slot"]:
            errors.append("第3希望は日付を入れた場合、時間帯も選択してください。")
        if reservation_data["third_choice_time_slot"] and not reservation_data["third_choice_date"]:
            errors.append("第3希望は時間帯を選んだ場合、日付も入力してください。")
            

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

@bp.route("/reservations/reschedule/<token>/", methods=["GET", "POST"])
def reschedule(token: str):
    # 1) token検証（48時間）
    data, err = verify_token(token, max_age_seconds=48 * 60 * 60)

    if err == "expired":
        return render_template("token_invalid.html", reason="expired")
    if err == "invalid" or data is None:
        return render_template("token_invalid.html", reason="invalid")

    # token には email と reservation_id が入っている想定
    email_from_token = data.get("email")
    reservation_id = data.get("reservation_id")

    if not email_from_token or reservation_id is None:
        return render_template("token_invalid.html", reason="invalid")

    try:
        reservation_id = int(reservation_id)
    except (TypeError, ValueError):
        return render_template("token_invalid.html", reason="invalid")

    # 2) DBから予約データ取得
    reservation = get_reservation_by_id(reservation_id)
    if reservation is None:
        flash("対象の予約が見つかりません。", "error")
        return redirect(url_for("public.email_input"))

    # 3) セキュリティ：tokenのemail と DBのemail が一致するか確認
    if reservation["email"] != email_from_token:
        return render_template("token_invalid.html", reason="invalid")

    # 4) POST：再入力された希望日程を処理
    if request.method == "POST":
        form = request.form

        # 希望日程だけ取り直す（患者基本情報はDBの値を優先して固定するのが安全）
        first_choice_date = form.get("first_choice_date", "").strip()
        first_choice_time_slot = form.get("first_choice_time_slot", "").strip()
        second_choice_date = form.get("second_choice_date", "").strip()
        second_choice_time_slot = form.get("second_choice_time_slot", "").strip()
        third_choice_date = form.get("third_choice_date", "").strip()
        third_choice_time_slot = form.get("third_choice_time_slot", "").strip()

        # バリデーション（最低限）
        errors = []
        if not first_choice_date:
            errors.append("第1希望の日付を入力してください。")
        if not first_choice_time_slot:
            errors.append("第1希望の時間帯を選択してください。")

        if second_choice_date and not second_choice_time_slot:
            errors.append("第2希望は日付を入れた場合、時間帯も選択してください。")
        if second_choice_time_slot and not second_choice_date:
            errors.append("第2希望は時間帯を選んだ場合、日付も入力してください。")

        if third_choice_date and not third_choice_time_slot:
            errors.append("第3希望は日付を入れた場合、時間帯も選択してください。")
        if third_choice_time_slot and not third_choice_date:
            errors.append("第3希望は時間帯を選んだ場合、日付も入力してください。")

        if errors:
            for m in errors:
                flash(m, "error")

            # 再表示のために form_data を作って返す（下のGETと同じ構造）
            form_data = {
                "referring_hospital": reservation["referring_hospital"] or "",
                "last_name": reservation["last_name"] or "",
                "first_name": reservation["first_name"] or "",
                "last_name_kana": reservation["last_name_kana"] or "",
                "first_name_kana": reservation["first_name_kana"] or "",
                "birth_date": reservation["birth_date"] or "",
                "sex": reservation["sex"] or "",

                "first_choice_date": first_choice_date,
                "first_choice_time_slot": first_choice_time_slot,
                "second_choice_date": second_choice_date,
                "second_choice_time_slot": second_choice_time_slot,
                "third_choice_date": third_choice_date,
                "third_choice_time_slot": third_choice_time_slot,
            }
            return render_template(
                "reservation_form.html",
                email=reservation["email"],
                form_data=form_data,
                mode="reschedule",
            )

        # ここから先は「DBへ反映」：おすすめは同一レコード更新
        # → ステップ3で reservation_model.py に更新関数を追加します
        from models.reservation_model import update_reservation_choices
        update_reservation_choices(
            reservation_id=reservation_id,
            first_choice_date=first_choice_date,
            first_choice_time_slot=first_choice_time_slot,
            second_choice_date=second_choice_date or None,
            second_choice_time_slot=second_choice_time_slot or None,
            third_choice_date=third_choice_date or None,
            third_choice_time_slot=third_choice_time_slot or None,
        )

        flash("再入力を受け付けました。スタッフが確認します。", "success")
        return redirect(url_for("public.reservation_done"))

    # 5) GET：フォーム初期値（患者情報を入力済みにする）
    form_data = {
        "chart_number": reservation["chart_number"] or "",
        "referring_hospital": reservation["referring_hospital"] or "",
        "last_name": reservation["last_name"] or "",
        "first_name": reservation["first_name"] or "",
        "last_name_kana": reservation["last_name_kana"] or "",
        "first_name_kana": reservation["first_name_kana"] or "",
        "birth_date": reservation["birth_date"] or "",
        "sex": reservation["sex"] or "",

        # 日程は空にして再入力させる（前回値を出したいなら reservationの値を入れる）
        "first_choice_date": "",
        "first_choice_time_slot": "",
        "second_choice_date": "",
        "second_choice_time_slot": "",
        "third_choice_date": "",
        "third_choice_time_slot": "",
    }

    return render_template(
        "reservation_form.html",
        email=reservation["email"],
        form_data=form_data,
        mode="reschedule",
    )