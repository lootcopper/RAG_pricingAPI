from fastapi import APIRouter, Depends, Query, Path, HTTPException
from sqlalchemy.orm import Session

from app.api import dependencies
from app.api.schemas import (
    ApiResponse, 
    ProviderModel, 
    ModelPricing, 
    PricingAggregation, 
    PricingCompareRequest, 
    PricingComparison,
    ModelComparison,
    ComparisonSummary,
    RAGQueryRequest,
    RAGSearchResponse,
    RAGSearchResult,
    RAGRecommendationResponse,
    ModelRecommendation
)
from app.db import repository_provider_model
from app.models import Modality

# Import RAG service only when needed
try:
    from app.rag_service import rag_service
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    rag_service = None

router = APIRouter()


@router.get("/", response_model=ApiResponse)
def root():
    """
    Root endpoint for the API.
    """
    return ApiResponse(data={"message": "Ready"})


@router.get("/models", response_model=ApiResponse[list[ProviderModel]])
def find_provider_models(
    min_context_window: int | None = Query(None, description="Minimum context window size."),
    required_modalities: list[Modality] | None = Query(
        None, description="Modalities the model must support."
    ),
    is_active: bool = Query(True, description="Whether to filter for active models only."),
    db: Session = Depends(dependencies.get_db),
):
    """
    Find available provider models based on specified criteria.
    """
    provider_models = repository_provider_model.find_models(
        db=db,
        min_context_window=min_context_window,
        required_modalities=required_modalities,
        is_active=is_active,
    )
    return ApiResponse(data=provider_models)


@router.get("/models/names", response_model=ApiResponse[list[str]])
def get_available_model_names(
    db: Session = Depends(dependencies.get_db),
):
    """
    Get all available model names for reference in pricing comparisons.
    """
    model_names = repository_provider_model.get_all_available_model_names(db=db)
    return ApiResponse(data=model_names)


@router.get("/modalities", response_model=ApiResponse[list[str]])
def get_available_modalities():
    """
    Get all available modalities supported by models.
    """
    modalities = [modality.value for modality in Modality]
    return ApiResponse(data=modalities)


@router.get("/models/{model_id}/pricing", response_model=ApiResponse[ModelPricing])
def get_model_pricing(
    model_id: int = Path(..., description="The ID of the model to get pricing for"),
    mode: str = Query("sync", description="Mode of operation: sync or async"),
    tier: str = Query("standard", description="Service tier: standard or pro"),
    region: str = Query(None, description="AWS region or provider region"),
    db: Session = Depends(dependencies.get_db),
):
    
    provider_model = repository_provider_model.get_model_by_id(db=db, model_id=model_id)
    
    if not provider_model:
        raise HTTPException(status_code=404, detail="Model not found")
    input_price_per_token = provider_model.input_cost_per_mtok / 1_000_000
    output_price_per_token = provider_model.output_cost_per_mtok / 1_000_000
    modality_str = provider_model.modalities[0].value if provider_model.modalities else "text"
    
    pricing_data = ModelPricing(
        model=provider_model.api_model_name,
        provider=provider_model.provider.name,
        input_token_price=input_price_per_token,
        output_token_price=output_price_per_token,
        unit="per token",
        modality=modality_str,
        free_tier=False  
    )
    
    return ApiResponse(data=pricing_data)


@router.get("/pricing", response_model=ApiResponse[list[PricingAggregation]])
def get_pricing_aggregation(
    modality: str | None = Query(None, description="Filter by modality (text, image, audio, video)"),
    mode: str | None = Query(None, description="Mode of operation (sync, async)"),
    region: str | None = Query(None, description="AWS region or provider region"),
    db: Session = Depends(dependencies.get_db),
):
    """
    Aggregate pricing view across all providers.
    """
    provider_models = repository_provider_model.get_all_pricing_data(
        db=db,
        modality=modality,
        mode=mode,
        region=region,
    )
    
    pricing_data = []
    for provider_model in provider_models:
        input_price_per_token = provider_model.input_cost_per_mtok / 1_000_000
        output_price_per_token = provider_model.output_cost_per_mtok / 1_000_000
        modality_str = provider_model.modalities[0].value if provider_model.modalities else "text"
        
        pricing_aggregation = PricingAggregation(
            model=provider_model.api_model_name,
            provider=provider_model.provider.name,
            input_token_price=input_price_per_token,
            output_token_price=output_price_per_token,
            modality=modality_str,
        )
        pricing_data.append(pricing_aggregation)
    
    return ApiResponse(data=pricing_data)


@router.post("/pricing/compare", response_model=ApiResponse[PricingComparison])
def compare_pricing(
    request: PricingCompareRequest,
    db: Session = Depends(dependencies.get_db),
):
    """
    Compare pricing across selected models with detailed cost analysis and recommendations.
    """
    provider_models = repository_provider_model.find_models_by_api_names(
        db=db,
        api_model_names=request.models,
    )
    
    if not provider_models:
        raise HTTPException(status_code=404, detail="No models found with the specified names")
    
    
    comparison_data = []
    for provider_model in provider_models:
        input_price_per_token = provider_model.input_cost_per_mtok / 1_000_000
        output_price_per_token = provider_model.output_cost_per_mtok / 1_000_000
        modality_str = provider_model.modalities[0].value if provider_model.modalities else "text"
        
       
        input_cost = input_price_per_token * request.input_tokens
        output_cost = output_price_per_token * request.output_tokens
        total_cost = input_cost + output_cost
        
       
        cost_per_character = total_cost / (request.input_tokens + request.output_tokens) / 4
        
      
        efficiency_score = 1.0 / (total_cost + 0.000001)  
        
        comparison_item = ModelComparison(
            model=provider_model.api_model_name,
            provider=provider_model.provider.name,
            input_token_price=input_price_per_token,
            output_token_price=output_price_per_token,
            modality=modality_str,
            context_window=provider_model.context_window,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            input_cost_rank=0,  
            output_cost_rank=0,  
            total_cost_rank=0,   
            cost_per_character=cost_per_character,
            efficiency_score=efficiency_score,
        )
        comparison_data.append(comparison_item)
    
  
    sorted_by_input_cost = sorted(comparison_data, key=lambda x: x.input_cost)
    sorted_by_output_cost = sorted(comparison_data, key=lambda x: x.output_cost)
    sorted_by_total_cost = sorted(comparison_data, key=lambda x: x.total_cost)
    
    for i, item in enumerate(sorted_by_input_cost):
        item.input_cost_rank = i + 1
    for i, item in enumerate(sorted_by_output_cost):
        item.output_cost_rank = i + 1
    for i, item in enumerate(sorted_by_total_cost):
        item.total_cost_rank = i + 1
    
    
    if comparison_data:
        
        min_input_price = min(p.input_token_price for p in comparison_data)
        max_input_price = max(p.input_token_price for p in comparison_data)
        min_output_price = min(p.output_token_price for p in comparison_data)
        max_output_price = max(p.output_token_price for p in comparison_data)
        
       
        min_total_cost = min(p.total_cost for p in comparison_data)
        max_total_cost = max(p.total_cost for p in comparison_data)
        avg_total_cost = sum(p.total_cost for p in comparison_data) / len(comparison_data)
        
       
        cheapest_model = min(comparison_data, key=lambda x: x.total_cost)
        most_expensive_model = max(comparison_data, key=lambda x: x.total_cost)
        most_efficient_model = max(comparison_data, key=lambda x: x.efficiency_score)
        
        
        provider_counts = {}
        provider_avg_costs = {}
        for item in comparison_data:
            provider_counts[item.provider] = provider_counts.get(item.provider, 0) + 1
            if item.provider not in provider_avg_costs:
                provider_avg_costs[item.provider] = []
            provider_avg_costs[item.provider].append(item.total_cost)
        
        for provider in provider_avg_costs:
            provider_avg_costs[provider] = sum(provider_avg_costs[provider]) / len(provider_avg_costs[provider])
        
        cheapest_provider = min(provider_avg_costs.items(), key=lambda x: x[1])
        
        comparison_summary = ComparisonSummary(
            total_models=len(comparison_data),
            mode=request.mode,
            scenario={
                "input_tokens": request.input_tokens,
                "output_tokens": request.output_tokens
            },
            price_ranges={
                "input_token_price": {
                    "min": min_input_price,
                    "max": max_input_price,
                    "range": max_input_price - min_input_price
                },
                "output_token_price": {
                    "min": min_output_price,
                    "max": max_output_price,
                    "range": max_output_price - min_output_price
                }
            },
            recommendations={
                "cheapest_overall": {
                    "model": cheapest_model.model,
                    "provider": cheapest_model.provider,
                    "total_cost": cheapest_model.total_cost
                },
                "most_efficient": {
                    "model": most_efficient_model.model,
                    "provider": most_efficient_model.provider,
                    "efficiency_score": most_efficient_model.efficiency_score
                },
                "best_input_cost": min(comparison_data, key=lambda x: x.input_cost).model,
                "best_output_cost": min(comparison_data, key=lambda x: x.output_cost).model,
                "cost_savings": {
                    "vs_most_expensive": most_expensive_model.total_cost - cheapest_model.total_cost,
                    "vs_average": avg_total_cost - cheapest_model.total_cost
                }
            },
            cost_analysis={
                "total_cost_range": {
                    "min": min_total_cost,
                    "max": max_total_cost,
                    "average": avg_total_cost,
                    "spread": max_total_cost - min_total_cost
                },
                "cost_distribution": {
                    "cheapest_25_percent": sorted_by_total_cost[:len(sorted_by_total_cost)//4] if len(sorted_by_total_cost) >= 4 else sorted_by_total_cost,
                    "most_expensive_25_percent": sorted_by_total_cost[-len(sorted_by_total_cost)//4:] if len(sorted_by_total_cost) >= 4 else sorted_by_total_cost
                }
            },
            provider_insights={
                "provider_distribution": provider_counts,
                "cheapest_provider": {
                    "name": cheapest_provider[0],
                    "average_cost": cheapest_provider[1]
                },
                "provider_cost_comparison": provider_avg_costs
            }
        )
    else:
        comparison_summary = ComparisonSummary(
            total_models=0,
            mode=request.mode,
            scenario={"input_tokens": request.input_tokens, "output_tokens": request.output_tokens},
            price_ranges={},
            recommendations={},
            cost_analysis={},
            provider_insights={}
        )
    
    comparison_response = PricingComparison(
        models=comparison_data,
        comparison_summary=comparison_summary
    )
    
    return ApiResponse(data=comparison_response)



@router.post("/rag/search", response_model=ApiResponse[RAGSearchResponse])
def search_models_rag(
    request: RAGQueryRequest,
    db: Session = Depends(dependencies.get_db),
):
    """
    Search for models using natural language queries.
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG service not available. Please install chromadb and sentence-transformers.")
    
    try:
        
        rag_service.index_models(db)
        
        
        results = rag_service.search_models(
            query=request.query,
            n_results=request.max_results
        )
        
    
        search_results = []
        for result in results:
            search_result = RAGSearchResult(
                model_name=result['model_name'],
                content=result['content'],
                metadata=result['metadata'],
                distance=result['distance']
            )
            search_results.append(search_result)
        
        response = RAGSearchResponse(
            query=request.query,
            results=search_results,
            total_results=len(search_results)
        )
        
        return ApiResponse(data=response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG search failed: {str(e)}")


@router.post("/rag/recommendations", response_model=ApiResponse[RAGRecommendationResponse])
def get_model_recommendations(
    use_case: str = Query(..., description="Use case description (e.g., 'coding', 'document analysis')"),
    budget: float | None = Query(None, description="Maximum budget in dollars"),
    max_tokens: int | None = Query(None, description="Estimated token usage"),
    db: Session = Depends(dependencies.get_db),
):
    """
    Get model recommendations based on use case and constraints.
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG service not available. Please install chromadb and sentence-transformers.")
    
    try:
        
        rag_service.index_models(db)
        

        recommendations_data = rag_service.get_model_recommendations(
            use_case=use_case,
            budget=budget,
            max_tokens=max_tokens
        )
        
        
        recommendations = []
        for rec in recommendations_data['recommendations']:
            recommendation = ModelRecommendation(
                model_name=rec['model_name'],
                provider=rec['provider'],
                modalities=rec['modalities'],
                context_window=rec['context_window'],
                input_price=rec['input_price'],
                output_price=rec['output_price'],
                estimated_cost=rec['estimated_cost'],
                reasoning=rec['reasoning'],
                budget_friendly=rec['budget_friendly']
            )
            recommendations.append(recommendation)
        
        response = RAGRecommendationResponse(
            use_case=recommendations_data['use_case'],
            budget=recommendations_data['budget'],
            max_tokens=recommendations_data['max_tokens'],
            recommendations=recommendations,
            cost_analysis=recommendations_data['cost_analysis'],
            provider_breakdown=recommendations_data['provider_breakdown']
        )
        
        return ApiResponse(data=response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendations failed: {str(e)}")


@router.post("/rag/index", response_model=ApiResponse)
def index_models_rag(
    db: Session = Depends(dependencies.get_db),
):
    """
    Manually trigger indexing of all models in the vector database.
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG service not available. Please install chromadb and sentence-transformers.")
    
    try:
        rag_service.index_models(db)
        return ApiResponse(data={"message": "Models indexed successfully"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")
