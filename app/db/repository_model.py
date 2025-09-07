from sqlalchemy.orm import Session

from app import models


def create_model(db: Session, model_name: str) -> models.Model:
    """Creates a new Model."""
    db_model = models.Model(model_name=model_name)
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model


def get_model(db: Session, model_id: int) -> models.Model | None:
    """Retrieves a Model by its ID."""
    return db.query(models.Model).filter(models.Model.id == model_id).first()


def get_model_by_name(db: Session, name: str) -> models.Model | None:
    """Retrieves a Model by its unique name."""
    return db.query(models.Model).filter(models.Model.model_name == name).first()


def get_all_models(db: Session, skip: int = 0, limit: int = 100) -> list[models.Model]:
    """Retrieves all Models with pagination."""
    return db.query(models.Model).offset(skip).limit(limit).all()


def get_or_create_model(db: Session, model_name: str) -> models.Model:
    """
    Retrieves a Model by name if it exists, otherwise creates it.
    """
    db_model = get_model_by_name(db, name=model_name)
    if db_model:
        return db_model
    return create_model(db, model_name=model_name)
