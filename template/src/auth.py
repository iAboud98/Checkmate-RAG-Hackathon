"""
Simple login with roles ("admin" can manage documents and see analytics; "user" can chat).

Users live in .env as AUTH_USERS="name:role:hash,name2:role:hash". Passwords are never
stored in plain text: only salted PBKDF2-SHA256 hashes (create one with
`python scripts/hash_password.py`). Comparison is constant-time (hmac.compare_digest).
For a real product: move users to the database and add rate limiting / SSO.
"""

import base64
import hashlib
import hmac
import os

from config import AUTH_USERS

ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2${ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$")
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt), int(iterations))
        return hmac.compare_digest(candidate, base64.b64decode(digest))
    except (ValueError, TypeError):
        return False


def load_users() -> dict[str, dict]:
    users = {}
    for entry in filter(None, (e.strip() for e in AUTH_USERS.split(","))):
        name, role, hashed = entry.split(":", 2)
        users[name] = {"role": role, "hash": hashed}
    return users


def authenticate(username: str, password: str) -> dict | None:
    user = load_users().get(username.strip())
    if user and verify_password(password, user["hash"]):
        return {"username": username.strip(), "role": user["role"]}
    return None
