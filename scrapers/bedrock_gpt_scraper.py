from scrapers.base import BaseProviderModelScraper, ProviderModelSpec
from app.models import Modality
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging

logger = logging.getLogger(__name__)

class BedrockGPTScraper(BaseProviderModelScraper):
    def scrape(self) -> list[ProviderModelSpec]:
        specs = []

        try:
            # Configure headless Chrome
            options = Options()
            options.add_argument('--headless=new')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            driver = webdriver.Chrome(options=options)

            # Try the direct AWS pricing page first
            pricing_urls = [
                "https://aws.amazon.com/bedrock/pricing/",
                "https://docs.aws.amazon.com/bedrock/latest/userguide/model-pricing.html"
            ]

            for url in pricing_urls:
                logger.info(f"Trying URL: {url}")
                try:
                    driver.get(url)
                    wait = WebDriverWait(driver, 20)
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    time.sleep(3)

                    # DEBUG: Print page title and check for Nova content
                    page_title = driver.title
                    logger.info(f"Page title: {page_title}")
                    
                    page_source = driver.page_source.lower()
                    if "nova" in page_source:
                        logger.info("Found 'nova' in page source!")
                        
                        # Look for Amazon Nova pricing directly
                        nova_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Nova') or contains(text(), 'nova')]")
                        logger.info(f"Found {len(nova_elements)} elements containing 'Nova'")
                        
                        # Try to find pricing tables
                        tables = driver.find_elements(By.TAG_NAME, "table")
                        logger.info(f"Found {len(tables)} tables on the page")
                        
                        for i, table in enumerate(tables):
                            table_text = table.text.lower()
                            if "nova" in table_text:
                                logger.info(f"Table {i} contains Nova pricing:")
                                logger.info(f"Table content preview: {table.text[:500]}...")
                                
                                # Extract Nova pricing from this table
                                specs.extend(self._extract_nova_from_table(table))
                                break
                        
                        if specs:
                            break
                    else:
                        logger.info("No 'nova' found in page source")
                        
                        # DEBUG: Print first 1000 chars of page
                        logger.info(f"Page content preview: {page_source[:1000]}...")

                except Exception as e:
                    logger.error(f"Error with URL {url}: {e}")
                    continue

            # If we found specs, return them
            if specs:
                logger.info(f"Successfully extracted {len(specs)} Nova models")
                driver.quit()
                return specs

            # Fallback: If no live scraping works, return fallback data
            logger.info("No live pricing found, returning fallback data")
            driver.quit()
            return self._get_fallback_data()

        except Exception as e:
            logger.error(f"Failed to scrape Amazon Bedrock pricing: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._get_fallback_data()

    def _extract_nova_from_table(self, table):
        """Extract Nova pricing from a table element"""
        specs = []
        try:
            # Get all rows
            rows = table.find_elements(By.TAG_NAME, "tr")
            logger.info(f"Table has {len(rows)} rows")
            
            # Print header for debugging
            if rows:
                header_cells = rows[0].find_elements(By.TAG_NAME, "th")
                if not header_cells:
                    header_cells = rows[0].find_elements(By.TAG_NAME, "td")
                
                headers = [cell.text.strip() for cell in header_cells]
                logger.info(f"Table headers: {headers}")

            # Process data rows
            for i, row in enumerate(rows[1:], 1):  # Skip header
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 3:
                    continue
                
                cell_texts = [cell.text.strip() for cell in cells]
                logger.info(f"Row {i}: {cell_texts}")
                
                # Look for Nova models
                model_name = cell_texts[0] if cell_texts else ""
                if "nova" in model_name.lower():
                    logger.info(f"Found Nova model: {model_name}")
                    
                    # Try to extract pricing (adjust indices based on actual table structure)
                    input_cost = self._parse_price(cell_texts[1] if len(cell_texts) > 1 else "")
                    cached_input_cost = self._parse_price(cell_texts[2] if len(cell_texts) > 2 else "")
                    output_cost = self._parse_price(cell_texts[3] if len(cell_texts) > 3 else "")
                    
                    if input_cost and output_cost:
                        spec = self._create_nova_spec(model_name, input_cost, cached_input_cost, output_cost)
                        if spec:
                            specs.append(spec)
                            logger.info(f"Created spec for {model_name}")

        except Exception as e:
            logger.error(f"Error extracting from table: {e}")
            
        return specs

    def _parse_price(self, text):
        """Parse price from text"""
        try:
            if not text or text.lower() in ['n/a', 'null', '']:
                return None
            
            import re
            # Look for price patterns
            match = re.search(r'\$?(\d+\.?\d*)', text.replace(',', ''))
            if match:
                return float(match.group(1))
        except:
            pass
        return None

    def _create_nova_spec(self, model_name, input_cost, cached_input_cost, output_cost):
        """Create a ProviderModelSpec for a Nova model"""
        try:
            # Convert from per-1k to per-1M tokens
            input_cost_per_mtok = input_cost * 1000
            output_cost_per_mtok = output_cost * 1000
            cached_input_cost_per_mtok = cached_input_cost * 1000 if cached_input_cost else None

            api_model_name = model_name.replace(" ", "_").lower().replace("amazon_", "")

            # Set context window and max output based on model type
            if "micro" in model_name.lower():
                context_window = 128000
                max_output_tokens = 4096
            elif "lite" in model_name.lower():
                context_window = 128000
                max_output_tokens = 4096
            elif "pro" in model_name.lower():
                context_window = 300000
                max_output_tokens = 5000
            elif "premier" in model_name.lower():
                context_window = 300000
                max_output_tokens = 5000
            else:
                context_window = 128000
                max_output_tokens = 4096

            return ProviderModelSpec(
                provider_name="Amazon Bedrock",
                provider_api_key_name="AWS_ACCESS_KEY_ID",
                provider_website="https://aws.amazon.com/bedrock/",
                model_name=model_name,
                api_model_name=api_model_name,
                context_window=context_window,
                max_output_tokens=max_output_tokens,
                input_cost_per_mtok=input_cost_per_mtok,
                cached_input_cost_per_mtok=cached_input_cost_per_mtok,
                output_cost_per_mtok=output_cost_per_mtok,
                tokens_per_second=None,
                modalities=[Modality.TEXT],
                supports_tools=True if "pro" in model_name.lower() or "premier" in model_name.lower() else False,
            )
        except Exception as e:
            logger.error(f"Error creating spec for {model_name}: {e}")
            return None

    def _get_fallback_data(self) -> list[ProviderModelSpec]:
        """Return fallback Amazon Nova pricing data"""
        logger.info("Using fallback pricing data for Amazon Nova models")
        return [
            ProviderModelSpec(
                provider_name="Amazon Bedrock",
                provider_api_key_name="AWS_ACCESS_KEY_ID",
                provider_website="https://aws.amazon.com/bedrock/",
                model_name="Amazon Nova Micro",
                api_model_name="nova_micro",
                context_window=128000,
                max_output_tokens=4096,
                input_cost_per_mtok=0.035,  # $0.000035 * 1000
                cached_input_cost_per_mtok=0.00875,  # $0.0000875 * 1000
                output_cost_per_mtok=0.14,  # $0.00014 * 1000
                tokens_per_second=None,
                modalities=[Modality.TEXT],
                supports_tools=False,
            ),
            ProviderModelSpec(
                provider_name="Amazon Bedrock",
                provider_api_key_name="AWS_ACCESS_KEY_ID",
                provider_website="https://aws.amazon.com/bedrock/",
                model_name="Amazon Nova Lite",
                api_model_name="nova_lite",
                context_window=128000,
                max_output_tokens=4096,
                input_cost_per_mtok=0.06,  # $0.00006 * 1000
                cached_input_cost_per_mtok=0.15,  # $0.00015 * 1000
                output_cost_per_mtok=0.24,  # $0.00024 * 1000
                tokens_per_second=None,
                modalities=[Modality.TEXT],
                supports_tools=False,
            ),
            ProviderModelSpec(
                provider_name="Amazon Bedrock",
                provider_api_key_name="AWS_ACCESS_KEY_ID",
                provider_website="https://aws.amazon.com/bedrock/",
                model_name="Amazon Nova Pro",
                api_model_name="nova_pro",
                context_window=300000,
                max_output_tokens=5000,
                input_cost_per_mtok=0.8,  # $0.0008 * 1000
                cached_input_cost_per_mtok=0.2,  # $0.0002 * 1000
                output_cost_per_mtok=3.2,  # $0.0032 * 1000
                tokens_per_second=None,
                modalities=[Modality.TEXT],
                supports_tools=True,
            ),
            ProviderModelSpec(
                provider_name="Amazon Bedrock",
                provider_api_key_name="AWS_ACCESS_KEY_ID",
                provider_website="https://aws.amazon.com/bedrock/",
                model_name="Amazon Nova Premier",
                api_model_name="nova_premier",
                context_window=300000,
                max_output_tokens=5000,
                input_cost_per_mtok=2.5,  # $0.0025 * 1000
                cached_input_cost_per_mtok=0.625,  # $0.000625 * 1000
                output_cost_per_mtok=12.5,  # $0.0125 * 1000
                tokens_per_second=None,
                modalities=[Modality.TEXT],
                supports_tools=True,
            ),
        ]