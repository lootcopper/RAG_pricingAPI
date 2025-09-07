from sqlalchemy.orm import Session

from app.db import repository_model


def test_create_and_get_model(db: Session):
    model = repository_model.create_model(db, model_name="TestModel-1")
    assert model.model_name == "TestModel-1"

    fetched = repository_model.get_model(db, model.id)
    assert fetched
    assert fetched.model_name == "TestModel-1"


def test_get_or_create_model(db: Session):
    # Test creation
    model1 = repository_model.get_or_create_model(db, "NewModel")
    assert model1.model_name == "NewModel"

    # Test retrieval
    model2 = repository_model.get_or_create_model(db, "NewModel")
    assert model1.id == model2.id


def test_get_model_by_name(db: Session):
    repository_model.create_model(db, model_name="KnownModel")
    fetched = repository_model.get_model_by_name(db, name="KnownModel")
    assert fetched
    assert fetched.model_name == "KnownModel"
    not_found = repository_model.get_model_by_name(db, name="UnknownModel")
    assert not_found is None


def test_get_all_models(db: Session):
    repository_model.create_model(db, "M1")
    repository_model.create_model(db, "M2")

    all_models = repository_model.get_all_models(db)
    assert len(all_models) == 2

    paginated = repository_model.get_all_models(db, skip=1, limit=1)
    assert len(paginated) == 1
    assert paginated[0].model_name == "M2"
