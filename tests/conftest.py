from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


from app.models import Base


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Fixture to create a new database session for each test function.
    Uses an in-memory SQLite database.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
