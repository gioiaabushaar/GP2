import argparse
from sqlalchemy import select
from app.core.db import Base, engine, SessionLocal
from app.core.models import User, Challenge, Writeup
from app.core.security import hash_password

def seed(email: str, password: str):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.email == email.lower()))
        if not u:
            u = User(email=email.lower(), full_name="NEXIS Demo Instructor", password_hash=hash_password(password), role="instructor")
            db.add(u)
        if not db.scalar(select(Challenge).where(Challenge.title == "SQL Injection Basics")):
            c = Challenge(title="SQL Injection Basics", description="Offline educational demo: identify why concatenating SQL strings is unsafe. No vulnerable public endpoint is deployed.", category="Web", difficulty="Easy", points=100, flag_hash=hash_password("NEXIS{demo_sql_injection}"))
            db.add(c)
            db.flush()
            db.add(Writeup(challenge_id=c.id, source="NEXIS local demo guide", content="SQL injection happens when untrusted input is combined with a query. Parameterized queries separate query structure from user-provided values. Validation and least privilege offer defense in depth. Review prepared statements and safe database APIs. Alternative safe designs include ORM bind parameters."))
        if not db.scalar(select(Challenge).where(Challenge.title == "Network Traffic Basics")):
            c = Challenge(title="Network Traffic Basics", description="Explore common network metadata and security logging concepts in an offline exercise.", category="Network", difficulty="Easy", points=100, flag_hash=hash_password("NEXIS{demo_network}"))
            db.add(c)
            db.flush()
            db.add(Writeup(challenge_id=c.id, source="NEXIS local network guide", content="Traffic analysis starts by identifying protocol, source, destination, ports and timestamps. DNS resolves names. HTTP is an application-layer protocol. Compare benign and unusual traffic patterns. Evaluate flow direction and interpret logs."))
        db.commit()
    print("Seed completed. Instructor:", email)
    print("Demo flags for classroom testing: NEXIS{demo_sql_injection}, NEXIS{demo_network}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    seed(args.email, args.password)