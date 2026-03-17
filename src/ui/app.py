"""
Flask web UI for LLM Debate System
Allows users to view debates, jury verdicts, and results
"""

import os
import sys
import json

# Add parent directory to path to allow imports from project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from flask import Flask, render_template_string, request, jsonify
from datetime import datetime
import logging

from config.config import Config, get_debug_config
from src.llm_client import create_llm_client
from src.agents.debater import ProponentDebater, OpponentDebater
from src.judges.judge import Judge, JuryPanel
from src.orchestrator.debate_orchestrator import DebateOrchestrator

# Setup
app = Flask(__name__)
logger = logging.getLogger(__name__)

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Debate with Jury Panel</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
        }
        
        .content {
            padding: 40px;
        }
        
        .input-section {
            margin-bottom: 40px;
        }
        
        .input-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        
        textarea, input[type="text"], input[type="number"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 5px;
            font-size: 1em;
            font-family: inherit;
        }
        
        textarea:focus, input:focus {
            border-color: #667eea;
            outline: none;
            box-shadow: 0 0 5px rgba(102, 126, 234, 0.3);
        }
        
        textarea {
            min-height: 100px;
            resize: vertical;
        }
        
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .section {
            margin-top: 40px;
            border-top: 2px solid #f0f0f0;
            padding-top: 30px;
        }
        
        .section h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5em;
        }
        
        .debate-round {
            background: #f9f9f9;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }
        
        .round-title {
            font-weight: 600;
            color: #667eea;
            margin-bottom: 15px;
        }
        
        .debater-view {
            margin-bottom: 15px;
            background: white;
            padding: 15px;
            border-radius: 3px;
        }
        
        .debater-a {
            border-left: 3px solid #4CAF50;
        }
        
        .debater-b {
            border-left: 3px solid #f44336;
        }
        
        .debater-name {
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .debater-a .debater-name {
            color: #4CAF50;
        }
        
        .debater-b .debater-name {
            color: #f44336;
        }
        
        .verdict-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 25px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        
        .judge-verdict {
            background: white;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 5px;
            border-top: 3px solid #2196F3;
        }
        
        .judge-id {
            font-weight: 600;
            color: #2196F3;
            margin-bottom: 10px;
        }
        
        .verdict-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 10px;
        }
        
        .info-item {
            background: #f0f0f0;
            padding: 10px;
            border-radius: 3px;
        }
        
        .info-label {
            font-size: 0.85em;
            color: #666;
            text-transform: uppercase;
        }
        
        .info-value {
            font-size: 1.2em;
            font-weight: 600;
            color: #333;
            margin-top: 5px;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
        }
        
        .spinner {
            border: 4px solid #f0f0f0;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .error {
            background: #ffebee;
            color: #c62828;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #c62828;
        }
        
        .success {
            background: #e8f5e9;
            color: #2e7d32;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #2e7d32;
        }
        
        .jury-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .stat-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 5px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 2em;
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎭 LLM Debate with Jury Panel</h1>
            <p>Multi-Agent Adversarial Reasoning with AI Judge Jury</p>
        </div>
        
        <div class="content">
            <div class="input-section">
                <h2>Start a Debate</h2>
                
                <div class="input-group">
                    <label for="question">Question:</label>
                    <textarea id="question" placeholder="Enter a question for debate...">Did the Roman Empire exist at the same time as the Mayan civilization?</textarea>
                </div>
                
                <div class="input-group">
                    <label for="context">Context (Optional):</label>
                    <textarea id="context" placeholder="Provide any background context...">Roman Empire: ~27 BC–476 AD. Mayan civilization: ~2000 BC–1500s AD.</textarea>
                </div>
                
                <div class="input-group">
                    <label for="ground_truth">Ground Truth Answer (Optional):</label>
                    <input type="text" id="ground_truth" placeholder="e.g., Yes, No, Both">
                </div>
                
                <div class="input-group">
                    <label>Configuration:</label>
                    <div>
                        <label style="display: inline; margin-right: 20px;">
                            <input type="checkbox" id="enable_jury" checked> Enable Jury Panel
                        </label>
                        <label style="display: inline;">
                            <input type="checkbox" id="enable_single_judge" checked> Enable Single Judge
                        </label>
                    </div>
                </div>
                
                <button id="start-debate-btn" onclick="startDebate()">Start Debate</button>
            </div>
            
            <div id="results" style="display:none;">
                <div id="loading" class="loading" style="display:none;">
                    <div class="spinner"></div>
                    <p>Running debate simulation...</p>
                </div>
                
                <div id="debate-results"></div>
            </div>
        </div>
    </div>
    
    <script>
        async function startDebate() {
            const question = document.getElementById('question').value;
            const context = document.getElementById('context').value;
            const groundTruth = document.getElementById('ground_truth').value;
            
            if (!question.trim()) {
                alert('Please enter a question');
                return;
            }
            
            document.getElementById('results').style.display = 'block';
            document.getElementById('loading').style.display = 'block';
            document.getElementById('debate-results').innerHTML = '';
            
            try {
                const response = await fetch('/api/debate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        question,
                        context,
                        ground_truth: groundTruth,
                        enable_jury: document.getElementById('enable_jury').checked,
                        enable_single_judge: document.getElementById('enable_single_judge').checked
                    })
                });
                
                const data = await response.json();
                
                document.getElementById('loading').style.display = 'none';
                
                if (!response.ok) {
                    document.getElementById('debate-results').innerHTML = 
                        `<div class="error">${data.error || 'Error running debate'}</div>`;
                    return;
                }
                
                displayResults(data);
            } catch (error) {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('debate-results').innerHTML = 
                    `<div class="error">Error: ${error.message}</div>`;
            }
        }
        
        function displayResults(data) {
            let html = '';
            
            html += `<div class="section">
                <h2>Debate Summary</h2>
                <div class="verdict-card">
                    <p><strong>Question:</strong> ${escapeHtml(data.question)}</p>
                    ${data.ground_truth ? `<p><strong>Ground Truth:</strong> ${escapeHtml(data.ground_truth)}</p>` : ''}
                    <p><strong>Rounds Completed:</strong> ${data.rounds_completed}</p>
                </div>
            </div>`;
            
            if (data.single_judge) {
                html += `<div class="section">
                    <h2>Single Judge Verdict</h2>
                    <div class="judge-verdict">
                        <div class="judge-id">Judge: ${data.single_judge.judge_id}</div>
                        <div class="verdict-info">
                            <div class="info-item">
                                <div class="info-label">Answer</div>
                                <div class="info-value">${escapeHtml(data.single_judge.answer)}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Confidence</div>
                                <div class="info-value">${data.single_judge.confidence}/5</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Correct</div>
                                <div class="info-value">${data.single_judge.correct !== null ? (data.single_judge.correct ? '✓ YES' : '✗ NO') : 'N/A'}</div>
                            </div>
                        </div>
                    </div>
                </div>`;
            }
            
            if (data.jury_panel) {
                const jury = data.jury_panel;
                html += `<div class="section">
                    <h2>Jury Panel Verdict (${jury.num_judges} Judges)</h2>
                    <div class="verdict-card">
                        <div class="verdict-info">
                            <div class="info-item">
                                <div class="info-label">Final Answer</div>
                                <div class="info-value">${escapeHtml(jury.answer)}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Confidence</div>
                                <div class="info-value">${jury.confidence.toFixed(1)}/5</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Unanimous</div>
                                <div class="info-value">${jury.unanimous ? '✓ Yes' : '✗ No'}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Agreement Level</div>
                                <div class="info-value">${(jury.agreement_level * 100).toFixed(0)}%</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Correct</div>
                                <div class="info-value">${jury.correct !== null ? (jury.correct ? '✓ YES' : '✗ NO') : 'N/A'}</div>
                            </div>
                        </div>
                    </div>
                </div>`;
            }
            
            document.getElementById('debate-results').innerHTML = html;
        }
        
        function escapeHtml(text) {
            const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
            return text.replace(/[&<>"']/g, m => map[m]);
        }
    </script>
</body>
</html>
"""


# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main page"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/debate', methods=['POST'])
def run_debate_api():
    """API endpoint to run a debate"""
    try:
        data = request.json
        
        question = data.get('question', '')
        context = data.get('context', '')
        ground_truth = data.get('ground_truth', '')
        enable_jury = data.get('enable_jury', True)
        enable_single_judge = data.get('enable_single_judge', True)
        
        if not question:
            return jsonify({'error': 'Question required'}), 400
        
        # Configuration
        config = get_debug_config()
        config.use_jury = enable_jury
        config.use_single_judge = enable_single_judge
        config.debate.num_rounds = 3  # Keep short for UI
        
        # Create LLM clients
        api_key = config.model.anthropic_api_key if config.model.provider == "anthropic" else config.model.openai_api_key
        
        debater_a_client = create_llm_client(
            model=config.model.debater_model,
            api_key=api_key,
            temperature=config.model.temperature,
            max_tokens=config.model.max_tokens_debater,
            provider=config.model.provider
        )
        
        debater_b_client = create_llm_client(
            model=config.model.debater_model,
            api_key=api_key,
            temperature=config.model.temperature,
            max_tokens=config.model.max_tokens_debater,
            provider=config.model.provider
        )
        
        judge_client = create_llm_client(
            model=config.model.judge_model,
            api_key=api_key,
            temperature=0.3,
            max_tokens=config.model.max_tokens_judge,
            provider=config.model.provider
        )
        
        # Create agents
        debater_a = ProponentDebater(debater_a_client)
        debater_b = OpponentDebater(debater_b_client)
        judge = Judge("judge_single", judge_client) if enable_single_judge else None
        
        # Create jury panel
        jury_panel = None
        if enable_jury:
            jury_clients = [
                create_llm_client(
                    model=config.model.judge_model,
                    api_key=api_key,
                    temperature=0.3,
                    max_tokens=config.model.max_tokens_judge,
                    provider=config.model.provider
                )
                for _ in range(3)
            ]
            judges_list = [Judge(f"judge_{i+1}", c) for i, c in enumerate(jury_clients)]
            jury_panel = JuryPanel(judges_list)
        
        # Run debate
        orchestrator = DebateOrchestrator(config)
        session = orchestrator.create_session(
            question=question,
            debater_a=debater_a,
            debater_b=debater_b,
            judge=judge,
            jury_panel=jury_panel,
            context=context,
            ground_truth_answer=ground_truth
        )
        
        orchestrator.run_complete_debate(session)
        
        # Format response
        result = {
            'question': question,
            'context': context,
            'ground_truth': ground_truth,
            'rounds_completed': session.rounds_completed,
            'single_judge': None,
            'jury_panel': None
        }
        
        if session.judge_verdict:
            result['single_judge'] = session.judge_verdict
        
        if session.jury_consensus:
            result['jury_panel'] = {
                'num_judges': session.jury_consensus['num_judges'],
                'answer': session.jury_consensus['consensus_answer'],
                'confidence': session.jury_consensus['consensus_confidence'],
                'unanimous': session.jury_consensus['disagreement_analysis']['unanimous'],
                'agreement_level': session.jury_consensus['disagreement_analysis']['agreement_level'],
                'correct': session.jury_consensus['consensus_answer'].lower().strip() == ground_truth.lower().strip() if ground_truth else None
            }
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in debate API: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, port=8000, host='0.0.0.0')
