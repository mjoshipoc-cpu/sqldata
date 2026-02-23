
# Notebook 03: Risk Score Model Training & Explainability
# Trains XGBoost risk model with clinical + SDOH features
# Generates per-member SHAP explanations (SDOH vs Clinical drivers)
# Logs everything to MLflow and registers model to Unity Catalog
# Deploys a batch scoring pipeline producing member risk scores

%pip install xgboost shap lightgbm scikit-learn imbalanced-learn databricks-feature-engineering --quiet
dbutils.library.restartPython()

import numpy as np
import pandas as pd
import mlflow
import mlflow.xgboost
import xgboost as xgb
import shap
import json
import warnings
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import (roc_auc_score, average_precision_score,classification_report, confusion_matrix)
from sklearn.preprocessing import LabelEncoder
from databricks.feature_engineering import FeatureEngineeringClient

warnings.filterwarnings("ignore")

CATALOG    = "aiagenticdemo"
GOLD       = f"{CATALOG}.sdoh_agents"
MODEL_NAME = f"{CATALOG}.sdoh_agents.risk_scorer_v1"
FE         = FeatureEngineeringClient()

username = dbutils.notebook.entry_point.getDbutils().notebook().getContext().userName().get()
experiment_path = f"/Users/{username}/health_ai_risk_model"
mlflow.set_registry_uri("databricks-uc")
mlflow.set_tracking_uri("databricks")
mlflow.set_experiment(experiment_path)
print(f"✅ MLflow experiment set: {mlflow.get_experiment_by_name(experiment_path)}")
print("✅ Setup complete")

# %md ## 1️⃣ Load & Prepare Training Data

df = spark.table(f"{GOLD}.sdoh_training_dataset").toPandas()
print(f"Loaded: {df.shape[0]:,} rows × {df.shape[1]} columns")

# ── Feature selection ────────────────────────────────────────────────────────
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

CATEGORICAL_FEATURES = ["gender", "plan_type", "age_band", "sdoh_tier", "primary_sdoh_domain"]
ALL_FEATURES = CLINICAL_FEATURES + SDOH_FEATURES + CATEGORICAL_FEATURES

# ── Identify and fix all object columns that should be numeric ──────────
NUMERIC_COLS = CLINICAL_FEATURES + SDOH_FEATURES

print("🔍 Checking for object-type columns that should be numeric...")
problem_cols = []
for col in NUMERIC_COLS:
    if col in df.columns and df[col].dtype == object:
        problem_cols.append(col)
        print(f"   ⚠️  {col}: {df[col].dtype} → converting to float")

# Force-convert all numeric feature columns
for col in NUMERIC_COLS:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

# Also force categorical columns to string then encode
for col in CATEGORICAL_FEATURES:
    if col in df.columns:
        df[col] = df[col].fillna("UNKNOWN").astype(str)

print(f"\n✅ Fixed {len(problem_cols)} problem columns: {problem_cols}")

# ── Final dtype check ───────────────────────────────────────────────────
print("\n🔍 Final dtype audit on feature matrix:")
X_check = df[ALL_FEATURES]
bad = [(c, str(X_check[c].dtype)) for c in X_check.columns if X_check[c].dtype == object]
if bad:
    print(f"   ❌ Still object type: {bad}")
else:
    print(f"   ✅ All {len(ALL_FEATURES)} features are numeric — safe to train")

# Encode categoricals
le_map = {}
for col in CATEGORICAL_FEATURES:
    le = LabelEncoder()
    df[col] = df[col].fillna("UNKNOWN").astype(str)
    df[col] = le.fit_transform(df[col])
    le_map[col] = dict(zip(le.classes_, le.transform(le.classes_)))

# Fill missing numerics
for col in CLINICAL_FEATURES + SDOH_FEATURES:
    if col in df.columns:
        #df[col] = df[col].fillna(df[col].median()) to handle nulls
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(df[col].median())

X = df[ALL_FEATURES].astype(float)
y = df["high_risk_label"]

print(f"Features: {len(ALL_FEATURES)} ({len(CLINICAL_FEATURES)} clinical, {len(SDOH_FEATURES)} SDOH)")
print(f"✅ X shape: {X.shape} | dtypes: {X.dtypes.value_counts().to_dict()}")
print(f"Label balance: {y.mean():.1%} high-risk")

# MAGIC %md ## 2️⃣ Train XGBoost Risk Model with Cross-Validation

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

X_train, X_val, y_train, y_val = train_test_split(X_train, y_train, test_size=0.15, stratify=y_train, random_state=42)

class_ratio = (y_train == 0).sum() / (y_train == 1).sum()
print(f"Train: {len(X_train):,} | Val: {len(X_val):,} | Test: {len(X_test):,}")
print(f"Class imbalance ratio: {class_ratio:.1f}:1")

with mlflow.start_run(run_name="xgb_sdoh_clinical_v1") as run:
    run_id = run.info.run_id

    params = {
        "n_estimators"      : 600,
        "max_depth"         : 6,
        "learning_rate"     : 0.04,
        "subsample"         : 0.8,
        "colsample_bytree"  : 0.8,
        "min_child_weight"  : 5,
        "scale_pos_weight"  : class_ratio,
        "eval_metric"       : "aucpr",
        "random_state"      : 42,
        "tree_method"       : "hist",
        "enable_categorical": False,
    }

    model = xgb.XGBClassifier(**params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=50
    )

    # Evaluate
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred       = (y_pred_proba >= 0.45).astype(int)

    auc_roc  = roc_auc_score(y_test, y_pred_proba)
    auc_pr   = average_precision_score(y_test, y_pred_proba)

    print(f"\n{'='*50}")
    print(f"  AUC-ROC : {auc_roc:.4f}")
    print(f"  AUC-PR  : {auc_pr:.4f}")
    print(f"{'='*50}\n")
    print(classification_report(y_test, y_pred))

    # Log to MLflow
    mlflow.log_params(params)
    mlflow.log_metric("auc_roc",round(auc_roc,  4))
    mlflow.log_metric("auc_pr",round(auc_pr,   4))
    mlflow.log_metric("best_iteration", getattr(model, "best_iteration", params["n_estimators"]))
    mlflow.log_param("n_clinical_features",len(CLINICAL_FEATURES))
    mlflow.log_param("n_sdoh_features",len(SDOH_FEATURES))
    mlflow.log_param("feature_names",json.dumps(ALL_FEATURES))

    # Feature importance
    fi = pd.Series(model.feature_importances_, index=ALL_FEATURES).sort_values(ascending=False)
    clinical_importance = fi[CLINICAL_FEATURES].sum()
    sdoh_importance     = fi[SDOH_FEATURES].sum()
    total_importance    = fi.sum()
    sdoh_pct            = sdoh_importance / total_importance * 100

    mlflow.log_metric("sdoh_feature_importance_pct", round(sdoh_pct, 1))
    print(f"📊 SDOH accounts for {sdoh_pct:.1f}% of total feature importance")
    print(f"   Top 5 features: {fi.head(5).index.tolist()}")

def to_python(obj):
    """Recursively convert numpy types to native Python for MLflow serialization."""
    if isinstance(obj, dict):
        return {k: to_python(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_python(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    return obj

    # Register model
mlflow.xgboost.log_model(
    model, "risk_model",
    registered_model_name=MODEL_NAME,
    input_example=X_test.head(5).astype(float),
    metadata=to_python({
        "clinical_features"  : CLINICAL_FEATURES,
        "sdoh_features"      : SDOH_FEATURES,
        "all_features"       : ALL_FEATURES,
        "categorical_encoding": le_map,
        "threshold"          : 0.45,
    })
)

print(f"✅ Model registered: {MODEL_NAME}")

# Save test set for SHAP
test_results_pd = X_test.copy()
test_results_pd["y_true"]      = y_test.values
test_results_pd["y_pred_proba"]= y_pred_proba
test_results_pd["y_pred"]      = y_pred

spark.createDataFrame(test_results_pd.astype(float)).write.format("delta").mode("overwrite").saveAsTable(f"{GOLD}.sdoh_model_test_results")
print(f"✅ Test results saved to {GOLD}.sdoh_model_test_results — {len(test_results_pd):,} rows")

# %md ## 3️⃣ SHAP Explainability: Clinical vs SDOH Drivers

print("Computing SHAP values (TreeExplainer)...")
explainer  = shap.TreeExplainer(model)

# Use sample for speed
shap_sample = X_test.sample(min(5000, len(X_test)), random_state=42)
shap_values = explainer.shap_values(shap_sample)
shap_df     = pd.DataFrame(shap_values, columns=ALL_FEATURES, index=shap_sample.index)

print(f"✅ SHAP values computed for {len(shap_df):,} members")

# ── Per-feature SHAP analysis ─────────────────────────────────────────────
mean_abs_shap = shap_df.abs().mean().sort_values(ascending=False)
print("\n🔍 Top 10 Most Important Features (mean |SHAP|):")
for feat, val in mean_abs_shap.head(10).items():
    tag = "SDOH" if feat in SDOH_FEATURES else "CLIN"
    print(f"   [{tag}] {feat:<40} {val:.4f}")

# %md ## 4️⃣ Batch Score All 50K Members

print("Scoring all members...")
full_df = spark.table(f"{GOLD}.sdoh_training_dataset").toPandas()

# ── Force all feature columns to numeric ──────────────────────────────
for col in ALL_FEATURES:
    if col in full_df.columns:
        full_df[col] = pd.to_numeric(full_df[col], errors='coerce').fillna(0.0)

# Re-apply label encoding on categoricals
for col in CATEGORICAL_FEATURES:
    if col in full_df.columns:
        full_df[col] = full_df[col].fillna("UNKNOWN").astype(str)
        if col in le_map:
            full_df[col] = full_df[col].map(le_map[col]).fillna(-1).astype(float)

# Final safety cast
X_full = full_df[ALL_FEATURES].astype(float)

print(f"✅ X_full ready: {X_full.shape}")
print(f"   Any object cols: {[c for c in X_full.columns if X_full[c].dtype == object]}")

# Apply same preprocessing
for col in CATEGORICAL_FEATURES:
    full_df[col] = full_df[col].fillna("UNKNOWN").astype(str)
    if col in le_map:
        full_df[col] = full_df[col].map(le_map[col]).fillna(-1).astype(int)

for col in CLINICAL_FEATURES + SDOH_FEATURES:
    if col in full_df.columns:
        full_df[col] = full_df[col].fillna(full_df[col].median())

X_full = full_df[ALL_FEATURES]

# Score
risk_proba = model.predict_proba(X_full)[:, 1]

# SHAP for all members
shap_all   = explainer.shap_values(X_full)
shap_all_df = pd.DataFrame(shap_all, columns=ALL_FEATURES)

shap_all_df = shap_all_df.apply(pd.to_numeric, errors='coerce').fillna(0.0)

print(f"✅ SHAP df clean: {shap_all_df.shape} | object cols: {[c for c in shap_all_df.columns if shap_all_df[c].dtype == object]}")

# Compute SDOH contribution
sdoh_shap      = shap_all_df[SDOH_FEATURES].sum(axis=1)
clinical_shap  = shap_all_df[CLINICAL_FEATURES].sum(axis=1)
total_pos_shap = shap_all_df.clip(lower=0).sum(axis=1) + 1e-9
sdoh_contrib_pct = (shap_all_df[SDOH_FEATURES].clip(lower=0).sum(axis=1) / total_pos_shap * 100)
clinical_contrib_pct = (shap_all_df[CLINICAL_FEATURES].clip(lower=0).sum(axis=1) / total_pos_shap * 100)

# Top drivers
def top_drivers(row, n=3):
    numeric_row = pd.to_numeric(row, errors='coerce').fillna(0.0)
    return ",".join(numeric_row.abs().nlargest(n).index.tolist())

print("Computing per-member top drivers...")

# Add member_id AFTER the float cast
shap_all_df["member_id"] = full_df["member_id"].values

top_clinical = shap_all_df[CLINICAL_FEATURES].apply(top_drivers, axis=1)
top_sdoh     = shap_all_df[SDOH_FEATURES].apply(top_drivers, axis=1)

print(f"✅ Top drivers computed for {len(top_clinical):,} members")

# Assemble scores table
scores_pd = pd.DataFrame({
    "member_id"           : full_df["member_id"],
    "risk_score"          : risk_proba.round(4),
    "risk_tier"           : pd.cut(risk_proba, bins=[0, 0.35, 0.65, 1.0],
                                    labels=["LOW","MEDIUM","HIGH"]).astype(str),
    "sdoh_contribution_pct": sdoh_contrib_pct.round(1),
    "clinical_contribution_pct": clinical_contrib_pct.round(1),
    "top_clinical_drivers": top_clinical.values,
    "top_sdoh_drivers"    : top_sdoh.values,
    "scored_at"           : pd.Timestamp.now().isoformat(),
    "model_version"       : "v1",
})

scores_df = spark.createDataFrame(scores_pd)
scores_df.write.format("delta").mode("overwrite").option("mergeSchema", "true").saveAsTable(f"{GOLD}.sdoh_member_risk_scores")

print(f"✅ Gold: member_risk_scores — {scores_df.count():,} members scored")




# Ensure SHAP values are numeric and clean
shap_all_df = shap_all_df.apply(pd.to_numeric, errors="coerce").fillna(0.0)

# Add member_id to SHAP dataframe
shap_all_df["member_id"] = full_df["member_id"].values

# Function to extract top N drivers
def get_top_n_drivers(shap_df, feature_list, n=5):
    """
    Returns dataframe with top N drivers per member based on absolute SHAP value
    """
    top_n = (
        shap_df[feature_list]
        .abs()
        .apply(lambda row: row.nlargest(n).index.tolist(), axis=1)
        .apply(pd.Series)
    )

    top_n.columns = [f"clinical_driver_{i+1}" for i in range(n)]

    return top_n


# Get Top 5 Clinical Drivers
top5_clinical_df = get_top_n_drivers(shap_all_df, CLINICAL_FEATURES, n=5)

# Combine with member_id
top5_clinical_df["member_id"] = shap_all_df["member_id"].values

# Merge into scores table
scores_pd = scores_pd.merge(
    top5_clinical_df,
    on="member_id",
    how="left"
)

print(f"✅ Top 5 clinical drivers computed for {len(scores_pd):,} members")


