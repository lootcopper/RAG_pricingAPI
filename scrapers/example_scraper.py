from app.models import Modality
from scrapers.base import BaseProviderModelScraper, ProviderModelSpec


class ExampleScraper(BaseProviderModelScraper):
    """An example scraper that returns hardcoded data for testing."""

    def scrape(self) -> list[ProviderModelSpec]:
        """Returns a list of dummy model data."""
        return [
            ProviderModelSpec(
                provider_name="ExampleProvider",
                provider_api_key_name=None,
                provider_website="https://example.com",
                model_name="ExampleModel-1",
                api_model_name="example/model-1",
                context_window=8000,
                max_output_tokens=4096,
                input_cost_per_mtok=0.50,
                output_cost_per_mtok=1.50,
                tokens_per_second=150,
                modalities=[Modality.TEXT, Modality.IMAGE],
                supports_tools=False,
                discount_start_time_utc = "00:00",
                discount_end_time_utc = "00:00",
                input_discount_price=0.0,
                output_discount_price=0.0,
            ),
            ProviderModelSpec(
                provider_name="ExampleProvider",
                provider_api_key_name=None,
                provider_website="https://example.com",
                model_name="ExampleModel-2-Large",
                api_model_name="example/model-2-large-context",
                context_window=128000,
                max_output_tokens=8192,
                input_cost_per_mtok=3.00,
                output_cost_per_mtok=6.00,
                tokens_per_second=100,
                modalities=[Modality.TEXT, Modality.IMAGE],
                supports_tools=True,
            ),
        ]