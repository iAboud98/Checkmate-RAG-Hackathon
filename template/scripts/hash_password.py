"""
Create a login entry for AUTH_USERS in .env (the password is hashed, never stored as is).

    python scripts/hash_password.py
Then add the printed entry to AUTH_USERS in .env (comma-separate several users).
"""

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.auth import hash_password  # noqa: E402

name = input("Username: ").strip()
role = input("Role [admin/user]: ").strip() or "user"
password = getpass.getpass("Password: ")
print(f"\nAdd to AUTH_USERS in .env:\n{name}:{role}:{hash_password(password)}")
