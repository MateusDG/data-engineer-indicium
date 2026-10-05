"""Local dashboard sessions: HMAC-signed, short-lived, HTTP-only cookies."""
import base64
import hashlib
import hmac
import os
import secrets
import time

COOKIE = 'banvic_session'
SESSION_SECONDS = 8*60*60


def valid_login(username,password):
    user_ok = secrets.compare_digest(username.encode(),os.environ.get('DASHBOARD_USER','comercial').encode())
    password_ok = secrets.compare_digest(password.encode(),os.environ['DASHBOARD_PASSWORD'].encode())
    return user_ok and password_ok


def sign(value):
    return hmac.new(os.environ['DASHBOARD_SESSION_KEY'].encode(),value.encode(),hashlib.sha256).hexdigest()


def create_session():
    value = f'{int(time.time())+SESSION_SECONDS}:{secrets.token_hex(16)}'
    return base64.urlsafe_b64encode((value+':'+sign(value)).encode()).decode()


def validate_session(token):
    try:
        if len(token)>256:
            return False
        value,signature = base64.urlsafe_b64decode(token.encode()).decode().rsplit(':',1)
        expiry,nonce = value.split(':')
        current = int(time.time())
        return hmac.compare_digest(signature,sign(value)) and current<int(expiry)<=current+SESSION_SECONDS and len(nonce)==32
    except (ValueError,TypeError,UnicodeError):
        return False
