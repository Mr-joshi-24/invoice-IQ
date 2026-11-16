import json
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score, precision_score, recall_score, brier_score_loss
from ml.datasets.synthetic_generator import generate_dataset
from ml.src.features import prepare_dataset_for_training


def evaluate_field_exact_match(
    model,
    vectorizer,
    test_docs: List[Dict[str, Any]]
) -> Tuple[float, Dict[str, float]]:
    """
    Evaluates end-to-end exact-match accuracy for extracted invoice fields
    against ground truth annotations on held-out test documents.
    """
    field_mapping = {
        "GSTIN": "gstin",
        "INVOICE_NUM": "invoice_number",
        "DATE": "invoice_date",
        "SUBTOTAL": "subtotal",
        "TAX": "tax_amount",
        "TOTAL": "total_amount"
    }
    field_stats = {k: {"correct": 0, "total": 0} for k in field_mapping.values()}
    total_correct = 0
    total_fields = 0

    classes = list(model.classes_)

    for doc in test_docs:
        doc_tokens = doc.get("tokens", [])
        if not doc_tokens:
            continue
        feat_strings = prepare_dataset_for_training([doc])[0]
        token_vecs = vectorizer.transform(feat_strings)
        doc_preds = model.predict(token_vecs)
        probs = model.predict_proba(token_vecs)

        gt = doc.get("ground_truth", {})
        pred_map = {}

        for i, pred_cls in enumerate(doc_preds):
            if pred_cls != "O" and pred_cls in classes:
                cls_idx = classes.index(pred_cls)
                prob = probs[i][cls_idx]
                if pred_cls not in pred_map or prob > pred_map[pred_cls]["prob"]:
                    pred_map[pred_cls] = {"text": doc_tokens[i]["text"], "prob": prob}

        for ml_cls, gt_key in field_mapping.items():
            if gt_key in gt:
                field_stats[gt_key]["total"] += 1
                total_fields += 1
                if ml_cls in pred_map and pred_map[ml_cls]["text"] == gt[gt_key]:
                    field_stats[gt_key]["correct"] += 1
                    total_correct += 1

    overall_acc = round(total_correct / total_fields, 4) if total_fields else 0.0
    per_field_acc = {
        k: round(v["correct"] / v["total"], 4) if v["total"] else 0.0
        for k, v in field_stats.items()
    }
    return overall_acc, per_field_acc


def train_and_benchmark_models(
    total_documents: int = 300,
    output_dir: str = "./ml/artifacts"
) -> Dict[str, Any]:
    """
    Trains and rigorously benchmarks 3 distinct token classification models
    (Logistic Regression, Calibrated Linear SVM, Random Forest) on multi-layout
    synthetic invoices, evaluating on held-out test split.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"[Phase 3] Generating multi-layout dataset ({total_documents} documents across Train/Val/Test)...")
    dataset = generate_dataset(total_documents=total_documents)

    X_train_text, y_train = prepare_dataset_for_training(dataset["train"])
    X_val_text, y_val = prepare_dataset_for_training(dataset["val"])
    X_test_text, y_test = prepare_dataset_for_training(dataset["test"])

    print(f"[Phase 3] Extracted Tokens: Train={len(X_train_text)}, Val={len(X_val_text)}, Test={len(X_test_text)}")

    # 1. Fit TF-IDF Feature Vectorizer
    print("[Phase 3] Vectorizing tokens via sublinear TF-IDF (1, 2) n-grams...")
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2,
        sublinear_tf=True,
        token_pattern=r"(?u)\b\w+\b|[^\w\s]"
    )
    X_train_vec = vectorizer.fit_transform(X_train_text)
    X_test_vec = vectorizer.transform(X_test_text)

    # 2. Candidate Models
    candidate_models = {
        "LogisticRegression": LogisticRegression(
            class_weight="balanced",
            C=2.5,
            max_iter=1000,
            random_state=42
        ),
        "CalibratedLinearSVM": CalibratedClassifierCV(
            LinearSVC(C=1.0, random_state=42, max_iter=2000),
            cv=3
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=100,
            max_depth=22,
            random_state=42,
            n_jobs=-1
        )
    }

    benchmark_results = {}
    best_model_name = None
    best_macro_f1 = -1.0
    best_model = None

    for name, model in candidate_models.items():
        print(f"\n--- Training Candidate Model: {name} ---")
        t0 = time.time()
        model.fit(X_train_vec, y_train)
        fit_time = round(time.time() - t0, 3)

        # Test inference
        t1 = time.time()
        y_pred = model.predict(X_test_vec)
        inf_time = round(time.time() - t1, 4)
        y_probs = model.predict_proba(X_test_vec)

        # Metrics
        tok_acc = round(float(accuracy_score(y_test, y_pred)), 4)
        macro_f1 = round(float(f1_score(y_test, y_pred, average="macro", zero_division=0)), 4)
        weighted_f1 = round(float(f1_score(y_test, y_pred, average="weighted", zero_division=0)), 4)
        macro_prec = round(float(precision_score(y_test, y_pred, average="macro", zero_division=0)), 4)
        macro_rec = round(float(recall_score(y_test, y_pred, average="macro", zero_division=0)), 4)

        # Exact match accuracy on test documents
        field_exact_match, per_field_acc = evaluate_field_exact_match(model, vectorizer, dataset["test"])

        # Compute Brier score calibration metric (average one-vs-rest)
        classes = list(model.classes_)
        brier_scores = []
        for c_idx, c_name in enumerate(classes):
            bin_y = [1.0 if y == c_name else 0.0 for y in y_test]
            prob_c = y_probs[:, c_idx]
            brier_scores.append(float(brier_score_loss(bin_y, prob_c)))
        avg_brier = round(float(np.mean(brier_scores)), 4)

        print(f"Results for {name}:")
        print(f"  Token Accuracy: {tok_acc * 100:.2f}% | Macro F1: {macro_f1 * 100:.2f}% | Weighted F1: {weighted_f1 * 100:.2f}%")
        print(f"  Field Exact-Match Accuracy: {field_exact_match * 100:.2f}% | Brier Score Loss: {avg_brier}")

        benchmark_results[name] = {
            "token_accuracy": tok_acc,
            "macro_precision": macro_prec,
            "macro_recall": macro_rec,
            "macro_f1": macro_f1,
            "weighted_f1": weighted_f1,
            "field_exact_match_accuracy": field_exact_match,
            "per_field_accuracy": per_field_acc,
            "brier_score": avg_brier,
            "training_time_sec": fit_time,
            "inference_time_sec": inf_time,
            "classification_report": classification_report(y_test, y_pred, output_dict=True, zero_division=0)
        }

        # Select model prioritizing Macro F1 and Field Exact Match
        selection_metric = (macro_f1 * 0.6) + (field_exact_match * 0.4)
        if selection_metric > best_macro_f1:
            best_macro_f1 = selection_metric
            best_model_name = name
            best_model = model

    print(f"\n[Phase 3] Selection: Winning Model is '{best_model_name}' (Score: {best_macro_f1:.4f})")

    # Serialize Best Model and TF-IDF Vectorizer
    model_path = out_path / "field_classifier.joblib"
    vec_path = out_path / "tfidf_vectorizer.joblib"
    metrics_path = out_path / "metrics_summary.json"

    joblib.dump(best_model, model_path)
    joblib.dump(vectorizer, vec_path)

    # Detailed metrics summary artifact
    winning_meta = benchmark_results[best_model_name]
    summary_report = {
        "status": "success",
        "model_type": best_model_name,
        "selected_model": best_model_name,
        "is_trained": True,
        "token_accuracy": winning_meta["token_accuracy"],
        "macro_precision": winning_meta["macro_precision"],
        "macro_recall": winning_meta["macro_recall"],
        "macro_f1": winning_meta["macro_f1"],
        "weighted_f1": winning_meta["weighted_f1"],
        "exact_match_accuracy": winning_meta["field_exact_match_accuracy"],
        "per_field_accuracy": winning_meta["per_field_accuracy"],
        "brier_calibration_score": winning_meta["brier_score"],
        "training_dataset_size": {
            "total_documents": total_documents,
            "train_tokens": len(X_train_text),
            "val_tokens": len(X_val_text),
            "test_tokens": len(X_test_text)
        },
        "model_benchmarking_comparison": {
            k: {
                "macro_f1": v["macro_f1"],
                "weighted_f1": v["weighted_f1"],
                "token_accuracy": v["token_accuracy"],
                "field_exact_match_accuracy": v["field_exact_match_accuracy"],
                "brier_score": v["brier_score"],
                "training_time_sec": v["training_time_sec"]
            }
            for k, v in benchmark_results.items()
        },
        "classification_report": winning_meta["classification_report"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)

    print(f"[Phase 3] Serialized artifacts:\n  - Model: {model_path}\n  - Vectorizer: {vec_path}\n  - Metrics: {metrics_path}")
    return summary_report


if __name__ == "__main__":
    train_and_benchmark_models(total_documents=300)
