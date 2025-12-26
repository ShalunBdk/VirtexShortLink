"""
Initialize database and create first superuser.

Run this script once to set up the database:
    python init_db.py
"""

from app.database import engine, Base, SessionLocal
from app.models import User
from app.core.security import get_password_hash


def init_database():
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


def create_superuser():
    """Create the first superuser"""
    db = SessionLocal()

    try:
        # Check if any users exist
        existing_user = db.query(User).first()

        if existing_user:
            print("Users already exist in the database.")
            print("Skipping superuser creation.")
            return

        # Create superuser
        print("\nCreating superuser...")

        # Simple password for initial setup
        password = "q1w2e3r4_+ASD"

        try:
            hashed_pwd = get_password_hash(password)
        except Exception as hash_error:
            print(f"Error hashing password: {hash_error}")
            print("Trying alternative method...")
            # Fallback: use bcrypt directly
            import bcrypt
            hashed_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        superuser = User(
            username="admin",
            email="admin@virtexfood.com",
            hashed_password=hashed_pwd,
            is_active=True,
            is_superuser=True
        )

        db.add(superuser)
        db.commit()

        print("\n" + "="*50)
        print("Superuser created successfully!")
        print("="*50)
        print(f"Username: admin")
        print(f"Password: admin123")
        print(f"Email: admin@virtexfood.com")
        print("="*50)
        print("\n⚠️  IMPORTANT: Change this password after first login!")
        print("="*50)

    except Exception as e:
        print(f"Error creating superuser: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("="*50)
    print("Virtex Food Short Links - Database Initialization")
    print("="*50)

    init_database()
    create_superuser()

    print("\n✅ Database initialization complete!")
    print("\nYou can now start the server with:")
    print("    uvicorn app.main:app --reload")
