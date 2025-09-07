import abc
from dataclasses import dataclass

from app.models import Modality


@dataclass
class ProviderModelSpec:
    """
    A standard data structure for returning scraped model information.
    """

    provider_name: str
    """
    The name of the provider, e.g., "OpenAI", "Anthropic", etc.
    """
    provider_api_key_name: str | None
    """
    The name of the API key used to authenticate with the provider.
    This is used to identify the API key in the configuration. Can be None
    for providers that do not use a simple API key (e.g., AWS Bedrock).
    """
    provider_website: str
    """
    The website URL of the provider, e.g., "https://openai.com".
    """
    model_name: str
    """
    The name of the model, independent of the provider.
    For example, "Claude 3 Opus" or "GPT-4 Turbo".
    """
    api_model_name: str
    """
    The specific API model name used by the provider.
    For example, "gpt-4-turbo" or "claude-3-opus".
    """
    context_window: int
    """
    The maximum context window size for the model, in tokens.
    This is the maximum number of tokens the model can process in a single request.
    """
    max_output_tokens: int | None
    """
    The maximum number of output tokens a model can generate.
    Can be None if not applicable or not specified.
    """
    input_cost_per_mtok: float
    """
    The cost of input tokens for the model, in USD per million tokens.
    """
    output_cost_per_mtok: float
    """
    The cost of output tokens for the model, in USD per million tokens.
    """
    modalities: list[Modality]
    """
    A list of modalities supported by the model (e.g., text, image, audio).
    """
    supports_tools: bool
    """
    Whether the model supports tool usage (e.g., function calling).
    This is True if the model can use tools, False otherwise.
    """
    discount_start_time_utc: str = "00:00"  
    discount_end_time_utc: str = "00:00"    
    input_discount_price: float = 0.0       
    output_discount_price: float = 0.0
 
    cached_input_cost_per_mtok: float | None = None
    """
    The cost of cached input tokens for the model, in USD per million tokens.
    This is typically lower than regular input cost and applies to providers
    that offer caching discounts (e.g., OpenAI). Can be None if not supported.
    """
    tokens_per_second: float | None = None
    """
    The speed of the model in tokens per second.
    This is optional and may be None if not applicable.
    """

class BaseProviderModelScraper(abc.ABC):
    """
    Abstract base class for all scrapers.

    Each scraper implementation will be a subclass of this class, implementing
    the scrape method to fetch model data from a specific model provider source.
    """

    @abc.abstractmethod
    def scrape(self) -> list[ProviderModelSpec]:
        """
        The core method for a scraper. It should fetch data and return it
        as a list of ProviderModelSpec objects.
        """
        raise NotImplementedError
