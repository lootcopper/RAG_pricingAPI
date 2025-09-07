from app.db.session import SessionLocal


def get_db():
    """
    Dependency function that provides a database session to an endpoint.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
