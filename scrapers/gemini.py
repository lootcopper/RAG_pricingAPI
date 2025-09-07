import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

from scrapers.base import BaseProviderModelScraper, ProviderModelSpec
from app.models import Modality


class GeminiScraper(BaseProviderModelScraper):
    def __init__(self):
        super().__init__()
        self.provider_name = "Google AI"
        self.base_url = "https://ai.google.dev/pricing"  

    def scrape(self) -> List[ProviderModelSpec]:
        print(f"Scraping Gemini models from {self.base_url}")
        response = self._make_request_with_retry(self.base_url)
        if not response:
            return []

        soup = BeautifulSoup(response.content, 'html.parser')
        models = []

      
        models.extend(self._extract_from_sections(soup))


        unique_models = {}
        for model in models:
            model_name = model['model_name']
            if model_name not in unique_models:
                unique_models[model_name] = model

        return [self._to_provider_model_spec(model) for model in unique_models.values()]

    def _make_request_with_retry(self, url: str, retries: int = 3) -> Optional[requests.Response]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Connection": "keep-alive"
        }
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    return response
                else:
                    print(f"HTTP {response.status_code} on attempt {attempt + 1}")
            except requests.RequestException as e:
                print(f"Request failed on attempt {attempt + 1}: {e}")
                continue
        print(f"Failed to fetch data from {url} after {retries} attempts")
        return None

    def _extract_from_sections(self, soup: BeautifulSoup) -> List[Dict]:
        models = []
        pricing_sections = soup.find_all(['div', 'section', 'article', 'table', 'tbody', 'tr'])

        for section in pricing_sections:
            text_content = section.get_text(separator=' ', strip=True)
            if not text_content or len(text_content) < 10:
                continue

            if 'gemini' not in text_content.lower():
                continue

         
            gemini_patterns = [
                r'gemini[\s-]*(?:pro|ultra|nano|flash)?[\s-]*(?:\d+\.?\d*)?[a-z]*',
                r'gemini[\s-]*\d+\.?\d*[a-z]*',
                r'gemini[\s-]*(?:pro|ultra|nano|flash)'
            ]
            
            found_models = set()
            for pattern in gemini_patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    clean_name = self._clean_model_name(match)
                    if clean_name and clean_name not in found_models:
                        found_models.add(clean_name)
                        
                     
                        pricing_info = self._extract_pricing_from_text(text_content)
                        
                        models.append({
                            'model_name': clean_name,
                            'provider': self.provider_name,
                            'model_type': 'gemini',
                            'source_url': self.base_url,
                            'pricing_data': pricing_info
                        })

        return models

    def _clean_model_name(self, raw_name: str) -> Optional[str]:
        unwanted_phrases = [
            'This is some text inside of a div block.',
            'try it', 'ChatGemini', 'Chat', '→',
            'Which LLM to Use', 'Find the', 'right model',
            'use case', 'Models', 'See all models',
            'API', 'pricing', 'per million', 'tokens',
            'input', 'output', 'characters'
        ]
        
        cleaned = raw_name.strip()
        

        for phrase in unwanted_phrases:
            cleaned = cleaned.replace(phrase, '')
            

        cleaned = re.sub(r'[→\[\]{}()]+', '', cleaned)
        cleaned = re.sub(r'[^\w\s\.-]', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
     
        if 'gemini' in cleaned.lower():
            cleaned = re.sub(r'gemini', 'Gemini', cleaned, flags=re.IGNORECASE)
            
     
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        

        if (len(cleaned) < 3 or len(cleaned) > 50 or 
            not any(char.isalnum() for char in cleaned) or
            cleaned.lower() == 'gemini'):
            return None
            
        return cleaned

    def _extract_pricing_from_text(self, text: str) -> Dict:
        pricing = {}

   
        input_patterns = [
            r'input[^$]*\$(\d+\.?\d*)',
            r'(\d+\.?\d*)[^$]*input',
            r'input[^0-9]*(\d+\.?\d*)'
        ]
        
        output_patterns = [
            r'output[^$]*\$(\d+\.?\d*)',
            r'(\d+\.?\d*)[^$]*output',
            r'output[^0-9]*(\d+\.?\d*)'
        ]

        for pattern in input_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    pricing['input_price_per_1m_tokens'] = float(match.group(1))
                    break
                except ValueError:
                    continue

        for pattern in output_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    pricing['output_price_per_1m_tokens'] = float(match.group(1))
                    break
                except ValueError:
                    continue


        if not pricing:
            price = self._extract_price_from_text(text)
            if price:
                pricing['price_per_1m_tokens'] = price

        return pricing

    def _extract_price_from_text(self, text: str) -> Optional[float]:
        price_patterns = [
            r'\$(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*\$',
            r'USD\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*USD',
            r'(\d+\.?\d*)\s*per\s*million',
            r'(\d+\.?\d*)\s*per\s*1M',
            r'(\d+\.?\d*)\s*per\s*1000',
            r'(\d+\.?\d*)\s*per\s*1K',
            r'(\d+\.?\d*)\s*cents',
            r'(\d+\.?\d*)\s*¢'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    price = float(match.group(1))
              
                    if 'cents' in text.lower() or '¢' in text:
                        price /= 100
                
                    if 'per 1k' in text.lower() or 'per 1000' in text.lower():
                        price *= 1000
                    return price
                except ValueError:
                    continue
        return None

    def _to_provider_model_spec(self, model_data: Dict) -> ProviderModelSpec:
        pricing = model_data.get("pricing_data", {})
        return ProviderModelSpec(
            provider_name=self.provider_name,
            provider_api_key_name=None,
            provider_website=self.base_url,
            model_name=model_data["model_name"],
            api_model_name=model_data["model_name"].lower().replace(' ', '-'),
            context_window=1_000_000, 
            max_output_tokens=None,
            input_cost_per_mtok=pricing.get("input_price_per_1m_tokens", 0.0),
            output_cost_per_mtok=pricing.get("output_price_per_1m_tokens", 0.0),
            tokens_per_second=None,
            modalities=[Modality.TEXT],
            supports_tools=True
        )
