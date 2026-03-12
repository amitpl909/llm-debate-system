# LLM Debate System - Complete Step-by-Step Implementation Guide

## Overview

This guide provides a complete, step-by-step walkthrough to implement and deploy the LLM Debate with Multi-Agent Judge Jury Panel system from scratch. It covers all components from configuration to experimentation to evaluation.

---

## STEP 1: PROJECT SETUP (5 minutes)

### 1.1 Create Project Directory
```bash
mkdir llm_debate_system
cd llm_debate_system
```

### 1.2 Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 1.3 Install Dependencies
```bash
# Copy requirements.txt to project directory, then:
pip install -r requirements.txt
```

### 1.4 Set Environment Variables
```bash
# Windows (Command Prompt)
set OPENAI_API_KEY=sk-your-key-here

# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-your-key-here"

# macOS/Linux
export OPENAI_API_KEY="sk-your-key-here"
```

### 1.5 Verify Installation
```bash
python -c "import openai; print('OpenAI SDK installed')"
python -c "from flask import Flask; print('Flask installed')"
```

---

## STEP 2: UNDERSTAND THE ARCHITECTURE (10 minutes)

### 2.1 Four Phases of the System

**Phase 1 - Initialization** (5 min per question)
- Debater A generates initial YES/NO position with reasoning
- Debater B generates opposite initial position
- Check if they agree (consensus) → Skip to Phase 3 if unanimous

**Phase 2 - Multi-Round Debate** (10-15 min per question)
- Round 1-N: Debater A argues, then Debater B responds
- Each debater has access to full debate history
- Debate continues for N rounds (default: 5)
- Early stopping if both converge to same answer for 2 consecutive rounds

**Phase 3 - Judgment** (5-10 min per question)
- Single Judge evaluates full debate transcript:
  - Analyzes both sides' arguments
  - Identifies strongest/weakest from each
  - Renders verdict with 1-5 confidence score
- Jury Panel (3+ Judges) conducts:
  - Independent evaluation (no communication)
  - Disagreement analysis
  - Deliberation if not unanimous
  - Reach consensus through voting

**Phase 4 - Evaluation** (1 min per question)
- Compare verdicts to ground truth
- Calculate accuracy metrics
- Record all results for analysis

### 2.2 Component Overview

```
User provides question
    ↓
Phase 1: Initialize (Debaters A & B generate positions)
    ↓ (if disagree)
Phase 2: Debate (N rounds of argument exchange)
    ↓
Phase 3: Judgment
    ├─ Single Judge evaluates
    └─ Jury Panel evaluates (3+ judges with deliberation)
    ↓
Phase 4: Evaluate (Compare to ground truth)
    ↓
Results & Metrics
```

---

## STEP 3: CONFIGURATION (5 minutes)

### 3.1 Create config/config.py

Key settings to customize:
```python
# config/config.py

ModelConfig:
  debater_model = "gpt-3.5-turbo"  # Cheaper for development
  judge_model = "gpt-4"             # Better judgment
  temperature = 0.7                 # Debaters: More creative
  
DebateConfig:
  num_rounds = 5                    # 5 rounds for final, 3 for debug
  enable_early_stopping = True
  
JuryConfig:
  num_judges = 3                    # 3+ judges per assignment
  enable_deliberation = True        # BONUS FEATURE
  
BaselineConfig:
  enable_direct_qa = True           # Baseline 1
  enable_self_consistency = True    # Baseline 2
  self_consistency_samples = 5
```

### 3.2 Create .env File (Optional)
```bash
# .env
OPENAI_API_KEY=sk-...
DEBUG_MODE=False
SAMPLE_SIZE=100
```

---

## STEP 4: IMPLEMENT LLM CLIENT (10 minutes)

### 4.1 Create src/llm_client.py

Key classes:
- `LLMClient` - Abstract base class
- `OpenAIClient` - Implements OpenAI API with retry logic
- `MockLLMClient` - For testing without API calls

### 4.2 Test the Client
```python
from src.llm_client import create_llm_client

client = create_llm_client(model="gpt-3.5-turbo")
response = client.generate(
    system_prompt="You are helpful.",
    user_prompt="Say hello."
)
print(response)
```

---

## STEP 5: IMPLEMENT DEBATERS (15 minutes)

### 5.1 Create src/agents/debater.py

Key classes:
- `ProponentDebater` (Debater A) - Argues for YES
- `OpponentDebater` (Debater B) - Argues for NO

Methods:
- `generate_initial_position(question, context)` → DebaterPosition
- `generate_argument(question, debate_history, round_number)` → Argument dict

### 5.2 Test Debaters
```python
from src.agents.debater import ProponentDebater, OpponentDebater
from src.llm_client import create_llm_client

client_a = create_llm_client("gpt-3.5-turbo")
client_b = create_llm_client("gpt-3.5-turbo")

debater_a = ProponentDebater(client_a)
debater_b = OpponentDebater(client_b)

question = "Is climate change real?"
pos_a = debater_a.generate_initial_position(question)
pos_b = debater_b.generate_initial_position(question)

print(f"A: {pos_a.answer} (confidence: {pos_a.confidence})")
print(f"B: {pos_b.answer} (confidence: {pos_b.confidence})")
```

---

## STEP 6: IMPLEMENT JUDGES & JURY (15 minutes)

### 6.1 Create src/judges/judge.py

Key classes:
- `Judge` - Single judge evaluation
- `JuryPanel` - Multi-judge system with deliberation ✨

Key methods:
- `Judge.render_verdict(question, debate_transcript)` → JudgeVerdict
- `JuryPanel.conduct_initial_evaluation()` → Dict of verdicts
- `JuryPanel.analyze_disagreement()` → Agreement metrics
- `JuryPanel.conduct_deliberation()` → Judges discuss
- `JuryPanel.reach_consensus()` → Final jury verdict

### 6.2 Test Judge & Jury
```python
from src.judges.judge import Judge, JuryPanel
from src.llm_client import create_llm_client

# Single Judge
judge_client = create_llm_client("gpt-4")
judge = Judge("judge_1", judge_client)

# Jury Panel
jury_judges = [
    Judge(f"judge_{i+1}", create_llm_client("gpt-4"))
    for i in range(3)
]
jury = JuryPanel(jury_judges, enable_deliberation=True)

# Test jury evaluation
verdicts = jury.conduct_initial_evaluation(
    question="Is climate changing?",
    debate_transcript="[debate text]"
)

disagreement = jury.analyze_disagreement()
print(f"Agreement level: {disagreement['agreement_level']:.1%}")

if not disagreement['unanimous']:
    jury.conduct_deliberation(
        question="Is climate changing?",
        debate_transcript="[debate text]",
        rounds=2
    )

consensus = jury.reach_consensus(
    question="Is climate changing?",
    debate_transcript="[debate text]"
)
print(f"Jury verdict: {consensus['consensus_answer']}")
```

---

## STEP 7: IMPLEMENT ORCHESTRATOR (15 minutes)

### 7.1 Create src/orchestrator/debate_orchestrator.py

Key class:
- `DebateOrchestrator` - Coordinates all phases

Key methods:
- `create_session()` - Creates a debate session
- `phase1_initialization()` - Get initial positions
- `phase2_debate()` - Run debate rounds
- `phase3_judgment()` - Get judge/jury verdicts
- `phase4_evaluation()` - Compare against ground truth
- `run_complete_debate()` - Run all phases

### 7.2 Test Orchestrator
```python
from config.config import Config
from src.orchestrator.debate_orchestrator import DebateOrchestrator
from src.agents.debater import ProponentDebater, OpponentDebater
from src.judges.judge import Judge, JuryPanel
from src.llm_client import create_llm_client

config = Config()

# Create agents
debater_a = ProponentDebater(create_llm_client("gpt-3.5-turbo"))
debater_b = OpponentDebater(create_llm_client("gpt-3.5-turbo"))
judge = Judge("judge_1", create_llm_client("gpt-4"))

jury_judges = [
    Judge(f"judge_{i+1}", create_llm_client("gpt-4"))
    for i in range(3)
]
jury = JuryPanel(jury_judges)

# Create orchestrator
orchestrator = DebateOrchestrator(config)

# Create session
session = orchestrator.create_session(
    question="Is climate change real?",
    debater_a=debater_a,
    debater_b=debater_b,
    judge=judge,
    jury_panel=jury,
    ground_truth_answer="Yes"
)

# Run full debate
results = orchestrator.run_complete_debate(session)

print(f"Jury Answer: {results['jury_panel']['answer']}")
print(f"Jury Correct: {results['jury_panel']['correct']}")
```

---

## STEP 8: IMPLEMENT EVALUATION (10 minutes)

### 8.1 Create src/evaluation/evaluator.py

Key classes:
- `EvaluationMetrics` - Calculate metrics
- `ResultsAggregator` - Aggregate results across debates
- `DebateQualityAnalyzer` - Analyze debate quality

### 8.2 Test Evaluation
```python
from src.evaluation.evaluator import ResultsAggregator

aggregator = ResultsAggregator()

aggregator.add_debate_result(
    debate_id="d1",
    question="Is climate real?",
    ground_truth="Yes",
    direct_qa_answer="Yes",
    direct_qa_correct=True,
    self_consistency_answer="Yes",
    self_consistency_correct=True,
    judge_answer="Yes",
    judge_correct=True,
    judge_confidence=5,
    jury_answer="Yes",
    jury_correct=True,
    jury_confidence=4.5,
    jury_unanimous=True,
    jury_agreement_level=1.0,
    num_judges=3
)

summary = aggregator.generate_summary_statistics()
print(summary)

# Print comparison
print(aggregator.generate_comparison_table())

# Save results
aggregator.to_json("results.json")
aggregator.to_csv("results.csv")
```

---

## STEP 9: IMPLEMENT DATA LOADER (10 minutes)

### 9.1 Create src/data/data_loader.py

Key classes:
- `DebateQuestion` - Data model for questions
- `DataLoader` - Load from JSON
- `SampleDatasets` - Built-in sample data

### 9.2 Load Data
```python
from src.data.data_loader import create_dataset, SampleDatasets

# Load sample dataset
questions = create_dataset(
    dataset_type="commonsense_qa",
    sample_size=10,
    seed=42
)

# Print sample
for q in questions[:3]:
    print(f"Q: {q.question}")
    print(f"A: {q.answer}\n")
```

---

## STEP 10: IMPLEMENT MAIN RUNNER (10 minutes)

### 10.1 Create main.py

Key class:
- `ExperimentRunner` - Runs complete experiments
- `BaselineRunner` - Implements baseline methods

### 10.2 Run Experiments
```bash
# Debug mode (small sample)
python main.py --debug

# Production mode (full experiments)
python main.py
```

---

## STEP 11: BUILD WEB UI (Optional, 15 minutes)

### 11.1 Create src/ui/app.py

Flask web UI with:
- Question input
- Real-time debate visualization
- Judge verdicts display
- Jury panel results

### 11.2 Run Web UI
```bash
python src/ui/app.py
# Visit: http://localhost:8000
```

---

## STEP 12: RUN COMPLETE EXPERIMENT (30-60 minutes)

### 12.1 Quick Test (Debug Mode)
```bash
# Uses 5 questions, 3 rounds, lower costs
python main.py --debug

# Verify:
# - logs/debate_system.log - Check for errors
# - logs/session_*.json - Debate transcripts
# - outputs/results_*.json - Results
```

### 12.2 Full Experiment (Production Mode)
```bash
# Uses 150 questions, 5 rounds, full evaluation
python main.py

# Expected time: 2-4 hours (depends on API)
# Expected cost: $600-800 with GPT-4 for judges
```

### 12.3 Analyze Results
```bash
python -c "
import json
with open('outputs/results_20260311_120000.json') as f:
    data = json.load(f)
    summary = data['summary']
    print('Jury Accuracy:', summary['method_accuracies']['jury_panel'])
    print('Judge Accuracy:', summary['method_accuracies']['single_judge'])
    print('Improvement:', summary['method_comparisons']['jury_vs_judge']['improvement_percent'])
"
```

---

## STEP 13: GENERATE BLOG POST & REPORT (30 minutes)

### 13.1 Create REPORT.md

Include:
1. **Methodology** (1 page)
   - System architecture
   - Task domain
   - Baselines
   - Configuration

2. **Experiments** (3 pages)
   - Experimental design
   - Results tables
   - Statistical tests
   - Jury dynamics analysis

3. **Analysis** (1 page)
   - 3-5 debate transcripts
   - Failure mode analysis
   - Connection to prior work

4. **Prompt Engineering** (variable)
   - Iteration history
   - Key design decisions
   - What changed based on failures

5. **Appendix**
   - Complete prompt templates (all 6 prompts)
   - Formatted with variable placeholders

### 13.2 Key Sections for Blog Post

**Methodology Section** should explain:
- The 4-phase pipeline
- Why jury panel matters (BONUS feature)
- Model choices and temperature settings
- Task selection (commonsense QA)

**Experiments Section** should show:
- Accuracy comparison table (all 4 methods)
- Jury dynamics: unanimity, agreement levels
- Correlation of disagreement with accuracy
- Deliberation impact analysis

**Analysis Section** should include:
- Summary of 3-5 real debate transcripts
- Where judges agreed vs disagreed
- Why some debates failed
- Connection to Irving et al. (debate improves reasoning)

---

## STEP 14: CREATE GITHUB REPOSITORY

### 14.1 Initialize Git
```bash
git init
git add -A
git commit -m "Initial commit: LLM Debate with Jury Panel System"

# Add remote
git remote add origin https://github.com/yourusername/llm-debate-system.git
git push -u origin main
```

### 14.2 Repository Structure
```
llm-debate-system/
├── README.md
├── REPORT.md                # 5-page blog post
├── requirements.txt
├── main.py
├── config/config.py
├── prompts/templates.py
├── src/
│   ├── llm_client.py
│   ├── agents/debater.py
│   ├── judges/judge.py
│   ├── orchestrator/debate_orchestrator.py
│   ├── evaluation/evaluator.py
│   ├── data/data_loader.py
│   └── ui/app.py
├── logs/                    # Generated during runs
├── outputs/                 # Results & metrics
└── .gitignore
```

---

## STEP 15: SUBMIT ASSIGNMENT

### 15.1 Submission Checklist

- [ ] Code runs without errors
- [ ] All 4 phases (initialization, debate, judgment, evaluation) implemented
- [ ] Jury panel with 3+ judges ✨ (BONUS)
- [ ] Single judge baseline ✓
- [ ] Direct QA baseline ✓
- [ ] Self-Consistency baseline ✓
- [ ] 100+ questions tested
- [ ] Jury deliberation implemented and tested ✓
- [ ] Results saved as JSON with full transcripts
- [ ] REPORT.md created (5 pages + appendix)
- [ ] All prompts included in appendix
- [ ] README.md with setup instructions
- [ ] GitHub repository created
- [ ] Web UI functional (optional but recommended)

### 15.2 Final Verification
```bash
# 1. Test code runs
python main.py --debug

# 2. Check results exist
ls -la logs/
ls -la outputs/

# 3. Verify REPORT.md exists
wc -w REPORT.md  # Should be ~2500 words

# 4. Push to GitHub
git push origin main
```

### 15.3 Submit Via Portal
- Submit GitHub repository link
- Include: README.md, REPORT.md, code, results

---

## DEBUGGING & TROUBLESHOOTING

### API Rate Limits
```python
# In config/config.py, increase retry delay:
retry_delay: float = 2.0  # Increase from 1.0
max_retries: int = 5      # Increase from 3
```

### Out of Memory / Slow Execution
```python
# Use smaller sample for testing:
python main.py --debug

# Or reduce in config:
sample_size = 10  # Start small, scale up
num_rounds = 3    # Minimum per assignment
```

### LLM Calls Not Working
```bash
# Verify API key
echo $OPENAI_API_KEY  # Should print your key

# Test API directly
python -c "
import openai
openai.api_key = 'sk-...'
print(openai.Model.list())
"
```

### Results Not Saved
```bash
# Verify directories exist
mkdir -p logs outputs

# Check permissions
chmod 755 logs outputs

# Rerun with debug mode
python main.py --debug
```

---

## EXPECTED OUTCOMES

After completing all steps:

1. **Working System**
   - Runs debates on 100+ questions
   - Jury panel with 3+ judges functioning
   - Single judge + baselines for comparison
   - Results saved to JSON/CSV

2. **Results**
   - Jury accuracy: ~70-75% on commonsense QA
   - Single judge accuracy: ~68-72%
   - Direct QA accuracy: ~60-65%
   - Self-Consistency: ~65-70%
   - Jury > Single Judge statistically significant

3. **Documentation**
   - 5-page blog post with findings
   - Complete prompt appendix
   - README with reproduction steps
   - All code on GitHub

4. **Bonus Points** ✨
   - 3+ judge jury panel: +15%
   - Web UI: Functional for graders
   - Comprehensive analysis: Well-written insights

---

## COST ESTIMATION

| Phase | Calls | Model | Cost |
|-------|-------|-------|------|
| Initialization | 1 × 2 judges | GPT-3.5 | $0.01 |
| Debate | 5 × 2 debaters | GPT-3.5 | $0.05 |
| Judge | 1 judge | GPT-4 | $0.30 |
| Jury | 3 judges + deliberation | GPT-4 | $1.00 |
| Baselines | 2 methods | GPT-3.5 | $0.10 |
| **Total per question** | **~15 calls** | **Mixed** | **~$1.50** |
| **For 100 questions** | | | **~$150** |
| **For 150 questions** | | | **~$225** |
| **With contingency** | | | **~$300** |

---

## TIMELINE

| Task | Time | Cumulative |
|------|------|-----------|
| Setup & Configuration | 30 min | 30 min |
| Understand Architecture | 10 min | 40 min |
| Implement LLM Client | 10 min | 50 min |
| Implement Debaters | 15 min | 65 min |
| Implement Judges | 15 min | 80 min |
| Implement Orchestrator | 15 min | 95 min |
| Implement Evaluation | 10 min | 105 min |
| Implement Data Loader | 10 min | 115 min |
| Implement Main Runner | 10 min | 125 min |
| Web UI (Optional) | 15 min | 140 min |
| Run Debug Experiment | 15 min | 155 min |
| Run Full Experiment | 2-4 hours | 2h 20min - 4h 20min |
| Write Blog Post | 60 min | 3h 20min - 5h 20min |
| GitHub Setup | 10 min | 3h 30min - 5h 30min |

**Total Development Time**: 3.5-5.5 hours coding + analysis

---

## SUCCESS CRITERIA

✅ Code compiles and runs without errors  
✅ 4 phases implemented and functioning  
✅ 3+ judge jury panel with deliberation (BONUS)  
✅ All baselines implemented  
✅ 100+ questions tested  
✅ Results show jury ≥ single judge accuracy  
✅ Blog post covers methodology, experiments, analysis  
✅ All prompts documented in appendix  
✅ GitHub repository with clear README  
✅ Web UI functional (bonus)  

---

Good luck with your implementation! 🚀
