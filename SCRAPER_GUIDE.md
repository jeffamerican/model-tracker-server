# Scraper Development Guide

## Overview

This guide explains how to create, maintain, and troubleshoot scrapers for the pricing service. Scrapers are responsible for fetching pricing data from various AI model providers.

## Scraper Architecture

### Current Scrapers
- `openai.py` - Scrapes OpenAI pricing (currently blocked by 403)
- `fal.py` - Placeholder scraper for fal.ai

### Scraper Interface
All scrapers must implement the following interface and classify each entry with a `service_type` value (for example `api_endpoint`, `server_rental`, or `subscription`):

```python
def fetch_prices() -> dict:
    """
    Fetch pricing data from the provider.
    
    Returns:
        dict: Dictionary with model IDs as keys and pricing data as values.
              Format: {model_id: {"raw": data, "source": url, "service_type": str}}
    """
```

## Creating a New Scraper

### Step 1: Create the Scraper File

Create a new file in `src/pricing_service/scrapers/` with a descriptive name:

```python
"""Scraper for [Provider Name] pricing."""
from __future__ import annotations

import requests
from bs4 import BeautifulSoup
import json
from typing import Dict, Any

PROVIDER_URL = "https://provider.com/pricing"
PROVIDER_NAME = "Provider Name"

def fetch_prices() -> Dict[str, Dict[str, Any]]:
    """
    Fetch pricing data from [Provider Name].
    
    Returns:
        Dictionary with model pricing data.
    """
    data = {}
    
    try:
        # Fetch the pricing page
        response = requests.get(PROVIDER_URL, timeout=10)
        response.raise_for_status()
        
        # Parse the response (HTML, JSON, etc.)
        if response.headers.get('content-type', '').startswith('application/json'):
            # Handle JSON response
            pricing_data = response.json()
            data = parse_json_pricing(pricing_data)
        else:
            # Handle HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            data = parse_html_pricing(soup)
            
    except requests.RequestException as e:
        print(f"Network error fetching {PROVIDER_URL}: {e}")
    except Exception as e:
        print(f"Error parsing {PROVIDER_URL}: {e}")
    
    return data

def parse_html_pricing(soup: BeautifulSoup) -> Dict[str, Dict[str, Any]]:
    """Parse HTML pricing data."""
    data = {}
    
    # Example: Find pricing tables
    tables = soup.find_all('table')
    for table in tables:
        # Extract model information from table
        rows = table.find_all('tr')
        for row in rows[1:]:  # Skip header row
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 3:
                model_name = cells[0].get_text(strip=True)
                input_price = cells[1].get_text(strip=True)
                output_price = cells[2].get_text(strip=True)
                
                data[model_name] = {
                    "raw": {
                        "Model": model_name,
                        "Input": input_price,
                        "Output": output_price,
                    },
                    "source": PROVIDER_URL
                }
    
    return data

def parse_json_pricing(json_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Parse JSON pricing data."""
    data = {}
    
    # Example: Extract from JSON structure
    models = json_data.get('models', [])
    for model in models:
        model_id = model.get('id')
        if model_id:
            data[model_id] = {
                "raw": model,
                "source": PROVIDER_URL
            }
    
    return data
```

### Step 2: Register the Scraper

Add your new scraper to the `SCRAPER_MODULES` list in `src/pricing_service/scraper.py`:

```python
SCRAPER_MODULES: Iterable[str] = [
    "pricing_service.scrapers.openai",
    "pricing_service.scrapers.fal",
    "pricing_service.scrapers.your_new_scraper",  # Add this line
]
```

### Step 3: Test the Scraper

Test your scraper individually:

```python
# Create a test script
from pricing_service.scrapers.your_new_scraper import fetch_prices

data = fetch_prices()
print(json.dumps(data, indent=2))
```

## Common Scraping Patterns

### 1. HTML Table Scraping
```python
def scrape_table_pricing(soup: BeautifulSoup) -> Dict[str, Dict[str, Any]]:
    """Scrape pricing from HTML tables."""
    data = {}
    
    # Find pricing tables
    tables = soup.find_all('table', class_='pricing-table')
    
    for table in tables:
        headers = []
        header_row = table.find('thead').find('tr')
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
        
        # Process data rows
        for row in table.find('tbody').find_all('tr'):
            cells = row.find_all('td')
            if len(cells) == len(headers):
                row_data = dict(zip(headers, [cell.get_text(strip=True) for cell in cells]))
                model_id = row_data.get('Model', '').lower().replace(' ', '-')
                if model_id:
                    data[model_id] = {
                        "raw": row_data,
                        "source": PROVIDER_URL
                    }
    
    return data
```

### 2. JSON API Scraping
```python
def scrape_json_pricing(api_url: str) -> Dict[str, Dict[str, Any]]:
    """Scrape pricing from JSON API."""
    data = {}
    
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        
        pricing_data = response.json()
        
        # Navigate JSON structure
        models = pricing_data.get('data', {}).get('models', [])
        
        for model in models:
            model_id = model.get('id')
            if model_id:
                data[model_id] = {
                    "raw": {
                        "Model": model.get('name'),
                        "Input": model.get('input_price'),
                        "Output": model.get('output_price'),
                        "Context": model.get('context_window'),
                    },
                    "source": api_url
                }
    
    except Exception as e:
        print(f"Error scraping JSON API: {e}")
    
    return data
```

### 3. Dynamic Content Scraping
```python
def scrape_dynamic_pricing(url: str) -> Dict[str, Dict[str, Any]]:
    """Scrape pricing from JavaScript-rendered content."""
    data = {}
    
    try:
        # Use selenium for JavaScript-rendered content
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        
        # Wait for content to load
        import time
        time.sleep(5)
        
        # Extract pricing data
        elements = driver.find_elements_by_css_selector('.pricing-card')
        
        for element in elements:
            model_name = element.find_element_by_css_selector('.model-name').text
            input_price = element.find_element_by_css_selector('.input-price').text
            output_price = element.find_element_by_css_selector('.output-price').text
            
            data[model_name.lower().replace(' ', '-')] = {
                "raw": {
                    "Model": model_name,
                    "Input": input_price,
                    "Output": output_price,
                },
                "source": url
            }
        
        driver.quit()
    
    except Exception as e:
        print(f"Error scraping dynamic content: {e}")
    
    return data
```

## Error Handling Best Practices

### 1. Network Errors
```python
def robust_fetch(url: str) -> requests.Response:
    """Robust HTTP fetching with retries."""
    import time
    
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
```

### 2. Parsing Errors
```python
def safe_parse_text(element) -> str:
    """Safely extract text from HTML element."""
    try:
        return element.get_text(strip=True) if element else ""
    except Exception:
        return ""

def safe_parse_json(text: str) -> Dict[str, Any]:
    """Safely parse JSON text."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}
```

### 3. Data Validation
```python
def validate_pricing_data(data: Dict[str, Any]) -> bool:
    """Validate pricing data structure."""
    required_fields = ['Model', 'Input', 'Output']
    
    for model_id, model_data in data.items():
        raw_data = model_data.get('raw', {})
        source = model_data.get('source')
        
        if not source:
            print(f"Missing source for {model_id}")
            return False
        
        for field in required_fields:
            if field not in raw_data:
                print(f"Missing {field} for {model_id}")
                return False
    
    return True
```

## Testing Scrapers

### 1. Unit Testing
```python
import unittest
from unittest.mock import patch, Mock
from pricing_service.scrapers.your_scraper import fetch_prices

class TestYourScraper(unittest.TestCase):
    
    @patch('requests.get')
    def test_fetch_prices_success(self, mock_get):
        # Mock successful response
        mock_response = Mock()
        mock_response.text = '<html><table>...</table></html>'
        mock_response.headers = {'content-type': 'text/html'}
        mock_get.return_value = mock_response
        
        result = fetch_prices()
        self.assertIsInstance(result, dict)
    
    @patch('requests.get')
    def test_fetch_prices_network_error(self, mock_get):
        # Mock network error
        mock_get.side_effect = requests.RequestException("Network error")
        
        result = fetch_prices()
        self.assertEqual(result, {})
```

### 2. Integration Testing
```python
def test_scraper_integration():
    """Test scraper with real data."""
    from pricing_service.scrapers.your_scraper import fetch_prices
    
    data = fetch_prices()
    
    # Verify data structure
    assert isinstance(data, dict)
    
    for model_id, model_data in data.items():
        assert 'raw' in model_data
        assert 'source' in model_data
        assert isinstance(model_data['raw'], dict)
        assert isinstance(model_data['source'], str)
```

## Troubleshooting Common Issues

### 1. 403 Forbidden Errors
**Problem**: Website blocks automated requests.

**Solutions**:
- Add user-agent headers
- Use rotating IP addresses
- Implement delays between requests
- Check if API endpoints are available

```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
response = requests.get(url, headers=headers, timeout=10)
```

### 2. Rate Limiting
**Problem**: Too many requests too quickly.

**Solutions**:
- Add delays between requests
- Implement exponential backoff
- Use session objects for connection pooling

```python
import time

def fetch_with_delay(url: str, delay: float = 1.0):
    time.sleep(delay)
    return requests.get(url, timeout=10)
```

### 3. HTML Structure Changes
**Problem**: Website layout changes break scrapers.

**Solutions**:
- Use multiple CSS selectors
- Implement fallback parsing strategies
- Add comprehensive error logging
- Regular monitoring and updates

```python
def robust_element_find(soup: BeautifulSoup, selectors: List[str]):
    """Try multiple selectors to find element."""
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            return element
    return None
```

### 4. Missing Dependencies
**Problem**: Scraper requires additional packages.

**Solutions**:
- Add dependencies to `pyproject.toml`
- Use try/except for optional dependencies
- Document requirements clearly

```python
try:
    from selenium import webdriver
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Selenium not available, using fallback method")
```

## Monitoring and Maintenance

### 1. Logging
```python
import logging

logger = logging.getLogger(__name__)

def fetch_prices() -> Dict[str, Dict[str, Any]]:
    logger.info(f"Starting scrape for {PROVIDER_NAME}")
    
    try:
        # ... scraping logic ...
        logger.info(f"Successfully scraped {len(data)} models")
        return data
    except Exception as e:
        logger.error(f"Failed to scrape {PROVIDER_NAME}: {e}")
        return {}
```

### 2. Health Checks
```python
def health_check() -> bool:
    """Check if scraper is working."""
    try:
        data = fetch_prices()
        return len(data) > 0
    except Exception:
        return False
```

### 3. Data Validation
```python
def validate_scraper_output(data: Dict[str, Dict[str, Any]]) -> List[str]:
    """Validate scraper output and return issues."""
    issues = []
    
    if not data:
        issues.append("No data returned")
        return issues
    
    for model_id, model_data in data.items():
        if 'raw' not in model_data:
            issues.append(f"Missing 'raw' data for {model_id}")
        if 'source' not in model_data:
            issues.append(f"Missing 'source' for {model_id}")
    
    return issues
```

## Best Practices

1. **Be Respectful**: Add delays between requests
2. **Handle Errors**: Implement comprehensive error handling
3. **Validate Data**: Check data structure and content
4. **Log Everything**: Use proper logging for debugging
5. **Test Thoroughly**: Unit and integration tests
6. **Document Changes**: Update documentation when modifying scrapers
7. **Monitor Performance**: Track success rates and response times
8. **Plan for Failures**: Implement fallback strategies
