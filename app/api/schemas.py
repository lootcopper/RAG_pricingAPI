from datetime import datetime, timezone
from typing import Generic, Optional, TypeVar, List, Dict, Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import Modality

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Base API response wrapper."""

    status: str = "success"
    message: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: Optional[T] = None


class ProviderModel(BaseModel):
    """Represents a model offered by a provider."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    api_model_name: str
    context_window: int
    max_output_tokens: int | None
    tokens_per_second: float | None
    modalities: list[Modality]
    provider_id: int
    is_active: bool


class ModelPricing(BaseModel):
    """Represents pricing information for a specific model."""
    
    model: str
    provider: str
    input_token_price: float
    output_token_price: float
    unit: str = "per token"
    modality: str
    free_tier: bool = False


class PricingAggregation(BaseModel):
    """Represents aggregated pricing information for a model across providers."""
    
    model: str
    provider: str
    input_token_price: float
    output_token_price: float
    modality: str


class PricingCompareRequest(BaseModel):
    """Request body for pricing comparison endpoint."""
    
    models: List[str]
    mode: str = "sync"
    input_tokens: int = 1000
    output_tokens: int = 1000


class ModelComparison(BaseModel):
    """Enhanced model comparison data with cost analysis."""
    
    model: str
    provider: str
    input_token_price: float
    output_token_price: float
    modality: str
    context_window: int
    
    input_cost: float
    output_cost: float
    total_cost: float

    input_cost_rank: int
    output_cost_rank: int
    total_cost_rank: int

    cost_per_character: float
    efficiency_score: float


class ComparisonSummary(BaseModel):
    """Detailed comparison summary with insights."""
    
    total_models: int
    mode: str
    scenario: Dict[str, int]  
    price_ranges: Dict[str, Dict[str, float]]
    recommendations: Dict[str, Any]
    cost_analysis: Dict[str, Any]
    provider_insights: Dict[str, Any]


class PricingComparison(BaseModel):
    """Enhanced pricing comparison response."""
    
    models: List[ModelComparison]
    comparison_summary: ComparisonSummary



class RAGQueryRequest(BaseModel):
    """Request for natural language model search."""
    
    query: str
    max_results: int = 5
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Optional filters for search")


class ModelRecommendation(BaseModel):
    """Model recommendation from RAG search."""
    
    model_name: str
    provider: str
    modalities: List[str]
    context_window: int
    input_price: float
    output_price: float
    estimated_cost: Optional[float] = None
    reasoning: str
    budget_friendly: bool = False


class RAGRecommendationResponse(BaseModel):
    """Response for model recommendations."""
    
    use_case: str
    budget: Optional[float] = None
    max_tokens: Optional[int] = None
    recommendations: List[ModelRecommendation]
    cost_analysis: Dict[str, Any]
    provider_breakdown: Dict[str, int]


class RAGSearchResult(BaseModel):
    """Result from semantic model search."""
    
    model_name: str
    content: str
    metadata: Dict[str, Any]
    distance: Optional[float] = None


class RAGSearchResponse(BaseModel):
    """Response for semantic model search."""
    
    query: str
    results: List[RAGSearchResult]
    total_results: int
