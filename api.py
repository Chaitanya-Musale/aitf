"""
Resume Verification API - Flask Backend for Node.js Integration
Provides REST endpoints for resume analysis
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import tempfile
import traceback
from datetime import datetime
import json
import logging

# Import your modules
from cv_parser import CVParser
from claim_extractor import ClaimExtractor
from evidence_validator import EvidenceValidator
from red_flag_detector import RedFlagDetector
from gemini_client import GeminiClient
from evidence_heatmap import EvidenceHeatmap

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow requests from Node.js app

# Store API key (should be in environment variable)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# Initialize Gemini client (reuse across requests)
gemini_client = None

def get_gemini_client():
    """Get or create Gemini client"""
    global gemini_client
    if gemini_client is None:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        gemini_client = GeminiClient(api_key=GEMINI_API_KEY)
    return gemini_client

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'api_key_configured': bool(GEMINI_API_KEY)
    })

@app.route('/api/analyze', methods=['POST'])
def analyze_resume():
    """
    Analyze resume endpoint

    Expects:
    - file: resume file (PDF, DOCX, or TXT)
    - seniority: intern|junior|mid|senior|lead (optional, default: mid)
    - strictness: low|medium|high (optional, default: medium)
    - deep_analysis: true|false (optional, default: false)

    Returns:
    - JSON with analysis results
    """
    try:
        # Validate file upload
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400

        # Get parameters
        seniority = request.form.get('seniority', 'mid').lower()
        strictness = request.form.get('strictness', 'medium').lower()
        deep_analysis = request.form.get('deep_analysis', 'false').lower() == 'true'

        # Validate parameters
        valid_seniority = ['intern', 'junior', 'mid', 'senior', 'lead']
        valid_strictness = ['low', 'medium', 'high']

        if seniority not in valid_seniority:
            return jsonify({'error': f'Invalid seniority. Must be one of: {valid_seniority}'}), 400

        if strictness not in valid_strictness:
            return jsonify({'error': f'Invalid strictness. Must be one of: {valid_strictness}'}), 400

        # Save uploaded file temporarily
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1])
        file.save(temp_file.name)
        temp_file.close()

        try:
            # Initialize modules
            client = get_gemini_client()
            cv_parser = CVParser()
            claim_extractor = ClaimExtractor(client)
            evidence_validator = EvidenceValidator(client)
            red_flag_detector = RedFlagDetector(client, strictness_level=strictness)

            # Step 1: Parse CV
            logger.info(f"Parsing resume: {file.filename}")
            parsed_cv = cv_parser.parse(temp_file.name)

            # Step 2: Extract claims
            logger.info("Extracting claims...")
            claims_result = claim_extractor.extract_claims(parsed_cv, seniority)
            claims = claims_result['claims']

            if not claims:
                return jsonify({
                    'error': 'No claims found in resume',
                    'suggestion': 'Ensure resume includes work experience, projects, or skills'
                }), 400

            # Step 3: Validate evidence
            logger.info(f"Validating {len(claims)} claims...")
            validation_result = evidence_validator.validate_evidence(
                claims,
                parsed_cv['raw_text'],
                check_links=deep_analysis,
                deep_repo_analysis=deep_analysis
            )

            # Step 4: Detect red flags
            logger.info("Detecting red flags...")
            red_flag_result = red_flag_detector.detect_red_flags(
                {
                    'claims': claims,
                    'validations': validation_result['validations'],
                    'consistency_score': validation_result['consistency_score']
                },
                seniority
            )

            # Normalize consistency score
            def normalize_score(score):
                if score > 100:
                    return min(100, score / 100)
                elif score <= 1:
                    return score * 100
                return min(100, score)

            consistency_score = normalize_score(validation_result['consistency_score'])

            # Round scores
            final_score = round(red_flag_result['final_score'], 1)
            credibility_score = round(red_flag_result['credibility_score'], 1)
            consistency_score = round(consistency_score, 1)

            # Compile results
            analysis_results = {
                'success': True,
                'filename': file.filename,
                'analysis_date': datetime.now().isoformat(),
                'seniority_level': seniority,
                'strictness_level': strictness,

                # Scores
                'final_score': final_score,
                'credibility_score': credibility_score,
                'consistency_score': consistency_score,
                'risk_assessment': red_flag_result['risk_assessment'],

                # Counts
                'total_claims': len(claims),
                'verified_claims': sum(1 for v in validation_result['validations']
                                     if v.get('verification_status') == 'verified'),
                'unverified_claims': sum(1 for v in validation_result['validations']
                                        if v.get('verification_status') in ['unverified', 'red_flag']),
                'total_red_flags': len(red_flag_result['red_flags']),

                # Details
                'red_flags': red_flag_result['red_flags'],
                'recommendation': red_flag_result['summary']['recommendation'],
                'claim_metrics': claims_result['metrics'],

                # Optional: include full data
                'claims': claims if request.form.get('include_claims') == 'true' else None,
                'validations': validation_result['validations'] if request.form.get('include_validations') == 'true' else None
            }

            logger.info(f"Analysis complete: {final_score}/100, {len(red_flag_result['red_flags'])} red flags")

            return jsonify(analysis_results)

        finally:
            # Clean up temp file
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)

    except Exception as e:
        logger.error(f"Analysis failed: {traceback.format_exc()}")
        return jsonify({
            'error': 'Analysis failed',
            'message': str(e),
            'traceback': traceback.format_exc() if app.debug else None
        }), 500

@app.route('/api/export', methods=['POST'])
def export_report():
    """
    Export report endpoint

    Expects JSON body with analysis results
    Query param: format=html|json|csv

    Returns: File download
    """
    try:
        export_format = request.args.get('format', 'html').lower()

        if export_format not in ['html', 'json', 'csv']:
            return jsonify({'error': 'Invalid format. Must be: html, json, or csv'}), 400

        # Get analysis results from request body
        results = request.get_json()

        if not results:
            return jsonify({'error': 'No analysis results provided'}), 400

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if export_format == 'html':
            html_content = generate_html_report(results)
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html')
            temp_file.write(html_content)
            temp_file.close()

            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name=f'resume_analysis_{timestamp}.html',
                mimetype='text/html'
            )

        elif export_format == 'json':
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
            json.dump(results, temp_file, indent=2, default=str)
            temp_file.close()

            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name=f'resume_analysis_{timestamp}.json',
                mimetype='application/json'
            )

        elif export_format == 'csv':
            csv_content = generate_csv_report(results)
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
            temp_file.write(csv_content)
            temp_file.close()

            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name=f'resume_analysis_{timestamp}.csv',
                mimetype='text/csv'
            )

    except Exception as e:
        logger.error(f"Export failed: {traceback.format_exc()}")
        return jsonify({'error': 'Export failed', 'message': str(e)}), 500

def generate_html_report(results):
    """Generate HTML report"""
    consistency_score = min(100, results.get('consistency_score', 0))

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Resume Verification Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
        .score {{ font-size: 48px; font-weight: bold; }}
        .card {{ background: #f8f9fa; padding: 20px; margin: 15px 0; border-radius: 5px; }}
        .red-flag {{ background: #ffebee; border-left: 4px solid #f44336; padding: 15px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Resume Verification Report</h1>
            <p>Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        </div>

        <div class="card">
            <h2>Overall Assessment</h2>
            <div class="score">{results.get('final_score', 0):.0f}/100</div>
            <p><strong>Risk Level:</strong> {results.get('risk_assessment', 'Unknown').upper()}</p>
            <p><strong>Credibility:</strong> {results.get('credibility_score', 0):.0f}/100</p>
            <p><strong>Consistency:</strong> {consistency_score:.0f}/100</p>
        </div>

        <div class="card">
            <h2>Claims Analysis</h2>
            <p><strong>Total Claims:</strong> {results.get('total_claims', 0)}</p>
            <p><strong>Verified:</strong> {results.get('verified_claims', 0)}</p>
            <p><strong>Unverified:</strong> {results.get('unverified_claims', 0)}</p>
            <p><strong>Red Flags:</strong> {results.get('total_red_flags', 0)}</p>
        </div>

        <div class="card">
            <h2>Red Flags</h2>
            {''.join(f'<div class="red-flag"><strong>{flag.get("severity", "").upper()}:</strong> {flag.get("description", "")}</div>' for flag in results.get('red_flags', [])[:10])}
        </div>

        <div class="card">
            <h2>Recommendation</h2>
            <p>{results.get('recommendation', 'No recommendation available')}</p>
        </div>
    </div>
</body>
</html>
"""
    return html

def generate_csv_report(results):
    """Generate CSV report"""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Final Score', results.get('final_score', 0)])
    writer.writerow(['Credibility Score', results.get('credibility_score', 0)])
    writer.writerow(['Consistency Score', results.get('consistency_score', 0)])
    writer.writerow(['Risk Assessment', results.get('risk_assessment', 'Unknown')])
    writer.writerow(['Total Claims', results.get('total_claims', 0)])
    writer.writerow(['Verified Claims', results.get('verified_claims', 0)])
    writer.writerow(['Red Flags', results.get('total_red_flags', 0)])
    writer.writerow([])

    # Write red flags
    writer.writerow(['Red Flag Severity', 'Description'])
    for flag in results.get('red_flags', []):
        writer.writerow([flag.get('severity', ''), flag.get('description', '')])

    return output.getvalue()

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Check API key
    if not GEMINI_API_KEY:
        print("⚠️ WARNING: GEMINI_API_KEY environment variable not set!")
        print("Set it with: export GEMINI_API_KEY='your-key-here'")

    # Run Flask app
    port = int(os.getenv('PORT', 5000))
    print(f"🚀 Resume Verification API starting on http://localhost:{port}")
    print(f"📊 Health check: http://localhost:{port}/health")
    print(f"📝 Analyze endpoint: http://localhost:{port}/api/analyze")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.getenv('FLASK_ENV') == 'development'
    )
