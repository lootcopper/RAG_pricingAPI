from sqlalchemy.orm import Session

from app.db import repository_provider


def test_create_and_get_provider(db: Session):
    provider = repository_provider.create_provider(
        db, name="TestProvider", website="https://test.com", api_key_name="TEST_KEY"
    )
    assert provider.name == "TestProvider"
    assert provider.website == "https://test.com"

    fetched = repository_provider.get_provider(db, provider.id)
    assert fetched
    assert fetched.name == "TestProvider"


def test_get_or_create_provider(db: Session):
    # Test creation
    provider1 = repository_provider.get_or_create_provider(
        db, name="NewProvider", website="https://new.com"
    )
    assert provider1.name == "NewProvider"

    # Test retrieval
    provider2 = repository_provider.get_or_create_provider(
        db, name="NewProvider", website="https://new.com"
    )
    assert provider1.id == provider2.id


def test_get_provider_by_name(db: Session):
    repository_provider.create_provider(
        db, name="KnownProvider", website="https://known.com"
    )
    fetched = repository_provider.get_provider_by_name(db, name="KnownProvider")
    assert fetched
    assert fetched.name == "KnownProvider"

    not_found = repository_provider.get_provider_by_name(db, name="UnknownProvider")
    assert not_found is None


def test_get_all_providers(db: Session):
    repository_provider.create_provider(db, name="P1", website="p1.com")
    repository_provider.create_provider(db, name="P2", website="p2.com")

    all_providers = repository_provider.get_all_providers(db)
    assert len(all_providers) == 2

    paginated = repository_provider.get_all_providers(db, skip=1, limit=1)
    assert len(paginated) == 1
    assert paginated[0].name == "P2"
