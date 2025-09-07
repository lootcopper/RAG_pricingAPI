import requests
from bs4 import BeautifulSoup
import re

from app.models import Modality
from scrapers.base import BaseProviderModelScraper, ProviderModelSpec


class AnthropicScraper(BaseProviderModelScraper):
    
    def scrape(self) -> list[ProviderModelSpec]:
        url = "https://www.anthropic.com/pricing#api"
        
        response = requests.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        all_text = soup.get_text()
        
        models = []
        
        pricing_pattern = r'(Claude (?:Opus|Sonnet|Haiku) [0-9.]+(?:[^I]{0,50}?)??)Input\$(\d+(?:\.\d+)?) / MTokOutput\$(\d+(?:\.\d+)?) / MTok'
        
        matches = re.findall(pricing_pattern, all_text)
        
        for match in matches:
            raw_model_name, input_price, output_price = match
            
            model_name = self._clean_model_name(raw_model_name)
            
            if not model_name or 'caching' in model_name.lower():
                continue
                
            input_cost = float(input_price)
            output_cost = float(output_price)
            
            api_model_name = self._convert_to_api_name(model_name)
            context_window = self._estimate_context_window(model_name)
            max_output_tokens = self._estimate_max_output_tokens(model_name)
            
            models.append(ProviderModelSpec(
                provider_name="Anthropic",
                provider_api_key_name="ANTHROPIC_API_KEY",
                provider_website="https://www.anthropic.com",
                model_name=model_name,
                api_model_name=api_model_name,
                context_window=context_window,
                max_output_tokens=max_output_tokens,
                input_cost_per_mtok=input_cost,
                output_cost_per_mtok=output_cost,
                tokens_per_second=None,
                modalities=[Modality.TEXT],
                supports_tools=True,
            ))
        
        return models
    
    def _clean_model_name(self, raw_name: str) -> str:
        # Extract just the Claude model name part
        claude_pattern = r'(Claude (?:Opus|Sonnet|Haiku) [0-9.]+)'
        match = re.search(claude_pattern, raw_name)
        if match:
            return match.group(1)
        return raw_name.strip()
    
    def _convert_to_api_name(self, model_name: str) -> str:
        name_lower = model_name.lower()
        
        if 'claude 3.5 sonnet' in name_lower:
            return 'claude-3-5-sonnet-20241022'
        elif 'claude 3.5 haiku' in name_lower:
            return 'claude-3-5-haiku-20241022'
        elif 'claude 3 opus' in name_lower:
            return 'claude-3-opus-20240229'
        elif 'claude 3 sonnet' in name_lower:
            return 'claude-3-sonnet-20240229'
        elif 'claude 3 haiku' in name_lower:
            return 'claude-3-haiku-20240307'
        elif 'opus 4' in name_lower:
            return 'claude-3-opus-20240229'
        elif 'sonnet 4' in name_lower:
            return 'claude-3-5-sonnet-20241022'
        elif 'haiku 3.5' in name_lower:
            return 'claude-3-5-haiku-20241022'
        elif 'sonnet 3.7' in name_lower:
            return 'claude-3-sonnet-20240229'
        else:
            return model_name.lower().replace(' ', '-')
    
    def _estimate_context_window(self, model_name: str) -> int:
        name_lower = model_name.lower()
        
        if 'opus' in name_lower or 'sonnet' in name_lower or 'haiku' in name_lower:
            return 200000
        else:
            return 100000
    
    def _estimate_max_output_tokens(self, model_name: str) -> int:
        name_lower = model_name.lower()
        
        if 'opus' in name_lower or 'sonnet' in name_lower or 'haiku' in name_lower:
            return 8192
        else:
            return 4096 