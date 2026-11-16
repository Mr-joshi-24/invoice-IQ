import random
from pathlib import Path
from typing import Dict, Any, List
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler


def generate_anomaly_training_data(n_samples: int = 1500) -> np.ndarray:
    """
    Generates realistic financial feature vectors for business invoices.
    Feature columns:
    0: total_amount_log = ln(total + 1)
    1: tax_ratio = tax / subtotal
    2: subtotal_to_total_ratio = subtotal / total
    3: math_discrepancy = |subtotal + tax - total|
    """
    np.random.seed(42)
    random.seed(42)
    features: List[List[float]] = []

    # 1. Normal business transactions (95% of data)
    n_normal = int(n_samples * 0.95)
    for _ in range(n_normal):
        # Subtotal: log-normal distribution centered around 5,000
        subtotal = float(np.random.lognormal(mean=8.2, sigma=1.1))
        subtotal = max(100.0, min(100000.0, subtotal))

        # Standard GST rates: 5%, 12%, 18%, 28% with minor rounding jitter
        base_rate = random.choice([0.05, 0.12, 0.18, 0.28])
        tax_rate = base_rate + np.random.normal(0, 0.001)
        tax = round(subtotal * tax_rate, 2)
        total = round(subtotal + tax, 2)

        tot_log = float(np.log1p(total))
        t_ratio = float(tax / subtotal)
        st_ratio = float(subtotal / total)
        discrepancy = float(abs(subtotal + tax - total))

        features.append([tot_log, t_ratio, st_ratio, discrepancy])

    # 2. Injected Anomalous Outliers (5% of data)
    n_anomalies = n_samples - n_normal
    for _ in range(n_anomalies):
        anomaly_type = random.choice(["huge_amount", "unusual_tax", "math_error"])
        if anomaly_type == "huge_amount":
            total = float(np.random.uniform(5000000.0, 50000000.0))  # 50 Lakhs to 5 Crores
            subtotal = total * 0.82
            tax = total * 0.18
        elif anomaly_type == "unusual_tax":
            subtotal = float(np.random.uniform(1000.0, 10000.0))
            tax = subtotal * float(np.random.uniform(0.50, 0.95))  # 50% to 95% abnormal tax
            total = subtotal + tax
        else:  # math_error
            subtotal = float(np.random.uniform(1000.0, 10000.0))
            tax = subtotal * 0.18
            total = subtotal + tax + float(np.random.uniform(500.0, 5000.0))  # Broken total calculation

        tot_log = float(np.log1p(total))
        t_ratio = float(tax / max(1.0, subtotal))
        st_ratio = float(subtotal / max(1.0, total))
        discrepancy = float(abs(subtotal + tax - total))

        features.append([tot_log, t_ratio, st_ratio, discrepancy])

    return np.array(features, dtype=np.float64)


def train_anomaly_model(output_dir: str = "./ml/artifacts") -> Dict[str, Any]:
    """
    Fits RobustScaler and IsolationForest on financial transaction vectors,
    and serializes model artifacts.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("[Phase 3] Generating 1,500 synthetic financial transaction vectors...")
    X = generate_anomaly_training_data(1500)

    print("[Phase 3] Fitting RobustScaler for financial features...")
    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X)

    print("[Phase 3] Fitting Isolation Forest model (contamination=0.05, n_estimators=120)...")
    iso_forest = IsolationForest(
        n_estimators=120,
        contamination=0.05,
        random_state=42,
        n_jobs=-1
    )
    iso_forest.fit(X_scaled)

    model_path = out_path / "anomaly_model.joblib"
    scaler_path = out_path / "anomaly_scaler.joblib"

    joblib.dump(iso_forest, model_path)
    joblib.dump(scaler, scaler_path)

    print(f"[Phase 3] Serialized anomaly detector to {model_path} and scaler to {scaler_path}.")

    return {
        "n_samples": len(X),
        "contamination": 0.05,
        "model_path": str(model_path),
        "scaler_path": str(scaler_path)
    }


if __name__ == "__main__":
    train_anomaly_model()
