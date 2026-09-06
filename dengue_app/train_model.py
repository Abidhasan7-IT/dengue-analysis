
import json
import pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, confusion_matrix
)

RANDOM_STATE = 42
CATEGORICAL_COLS = ["Gender", "Area", "AreaType", "HouseType"]
BINARY_SYMPTOM_COLS = ["Joint_Pain", "Headache", "Retro_Orbital_Pain", "Myalgia", "Rash"]
NUMERIC_COLS = ["Age", "Fever_Duration", "Body_Temperature", "Platelet_Count", "WBC_Count"]
TARGET = "Outcome"

# Clinical reference ranges, taken from the project brief (idea.docx).
# Used both for the dashboard's "clinical flags" panel and the per-patient explanation.
CLINICAL_FLAGS = {
    "Body_Temperature": {"op": ">=", "value": 38.0, "label": "Fever \u2265 38\u00b0C"},
    "Fever_Duration": {"op": ">=", "value": 3, "label": "Fever lasting \u2265 3 days"},
    "Platelet_Count": {"op": "<", "value": 150000, "label": "Platelets < 150,000 /\u00b5L"},
    "WBC_Count": {"op": "<", "value": 4000, "label": "WBC < 4,000 /\u00b5L"},
}


def main():
    df = pd.read_csv("dataset.csv")
    df = df.drop_duplicates().reset_index(drop=True)

    # --- encode categoricals -------------------------------------------------
    encoders = {}
    df_enc = df.copy()
    for col in CATEGORICAL_COLS:
        le = LabelEncoder()
        df_enc[col] = le.fit_transform(df_enc[col])
        encoders[col] = le

    feature_cols = CATEGORICAL_COLS + ["Age", "Fever_Duration", "Body_Temperature",
                                        "Platelet_Count", "WBC_Count"] + BINARY_SYMPTOM_COLS
    X = df_enc[feature_cols]
    y = df_enc[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # --- deployed model: Logistic Regression (most interpretable) -----------
    model = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    y_prob = model.predict_proba(X_test_scaled)[:, 1]

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    X_all_scaled = scaler.transform(X)
    cv_scores = cross_val_score(model, X_all_scaled, y, cv=cv, scoring="accuracy")

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_prob)
    cm = confusion_matrix(y_test, y_pred).tolist()
    fpr, tpr, _ = roc_curve(y_test, y_prob)
    roc_points = [{"fpr": float(f), "tpr": float(t)} for f, t in zip(fpr[::5], tpr[::5])]
    if roc_points[-1]["fpr"] != 1.0:
        roc_points.append({"fpr": 1.0, "tpr": float(tpr[-1])})

    # --- secondary model: Random Forest, used only for the importance chart -
    rf = RandomForestClassifier(n_estimators=200, random_state=RANDOM_STATE, n_jobs=-1)
    rf.fit(X, y)
    rf_importance = sorted(
        zip(feature_cols, rf.feature_importances_.tolist()),
        key=lambda p: p[1], reverse=True
    )

    # --- dataset-level stats for the dashboard charts ------------------------
    outcome_counts = df[TARGET].value_counts().sort_index()
    numeric_by_outcome = {
        col: {
            "negative": {"mean": float(df.loc[df[TARGET] == 0, col].mean()),
                         "std": float(df.loc[df[TARGET] == 0, col].std())},
            "positive": {"mean": float(df.loc[df[TARGET] == 1, col].mean()),
                         "std": float(df.loc[df[TARGET] == 1, col].std())},
        }
        for col in ["Platelet_Count", "WBC_Count", "Body_Temperature", "Fever_Duration"]
    }
    area_counts = df["Area"].value_counts().head(10)

    metrics = {
        "model_name": "Logistic Regression",
        "n_samples": int(len(df)),
        "n_features": len(feature_cols),
        "test_size": int(len(y_test)),
        "scores": {
            "accuracy": acc, "precision": prec, "recall": rec,
            "f1": f1, "auc": auc,
            "cv_mean": float(cv_scores.mean()), "cv_std": float(cv_scores.std()),
        },
        "confusion_matrix": cm,
        "roc_curve": roc_points,
        "rf_importance": rf_importance,
        "lr_coefficients": sorted(
            zip(feature_cols, model.coef_[0].tolist()),
            key=lambda p: abs(p[1]), reverse=True
        ),
        "outcome_distribution": {
            "negative": int(outcome_counts.get(0, 0)),
            "positive": int(outcome_counts.get(1, 0)),
        },
        "numeric_by_outcome": numeric_by_outcome,
        "top_areas": {str(k): int(v) for k, v in area_counts.items()},
        "clinical_flags": CLINICAL_FLAGS,
    }

    feature_meta = {
        "feature_order": feature_cols,
        "categorical_choices": {
            col: sorted(df[col].unique().tolist()) for col in CATEGORICAL_COLS
        },
        "numeric_ranges": {
            col: {"min": float(df[col].min()), "max": float(df[col].max()),
                  "mean": float(df[col].mean())}
            for col in NUMERIC_COLS
        },
        "binary_symptoms": BINARY_SYMPTOM_COLS,
    }

    with open("model/model.pkl", "wb") as f:
        pickle.dump(model, f)
    with open("model/scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    with open("model/encoders.pkl", "wb") as f:
        pickle.dump(encoders, f)
    with open("model/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    with open("model/feature_meta.json", "w") as f:
        json.dump(feature_meta, f, indent=2)

    print(f"Trained on {len(df)} records | Test accuracy: {acc:.4f} | AUC: {auc:.4f}")
    print(f"5-fold CV accuracy: {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}")
    print("Saved model + metrics to ./model/")


if __name__ == "__main__":
    main()
