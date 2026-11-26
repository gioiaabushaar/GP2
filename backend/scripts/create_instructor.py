import sys
from pathlib import Path
from getpass import getpass

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.db import SessionLocal, engine
from app.core.models import User
from app.core.security import hash_password
from getpass import getpass

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.db import SessionLocal, engine
from app.core.models import User
from app.core.security import hash_password


def main():
    if engine.dialect.name != "postgresql":
        raise SystemExit("PostgreSQL is required.")
    if (
        engine.url.database != "nexis_db"
        or engine.url.host not in ("localhost", "127.0.0.1", "::1")
    ):
        raise SystemExit(
            "Provisioning is restricted to local nexis_db."
        )

    print("NEXIS Instructor Account Provisioning")
    print("-------------------------------------")

    print("Database:", engine.url.database)
    print("Host:", engine.url.host)
    print("Database User:", engine.url.username)

    confirmation = input(
        "\nType CREATE to continue: "
    ).strip()

    if confirmation != "CREATE":
        raise SystemExit("Operation cancelled.")

    email_input = input("Instructor email: ").strip()

    try:
        email = str(
            TypeAdapter(EmailStr).validate_python(email_input)
        ).lower()
    except Exception:
        raise SystemExit("Invalid email address.")

    full_name = input("Instructor full name: ").strip()

    if not 2 <= len(full_name) <= 120:
        raise SystemExit("Name must be between 2 and 120 characters.")

    password = getpass("Instructor password: ")
    confirm_password = getpass("Confirm password: ")

    if password != confirm_password:
        raise SystemExit("Passwords do not match.")

    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters.")

    try:
        with SessionLocal() as db:
            existing = db.scalar(
                select(User).where(User.email == email)
            )

            if existing:
                raise SystemExit(
                    "An account with this email already exists."
                )

            instructor = User(
                email=email,
                full_name=full_name,
                password_hash=hash_password(password),
                role="instructor",
            )

            db.add(instructor)
            db.commit()
            db.refresh(instructor)

            print("\nInstructor created successfully.")
            print("ID:", instructor.id)
            print("Email:", instructor.email)
            print("Role:", instructor.role)

    except IntegrityError:
        raise SystemExit(
            "Account creation failed. Check for a duplicate email."
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
