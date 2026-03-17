# LLM Debate with Multi-Agent Judge Jury Panel

A complete system for running adversarial multi-agent debates between LLM agents, judged by single judges and jury panels. This project implements the core architecture from [Irving et al. (2018)](https://arxiv.org/abs/1805.00899) on AI Safety via Debate, extended with a novel **3+ judge jury panel with deliberation** (BONUS FEATURE).

## Overview

### Architecture

The system implements a 4-phase pipeline:

1. **Phase 1 - Initialization**: Both debaters generate independent initial positions on the question
2. **Phase 2 - Multi-Round Debate**: Debaters engage in N rounds of argumentation with access to debate history
3. **Phase 3 - Judgment**: 
   - Single judge independently evaluates the debate
   - Jury panel (3+ judges) conducts independent evaluation, deliberation, and consensus
4. **Phase 4 - Evaluation**: Compare verdicts against ground truth and compute metrics

### Bonus Feature: Jury Panel with Deliberation

Instead of a single judge, the system implements a jury panel of 3+ LLM judges that:
- Conduct independent evaluations of the debate
- Analyze disagreement among judges
- Engage in deliberation rounds to potentially reach consensus
- Compare jury accuracy to single-judge accuracy
- Analyze how panel disagreement correlates with question difficulty

## Project Structure

```
llm_debate_system/
├── src/
│   ├── llm_client.py              # LLM API client (OpenAI, Mock)
│   ├── agents/
│   │   └── debater.py             # Proponent & Opponent debater classes
│   ├── judges/
│   │   └── judge.py               # Single Judge & Jury Panel classes
│   ├── orchestrator/
│   │   └── debate_orchestrator.py  # Main debate coordinator
│   ├── evaluation/
│   │   └── evaluator.py           # Metrics & results analysis
│   ├── data/
│   │   └── data_loader.py         # Dataset loading utilities
│   └── ui/
│       └── app.py                 # Flask web UI (optional)
├── config/
│   └── config.py                  # Configuration & hyperparameters
├── prompts/
│   └── templates.py               # Prompt templates for all agents
├── main.py                        # Main experiment runner
├── requirements.txt               # Python dependencies
├── README.md                      # This file
├── BLOG_POST.md                   # 5-page research blog post
├── PROMPTS_APPENDIX.md            # Complete final prompts
├── logs/                          # Debate transcripts & logs
└── outputs/                       # Results & metrics
```

## Quick Start

### 1. Setup Environment

```bash
# Clone repository
cd llm_debate_system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
# Set Anthropic API key (recommended)
export ANTHROPIC_API_KEY="sk-ant-..."  # On Windows: set ANTHROPIC_API_KEY=sk-ant-...

# Alternatively, create a .env file in project root:
# ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 3. Run Experiments

```bash
# Debug mode (5 questions, 3 rounds)
python main.py --debug

# Production mode (200 questions, 5 rounds)
python main.py
```

### 4. Run Web UI

```bash
# Start the Flask web application
python src/ui/app.py

# Then open browser to http://localhost:8000
```

## Configuration

Edit `config/config.py` to customize:

### Model Configuration
```python
ModelConfig:
  - provider: "anthropic" (default) or "openai"
  - debater_model: "claude-3-haiku-20240307"
  - judge_model: "claude-3-haiku-20240307"
  - debater_temperature: 0.7
  - judge_temperature: 0.3
  - max_tokens_debater: 500
  - max_tokens_judge: 800
```

### Debate Configuration
```python
DebateConfig:
  - num_rounds: 5 (N >= 3 as per assignment)
  - enable_early_stopping: True
  - convergence_rounds: 2
  - sample_size: 5 (debug) or 200 (production)
```

### Jury Panel Configuration
```python
JuryConfig:
  - num_judges: 3  # 3+ judges for jury
  - enable_deliberation: True
  - deliberation_rounds: 2
  - voting_strategy: "majority"
```

### Baseline Configuration
```python
BaselineConfig:
  - enable_direct_qa: True
  - enable_self_consistency: True
  - self_consistency_samples: 5
```

## Prompts

All prompts are stored as templates in `prompts/templates.py` with variable placeholders:

### Key Prompts

#### Debater A (Proponent)
- System prompt establishes role and guidelines
- Initial position prompt: Generate answer + CoT reasoning + key arguments
- Debate round prompt: Generate argument for specific round with debate history

#### Debater B (Opponent)
- Similar structure but focuses on counterarguments and critique
- Identifies flaws in opponent's reasoning
- Presents alternative evidence

#### Judge (Single)
- Analyzes both debaters' arguments
- Identifies strongest/weakest arguments from each side
- Renders verdict with confidence (1-5 scale)

#### Jury Panel (BONUS)
- Each judge independently evaluates
- Judges conduct deliberation if not unanimous
- Reach consensus through voting

## Experimental Setup

### Datasets

The system includes built-in datasets:

1. **Commonsense QA** (10 sample questions included)
   - Roman Empire vs Mayan civilization overlaps
   - Penguin vs salmon speed
   - Tomato as fruit
   - Animal comparisons
   - Historical facts

2. **Fact Verification** (5 sample questions)
   - Vitamin C and common cold
   - Coffee and heart disease
   - Vaccines and autism
   - GMO safety
   - Climate change attribution

### Baselines

The system compares jury performance against:

1. **Direct QA**: Single LLM call with CoT (no debate)
2. **Self-Consistency**: N independent calls with majority voting
3. **Single Judge**: Traditional debate + single judge (no jury)

### Experiments

Run these experiments and report:
- Accuracy of each method
- Confidence calibration of judges
- Agreement level of jury panel
- Impact of deliberation on consensus quality
- Correlation of disagreement with question difficulty

## Logging & Results

### Debate Transcripts

Full debate transcripts saved as JSON in `logs/`:
```json
{
  "session_id": "session_cqa_1",
  "question": "Did the Roman Empire exist...",
  "ground_truth": "Yes",
  "initial_positions_match": false,
  "rounds_completed": 3,
  "judge_verdict": {...},
  "jury_consensus": {...}
}
```

### Results Files

After experiments, results saved to `outputs/`:
- `results_TIMESTAMP.json` - Complete results with all details
- `results_TIMESTAMP.csv` - Tabular format for analysis

## Evaluation Metrics

### Accuracy
- Simple % correct across methods
- Computed for all 4 methods: Direct QA, Self-Consistency, Single Judge, Jury Panel

### Jury-Specific Metrics
- **Unanimity Rate**: % of debates where all judges agree
- **Agreement Level**: Average agreement percentage across debates
- **Confidence Calibration**: Expected vs actual accuracy at each confidence level

### Statistical Significance
- t-tests comparing jury accuracy to single judge
- p-values for determining if improvements are statistically significant

## Key Results Expected

Based on prior work (Irving et al., Liang et al., Kenton et al.):

1. **Jury Panel > Single Judge**: Multiple judges with deliberation should outperform single judge
2. **Jury Panel ≥ Self-Consistency**: Structured debate should match or exceed multiple independent samples
3. **Agreement Correlates with Accuracy**: Questions where judges disagree tend to be harder

## Web UI / Flask Application

### Starting the Web UI

```bash
# Ensure you're in the virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the Flask application from project root
python src/ui/app.py
```

You should see output like:
```
 * Serving Flask app 'app'
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8000
 * Press CTRL+C to quit
```

### Accessing the UI

Open your web browser and navigate to:
- **Local (Recommended)**: http://localhost:8000
- **Network Access**: http://192.168.1.X:8000 (replace X with your machine's IP)

### Using the Web UI

1. **Enter a Question**: Type any yes/no question in the text area
   - Example: "Can a penguin swim faster than a salmon?"
   - Example: "Is the Earth flat?"

2. **Add Context** (Optional): Provide background information
   - Helps judges better understand the question
   - Example: "Average penguin swimming speed is 20 mph, salmon is 30 mph"

3. **Provide Ground Truth** (Optional): Enter the correct answer
   - Used to verify accuracy after debate concludes
   - Example: "No"

4. **Configure Options**:
   - ☑ **Enable Jury Panel**: Run with 3 judges conducting deliberation for consensus
   - ☑ **Enable Single Judge**: Run with single judge baseline for comparison

5. **Click "Start Debate"**: System will:
   - Initialize 2 debaters with independent positions
   - Run 3 debate rounds (shorter than production 5 rounds for UI speed)
   - Generate individual judge verdicts
   - Conduct jury deliberation if enabled
   - Display results with accuracy comparison

### UI Display Sections

1. **Debate Summary Panel**
   - Shows rounds completed and current status
   - Displays ground truth if provided
   - Shows accuracy against ground truth

2. **Judge Verdicts Panel**
   - Individual verdict from each judge
   - Confidence score (1-5 scale)
   - Judge reasoning and analysis

3. **Jury Panel Results** (if enabled)
   - Consensus answer from jury
   - Unanimity percentage
   - Agreement level
   - Number of judges who agreed

4. **Method Comparison** (if baselines enabled)
   - Accuracy percentages for each method
   - Helps evaluate debate system effectiveness

### UI Troubleshooting

**Port 8000 Already in Use:**
```python
# Option 1: Use a different port in src/ui/app.py (line ~595)
app.run(debug=True, port=8001, host='0.0.0.0')

# Option 2: Kill process on Linux/Mac
lsof -ti:8000 | xargs kill -9

# Option 3: On Windows, find process using port
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Chrome Security Warning for Localhost:**
- This is normal - click "Proceed" or "Advanced"
- Only appears on fresh browser sessions

**API Key Not Found Error:**
- Verify `.env` file exists in project root (not in llm_debate_system folder)
- Check key is set: `echo %ANTHROPIC_API_KEY%` (Windows) or `echo $ANTHROPIC_API_KEY` (Linux/Mac)
- Restart Flask after changing environment variables

**Import or ModuleNotFoundError:**
- Ensure virtual environment is activated
- Reinstall requirements: `pip install -r requirements.txt`

## Code Examples

### Running a Single Debate

```python
from config.config import Config, get_debug_config
from src.llm_client import create_llm_client
from src.agents.debater import ProponentDebater, OpponentDebater
from src.judges.judge import Judge
from src.orchestrator.debate_orchestrator import DebateOrchestrator

# Setup with debug configuration
config = get_debug_config()
api_key = config.model.anthropic_api_key

# Create LLM clients with Claude 3 Haiku
debater_a_client = create_llm_client(
    model="claude-3-haiku-20240307",
    api_key=api_key,
    temperature=0.7,
    max_tokens=500,
    provider="anthropic"
)
debater_b_client = create_llm_client(
    model="claude-3-haiku-20240307",
    api_key=api_key,
    temperature=0.7,
    max_tokens=500,
    provider="anthropic"
)
judge_client = create_llm_client(
    model="claude-3-haiku-20240307",
    api_key=api_key,
    temperature=0.3,
    max_tokens=800,
    provider="anthropic"
)

# Create agents
debater_a = ProponentDebater(debater_a_client)
debater_b = OpponentDebater(debater_b_client)
judge = Judge("judge_1", judge_client)

# Create orchestrator and session
orchestrator = DebateOrchestrator(config)
session = orchestrator.create_session(
    question="Is climate change real?",
    debater_a=debater_a,
    debater_b=debater_b,
    judge=judge,
    ground_truth_answer="Yes"
)

# Run debate
orchestrator.run_complete_debate(session)
```

### Creating a Jury Panel

```python
from src.judges.judge import JuryPanel, Judge

# Create multiple judge clients with Claude 3 Haiku
judges = [
    Judge(f"judge_{i}", create_llm_client(
        model="claude-3-haiku-20240307",
        api_key=api_key,
        temperature=0.3,
        max_tokens=800,
        provider="anthropic"
    ))
    for i in range(3)
]

# Create jury panel with deliberation
jury = JuryPanel(
    judges=judges,
    enable_deliberation=True,
    voting_strategy="majority"
)

# Run jury evaluation workflow
initial_verdicts = jury.conduct_initial_evaluation(question, debate_transcript)
disagreement_analysis = jury.analyze_disagreement()
jury.conduct_deliberation(question, debate_transcript, rounds=2)
final_consensus = jury.reach_consensus(question, debate_transcript)

print(f"Final Answer: {final_consensus['consensus_answer']}")
print(f"Unanimous: {final_consensus['disagreement_analysis']['unanimous']}")
print(f"Agreement Level: {final_consensus['disagreement_analysis']['agreement_level']:.1%}")
```

## API Costs

Estimated costs with Claude 3 Haiku (Anthropic):

- **Input tokens**: $0.80 per 1M tokens
- **Output tokens**: $4.00 per 1M tokens

Single debate estimate (~50 questions per full workflow):
- Input: ~8,000-10,000 tokens
- Output: ~2,000-3,000 tokens
- **Cost per debate: ~$0.05-0.10** (extremely cost-effective)

Full production experiment (200 questions):
- **Estimated: $10-20 total** (compared to $600-800 with GPT-4)
- Claude 3 Haiku provides excellent performance at minimal cost

## Troubleshooting

### API Key Issues
- **Error: ANTHROPIC_API_KEY not found**
  - Create `.env` file in project root with: `ANTHROPIC_API_KEY=sk-ant-...`
  - Or set environment variable: `export ANTHROPIC_API_KEY="sk-ant-..."`
  - On Windows: `set ANTHROPIC_API_KEY=sk-ant-...`
  - Restart Flask/main.py after setting environment variables

### API Rate Limits
- System includes automatic retry with exponential backoff
- Adjust `retry_delay` in `config.py` to increase wait time between retries
- Claude 3 Haiku has generous rate limits for most use cases

### Flask Web UI Issues
- **Port 8000 already in use**: Change port in `src/ui/app.py` or kill process on port 8000
- **ModuleNotFoundError (flask, config, etc)**: Ensure virtual environment is activated
- **Import errors**: Reinstall dependencies: `pip install -r requirements.txt`
- **Blank page loads**: Clear browser cache and reload, check browser console for errors

### Script Execution Issues
- **Out of Memory**: Reduce `sample_size` in config or run with `--debug` flag
- **No results file created**: Check `outputs/` directory exists, verify API key is correct
- **Session logs not saved**: Ensure `logs/` directory is writable

### Debugging
- Run with `--debug` flag: `python main.py --debug` (5 questions, faster testing)
- Check logs in `logs/debate_system.log` for detailed execution logs
- Check individual session files in `logs/session_*.json` for debate transcripts
- Enable debug mode in `config.py` for verbose console output

## References

1. Irving, G., Christiano, P., & Amodei, D. (2018). "AI Safety via Debate". arXiv:1805.00899
2. Snell, C. et al. (2024). "Scaling LLM Test-Time Compute Optimally". ICLR 2025
3. Liang, T. et al. (2024). "Encouraging Divergent Thinking through Multi-Agent Debate". EMNLP 2024
4. Kenton, Z. et al. (2024). "On Scalable Oversight with Weak LLMs Judging Strong LLMs". NeurIPS 2024
5. Kalra, N. et al. (2025). "VERDICT: A Library for Scaling Judge-Time Compute". Haize Labs

## License

MIT License - See LICENSE file

## Authors

**Author**: Amit Paul  
**Course**: NLP (Natural Language Processing) - Assignment 2: LLM Debate with Judge Pipeline  
**Date**: 3/16/2026  
**Instructor**: Dr. Peyman Najafirad  
**TA**: Mohammad Bahrami

Implementation uses Claude/Copilot for code generation assistance (disclosed per assignment policies).
