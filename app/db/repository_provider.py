from sqlalchemy.orm import Session

from app import models


def create_provider(
    db: Session, name: str, website: str, api_key_name: str | None = None
) -> models.Provider:
    """Creates a new Model Provider."""
    db_provider = models.Provider(name=name, website=website, api_key_name=api_key_name)
    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)
    return db_provider


def get_provider(db: Session, provider_id: int) -> models.Provider | None:
    """Retrieves a Provider by its ID."""
    return db.query(models.Provider).filter(models.Provider.id == provider_id).first()


def get_provider_by_name(db: Session, name: str) -> models.Provider | None:
    """Retrieves a Provider by its unique name."""
    return db.query(models.Provider).filter(models.Provider.name == name).first()


def get_all_providers(db: Session, skip: int = 0, limit: int = 100) -> list[models.Provider]:
    """Retrieves all Providers with pagination."""
    return db.query(models.Provider).offset(skip).limit(limit).all()


def get_or_create_provider(
    db: Session, name: str, website: str, api_key_name: str | None = None
) -> models.Provider:
    """
    Retrieves a Provider by name if it exists, otherwise creates it.
    """
    db_provider = get_provider_by_name(db, name=name)
    if db_provider:
        return db_provider
    return create_provider(db, name=name, website=website, api_key_name=api_key_name)
