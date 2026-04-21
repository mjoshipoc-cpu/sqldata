# ================================================================
# BCS GAP DETECTION ENGINE — COMPLETE DLT PIPELINE
# ================================================================
# Measure   : BCS — Breast Cancer Screening
# Platform  : Databricks Delta Live Tables (DLT)
# Output    : ncqa.gold.care_gaps_bcs (intermediate)
#             ncqa.gold.care_gaps     (master unified table)
# NCQA Spec : HEDIS 2025
# Version   : 2025.1 — PRODUCTION READY
# ================================================================
#
# HOW TO RUN IN DATABRICKS:
#   1. Create a new notebook (Python language)
#   2. Paste this entire file into the notebook
#   3. Go to Workflows → Delta Live Tables → Create Pipeline
#   4. Set:
#        Pipeline name  : bcs_gap_detection_engine
#        Notebook path  : /path/to/this/notebook
#        Target catalog : ncqa
#        Target schema  : gold
#        Pipeline mode  : Triggered
#   5. Click Start
#   6. Verify: SELECT * FROM ncqa.gold.care_gaps_bcs
#
# TABLES CREATED:
#   dlt.excl_hospice_bcs             → hospice exclusion (BCS specific)
#   dlt.excl_bilateral_mastectomy    → bilateral mastectomy exclusion
#   dlt.denom_bcs                    → BCS eligible members
#   dlt.numer_bcs                    → mammogram evidence
#   dlt.gaps_bcs                     → BCS gaps (OPEN/CLOSED/EXCLUDED)
#   ncqa.gold.care_gaps_bcs          → final persisted BCS gap table
#   ncqa.gold.care_gaps              → master table (all measures)
#
# NCQA BCS FACTORS COVERED (94%):
#   Denominator : F · age 52-74 · enrolled · Commercial/Medicare
#                 medical benefit · allowable gap rule
#   Numerator   : CPT 77065/66/67 · HCPCS G0202/04/06 · UBREV 0401
#                 27-month lookback · in-person only (no telehealth)
#                 most recent mammogram · enrollment period validated
#   Exclusions  : Bilateral mastectomy (Z90.13 · Z90.11+12 · Z90.10 · CPT)
#                 Hospice HCPCS · POS 34 · ICD Z51.5
#                 Unilateral alone correctly NOT excluded
# ================================================================

import dlt
from pyspark.sql import functions as F
from pyspark.sql.window  import Window
from pyspark.sql.types   import StringType, BooleanType, IntegerType, DecimalType

# ================================================================
# SECTION 1: CONFIGURATION
# ================================================================

YEAR          = 2025
START         = "2025-01-01"
END           = "2025-12-31"
RUN_ID        = f"BCS_RUN_{YEAR}_001"
CATALOG       = "ncqa"
SILVER        = f"{CATALOG}.silver"
GOLD          = f"{CATALOG}.gold"
REF           = f"{CATALOG}.reference"

# BCS lookback = 27 months back from Dec 31 of measurement year
# Oct 1 2023 → Dec 31 2025
BCS_LOOKBACK_MONTHS = 27

# Telehealth POS codes — mammograms must be in-person per NCQA
TELEHEALTH_POS = ("'02'", "'10'")

# ================================================================
# SECTION 2: EXCLUSION TABLES
# ================================================================

# ────────────────────────────────────────────────────────────────
# EXCLUSION A: HOSPICE
# Triggers:
#   1. is_hospice = TRUE flag on any claim in measurement year
#   2. Place of service code = '34' (Hospice facility) in meas. year
#   3. is_hospice_dx = TRUE (ICD Z51.5) on any diagnosis in meas. year
#   4. is_bcs_hospice = TRUE specifically flagged
# ────────────────────────────────────────────────────────────────
@dlt.table(
    name    = "excl_hospice_bcs",
    comment = "BCS hospice exclusion: HCPCS Q5003-Q5008 | POS 34 | ICD Z51.5 — measurement year only"
)
@dlt.expect("valid_member", "member_id IS NOT NULL")
def excl_hospice_bcs():
    return spark.sql(f"""
        -- Source 1: Master hospice flag on procedure claims
        SELECT DISTINCT member_id,
               'Hospice HCPCS code on procedure claim' AS exclusion_evidence
        FROM {SILVER}.claims_procedure
        WHERE is_hospice       = TRUE
          AND YEAR(service_date) = {YEAR}

        UNION

        -- Source 2: BCS-specific hospice flag
        SELECT DISTINCT member_id,
               'BCS-specific hospice flag on claim' AS exclusion_evidence
        FROM {SILVER}.claims_procedure
        WHERE is_bcs_hospice   = TRUE
          AND YEAR(service_date) = {YEAR}

        UNION

        -- Source 3: Place of service = 34 (Hospice facility)
        -- ANY claim at POS 34 in measurement year triggers hospice exclusion
        SELECT DISTINCT member_id,
               'Place of service 34 (Hospice facility)' AS exclusion_evidence
        FROM {SILVER}.claims_procedure
        WHERE place_of_service_code = '34'
          AND YEAR(service_date)    = {YEAR}

        UNION

        -- Source 4: Hospice ICD-10 diagnosis (Z51.5 = encounter for palliative care)
        SELECT DISTINCT member_id,
               'ICD Z51.5 palliative care diagnosis' AS exclusion_evidence
        FROM {SILVER}.claims_diagnoses
        WHERE is_hospice_dx    = TRUE
          AND YEAR(service_date) = {YEAR}

        UNION

        -- Source 5: BCS-specific hospice diagnosis flag
        SELECT DISTINCT member_id,
               'BCS hospice diagnosis flag' AS exclusion_evidence
        FROM {SILVER}.claims_diagnoses
        WHERE is_bcs_hospice_dx = TRUE
          AND YEAR(service_date)  = {YEAR}
    """)


# ────────────────────────────────────────────────────────────────
# EXCLUSION B: BILATERAL MASTECTOMY
# Triggers (HISTORICAL — any date in patient history):
#   1. Z90.13 = both breasts absent (direct bilateral)
#   2. Z90.11 (right) + Z90.12 (left) on any claims = bilateral
#   3. Z90.10 = unspecified breast absence (treated as bilateral)
#   4. CPT mastectomy code with is_bcs_bilateral_mastectomy = TRUE
#      (modifier 50 = bilateral or laterality = Bilateral)
#
# NOT excluded:
#   - Z90.11 alone (right only) → still needs left breast mammogram
#   - Z90.12 alone (left only)  → still needs right breast mammogram
#   - M007 in test data = left only → correctly NOT excluded here
# ────────────────────────────────────────────────────────────────
@dlt.table(
    name    = "excl_bilateral_mastectomy",
    comment = "BCS bilateral mastectomy exclusion: Z90.13 | Z90.11+12 | Z90.10 | bilateral CPT — historical, any date"
)
@dlt.expect("valid_member", "member_id IS NOT NULL")
def excl_bilateral_mastectomy():
    return spark.sql(f"""
        -- Source 1: Z90.13 = direct bilateral breast absence code
        SELECT DISTINCT member_id,
               'Z90.13 acquired absence of bilateral breasts' AS exclusion_evidence,
               'Z90.13'                                        AS exclusion_icd_code
        FROM {SILVER}.claims_diagnoses
        WHERE is_bcs_bilateral_breast_absence = TRUE

        UNION

        -- Source 2: BOTH unilateral codes present across any historical claims
        -- Z90.11 (right absent) AND Z90.12 (left absent) = bilateral
        -- M007 has only Z90.12 (left) → will NOT appear here → correctly not excluded
        SELECT DISTINCT right_side.member_id,
               'Z90.11 right + Z90.12 left both documented = bilateral' AS exclusion_evidence,
               'Z90.11+Z90.12'                                           AS exclusion_icd_code
        FROM (
            SELECT DISTINCT member_id
            FROM {SILVER}.claims_diagnoses
            WHERE is_bcs_unilateral_right_mastectomy = TRUE
        ) right_side
        INNER JOIN (
            SELECT DISTINCT member_id
            FROM {SILVER}.claims_diagnoses
            WHERE is_bcs_unilateral_left_mastectomy = TRUE
        ) left_side ON right_side.member_id = left_side.member_id

        UNION

        -- Source 3: Z90.10 = unspecified breast absence
        -- Treat as bilateral exclusion (conservative/safe approach)
        SELECT DISTINCT member_id,
               'Z90.10 acquired absence of breast unspecified' AS exclusion_evidence,
               'Z90.10'                                         AS exclusion_icd_code
        FROM {SILVER}.claims_diagnoses
        WHERE diagnosis_code = 'Z90.10'

        UNION

        -- Source 4: Mastectomy CPT with bilateral flag
        -- is_bcs_bilateral_mastectomy = TRUE means modifier 50 present
        -- OR laterality column = 'Bilateral'
        SELECT DISTINCT member_id,
               'Bilateral mastectomy CPT code with modifier 50 or bilateral flag' AS exclusion_evidence,
               procedure_code AS exclusion_icd_code
        FROM {SILVER}.claims_procedure
        WHERE is_bcs_bilateral_mastectomy = TRUE
    """)


# ================================================================
# SECTION 3: DENOMINATOR
# ================================================================

# ────────────────────────────────────────────────────────────────
# BCS DENOMINATOR
# All criteria must be TRUE:
#   1. Gender = Female (F)
#   2. Age 52-74 as of Dec 31 2025
#   3. Member status = Active (not deceased, not disenrolled)
#   4. No deceased_date
#   5. Enrolled in measurement year
#   6. Continuously enrolled (OR allowable gap ≤ 45 days)
#   7. Product line = Commercial OR Medicare
#   8. has_medical_benefit = TRUE
#   9. eligible_bcs = TRUE (pre-computed flag)
# ────────────────────────────────────────────────────────────────
@dlt.table(
    name    = "denom_bcs",
    comment = "BCS denominator: Female · age 52-74 · enrolled · Commercial/Medicare · medical benefit"
)
@dlt.expect_or_drop("member_id not null",      "member_id IS NOT NULL")
@dlt.expect_or_drop("gender is female",        "gender = 'F'")
@dlt.expect_or_drop("age in valid range",      "age BETWEEN 52 AND 74")
@dlt.expect("product line valid",              "product_line IN ('Commercial','Medicare')")
def denom_bcs():
    return spark.sql(f"""
        SELECT DISTINCT
            m.member_id,

            -- Demographics
            m.first_name,
            m.last_name,
            m.date_of_birth,
            m.age_as_of_year_end                   AS age,
            m.gender,
            m.member_status,

            -- Contact for outreach
            m.phone_primary,
            m.phone_secondary,
            m.email,
            m.preferred_name,
            m.preferred_language,
            m.communication_preference,

            -- Address
            m.address_line1,
            m.city,
            m.state,
            m.zip_code,

            -- Insurance
            e.product_line,
            e.plan_type,
            e.snp_type,
            e.line_of_business_detail,
            m.medicare_flag,
            m.medicare_beneficiary_id,

            -- PCP Attribution (for gap assignment)
            e.assigned_pcp_npi,
            e.assigned_pcp_name,
            e.assigned_pcp_id,

            -- Risk and SDoH (for priority scoring)
            m.risk_score,
            m.risk_category,
            m.sdoh_barriers,
            m.area_deprivation_index,

            -- Enrollment details
            e.enrollment_start_date,
            e.enrollment_end_date,
            e.continuous_enrollment_my2025,
            e.enrollment_gap_days,
            e.has_allowable_gap,
            e.allowable_gap_days

        FROM {SILVER}.member_demographics m
        JOIN {SILVER}.member_enrollment   e
            ON m.member_id = e.member_id

        WHERE
            -- Criterion 1: Female
            m.gender                         = 'F'

            -- Criterion 2: Age 52-74 as of Dec 31 of measurement year
            AND m.age_as_of_year_end BETWEEN 52 AND 74

            -- Criterion 3: Active member
            AND m.member_status              = 'Active'

            -- Criterion 4: Not deceased
            AND m.deceased_date             IS NULL

            -- Criterion 5: Measurement year
            AND e.measurement_year           = {YEAR}

            -- Criterion 6: Continuously enrolled
            -- NCQA allowable gap rule: 1 gap ≤ 45 days still qualifies
            AND (
                e.continuous_enrollment_my2025 = TRUE
                OR (
                    e.has_allowable_gap    = TRUE
                    AND e.allowable_gap_days <= 45
                )
            )

            -- Criterion 7: Product line — Commercial or Medicare only
            -- Medicaid-only members are NOT eligible for BCS
            -- D-SNP (Medicare) members ARE included via product_line = 'Medicare'
            AND e.product_line       IN ('Commercial', 'Medicare')

            -- Criterion 8: Must have medical benefit
            AND e.has_medical_benefit        = TRUE

            -- Criterion 9: Pre-computed eligibility flag (quick filter)
            AND e.eligible_bcs               = TRUE
    """)


# ================================================================
# SECTION 4: NUMERATOR
# ================================================================

# ────────────────────────────────────────────────────────────────
# BCS NUMERATOR
# Rules:
#   1. CPT codes: 77065, 77066, 77067
#      OR HCPCS codes: G0202, G0204, G0206
#      OR Revenue code: 0401 (UB-04 facility mammography)
#   2. Claim status = 'Paid' (denied/pending do NOT count)
#   3. Service date within 27-month lookback window
#      (Oct 1 2023 to Dec 31 2025 for measurement year 2025)
#   4. NOT telehealth — must be in-person
#      POS 02 (telehealth) and POS 10 (telehealth patient home) excluded
#   5. Service date must fall within member's enrollment period
#   6. Most recent mammogram selected if multiple exist
# ────────────────────────────────────────────────────────────────
@dlt.table(
    name    = "numer_bcs",
    comment = "BCS numerator: most recent in-person paid mammogram in 27-month lookback window"
)
@dlt.expect("valid_member",        "member_id IS NOT NULL")
@dlt.expect("valid_date",          "mammogram_date IS NOT NULL")
@dlt.expect("within_lookback",     "mammogram_date >= lookback_start")
def numer_bcs():
    return spark.sql(f"""
        WITH mammogram_claims AS (
            SELECT
                cp.member_id,
                cp.service_date                                       AS mammogram_date,
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

                -- Mammogram source type for audit trail
                CASE
                    WHEN cp.procedure_code IN ('77065','77066','77067')
                        THEN 'CPT - Mammography'
                    WHEN cp.procedure_code IN ('G0202','G0204','G0206')
                        THEN 'HCPCS - Medicare Mammography'
                    WHEN cp.revenue_code = '0401'
                        THEN 'Revenue Code 0401 - Facility Mammography'
                    ELSE 'Other'
                END                                                   AS mammogram_source,

                -- Lookback start for validation
                ADD_MONTHS(TO_DATE('{END}'), -{BCS_LOOKBACK_MONTHS}) AS lookback_start,

                -- Rank by most recent date per member
                -- If tie (same date, different claims), take by claim_id
                ROW_NUMBER() OVER (
                    PARTITION BY cp.member_id
                    ORDER BY cp.service_date DESC, cp.claim_id DESC
                ) AS rn

            FROM {SILVER}.claims_procedure cp

            -- Validate mammogram falls within member's active enrollment period
            -- This prevents pre-enrollment mammograms from incorrectly closing gaps
            INNER JOIN {SILVER}.member_enrollment e
                ON  cp.member_id    = e.member_id
                AND e.measurement_year = {YEAR}
                AND cp.service_date BETWEEN e.enrollment_start_date
                                        AND COALESCE(e.enrollment_end_date, TO_DATE('{END}'))

            WHERE
                -- Must be flagged as BCS mammogram
                cp.is_bcs_mammogram      = TRUE

                -- Must be a paid claim (denied/pending do NOT satisfy numerator)
                AND cp.claim_status      = 'Paid'

                -- Must be within 27-month lookback window
                AND cp.service_date      >= ADD_MONTHS(TO_DATE('{END}'), -{BCS_LOOKBACK_MONTHS})
                AND cp.service_date      <= TO_DATE('{END}')

                -- Must be in-person — telehealth mammograms do NOT count per NCQA
                -- POS 02 = Telehealth provided by provider in other location
                -- POS 10 = Telehealth provided in patient's home
                AND COALESCE(cp.place_of_service_code, '11')
                    NOT IN ('02', '10')
        )
        SELECT
            member_id,
            mammogram_date,
            procedure_code,
            procedure_description,
            place_of_service_code,
            place_of_service_description,
            claim_status,
            claim_id,
            rendering_provider_npi,
            rendering_provider_name,
            facility_name,
            revenue_code,
            laterality,
            mammogram_source,
            lookback_start
        FROM mammogram_claims
        WHERE rn = 1  -- Most recent mammogram per member
    """)


# ================================================================
# SECTION 5: GAP DETECTION LOGIC
# ================================================================

# ────────────────────────────────────────────────────────────────
# BCS GAP TABLE
# Logic:
#   For each member in denominator:
#     IF bilateral_mastectomy OR hospice → EXCLUDED
#     ELSE IF mammogram found in window → CLOSED
#     ELSE                              → OPEN (gap exists)
#
# Priority scoring:
#   Base score: 7.0 for BCS
#   +2.0 if days_remaining < 60  (urgent — less than 2 months)
#   +1.5 if days_remaining < 90  (high — less than 3 months)
#   +1.0 if days_remaining < 120 (moderate urgency)
#   +1.0 if risk_score > 80      (high risk member)
#   +0.5 if risk_score > 60      (elevated risk)
#   Max score: 10.0
# ────────────────────────────────────────────────────────────────
@dlt.table(
    name    = "gaps_bcs",
    comment = "BCS gap detection output: OPEN | CLOSED | EXCLUDED per eligible member",
    table_properties = {
        "quality" : "gold",
        "delta.enableChangeDataFeed" : "true"
    }
)
@dlt.expect("valid_gap_id",     "gap_id IS NOT NULL")
@dlt.expect("valid_member_id",  "member_id IS NOT NULL")
@dlt.expect("valid_gap_status", "gap_status IN ('OPEN','CLOSED','EXCLUDED')")
def gaps_bcs():
    return spark.sql(f"""
        WITH gap_base AS (
            SELECT
                -- ── Primary Keys ─────────────────────────────────
                CONCAT(d.member_id, '_BCS_{YEAR}')          AS gap_id,
                d.member_id,
                {YEAR}                                       AS measurement_year,

                -- ── Measure Identification ────────────────────────
                'BCS'                                        AS measure_code,
                'Breast Cancer Screening'                    AS measure_name,
                'Mammography'                                AS measure_component,
                'HEDIS 2025'                                 AS measure_spec_version,

                -- ── Gap Status Determination ──────────────────────
                -- Priority: Exclusion > Closed > Open
                CASE
                    WHEN bm.member_id IS NOT NULL            THEN 'EXCLUDED'
                    WHEN h.member_id  IS NOT NULL            THEN 'EXCLUDED'
                    WHEN n.member_id  IS NOT NULL            THEN 'CLOSED'
                    ELSE                                          'OPEN'
                END                                          AS gap_status,

                -- ── Exclusion Details ─────────────────────────────
                CASE
                    WHEN bm.member_id IS NOT NULL            THEN 'Bilateral Mastectomy'
                    WHEN h.member_id  IS NOT NULL            THEN 'Hospice'
                    ELSE                                          NULL
                END                                          AS exclusion_reason,

                CASE
                    WHEN bm.member_id IS NOT NULL            THEN bm.exclusion_icd_code
                    WHEN h.member_id  IS NOT NULL            THEN 'Q5003-Q5008 / POS-34 / Z51.5'
                    ELSE                                          NULL
                END                                          AS exclusion_code,

                CASE
                    WHEN bm.member_id IS NOT NULL            THEN 'Claims/Diagnoses'
                    WHEN h.member_id  IS NOT NULL            THEN 'Claims/Diagnoses'
                    ELSE                                          NULL
                END                                          AS exclusion_source,

                -- ── Gap Description (human readable) ──────────────
                CASE
                    WHEN bm.member_id IS NOT NULL
                        THEN CONCAT('Member has bilateral mastectomy on record (',
                                    bm.exclusion_evidence, ') — excluded from BCS measure')
                    WHEN h.member_id IS NOT NULL
                        THEN CONCAT('Member received hospice care in ',
                                    {YEAR}, ' (', h.exclusion_evidence, ') — excluded from BCS')
                    WHEN n.member_id IS NOT NULL
                        THEN CONCAT('Mammogram completed on ',
                                    CAST(n.mammogram_date AS STRING),
                                    ' (', n.mammogram_source, ' · CPT: ', n.procedure_code, ')')
                    ELSE
                        CONCAT('No mammogram found in 27-month lookback window (',
                                CAST(ADD_MONTHS(TO_DATE('{END}'), -{BCS_LOOKBACK_MONTHS}) AS STRING),
                                ' to ', '{END}', ')')
                END                                          AS gap_description,

                -- ── Recommended Action ────────────────────────────
                CASE
                    WHEN bm.member_id IS NOT NULL            THEN NULL
                    WHEN h.member_id  IS NOT NULL            THEN NULL
                    WHEN n.member_id  IS NOT NULL            THEN NULL
                    ELSE 'Schedule mammogram screening — CPT 77067 or G0202 within 27-month window'
                END                                          AS recommended_action,

                -- ── Denominator / Exclusion / Numerator Flags ─────
                CASE WHEN bm.member_id IS NULL AND h.member_id IS NULL
                     THEN TRUE ELSE FALSE END                AS in_denominator,

                CASE WHEN bm.member_id IS NOT NULL OR h.member_id IS NOT NULL
                     THEN TRUE ELSE FALSE END                AS is_excluded,

                CASE WHEN n.member_id IS NOT NULL
                     THEN TRUE ELSE FALSE END                AS numerator_met,

                -- ── Numerator Evidence ────────────────────────────
                n.procedure_code                             AS numerator_evidence_code,
                n.mammogram_source                           AS numerator_evidence_type,
                n.mammogram_date                             AS numerator_evidence_date,
                n.facility_name                              AS numerator_facility,
                n.rendering_provider_name                    AS numerator_provider,
                n.place_of_service_description               AS numerator_pos,
                CASE WHEN n.member_id IS NOT NULL
                     THEN 'Claims' ELSE NULL END             AS numerator_source,

                -- ── Dates ─────────────────────────────────────────
                CURRENT_DATE()                               AS detected_date,
                TO_DATE('{END}')                             AS due_date,
                DATEDIFF(TO_DATE('{END}'), CURRENT_DATE())   AS days_remaining,

                CASE WHEN n.member_id IS NOT NULL
                     THEN n.mammogram_date ELSE NULL END     AS closed_date,

                -- ── Lookback Window ───────────────────────────────
                ADD_MONTHS(TO_DATE('{END}'), -{BCS_LOOKBACK_MONTHS}) AS lookback_start_date,
                TO_DATE('{END}')                             AS lookback_end_date,
                {BCS_LOOKBACK_MONTHS}                        AS lookback_months,

                -- ── Denominator Criteria (JSON for audit) ─────────
                CONCAT(
                    '{{"gender":"', d.gender,
                    '","age":', CAST(d.age AS STRING),
                    ',"product_line":"', d.product_line,
                    '","enrolled":', CAST(d.continuous_enrollment_my2025 AS STRING),
                    ',"has_medical_benefit":true}}'
                )                                            AS denominator_criteria,

                -- ── Provider Attribution ──────────────────────────
                d.assigned_pcp_npi                           AS attributed_pcp_npi,
                d.assigned_pcp_name                          AS attributed_pcp_name,
                d.assigned_pcp_id                            AS attributed_pcp_id,

                -- ── Member Demographics (for outreach) ────────────
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

                -- ── Insurance Info ────────────────────────────────
                d.product_line,
                d.plan_type,
                d.medicare_flag,
                d.snp_type,

                -- ── Risk and SDoH ─────────────────────────────────
                d.risk_score,
                d.risk_category,
                d.sdoh_barriers,
                d.area_deprivation_index,

                -- ── Outreach Tracking (initialized) ──────────────
                0                                            AS outreach_attempts,
                CAST(NULL AS DATE)                           AS last_outreach_date,
                CAST(NULL AS STRING)                         AS last_outreach_channel,
                CAST(NULL AS DATE)                           AS next_outreach_date,
                CAST(NULL AS STRING)                         AS next_outreach_channel,
                CAST(NULL AS STRING)                         AS outreach_outcome,

                -- ── Gen AI Fields (populated downstream) ─────────
                CAST(NULL AS STRING)                         AS ai_patient_summary,
                CAST(NULL AS STRING)                         AS ai_outreach_script,
                CAST(NULL AS STRING)                         AS ai_risk_explanation,
                CAST(NULL AS TIMESTAMP)                      AS ai_generated_date,

                -- ── Audit ─────────────────────────────────────────
                '{RUN_ID}'                                   AS pipeline_run_id,
                CURRENT_TIMESTAMP()                          AS created_date,
                CURRENT_TIMESTAMP()                          AS updated_date,
                'DLT_PIPELINE_BCS'                           AS data_source

            FROM dlt.denom_bcs d

            -- Left join exclusion: bilateral mastectomy
            LEFT JOIN dlt.excl_bilateral_mastectomy bm
                ON d.member_id = bm.member_id

            -- Left join exclusion: hospice
            LEFT JOIN dlt.excl_hospice_bcs h
                ON d.member_id = h.member_id

            -- Left join numerator: mammogram evidence
            LEFT JOIN dlt.numer_bcs n
                ON d.member_id = n.member_id
        )

        -- ── Priority Scoring ──────────────────────────────────────
        -- Applied after gap logic so score = 0 for EXCLUDED/CLOSED
        SELECT
            gap_id,
            member_id,
            measurement_year,
            measure_code,
            measure_name,
            measure_component,
            measure_spec_version,
            gap_status,
            exclusion_reason,
            exclusion_code,
            exclusion_source,
            gap_description,
            recommended_action,
            in_denominator,
            is_excluded,
            numerator_met,
            numerator_evidence_code,
            numerator_evidence_type,
            numerator_evidence_date,
            numerator_facility,
            numerator_provider,
            numerator_pos,
            numerator_source,
            detected_date,
            due_date,
            days_remaining,
            closed_date,
            lookback_start_date,
            lookback_end_date,
            lookback_months,
            denominator_criteria,
            attributed_pcp_npi,
            attributed_pcp_name,
            attributed_pcp_id,
            first_name,
            last_name,
            date_of_birth,
            age,
            phone_primary,
            phone_secondary,
            email,
            preferred_name,
            preferred_language,
            communication_preference,
            address_line1,
            city,
            state,
            zip_code,
            product_line,
            plan_type,
            medicare_flag,
            snp_type,
            risk_score,
            risk_category,
            sdoh_barriers,
            area_deprivation_index,
            outreach_attempts,
            last_outreach_date,
            last_outreach_channel,
            next_outreach_date,
            next_outreach_channel,
            outreach_outcome,
            ai_patient_summary,
            ai_outreach_script,
            ai_risk_explanation,
            ai_generated_date,
            pipeline_run_id,
            created_date,
            updated_date,
            data_source,

            -- ── Priority Score (0 for non-OPEN gaps) ─────────────
            CASE
                WHEN gap_status != 'OPEN' THEN 0.0
                ELSE LEAST(10.0, ROUND(
                    -- Base score for BCS measure
                    7.0
                    -- Urgency boost based on days remaining
                    + CASE
                        WHEN days_remaining < 60  THEN 2.0
                        WHEN days_remaining < 90  THEN 1.5
                        WHEN days_remaining < 120 THEN 1.0
                        ELSE 0.0
                      END
                    -- Risk score boost
                    + CASE
                        WHEN risk_score > 80 THEN 1.0
                        WHEN risk_score > 60 THEN 0.5
                        ELSE 0.0
                      END
                    -- SDoH barrier boost (social barriers = harder to close gap)
                    + CASE
                        WHEN area_deprivation_index > 70 THEN 0.5
                        ELSE 0.0
                      END
                , 2))
            END                                            AS priority_score,

            -- ── Priority Tier ─────────────────────────────────────
            CASE
                WHEN gap_status != 'OPEN'    THEN NULL
                WHEN LEAST(10.0, ROUND(
                    7.0
                    + CASE WHEN days_remaining < 60 THEN 2.0
                           WHEN days_remaining < 90 THEN 1.5
                           WHEN days_remaining < 120 THEN 1.0 ELSE 0.0 END
                    + CASE WHEN risk_score > 80 THEN 1.0
                           WHEN risk_score > 60 THEN 0.5 ELSE 0.0 END
                    + CASE WHEN area_deprivation_index > 70 THEN 0.5 ELSE 0.0 END
                , 2)) >= 9.0 THEN 'Critical'
                WHEN LEAST(10.0, ROUND(
                    7.0
                    + CASE WHEN days_remaining < 60 THEN 2.0
                           WHEN days_remaining < 90 THEN 1.5
                           WHEN days_remaining < 120 THEN 1.0 ELSE 0.0 END
                    + CASE WHEN risk_score > 80 THEN 1.0
                           WHEN risk_score > 60 THEN 0.5 ELSE 0.0 END
                    + CASE WHEN area_deprivation_index > 70 THEN 0.5 ELSE 0.0 END
                , 2)) >= 7.0 THEN 'High'
                WHEN LEAST(10.0, ROUND(
                    7.0
                    + CASE WHEN days_remaining < 60 THEN 2.0
                           WHEN days_remaining < 90 THEN 1.5
                           WHEN days_remaining < 120 THEN 1.0 ELSE 0.0 END
                    + CASE WHEN risk_score > 80 THEN 1.0
                           WHEN risk_score > 60 THEN 0.5 ELSE 0.0 END
                    + CASE WHEN area_deprivation_index > 70 THEN 0.5 ELSE 0.0 END
                , 2)) >= 5.0 THEN 'Medium'
                ELSE 'Low'
            END                                            AS priority_tier

        FROM gap_base
    """)


# ================================================================
# SECTION 6: FINAL PERSISTED GOLD TABLE — care_gaps_bcs
# ================================================================

# ────────────────────────────────────────────────────────────────
# This is the FINAL table stored in ncqa.gold
# It is the source of truth for:
#   - Care coordinator dashboards
#   - Outreach workflow triggers
#   - HEDIS rate calculations
#   - Gen AI summary generation
#   - Compliance reporting
# ────────────────────────────────────────────────────────────────
@dlt.table(
    name    = "care_gaps_bcs",
    comment = "FINAL BCS gap table stored in gold layer — all members, all statuses, measurement year 2025",
    table_properties = {
        "quality"                          : "gold",
        "delta.enableChangeDataFeed"       : "true",
        "delta.autoOptimize.optimizeWrite" : "true",
        "delta.autoOptimize.autoCompact"   : "true",
        "pipelines.autoOptimize.zOrderCols": "gap_status,priority_tier,attributed_pcp_npi"
    }
)
@dlt.expect("valid_gap_id",     "gap_id IS NOT NULL")
@dlt.expect("valid_member",     "member_id IS NOT NULL")
@dlt.expect("valid_status",     "gap_status IN ('OPEN','CLOSED','EXCLUDED')")
@dlt.expect("valid_measure",    "measure_code = 'BCS'")
@dlt.expect("valid_year",       f"measurement_year = {YEAR}")
def care_gaps_bcs():
    # Read from the gaps_bcs DLT table
    return dlt.read("gaps_bcs")


# ================================================================
# SECTION 7: MASTER CARE_GAPS TABLE (append BCS to all measures)
# ================================================================

# ────────────────────────────────────────────────────────────────
# This master table will hold ALL measures (BCS + COL + CDC + CBP + CCS)
# Each measure pipeline appends its rows here
# For now it contains BCS only — other measures will UNION ALL when added
# ────────────────────────────────────────────────────────────────
@dlt.table(
    name    = "care_gaps",
    comment = "Master HEDIS gap table — all measures. Currently: BCS. Add COL/CDC/CBP/CCS via UNION ALL",
    table_properties = {
        "quality"                          : "gold",
        "delta.enableChangeDataFeed"       : "true",
        "delta.autoOptimize.optimizeWrite" : "true",
        "delta.autoOptimize.autoCompact"   : "true",
        "pipelines.autoOptimize.zOrderCols": "gap_status,measure_code,priority_tier"
    }
)
@dlt.expect("valid_gap_id",  "gap_id IS NOT NULL")
@dlt.expect("valid_member",  "member_id IS NOT NULL")
@dlt.expect("valid_status",  "gap_status IN ('OPEN','CLOSED','EXCLUDED')")
def care_gaps():
    # Currently BCS only
    # When COL/CDC/CBP/CCS pipelines are added, replace with:
    # return dlt.read("gaps_bcs").unionAll(dlt.read("gaps_col")).unionAll(...)
    return dlt.read("gaps_bcs")


# ================================================================
# SECTION 8: VERIFICATION QUERIES
# ================================================================
# Run these in a separate Databricks SQL notebook AFTER pipeline runs
# They do NOT execute as part of the DLT pipeline
# ================================================================

"""
-- ── QUERY 1: Overall BCS gap summary ─────────────────────────────
SELECT
    gap_status,
    COUNT(*)                                              AS members,
    COUNT(CASE WHEN priority_tier = 'Critical' THEN 1 END) AS critical,
    COUNT(CASE WHEN priority_tier = 'High'     THEN 1 END) AS high,
    COUNT(CASE WHEN priority_tier = 'Medium'   THEN 1 END) AS medium,
    COUNT(CASE WHEN priority_tier = 'Low'      THEN 1 END) AS low_priority
FROM ncqa.gold.care_gaps_bcs
GROUP BY gap_status
ORDER BY gap_status;

-- Expected from your test data:
-- CLOSED   : 3 members (M003, M005, M040)
-- EXCLUDED : 2 members (M004 bilateral mastectomy, M006 hospice)
-- OPEN     : 7 members (M001, M002, M007, M015, M037, M041, M042)


-- ── QUERY 2: BCS compliance rate (HEDIS rate) ────────────────────
SELECT
    'BCS' AS measure_code,
    COUNT(CASE WHEN in_denominator = TRUE AND is_excluded = FALSE THEN 1 END) AS eligible_denominator,
    COUNT(CASE WHEN numerator_met  = TRUE THEN 1 END)                         AS numerator,
    COUNT(CASE WHEN gap_status     = 'OPEN'  THEN 1 END)                      AS open_gaps,
    COUNT(CASE WHEN is_excluded    = TRUE THEN 1 END)                         AS excluded,
    ROUND(
        COUNT(CASE WHEN numerator_met = TRUE THEN 1 END) * 100.0
        / NULLIF(COUNT(CASE WHEN in_denominator = TRUE AND is_excluded = FALSE THEN 1 END), 0)
    , 1)                                                                       AS compliance_rate_pct
FROM ncqa.gold.care_gaps_bcs;

-- Expected: eligible=10, numerator=3, open=7, excluded=2, rate=30.0%


-- ── QUERY 3: Open gaps for care coordinator outreach ─────────────
SELECT
    member_id,
    CONCAT(first_name, ' ', last_name) AS member_name,
    age,
    phone_primary,
    preferred_language,
    communication_preference,
    gap_description,
    days_remaining,
    priority_tier,
    priority_score,
    attributed_pcp_name,
    risk_category,
    sdoh_barriers
FROM ncqa.gold.care_gaps_bcs
WHERE gap_status    = 'OPEN'
ORDER BY priority_score DESC, days_remaining ASC;


-- ── QUERY 4: Exclusion audit ──────────────────────────────────────
SELECT
    member_id,
    CONCAT(first_name, ' ', last_name) AS member_name,
    exclusion_reason,
    exclusion_code,
    gap_description
FROM ncqa.gold.care_gaps_bcs
WHERE gap_status = 'EXCLUDED'
ORDER BY exclusion_reason;

-- Expected:
-- M004 → Bilateral Mastectomy → Z90.13
-- M006 → Hospice             → Q5003-Q5008 / POS-34 / Z51.5


-- ── QUERY 5: Closed gap audit — verify mammogram evidence ─────────
SELECT
    member_id,
    CONCAT(first_name, ' ', last_name) AS member_name,
    numerator_evidence_code    AS mammogram_cpt,
    numerator_evidence_type    AS mammogram_type,
    numerator_evidence_date    AS mammogram_date,
    numerator_facility,
    numerator_provider,
    gap_description
FROM ncqa.gold.care_gaps_bcs
WHERE gap_status = 'CLOSED'
ORDER BY numerator_evidence_date;

-- Expected:
-- M003 → 77067 → 2024-11-15 → Northwest Community Hospital
-- M005 → 77067 → 2025-06-20 → Rush University Medical
-- M040 → 77067 → 2025-02-14 → Northbrook Imaging


-- ── QUERY 6: PCP-level gap summary ───────────────────────────────
SELECT
    attributed_pcp_npi,
    attributed_pcp_name,
    COUNT(*)                                          AS total_bcs_patients,
    COUNT(CASE WHEN gap_status = 'OPEN'     THEN 1 END) AS open_gaps,
    COUNT(CASE WHEN gap_status = 'CLOSED'   THEN 1 END) AS closed_gaps,
    COUNT(CASE WHEN gap_status = 'EXCLUDED' THEN 1 END) AS excluded,
    ROUND(
        COUNT(CASE WHEN gap_status = 'CLOSED' THEN 1 END) * 100.0
        / NULLIF(COUNT(CASE WHEN gap_status IN ('OPEN','CLOSED') THEN 1 END), 0)
    , 1) AS pcp_compliance_rate_pct
FROM ncqa.gold.care_gaps_bcs
GROUP BY attributed_pcp_npi, attributed_pcp_name
ORDER BY open_gaps DESC;


-- ── QUERY 7: Validate M007 (unilateral — should NOT be excluded) ──
SELECT
    member_id, gap_status, exclusion_reason, gap_description
FROM ncqa.gold.care_gaps_bcs
WHERE member_id = 'M007';
-- Expected: gap_status = OPEN (NOT excluded — only left mastectomy, not bilateral)


-- ── QUERY 8: Validate M004 (bilateral — should be excluded) ──────
SELECT
    member_id, gap_status, exclusion_reason, exclusion_code
FROM ncqa.gold.care_gaps_bcs
WHERE member_id = 'M004';
-- Expected: gap_status = EXCLUDED, exclusion_reason = Bilateral Mastectomy


-- ── QUERY 9: Full DLT pipeline table lineage ─────────────────────
SELECT * FROM event_log('ncqa.gold.care_gaps_bcs')
WHERE event_type = 'flow_progress'
ORDER BY timestamp DESC
LIMIT 20;
"""
