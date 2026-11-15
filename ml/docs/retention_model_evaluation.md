# Retention Model Evaluation Report

## 1. Overview

This report documents the synthetic retention prediction experiments in NeuroLearn.

**Important:** All datasets and metrics in this report are synthetic simulation benchmarks. They are not evidence of real-world student performance.

## 2. Dataset

| Property | Value |
|---|---:|
| Review events | 32,036 |
| Synthetic learners | 250 |
| Temporal test events | 4,806 |
| User-disjoint test events | 4,891 |
| User-disjoint test learners | 38 |

## 3. Temporal Holdout Evaluation

The temporal split sorts review events chronologically and partitions them into training, validation, and testing subsets.

### Test metrics

| Metric | Logistic Regression | Hist Gradient Boosting |
|---|---:|---:|
| Brier Score | 0.15999 | 0.10113 |
| Log Loss | 0.49957 | 0.33484 |
| ROC-AUC | 0.90585 | 0.92295 |
| Accuracy | 83.25% | 86.49% |
| Precision | 80.33% | 84.35% |
| Recall | 96.00% | 95.53% |

Hist Gradient Boosting performs better overall on Brier score, log loss, ROC-AUC, accuracy, and precision. Logistic Regression has marginally higher recall.

## 4. User-Disjoint Evaluation

The user-disjoint split assigns complete learners to training, validation, or test partitions.

| Partition | Learners | Review events |
|---|---:|---:|
| Training | 175 | 22,715 |
| Validation | 37 | 4,430 |
| Testing | 38 | 4,891 |

### Test metrics

| Model | Brier Score | Log Loss | ROC-AUC | Accuracy |
|---|---:|---:|---:|---:|
| Population Prevalence | 0.23885 | 0.67076 | 0.50000 | 60.89% |
| Ebbinghaus Baseline | 0.13877 | 0.50286 | 0.92349 | 78.65% |
| Logistic Regression | 0.15999 | 0.49957 | 0.90585 | 83.25% |
| Hist Gradient Boosting | 0.10113 | 0.33484 | 0.92295 | 86.49% |

Hist Gradient Boosting achieves the strongest overall balance of calibration and classification performance in this synthetic evaluation. Ebbinghaus achieves slightly higher ROC-AUC.

## 5. Split Integrity

The user-disjoint partition was checked for user leakage.

| Check | Overlapping users |
|---|---:|
| Training–Validation | 0 |
| Training–Test | 0 |
| Validation–Test | 0 |

The temporal and user-disjoint test sets are different:

| Check | Result |
|---|---:|
| Temporal test events | 4,806 |
| User-disjoint test events | 4,891 |
| Shared event IDs | 742 |
| Identical test sets | No |

The two evaluation strategies use the same underlying synthetic dataset. Their test sets overlap by 742 events and therefore should not be described as independent datasets.

## 6. Limitations

- All results are synthetic.
- Only 250 simulated learners are represented.
- Synthetic performance does not establish real-world retention prediction accuracy.
- User-disjoint evaluation measures generalization to simulated unseen learners.
- The temporal and user-disjoint test sets share some events.
- Real learner data, external validation, and further calibration checks are required before making real-world performance claims.

## 7. Current Conclusion

Hist Gradient Boosting is the leading candidate among the evaluated retention models on the current synthetic benchmarks.

The user-disjoint split passes the user-isolation checks. These findings support continued ML experimentation, but do not establish production readiness or real-world effectiveness.
