# ============================================================
# IMPORTS
# ============================================================

import numpy as np
import pandas as pd
import shap
import xgboost as xgb

from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

# ============================================================
# CONFIGURATION
# ============================================================

CATALOG = "aiagenticdemo"
SCHEMA  = "sdoh_agents"
GOLD    = f"{CATALOG}.{SCHEMA}"

INPUT_TABLE  = f"{GOLD}.sdoh_training_dataset"
OUTPUT_TABLE = f"{GOLD}.sdoh_member_risk_scores"

print("Configuration loaded")


# ============================================================
# DEFINE FEATURES
# ============================================================

CLINICAL_FEATURES = [
    "age", "cci_score", "n_conditions",
    "diabetes_flag", "hypertension_flag", "chf_flag", "copd_flag",
    "depression_flag", "ckd_flag",
    "er_visits_l12m", "ip_admits_l12m", "pcp_visits_l12m", "hedis_gaps",
    "pdc_ratio", "n_rx_l12m", "poly_pharmacy_flag", "poor_adherence_flag",
    "hba1c_imputed", "bmi", "systolic_bp",
    "hba1c_uncontrolled", "obesity_flag", "htn_uncontrolled",
    "frequent_er_flag", "inpatient_flag", "no_pcp_visit_flag",
    "multi_gap_flag", "clinical_burden_composite", "log_spend_l12m",
    "pcp_assigned", "digital_active",
]

SDOH_FEATURES = [
    "adi_national_rank", "poverty_pct", "unemployment_pct",
    "high_deprivation_flag", "high_poverty_flag",
    "food_desert_flag", "snap_eligible_flag", "food_insecurity_score",
    "severe_food_insecurity", "housing_cost_burden_pct",
    "housing_instability_score", "overcrowding_flag", "severe_housing_burden",
    "car_access_flag", "transit_score", "transport_barrier_flag",
    "social_isolation_score", "caregiver_flag", "limited_english_flag",
    "severely_isolated", "hs_graduation_rate", "low_education_flag",
    "pcp_density_per_10k", "sdoh_burden_score", "n_sdoh_barriers",
]

CATEGORICAL_FEATURES = [
    "gender", "plan_type", "age_band", "sdoh_tier", "primary_sdoh_domain"
]

ALL_FEATURES = CLINICAL_FEATURES + SDOH_FEATURES + CATEGORICAL_FEATURES

print(f"Total features: {len(ALL_FEATURES)}")


# ============================================================
# LOAD DATA
# ============================================================

print("Loading dataset...")

full_df = spark.table(INPUT_TABLE).toPandas()

print(f"Loaded: {full_df.shape}")


# ============================================================
# PREPROCESS DATA
# ============================================================

# Convert numeric features
for col in ALL_FEATURES:
    if col in full_df.columns:
        full_df[col] = pd.to_numeric(full_df[col], errors="coerce").fillna(0.0)

# Create feature matrix
X_full = full_df[ALL_FEATURES].astype(float)

print("Feature matrix ready:", X_full.shape)


# ============================================================
# LOAD MODEL
# ============================================================

# If model already exists in memory, skip loading
# Otherwise load from MLflow or file

# Example loading from file:
# model = xgb.XGBClassifier()
# model.load_model("/dbfs/path/model.json")

print("Model ready")


# ============================================================
# SCORE MEMBERS
# ============================================================

print("Scoring members...")

risk_proba = model.predict_proba(X_full)[:, 1]

print("Scoring complete")


# ============================================================
# COMPUTE SHAP VALUES
# ============================================================

print("Computing SHAP values...")

explainer = shap.TreeExplainer(model)

shap_values = explainer.shap_values(X_full)

shap_df = pd.DataFrame(
    shap_values,
    columns=ALL_FEATURES
)

shap_df = shap_df.fillna(0.0)

print("SHAP computed:", shap_df.shape)


# ============================================================
# FUNCTION: TOP 5 CLINICAL DRIVERS + VALUES
# ============================================================

def get_top5_clinical(shap_dataframe, clinical_features):

    clinical_shap = shap_dataframe[clinical_features]

    clinical_abs = clinical_shap.abs()

    top_features = clinical_abs.apply(
        lambda row: row.nlargest(5).index.tolist(),
        axis=1
    )

    top_values = []

    for i, features in enumerate(top_features):

        values = []

        for f in features:
            values.append(clinical_shap.iloc[i][f])

        top_values.append(values)

    feature_df = pd.DataFrame(
        top_features.tolist(),
        columns=[
            "clinical_driver_1",
            "clinical_driver_2",
            "clinical_driver_3",
            "clinical_driver_4",
            "clinical_driver_5"
        ]
    )

    value_df = pd.DataFrame(
        top_values,
        columns=[
            "clinical_driver_1_shap",
            "clinical_driver_2_shap",
            "clinical_driver_3_shap",
            "clinical_driver_4_shap",
            "clinical_driver_5_shap"
        ]
    )

    return pd.concat([feature_df, value_df], axis=1)


# ============================================================
# EXTRACT TOP CLINICAL DRIVERS
# ============================================================

print("Extracting Top 5 Clinical Drivers...")

top5_df = get_top5_clinical(shap_df, CLINICAL_FEATURES)

print("Top drivers extracted:", top5_df.shape)


# ============================================================
# CREATE FINAL OUTPUT
# ============================================================

result_df = pd.DataFrame({

    "member_id": full_df["member_id"],

    "risk_score": risk_proba.round(4),

    "risk_tier": pd.cut(
        risk_proba,
        bins=[0,0.35,0.65,1],
        labels=["LOW","MEDIUM","HIGH"]
    ).astype(str),

    "scored_at": pd.Timestamp.now().isoformat()

})

result_df = pd.concat([result_df, top5_df], axis=1)

print("Final dataframe:", result_df.shape)


# ============================================================
# SAVE TO DELTA TABLE
# ============================================================

spark_df = spark.createDataFrame(result_df)

spark_df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("mergeSchema", "true") \
    .saveAsTable(OUTPUT_TABLE)

print("SUCCESS")
print("Saved to:", OUTPUT_TABLE)
print("Rows:", spark_df.count())
