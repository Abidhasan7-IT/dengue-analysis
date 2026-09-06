
import json
import pickle
from pathlib import Path

import numpy as np
from flask import Flask, render_template, request, jsonify

APP_DIR = Path(__file__).parent
MODEL_DIR = APP_DIR / "model"

app = Flask(__name__)

# ---------------------------------------------------------------- load once
with open(MODEL_DIR / "model.pkl", "rb") as f:
    MODEL = pickle.load(f)
with open(MODEL_DIR / "scaler.pkl", "rb") as f:
    SCALER = pickle.load(f)
with open(MODEL_DIR / "encoders.pkl", "rb") as f:
    ENCODERS = pickle.load(f)
with open(MODEL_DIR / "metrics.json") as f:
    METRICS = json.load(f)
with open(MODEL_DIR / "feature_meta.json") as f:
    FEATURE_META = json.load(f)

FEATURE_ORDER = FEATURE_META["feature_order"]
CLINICAL_FLAGS = METRICS["clinical_flags"]
MODEL_ONLY_CATEGORICALS = {
    "Area": ENCODERS["Area"].classes_[0],
    "AreaType": ENCODERS["AreaType"].classes_[0],
    "HouseType": ENCODERS["HouseType"].classes_[0],
}
# coefficient lookup for per-patient explanation
LR_COEF = dict(METRICS["lr_coefficients"])


def build_feature_vector(form):
    """Turn submitted form fields into a single-row feature array, in FEATURE_ORDER."""
    row = {}
    row["Gender"] = ENCODERS["Gender"].transform([form["Gender"]])[0]
    for col, value in MODEL_ONLY_CATEGORICALS.items():
        row[col] = ENCODERS[col].transform([value])[0]
    row["Age"] = float(form["Age"])
    row["Fever_Duration"] = float(form["Fever_Duration"])
    row["Body_Temperature"] = float(form["Body_Temperature"])
    row["Platelet_Count"] = float(form["Platelet_Count"])
    row["WBC_Count"] = float(form["WBC_Count"])
    for sym in FEATURE_META["binary_symptoms"]:
        row[sym] = 1 if form.get(sym) in ("1", "on", "true", "True") else 0
    vector = [row[col] for col in FEATURE_ORDER]
    return np.array(vector).reshape(1, -1), row


def clinical_flags_hit(raw_row):
    """Which of the brief's clinical thresholds does this patient trip?"""
    hits = []
    for feat, rule in CLINICAL_FLAGS.items():
        val = raw_row[feat]
        if rule["op"] == ">=" and val >= rule["value"]:
            hits.append(rule["label"])
        elif rule["op"] == "<" and val < rule["value"]:
            hits.append(rule["label"])
    return hits


def top_contributors(scaled_row, k=5):
    """Simple, transparent explanation: |coefficient * standardized value| ranking."""
    contributions = []
    for i, feat in enumerate(FEATURE_ORDER):
        contrib = float(LR_COEF[feat]) * float(scaled_row[0][i])
        contributions.append({"feature": feat, "contribution": contrib})
    contributions.sort(key=lambda c: abs(c["contribution"]), reverse=True)
    return contributions[:k]


FRIENDLY_NAMES = {
    "Body_Temperature": "Body temperature", "Fever_Duration": "Fever duration",
    "Platelet_Count": "Platelet count", "WBC_Count": "WBC count", "Age": "Age",
    "Gender": "Gender", "Area": "Area", "AreaType": "Area type", "HouseType": "House type",
    "Joint_Pain": "Joint pain", "Headache": "Headache",
    "Retro_Orbital_Pain": "Retro-orbital pain", "Myalgia": "Myalgia", "Rash": "Rash",
}


@app.route("/")
def dashboard():
    return render_template("dashboard.html", metrics=METRICS)


@app.route("/predict", methods=["GET"])
def predict_form():
    return render_template("predict.html", meta=FEATURE_META)


@app.route("/api/predict", methods=["POST"])
def api_predict():
    form = request.get_json(force=True)
    try:
        vector, raw_row = build_feature_vector(form)
    except Exception as exc:  # bad / missing field
        return jsonify({"error": f"Invalid input: {exc}"}), 400

    scaled = SCALER.transform(vector)
    prob = float(MODEL.predict_proba(scaled)[0][1])
    pred = int(prob >= 0.5)

    if prob >= 0.7:
        risk_level = "High"
    elif prob >= 0.4:
        risk_level = "Moderate"
    else:
        risk_level = "Low"

    contributors = top_contributors(scaled)
    for c in contributors:
        c["label"] = FRIENDLY_NAMES.get(c["feature"], c["feature"])
        c["direction"] = "raises risk" if c["contribution"] > 0 else "lowers risk"

    flags = clinical_flags_hit(raw_row)

    return jsonify({
        "prediction": pred,
        "probability": prob,
        "risk_level": risk_level,
        "contributors": contributors,
        "clinical_flags": flags,
    })


if __name__ == "__main__":
    app.run(debug=True)
