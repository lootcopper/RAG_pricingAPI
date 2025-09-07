from sqlalchemy.orm import Session

from app.db import (
    repository_model,
    repository_provider,
    repository_provider_model,
)
from app.models import Modality


def test_add_model_to_provider(db: Session):
    provider = repository_provider.create_provider(db, name="P1", website="p1.com")
    model = repository_model.create_model(db, model_name="M1")

    offering = repository_provider_model.add_model_to_provider(
        db=db,
        provider_id=provider.id,
        model_id=model.id,
        api_model_name="p1/m1",
        context_window=8000,
        max_output_tokens=4096,
        input_cost_per_mtok=1.0,
        output_cost_per_mtok=2.0,
        modalities=[Modality.TEXT, Modality.IMAGE],
    )

    assert offering.api_model_name == "p1/m1"
    assert offering.context_window == 8000
    assert Modality.IMAGE in offering.modalities


def test_add_model_to_provider_update(db: Session):
    provider = repository_provider.create_provider(db, name="P1", website="p1.com")
    model = repository_model.create_model(db, model_name="M1")

    # First, create the offering
    offering1 = repository_provider_model.add_model_to_provider(
        db=db,
        provider_id=provider.id,
        model_id=model.id,
        api_model_name="p1/m1",
        context_window=8000,
        max_output_tokens=4096,
        input_cost_per_mtok=1.0,
        output_cost_per_mtok=2.0,
        modalities=[Modality.TEXT],
    )
    assert offering1.context_window == 8000

    # Now, update it
    offering2 = repository_provider_model.add_model_to_provider(
        db=db,
        provider_id=provider.id,
        model_id=model.id,
        api_model_name="p1/m1-updated",
        context_window=16000,
        max_output_tokens=8192,
        input_cost_per_mtok=1.5,
        output_cost_per_mtok=2.5,
        modalities=[Modality.TEXT, Modality.IMAGE],
    )

    assert offering1.id == offering2.id
    assert offering2.api_model_name == "p1/m1-updated"
    assert offering2.context_window == 16000
    assert Modality.IMAGE in offering2.modalities


def test_find_models(db: Session):
    p1 = repository_provider.create_provider(db, name="P1", website="p1.com")
    p2 = repository_provider.create_provider(db, name="P2", website="p2.com")
    m1 = repository_model.create_model(db, model_name="M1-cheapest")
    m2 = repository_model.create_model(db, model_name="M2-image")
    m3 = repository_model.create_model(db, model_name="M3-tools")
    m4 = repository_model.create_model(db, model_name="M4-inactive")

    # A cheap text model
    repository_provider_model.add_model_to_provider(
        db=db,
        provider_id=p1.id,
        model_id=m1.id,
        api_model_name="p1/m1",
        context_window=8000,
        max_output_tokens=2048,
        input_cost_per_mtok=0.5,
        output_cost_per_mtok=1.5,
        modalities=[Modality.TEXT],
        is_active=True,
    )
    # A model that supports images, more expensive
    repository_provider_model.add_model_to_provider(
        db=db,
        provider_id=p1.id,
        model_id=m2.id,
        api_model_name="p1/m2",
        context_window=4000,
        max_output_tokens=1024,
        input_cost_per_mtok=1.0,
        output_cost_per_mtok=3.0,
        modalities=[Modality.TEXT, Modality.IMAGE],
        is_active=True,
    )
    # A model that supports tools, most expensive
    repository_provider_model.add_model_to_provider(
        db=db,
        provider_id=p2.id,
        model_id=m3.id,
        api_model_name="p2/m3",
        context_window=16000,
        max_output_tokens=4096,
        input_cost_per_mtok=2.0,
        output_cost_per_mtok=5.0,
        modalities=[Modality.TEXT],
        supports_tools=True,
        is_active=True,
    )
    # An inactive model
    repository_provider_model.add_model_to_provider(
        db=db,
        provider_id=p2.id,
        model_id=m4.id,
        api_model_name="p2/m4",
        context_window=4000,
        max_output_tokens=1024,
        input_cost_per_mtok=1.0,
        output_cost_per_mtok=1.0,
        modalities=[Modality.TEXT],
        is_active=False,
    )

    # By default, only active models are returned
    results = repository_provider_model.find_models(db)
    assert len(results) == 3
    assert "p2/m4" not in [r.api_model_name for r in results]

    # Test finding inactive models
    results = repository_provider_model.find_models(db, is_active=False)
    assert len(results) == 1
    assert results[0].api_model_name == "p2/m4"

    # Find models with image support
    results = repository_provider_model.find_models(
        db, required_modalities=[Modality.IMAGE]
    )
    assert len(results) == 1
    assert results[0].api_model_name == "p1/m2"

    # Find models with high context window
    results = repository_provider_model.find_models(db, min_context_window=10000)
    assert len(results) == 1
    assert results[0].api_model_name == "p2/m3"

    # Find models that support tools
    results = repository_provider_model.find_models(db, supports_tools=True)
    assert len(results) == 1
    assert results[0].api_model_name == "p2/m3"

    # Find with multiple criteria
    results = repository_provider_model.find_models(
        db, min_context_window=4000, required_modalities=[Modality.IMAGE]
    )
    assert len(results) == 1
    assert results[0].api_model_name == "p1/m2"

    # Test cost ordering (avg cost = (input + output) / 2)
    # p1/m1 avg cost = (0.5+1.5)/2 = 1.0
    # p1/m2 avg cost = (1.0+3.0)/2 = 2.0
    # p2/m3 avg cost = (2.0+5.0)/2 = 3.5
    results = repository_provider_model.find_models(db)
    api_model_names = [r.api_model_name for r in results]
    assert api_model_names == ["p1/m1", "p1/m2", "p2/m3"]
