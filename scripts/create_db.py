from app.db.session import engine
from app.models import Base


def main():
    """Creates all database tables."""
    print("Creating database tables...")
    Base.metadata.drop_all(bind=engine)  
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")


if __name__ == "__main__":
    main()
