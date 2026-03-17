#!/usr/bin/env python3
"""Quick test to verify StrategyQA dataset loading"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.data_loader import create_dataset

print("Loading StrategyQA dataset from GitHub...")
try:
    questions = create_dataset('commonsense_qa', 200)
    print(f'✓ Successfully loaded {len(questions)} questions from StrategyQA')
    if questions:
        print(f'\n📝 First question: {questions[0].question[:100]}...')
        print(f'✓ Answer: {questions[0].answer}')
        print(f'✓ Source: {questions[0].source}')
except Exception as e:
    print(f'✗ Error loading dataset: {str(e)}')
    import traceback
    traceback.print_exc()
