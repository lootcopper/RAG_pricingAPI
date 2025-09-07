from sqlalchemy.orm import Session

from app import models
from app.models import Modality, ProviderModelModality


def add_model_to_provider(
    db: Session,
    provider_id: int,
    model_id: int,
    api_model_name: str,
    context_window: int,
    max_output_tokens: int,
    input_cost_per_mtok: float,
    output_cost_per_mtok: float,
    modalities: list[Modality],
    tokens_per_second: float = None,
    supports_tools: bool = False,
    discount_start_time_utc: str = "00:00",
    discount_end_time_utc: str = "00:00",
    input_discount_price: float = 0.0,
    output_discount_price: float = 0.0,
    is_active: bool = True,
    cached_input_cost_per_mtok: float = None,  
) -> models.ProviderModel:
    """
    Adds a model offering from a provider, linking a Provider and a Model.
    This also handles updates if the offering already exists.
    """
    db_offering = (
        db.query(models.ProviderModel).filter_by(provider_id=provider_id, model_id=model_id).first()
    )

    if db_offering:
        
        db_offering.api_model_name = api_model_name
        db_offering.context_window = context_window
        db_offering.max_output_tokens = max_output_tokens
        db_offering.input_cost_per_mtok = input_cost_per_mtok
        db_offering.cached_input_cost_per_mtok = cached_input_cost_per_mtok 
        db_offering.output_cost_per_mtok = output_cost_per_mtok
        db_offering.tokens_per_second = tokens_per_second
        db_offering.supports_tools = supports_tools
        db_offering.discount_start_time_utc = discount_start_time_utc
        db_offering.discount_end_time_utc = discount_end_time_utc
        db_offering.input_discount_price = input_discount_price
        db_offering.output_discount_price = output_discount_price
        db_offering.is_active = is_active
       
        db_offering.modalities_association.clear()
        db_offering.modalities_association = [ProviderModelModality(modality=m) for m in modalities]
    else:
       
        db_offering = models.ProviderModel(
            provider_id=provider_id,
            model_id=model_id,
            api_model_name=api_model_name,
            context_window=context_window,
            max_output_tokens=max_output_tokens,
            input_cost_per_mtok=input_cost_per_mtok,
            cached_input_cost_per_mtok=cached_input_cost_per_mtok, 
            output_cost_per_mtok=output_cost_per_mtok,
            tokens_per_second=tokens_per_second,
            supports_tools=supports_tools,
            discount_start_time_utc=discount_start_time_utc,
            discount_end_time_utc=discount_end_time_utc,
            input_discount_price=input_discount_price,
            output_discount_price=output_discount_price,
            is_active=is_active,
            modalities_association=[ProviderModelModality(modality=m) for m in modalities],
        )
        db.add(db_offering)

    db.commit()
    db.refresh(db_offering)
    return db_offering


def find_models(
    db: Session,
    min_context_window: int | None = None,
    required_modalities: list[Modality] | None = None,
    supports_tools: bool | None = None,
    is_active: bool = True,
) -> list[models.ProviderModel]:
    """
    Finds model offerings based on specified criteria.
    """
    query = db.query(models.ProviderModel).filter(models.ProviderModel.is_active == is_active)

    if min_context_window is not None:
        query = query.filter(models.ProviderModel.context_window >= min_context_window)

    if required_modalities:
        for modality in required_modalities:
            query = query.filter(models.ProviderModel.modalities_association.any(modality=modality))

    if supports_tools is not None:
        query = query.filter(models.ProviderModel.supports_tools == supports_tools)

    query = query.order_by(
        (models.ProviderModel.input_cost_per_mtok + models.ProviderModel.output_cost_per_mtok) / 2
    )

    return query.all()


def get_model_by_id(db: Session, model_id: int) -> models.ProviderModel | None:
    """
    Get a specific provider model by ID.
    """
    return db.query(models.ProviderModel).filter(models.ProviderModel.id == model_id).first()


def get_all_pricing_data(
    db: Session,
    modality: str | None = None,
    mode: str | None = None,
    region: str | None = None,
) -> list[models.ProviderModel]:
    """
    Get all pricing data for active models with optional filtering.
    """
    query = db.query(models.ProviderModel).filter(models.ProviderModel.is_active == True)
    
   
    if modality:
        modality_enum = Modality(modality.lower())
        query = query.filter(models.ProviderModel.modalities_association.any(modality=modality_enum))
    
   
    
    return query.all()


def find_models_by_api_names(
    db: Session,
    api_model_names: list[str],
) -> list[models.ProviderModel]:
    """
    Find models by their API model names with enhanced data for comparison.
    """
    return (
        db.query(models.ProviderModel)
        .filter(
            models.ProviderModel.api_model_name.in_(api_model_names),
            models.ProviderModel.is_active == True
        )
        .order_by(models.ProviderModel.input_cost_per_mtok + models.ProviderModel.output_cost_per_mtok)
        .all()
    )


def get_all_available_model_names(db: Session) -> list[str]:
    """
    Get all available model names for reference.
    """
    return [
        model.api_model_name 
        for model in db.query(models.ProviderModel)
        .filter(models.ProviderModel.is_active == True)
        .all()
    ]
