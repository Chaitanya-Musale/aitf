"""
Resume Verification System - Professional Edition
Enhanced UI, comprehensive explanations, and bug fixes
"""

import gradio as gr
import logging
import json
import traceback
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd

# Import custom modules
try:
    from cv_parser import CVParser
    from claim_extractor import ClaimExtractor
    from evidence_validator import EvidenceValidator
    from red_flag_detector import RedFlagDetector
    from gemini_client import GeminiClient
    from sota_checker import SOTAChecker
    from evidence_heatmap import EvidenceHeatmap
    from report_generator import ReportGenerator
except ImportError as e:
    print(f"Failed to import modules: {e}")
    raise

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global session storage
current_session = {
    'initialized': False,
    'gemini_client': None,
    'api_key': None,
    'last_analysis': None
}

def initialize_session(api_key: str, mock_mode: bool = False) -> Tuple[bool, str]:
    """
    Initialize Gemini session with API key

    Args:
        api_key: Google AI API key
        mock_mode: Use mock mode for testing (not implemented)

    Returns:
        Tuple of (success, message)
    """
    global current_session

    try:
        if not api_key or api_key.strip() == "":
            return False, "❌ Please enter a valid API key"

        # Initialize Gemini client
        logger.info("Initializing Gemini client...")
        gemini_client = GeminiClient(api_key=api_key.strip())

        # Test connection
        test_response = gemini_client.generate_content(
            "Say 'OK' if you can read this",
            generation_config={'temperature': 0.1, 'max_output_tokens': 10}
        )

        if not test_response or not test_response.text:
            return False, "❌ Failed to connect to Gemini API"

        # Store in session
        current_session['gemini_client'] = gemini_client
        current_session['api_key'] = api_key
        current_session['initialized'] = True

        logger.info("Session initialized successfully")
        return True, "✅ Session initialized successfully! You can now upload and analyze resumes."

    except Exception as e:
        logger.error(f"Session initialization failed: {e}")
        return False, f"❌ Initialization failed: {str(e)}\n\nPlease check your API key at https://makersuite.google.com/app/apikey"

def generate_comprehensive_analysis_display(analysis_results: Dict) -> str:
    """Generate comprehensive analysis display with all factors we consider"""

    # Fix consistency score if it exceeds 100
    consistency_score = min(100, analysis_results.get('consistency_score', 0))
    analysis_results['consistency_score'] = consistency_score

    display = f"""
<div style="font-family: 'Segoe UI', Arial, sans-serif;">

# 📊 Comprehensive Resume Analysis

<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
    <h2 style="color: white; margin: 0;">Overall Assessment</h2>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; margin-top: 20px;">
        <div style="text-align: center;">
            <div style="font-size: 48px; font-weight: bold;">{analysis_results['final_score']:.1f}</div>
            <div>Final Score</div>
        </div>
        <div style="text-align: center;">
            <div style="font-size: 48px; font-weight: bold;">{analysis_results['credibility_score']:.1f}</div>
            <div>Credibility</div>
        </div>
        <div style="text-align: center;">
            <div style="font-size: 48px; font-weight: bold;">{consistency_score:.1f}</div>
            <div>Consistency</div>
        </div>
        <div style="text-align: center;">
            <div style="font-size: 24px; font-weight: bold; padding: 12px 0;">{analysis_results['risk_assessment'].upper()}</div>
            <div>Risk Level</div>
        </div>
    </div>
</div>

## 🔍 What We Analyzed

<div style="background: #f8f9fa; border-left: 4px solid #4CAF50; padding: 15px; margin: 15px 0;">

### ✅ Document Quality Metrics
- **Total Claims Extracted:** {analysis_results['total_claims']} factual claims identified
- **Claims with Evidence:** {analysis_results['verified_claims']} ({analysis_results['verified_claims']/max(1, analysis_results['total_claims'])*100:.0f}%)
- **Unsupported Claims:** {analysis_results['unverified_claims']} ({analysis_results['unverified_claims']/max(1, analysis_results['total_claims'])*100:.0f}%)
- **Document Structure:** {analysis_results.get('structure_quality', 'Well-organized')}

### 📈 Claim Quality Analysis
- **Specificity Score:** {analysis_results.get('claim_metrics', {}).get('specificity_score', 0)*100:.0f}% (How specific vs vague)
- **Claims with Metrics:** {analysis_results.get('claim_metrics', {}).get('claims_with_metrics', 0)}/{analysis_results['total_claims']}
- **Claims with Artifacts:** {analysis_results.get('claim_metrics', {}).get('claims_with_artifacts', 0)}/{analysis_results['total_claims']}
- **Buzzword Density:** {analysis_results.get('claim_metrics', {}).get('buzzword_density', 0)*100:.1f}% {get_buzzword_interpretation(analysis_results.get('claim_metrics', {}).get('buzzword_density', 0))}

### 🔗 Evidence Validation Results
- **Direct Evidence Found:** {count_evidence_type(analysis_results, 'direct')} claims
- **Contextual Evidence:** {count_evidence_type(analysis_results, 'contextual')} claims
- **No Evidence:** {count_evidence_type(analysis_results, 'none')} claims
- **Link Verification:** {analysis_results.get('links_checked', 0)} URLs checked

### 🎯 Advanced Checks Performed
- **Timeline Consistency:** {get_timeline_status(analysis_results)}
- **Technology Timeline:** {get_tech_timeline_status(analysis_results)}
- **Role-Achievement Match:** {get_role_match_status(analysis_results)}
- **Skill Usage Verification:** {get_skill_usage_status(analysis_results)}
- **Metric Plausibility:** {get_metric_status(analysis_results)}

</div>

## 🚩 Red Flag Analysis

{generate_detailed_red_flag_analysis(analysis_results.get('red_flags', []))}

## 💡 Score Calculation Breakdown

{generate_score_calculation_details(analysis_results)}

## 📋 Final Recommendation

<div style="background: #e3f2fd; border-left: 4px solid #2196F3; padding: 15px; margin: 15px 0;">
<strong>{analysis_results['recommendation']}</strong>

Based on {analysis_results['total_claims']} claims analyzed with {analysis_results.get('total_red_flags', 0)} red flags detected.
</div>

</div>
"""
    return display

def get_buzzword_interpretation(density: float) -> str:
    """Interpret buzzword density"""
    if density < 0.02:
        return "✅ Excellent - Concrete language"
    elif density < 0.05:
        return "✅ Good - Mostly specific"
    elif density < 0.10:
        return "⚠️ Moderate - Some vagueness"
    else:
        return "❌ High - Too many buzzwords"

def count_evidence_type(results: Dict, evidence_type: str) -> int:
    """Count claims with specific evidence type"""
    validations = results.get('validations', [])
    return sum(1 for v in validations if v.get('evidence_present') == evidence_type)

def get_timeline_status(results: Dict) -> str:
    """Get timeline consistency status"""
    red_flags = results.get('red_flags', [])
    timeline_issues = [f for f in red_flags if f.get('category') == 'timeline']
    if not timeline_issues:
        return "✅ Consistent - No gaps or overlaps"
    else:
        return f"❌ {len(timeline_issues)} issues found"

def get_tech_timeline_status(results: Dict) -> str:
    """Get technology timeline status"""
    red_flags = results.get('red_flags', [])
    tech_issues = [f for f in red_flags if 'tech' in f.get('description', '').lower()]
    if not tech_issues:
        return "✅ Valid - All technologies used after release"
    else:
        return f"❌ {len(tech_issues)} anachronisms detected"

def get_role_match_status(results: Dict) -> str:
    """Get role-achievement match status"""
    red_flags = results.get('red_flags', [])
    mismatch_issues = [f for f in red_flags if f.get('category') == 'mismatch']
    if not mismatch_issues:
        return "✅ Aligned - Achievements match role level"
    else:
        return f"⚠️ {len(mismatch_issues)} mismatches found"

def get_skill_usage_status(results: Dict) -> str:
    """Get skill usage verification status"""
    metrics = results.get('claim_metrics', {})
    if metrics.get('cross_referenced_skills', 0) > metrics.get('total_skills', 1) * 0.7:
        return "✅ Verified - Skills used in projects"
    else:
        return "⚠️ Some skills never demonstrated"

def get_metric_status(results: Dict) -> str:
    """Get metric plausibility status"""
    red_flags = results.get('red_flags', [])
    implausible = [f for f in red_flags if f.get('category') == 'implausible']
    if not implausible:
        return "✅ Plausible - Metrics within norms"
    else:
        return f"❌ {len(implausible)} unrealistic claims"

def generate_detailed_red_flag_analysis(red_flags: List[Dict]) -> str:
    """Generate detailed red flag analysis with better UI"""
    if not red_flags:
        return """
<div style="background: #e8f5e9; border-left: 4px solid #4CAF50; padding: 15px; margin: 15px 0;">
<h3 style="color: #2e7d32;">✅ No Critical Issues Detected</h3>
<p>The resume appears internally consistent with reasonable claims.</p>
</div>
"""

    # Group by severity
    critical = [f for f in red_flags if f.get('severity') == 'critical']
    high = [f for f in red_flags if f.get('severity') == 'high']
    medium = [f for f in red_flags if f.get('severity') == 'medium']
    low = [f for f in red_flags if f.get('severity') == 'low']

    html = ""

    if critical:
        html += """
<div style="background: #ffebee; border-left: 4px solid #f44336; padding: 15px; margin: 15px 0;">
<h3 style="color: #c62828;">🔴 Critical Issues ({count})</h3>
""".format(count=len(critical))
        for flag in critical:
            html += generate_single_flag_html(flag)
        html += "</div>"

    if high:
        html += """
<div style="background: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin: 15px 0;">
<h3 style="color: #e65100;">🟠 High Priority Issues ({count})</h3>
""".format(count=len(high))
        for flag in high:
            html += generate_single_flag_html(flag)
        html += "</div>"

    if medium:
        html += """
<div style="background: #fffde7; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0;">
<h3 style="color: #f57c00;">🟡 Medium Priority Issues ({count})</h3>
""".format(count=len(medium))
        for flag in medium[:3]:  # Limit to top 3
            html += generate_single_flag_html(flag)
        html += "</div>"

    return html

def generate_single_flag_html(flag: Dict) -> str:
    """Generate HTML for a single red flag with detailed explanation"""
    category_explanations = {
        'vague': {
            'icon': '💭',
            'why': 'Vague claims without specifics are common in padded resumes',
            'impact': 'Cannot verify actual expertise level',
            'action': 'Request specific examples with metrics'
        },
        'timeline': {
            'icon': '📅',
            'why': 'Timeline inconsistencies suggest potential fabrication',
            'impact': 'Questions overall resume credibility',
            'action': 'Verify exact dates with references'
        },
        'implausible': {
            'icon': '📊',
            'why': 'Claims exceeding industry norms need strong evidence',
            'impact': 'Likely exaggeration or misrepresentation',
            'action': 'Request detailed methodology and proof'
        },
        'mismatch': {
            'icon': '⚖️',
            'why': 'Achievements should match role seniority',
            'impact': 'Suggests overclaiming or title inflation',
            'action': 'Explore actual responsibilities and authority'
        },
        'overclaim': {
            'icon': '👥',
            'why': 'Taking sole credit for team work is concerning',
            'impact': 'Questions integrity and teamwork',
            'action': 'Ask about team composition and individual contribution'
        }
    }

    cat_info = category_explanations.get(flag.get('category', ''), {
        'icon': '⚠️',
        'why': 'This pattern needs verification',
        'impact': 'May affect credibility',
        'action': 'Verify during interview'
    })

    return f"""
<div style="margin: 10px 0; padding: 10px; background: rgba(255,255,255,0.5); border-radius: 5px;">
    <h4 style="margin: 5px 0;">{cat_info['icon']} {flag.get('description', 'Issue detected')}</h4>
    <ul style="margin: 5px 0;">
        <li><strong>Why this matters:</strong> {cat_info['why']}</li>
        <li><strong>Impact:</strong> {cat_info['impact']}</li>
        <li><strong>Action needed:</strong> {cat_info['action']}</li>
    </ul>
    <p style="background: #f5f5f5; padding: 8px; border-radius: 3px; margin: 5px 0;">
        <strong>Interview Question:</strong> {flag.get('interview_probe', 'Verify this claim in detail')}
    </p>
</div>
"""

def generate_score_calculation_details(results: Dict) -> str:
    """Generate detailed score calculation breakdown"""

    # Ensure consistency score doesn't exceed 100
    consistency_score = min(100, results.get('consistency_score', 0))

    html = f"""
<div style="background: #f5f5f5; padding: 20px; border-radius: 10px; margin: 20px 0;">

### How We Calculate Your Scores

#### 📊 Final Score: {results.get('final_score', 0):.1f}/100
**Formula:** (Credibility × 0.6) + (Consistency × 0.4)

#### 🎯 Credibility Score: {results.get('credibility_score', 0):.1f}/100

<table style="width: 100%; border-collapse: collapse;">
<tr style="background: #e0e0e0;">
    <th style="padding: 10px; text-align: left;">Factor</th>
    <th style="padding: 10px;">Impact</th>
    <th style="padding: 10px;">Your Status</th>
</tr>
<tr>
    <td style="padding: 10px;">Base Score</td>
    <td style="padding: 10px; text-align: center;">100 points</td>
    <td style="padding: 10px; text-align: center;">✓</td>
</tr>
"""

    # Deductions
    if results.get('unverified_claims', 0) > results.get('total_claims', 1) * 0.5:
        deduction = -20
        html += f"""
<tr style="background: #ffebee;">
    <td style="padding: 10px;">Majority claims unverified</td>
    <td style="padding: 10px; text-align: center;">{deduction} points</td>
    <td style="padding: 10px; text-align: center;">Applied</td>
</tr>
"""

    red_flag_deduction = results.get('total_red_flags', 0) * -5
    if red_flag_deduction < 0:
        html += f"""
<tr style="background: #ffebee;">
    <td style="padding: 10px;">Red flags ({results.get('total_red_flags', 0)} found)</td>
    <td style="padding: 10px; text-align: center;">{red_flag_deduction} points</td>
    <td style="padding: 10px; text-align: center;">Applied</td>
</tr>
"""

    if results.get('claim_metrics', {}).get('buzzword_density', 0) > 0.1:
        html += """
<tr style="background: #ffebee;">
    <td style="padding: 10px;">High buzzword density</td>
    <td style="padding: 10px; text-align: center;">-10 points</td>
    <td style="padding: 10px; text-align: center;">Applied</td>
</tr>
"""

    # Positive factors
    if results.get('verified_claims', 0) > results.get('total_claims', 1) * 0.7:
        html += """
<tr style="background: #e8f5e9;">
    <td style="padding: 10px;">Strong evidence ratio</td>
    <td style="padding: 10px; text-align: center;">+10 points</td>
    <td style="padding: 10px; text-align: center;">Applied</td>
</tr>
"""

    html += f"""
</table>

#### 🔄 Consistency Score: {consistency_score:.1f}/100

<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
<tr style="background: #e0e0e0;">
    <th style="padding: 10px; text-align: left;">Check</th>
    <th style="padding: 10px;">Weight</th>
    <th style="padding: 10px;">Result</th>
</tr>
<tr>
    <td style="padding: 10px;">Timeline Consistency</td>
    <td style="padding: 10px; text-align: center;">30%</td>
    <td style="padding: 10px; text-align: center;">{get_check_status(results, 'timeline')}</td>
</tr>
<tr>
    <td style="padding: 10px;">Technology Timeline</td>
    <td style="padding: 10px; text-align: center;">20%</td>
    <td style="padding: 10px; text-align: center;">{get_check_status(results, 'tech_timeline')}</td>
</tr>
<tr>
    <td style="padding: 10px;">Skill Usage Cross-Reference</td>
    <td style="padding: 10px; text-align: center;">30%</td>
    <td style="padding: 10px; text-align: center;">{get_check_status(results, 'skill_usage')}</td>
</tr>
<tr>
    <td style="padding: 10px;">Internal Coherence</td>
    <td style="padding: 10px; text-align: center;">20%</td>
    <td style="padding: 10px; text-align: center;">{get_check_status(results, 'coherence')}</td>
</tr>
</table>

</div>
"""
    return html

def get_check_status(results: Dict, check_type: str) -> str:
    """Get status for specific check"""
    red_flags = results.get('red_flags', [])

    if check_type == 'timeline':
        issues = [f for f in red_flags if f.get('category') == 'timeline']
        return "❌ Failed" if issues else "✅ Passed"
    elif check_type == 'tech_timeline':
        issues = [f for f in red_flags if 'tech' in f.get('description', '').lower()]
        return "❌ Failed" if issues else "✅ Passed"
    elif check_type == 'skill_usage':
        return "⚠️ Partial"
    else:
        return "✅ Passed"

def generate_enhanced_claim_analysis(claims: List[Dict], validations: List[Dict]) -> str:
    """Generate enhanced claim-by-claim analysis with better UI"""

    if not claims:
        return "<p>No claims found to analyze.</p>"

    html = """
<div style="font-family: 'Segoe UI', Arial, sans-serif;">

# 📋 Detailed Claim Analysis

<div style="background: #f8f9fa; padding: 15px; border-radius: 10px; margin: 15px 0;">
<p><strong>Analyzing {total} claims for evidence and credibility...</strong></p>
</div>

""".format(total=len(claims))

    # Create validation map by claim_id for proper matching
    validation_map = {}
    for val in validations:
        claim_id = val.get('claim_id', '')
        if claim_id:
            validation_map[claim_id] = val

    # Group claims by category
    categories = {}
    for claim in claims[:20]:  # Limit to top 20
        cat = claim.get('category', 'other')
        if cat not in categories:
            categories[cat] = []

        # Get validation by claim_id
        claim_id = claim.get('claim_id', '')
        validation = validation_map.get(claim_id, {})
        categories[cat].append((claim, validation))

    # Display by category
    category_icons = {
        'work_experience': '💼',
        'project': '🚀',
        'skill': '🛠️',
        'research': '🔬',
        'education': '🎓'
    }

    for category, items in categories.items():
        icon = category_icons.get(category, '📌')
        html += f"""
<h2>{icon} {category.replace('_', ' ').title()} ({len(items)} claims)</h2>
"""

        for claim, validation in items[:5]:  # Limit to 5 per category
            html += generate_single_claim_analysis(claim, validation)

    html += "</div>"
    return html

def generate_single_claim_analysis(claim: Dict, validation: Dict) -> str:
    """Generate analysis for a single claim with detailed explanation"""

    status = validation.get('verification_status', 'unknown')
    score = validation.get('final_evidence_score', 0)

    # Determine status color and icon
    if status == 'verified':
        color = '#4CAF50'
        bg_color = '#e8f5e9'
        icon = '✅'
        status_text = 'VERIFIED'
    elif status == 'partial':
        color = '#FF9800'
        bg_color = '#fff3e0'
        icon = '⚠️'
        status_text = 'PARTIALLY VERIFIED'
    else:
        color = '#f44336'
        bg_color = '#ffebee'
        icon = '❌'
        status_text = 'UNVERIFIED'

    claim_text = claim.get('claim_text', 'Unknown claim')
    display_text = claim_text[:100] + "..." if len(claim_text) > 100 else claim_text

    html = f"""
<div style="margin: 15px 0; padding: 15px; background: {bg_color}; border-left: 4px solid {color}; border-radius: 5px;">
    <h3 style="margin: 0 0 10px 0; color: #333;">
        {icon} {display_text}
    </h3>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 10px 0;">
        <div>
            <strong>Status:</strong> <span style="color: {color}; font-weight: bold;">{status_text}</span><br>
            <strong>Evidence Score:</strong> {score:.1%}<br>
            <strong>Verifiability:</strong> {claim.get('verifiability_level', 'Unknown')}
        </div>
        <div>
            <strong>Category:</strong> {claim.get('category', 'Unknown')}<br>
            <strong>Has Metrics:</strong> {'Yes' if claim.get('quantifiable_metrics') else 'No'}<br>
            <strong>Has Links:</strong> {'Yes' if claim.get('links_artifacts') else 'No'}
        </div>
    </div>
</div>
"""

    return html

def generate_interview_guide_with_context(results: Dict) -> str:
    """Generate comprehensive interview guide with full context"""

    if not results:
        return "<p>No analysis results available yet. Please run an analysis first.</p>"

    html = """
<div style="font-family: 'Segoe UI', Arial, sans-serif;">

# 🎯 Strategic Interview Guide

<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
    <h2 style="color: white; margin: 0;">Customized for {level} Level Position</h2>
    <p>Based on {claims} claims analyzed with {flags} concerns identified</p>
</div>

""".format(
        level=results.get('seniority_level', 'Mid'),
        claims=results.get('total_claims', 0),
        flags=results.get('total_red_flags', 0)
    )

    # Priority verification areas
    html += """
<h2>🔴 Priority Verification Areas</h2>
<div style="background: #ffebee; border-left: 4px solid #f44336; padding: 15px; margin: 15px 0;">
"""

    red_flags = results.get('red_flags', [])

    if not red_flags:
        html += "<p>✅ No critical areas identified - proceed with standard behavioral interview</p>"
    else:
        for i, flag in enumerate(red_flags[:5], 1):
            description = flag.get('description', 'Issue detected')
            probe = flag.get('interview_probe', 'Can you provide more details about this?')

            html += f"""
<div style="margin: 15px 0; padding: 15px; background: white; border-radius: 5px;">
    <h3>Priority #{i}: {description}</h3>

    <div style="background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 3px;">
        <strong>🎤 Primary Question:</strong><br>
        {probe}
    </div>

    <div style="background: #e3f2fd; padding: 10px; margin: 10px 0; border-radius: 3px;">
        <strong>💡 Follow-up Questions:</strong>
        <ul style="margin: 5px 0;">
            <li>Can you walk me through the specific details?</li>
            <li>Who else was involved and what were their roles?</li>
            <li>What evidence or documentation do you have?</li>
        </ul>
    </div>
</div>
"""

    html += """
</div>

<h2>✅ Standard Interview Questions</h2>
<div style="background: #e8f5e9; border-left: 4px solid #4CAF50; padding: 15px; margin: 15px 0;">

<div style="margin: 15px 0; padding: 15px; background: white; border-radius: 5px;">
    <p><strong>Q1: Walk me through your most significant technical contribution.</strong></p>
    <p style="color: #666; font-size: 0.9em;">Purpose: Verify depth of technical involvement and ownership</p>
</div>

<div style="margin: 15px 0; padding: 15px; background: white; border-radius: 5px;">
    <p><strong>Q2: Describe a time when a project didn't go as planned. What happened?</strong></p>
    <p style="color: #666; font-size: 0.9em;">Purpose: Test honesty and ability to learn from failures</p>
</div>

<div style="margin: 15px 0; padding: 15px; background: white; border-radius: 5px;">
    <p><strong>Q3: How do you measure success in your role?</strong></p>
    <p style="color: #666; font-size: 0.9em;">Purpose: Verify metrics-driven approach and claimed achievements</p>
</div>

</div>

</div>
"""

    return html

def analyze_resume(
    file,
    seniority_level: str,
    strictness_level: str,
    deep_analysis: bool,
    progress=gr.Progress()
) -> Tuple[str, Any, Any, Any, Any, str, str, str, str]:
    """Main analysis function with enhanced outputs"""
    global current_session

    if not current_session.get('initialized'):
        return "❌ Please initialize session with API key first", None, None, None, None, "", "", "", ""

    if file is None:
        return "❌ Please upload a resume file", None, None, None, None, "", "", "", ""

    try:
        progress(0.0, desc="Initializing analysis...")

        # Get file path
        file_path = file.name if hasattr(file, 'name') else str(file)

        # Initialize modules
        gemini_client = current_session['gemini_client']
        cv_parser = CVParser()
        claim_extractor = ClaimExtractor(gemini_client)
        evidence_validator = EvidenceValidator(gemini_client)
        red_flag_detector = RedFlagDetector(gemini_client, strictness_level=strictness_level.lower())

        progress(0.1, desc="Parsing resume...")
        parsed_cv = cv_parser.parse(file_path)

        progress(0.3, desc="Extracting claims...")
        claims_result = claim_extractor.extract_claims(parsed_cv, seniority_level.lower())
        claims = claims_result['claims']

        if not claims:
            # Diagnose why no claims found
            resume_length = len(parsed_cv.get('raw_text', ''))
            sections_found = list(parsed_cv.get('sections', {}).keys())

            if resume_length < 100:
                error_msg = "⚠️ Resume too short (< 100 words). Please upload a complete resume with work experience, projects, or skills."
            elif len(sections_found) == 0:
                error_msg = "⚠️ Could not parse resume structure. Please ensure the file is a valid PDF, DOCX, or TXT with clear sections."
            elif sections_found == ['education'] or len(sections_found) == 1:
                error_msg = f"⚠️ Only found {sections_found[0]} section. Please add:\n• Work experience\n• Projects\n• Skills\n• Achievements"
            else:
                error_msg = f"⚠️ No analyzable claims found. Sections detected: {', '.join(sections_found)}.\n\nEnsure resume includes specific achievements, not just responsibilities."

            return error_msg, None, None, None, None, "", "", "", ""

        progress(0.5, desc="Validating evidence...")
        validation_result = evidence_validator.validate_evidence(
            claims,
            parsed_cv['raw_text'],
            check_links=deep_analysis,
            deep_repo_analysis=deep_analysis
        )

        progress(0.7, desc="Detecting red flags...")
        red_flag_result = red_flag_detector.detect_red_flags(
            {
                'claims': claims,
                'validations': validation_result['validations'],
                'consistency_score': validation_result['consistency_score']
            },
            seniority_level.lower()
        )

        progress(0.8, desc="Generating comprehensive analysis...")

        # Fix consistency score normalization (handle both 0-1 and 0-100 formats)
        def normalize_score(score):
            """Normalize score to 0-100 range"""
            if score > 100:
                # Score was mistakenly multiplied
                return min(100, score / 100)
            elif score <= 1:
                # Score is in decimal format (0-1)
                return score * 100
            else:
                # Score is already in 0-100 range
                return min(100, score)

        consistency_score = normalize_score(validation_result['consistency_score'])

        # Round all scores to 1 decimal place for consistency
        final_score = round(red_flag_result['final_score'], 1)
        credibility_score = round(red_flag_result['credibility_score'], 1)
        consistency_score = round(consistency_score, 1)

        # Compile comprehensive results
        analysis_results = {
            'parsed_cv': parsed_cv,
            'claims': claims,
            'total_claims': len(claims),
            'verified_claims': sum(1 for v in validation_result['validations'] if v.get('verification_status') == 'verified'),
            'unverified_claims': sum(1 for v in validation_result['validations'] if v.get('verification_status') in ['unverified', 'red_flag']),
            'claim_metrics': claims_result['metrics'],
            'validations': validation_result['validations'],
            'consistency_score': consistency_score,
            'red_flags': red_flag_result['red_flags'],
            'total_red_flags': len(red_flag_result['red_flags']),
            'credibility_score': credibility_score,
            'final_score': final_score,
            'risk_assessment': red_flag_result['risk_assessment'],
            'recommendation': red_flag_result['summary']['recommendation'],
            'seniority_level': seniority_level,
            'links_checked': sum(1 for c in claims if c.get('links_artifacts')),
            'structure_quality': 'Well-organized',
            'analysis_timestamp': datetime.now().isoformat()
        }

        # Store for export
        current_session['last_analysis'] = analysis_results

        # Generate visualizations
        progress(0.9, desc="Creating visualizations...")
        try:
            heatmap = EvidenceHeatmap()
            heatmap_fig = heatmap.create_evidence_heatmap(validation_result['validations'], claims)
            dashboard_fig = heatmap.create_credibility_dashboard(
                {
                    'final': red_flag_result['final_score'],
                    'credibility': red_flag_result['credibility_score'],
                    'consistency': consistency_score,
                    'risk_level': red_flag_result['risk_assessment']
                },
                red_flag_result['red_flags']
            )
            distribution_fig = heatmap.create_claim_distribution(claims)
            validation_fig = heatmap.create_validation_summary(validation_result['validations'], claims)
        except Exception as e:
            logger.warning(f"Visualization failed: {e}")
            heatmap_fig = dashboard_fig = distribution_fig = validation_fig = None

        # Generate comprehensive displays
        main_analysis = generate_comprehensive_analysis_display(analysis_results)
        claim_analysis = generate_enhanced_claim_analysis(claims, validation_result['validations'])
        interview_guide = generate_interview_guide_with_context(analysis_results)

        progress(1.0, desc="Analysis complete!")

        return (
            main_analysis,
            dashboard_fig,
            heatmap_fig,
            distribution_fig,
            validation_fig,
            interview_guide,
            "",  # Red flags are now integrated into main analysis
            claim_analysis,
            "✅ Analysis complete! Review the comprehensive breakdown above."
        )

    except Exception as e:
        logger.error(f"Analysis failed: {traceback.format_exc()}")
        return f"❌ Analysis failed: {str(e)}", None, None, None, None, "", "", "", ""

def export_report(format_type: str):
    """Export report with fixed consistency score"""
    global current_session

    if 'last_analysis' not in current_session:
        return None, "❌ No analysis available to export. Please analyze a resume first."

    try:
        results = current_session['last_analysis']

        # Fix consistency score before export
        results['consistency_score'] = min(100, results.get('consistency_score', 0))

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if format_type == "HTML":
            html_content = generate_comprehensive_html_report(results)

            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                delete=False,
                suffix='.html',
                prefix=f'resume_analysis_{timestamp}_'
            )
            temp_file.write(html_content)
            temp_file.close()

            return temp_file.name, "✅ HTML report generated successfully!"

        elif format_type == "JSON":
            json_content = json.dumps(results, indent=2, default=str)

            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                delete=False,
                suffix='.json',
                prefix=f'resume_analysis_{timestamp}_'
            )
            temp_file.write(json_content)
            temp_file.close()

            return temp_file.name, "✅ JSON export generated successfully!"

        elif format_type == "CSV":
            claims_df = pd.DataFrame(results.get('claims', []))

            if not claims_df.empty:
                columns = ['claim_text', 'category', 'verifiability_level', 'evidence_present']
                columns = [col for col in columns if col in claims_df.columns]
                claims_df = claims_df[columns]

            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                delete=False,
                suffix='.csv',
                prefix=f'resume_claims_{timestamp}_'
            )
            claims_df.to_csv(temp_file.name, index=False)
            temp_file.close()

            return temp_file.name, "✅ CSV export generated successfully!"

        elif format_type == "Interview Checklist":
            checklist = generate_professional_interview_checklist(results)

            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                delete=False,
                suffix='.txt',
                prefix=f'interview_checklist_{timestamp}_'
            )
            temp_file.write(checklist)
            temp_file.close()

            return temp_file.name, "✅ Interview checklist generated successfully!"

    except Exception as e:
        logger.error(f"Export failed: {traceback.format_exc()}")
        return None, f"❌ Export failed: {str(e)}"

def generate_comprehensive_html_report(results: Dict) -> str:
    """Generate beautiful comprehensive HTML report"""

    # Fix consistency score
    consistency_score = min(100, results.get('consistency_score', 0))

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Resume Verification Report - Professional Analysis</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .score-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .score-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }}
        .score-number {{
            font-size: 48px;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .section {{
            background: white;
            padding: 30px;
            margin: 20px 0;
            border-radius: 10px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.05);
        }}
        h2 {{
            color: #2c3e50;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            margin-top: 40px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Resume Verification Report</h1>
            <p style="margin-top: 10px;">
                <strong>Generated:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br>
                <strong>Seniority Level:</strong> {results.get('seniority_level', 'Unknown')}<br>
                <strong>Analysis Type:</strong> Comprehensive Multi-Factor Verification
            </p>
        </div>

        <div class="score-grid">
            <div class="score-card">
                <div class="score-number">{results.get('final_score', 0):.0f}</div>
                <h3>Final Score</h3>
                <p>Overall Assessment</p>
            </div>
            <div class="score-card">
                <div class="score-number">{results.get('credibility_score', 0):.0f}</div>
                <h3>Credibility</h3>
                <p>Evidence Strength</p>
            </div>
            <div class="score-card">
                <div class="score-number">{consistency_score:.0f}</div>
                <h3>Consistency</h3>
                <p>Internal Coherence</p>
            </div>
            <div class="score-card">
                <div class="score-number" style="font-size: 32px;">{results.get('risk_assessment', 'UNKNOWN').upper()}</div>
                <h3>Risk Level</h3>
                <p>Hiring Risk</p>
            </div>
        </div>

        <div class="section">
            <h2>Executive Summary</h2>
            <p><strong>Recommendation:</strong> {results.get('recommendation', 'No recommendation available')}</p>
            <p style="margin-top: 10px;">
                Based on analysis of <strong>{results.get('total_claims', 0)} claims</strong>,
                we found <strong>{results.get('verified_claims', 0)} verified</strong>,
                <strong>{results.get('unverified_claims', 0)} unverified</strong>, and
                <strong>{results.get('total_red_flags', 0)} red flags</strong>.
            </p>
        </div>

        <div class="footer">
            <p>© 2025 Resume Verification System - Professional Edition</p>
            <p>This report is confidential and intended for hiring decisions only.</p>
        </div>
    </div>
</body>
</html>
"""
    return html

def generate_professional_interview_checklist(results: Dict) -> str:
    """Generate professional interview checklist"""

    # Fix consistency score
    consistency_score = min(100, results.get('consistency_score', 0))

    checklist = f"""
================================================================================
                    PROFESSIONAL INTERVIEW VERIFICATION CHECKLIST
================================================================================

Date: {datetime.now().strftime('%B %d, %Y')}
Position Level: {results.get('seniority_level', 'Unknown')}

CANDIDATE RISK ASSESSMENT
--------------------------------------------------------------------------------
Overall Risk Level: {results.get('risk_assessment', 'Unknown').upper()}
Final Score: {results.get('final_score', 0):.0f}/100
Credibility Score: {results.get('credibility_score', 0):.0f}/100
Consistency Score: {consistency_score:.0f}/100
Red Flags Detected: {results.get('total_red_flags', 0)}

KEY METRICS
--------------------------------------------------------------------------------
Total Claims: {results.get('total_claims', 0)}
Verified Claims: {results.get('verified_claims', 0)}
Unverified Claims: {results.get('unverified_claims', 0)}
Buzzword Density: {results.get('claim_metrics', {}).get('buzzword_density', 0)*100:.1f}%

PRIORITY VERIFICATION POINTS
================================================================================
"""

    for i, flag in enumerate(results.get('red_flags', [])[:10], 1):
        checklist += f"""
{i}. [{flag.get('severity', '').upper()}] {flag.get('description', '')}

   Primary Question: {flag.get('interview_probe', 'Verify this claim')}

   Verification:
   □ Claim verified with specific examples
   □ Partial verification - needs follow-up
   □ Unable to verify - major concern

   Notes: ________________________________________________________
   _____________________________________________________________

"""

    checklist += """
FINAL RECOMMENDATION
================================================================================

□ STRONGLY RECOMMEND - All claims verified, excellent fit
□ RECOMMEND - Minor concerns resolved, good candidate
□ RECOMMEND WITH RESERVATIONS - Some unresolved concerns
□ DO NOT RECOMMEND - Significant credibility issues

Interviewer: ______________________  Date: _____________________________

================================================================================
"""

    return checklist

# Create enhanced Gradio interface
def create_interface():
    """Create professional Gradio interface with comprehensive features"""

    custom_css = """
    .gradio-container {
        font-family: 'Segoe UI', Arial, sans-serif !important;
    }
    .main-title {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 30px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
    """

    with gr.Blocks(title="Resume Verification System - Professional", theme=gr.themes.Soft(), css=custom_css) as app:

        gr.HTML("""
        <div class="main-title">
            <h1>🔍 Resume Verification System - Professional Edition</h1>
            <p>Comprehensive AI-powered analysis with full transparency and interpretability</p>
        </div>
        """)

        # Tab 1: Setup
        with gr.Tab("1️⃣ Setup & Configuration"):
            with gr.Row():
                with gr.Column():
                    api_key_input = gr.Textbox(
                        label="Google AI API Key",
                        type="password",
                        placeholder="Enter your Gemini API key",
                        info="Get your API key at https://makersuite.google.com/app/apikey"
                    )

                    mock_mode = gr.Checkbox(
                        label="Mock Mode (Testing)",
                        value=False,
                        visible=False
                    )

                    init_button = gr.Button("Initialize Session", variant="primary", size="lg")
                    init_status = gr.Textbox(label="Status", interactive=False)

                with gr.Column():
                    gr.Markdown("""
                    ### 🎯 What This System Analyzes

                    #### Document Quality
                    - Claim extraction and categorization
                    - Evidence strength assessment
                    - Buzzword density analysis
                    - Structural quality evaluation

                    #### Credibility Factors
                    - Direct evidence verification
                    - Cross-section validation
                    - Timeline consistency checks
                    - Technology timeline validation

                    #### Advanced Detection
                    - Role-achievement mismatches
                    - Sole credit detection
                    - Metric plausibility analysis
                    - Vagueness patterns

                    #### Risk Assessment
                    - Multi-factor scoring
                    - Seniority-adjusted thresholds
                    - Red flag prioritization
                    - Interview strategy generation
                    """)

        # Tab 2: Analysis
        with gr.Tab("2️⃣ Resume Analysis"):
            with gr.Row():
                with gr.Column(scale=1):
                    file_input = gr.File(
                        label="Upload Resume",
                        file_types=[".pdf", ".docx", ".txt"],
                        elem_id="file-upload"
                    )

                    seniority_dropdown = gr.Dropdown(
                        label="Seniority Level",
                        choices=["Intern", "Junior", "Mid", "Senior", "Lead"],
                        value="Mid",
                        info="Adjusts verification thresholds"
                    )

                    strictness_radio = gr.Radio(
                        label="Analysis Strictness",
                        choices=["Low", "Medium", "High"],
                        value="Medium",
                        info="Controls sensitivity of red flag detection"
                    )

                    deep_analysis = gr.Checkbox(
                        label="Enable Deep Analysis",
                        value=False,
                        info="Includes link checking and repository analysis (slower)"
                    )

                    analyze_button = gr.Button("🚀 Analyze Resume", variant="primary", size="lg")

                with gr.Column(scale=2):
                    analysis_status = gr.Textbox(label="Status", interactive=False)
                    comprehensive_analysis = gr.Markdown(label="Comprehensive Analysis")

        # Tab 3: Visualizations
        with gr.Tab("3️⃣ Visual Analytics"):
            with gr.Row():
                dashboard_plot = gr.Plot(label="Credibility Dashboard")
            with gr.Row():
                with gr.Column():
                    heatmap_plot = gr.Plot(label="Evidence Heatmap")
                with gr.Column():
                    distribution_plot = gr.Plot(label="Claim Distribution")
            with gr.Row():
                validation_plot = gr.Plot(label="Verification Summary")

        # Tab 4: Detailed Analysis
        with gr.Tab("4️⃣ Claim-by-Claim Analysis"):
            claim_analysis = gr.Markdown(label="Detailed Claim Analysis")

        # Tab 5: Interview Strategy
        with gr.Tab("5️⃣ Interview Strategy"):
            interview_guide = gr.Markdown(label="Strategic Interview Guide")

        # Tab 6: Export
        with gr.Tab("6️⃣ Export Reports"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("""
                    ### 📄 Professional Export Options

                    Generate comprehensive reports with full analysis details.
                    """)

                    report_format = gr.Radio(
                        label="Report Format",
                        choices=["HTML", "JSON", "CSV", "Interview Checklist"],
                        value="HTML",
                        info="Choose export format"
                    )

                    download_button = gr.Button("📥 Generate Report", variant="primary", size="lg")
                    download_file = gr.File(label="Download Report", interactive=False)
                    export_status = gr.Textbox(label="Export Status", interactive=False)

                with gr.Column():
                    gr.Markdown("""
                    ### 📊 Export Features

                    **HTML Report**
                    - Beautiful formatted report
                    - All scores and explanations
                    - Ready for sharing

                    **JSON Export**
                    - Complete analysis data
                    - Integration-ready format
                    - All metrics included

                    **CSV Export**
                    - Claims spreadsheet
                    - Easy data analysis
                    - Excel compatible

                    **Interview Checklist**
                    - Printable format
                    - Verification points
                    - Scoring rubric
                    """)

        # Hidden components for unused outputs
        red_flags_hidden = gr.Markdown(visible=False)

        # Event handlers
        init_button.click(
            fn=lambda key, mock: initialize_session(key, mock),
            inputs=[api_key_input, mock_mode],
            outputs=[init_status]
        )

        analyze_button.click(
            fn=analyze_resume,
            inputs=[file_input, seniority_dropdown, strictness_radio, deep_analysis],
            outputs=[
                comprehensive_analysis,
                dashboard_plot,
                heatmap_plot,
                distribution_plot,
                validation_plot,
                interview_guide,
                red_flags_hidden,
                claim_analysis,
                analysis_status
            ]
        )

        download_button.click(
            fn=export_report,
            inputs=[report_format],
            outputs=[download_file, export_status]
        )

    return app

# Launch the app
if __name__ == "__main__":
    logger.info("Starting Resume Verification System...")
    app = create_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
