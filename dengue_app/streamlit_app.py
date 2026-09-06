import pandas as pd
import streamlit as st

from app import (
    CLINICAL_FLAGS,
    FEATURE_META,
    FRIENDLY_NAMES,
    METRICS,
    MODEL,
    SCALER,
    build_feature_vector,
    clinical_flags_hit,
    top_contributors,
)


st.set_page_config(
    page_title="Dengue Risk Assessment",
    layout="wide",
)


def metric_card(label, value):
    st.metric(label, value)


def dashboard():
    st.title("Dengue Risk Assessment")
    st.caption("Model dashboard and transparent patient-level decision support")

    scores = METRICS["scores"]
    columns = st.columns(4)
    with columns[0]:
        metric_card("Test accuracy", f"{scores['accuracy']:.1%}")
    with columns[1]:
        metric_card("ROC AUC", f"{scores['auc']:.3f}")
    with columns[2]:
        metric_card("Training records", f"{METRICS['n_samples']:,}")
    with columns[3]:
        metric_card("Features", METRICS["n_features"])

    st.subheader("Model performance")
    performance = pd.DataFrame(
        {
            "Metric": ["Accuracy", "Precision", "Recall", "F1", "5-fold CV mean"],
            "Score": [
                scores["accuracy"],
                scores["precision"],
                scores["recall"],
                scores["f1"],
                scores["cv_mean"],
            ],
        }
    ).set_index("Metric")
    st.bar_chart(performance)

    left, right = st.columns(2)
    with left:
        st.subheader("Random forest feature importance")
        importance = pd.DataFrame(
            METRICS["rf_importance"], columns=["Feature", "Importance"]
        ).set_index("Feature")
        st.bar_chart(importance)
    with right:
        st.subheader("Outcome distribution")
        outcomes = pd.DataFrame.from_dict(
            METRICS["outcome_distribution"], orient="index", columns=["Records"]
        )
        st.bar_chart(outcomes)

    st.subheader("Clinical reference flags")
    st.dataframe(
        pd.DataFrame(
            [
                {"Measure": key, "Rule": f"{rule['op']} {rule['value']}", "Meaning": rule["label"]}
                for key, rule in CLINICAL_FLAGS.items()
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )


def numeric_input(label, field):
    bounds = FEATURE_META["numeric_ranges"][field]
    return st.number_input(
        label,
        min_value=float(bounds["min"]),
        max_value=float(bounds["max"]),
        value=float(bounds["mean"]),
    )


def prediction_form():
    st.title("Patient assessment")
    st.caption("Enter the available patient information to estimate dengue risk.")

    choices = FEATURE_META["categorical_choices"]
    with st.form("prediction_form"):
        demographics, observations = st.columns(2)
        with demographics:
            gender = st.selectbox("Gender", choices["Gender"])
            area = st.selectbox("Area", choices["Area"])
            area_type = st.selectbox("Area type", choices["AreaType"])
            house_type = st.selectbox("House type", choices["HouseType"])
            age = numeric_input("Age", "Age")
        with observations:
            fever_duration = numeric_input("Fever duration (days)", "Fever_Duration")
            body_temperature = numeric_input("Body temperature (C)", "Body_Temperature")
            platelet_count = numeric_input("Platelet count (per uL)", "Platelet_Count")
            wbc_count = numeric_input("WBC count (per uL)", "WBC_Count")
            symptoms = st.multiselect(
                "Symptoms",
                FEATURE_META["binary_symptoms"],
                format_func=lambda value: FRIENDLY_NAMES.get(value, value),
            )

        submitted = st.form_submit_button("Assess risk", type="primary")

    if not submitted:
        return

    form = {
        "Gender": gender,
        "Area": area,
        "AreaType": area_type,
        "HouseType": house_type,
        "Age": age,
        "Fever_Duration": fever_duration,
        "Body_Temperature": body_temperature,
        "Platelet_Count": platelet_count,
        "WBC_Count": wbc_count,
        **{symptom: "1" if symptom in symptoms else "0" for symptom in FEATURE_META["binary_symptoms"]},
    }
    vector, raw_row = build_feature_vector(form)
    scaled = SCALER.transform(vector)
    probability = float(MODEL.predict_proba(scaled)[0][1])
    if probability >= 0.7:
        risk_level = "High"
    elif probability >= 0.4:
        risk_level = "Moderate"
    else:
        risk_level = "Low"

    result, details = st.columns([1, 2])
    with result:
        st.subheader(f"{risk_level} risk")
        st.metric("Estimated probability", f"{probability:.1%}")
        st.progress(probability, text="Model probability")
    with details:
        st.subheader("Main contributing factors")
        contributor_rows = []
        for contributor in top_contributors(scaled):
            contributor_rows.append(
                {
                    "Factor": FRIENDLY_NAMES.get(contributor["feature"], contributor["feature"]),
                    "Effect": "Raises risk" if contributor["contribution"] > 0 else "Lowers risk",
                    "Contribution": round(contributor["contribution"], 3),
                }
            )
        st.dataframe(pd.DataFrame(contributor_rows), hide_index=True, use_container_width=True)

    flags = clinical_flags_hit(raw_row)
    st.subheader("Clinical threshold flags")
    if flags:
        for flag in flags:
            st.warning(flag)
    else:
        st.success("No configured clinical thresholds were triggered.")
    st.caption("This tool is for decision support and does not replace clinical assessment.")


page = st.sidebar.radio("View", ["Dashboard", "Patient assessment"])
if page == "Dashboard":
    dashboard()
else:
    prediction_form()