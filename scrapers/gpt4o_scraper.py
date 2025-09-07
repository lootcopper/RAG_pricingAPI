from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
import time
from scrapers.base import BaseProviderModelScraper, ProviderModelSpec
from app.models import Modality

class GPT4OScraper(BaseProviderModelScraper):
    def scrape(self) -> list[ProviderModelSpec]:
        # Set up Chrome options for headless browsing
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        driver = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.get("https://openai.com/api/pricing")

            
            # Wait for page to load
            wait = WebDriverWait(driver, 30)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Additional wait for dynamic content
            time.sleep(5)

            # SAVE PAGE SOURCE FOR DEBUGGING
            #with open("openai_pricing_page.html", "w", encoding="utf-8") as f:
                #f.write(driver.page_source)
            #print("Saved OpenAI pricing page to openai_pricing_page.html")

            # Look for pricing information in various ways
            models_data = []
            
            # Try to find GPT-4o and GPT-4o mini pricing
            gpt4o_data = self._extract_gpt4o_pricing(driver)
            gpt4o_mini_data = self._extract_gpt4o_mini_pricing(driver)
            
            if gpt4o_data:
                models_data.append(gpt4o_data)
            if gpt4o_mini_data:
                models_data.append(gpt4o_mini_data)
            
            if not models_data:
                print("Could not extract pricing from page, using fallback")
                return self._get_fallback_data()
            
            print(f"Successfully scraped {len(models_data)} models from OpenAI pricing page")
            return models_data
            
        except Exception as e:
            print(f"GPT-4o scraping failed: {e}")
            return self._get_fallback_data()
        finally:
            if driver:
                driver.quit()

    
    def _extract_gpt4o_pricing(self, driver) -> ProviderModelSpec:
        """Extract GPT-4o pricing including cached input pricing"""
        try:
            # Look for GPT-4o section
            page_source = driver.page_source.lower()
            
            # Find elements containing GPT-4o pricing
            elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'GPT-4o') or contains(text(), 'gpt-4o')]")
            
            input_cost = None
            cached_input_cost = None
            output_cost = None
            
            for element in elements:
                try:
                    # Get the parent container that might contain pricing info
                    parent = element.find_element(By.XPATH, "./ancestor::*[contains(@class, 'pricing') or contains(@class, 'table') or contains(@class, 'row')]")
                    text = parent.text.lower()
                    
                    # Look for pricing patterns
                    if "gpt-4o" in text and "mini" not in text:
                        # Extract input cost
                        input_match = re.search(r'(?:input.*?)?\$(\d+\.?\d*)\s*(?:/\s*1m|per\s*1m)', text)
                        if input_match:
                            input_cost = float(input_match.group(1))
                        
                        # Extract cached input cost
                        cached_match = re.search(r'(?:cached.*?input.*?)?\$(\d+\.?\d*)\s*(?:/\s*1m|per\s*1m)', text)
                        if cached_match:
                            cached_input_cost = float(cached_match.group(1))
                        
                        # Extract output cost
                        output_match = re.search(r'(?:output.*?)?\$(\d+\.?\d*)\s*(?:/\s*1m|per\s*1m)', text)
                        if output_match:
                            output_cost = float(output_match.group(1))
                        
                        if input_cost and output_cost:
                            break
                            
                except Exception:
                    continue
            
            # Fallback: try to find pricing in tables or structured elements
            if not input_cost or not output_cost:
                input_cost, cached_input_cost, output_cost = self._extract_from_structured_elements(driver, "gpt-4o", exclude_mini=True)
            
            if input_cost and output_cost:
                print(f"Found GPT-4o pricing - Input: ${input_cost}, Cached Input: ${cached_input_cost}, Output: ${output_cost}")
                return ProviderModelSpec(
                    provider_name="OpenAI",
                    provider_api_key_name="OPENAI_API_KEY",
                    provider_website="https://openai.com",
                    model_name="GPT-4o",
                    api_model_name="gpt-4o",
                    context_window=128000,
                    max_output_tokens=None,
                    input_cost_per_mtok=input_cost,
                    cached_input_cost_per_mtok=cached_input_cost,  # New field
                    output_cost_per_mtok=output_cost,
                    tokens_per_second=None,
                    modalities=[Modality.TEXT],
                    supports_tools=True,
                )
            
            return None
            
        except Exception as e:
            print(f"Error extracting GPT-4o pricing: {e}")
            return None
    
    def _extract_gpt4o_mini_pricing(self, driver) -> ProviderModelSpec:
        try:
            page_text = driver.page_source.lower()

            # Find all matches for GPT-4o mini pricing blocks
            pattern = r"gpt-4o mini\s*\$([0-9.]+)\s*/\s*1m input tokens\s*\$([0-9.]+)\s*/\s*1m cached input tokens\s*\$([0-9.]+)\s*/\s*1m output tokens"
            matches = re.findall(pattern, page_text)

            if matches:
                # Take the first match
                input_cost, cached_input_cost, output_cost = map(float, matches[0])
                print(f"Found GPT-4o mini pricing - Input: ${input_cost}, Cached Input: ${cached_input_cost}, Output: ${output_cost}")

                return ProviderModelSpec(
                    provider_name="OpenAI",
                    provider_api_key_name="OPENAI_API_KEY",
                    provider_website="https://openai.com",
                    model_name="GPT-4o mini",
                    api_model_name="gpt-4o-mini",
                    context_window=128000,
                    max_output_tokens=None,
                    input_cost_per_mtok=input_cost,
                    cached_input_cost_per_mtok=cached_input_cost,
                    output_cost_per_mtok=output_cost,
                    tokens_per_second=None,
                    modalities=[Modality.TEXT],
                    supports_tools=True,
                )
            else:
                print("GPT-4o mini pricing not found in page source")
                return None

        except Exception as e:
            print(f"Error extracting GPT-4o mini pricing: {e}")
            return None


    
    def _extract_from_structured_elements(self, driver, model_name, exclude_mini=False):
        """Try to extract pricing from tables or other structured elements"""
        input_cost = None
        cached_input_cost = None
        output_cost = None
        
        try:
            # Look for tables
            tables = driver.find_elements(By.TAG_NAME, "table")
            for table in tables:
                text = table.text.lower()
                if model_name.lower() in text:
                    if exclude_mini and "mini" in text and model_name.lower() != "gpt-4o mini":
                        continue
                    
                    # Try to extract prices from table structure
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        row_text = row.text.lower()
                        if model_name.lower() in row_text:
                            # Look for price cells
                            cells = row.find_elements(By.TAG_NAME, "td")
                            for i, cell in enumerate(cells):
                                cell_text = cell.text.strip()
                                if "$" in cell_text:
                                    price_match = re.search(r'\$(\d+\.?\d*)', cell_text)
                                    if price_match:
                                        price = float(price_match.group(1))
                                        
                                        # Try to determine what type of pricing this is based on context
                                        if "input" in cell_text.lower() and "cached" not in cell_text.lower():
                                            input_cost = price
                                        elif "cached" in cell_text.lower():
                                            cached_input_cost = price
                                        elif "output" in cell_text.lower():
                                            output_cost = price
                                        elif input_cost is None:
                                            input_cost = price
                                        elif output_cost is None:
                                            output_cost = price
            
        except Exception as e:
            print(f"Error in structured element extraction: {e}")
        
        return input_cost, cached_input_cost, output_cost
    
    def _get_fallback_data(self) -> list[ProviderModelSpec]:
        """Return fallback data with current known pricing"""
        print("Using fallback pricing data for OpenAI models")
        return [
            ProviderModelSpec(
                provider_name="OpenAI",
                provider_api_key_name="OPENAI_API_KEY",
                provider_website="https://openai.com",
                model_name="GPT-4o",
                api_model_name="gpt-4o",
                context_window=128000,
                max_output_tokens=None,
                input_cost_per_mtok=5.0,  # Updated fallback pricing
                cached_input_cost_per_mtok=2.5,  # Cached input pricing
                output_cost_per_mtok=20.0,
                tokens_per_second=None,
                modalities=[Modality.TEXT],
                supports_tools=True,
            ),
            ProviderModelSpec(
                provider_name="OpenAI",
                provider_api_key_name="OPENAI_API_KEY",
                provider_website="https://openai.com",
                model_name="GPT-4o mini",
                api_model_name="gpt-4o-mini",
                context_window=128000,
                max_output_tokens=None,
                input_cost_per_mtok=0.6,  # Updated fallback pricing
                cached_input_cost_per_mtok=0.3,  # Cached input pricing
                output_cost_per_mtok=2.4,
                tokens_per_second=None,
                modalities=[Modality.TEXT],
                supports_tools=True,
            )
        ]