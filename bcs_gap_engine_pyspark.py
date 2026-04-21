# ================================================================
# BCS GAP DETECTION ENGINE — PURE PYSPARK (NO DLT)
# ================================================================
# Measure  : BCS — Breast Cancer Screening
# Platform : Databricks — any cluster, no DLT required
# Output   : ncqa.gold.care_gaps_bcs  (BCS-specific table)
#            ncqa.gold.care_gaps       (master unified table)
# Version  : 2025.1 — PRODUCTION READY
# ================================================================
# HOW TO RUN:
#   1. Create a new Python notebook in Databricks
#   2. Attach to any running cluster (DBR 12+ recommended)
#   3. Paste this entire file
#   4. Click Run All
#   5. Check output at the bottom of each cell
# ================================================================

# ================================================================
# CELL 1 — CONFIGURATION
# ================================================================

YEAR                = 2025
START               = "2025-01-01"
END                 = "2025-12-31"
RUN_ID              = f"BCS_RUN_{YEAR}_001"
CATALOG             = "ncqa"
SILVER              = f"{CATALOG}.silver"
GOLD                = f"{CATALOG}.gold"
BCS_LOOKBACK_MONTHS = 27

# Set catalog
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.gold")

print("=" * 55)
print("BCS GAP DETECTION ENGINE — STARTING")
print("=" * 55)
print(f"  Measurement year : {YEAR}")
print(f"  Window start     : {START}")
print(f"  Window end       : {END}")
print(f"  Lookback window  : {BCS_LOOKBACK_MONTHS} months")
print(f"  Silver layer     : {SILVER}")
print(f"  Gold output      : {GOLD}.care_gaps_bcs")
print("=" * 55)

# ================================================================
# CELL 2 — VERIFY SILVER TABLES EXIST
# ================================================================

print("\nChecking silver tables...")
tables = [
    "member_demographics",
    "member_enrollment",
    "claims_procedure",
    "claims_diagnoses"
]

for t in tables:
    try:
        cnt = spark.sql(f"SELECT COUNT(*) AS n FROM {SILVER}.{t}").collect()[0]["n"]
        print(f"  ✅ {SILVER}.{t} — {cnt} rows")
    except Exception as e:
        print(f"  ❌ {SILVER}.{t} — NOT FOUND: {e}")

# ================================================================
# CELL 3 — EXCLUSION A: HOSPICE
# ================================================================

print("\n" + "=" * 55)
print("STEP 1: Building hospice exclusion...")

excl_hospice_sql = f"""
    SELECT DISTINCT member_id,
           'Hospice flag on procedure claim'  AS exclusion_evidence
    FROM {SILVER}.claims_procedure
    WHERE is_hospice = TRUE
      AND YEAR(service_date) = {YEAR}

    UNION

    SELECT DISTINCT member_id,
           'BCS hospice flag on claim'        AS exclusion_evidence
    FROM {SILVER}.claims_procedure
    WHERE is_bcs_hospice = TRUE
      AND YEAR(service_date) = {YEAR}

    UNION

    SELECT DISTINCT member_id,
           'Place of service 34 (Hospice)'   AS exclusion_evidence
    FROM {SILVER}.claims_procedure
    WHERE place_of_service_code = '34'
      AND YEAR(service_date)    = {YEAR}

    UNION

    SELECT DISTINCT member_id,
           'ICD Z51.5 palliative care dx'     AS exclusion_evidence
    FROM {SILVER}.claims_diagnoses
    WHERE is_hospice_dx = TRUE
      AND YEAR(service_date) = {YEAR}

    UNION

    SELECT DISTINCT member_id,
           'BCS hospice diagnosis flag'       AS exclusion_evidence
    FROM {SILVER}.claims_diagnoses
    WHERE is_bcs_hospice_dx = TRUE
      AND YEAR(service_date) = {YEAR}
"""

excl_hospice_df = spark.sql(excl_hospice_sql)
excl_hospice_df.createOrReplaceTempView("excl_hospice_bcs")

hospice_count = excl_hospice_df.select("member_id").distinct().count()
print(f"  ✅ Hospice exclusion built — {hospice_count} members excluded")
excl_hospice_df.show(truncate=False)

# ================================================================
# CELL 4 — EXCLUSION B: BILATERAL MASTECTOMY
# ================================================================

print("\n" + "=" * 55)
print("STEP 2: Building bilateral mastectomy exclusion...")

excl_bilateral_sql = f"""
    -- Source 1: Z90.13 = direct bilateral breast absence
    SELECT DISTINCT member_id,
           'Z90.13 bilateral breast absence'            AS exclusion_evidence,
           'Z90.13'                                      AS exclusion_code
    FROM {SILVER}.claims_diagnoses
    WHERE is_bcs_bilateral_breast_absence = TRUE

    UNION

    -- Source 2: Both Z90.11 (right) AND Z90.12 (left) present
    -- M007 has only left (Z90.12) → will NOT match → correctly not excluded
    SELECT DISTINCT r.member_id,
           'Z90.11 right + Z90.12 left both present'   AS exclusion_evidence,
           'Z90.11+Z90.12'                              AS exclusion_code
    FROM (
        SELECT DISTINCT member_id FROM {SILVER}.claims_diagnoses
        WHERE is_bcs_unilateral_right_mastectomy = TRUE
    ) r
    INNER JOIN (
        SELECT DISTINCT member_id FROM {SILVER}.claims_diagnoses
        WHERE is_bcs_unilateral_left_mastectomy = TRUE
    ) l ON r.member_id = l.member_id

    UNION

    -- Source 3: Z90.10 = unspecified breast absence
    SELECT DISTINCT member_id,
           'Z90.10 unspecified breast absence'          AS exclusion_evidence,
           'Z90.10'                                      AS exclusion_code
    FROM {SILVER}.claims_diagnoses
    WHERE diagnosis_code = 'Z90.10'

    UNION

    -- Source 4: CPT mastectomy with bilateral flag (modifier 50 or laterality)
    SELECT DISTINCT member_id,
           'Bilateral mastectomy CPT with modifier 50'  AS exclusion_evidence,
           procedure_code                               AS exclusion_code
    FROM {SILVER}.claims_procedure
    WHERE is_bcs_bilateral_mastectomy = TRUE
"""

excl_bilateral_df = spark.sql(excl_bilateral_sql)
excl_bilateral_df.createOrReplaceTempView("excl_bilateral_mastectomy")

bilateral_count = excl_bilateral_df.select("member_id").distinct().count()
print(f"  ✅ Bilateral mastectomy exclusion built — {bilateral_count} members excluded")
excl_bilateral_df.show(truncate=False)

# Verify M007 is NOT in bilateral exclusion (has left side only)
m007_check = excl_bilateral_df.filter("member_id = 'M007'").count()
print(f"  ✅ M007 in bilateral exclusion: {m007_check} rows (expected 0 — left only)")

# ================================================================
# CELL 5 — DENOMINATOR
# ================================================================

print("\n" + "=" * 55)
print("STEP 3: Building BCS denominator...")

denom_sql = f"""
    SELECT DISTINCT
        m.member_id,
        m.first_name,
        m.last_name,
        m.date_of_birth,
        m.age_as_of_year_end                   AS age,
        m.gender,
        m.member_status,
        m.phone_primary,
        m.phone_secondary,
        m.email,
        m.preferred_name,
        m.preferred_language,
        m.communication_preference,
        m.address_line1,
        m.city,
        m.state,
        m.zip_code,
        m.medicare_flag,
        m.medicare_beneficiary_id,
        e.product_line,
        e.plan_type,
        e.snp_type,
        e.line_of_business_detail,
        e.assigned_pcp_npi,
        e.assigned_pcp_name,
        e.assigned_pcp_id,
        e.enrollment_start_date,
        e.enrollment_end_date,
        e.continuous_enrollment_my2025,
        e.enrollment_gap_days,
        e.has_allowable_gap,
        m.risk_score,
        m.risk_category,
        m.sdoh_barriers,
        m.area_deprivation_index
    FROM {SILVER}.member_demographics m
    JOIN {SILVER}.member_enrollment   e
        ON m.member_id = e.member_id
    WHERE
        -- Criterion 1: Female
        m.gender                            = 'F'
        -- Criterion 2: Age 52-74 as of Dec 31
        AND m.age_as_of_year_end  BETWEEN 52 AND 74
        -- Criterion 3: Active
        AND m.member_status                 = 'Active'
        -- Criterion 4: Not deceased
        AND m.deceased_date                IS NULL
        -- Criterion 5: Measurement year
        AND e.measurement_year              = {YEAR}
        -- Criterion 6: Continuous enrollment OR allowable gap ≤ 45 days
        AND (
            e.continuous_enrollment_my2025 = TRUE
            OR (e.has_allowable_gap = TRUE AND e.enrollment_gap_days <= 45)
        )
        -- Criterion 7: Commercial or Medicare (NOT Medicaid-only)
        AND e.product_line         IN ('Commercial', 'Medicare')
        -- Criterion 8: Must have medical benefit
        AND e.has_medical_benefit           = TRUE
        -- Criterion 9: Pre-computed eligibility flag
        AND e.eligible_bcs                  = TRUE
"""

denom_df = spark.sql(denom_sql)
denom_df.createOrReplaceTempView("denom_bcs")

denom_count = denom_df.count()
print(f"  ✅ BCS denominator built — {denom_count} eligible members")
print("\n  Denominator members:")
denom_df.select("member_id", "age", "gender", "product_line",
                "continuous_enrollment_my2025", "assigned_pcp_name") \
        .orderBy("member_id") \
        .show(truncate=False)

# ================================================================
# CELL 6 — NUMERATOR
# ================================================================

print("\n" + "=" * 55)
print("STEP 4: Building BCS numerator (mammogram evidence)...")

numer_sql = f"""
    WITH mammogram_claims AS (
        SELECT
            cp.member_id,
            cp.service_date                                          AS mammogram_date,
            cp.procedure_code,
            cp.procedure_description,
            cp.place_of_service_code,
            cp.place_of_service_description,
            cp.claim_status,
            cp.claim_id,
            cp.rendering_provider_npi,
            cp.rendering_provider_name,
            cp.facility_name,
            cp.revenue_code,
            cp.laterality,
            CASE
                WHEN cp.procedure_code IN ('77065','77066','77067')
                     THEN 'CPT Mammography'
                WHEN cp.procedure_code IN ('G0202','G0204','G0206')
                     THEN 'HCPCS Medicare Mammography'
                WHEN cp.revenue_code = '0401'
                     THEN 'Revenue Code 0401 Facility'
                ELSE 'Other'
            END                                                      AS mammogram_source,
            ADD_MONTHS(TO_DATE('{END}'), -{BCS_LOOKBACK_MONTHS})     AS lookback_start,
            ROW_NUMBER() OVER (
                PARTITION BY cp.member_id
                ORDER BY cp.service_date DESC, cp.claim_id DESC
            )                                                        AS rn
        FROM {SILVER}.claims_procedure cp
        -- Validate mammogram is within member's enrolled period
        INNER JOIN {SILVER}.member_enrollment e
            ON  cp.member_id    = e.member_id
            AND e.measurement_year = {YEAR}
            AND cp.service_date BETWEEN e.enrollment_start_date
                                    AND COALESCE(e.enrollment_end_date, TO_DATE('{END}'))
        WHERE
            -- Must be flagged as BCS mammogram
            cp.is_bcs_mammogram     = TRUE
            -- Paid claims only
            AND cp.claim_status      = 'Paid'
            -- Within 27-month lookback window
            AND cp.service_date     >= ADD_MONTHS(TO_DATE('{END}'), -{BCS_LOOKBACK_MONTHS})
            AND cp.service_date     <= TO_DATE('{END}')
            -- In-person only — NO telehealth
            AND COALESCE(cp.place_of_service_code, '11')
                NOT IN ('02', '10')
    )
    SELECT
        member_id,
        mammogram_date,
        procedure_code,
        procedure_description,
        place_of_service_code,
        claim_id,
        rendering_provider_name,
        facility_name,
        mammogram_source,
        lookback_start
    FROM mammogram_claims
    WHERE rn = 1
"""

numer_df = spark.sql(numer_sql)
numer_df.createOrReplaceTempView("numer_bcs")

numer_count = numer_df.count()
print(f"  ✅ BCS numerator built — {numer_count} members with mammogram evidence")
print("\n  Mammogram evidence found:")
numer_df.select("member_id", "mammogram_date", "procedure_code",
                "mammogram_source", "facility_name") \
        .orderBy("member_id") \
        .show(truncate=False)

# ================================================================
# CELL 7 — GAP DETECTION LOGIC
# ================================================================

print("\n" + "=" * 55)
print("STEP 5: Running gap detection — OPEN / CLOSED / EXCLUDED...")

gaps_sql = f"""
    WITH gap_base AS (
        SELECT
            CONCAT(d.member_id, '_BCS_{YEAR}')            AS gap_id,
            d.member_id,
            {YEAR}                                         AS measurement_year,
            'BCS'                                          AS measure_code,
            'Breast Cancer Screening'                      AS measure_name,
            'Mammography'                                  AS measure_component,
            'HEDIS 2025'                                   AS measure_spec_version,

            -- ── Gap Status ─────────────────────────────────
            CASE
                WHEN bm.member_id IS NOT NULL              THEN 'EXCLUDED'
                WHEN h.member_id  IS NOT NULL              THEN 'EXCLUDED'
                WHEN n.member_id  IS NOT NULL              THEN 'CLOSED'
                ELSE                                            'OPEN'
            END                                            AS gap_status,

            -- ── Exclusion Details ──────────────────────────
            CASE
                WHEN bm.member_id IS NOT NULL              THEN 'Bilateral Mastectomy'
                WHEN h.member_id  IS NOT NULL              THEN 'Hospice'
                ELSE                                            NULL
            END                                            AS exclusion_reason,

            CASE
                WHEN bm.member_id IS NOT NULL              THEN bm.exclusion_code
                WHEN h.member_id  IS NOT NULL              THEN 'Q5003/POS-34/Z51.5'
                ELSE                                            NULL
            END                                            AS exclusion_code,

            CASE
                WHEN bm.member_id IS NOT NULL              THEN bm.exclusion_evidence
                WHEN h.member_id  IS NOT NULL              THEN h.exclusion_evidence
                ELSE                                            NULL
            END                                            AS exclusion_evidence,

            -- ── Gap Description ────────────────────────────
            CASE
                WHEN bm.member_id IS NOT NULL
                    THEN CONCAT('EXCLUDED: Bilateral mastectomy (',
                                bm.exclusion_evidence, ')')
                WHEN h.member_id IS NOT NULL
                    THEN CONCAT('EXCLUDED: Hospice care in {YEAR} (',
                                h.exclusion_evidence, ')')
                WHEN n.member_id IS NOT NULL
                    THEN CONCAT('CLOSED: Mammogram on ',
                                CAST(n.mammogram_date AS STRING),
                                ' | ', n.mammogram_source,
                                ' | CPT: ', n.procedure_code)
                ELSE
                    CONCAT('OPEN: No mammogram in 27-month window (',
                           CAST(ADD_MONTHS(TO_DATE('{END}'), -{BCS_LOOKBACK_MONTHS}) AS STRING),
                           ' to {END})')
            END                                            AS gap_description,

            -- ── Recommended Action ─────────────────────────
            CASE
                WHEN bm.member_id IS NOT NULL OR h.member_id IS NOT NULL THEN NULL
                WHEN n.member_id  IS NOT NULL              THEN NULL
                ELSE 'Schedule mammogram — CPT 77067 or HCPCS G0202 within 27-month window'
            END                                            AS recommended_action,

            -- ── Flags ──────────────────────────────────────
            CASE WHEN bm.member_id IS NULL AND h.member_id IS NULL
                 THEN TRUE  ELSE FALSE END                 AS in_denominator,
            CASE WHEN bm.member_id IS NOT NULL OR h.member_id IS NOT NULL
                 THEN TRUE  ELSE FALSE END                 AS is_excluded,
            CASE WHEN n.member_id  IS NOT NULL
                 THEN TRUE  ELSE FALSE END                 AS numerator_met,

            -- ── Numerator Evidence ─────────────────────────
            n.procedure_code                               AS numerator_evidence_code,
            n.mammogram_source                             AS numerator_evidence_type,
            n.mammogram_date                               AS numerator_evidence_date,
            n.facility_name                                AS numerator_facility,
            n.rendering_provider_name                      AS numerator_provider,
            CASE WHEN n.member_id IS NOT NULL
                 THEN 'Claims' ELSE NULL END               AS numerator_source,

            -- ── Dates ──────────────────────────────────────
            CURRENT_DATE()                                 AS detected_date,
            TO_DATE('{END}')                               AS due_date,
            DATEDIFF(TO_DATE('{END}'), CURRENT_DATE())     AS days_remaining,
            CASE WHEN n.member_id IS NOT NULL
                 THEN n.mammogram_date ELSE NULL END        AS closed_date,
            ADD_MONTHS(TO_DATE('{END}'), -{BCS_LOOKBACK_MONTHS}) AS lookback_start_date,
            TO_DATE('{END}')                               AS lookback_end_date,

            -- ── Denominator Criteria JSON ──────────────────
            CONCAT(
                '{{"gender":"', d.gender,
                '","age":',     CAST(d.age AS STRING),
                ',"product":"', d.product_line,
                '","enrolled":', CAST(d.continuous_enrollment_my2025 AS STRING),
                ',"med_benefit":true}}'
            )                                              AS denominator_criteria,

            -- ── Provider Attribution ───────────────────────
            d.assigned_pcp_npi                             AS attributed_pcp_npi,
            d.assigned_pcp_name                            AS attributed_pcp_name,
            d.assigned_pcp_id                              AS attributed_pcp_id,

            -- ── Member Info for Outreach ───────────────────
            d.first_name,
            d.last_name,
            d.date_of_birth,
            d.age,
            d.phone_primary,
            d.phone_secondary,
            d.email,
            d.preferred_name,
            d.preferred_language,
            d.communication_preference,
            d.address_line1,
            d.city,
            d.state,
            d.zip_code,
            d.product_line,
            d.plan_type,
            d.snp_type,
            d.medicare_flag,

            -- ── Risk & SDoH ────────────────────────────────
            d.risk_score,
            d.risk_category,
            d.sdoh_barriers,
            d.area_deprivation_index,

            -- ── Outreach Tracking ──────────────────────────
            0                                              AS outreach_attempts,
            CAST(NULL AS DATE)                             AS last_outreach_date,
            CAST(NULL AS STRING)                           AS last_outreach_channel,
            CAST(NULL AS DATE)                             AS next_outreach_date,
            CAST(NULL AS STRING)                           AS next_outreach_channel,
            CAST(NULL AS STRING)                           AS outreach_outcome,

            -- ── Gen AI Fields ──────────────────────────────
            CAST(NULL AS STRING)                           AS ai_patient_summary,
            CAST(NULL AS STRING)                           AS ai_outreach_script,
            CAST(NULL AS STRING)                           AS ai_risk_explanation,
            CAST(NULL AS TIMESTAMP)                        AS ai_generated_date,

            -- ── Audit ──────────────────────────────────────
            '{RUN_ID}'                                     AS pipeline_run_id,
            CURRENT_TIMESTAMP()                            AS created_date,
            CURRENT_TIMESTAMP()                            AS updated_date,
            'PYSPARK_NOTEBOOK'                             AS data_source

        FROM denom_bcs d
        LEFT JOIN excl_bilateral_mastectomy bm ON d.member_id = bm.member_id
        LEFT JOIN excl_hospice_bcs          h  ON d.member_id = h.member_id
        LEFT JOIN numer_bcs                 n  ON d.member_id = n.member_id
    )

    -- Add priority score on top
    SELECT
        *,
        CASE
            WHEN gap_status != 'OPEN' THEN 0.0
            ELSE LEAST(10.0, ROUND(
                  7.0
                + CASE WHEN days_remaining < 60  THEN 2.0
                       WHEN days_remaining < 90  THEN 1.5
                       WHEN days_remaining < 120 THEN 1.0
                       ELSE 0.0 END
                + CASE WHEN risk_score > 80 THEN 1.0
                       WHEN risk_score > 60 THEN 0.5
                       ELSE 0.0 END
                + CASE WHEN area_deprivation_index > 70 THEN 0.5
                       ELSE 0.0 END
            , 2))
        END                                                AS priority_score,

        CASE
            WHEN gap_status != 'OPEN' THEN NULL
            WHEN LEAST(10.0, ROUND(
                  7.0
                + CASE WHEN days_remaining < 60  THEN 2.0
                       WHEN days_remaining < 90  THEN 1.5
                       WHEN days_remaining < 120 THEN 1.0 ELSE 0.0 END
                + CASE WHEN risk_score > 80 THEN 1.0
                       WHEN risk_score > 60 THEN 0.5 ELSE 0.0 END
                + CASE WHEN area_deprivation_index > 70 THEN 0.5 ELSE 0.0 END
            , 2)) >= 9.0 THEN 'Critical'
            WHEN LEAST(10.0, ROUND(
                  7.0
                + CASE WHEN days_remaining < 60  THEN 2.0
                       WHEN days_remaining < 90  THEN 1.5
                       WHEN days_remaining < 120 THEN 1.0 ELSE 0.0 END
                + CASE WHEN risk_score > 80 THEN 1.0
                       WHEN risk_score > 60 THEN 0.5 ELSE 0.0 END
                + CASE WHEN area_deprivation_index > 70 THEN 0.5 ELSE 0.0 END
            , 2)) >= 7.0 THEN 'High'
            WHEN LEAST(10.0, ROUND(
                  7.0
                + CASE WHEN days_remaining < 60  THEN 2.0
                       WHEN days_remaining < 90  THEN 1.5
                       WHEN days_remaining < 120 THEN 1.0 ELSE 0.0 END
                + CASE WHEN risk_score > 80 THEN 1.0
                       WHEN risk_score > 60 THEN 0.5 ELSE 0.0 END
                + CASE WHEN area_deprivation_index > 70 THEN 0.5 ELSE 0.0 END
            , 2)) >= 5.0 THEN 'Medium'
            ELSE 'Low'
        END                                                AS priority_tier

    FROM gap_base
"""

gaps_df = spark.sql(gaps_sql)
gaps_df.createOrReplaceTempView("gaps_bcs")

total = gaps_df.count()
open_cnt     = gaps_df.filter("gap_status = 'OPEN'").count()
closed_cnt   = gaps_df.filter("gap_status = 'CLOSED'").count()
excluded_cnt = gaps_df.filter("gap_status = 'EXCLUDED'").count()

print(f"\n  ✅ Gap detection complete — {total} total rows")
print(f"     OPEN     : {open_cnt}")
print(f"     CLOSED   : {closed_cnt}")
print(f"     EXCLUDED : {excluded_cnt}")

print("\n  Full gap results:")
gaps_df.select(
    "member_id","gap_status","exclusion_reason",
    "numerator_evidence_date","days_remaining",
    "priority_score","priority_tier","attributed_pcp_name"
).orderBy("gap_status","member_id").show(50, truncate=False)

# ================================================================
# CELL 8 — WRITE TO GOLD TABLE: care_gaps_bcs
# ================================================================

print("\n" + "=" * 55)
print("STEP 6: Writing to gold.care_gaps_bcs...")

# Delete existing BCS rows for this measurement year (safe re-run)
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {GOLD}.care_gaps_bcs
    USING DELTA
    COMMENT 'BCS gap detection output — HEDIS 2025'
    AS SELECT * FROM gaps_bcs WHERE 1=0
""")

spark.sql(f"""
    DELETE FROM {GOLD}.care_gaps_bcs
    WHERE measure_code      = 'BCS'
      AND measurement_year  = {YEAR}
""")

# Write all BCS gaps
gaps_df.write \
    .format("delta") \
    .mode("append") \
    .option("mergeSchema", "true") \
    .saveAsTable(f"{GOLD}.care_gaps_bcs")

written = spark.sql(f"""
    SELECT COUNT(*) AS n FROM {GOLD}.care_gaps_bcs
    WHERE measure_code = 'BCS' AND measurement_year = {YEAR}
""").collect()[0]["n"]

print(f"  ✅ Written {written} rows to {GOLD}.care_gaps_bcs")

# ================================================================
# CELL 9 — WRITE TO MASTER TABLE: care_gaps
# ================================================================

print("\n" + "=" * 55)
print("STEP 7: Writing to gold.care_gaps (master table)...")

spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {GOLD}.care_gaps
    USING DELTA
    COMMENT 'Master HEDIS gap table — all measures combined'
    AS SELECT * FROM gaps_bcs WHERE 1=0
""")

spark.sql(f"""
    DELETE FROM {GOLD}.care_gaps
    WHERE measure_code     = 'BCS'
      AND measurement_year = {YEAR}
""")

gaps_df.write \
    .format("delta") \
    .mode("append") \
    .option("mergeSchema", "true") \
    .saveAsTable(f"{GOLD}.care_gaps")

master_cnt = spark.sql(f"SELECT COUNT(*) AS n FROM {GOLD}.care_gaps").collect()[0]["n"]
print(f"  ✅ Written to {GOLD}.care_gaps — total rows in master table: {master_cnt}")

# ================================================================
# CELL 10 — VERIFICATION QUERIES
# ================================================================

print("\n" + "=" * 55)
print("STEP 8: Running verification checks...")
print("=" * 55)

# ── Check 1: Summary by gap status ──────────────────────────────
print("\n📊 GAP SUMMARY:")
spark.sql(f"""
    SELECT
        gap_status,
        COUNT(*)                                              AS members,
        COUNT(CASE WHEN priority_tier = 'Critical' THEN 1 END) AS critical,
        COUNT(CASE WHEN priority_tier = 'High'     THEN 1 END) AS high,
        COUNT(CASE WHEN priority_tier = 'Medium'   THEN 1 END) AS medium
    FROM {GOLD}.care_gaps_bcs
    WHERE measurement_year = {YEAR}
    GROUP BY gap_status
    ORDER BY gap_status
""").show()

# ── Check 2: HEDIS compliance rate ──────────────────────────────
print("\n📊 HEDIS BCS COMPLIANCE RATE:")
spark.sql(f"""
    SELECT
        'BCS'                                                  AS measure,
        COUNT(CASE WHEN in_denominator=TRUE AND is_excluded=FALSE
                   THEN 1 END)                                 AS eligible_denominator,
        COUNT(CASE WHEN numerator_met=TRUE  THEN 1 END)        AS numerator,
        COUNT(CASE WHEN gap_status='OPEN'   THEN 1 END)        AS open_gaps,
        COUNT(CASE WHEN is_excluded=TRUE    THEN 1 END)        AS excluded,
        ROUND(
            COUNT(CASE WHEN numerator_met=TRUE THEN 1 END) * 100.0
            / NULLIF(COUNT(CASE WHEN in_denominator=TRUE
                                 AND is_excluded=FALSE THEN 1 END), 0)
        , 1)                                                   AS compliance_pct
    FROM {GOLD}.care_gaps_bcs
    WHERE measurement_year = {YEAR}
""").show()

# ── Check 3: Open gaps for outreach ─────────────────────────────
print("\n📊 OPEN GAPS — OUTREACH PRIORITY LIST:")
spark.sql(f"""
    SELECT
        member_id,
        CONCAT(first_name,' ',last_name)   AS member_name,
        age,
        phone_primary,
        preferred_language,
        days_remaining,
        priority_tier,
        priority_score,
        attributed_pcp_name
    FROM {GOLD}.care_gaps_bcs
    WHERE gap_status        = 'OPEN'
      AND measurement_year  = {YEAR}
    ORDER BY priority_score DESC, days_remaining ASC
""").show(truncate=False)

# ── Check 4: Exclusion audit ─────────────────────────────────────
print("\n📊 EXCLUDED MEMBERS AUDIT:")
spark.sql(f"""
    SELECT
        member_id,
        CONCAT(first_name,' ',last_name)   AS member_name,
        exclusion_reason,
        exclusion_code,
        exclusion_evidence,
        gap_description
    FROM {GOLD}.care_gaps_bcs
    WHERE gap_status       = 'EXCLUDED'
      AND measurement_year = {YEAR}
    ORDER BY exclusion_reason
""").show(truncate=False)

# ── Check 5: Closed gap audit ────────────────────────────────────
print("\n📊 CLOSED GAPS — MAMMOGRAM EVIDENCE:")
spark.sql(f"""
    SELECT
        member_id,
        CONCAT(first_name,' ',last_name)   AS member_name,
        numerator_evidence_code            AS cpt_code,
        numerator_evidence_type            AS mammogram_type,
        numerator_evidence_date            AS mammogram_date,
        numerator_facility
    FROM {GOLD}.care_gaps_bcs
    WHERE gap_status       = 'CLOSED'
      AND measurement_year = {YEAR}
    ORDER BY numerator_evidence_date
""").show(truncate=False)

# ── Check 6: PCP-level summary ───────────────────────────────────
print("\n📊 PCP-LEVEL GAP SUMMARY:")
spark.sql(f"""
    SELECT
        attributed_pcp_npi,
        attributed_pcp_name,
        COUNT(*)                                              AS total_patients,
        COUNT(CASE WHEN gap_status='OPEN'     THEN 1 END)    AS open_gaps,
        COUNT(CASE WHEN gap_status='CLOSED'   THEN 1 END)    AS closed,
        COUNT(CASE WHEN gap_status='EXCLUDED' THEN 1 END)    AS excluded,
        ROUND(
            COUNT(CASE WHEN gap_status='CLOSED' THEN 1 END)*100.0
            / NULLIF(COUNT(CASE WHEN gap_status IN ('OPEN','CLOSED') THEN 1 END),0)
        ,1)                                                   AS compliance_pct
    FROM {GOLD}.care_gaps_bcs
    WHERE measurement_year = {YEAR}
    GROUP BY attributed_pcp_npi, attributed_pcp_name
    ORDER BY open_gaps DESC
""").show(truncate=False)

# ── Check 7: Validate M007 (unilateral only — must NOT be excluded)
print("\n📊 M007 VALIDATION (should be OPEN, not EXCLUDED):")
spark.sql(f"""
    SELECT member_id, gap_status, exclusion_reason, gap_description
    FROM {GOLD}.care_gaps_bcs
    WHERE member_id = 'M007'
""").show(truncate=False)

# ── Check 8: Validate M004 (bilateral — must be excluded) ────────
print("\n📊 M004 VALIDATION (should be EXCLUDED — bilateral mastectomy):")
spark.sql(f"""
    SELECT member_id, gap_status, exclusion_reason, exclusion_code, gap_description
    FROM {GOLD}.care_gaps_bcs
    WHERE member_id = 'M004'
""").show(truncate=False)

# ── Check 9: Validate M006 (hospice — must be excluded) ──────────
print("\n📊 M006 VALIDATION (should be EXCLUDED — hospice):")
spark.sql(f"""
    SELECT member_id, gap_status, exclusion_reason, exclusion_code, gap_description
    FROM {GOLD}.care_gaps_bcs
    WHERE member_id = 'M006'
""").show(truncate=False)

# ── Check 10: Table info ─────────────────────────────────────────
print("\n📊 FINAL TABLE DETAILS:")
spark.sql(f"DESCRIBE TABLE {GOLD}.care_gaps_bcs").show(50, truncate=False)

# ================================================================
# CELL 11 — FINAL SUMMARY
# ================================================================

print("\n" + "=" * 55)
print("BCS GAP DETECTION ENGINE — COMPLETE")
print("=" * 55)

final = spark.sql(f"""
    SELECT
        COUNT(*)                                              AS total_rows,
        COUNT(CASE WHEN gap_status='OPEN'     THEN 1 END)    AS open_gaps,
        COUNT(CASE WHEN gap_status='CLOSED'   THEN 1 END)    AS closed,
        COUNT(CASE WHEN gap_status='EXCLUDED' THEN 1 END)    AS excluded,
        COUNT(CASE WHEN priority_tier='Critical' THEN 1 END) AS critical_priority,
        COUNT(CASE WHEN priority_tier='High'     THEN 1 END) AS high_priority,
        ROUND(
            COUNT(CASE WHEN numerator_met=TRUE THEN 1 END)*100.0
            / NULLIF(COUNT(CASE WHEN in_denominator=TRUE
                                 AND is_excluded=FALSE THEN 1 END),0)
        ,1) AS compliance_pct
    FROM {GOLD}.care_gaps_bcs
    WHERE measurement_year = {YEAR}
""").collect()[0]

print(f"  Total rows written : {final['total_rows']}")
print(f"  OPEN gaps          : {final['open_gaps']}  ← needs outreach")
print(f"  CLOSED gaps        : {final['closed']}   ← care received")
print(f"  EXCLUDED           : {final['excluded']}   ← correctly removed")
print(f"  Critical priority  : {final['critical_priority']}")
print(f"  High priority      : {final['high_priority']}")
print(f"  BCS compliance     : {final['compliance_pct']}%")
print(f"\n  Output table : {GOLD}.care_gaps_bcs")
print(f"  Master table : {GOLD}.care_gaps")
print("=" * 55)
print("  Next step: query gold.care_gaps_bcs for outreach lists")
print("=" * 55)
