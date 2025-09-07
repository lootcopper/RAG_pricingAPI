import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import re

from app.models import Modality
from scrapers.base import BaseProviderModelScraper, ProviderModelSpec


class AWSBedrockAnthropicScraper(BaseProviderModelScraper):
    
    def scrape(self) -> list[ProviderModelSpec]:
        url = "https://aws.amazon.com/bedrock/pricing/"
        
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
        
        driver = None
        try:
            service = ChromeService()
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(url)

            wait = WebDriverWait(driver, 15)
            
            close_button_selectors = [
                "button[aria-label='Close']",
                "button[data-testid='close-button']", 
                ".modal button[type='button']",
                "//button[contains(@aria-label, 'Close') or contains(@aria-label, 'close')]",
                "//button[text()='×' or text()='✕' or text()='X']",
                "//button[contains(@class, 'close')]"
            ]
            
            popup_closed = False
            for selector in close_button_selectors:
                try:
                    if selector.startswith("//"):
                        close_button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, selector)))
                    else:
                        close_button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    
                    close_button.click()
                    popup_closed = True
                    time.sleep(3)
                    break
                except TimeoutException:
                    continue
                except Exception as e:
                    continue

            # Wait for page to fully load
            time.sleep(5)

            # Find the Anthropic tab
            wait = WebDriverWait(driver, 20)
            anthropic_tab = None
            
            selectors = [
                "//li[contains(@class, 'lb-tabs-trigger') and .//text()[contains(., 'Anthropic')]]",
                "li[role='tab'][aria-controls*='panel-3']",
                "//li[@role='tab']//div[contains(text(), 'Anthropic')]/.."
            ]
            
            for selector in selectors:
                try:
                    if selector.startswith("//"):
                        anthropic_tab = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    else:
                        anthropic_tab = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    break
                except TimeoutException:
                    continue
            
            if not anthropic_tab:
                return []

            driver.execute_script("arguments[0].click();", anthropic_tab)
            
            time.sleep(8)
            
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Claude 3.5') or contains(text(), 'Claude Opus')]")))
            except TimeoutException:
                pass
            
            time.sleep(5)

            page_source = driver.page_source
            
        except Exception:
            return []
        finally:
            if driver:
                driver.quit()

        return self._extract_pricing_data(page_source)
    
    def _extract_pricing_data(self, page_source):
        soup = BeautifulSoup(page_source, 'html.parser')
        models = []
        
        all_tables = soup.find_all('table')
        
        for table in all_tables:
            table_text = table.get_text()
            if not any(model in table_text for model in ['Claude 3.5', 'Claude Opus', 'Claude Sonnet 4', 'Claude 3.7']):
                continue
                
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue
                
            header_row = rows[0]
            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]
            
            model_col = -1
            input_price_col = -1
            output_price_col = -1
            
            for i, header in enumerate(headers):
                if 'anthropic' in header and 'models' in header:
                    model_col = i
                elif 'price per 1,000 input tokens' in header and 'batch' not in header and 'cache' not in header:
                    input_price_col = i
                elif 'price per 1,000 output tokens' in header and 'batch' not in header and 'cache' not in header:
                    output_price_col = i
            
            if model_col == -1 or input_price_col == -1 or output_price_col == -1:
                continue
                
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) <= max(model_col, input_price_col, output_price_col):
                    continue
                    
                model_name = cells[model_col].get_text(strip=True)
                input_price_text = cells[input_price_col].get_text(strip=True)
                output_price_text = cells[output_price_col].get_text(strip=True)
                
                if not model_name or 'claude' not in model_name.lower():
                    continue
                    
                input_cost = self._extract_price(input_price_text)
                output_cost = self._extract_price(output_price_text)
                
                if input_cost is not None and output_cost is not None:
                    input_cost_per_mtok = input_cost * 1000
                    output_cost_per_mtok = output_cost * 1000
                    
                    api_model_name = self._convert_to_api_name(model_name)
                    context_window = self._estimate_context_window(model_name)
                    max_output_tokens = self._estimate_max_output_tokens(model_name)
                    
                    models.append(ProviderModelSpec(
                        provider_name="AWS Bedrock (Anthropic)",
                        provider_api_key_name="AWS_ACCESS_KEY_ID",
                        provider_website="https://aws.amazon.com/bedrock/",
                        model_name=model_name,
                        api_model_name=api_model_name,
                        context_window=context_window,
                        max_output_tokens=max_output_tokens,
                        input_cost_per_mtok=input_cost_per_mtok,
                        output_cost_per_mtok=output_cost_per_mtok,
                        tokens_per_second=None,
                        modalities=[Modality.TEXT],
                        supports_tools=True,
                    ))
        
        return models
    
    def _extract_price(self, price_text: str) -> float | None:
        if 'n/a' in price_text.lower() or not price_text.strip():
            return None
            
        price_match = re.search(r'\$(\d+(?:\.\d+)?)', price_text)
        if price_match:
            return float(price_match.group(1))
        return None
    
    def _convert_to_api_name(self, model_name: str) -> str:
        name_map = {
            'Claude Opus 4': 'anthropic.claude-3-opus-20240229-v1:0',
            'Claude Sonnet 4': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
            'Claude 3.7 Sonnet': 'anthropic.claude-3-sonnet-20240229-v1:0',
            'Claude 3.5 Sonnet': 'anthropic.claude-3-5-sonnet-20240229-v1:0',
            'Claude 3.5 Sonnet v2': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
            'Claude 3.5 Haiku': 'anthropic.claude-3-5-haiku-20241022-v1:0',
            'Claude 3 Opus': 'anthropic.claude-3-opus-20240229-v1:0',
            'Claude 3 Sonnet': 'anthropic.claude-3-sonnet-20240229-v1:0',
            'Claude 3 Haiku': 'anthropic.claude-3-haiku-20240307-v1:0',
        }
        return name_map.get(model_name, f"anthropic.{model_name.lower().replace(' ', '-')}")
    
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