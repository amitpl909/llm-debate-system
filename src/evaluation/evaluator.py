"""
Evaluation framework for analyzing debate results
Computes metrics, comparisons, and statistical analysis
"""

import json
import logging
from typing import Dict, Any, List, Tuple
from collections import defaultdict
import math

logger = logging.getLogger(__name__)


# ============================================================================
# METRICS CALCULATION
# ============================================================================

class EvaluationMetrics:
    """Calculate evaluation metrics"""
    
    @staticmethod
    def calculate_accuracy(predictions: List[bool]) -> float:
        """Calculate accuracy: (TP + TN) / Total"""
        if not predictions:
            return 0.0
        correct = sum(predictions)
        return correct / len(predictions)
    
    @staticmethod
    def calculate_precision_recall_f1(tp: int, fp: int, tn: int, fn: int) -> Dict[str, float]:
        """Calculate precision, recall, and F1 score"""
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            "precision": precision,
            "recall": recall,
            "f1": f1
        }
    
    @staticmethod
    def calculate_confidence_calibration(predictions: List[Tuple[bool, int]]) -> Dict[str, Any]:
        """
        Analyze confidence calibration
        predictions: List of (is_correct, confidence) tuples
        """
        if not predictions:
            return {}
        
        # Group by confidence level
        by_confidence = defaultdict(list)
        for is_correct, confidence in predictions:
            by_confidence[confidence].append(is_correct)
        
        calibration = {}
        for conf_level in sorted(by_confidence.keys()):
            correct_list = by_confidence[conf_level]
            accuracy = sum(correct_list) / len(correct_list) if correct_list else 0.0
            count = len(correct_list)
            calibration[f"confidence_{conf_level}"] = {
                "expected_accuracy": conf_level / 5.0,  # 5-point scale
                "actual_accuracy": accuracy,
                "sample_count": count,
                "calibration_error": abs((conf_level / 5.0) - accuracy)
            }
        
        avg_calibration_error = sum(
            v["calibration_error"] for v in calibration.values()
        ) / len(calibration) if calibration else 0.0
        
        return {
            "by_confidence_level": calibration,
            "average_calibration_error": avg_calibration_error
        }
    
    @staticmethod
    def calculate_statistical_significance(
        group1_accuracies: List[float],
        group2_accuracies: List[float],
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """
        Calculate statistical significance using t-test
        Higher accuracy difference = lower p-value = more significant
        """
        if not group1_accuracies or not group2_accuracies:
            return {"significant": False, "p_value": 1.0}
        
        mean1 = sum(group1_accuracies) / len(group1_accuracies)
        mean2 = sum(group2_accuracies) / len(group2_accuracies)
        
        var1 = sum((x - mean1) ** 2 for x in group1_accuracies) / len(group1_accuracies)
        var2 = sum((x - mean2) ** 2 for x in group2_accuracies) / len(group2_accuracies)
        
        se = math.sqrt((var1 / len(group1_accuracies)) + (var2 / len(group2_accuracies)))
        
        if se == 0:
            t_stat = 0
        else:
            t_stat = abs(mean1 - mean2) / se
        
        # Simplified p-value estimation
        # This is a rough approximation; for production, use scipy.stats
        p_value = 1.0 / (1.0 + t_stat ** 2)
        
        return {
            "mean_group1": mean1,
            "mean_group2": mean2,
            "t_statistic": t_stat,
            "p_value": p_value,
            "significant": p_value < alpha,
            "alpha": alpha
        }


# ============================================================================
# RESULTS AGGREGATOR
# ============================================================================

class ResultsAggregator:
    """Aggregate results across multiple debates"""
    
    def __init__(self):
        self.debates = []
        self.debate_results = {
            "direct_qa": [],
            "self_consistency": [],
            "single_judge": [],
            "jury_panel": []
        }
    
    def add_debate_result(self, 
                         debate_id: str,
                         question: str,
                         ground_truth: str,
                         direct_qa_answer: str,
                         direct_qa_correct: bool,
                         self_consistency_answer: str,
                         self_consistency_correct: bool,
                         judge_answer: str,
                         judge_correct: bool,
                         judge_confidence: int,
                         jury_answer: str,
                         jury_correct: bool,
                         jury_confidence: float,
                         jury_unanimous: bool,
                         jury_agreement_level: float,
                         num_judges: int = 3) -> None:
        """Add a debate result to aggregation"""
        
        result = {
            "debate_id": debate_id,
            "question": question,
            "ground_truth": ground_truth,
            "direct_qa": {
                "answer": direct_qa_answer,
                "correct": direct_qa_correct
            },
            "self_consistency": {
                "answer": self_consistency_answer,
                "correct": self_consistency_correct
            },
            "single_judge": {
                "answer": judge_answer,
                "correct": judge_correct,
                "confidence": judge_confidence
            },
            "jury_panel": {
                "answer": jury_answer,
                "correct": jury_correct,
                "confidence": jury_confidence,
                "unanimous": jury_unanimous,
                "agreement_level": jury_agreement_level,
                "num_judges": num_judges
            }
        }
        
        self.debates.append(result)
        
        # Update method-specific results
        self.debate_results["direct_qa"].append(direct_qa_correct)
        self.debate_results["self_consistency"].append(self_consistency_correct)
        self.debate_results["single_judge"].append(judge_correct)
        self.debate_results["jury_panel"].append(jury_correct)
        
        logger.info(f"Added debate result: {debate_id}")
    
    def generate_summary_statistics(self) -> Dict[str, Any]:
        """Generate summary statistics"""
        
        metrics = EvaluationMetrics()
        
        summary = {
            "total_debates": len(self.debates),
            "method_accuracies": {},
            "method_comparisons": {},
            "jury_analysis": {}
        }
        
        # Method accuracies
        for method, results in self.debate_results.items():
            if results:
                accuracy = metrics.calculate_accuracy(results)
                summary["method_accuracies"][method] = accuracy
                logger.info(f"{method}: {accuracy:.2%} accuracy")
        
        # Comparisons
        qa_acc = metrics.calculate_accuracy(self.debate_results["direct_qa"])
        sc_acc = metrics.calculate_accuracy(self.debate_results["self_consistency"])
        judge_acc = metrics.calculate_accuracy(self.debate_results["single_judge"])
        jury_acc = metrics.calculate_accuracy(self.debate_results["jury_panel"])
        
        summary["method_comparisons"] = {
            "jury_vs_judge": {
                "jury_accuracy": jury_acc,
                "judge_accuracy": judge_acc,
                "improvement": jury_acc - judge_acc,
                "improvement_percent": (jury_acc - judge_acc) / judge_acc * 100 if judge_acc > 0 else 0
            },
            "jury_vs_direct_qa": {
                "jury_accuracy": jury_acc,
                "direct_qa_accuracy": qa_acc,
                "improvement": jury_acc - qa_acc,
                "improvement_percent": (jury_acc - qa_acc) / qa_acc * 100 if qa_acc > 0 else 0
            },
            "jury_vs_self_consistency": {
                "jury_accuracy": jury_acc,
                "self_consistency_accuracy": sc_acc,
                "improvement": jury_acc - sc_acc,
                "improvement_percent": (jury_acc - sc_acc) / sc_acc * 100 if sc_acc > 0 else 0
            },
            "judge_vs_direct_qa": {
                "judge_accuracy": judge_acc,
                "direct_qa_accuracy": qa_acc,
                "improvement": judge_acc - qa_acc,
                "improvement_percent": (judge_acc - qa_acc) / qa_acc * 100 if qa_acc > 0 else 0
            }
        }
        
        # Jury-specific analysis
        jury_unanimous_count = sum(
            1 for d in self.debates if d["jury_panel"]["unanimous"]
        )
        jury_agreement_levels = [
            d["jury_panel"]["agreement_level"] for d in self.debates
        ]
        
        summary["jury_analysis"] = {
            "unanimous_debates": jury_unanimous_count,
            "unanimous_ratio": jury_unanimous_count / len(self.debates) if self.debates else 0,
            "average_agreement_level": sum(jury_agreement_levels) / len(jury_agreement_levels) if jury_agreement_levels else 0,
            "num_judges": self.debates[0]["jury_panel"]["num_judges"] if self.debates else 0
        }
        
        return summary
    
    def generate_comparison_table(self) -> str:
        """Generate formatted comparison table"""
        
        summary = self.generate_summary_statistics()
        
        table = "\n" + "=" * 80 + "\n"
        table += "METHOD ACCURACY COMPARISON\n"
        table += "=" * 80 + "\n"
        
        table += f"{'Method':<30} {'Accuracy':<15} {'Count':<10}\n"
        table += "-" * 80 + "\n"
        
        for method, acc in summary["method_accuracies"].items():
            count = len(self.debate_results[method])
            table += f"{method:<30} {acc:>6.2%}            {count:<10}\n"
        
        table += "\n" + "=" * 80 + "\n"
        table += "JURY PANEL ANALYSIS\n"
        table += "=" * 80 + "\n"
        table += f"Total Debates: {summary['total_debates']}\n"
        table += f"Unanimous Verdict Rate: {summary['jury_analysis']['unanimous_ratio']:.2%}\n"
        table += f"Average Judge Agreement: {summary['jury_analysis']['average_agreement_level']:.2%}\n"
        table += f"Number of Judges: {summary['jury_analysis']['num_judges']}\n"
        
        table += "\n" + "=" * 80 + "\n"
        table += "JURY vs SINGLE JUDGE\n"
        table += "=" * 80 + "\n"
        jury_judge = summary["method_comparisons"]["jury_vs_judge"]
        table += f"Jury Accuracy:     {jury_judge['jury_accuracy']:.2%}\n"
        table += f"Judge Accuracy:    {jury_judge['judge_accuracy']:.2%}\n"
        table += f"Improvement:       {jury_judge['improvement_percent']:+.2f}%\n"
        
        return table
    
    def to_json(self, filepath: str) -> None:
        """Save results to JSON"""
        data = {
            "total_debates": len(self.debates),
            "debates": self.debates,
            "summary": self.generate_summary_statistics()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Results saved to {filepath}")
    
    def to_csv(self, filepath: str) -> None:
        """Save results to CSV"""
        import csv
        
        if not self.debates:
            logger.warning("No debates to export")
            return
        
        fieldnames = [
            "debate_id",
            "ground_truth",
            "direct_qa_answer",
            "direct_qa_correct",
            "self_consistency_answer",
            "self_consistency_correct",
            "judge_answer",
            "judge_correct",
            "judge_confidence",
            "jury_answer",
            "jury_correct",
            "jury_confidence",
            "jury_unanimous",
            "jury_agreement_level"
        ]
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for debate in self.debates:
                row = {
                    "debate_id": debate["debate_id"],
                    "ground_truth": debate["ground_truth"],
                    "direct_qa_answer": debate["direct_qa"]["answer"],
                    "direct_qa_correct": debate["direct_qa"]["correct"],
                    "self_consistency_answer": debate["self_consistency"]["answer"],
                    "self_consistency_correct": debate["self_consistency"]["correct"],
                    "judge_answer": debate["single_judge"]["answer"],
                    "judge_correct": debate["single_judge"]["correct"],
                    "judge_confidence": debate["single_judge"]["confidence"],
                    "jury_answer": debate["jury_panel"]["answer"],
                    "jury_correct": debate["jury_panel"]["correct"],
                    "jury_confidence": debate["jury_panel"]["confidence"],
                    "jury_unanimous": debate["jury_panel"]["unanimous"],
                    "jury_agreement_level": debate["jury_panel"]["agreement_level"]
                }
                writer.writerow(row)
        
        logger.info(f"Results exported to {filepath}")


# ============================================================================
# DEBATE QUALITY ANALYZER
# ============================================================================

class DebateQualityAnalyzer:
    """Analyze quality of individual debates"""
    
    @staticmethod
    def analyze_debate_transcript(transcript: str) -> Dict[str, Any]:
        """Analyze debate transcript quality"""
        
        analysis = {
            "word_count": len(transcript.split()),
            "num_paragraphs": transcript.count('\n\n'),
            "has_cot_reasoning": "reasoning" in transcript.lower() or "because" in transcript.lower(),
            "has_evidence": any(word in transcript.lower() for word in ["study", "research", "evidence", "data"]),
            "debate_turns": transcript.count("ROUND")
        }
        
        return analysis
    
    @staticmethod
    def identify_failure_modes(
        question: str,
        ground_truth: str,
        jury_answer: str,
        jury_agreement_level: float
    ) -> Dict[str, Any]:
        """Identify why jury might fail on a question"""
        
        is_correct = jury_answer.lower().strip() == ground_truth.lower().strip()
        
        failure_analysis = {
            "is_correct": is_correct,
            "potential_issues": []
        }
        
        if not is_correct:
            if jury_agreement_level < 0.5:
                failure_analysis["potential_issues"].append("High disagreement among judges")
            
            if len(question) > 200:
                failure_analysis["potential_issues"].append("Question is complex/long")
            
            if any(word in question.lower() for word in ["not", "doesn't", "can't", "won't"]):
                failure_analysis["potential_issues"].append("Negation in question may cause confusion")
        
        return failure_analysis
