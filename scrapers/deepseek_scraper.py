import re
from sqlalchemy import table
from app import models
from app.models import Modality
from scrapers.base import BaseProviderModelScraper, ProviderModelSpec
from bs4 import BeautifulSoup
import requests


class DeepseekScraper(BaseProviderModelScraper):
    """An example scraper that returns hardcoded data for testing."""

    def scrape(self) -> list[ProviderModelSpec]:
        url = 'https://api-docs.deepseek.com/quick_start/pricing'
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        models = []
        matrix = []
        table = soup.find('table')  
        if table:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                matrix.append(cols)
            #scrape standard
            for i in range(1,3):

                model = ProviderModelSpec(
                    provider_name="Deepseek",
                    provider_api_key_name="DEEPSEEK_API_KEY",
                    provider_website=url,
                    model_name=self.get_name(matrix[0][i].text.strip()),
                    api_model_name=matrix[0][i].text.strip(),  
                    context_window=64000,
                    max_output_tokens=64000, 
                    # There are a lot of complexities with the pricing, at certain times there are discounts and there is a price difference between cache hit and cache miss. I have used standard cache hit pricing to fit current db structure. See detailed pricing info here: https://api-docs.deepseek.com/quick_start/pricing
                    input_cost_per_mtok=float(matrix[8][i].text.strip().replace('$', '')), 
                    output_cost_per_mtok=float(matrix[9][i].text.strip().replace('$', '')),
                    tokens_per_second=24, # based on https://artificialanalysis.ai/providers/deepseek
                    modalities=[Modality.TEXT],
                    supports_tools=True,
                    discount_start_time_utc = "16:30",
                    discount_end_time_utc = "00:30",
                    input_discount_price=self.get_price(matrix[11][i], matrix),
                    output_discount_price=self.get_price(matrix[12][i], matrix),
                )

                models.append(model)
        return models

    def get_name(self, api_name):
        return api_name.title().replace('-', ' ').replace('_', ' ')
    def get_price(self, price_text, mat):
        text=price_text.text.strip().replace('$', '')
        match = re.search(r'\d+\.\d+', text)
        if match:
            return float(match.group().replace('$', ''))
        return 0.0

