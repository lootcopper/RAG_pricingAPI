from sqlalchemy import table
from app.models import Modality
from scrapers.base import BaseProviderModelScraper, ProviderModelSpec
from bs4 import BeautifulSoup
import requests


class PerplexityScraper(BaseProviderModelScraper):
    """An example scraper that returns hardcoded data for testing."""

    def scrape(self) -> list[ProviderModelSpec]:
        url = 'https://docs.perplexity.ai/getting-started/pricing'
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        models = []

        table = soup.find('table')  
        if table:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if (cols):
                    model_name=cols[0].text.strip()
                    model = (
                        ProviderModelSpec(
                            provider_name="Perplexity",
                            provider_api_key_name="SONAR_API_KEY",
                            provider_website=url,
                            model_name=model_name,
                            api_model_name=self.get_api_name(model_name),  
                            context_window=self.get_context_window(model_name),
                            max_output_tokens=8000, # not explicity stated anwhere for each model, except for sonar pro which is 8000
                            input_cost_per_mtok=float(cols[1].text.strip().replace('$', '')),
                            output_cost_per_mtok=float(cols[2].text.strip().replace('$', '')),
                            tokens_per_second=self.get_tokens_per_sec(model_name),
                            modalities=[Modality.TEXT],
                            supports_tools=False,

                        )
                    )
                    models.append(model)
        return models

    def get_api_name(self, model_name):
        if 'r1' in model_name.lower():
            return 'r1-1776'
        return model_name.lower().replace(' ', '-').replace('_', '-')
    
    def get_context_window(self, model_name):
        if model_name == "Sonar Pro" :
            return 200000
        else:
            return 128000
        
    def get_tokens_per_sec(self, model_name): #based on https://artificialanalysis.ai/providers/perplexity
        if model_name == "Sonar Pro":
            return 141
        if model_name == "Sonar":
            return 96
        if model_name == "Sonar Pro":
            return 85
        else:
            return 85 # no data available for other models, so assuming 85

