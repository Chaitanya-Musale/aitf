# Node.js Integration Guide

## 🏗️ Architecture

```
Your Node.js App (Port 3000)
       ↓
   HTTP Request
       ↓
Python Flask API (Port 5000)
       ↓
   Returns JSON
       ↓
Your Node.js App
```

---

## 📂 File Structure

```
your-project/
├── nodejs-app/                 # Your existing Node.js app
│   ├── server.js
│   ├── routes/
│   ├── package.json
│   └── ...
│
└── python-api/                 # Python resume verification API
    ├── api.py                 # ← Flask API (created)
    ├── cv_parser.py           # ← Copy from current project
    ├── claim_extractor.py     # ← Copy from current project
    ├── evidence_validator.py  # ← Copy from current project
    ├── red_flag_detector.py   # ← Copy from current project
    ├── gemini_client.py       # ← Copy from current project
    ├── prompts.py
    ├── sota_checker.py
    ├── evidence_heatmap.py
    ├── requirements-api.txt   # ← Updated requirements
    └── .env                   # ← GEMINI_API_KEY=your-key
```

---

## 🚀 Setup Steps

### 1. Create Python API folder

```bash
# In your project root
mkdir python-api
cd python-api

# Copy all Python files here
# (cv_parser.py, claim_extractor.py, etc.)
```

### 2. Install Python dependencies

```bash
cd python-api
pip install -r requirements-api.txt
```

### 3. Set up environment variables

```bash
# Create .env file
echo "GEMINI_API_KEY=your-actual-api-key-here" > .env

# Or export directly
export GEMINI_API_KEY="your-key-here"
```

### 4. Start Python API

```bash
cd python-api
python api.py

# Output:
# 🚀 Resume Verification API starting on http://localhost:5000
# 📊 Health check: http://localhost:5000/health
# 📝 Analyze endpoint: http://localhost:5000/api/analyze
```

### 5. Keep it running (separate terminal)

```bash
# Terminal 1: Python API
cd python-api && python api.py

# Terminal 2: Your Node.js app
cd nodejs-app && npm start
```

---

## 💻 Node.js Integration Code

### Option 1: Using axios (Recommended)

```bash
# In your Node.js app
npm install axios form-data
```

```javascript
// In your Node.js route handler
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

// Example Express route
app.post('/api/verify-resume', async (req, res) => {
    try {
        // Get uploaded file from your Node.js request
        const resumeFile = req.file; // Assumes multer middleware

        // Create form data
        const formData = new FormData();
        formData.append('file', fs.createReadStream(resumeFile.path));
        formData.append('seniority', req.body.seniority || 'mid');
        formData.append('strictness', req.body.strictness || 'medium');
        formData.append('deep_analysis', req.body.deep_analysis || 'false');

        // Call Python API
        const response = await axios.post('http://localhost:5000/api/analyze', formData, {
            headers: formData.getHeaders(),
            timeout: 120000 // 2 minutes
        });

        // Return results to your frontend
        res.json(response.data);

    } catch (error) {
        console.error('Python API error:', error.message);
        res.status(500).json({
            error: 'Resume analysis failed',
            message: error.response?.data?.message || error.message
        });
    }
});
```

### Option 2: Using fetch (Node.js 18+)

```javascript
const FormData = require('form-data');
const fs = require('fs');

app.post('/api/verify-resume', async (req, res) => {
    const formData = new FormData();
    formData.append('file', fs.createReadStream(req.file.path));
    formData.append('seniority', req.body.seniority || 'mid');

    const response = await fetch('http://localhost:5000/api/analyze', {
        method: 'POST',
        body: formData,
    });

    const data = await response.json();
    res.json(data);
});
```

### Option 3: Direct proxy (simplest)

```javascript
// Just proxy to Python API
const { createProxyMiddleware } = require('http-proxy-middleware');

app.use('/python-api', createProxyMiddleware({
    target: 'http://localhost:5000',
    changeOrigin: true,
    pathRewrite: {
        '^/python-api': '/api'
    }
}));

// Now your frontend calls:
// POST /python-api/analyze
// and it automatically goes to Python API
```

---

## 🎯 API Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

```bash
curl http://localhost:5000/health
```

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2025-10-26T15:30:00",
    "api_key_configured": true
}
```

---

### 2. Analyze Resume

**Endpoint:** `POST /api/analyze`

**Parameters:**
- `file` (file, required) - Resume file (PDF, DOCX, TXT)
- `seniority` (string, optional) - intern|junior|mid|senior|lead (default: mid)
- `strictness` (string, optional) - low|medium|high (default: medium)
- `deep_analysis` (boolean, optional) - true|false (default: false)
- `include_claims` (boolean, optional) - Include full claims array
- `include_validations` (boolean, optional) - Include full validations

**Example:**
```bash
curl -X POST http://localhost:5000/api/analyze \
  -F "file=@resume.pdf" \
  -F "seniority=senior" \
  -F "strictness=high" \
  -F "deep_analysis=true"
```

**Response:**
```json
{
    "success": true,
    "filename": "resume.pdf",
    "analysis_date": "2025-10-26T15:30:00",
    "seniority_level": "senior",
    "strictness_level": "high",

    "final_score": 78.5,
    "credibility_score": 82.0,
    "consistency_score": 73.0,
    "risk_assessment": "medium",

    "total_claims": 45,
    "verified_claims": 32,
    "unverified_claims": 13,
    "total_red_flags": 3,

    "red_flags": [
        {
            "severity": "medium",
            "category": "timeline",
            "description": "Gap of 6 months between positions",
            "interview_probe": "Can you explain the gap between..."
        }
    ],

    "recommendation": "Proceed with interview. Some claims need verification.",

    "claim_metrics": {
        "specificity_score": 0.75,
        "buzzword_density": 0.08,
        "claims_with_metrics": 25
    }
}
```

---

### 3. Export Report

**Endpoint:** `POST /api/export?format=html|json|csv`

**Body:** Send the analysis results from step 2

**Example:**
```javascript
// First analyze
const analysisResult = await axios.post('http://localhost:5000/api/analyze', formData);

// Then export
const exportResponse = await axios.post(
    'http://localhost:5000/api/export?format=html',
    analysisResult.data,
    { responseType: 'blob' }
);

// Save file
fs.writeFileSync('report.html', exportResponse.data);
```

---

## 🔧 Complete Node.js Example

```javascript
// server.js or routes/resume.js
const express = require('express');
const multer = require('multer');
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

const router = express.Router();
const upload = multer({ dest: 'uploads/' });

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:5000';

// Analyze resume
router.post('/verify-resume', upload.single('resume'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No file uploaded' });
        }

        // Prepare form data for Python API
        const formData = new FormData();
        formData.append('file', fs.createReadStream(req.file.path));
        formData.append('seniority', req.body.seniority || 'mid');
        formData.append('strictness', req.body.strictness || 'medium');
        formData.append('deep_analysis', req.body.deep_analysis || 'false');

        // Call Python API
        const response = await axios.post(`${PYTHON_API}/api/analyze`, formData, {
            headers: formData.getHeaders(),
            timeout: 120000 // 2 minutes
        });

        // Clean up uploaded file
        fs.unlinkSync(req.file.path);

        // Return results
        res.json({
            success: true,
            data: response.data
        });

    } catch (error) {
        console.error('Analysis error:', error.message);

        // Clean up on error
        if (req.file && fs.existsSync(req.file.path)) {
            fs.unlinkSync(req.file.path);
        }

        res.status(500).json({
            success: false,
            error: error.response?.data?.message || error.message
        });
    }
});

// Export report
router.post('/export-report', async (req, res) => {
    try {
        const { analysisData, format } = req.body;

        const response = await axios.post(
            `${PYTHON_API}/api/export?format=${format || 'html'}`,
            analysisData,
            { responseType: 'arraybuffer' }
        );

        const filename = `resume_report_${Date.now()}.${format || 'html'}`;

        res.setHeader('Content-Disposition', `attachment; filename=${filename}`);
        res.setHeader('Content-Type', response.headers['content-type']);
        res.send(response.data);

    } catch (error) {
        console.error('Export error:', error.message);
        res.status(500).json({ error: error.message });
    }
});

module.exports = router;
```

**Usage in main server:**
```javascript
// server.js
const express = require('express');
const resumeRoutes = require('./routes/resume');

const app = express();

app.use(express.json());
app.use('/api', resumeRoutes);

app.listen(3000, () => {
    console.log('Node.js app running on port 3000');
});
```

---

## 🌐 Frontend Integration (React/Vue/Vanilla JS)

```javascript
// From your frontend
async function analyzeResume(file) {
    const formData = new FormData();
    formData.append('resume', file);
    formData.append('seniority', 'senior');
    formData.append('strictness', 'high');

    // Call your Node.js API (which proxies to Python)
    const response = await fetch('http://localhost:3000/api/verify-resume', {
        method: 'POST',
        body: formData
    });

    const result = await response.json();

    console.log('Final Score:', result.data.final_score);
    console.log('Risk Level:', result.data.risk_assessment);
    console.log('Red Flags:', result.data.red_flags);
}
```

---

## 🚀 Production Deployment

### Option 1: Both on same server

```bash
# Use PM2 to run both
npm install -g pm2

# Start Python API
pm2 start api.py --name python-api --interpreter python3

# Start Node.js app
pm2 start server.js --name nodejs-app

# View logs
pm2 logs
```

### Option 2: Separate deployments

**Python API:**
- Deploy to Heroku, AWS Lambda, Google Cloud Run
- Get URL: `https://api.yourapp.com`

**Node.js App:**
- Deploy normally
- Set env var: `PYTHON_API_URL=https://api.yourapp.com`

---

## 🧪 Testing

```bash
# Test Python API directly
curl -X POST http://localhost:5000/api/analyze \
  -F "file=@test_resume.pdf" \
  -F "seniority=mid"

# Test through Node.js
curl -X POST http://localhost:3000/api/verify-resume \
  -F "resume=@test_resume.pdf" \
  -F "seniority=mid"
```

---

## ⚠️ Common Issues

### Issue 1: CORS errors
**Solution:** Flask-CORS already configured in api.py. If still issues:
```python
CORS(app, origins=["http://localhost:3000"])  # Specify your Node.js URL
```

### Issue 2: Timeout errors
**Solution:** Increase timeout in axios:
```javascript
axios.post(url, data, { timeout: 180000 }) // 3 minutes
```

### Issue 3: File upload errors
**Solution:** Check multer configuration:
```javascript
const upload = multer({
    dest: 'uploads/',
    limits: { fileSize: 10 * 1024 * 1024 } // 10MB max
});
```

---

## 📊 Summary

**What you need to do:**

1. ✅ Copy all Python files to `python-api/` folder
2. ✅ Install: `pip install -r requirements-api.txt`
3. ✅ Set: `export GEMINI_API_KEY=your-key`
4. ✅ Run: `python api.py`
5. ✅ From Node.js, call: `http://localhost:5000/api/analyze`

**That's it!** Your Node.js app now talks to the Python API.
