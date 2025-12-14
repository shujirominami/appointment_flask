# utils/tokens.py
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from flask import current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

DEFAULT_SALT = "ci-appointment-magic-link"


def _serializer(salt: str = DEFAULT_SALT) -> URLSafeTimedSerializer:
    secret_key = current_app.config["SECRET_KEY"]
    return URLSafeTimedSerializer(secret_key, salt=salt)


def issue_token(payload: Dict[str, Any], *, salt: str = DEFAULT_SALT) -> str:
    """
    payload（例：{"email": "...", "reservation_id": 1, "purpose": "reschedule"}）を
    改ざんできないトークン文字列にして返す。
    """
    s = _serializer(salt=salt)
    return s.dumps(payload)


def verify_token(
    token: str,
    *,
    max_age_seconds: int,
    salt: str = DEFAULT_SALT
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    tokenを検証してpayloadを返す。
    戻り値:
      (payload, None)  … OK
      (None, "expired")… 期限切れ
      (None, "invalid")… 不正
    """
    s = _serializer(salt=salt)
    try:
        data = s.loads(token, max_age=max_age_seconds)
        if not isinstance(data, dict):
            return None, "invalid"
        return data, None
    except SignatureExpired:
        return None, "expired"
    except BadSignature:
        return None, "invalid"