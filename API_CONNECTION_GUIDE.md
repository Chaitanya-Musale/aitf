# API Connection Quick Reference 🔑

## Get Your Gemini API Key

1. Visit: **https://makersuite.google.com/app/apikey**
2. Click: **"Get API Key"** or **"Create API Key"**
3. Copy your key (looks like: `AIzaSy...`)

## Test Your API Key

Run this quick test:

```bash
python << 'EOF'
import google.generativeai as genai

# REPLACE WITH YOUR ACTUAL KEY
API_KEY = "AIzaSy_YOUR_KEY_HERE"

try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    response = model.generate_content("Say OK")
    print(f"✅ SUCCESS! API is working")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ FAILED: {e}")
    print("\nTroubleshooting:")
    print("1. Check your API key is correct")
    print("2. Try model: 'gemini-1.5-flash' instead")
    print("3. Check internet connection")
    print("4. Verify API quota at: https://console.cloud.google.com/")
EOF
```

## Common Errors & Solutions

### Error 1: "API key is required"
```
❌ Please enter a valid API key
```

**Solution:**
- Make sure you pasted the full API key
- No extra spaces before/after
- Click "Initialize Session" button

---

### Error 2: "Failed to connect to Gemini API"
```
❌ Failed to connect to Gemini API
```

**Causes & Solutions:**

#### Cause A: Model not available
The app uses `gemini-2.0-flash-exp` which may not be available in your region.

**Solution:** Edit `gemini_client.py` line 54:
```python
# Change from:
model_name: str = 'gemini-2.0-flash-exp'

# To:
model_name: str = 'gemini-1.5-flash'
```

#### Cause B: Invalid API key
**Solution:**
- Get a new API key from https://makersuite.google.com/app/apikey
- Make sure you copied the entire key

#### Cause C: No internet connection
**Solution:**
```bash
# Test internet
ping google.com

# Test API endpoint
curl https://generativelanguage.googleapis.com/
```

---

### Error 3: "Rate limit exceeded"
```
429 Quota exceeded
```

**Solution:**
- Wait 60 seconds and try again
- Check your quota: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas
- Free tier limits:
  - 60 requests per minute
  - 1,500 requests per day

---

### Error 4: "Module not found"
```
ImportError: No module named 'google.generativeai'
```

**Solution:**
```bash
pip install google-generativeai
# or
pip install -r requirements.txt
```

---

### Error 5: "Invalid model name"
```
404 Model not found
```

**Available models:**
- `gemini-2.0-flash-exp` (experimental, fastest)
- `gemini-1.5-flash` (stable, fast)
- `gemini-1.5-pro` (stable, best quality)

**Solution:** Change model in `gemini_client.py`:
```python
def __init__(self,
             api_key: str,
             model_name: str = 'gemini-1.5-flash',  # Change here
             ...
```

---

## Step-by-Step API Setup

### Step 1: Install Dependencies
```bash
cd /home/user/aitf
pip install -r requirements.txt
```

### Step 2: Get API Key
```bash
# Open in browser:
# https://makersuite.google.com/app/apikey

# Or using xdg-open:
xdg-open https://makersuite.google.com/app/apikey
```

### Step 3: Test API Key
```bash
# Save this to test_api.py
cat > test_api.py << 'EOF'
import google.generativeai as genai

API_KEY = input("Enter your API key: ")

try:
    genai.configure(api_key=API_KEY)

    # Try experimental model first
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content("Say OK")
        print(f"✅ gemini-2.0-flash-exp works!")
    except:
        print("⚠️ gemini-2.0-flash-exp not available, trying fallback...")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Say OK")
        print(f"✅ gemini-1.5-flash works!")

    print(f"Response: {response.text}")

except Exception as e:
    print(f"❌ Error: {e}")
EOF

python test_api.py
```

### Step 4: Run App
```bash
python app.py
```

### Step 5: Initialize in Browser
1. Go to: http://localhost:7860
2. Tab: "1️⃣ Setup & Configuration"
3. Enter API key
4. Click "Initialize Session"
5. Wait for: "✅ Session initialized successfully!"

---

## Model Comparison

| Model | Speed | Quality | Availability | Recommended For |
|-------|-------|---------|--------------|-----------------|
| gemini-2.0-flash-exp | ⚡ Fastest | ⭐⭐⭐ Good | 🔶 Limited | Testing, Development |
| gemini-1.5-flash | ⚡ Fast | ⭐⭐⭐⭐ Better | ✅ Global | Production |
| gemini-1.5-pro | 🐢 Slower | ⭐⭐⭐⭐⭐ Best | ✅ Global | High accuracy needed |

---

## API Configuration Files

### 1. `gemini_client.py` (line 54)
```python
def __init__(self,
             api_key: str,
             model_name: str = 'gemini-2.0-flash-exp',  # ← CHANGE HERE
             enable_caching: bool = True,
             cache_ttl: int = 3600):
```

### 2. Rate Limits (line 46-50)
```python
RATE_LIMITS = {
    'requests_per_minute': 60,      # ← Adjust if needed
    'tokens_per_minute': 1000000,
    'requests_per_day': 1500
}
```

---

## Debugging API Issues

### Enable Debug Logging

Add to top of `app.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check API Response

Add to `initialize_session()` in `app.py`:
```python
# After line 63, add:
print(f"DEBUG: API Response: {test_response}")
print(f"DEBUG: Response text: {test_response.text}")
```

### Test Each Module

```bash
# Test GeminiClient
python << 'EOF'
from gemini_client import GeminiClient
client = GeminiClient(api_key="YOUR_KEY")
response = client.generate_content("Test", generation_config={'temperature': 0.1})
print(f"Success: {response.text}")
EOF

# Test ClaimExtractor
python << 'EOF'
from gemini_client import GeminiClient
from claim_extractor import ClaimExtractor
client = GeminiClient(api_key="YOUR_KEY")
extractor = ClaimExtractor(client)
print("ClaimExtractor initialized successfully!")
EOF
```

---

## Alternative: Using Environment Variables

Instead of entering API key in UI, use environment variable:

### Option 1: Export in terminal
```bash
export GEMINI_API_KEY="your_key_here"
python app.py
```

### Option 2: Create .env file
```bash
echo 'GEMINI_API_KEY=your_key_here' > .env

# Then modify app.py to load from .env
pip install python-dotenv

# Add to top of app.py:
from dotenv import load_dotenv
import os
load_dotenv()
```

### Option 3: Modify initialize_session()
```python
def initialize_session(api_key: str = None, mock_mode: bool = False):
    # Try environment variable first
    if not api_key:
        api_key = os.getenv('GEMINI_API_KEY')

    if not api_key or api_key.strip() == "":
        return False, "❌ Please enter a valid API key or set GEMINI_API_KEY"
    # ... rest of function
```

---

## Still Having Issues?

### 1. Check System Requirements
```bash
python --version  # Should be 3.8+
pip list | grep -E 'gradio|google-generativeai'
```

### 2. Reinstall Dependencies
```bash
pip uninstall google-generativeai gradio -y
pip install -r requirements.txt
```

### 3. Try Minimal Test
```python
import google.generativeai as genai

genai.configure(api_key="YOUR_KEY")
model = genai.GenerativeModel('gemini-1.5-flash')
print(model.generate_content("Hello").text)
```

### 4. Check Firewall/Proxy
```bash
# Test direct connection
curl https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_KEY
```

### 5. Verify API Key Format
```
✅ Correct: AIzaSyAbc123Def456Ghi789Jkl012Mno345Pqr678
❌ Wrong:   AIza... (truncated)
❌ Wrong:   <API_KEY> (placeholder)
❌ Wrong:   "AIza..." (with quotes)
```

---

## Quick Reference Commands

```bash
# Get Gemini API key
open https://makersuite.google.com/app/apikey

# Install dependencies
pip install -r requirements.txt

# Test API
python -c "import google.generativeai as genai; genai.configure(api_key='YOUR_KEY'); print(genai.GenerativeModel('gemini-1.5-flash').generate_content('OK').text)"

# Run app
python app.py

# Access interface
open http://localhost:7860
```

---

## Success Checklist

- [ ] ✅ API key obtained from makersuite.google.com
- [ ] ✅ Dependencies installed
- [ ] ✅ API key tested successfully
- [ ] ✅ App starts without errors
- [ ] ✅ Can access http://localhost:7860
- [ ] ✅ Session initializes successfully
- [ ] ✅ Can analyze a resume

---

**Need more help?** Check `FIXES_APPLIED.md` for detailed troubleshooting.
