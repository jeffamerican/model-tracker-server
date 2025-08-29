# Quick Start Guide for Agents

## 🚀 Get Running in 5 Minutes

### 1. Setup Environment
```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
# OR
source venv/bin/activate     # Linux/Mac

# Install dependencies
pip install -e .
```

### 2. Start the Service
```bash
# Development mode (auto-reload)
uvicorn pricing_service.server:app --host 0.0.0.0 --port 8001 --reload

# Production mode
python -m pricing_service.server
```

### 3. Test the Service
```bash
# Test API
curl http://localhost:8001/api/pricing

# Open UI in browser
# http://localhost:8001/ui/
```

## 📁 Key Files for Agents

| File | Purpose |
|------|---------|
| `agents.md` | Complete agent documentation |
| `API_REFERENCE.md` | Detailed API documentation |
| `SCRAPER_GUIDE.md` | How to create new scrapers |
| `src/pricing_service/server.py` | Main FastAPI server |
| `src/pricing_service/scraper.py` | Scraper orchestrator |
| `src/pricing_service/scrapers/` | Individual scraper modules |
| `ui/index.html` | Web interface |

## 🔧 Common Tasks

### Add a New Scraper
1. Create `src/pricing_service/scrapers/new_provider.py`
2. Implement `fetch_prices()` function
3. Add to `SCRAPER_MODULES` in `scraper.py`
4. Test with `python -m pricing_service.scraper`

### Test API Endpoints
```bash
# All pricing data
curl http://localhost:8001/api/pricing

# Specific model
curl http://localhost:8001/api/pricing/gpt-4

# Web UI
curl http://localhost:8001/ui/
```

### Debug Issues
```bash
# Check scraper output
python -m pricing_service.scraper

# Run with debug logging
uvicorn pricing_service.server:app --log-level debug

# Check data file
cat data/model_pricing.json
```

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| Port 8000 in use | Use `--port 8001` |
| Import errors | Activate virtual environment |
| 403 errors | Expected for some scrapers |
| Empty data | Scrapers may be blocked |

## 📚 Next Steps

1. **Read `agents.md`** - Complete documentation
2. **Check `API_REFERENCE.md`** - API details
3. **Review `SCRAPER_GUIDE.md`** - Add new providers
4. **Test with browser** - Visit `http://localhost:8001/ui/`

## 🆘 Need Help?

- Check the documentation files
- Look at existing scraper examples
- Test individual components
- Check server logs for errors
