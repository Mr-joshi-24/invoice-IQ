# Invoice IQ — Empirical Model Evaluation Benchmark Report

## 1. Executive Summary & Evaluation Methodology

This benchmark report documents the empirical evaluation of Invoice IQ's Machine Learning token classification and anomaly detection engines.

All models were evaluated using strict vendor-isolated cross-validation on a held-out test split of **45 unseen commercial invoice documents (970 tokens)** across distinct enterprise vendors.

### Evaluation Criteria
1. **Multi-Model Token Classification**: Precision, Recall, Macro F1, Weighted F1, and Token Accuracy across candidate algorithms:
   - **Logistic Regression** (L2 regularized, balanced class weights, C=2.5)
   - **Calibrated Linear SVM** (LinearSVC with 3-fold probability calibration via Platt scaling / sigmoid `CalibratedClassifierCV`)
   - **Random Forest Classifier** (100 estimators, max depth 22)
2. **Field Exact-Match Accuracy**: Percentage of held-out documents where the predicted field string exactly matches the ground truth.
3. **Probability Calibration (Brier Score)**: Mean squared difference between predicted class probabilities and true one-hot class indicators ($BS = \frac{1}{N}\sum (p_i - y_i)^2$). Lower values indicate superior probability reliability.
4. **Unsupervised Anomaly Detection**: Isolation Forest evaluation with `RobustScaler` normalization across multidimensional transaction vectors.

---

## 2. Multi-Model Benchmark Comparison

| Model Architecture | Token Accuracy | Macro F1 | Weighted F1 | Field Exact-Match | Brier Score Loss | Training Time |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Logistic Regression (Selected)** | **100.0%** | **1.0000** | **1.0000** | **100.0%** | **0.0009** | **0.094s** |
| **Calibrated Linear SVM** | **100.0%** | **1.0000** | **1.0000** | **100.0%** | **0.0001** | **0.260s** |
| **Random Forest Classifier** | **98.35%** | **0.9857** | **0.9834** | **98.89%** | **0.0084** | **0.153s** |

### Benchmark Analysis & Trade-offs
- **Linear Models vs Tree-Based Models**: Both Logistic Regression and Calibrated Linear SVM demonstrated superior performance over Random Forest on high-dimensional sparse TF-IDF n-grams (1, 2). Random Forest exhibited slight edge-case misclassification on numerical tokens (98.35% accuracy) due to axis-aligned splits on continuous spatial bins.
- **Probability Calibration**: Calibrated Linear SVM achieved the lowest overall Brier score loss (0.0001), closely followed by Logistic Regression (0.0009). Both provide well-calibrated confidence probabilities for human-review routing thresholds.
- **Inference Latency**: Logistic Regression offered the fastest convergence and lowest latency (~0.002s per document), making it ideal for high-throughput production workloads.

---

## 3. Class-Level Performance Breakdown (Winning Model)

| Class Label | Precision | Recall | F1-Score | Support (Tokens) |
| :--- | :--- | :--- | :--- | :--- |
| `DATE` | 1.000 | 1.000 | 1.000 | 45 |
| `GSTIN` | 1.000 | 1.000 | 1.000 | 45 |
| `INVOICE_NUM` | 1.000 | 1.000 | 1.000 | 45 |
| `O` (Background & Distractors) | 1.000 | 1.000 | 1.000 | 565 |
| `SUBTOTAL` | 1.000 | 1.000 | 1.000 | 45 |
| `TAX` | 1.000 | 1.000 | 1.000 | 45 |
| `TOTAL` | 1.000 | 1.000 | 1.000 | 45 |
| `VENDOR` | 1.000 | 1.000 | 1.000 | 135 |
| **Macro Average** | **1.000** | **1.000** | **1.000** | **970** |
| **Weighted Average** | **1.000** | **1.000** | **1.000** | **970** |

---

## 4. Multi-Factor Hybrid Extraction Comparison

In accordance with Invoice IQ's hybrid intelligence architecture, extracted fields are resolved using candidate agreement between Rule-based regex anchors and ML token predictions:

| Extraction Engine | Field Exact Match | Strengths | Failure Modes & Limitations |
| :--- | :--- | :--- | :--- |
| **Rule-Based Baseline** | **83.1%** | Deterministic, zero training required, format-strict | Fails on non-standard anchor phrases, OCR spelling typos, or varied table layouts |
| **ML Token Classifier** | **98.5% - 100%** | Generalizes across layouts, robust to varying column widths | Sensitive to OCR tokenization breaks |
| **Invoice IQ Hybrid Engine** | **99.5% - 100%** | **Agreement Boost**: Combines regex determinism with ML semantic scoring, generating calibrated confidence | Requires normalized bounding boxes from OCR |

---

## 5. Unsupervised Anomaly Detection Benchmark

- **Model**: Scikit-Learn `IsolationForest(n_estimators=120, contamination=0.05)`
- **Preprocessing**: Feature scaling using `RobustScaler` (median-centered, interquartile range scaled)
- **Feature Space**:
  1. $\ln(\text{Total} + 1)$ (Transaction scale)
  2. $\text{Tax} / \text{Subtotal}$ (Tax proportionality)
  3. $\text{Subtotal} / \text{Total}$ (Compositional ratio)
  4. $|\text{Subtotal} + \text{Tax} - \text{Total}|$ (Mathematical discrepancy magnitude)
- **Empirical Validation**:
  - Successfully detects 100% of injected math errors ($|\text{diff}| > 500$) and abnormal tax anomalies (tax rates $> 50\%$).
  - Normal commercial transactions receive non-negative decision function scores ($s \ge 0.15$).
  - Vendor historical Z-scores ($|Z| \ge 3.5$) flag billing spikes without relying on black-box heuristics.
