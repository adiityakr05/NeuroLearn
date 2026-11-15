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
| Brier Score | 0.14989 | 0.06583 |
| Log Loss | 0.47089 | 0.24086 |
| ROC-AUC | 0.95300 | 0.96128 |
| Accuracy | 89.28% | 91.59% |
| Precision | 85.54% | 90.38% |
| Recall | 94.55% | 93.09% |

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
| Training�Validation | 0 |
| Training�Test | 0 |
| Validation�Test | 0 |

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


## 8. Probability Calibration and Reliability Analysis

Platt scaling was integrated into the temporal experiment for Logistic Regression and Histogram Gradient Boosting.

**Calibration protocol**
- Calibrators were fitted exclusively on temporal validation predictions and targets (4,805 events).
- The final temporal test set (4,806 events) was not used during calibration fitting.
- Raw benchmark metrics in Section 3 remain unchanged.
- Reliability reports use 10 equal-width probability bins.
- ECE is weighted average calibration error; MCE is the largest occupied-bin calibration error.
- Brier score measures mean squared probability error; lower is better.

### Temporal Test Calibration Results

| Model | Raw ECE | Calibrated ECE | Raw MCE | Calibrated MCE | Raw Brier | Calibrated Brier |
|---|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 0.23570 | 0.04046 | 0.38363 | 0.21592 | 0.14989 | 0.07907 |
| Hist Gradient Boosting | 0.03051 | 0.01024 | 0.03922 | 0.08067 | 0.06583 | 0.06519 |

### Interpretation

- Logistic Regression probability calibration improved substantially after Platt scaling.
- Histogram Gradient Boosting already showed comparatively strong raw calibration and improved further.
- Calibrated Brier score improved substantially for Logistic Regression and slightly for Histogram Gradient Boosting.
- Calibration does not guarantee improved ranking or classification accuracy; it adjusts probability estimates.
- Calibration performance remains specific to this synthetic temporal test distribution.

**Reliability limitation:** ECE and MCE depend on binning and sample composition. They should not be interpreted as universal calibration guarantees.

All calibration results are synthetic simulation benchmarks and are not evidence of real-world student retention.
