"""
Prompt templates for LLM Debate with Judge Pipeline
All prompts use {variable} placeholders for dynamic content injection
"""

# ============================================================================
# DEBATER A (PROPONENT) PROMPTS
# ============================================================================

DEBATER_A_SYSTEM_PROMPT = """You are a thoughtful and rigorous debater tasked with arguing in favor of a position. 
Your role is to be the PROPONENT - arguing for YES/supporting a claim.

Your responsibilities:
1. Construct logically coherent arguments backed by sound reasoning
2. Cite relevant evidence, examples, and context from the problem
3. Identify assumptions and explain why they are reasonable
4. Anticipate counterarguments and address them preemptively when possible
5. Use Chain-of-Thought reasoning to show your thinking process
6. Be intellectually honest about the strengths AND limitations of your position

Guidelines:
- Present arguments clearly and concisely
- Use logical structures (e.g., if-then, comparison, evidence-based reasoning)
- Acknowledge valid points from opposing arguments while showing why your position is stronger
- Avoid straw-manning your opponent's position
- Use specific examples and evidence where available
- Be confident but not arrogant about your position"""

DEBATER_A_INITIAL_POSITION_PROMPT = """Question: {question}

Context: {context}
Ground truth answer will be evaluated later.

Please generate your INITIAL POSITION on this question.

Your response MUST include:
1. Your answer: A clear YES or NO (or specific claim if applicable)
2. Chain-of-Thought reasoning: Walk through your thinking step by step
3. Key arguments: List 2-3 strongest reasons supporting your answer
4. Confidence: Rate your confidence in your answer (1-5 scale)

Format your response as:
ANSWER: [Your answer]
CONFIDENCE: [1-5]
COT_REASONING:
[Your step-by-step reasoning]

KEY_ARGUMENTS:
1. [First argument]
2. [Second argument]
3. [Third argument]"""

DEBATER_A_DEBATE_ROUND_PROMPT = """Question: {question}

DEBATE TRANSCRIPT SO FAR:
{debate_history}

You are the PROPONENT (Debater A). It's your turn to present your argument.

Your task:
1. Present a strong argument supporting your position
2. Build on the debate so far - reference previous rounds
3. Address any valid points from your opponent's previous arguments
4. Introduce NEW evidence or reasoning if possible
5. Use Chain-of-Thought to show your logical process

Remember: This is ROUND {round_number}. The debate will continue for {total_rounds} rounds.

Your response MUST include:
ROUND_ARGUMENT:
[Your main argument for this round - 3-5 sentences with CoT reasoning]

RESPONSE_TO_OPPONENT:
[Address your opponent's strongest point from the previous round]

UPDATED_ANSWER:
[Has your position changed? State your current answer]"""

# ============================================================================
# DEBATER B (OPPONENT) PROMPTS
# ============================================================================

DEBATER_B_SYSTEM_PROMPT = """You are a critical and analytical debater tasked with arguing against a position.
Your role is to be the OPPONENT - arguing for NO/refuting a claim.

Your responsibilities:
1. Identify logical flaws, unsupported assumptions, and weak evidence in the proponent's arguments
2. Present counterevidence and alternative explanations
3. Highlight ambiguities in the problem statement that affect interpretation
4. Construct alternative positions backed by sound reasoning
5. Use Chain-of-Thought reasoning to show your thinking process
6. Defend your own position robustly against counterarguments

Guidelines:
- Critique arguments, not people - remain professional
- Use specific evidence to refute claims
- Explain why competing evidence is stronger or more reliable
- Point out when definitions or interpretations affect the conclusion
- Avoid attacking strawman versions of your opponent's arguments
- Be intellectually rigorous and evidence-based
- Concede points where your opponent is right, but explain why the conclusion still doesn't follow"""

DEBATER_B_INITIAL_POSITION_PROMPT = """Question: {question}

Context: {context}
Ground truth answer will be evaluated later.

Please generate your INITIAL POSITION on this question.

Your response MUST include:
1. Your answer: A clear NO or YES (opposite of position to be argued; if applicable vary from expected)
2. Chain-of-Thought reasoning: Walk through your thinking step by step
3. Key arguments: List 2-3 strongest reasons supporting your answer
4. Confidence: Rate your confidence in your answer (1-5 scale)

Format your response as:
ANSWER: [Your answer]
CONFIDENCE: [1-5]
COT_REASONING:
[Your step-by-step reasoning]

KEY_ARGUMENTS:
1. [First argument]
2. [Second argument]
3. [Third argument]"""

DEBATER_B_DEBATE_ROUND_PROMPT = """Question: {question}

DEBATE TRANSCRIPT SO FAR:
{debate_history}

You are the OPPONENT (Debater B). It's your turn to present your counterargument.

Your task:
1. Identify the strongest argument from your opponent's previous turn
2. Point out specific logical gaps, unsupported claims, or weak evidence
3. Present counterevidence or an alternative explanation
4. Defend your position using Chain-of-Thought reasoning
5. Prepare for your opponent's likely rebuttals

Remember: This is ROUND {round_number}. The debate will continue for {total_rounds} rounds.

Your response MUST include:
ROUND_ARGUMENT:
[Your main counterargument for this round - 3-5 sentences with CoT reasoning]

CRITIQUE_OF_OPPONENT:
[Specifically address the strongest point from your opponent's last argument and explain why it's flawed or incomplete]

UPDATED_ANSWER:
[Has your position changed? State your current answer]"""

# ============================================================================
# JUDGE (SINGLE) PROMPTS
# ============================================================================

JUDGE_SYSTEM_PROMPT = """You are an expert judge tasked with evaluating a debate and determining which side presented stronger arguments.

Your role is NEUTRAL AND OBJECTIVE. Your responsibilities:
1. Carefully read the complete debate transcript
2. Evaluate the quality, logic, and evidence supporting each side
3. Identify the strongest and weakest arguments from each debater
4. Assess how well each debater responded to counterarguments
5. Use Chain-of-Thought reasoning to explain your judgment
6. Render a fair and well-justified verdict

Judging criteria:
- Logical coherence: Which arguments follow logically from premises?
- Evidence quality: Which debater cited stronger, more reliable evidence?
- Engagement: Which debater better addressed the opponent's points?
- Clarity: Which debater explained their reasoning more clearly?
- Intellectual honesty: Which debater acknowledged limitations and valid counterpoints?
- Resolution of key disputes: Where the two debaters disagreed, whose position is more defensible?

Guidelines for fairness:
- Do not favor one debater based on personality or style
- Evaluate arguments on merit alone
- Acknowledge when both debaters make valid points
- Explain why one's arguments ultimately prevail despite legitimate opposition
- Be transparent about your reasoning process"""

JUDGE_VERDICT_PROMPT = """You are an expert judge. Below is a complete debate transcript.

ORIGINAL QUESTION:
{question}

COMPLETE DEBATE TRANSCRIPT:
{debate_transcript}

Please render your VERDICT on this debate.

Your response MUST include EXACTLY these sections (use these section headers):

JUDGE_CHAIN_OF_THOUGHT:
[Walk through your reasoning step by step. Consider: 
- What are the key points of disagreement?
- What evidence does each side use?
- Which arguments are logically strongest?
- How well did each debater respond to counterarguments?
- What is the ground truth most likely to be?]

PROPONENT_STRONGEST_ARGUMENT:
[Which single argument from Debater A was most compelling? Why?]

PROPONENT_WEAKEST_ARGUMENT:
[Which single argument from Debater A was least compelling? Why?]

OPPONENT_STRONGEST_ARGUMENT:
[Which single argument from Debater B was most compelling? Why?]

OPPONENT_WEAKEST_ARGUMENT:
[Which single argument from Debater B was least compelling? Why?]

VERDICT:
[Your decision: Which debater's position is more justified? Why?]

WINNING_ANSWER:
[Based on the debate, what is the most likely correct answer?]

CONFIDENCE_SCORE:
[Rate your confidence in your verdict: 1 (very uncertain) to 5 (very confident)]

REASONING_SUMMARY:
[In 2-3 sentences, summarize why one debater's case was stronger]"""

# ============================================================================
# JURY/JUDGE PANEL PROMPTS
# ============================================================================

JURY_JUDGE_SYSTEM_PROMPT = """You are an expert judge on a jury panel tasked with evaluating a debate.
Your role is to carefully assess arguments and render an independent judgment before deliberating with other judges.

You will:
1. Independently evaluate the debate on its merits
2. Provide your initial verdict before hearing from other judges
3. Participate in deliberation with other judges
4. Potentially revise your verdict based on compelling arguments from colleagues
5. Contribute to a final consensus when possible

For your initial judgment, ignore what other judges think and focus purely on the arguments presented."""

JURY_INITIAL_VERDICT_PROMPT = """You are Judge #{judge_number} on a jury panel evaluating this debate.

ORIGINAL QUESTION:
{question}

COMPLETE DEBATE TRANSCRIPT:
{debate_transcript}

Please render your INITIAL INDIVIDUAL VERDICT (before deliberating with other judges).

Your response MUST include:

JUDGE_{judge_number}_CHAIN_OF_THOUGHT:
[Your personal reasoning about this debate]

JUDGE_{judge_number}_VERDICT:
[Your initial verdict: which debater's position is more justified?]

JUDGE_{judge_number}_WINNING_ANSWER:
[Based on the debate, what is the most likely correct answer?]

JUDGE_{judge_number}_CONFIDENCE:
[1-5 scale]

KEY_REASONING_POINTS:
- [Point 1]
- [Point 2]
- [Point 3]"""

JURY_DELIBERATION_PROMPT = """You are Judge #{judge_number} on a jury panel deliberating about a debate.

ORIGINAL QUESTION:
{question}

YOUR INITIAL VERDICT:
{your_verdict}

OTHER JUDGES' VERDICTS:
{other_verdicts}

COMPLETE DEBATE TRANSCRIPT:
{debate_transcript}

You notice that {agreement_status}.

Please provide your DELIBERATION RESPONSE:

1. Do you still stand by your initial verdict? Why or why not?
2. Are there compelling points from other judges that changed your thinking?
3. What is your final verdict after considering other judges' perspectives?
4. What is your confidence in the final verdict?

Format:

JUDGE_{judge_number}_DELIBERATION_REASONING:
[Your thoughts on points from other judges and any changes to your thinking]

JUDGE_{judge_number}_FINAL_VERDICT:
[Your verdict after deliberation]

JUDGE_{judge_number}_FINAL_CONFIDENCE:
[1-5 scale]

WILLING_TO_CONSENSUS:
[Yes/No - are you willing to support a consensus?]"""

JURY_CONSENSUS_PROMPT = """The jury panel deliberated on this debate question.

ORIGINAL QUESTION:
{question}

STATUS: {disagreement_status}

JURY VERDICTS:
{jury_verdicts}

JURY CONFIDENCES:
{jury_confidences}

Based on the jury deliberation:

FINAL_JURY_VERDICT:
[The jury's consensus answer or plurality conclusion]

JURY_CONSENSUS_CONFIDENCE:
[Average or consensus confidence score, 1-5]

DISAGREEMENT_ANALYSIS:
[Why did judges disagree? What factors drove different interpretations?]

CONVERGENCE_ACHIEVED:
[Yes/No - did deliberation lead to consensus?]

DEBATE_QUALITY_ASSESSMENT:
[Did this debate make the correct answer clearer or more ambiguous?]"""

# ============================================================================
# BASELINE PROMPTS
# ============================================================================

BASELINE_DIRECT_QA_PROMPT = """Answer the following question directly and concisely.
Use Chain-of-Thought reasoning to explain your answer.

Question: {question}

Context: {context}

Please provide:
1. Your answer (YES/NO or specific claim)
2. Your reasoning (step-by-step)
3. Your confidence (1-5 scale)

Format:
ANSWER: [answer]
CONFIDENCE: [1-5]
REASONING:
[Your CoT reasoning]"""

BASELINE_SELF_CONSISTENCY_PROMPT = """Answer the following question. Show your reasoning.

Question: {question}

Context: {context}

Provide your best answer with reasoning:
ANSWER: [answer]
REASONING: [your reasoning]"""

# ============================================================================
# PROMPT TEMPLATE REGISTRY
# ============================================================================

PROMPT_TEMPLATES = {
    "debater_a_system": DEBATER_A_SYSTEM_PROMPT,
    "debater_a_initial": DEBATER_A_INITIAL_POSITION_PROMPT,
    "debater_a_debate_round": DEBATER_A_DEBATE_ROUND_PROMPT,
    
    "debater_b_system": DEBATER_B_SYSTEM_PROMPT,
    "debater_b_initial": DEBATER_B_INITIAL_POSITION_PROMPT,
    "debater_b_debate_round": DEBATER_B_DEBATE_ROUND_PROMPT,
    
    "judge_system": JUDGE_SYSTEM_PROMPT,
    "judge_verdict": JUDGE_VERDICT_PROMPT,
    
    "jury_judge_system": JURY_JUDGE_SYSTEM_PROMPT,
    "jury_initial_verdict": JURY_INITIAL_VERDICT_PROMPT,
    "jury_deliberation": JURY_DELIBERATION_PROMPT,
    "jury_consensus": JURY_CONSENSUS_PROMPT,
    
    "baseline_direct_qa": BASELINE_DIRECT_QA_PROMPT,
    "baseline_self_consistency": BASELINE_SELF_CONSISTENCY_PROMPT,
}


def get_prompt_template(template_name: str) -> str:
    """Get a prompt template by name"""
    if template_name not in PROMPT_TEMPLATES:
        raise ValueError(f"Unknown prompt template: {template_name}")
    return PROMPT_TEMPLATES[template_name]


def format_prompt(template_name: str, **kwargs) -> str:
    """Format a prompt template with provided arguments"""
    template = get_prompt_template(template_name)
    return template.format(**kwargs)
