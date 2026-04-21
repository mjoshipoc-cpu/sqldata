-- ================================================================
-- NCQA HEDIS REFERENCE VALUE SETS
-- Complete Script: CREATE TABLE + INSERT ALL DATA
-- Measures  : BCS | COL-E | CDC | CBP | CCS
-- Platform  : Databricks Delta Lake
-- Version   : 2025.1 — NCQA HEDIS 2025 Specifications
-- ================================================================
-- HOW TO RUN IN DATABRICKS:
--   1. Open a SQL Editor or Notebook (SQL language)
--   2. Set your catalog: USE CATALOG ncqa;
--   3. Run this entire script top to bottom
--   4. Verify: SELECT COUNT(*) FROM reference.hedis_value_sets;
--      Expected: 224+ rows
-- ================================================================

-- ────────────────────────────────────────────────────────────────
-- SECTION 0: SCHEMA SETUP
-- ────────────────────────────────────────────────────────────────

CREATE CATALOG IF NOT EXISTS ncqa;
USE CATALOG ncqa;

CREATE SCHEMA IF NOT EXISTS reference;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- ────────────────────────────────────────────────────────────────
-- SECTION 1: CREATE TABLE
-- ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS reference.hedis_value_sets (
    value_set_id        BIGINT        GENERATED ALWAYS AS IDENTITY,
    measure_code        STRING        NOT NULL,
    -- BCS  = Breast Cancer Screening
    -- COL  = Colorectal Cancer Screening
    -- CDC  = Comprehensive Diabetes Care
    -- CBP  = Controlling Blood Pressure
    -- CCS  = Cervical Cancer Screening

    measure_component   STRING        NOT NULL,
    -- Denominator = who qualifies for the measure
    -- Numerator   = evidence that care was received
    -- Exclusion   = who should be removed from denominator

    code_system         STRING        NOT NULL,
    -- CPT      = Current Procedural Terminology
    -- HCPCS    = Healthcare Common Procedure Coding System
    -- ICD10CM  = ICD-10 Clinical Modification (diagnosis)
    -- LOINC    = Logical Observation Identifiers Names and Codes (labs)
    -- UBREV    = UB-04 Revenue Code (facility claims)

    code                STRING        NOT NULL,
    code_description    STRING,
    lookback_months     INT,
    -- NULL = historical (any time in patient history)
    -- 12   = current measurement year only
    -- 27   = 27 months back (BCS mammogram window)
    -- 36   = 3 years back
    -- 60   = 5 years back
    -- 120  = 10 years back (colonoscopy)

    effective_year      INT           DEFAULT 2025,
    is_active           BOOLEAN       DEFAULT TRUE,
    notes               STRING,
    created_date        TIMESTAMP     DEFAULT CURRENT_TIMESTAMP(),
    data_source         STRING        DEFAULT 'NCQA_HEDIS_2025'
)
USING DELTA
COMMENT 'NCQA HEDIS 2025 value sets — CPT, HCPCS, ICD-10, LOINC codes for all 5 measures';

-- Add table properties for performance
ALTER TABLE reference.hedis_value_sets
SET TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact'   = 'true'
);

-- ────────────────────────────────────────────────────────────────
-- SECTION 2: CLEAR EXISTING DATA (safe re-run)
-- ────────────────────────────────────────────────────────────────

DELETE FROM reference.hedis_value_sets WHERE effective_year = 2025;

-- ================================================================
-- SECTION 3: BCS — BREAST CANCER SCREENING
-- Denominator : Female, age 52-74, enrolled, Commercial/Medicare
-- Numerator   : Mammogram within 27-month lookback window
-- Exclusions  : Bilateral mastectomy (any history), hospice
-- ================================================================

INSERT INTO reference.hedis_value_sets
    (measure_code, measure_component, code_system, code, code_description, lookback_months, notes)
VALUES

-- ── BCS NUMERATOR: Mammogram CPT codes ──────────────────────────
('BCS','Numerator','CPT','77065',
 'Diagnostic mammography, unilateral including computer-aided detection',
 27, 'Diagnostic mammogram — counts for BCS numerator'),

('BCS','Numerator','CPT','77066',
 'Diagnostic mammography, bilateral including computer-aided detection',
 27, 'Diagnostic bilateral mammogram'),

('BCS','Numerator','CPT','77067',
 'Screening mammography, bilateral including computer-aided detection',
 27, 'Primary BCS numerator code — most common screening mammogram'),

-- ── BCS NUMERATOR: Mammogram HCPCS codes (Medicare) ─────────────
('BCS','Numerator','HCPCS','G0202',
 'Screening mammography, bilateral, 2D',
 27, 'Medicare screening mammogram — 2D'),

('BCS','Numerator','HCPCS','G0204',
 'Diagnostic mammography, bilateral including computer-aided detection',
 27, 'Medicare diagnostic bilateral mammogram'),

('BCS','Numerator','HCPCS','G0206',
 'Diagnostic mammography, unilateral including computer-aided detection',
 27, 'Medicare diagnostic unilateral mammogram'),

-- ── BCS NUMERATOR: Revenue Code (hospital/facility claims) ───────
('BCS','Numerator','UBREV','0401',
 'Mammography — UB-04 facility revenue code',
 27, 'Used on facility/hospital claims when CPT not present'),

-- ── BCS EXCLUSION: Bilateral breast absence ICD-10 ───────────────
('BCS','Exclusion','ICD10CM','Z90.13',
 'Acquired absence of bilateral breasts and nipples',
 NULL, 'PRIMARY bilateral exclusion — historical, any date'),

('BCS','Exclusion','ICD10CM','Z90.11',
 'Acquired absence of right breast and nipple',
 NULL, 'Unilateral right — if combined with Z90.12 = bilateral exclusion'),

('BCS','Exclusion','ICD10CM','Z90.12',
 'Acquired absence of left breast and nipple',
 NULL, 'Unilateral left — if combined with Z90.11 = bilateral exclusion'),

-- ── BCS EXCLUSION: Mastectomy CPT codes ─────────────────────────
('BCS','Exclusion','CPT','19180',
 'Mastectomy, simple, complete',
 NULL, 'Simple mastectomy — check laterality/modifier for bilateral'),

('BCS','Exclusion','CPT','19200',
 'Mastectomy, radical, including pectoral muscles, axillary lymph nodes',
 NULL, 'Radical mastectomy'),

('BCS','Exclusion','CPT','19220',
 'Mastectomy, radical, including pectoral muscles, axillary and internal mammary lymph nodes',
 NULL, 'Extended radical mastectomy'),

('BCS','Exclusion','CPT','19240',
 'Mastectomy, modified radical, including axillary lymph nodes, with or without pectoralis minor',
 NULL, 'Modified radical mastectomy'),

('BCS','Exclusion','CPT','19303',
 'Mastectomy, simple, complete (current code)',
 NULL, 'Current simple mastectomy code — supersedes 19180'),

('BCS','Exclusion','CPT','19304',
 'Mastectomy, subcutaneous',
 NULL, 'Subcutaneous mastectomy'),

('BCS','Exclusion','CPT','19305',
 'Mastectomy, radical, including pectoral muscles, axillary lymph nodes (current)',
 NULL, 'Current radical mastectomy code'),

('BCS','Exclusion','CPT','19306',
 'Mastectomy, radical, including pectoral muscles, axillary and internal mammary lymph nodes (current)',
 NULL, 'Current extended radical mastectomy code'),

('BCS','Exclusion','CPT','19307',
 'Mastectomy, modified radical (current code)',
 NULL, 'Current modified radical mastectomy — most common exclusion CPT'),

-- ── BCS EXCLUSION: Hospice HCPCS codes ──────────────────────────
('BCS','Exclusion','HCPCS','Q5003',
 'Hospice care, nursing facility',
 NULL, 'Hospice exclusion — any occurrence in measurement year'),

('BCS','Exclusion','HCPCS','Q5004',
 'Hospice care, custodial facility',
 NULL, 'Hospice exclusion'),

('BCS','Exclusion','HCPCS','Q5005',
 'Hospice care, inpatient hospital',
 NULL, 'Hospice exclusion'),

('BCS','Exclusion','HCPCS','Q5006',
 'Hospice care, inpatient hospital (short-term respite)',
 NULL, 'Hospice exclusion'),

('BCS','Exclusion','HCPCS','Q5007',
 'Hospice care, long-term care facility',
 NULL, 'Hospice exclusion'),

('BCS','Exclusion','HCPCS','Q5008',
 'Hospice care, at home',
 NULL, 'Hospice exclusion'),

('BCS','Exclusion','HCPCS','S9126',
 'Hospice care, at home, per diem',
 NULL, 'Hospice exclusion — some payers use S codes'),

-- ── BCS EXCLUSION: Hospice ICD-10 ───────────────────────────────
('BCS','Exclusion','ICD10CM','Z51.5',
 'Encounter for palliative care',
 NULL, 'Palliative/hospice diagnosis code');

-- ================================================================
-- SECTION 4: COL-E — COLORECTAL CANCER SCREENING
-- Denominator : Age 45-75, enrolled, all product lines
-- Numerator   : Any qualifying screening (5 test types, varying lookbacks)
-- Exclusions  : Prior colorectal cancer (any history), total colectomy, hospice
-- ================================================================

INSERT INTO reference.hedis_value_sets
    (measure_code, measure_component, code_system, code, code_description, lookback_months, notes)
VALUES

-- ── COL NUMERATOR: Colonoscopy (10-year lookback = 120 months) ──
('COL','Numerator','CPT','45378','Colonoscopy, diagnostic',120,'Standard diagnostic colonoscopy'),
('COL','Numerator','CPT','45379','Colonoscopy, with removal of foreign body',120,NULL),
('COL','Numerator','CPT','45380','Colonoscopy, with biopsy, single or multiple',120,NULL),
('COL','Numerator','CPT','45381','Colonoscopy, with directed submucosal injection',120,NULL),
('COL','Numerator','CPT','45382','Colonoscopy, with control of bleeding',120,NULL),
('COL','Numerator','CPT','45383','Colonoscopy, with ablation of tumor, polyp, or other lesion',120,NULL),
('COL','Numerator','CPT','45384','Colonoscopy, with removal of tumor by hot biopsy forceps',120,NULL),
('COL','Numerator','CPT','45385','Colonoscopy, with removal of tumor by snare technique',120,'Very common — polypectomy colonoscopy'),
('COL','Numerator','CPT','45386','Colonoscopy, with dilation of stricture',120,NULL),
('COL','Numerator','CPT','45387','Colonoscopy, with transendoscopic stent placement',120,NULL),
('COL','Numerator','CPT','45388','Colonoscopy, with ablation of lesion',120,NULL),
('COL','Numerator','CPT','45389','Colonoscopy, with endoscopic stent placement',120,NULL),
('COL','Numerator','CPT','45390','Colonoscopy, with endoscopic mucosal resection',120,NULL),
('COL','Numerator','CPT','45391','Colonoscopy, with endoscopic ultrasound examination',120,NULL),
('COL','Numerator','CPT','45392','Colonoscopy, with transendoscopic ultrasound guided aspiration',120,NULL),
('COL','Numerator','CPT','45393','Colonoscopy, with balloon dilation',120,NULL),
('COL','Numerator','HCPCS','G0105','Colorectal cancer screening; colonoscopy on individual at high risk',120,'Medicare high-risk colonoscopy'),
('COL','Numerator','HCPCS','G0121','Colorectal cancer screening; colonoscopy on individual not meeting high risk criteria',120,'Medicare standard colonoscopy'),

-- ── COL NUMERATOR: Flexible Sigmoidoscopy (5-year lookback = 60 months) ──
('COL','Numerator','CPT','45330','Sigmoidoscopy, flexible; diagnostic',60,'Flex sigmoidoscopy — 5yr lookback'),
('COL','Numerator','CPT','45331','Sigmoidoscopy, flexible; with biopsy',60,NULL),
('COL','Numerator','CPT','45332','Sigmoidoscopy, flexible; with removal of foreign body',60,NULL),
('COL','Numerator','CPT','45333','Sigmoidoscopy, flexible; with removal of tumor by hot biopsy',60,NULL),
('COL','Numerator','CPT','45334','Sigmoidoscopy, flexible; with control of bleeding',60,NULL),
('COL','Numerator','CPT','45335','Sigmoidoscopy, flexible; with directed submucosal injection',60,NULL),
('COL','Numerator','CPT','45337','Sigmoidoscopy, flexible; with decompression',60,NULL),
('COL','Numerator','CPT','45338','Sigmoidoscopy, flexible; with ablation of tumor',60,NULL),
('COL','Numerator','CPT','45339','Sigmoidoscopy, flexible; with ablation of lesion',60,NULL),
('COL','Numerator','CPT','45340','Sigmoidoscopy, flexible; with dilation of stricture',60,NULL),
('COL','Numerator','CPT','45341','Sigmoidoscopy, flexible; with endoscopic ultrasound',60,NULL),
('COL','Numerator','CPT','45342','Sigmoidoscopy, flexible; with transendoscopic ultrasound guided aspiration',60,NULL),
('COL','Numerator','CPT','45345','Sigmoidoscopy, flexible; with transendoscopic stent placement',60,NULL),
('COL','Numerator','CPT','45346','Sigmoidoscopy, flexible; with ablation of lesion (new)',60,NULL),
('COL','Numerator','CPT','45347','Sigmoidoscopy, flexible; with placement of endoscopic stent',60,NULL),
('COL','Numerator','CPT','45349','Sigmoidoscopy, flexible; with endoscopic mucosal resection',60,NULL),
('COL','Numerator','CPT','45350','Sigmoidoscopy, flexible; with band ligation',60,NULL),

-- ── COL NUMERATOR: FIT Test (annual = 12 months) ────────────────
('COL','Numerator','CPT','82270',
 'Occult blood, feces; immunoassay',
 12, 'FIT/FOBT test — must be done in CURRENT measurement year'),

('COL','Numerator','CPT','82274',
 'Blood, occult, by fecal hemoglobin determination by immunoassay, qualitative',
 12, 'FIT test — quantitative immunoassay version'),

-- ── COL NUMERATOR: FIT-DNA / Cologuard (3-year = 36 months) ─────
('COL','Numerator','CPT','81528',
 'Oncology, colorectal, quantitative real-time target and signal amplification of 10 DNA markers in fecal homogenate',
 36, 'Cologuard / FIT-DNA test — 3yr lookback per NCQA'),

-- ── COL NUMERATOR: CT Colonography (5-year = 60 months) ─────────
('COL','Numerator','CPT','74263',
 'Computed tomographic colonography, screening, including image postprocessing',
 60, 'Virtual colonoscopy — 5yr lookback'),

-- ── COL EXCLUSION: Prior colorectal cancer ICD-10 ───────────────
('COL','Exclusion','ICD10CM','C18.0','Malignant neoplasm of cecum',NULL,'Colorectal cancer — COL exclusion (historical)'),
('COL','Exclusion','ICD10CM','C18.1','Malignant neoplasm of appendix',NULL,NULL),
('COL','Exclusion','ICD10CM','C18.2','Malignant neoplasm of ascending colon',NULL,NULL),
('COL','Exclusion','ICD10CM','C18.3','Malignant neoplasm of hepatic flexure',NULL,NULL),
('COL','Exclusion','ICD10CM','C18.4','Malignant neoplasm of transverse colon',NULL,NULL),
('COL','Exclusion','ICD10CM','C18.5','Malignant neoplasm of splenic flexure',NULL,NULL),
('COL','Exclusion','ICD10CM','C18.6','Malignant neoplasm of descending colon',NULL,NULL),
('COL','Exclusion','ICD10CM','C18.7','Malignant neoplasm of sigmoid colon',NULL,NULL),
('COL','Exclusion','ICD10CM','C18.8','Overlapping malignant neoplasm of colon',NULL,NULL),
('COL','Exclusion','ICD10CM','C18.9','Malignant neoplasm of colon, unspecified',NULL,NULL),
('COL','Exclusion','ICD10CM','C19','Malignant neoplasm of rectosigmoid junction',NULL,NULL),
('COL','Exclusion','ICD10CM','C20','Malignant neoplasm of rectum',NULL,NULL),
('COL','Exclusion','ICD10CM','C26.0','Malignant neoplasm of intestinal tract, unspecified',NULL,NULL),

-- ── COL EXCLUSION: Total colectomy ICD-10 ───────────────────────
('COL','Exclusion','ICD10CM','Z90.49',
 'Acquired absence of other specified parts of digestive tract',
 NULL, 'Total colectomy status — historical'),

-- ── COL EXCLUSION: Total colectomy CPT ──────────────────────────
('COL','Exclusion','CPT','44150','Colectomy, total, abdominal, without proctectomy',NULL,NULL),
('COL','Exclusion','CPT','44151','Colectomy, total, abdominal, with ileostomy',NULL,NULL),
('COL','Exclusion','CPT','44155','Colectomy, total, abdominal with proctectomy, with ileostomy',NULL,NULL),
('COL','Exclusion','CPT','44156','Colectomy, total, abdominal with proctectomy, with continent ileostomy',NULL,NULL),
('COL','Exclusion','CPT','44157','Colectomy, total, abdominal with proctectomy, with ileoanal anastomosis',NULL,NULL),
('COL','Exclusion','CPT','44158','Colectomy, total, with proctectomy, with ileoanal anastomosis and loop ileostomy',NULL,NULL),
('COL','Exclusion','CPT','44210','Laparoscopy, colectomy, total, abdominal, without proctectomy',NULL,'Laparoscopic total colectomy'),
('COL','Exclusion','CPT','44211','Laparoscopy, colectomy, total, with proctectomy, with ileoanal anastomosis',NULL,NULL),
('COL','Exclusion','CPT','44212','Laparoscopy, colectomy, total, abdominal, with proctectomy, with ileostomy',NULL,NULL),

-- ── COL EXCLUSION: Hospice (same codes as BCS) ───────────────────
('COL','Exclusion','HCPCS','Q5003','Hospice care, nursing facility',NULL,'Hospice exclusion — measurement year'),
('COL','Exclusion','HCPCS','Q5004','Hospice care, custodial facility',NULL,NULL),
('COL','Exclusion','HCPCS','Q5005','Hospice care, inpatient hospital',NULL,NULL),
('COL','Exclusion','ICD10CM','Z51.5','Encounter for palliative care',NULL,NULL);

-- ================================================================
-- SECTION 5: CDC — COMPREHENSIVE DIABETES CARE
-- Denominator : Diabetes dx (E10/E11/E13), age 18-75, enrolled
-- Numerator   : 4 sub-measures — HbA1c, LDL, Eye Exam, Nephropathy
-- Exclusions  : Gestational diabetes, polycystic ovarian syndrome,
--               frailty (age 66+), hospice
-- ================================================================

INSERT INTO reference.hedis_value_sets
    (measure_code, measure_component, code_system, code, code_description, lookback_months, notes)
VALUES

-- ── CDC DENOMINATOR: Diabetes ICD-10 codes ──────────────────────
('CDC','Denominator','ICD10CM','E10',
 'Type 1 diabetes mellitus',
 12, 'Type 1 diabetes parent code — includes all E10.x subcodes'),

('CDC','Denominator','ICD10CM','E10.9',
 'Type 1 diabetes mellitus without complications',
 12, 'Most common Type 1 code'),

('CDC','Denominator','ICD10CM','E10.10',
 'Type 1 diabetes mellitus with diabetic ketoacidosis without coma',
 12, NULL),

('CDC','Denominator','ICD10CM','E10.40',
 'Type 1 diabetes mellitus with diabetic neuropathy, unspecified',
 12, NULL),

('CDC','Denominator','ICD10CM','E10.65',
 'Type 1 diabetes mellitus with hyperglycemia',
 12, NULL),

('CDC','Denominator','ICD10CM','E11',
 'Type 2 diabetes mellitus',
 12, 'Type 2 diabetes parent code — includes all E11.x subcodes'),

('CDC','Denominator','ICD10CM','E11.9',
 'Type 2 diabetes mellitus without complications',
 12, 'MOST COMMON diabetes code — primary denominator trigger'),

('CDC','Denominator','ICD10CM','E11.21',
 'Type 2 diabetes mellitus with diabetic nephropathy',
 12, NULL),

('CDC','Denominator','ICD10CM','E11.40',
 'Type 2 diabetes mellitus with diabetic neuropathy, unspecified',
 12, NULL),

('CDC','Denominator','ICD10CM','E11.51',
 'Type 2 diabetes mellitus with diabetic peripheral angiopathy without gangrene',
 12, NULL),

('CDC','Denominator','ICD10CM','E11.65',
 'Type 2 diabetes mellitus with hyperglycemia',
 12, 'Common secondary code'),

('CDC','Denominator','ICD10CM','E13',
 'Other specified diabetes mellitus',
 12, 'Other diabetes parent — secondary steroid-induced, etc.'),

('CDC','Denominator','ICD10CM','E13.9',
 'Other specified diabetes mellitus without complications',
 12, NULL),

-- ── CDC NUMERATOR: HbA1c Testing LOINC codes ────────────────────
('CDC','Numerator','LOINC','4548-4',
 'Hemoglobin A1c/Hemoglobin.total in Blood',
 12, 'PRIMARY HbA1c LOINC — most labs use this'),

('CDC','Numerator','LOINC','17856-6',
 'Hemoglobin A1c/Hemoglobin.total in Blood by IFCC standardized method',
 12, 'IFCC-standardized HbA1c'),

('CDC','Numerator','LOINC','59261-8',
 'Hemoglobin A1c/Hemoglobin.total in Blood by IFCC protocol',
 12, NULL),

('CDC','Numerator','LOINC','41995-2',
 'Hemoglobin A1c [Mass/volume] in Blood',
 12, NULL),

('CDC','Numerator','LOINC','55454-3',
 'Hemoglobin A1c/Hemoglobin.total in Blood by calculation',
 12, NULL),

('CDC','Numerator','LOINC','71875-9',
 'Hemoglobin A1c/Hemoglobin.total [Pure mass fraction] in Blood',
 12, NULL),

-- ── CDC NUMERATOR: LDL Cholesterol LOINC codes ──────────────────
('CDC','Numerator','LOINC','13457-7',
 'Cholesterol in LDL [Mass/volume] in Serum or Plasma by calculation',
 12, 'Calculated LDL — most common in US labs'),

('CDC','Numerator','LOINC','2089-1',
 'Cholesterol in LDL [Mass/volume] in Serum or Plasma',
 12, 'Direct LDL measurement'),

('CDC','Numerator','LOINC','18262-6',
 'Cholesterol in LDL [Mass/volume] in Serum or Plasma by Direct assay',
 12, 'Direct LDL assay'),

('CDC','Numerator','LOINC','2091-7',
 'Cholesterol in VLDL [Mass/volume] in Serum or Plasma',
 12, 'VLDL — used in Friedewald LDL calculation'),

('CDC','Numerator','LOINC','22748-8',
 'LDL Cholesterol [Mass/volume] in Serum or Plasma',
 12, NULL),

-- ── CDC NUMERATOR: Eye Exam CPT codes ───────────────────────────
('CDC','Numerator','CPT','92002',
 'Ophthalmological services, new patient, intermediate',
 12, 'Eye exam — new patient intermediate'),

('CDC','Numerator','CPT','92004',
 'Ophthalmological services, new patient, comprehensive',
 12, 'Comprehensive eye exam — new patient'),

('CDC','Numerator','CPT','92012',
 'Ophthalmological services, established patient, intermediate',
 12, 'Eye exam — established patient intermediate'),

('CDC','Numerator','CPT','92014',
 'Ophthalmological services, established patient, comprehensive',
 12, 'MOST COMMON eye exam code — established patient'),

('CDC','Numerator','CPT','92018',
 'Ophthalmological examination and evaluation, with anesthesia',
 12, NULL),

('CDC','Numerator','CPT','92019',
 'Ophthalmological examination and evaluation, with anesthesia; limited',
 12, NULL),

('CDC','Numerator','CPT','92228',
 'Remote imaging for detection of retinal disease; with analysis and report',
 12, 'Teleretinal screening — counts for CDC eye exam'),

('CDC','Numerator','CPT','92229',
 'Imaging of optic disc and retina; with on-site automated analysis and report',
 12, NULL),

('CDC','Numerator','CPT','92230',
 'Fluorescein angioscopy with interpretation and report',
 12, NULL),

('CDC','Numerator','CPT','92235',
 'Fluorescein angiography with interpretation and report',
 12, NULL),

('CDC','Numerator','CPT','92240',
 'Indocyanine-green angiography with interpretation and report',
 12, NULL),

('CDC','Numerator','CPT','92250',
 'Fundus photography with interpretation and report',
 12, 'Retinal photography — counts as eye exam'),

('CDC','Numerator','CPT','92260',
 'Ophthalmoscopy, extended, with retinal drawing and scleral depression',
 12, NULL),

-- ── CDC NUMERATOR: Nephropathy Screening — UACR LOINC ───────────
('CDC','Numerator','LOINC','14957-5',
 'Microalbumin [Mass/volume] in Urine',
 12, 'Microalbumin urine test — nephropathy screening'),

('CDC','Numerator','LOINC','14958-3',
 'Microalbumin [Mass/time] in 24 hour Urine',
 12, '24-hour urine microalbumin'),

('CDC','Numerator','LOINC','14959-1',
 'Microalbumin [Mass/volume] in Urine collected for unspecified duration',
 12, NULL),

('CDC','Numerator','LOINC','32294-1',
 'Albumin/Creatinine [Ratio] in Urine',
 12, 'UACR — primary nephropathy screening test'),

('CDC','Numerator','LOINC','76401-9',
 'Albumin/Creatinine [Ratio] in Urine by Detection limit <= 3 mg/L',
 12, NULL),

('CDC','Numerator','LOINC','30000-4',
 'Microalbumin/Creatinine [Mass ratio] in Urine',
 12, NULL),

-- ── CDC NUMERATOR: Nephropathy Screening — eGFR LOINC ───────────
('CDC','Numerator','LOINC','62238-1',
 'Glomerular filtration rate/1.73 sq M.predicted by Creatinine-based formula in Serum, Plasma or Blood',
 12, 'eGFR CKD-EPI formula — primary GFR test'),

('CDC','Numerator','LOINC','48642-3',
 'Glomerular filtration rate/1.73 sq M.predicted among non-blacks by Creatinine-based formula in Serum, Plasma or Blood',
 12, 'eGFR non-Black race-based calculation'),

('CDC','Numerator','LOINC','48643-1',
 'Glomerular filtration rate/1.73 sq M.predicted among blacks by Creatinine-based formula in Serum, Plasma or Blood',
 12, 'eGFR Black race-based calculation'),

('CDC','Numerator','LOINC','88293-6',
 'Glomerular filtration rate/1.73 sq M predicted by Creatinine-based formula',
 12, NULL),

('CDC','Numerator','LOINC','88294-4',
 'Glomerular filtration rate/1.73 sq M predicted by Cystatin C-based formula',
 12, 'Cystatin C-based eGFR'),

-- ── CDC EXCLUSION: Gestational diabetes ─────────────────────────
('CDC','Exclusion','ICD10CM','O24.40',
 'Gestational diabetes mellitus in pregnancy, unspecified',
 NULL, 'Gestational DM — does NOT qualify for CDC denominator'),

('CDC','Exclusion','ICD10CM','O24.41',
 'Gestational diabetes mellitus in pregnancy, diet controlled',
 NULL, NULL),

('CDC','Exclusion','ICD10CM','O24.42',
 'Gestational diabetes mellitus in pregnancy, controlled by oral hypoglycemic drugs',
 NULL, NULL),

('CDC','Exclusion','ICD10CM','O24.43',
 'Gestational diabetes mellitus in pregnancy, controlled by insulin',
 NULL, NULL),

('CDC','Exclusion','ICD10CM','O24.44',
 'Gestational diabetes mellitus in pregnancy, controlled by combination therapy',
 NULL, NULL),

-- ── CDC EXCLUSION: Polycystic ovarian syndrome ───────────────────
('CDC','Exclusion','ICD10CM','E28.2',
 'Polycystic ovarian syndrome',
 NULL, 'PCOS — diabetes-like codes present but not true diabetes'),

-- ── CDC EXCLUSION: Frailty ICD-10 (for age 66+ members) ─────────
('CDC','Exclusion','ICD10CM','R54',
 'Age-related physical debility',
 12, 'Frailty — excludes CDC for members 66+'),

('CDC','Exclusion','ICD10CM','Z74.01',
 'Bed confinement status',
 12, NULL),

('CDC','Exclusion','ICD10CM','Z74.09',
 'Other reduced mobility',
 12, NULL),

('CDC','Exclusion','ICD10CM','M62.84',
 'Sarcopenia',
 12, 'Muscle wasting — frailty indicator');

-- ================================================================
-- SECTION 6: CBP — CONTROLLING BLOOD PRESSURE
-- Denominator : Hypertension dx (I10/I11/I12), age 18-85, enrolled
-- Numerator   : Most recent BP reading < 140/90 in measurement year
-- Exclusions  : ESRD, dialysis, pregnancy, advanced illness/frailty (66+), hospice
-- ================================================================

INSERT INTO reference.hedis_value_sets
    (measure_code, measure_component, code_system, code, code_description, lookback_months, notes)
VALUES

-- ── CBP DENOMINATOR: Hypertension ICD-10 ────────────────────────
('CBP','Denominator','ICD10CM','I10',
 'Essential (primary) hypertension',
 12, 'PRIMARY hypertension code — most common CBP denominator trigger'),

('CBP','Denominator','ICD10CM','I11.0',
 'Hypertensive heart disease with heart failure',
 12, NULL),

('CBP','Denominator','ICD10CM','I11.9',
 'Hypertensive heart disease without heart failure',
 12, NULL),

('CBP','Denominator','ICD10CM','I12.9',
 'Hypertensive chronic kidney disease with stage 1 through stage 4 chronic kidney disease',
 12, NULL),

('CBP','Denominator','ICD10CM','I13.10',
 'Hypertensive heart and chronic kidney disease without heart failure, with stage 1 through 4 CKD',
 12, NULL),

('CBP','Denominator','ICD10CM','I13.11',
 'Hypertensive heart and chronic kidney disease without heart failure, with stage 5 CKD or ESRD',
 12, NULL),

-- ── CBP NUMERATOR: Blood Pressure Reading LOINC codes ───────────
('CBP','Numerator','LOINC','55284-4',
 'Blood pressure systolic and diastolic',
 12, 'BP panel — captures both systolic and diastolic together'),

('CBP','Numerator','LOINC','8480-6',
 'Systolic blood pressure',
 12, 'Systolic BP — 140 threshold for CBP controlled'),

('CBP','Numerator','LOINC','8462-4',
 'Diastolic blood pressure',
 12, 'Diastolic BP — 90 threshold for CBP controlled'),

('CBP','Numerator','LOINC','35094-2',
 'Blood pressure panel',
 12, 'Alternative BP panel LOINC code'),

('CBP','Numerator','LOINC','55285-1',
 'Blood pressure systolic and diastolic by 24 hour',
 12, 'Ambulatory BP monitoring'),

-- ── CBP EXCLUSION: ESRD / Dialysis ──────────────────────────────
('CBP','Exclusion','ICD10CM','N18.5',
 'Chronic kidney disease, stage 5',
 NULL, 'CKD Stage 5 — near-ESRD, CBP exclusion'),

('CBP','Exclusion','ICD10CM','N18.6',
 'End stage renal disease',
 NULL, 'ESRD — primary CBP exclusion'),

('CBP','Exclusion','ICD10CM','Z99.2',
 'Dependence on renal dialysis',
 NULL, 'Dialysis dependence — CBP exclusion'),

('CBP','Exclusion','ICD10CM','Z91.15',
 'Patient noncompliance with renal dialysis',
 NULL, 'Dialysis noncompliance — still ESRD patient'),

-- ── CBP EXCLUSION: Pregnancy hypertension ───────────────────────
('CBP','Exclusion','ICD10CM','O10.011',
 'Pre-existing essential hypertension complicating pregnancy, first trimester',
 NULL, 'Pregnancy HTN — CBP exclusion'),

('CBP','Exclusion','ICD10CM','O10.012',
 'Pre-existing essential hypertension complicating pregnancy, second trimester',
 NULL, NULL),

('CBP','Exclusion','ICD10CM','O10.013',
 'Pre-existing essential hypertension complicating pregnancy, third trimester',
 NULL, NULL),

('CBP','Exclusion','ICD10CM','O11.1',
 'Pre-existing hypertension with pre-eclampsia, first trimester',
 NULL, NULL),

('CBP','Exclusion','ICD10CM','O11.2',
 'Pre-existing hypertension with pre-eclampsia, second trimester',
 NULL, NULL),

('CBP','Exclusion','ICD10CM','O13.1',
 'Gestational hypertension without significant proteinuria, first trimester',
 NULL, NULL),

('CBP','Exclusion','ICD10CM','O13.2',
 'Gestational hypertension without significant proteinuria, second trimester',
 NULL, NULL),

('CBP','Exclusion','ICD10CM','O13.3',
 'Gestational hypertension without significant proteinuria, third trimester',
 NULL, NULL),

('CBP','Exclusion','ICD10CM','O14.00',
 'Mild to moderate pre-eclampsia, unspecified trimester',
 NULL, NULL),

('CBP','Exclusion','ICD10CM','O14.10',
 'Severe pre-eclampsia, unspecified trimester',
 NULL, NULL),

('CBP','Exclusion','ICD10CM','O16.1',
 'Unspecified maternal hypertension, first trimester',
 NULL, NULL),

-- ── CBP EXCLUSION: Frailty + Advanced Illness (age 66+) ─────────
('CBP','Exclusion','ICD10CM','R54',
 'Age-related physical debility',
 12, 'Frailty — CBP exclusion for members age 66+'),

('CBP','Exclusion','ICD10CM','M62.84',
 'Sarcopenia',
 12, NULL),

('CBP','Exclusion','ICD10CM','Z74.01',
 'Bed confinement status',
 12, NULL),

-- ── CBP EXCLUSION: Hospice ───────────────────────────────────────
('CBP','Exclusion','HCPCS','Q5003','Hospice care, nursing facility',NULL,'Hospice — CBP exclusion'),
('CBP','Exclusion','HCPCS','Q5004','Hospice care, custodial facility',NULL,NULL),
('CBP','Exclusion','HCPCS','Q5005','Hospice care, inpatient hospital',NULL,NULL),
('CBP','Exclusion','ICD10CM','Z51.5','Encounter for palliative care',NULL,NULL);

-- ================================================================
-- SECTION 7: CCS — CERVICAL CANCER SCREENING
-- Denominator : Female, age 24-64, enrolled
-- Numerator   : Pap smear (3yr lookback) OR Pap+HPV co-test (5yr lookback)
--               OR HPV primary screening alone (5yr lookback, NCQA 2025)
-- Exclusions  : Hysterectomy with cervix removal, hospice
-- ================================================================

INSERT INTO reference.hedis_value_sets
    (measure_code, measure_component, code_system, code, code_description, lookback_months, notes)
VALUES

-- ── CCS NUMERATOR: Pap Smear CPT codes (3-year = 36 months) ─────
('CCS','Numerator','CPT','88141',
 'Cytopathology, cervical or vaginal; requiring interpretation by physician',
 36, 'Pap with physician interpretation — 3yr lookback'),

('CCS','Numerator','CPT','88142',
 'Cytopathology, cervical or vaginal; collected in preservative fluid, automated thin layer preparation',
 36, 'ThinPrep Pap — most common liquid-based cytology'),

('CCS','Numerator','CPT','88143',
 'Cytopathology, cervical or vaginal; collected in preservative fluid, automated thin layer preparation, manual screening and rescreening',
 36, NULL),

('CCS','Numerator','CPT','88147',
 'Cytopathology smears, cervical or vaginal; screening by automated system under physician supervision',
 36, NULL),

('CCS','Numerator','CPT','88148',
 'Cytopathology smears, cervical or vaginal; screening by automated system with manual rescreening',
 36, NULL),

('CCS','Numerator','CPT','88150',
 'Cytopathology, slides, cervical or vaginal; manual screening under physician supervision',
 36, 'Conventional Pap smear'),

('CCS','Numerator','CPT','88152',
 'Cytopathology, slides, cervical or vaginal; with automated rescreening under physician supervision',
 36, NULL),

('CCS','Numerator','CPT','88153',
 'Cytopathology, slides, cervical or vaginal; with automated rescreening, requiring interpretation by physician',
 36, NULL),

('CCS','Numerator','CPT','88154',
 'Cytopathology, slides, cervical or vaginal; with automated thin layer preparation, screening and rescreening by automated system, requiring interpretation by physician',
 36, NULL),

('CCS','Numerator','CPT','88155',
 'Cytopathology, slides, cervical or vaginal; definitive hormonal evaluation',
 36, NULL),

('CCS','Numerator','CPT','88164',
 'Cytopathology, slides, cervical or vaginal; manual screening under physician supervision (Bethesda)',
 36, NULL),

('CCS','Numerator','CPT','88165',
 'Cytopathology, slides, cervical or vaginal; with manual screening and rescreening (Bethesda)',
 36, NULL),

('CCS','Numerator','CPT','88166',
 'Cytopathology, slides, cervical or vaginal; with automated screening (Bethesda)',
 36, NULL),

('CCS','Numerator','CPT','88167',
 'Cytopathology, slides, cervical or vaginal; with automated screening and manual rescreening (Bethesda)',
 36, NULL),

-- ── CCS NUMERATOR: Pap HCPCS codes ──────────────────────────────
('CCS','Numerator','CPT','P3000',
 'Screening Papanicolaou smear, cervical or vaginal, up to three smears',
 36, 'G-code — Medicare Pap smear'),

('CCS','Numerator','CPT','P3001',
 'Screening Papanicolaou smear, cervical or vaginal, up to three smears, requiring interpretation by physician',
 36, NULL),

('CCS','Numerator','HCPCS','G0123',
 'Screening cytopathology, cervical or vaginal (any reporting system), collected in preservative fluid, automated thin layer preparation',
 36, 'Medicare ThinPrep Pap'),

('CCS','Numerator','HCPCS','G0124',
 'Screening cytopathology, cervical or vaginal (any reporting system), collected in preservative fluid, automated thin layer preparation, requiring interpretation by physician',
 36, NULL),

('CCS','Numerator','HCPCS','G0141',
 'Screening cytopathology smears, cervical or vaginal, performed by automated system, with manual rescreening, requiring interpretation by physician',
 36, NULL),

('CCS','Numerator','HCPCS','G0143',
 'Screening cytopathology, cervical or vaginal, collected in preservative fluid, automated thin layer preparation, with manual screening and rescreening by cytotechnologist',
 36, NULL),

('CCS','Numerator','HCPCS','G0144',
 'Screening cytopathology, cervical or vaginal, collected in preservative fluid, automated thin layer preparation, with screening by automated system, under physician supervision',
 36, NULL),

('CCS','Numerator','HCPCS','G0145',
 'Screening cytopathology, cervical or vaginal, collected in preservative fluid, automated thin layer preparation, with screening by automated system and manual rescreening',
 36, NULL),

('CCS','Numerator','HCPCS','G0147',
 'Screening cytopathology smears, cervical or vaginal, performed by automated system under physician supervision',
 36, NULL),

('CCS','Numerator','HCPCS','G0148',
 'Screening cytopathology smears, cervical or vaginal, performed by automated system with manual rescreening',
 36, NULL),

-- ── CCS NUMERATOR: HPV Co-Test CPT (5-year = 60 months) ─────────
('CCS','Numerator','CPT','87620',
 'Infectious agent detection by nucleic acid; Human Papillomavirus (HPV), low-risk types',
 60, 'HPV low-risk types — co-test with Pap, 5yr lookback'),

('CCS','Numerator','CPT','87621',
 'Infectious agent detection by nucleic acid; Human Papillomavirus (HPV), high-risk types',
 60, 'HPV high-risk types — PRIMARY co-test code'),

('CCS','Numerator','CPT','87622',
 'Infectious agent detection by nucleic acid; Human Papillomavirus (HPV), types 16 and 18',
 60, 'HPV genotype 16 and 18 testing'),

('CCS','Numerator','CPT','87624',
 'Infectious agent detection by nucleic acid; Human Papillomavirus (HPV), high-risk types, with genotype 16 and 18 reporting',
 60, 'HPV high-risk with genotyping — newer code'),

('CCS','Numerator','CPT','87625',
 'Infectious agent detection by nucleic acid; Human Papillomavirus (HPV), types 16 and 18, with types 31, 33, 45, 52, and 58',
 60, 'Extended HPV genotyping panel — NCQA 2025 primary screening'),

-- ── CCS NUMERATOR: HPV LOINC codes (lab results) ────────────────
('CCS','Numerator','LOINC','21440-3',
 'Human papilloma virus 16+18+31+33+35+45+51+52+56 DNA [Presence] in Cervix by Probe',
 60, 'HPV DNA panel LOINC — lab result'),

('CCS','Numerator','LOINC','30167-1',
 'Human papilloma virus, high risk, DNA [Presence] in Cervix by Probe and target amplification method',
 60, 'HPV high-risk DNA probe — most common lab LOINC'),

('CCS','Numerator','LOINC','38372-9',
 'Human papilloma virus DNA panel, Cervix',
 60, 'HPV DNA panel'),

('CCS','Numerator','LOINC','59263-4',
 'Human papilloma virus 16 DNA [Presence] in Cervix by NAA with probe detection',
 60, 'HPV 16 specific LOINC'),

('CCS','Numerator','LOINC','59264-2',
 'Human papilloma virus 18 DNA [Presence] in Cervix by NAA with probe detection',
 60, 'HPV 18 specific LOINC'),

('CCS','Numerator','LOINC','77399-4',
 'Human papilloma virus High Risk DNA [Presence] in Cervix by NAA with probe detection',
 60, 'HPV primary screening LOINC — NCQA 2025 new addition'),

('CCS','Numerator','LOINC','77400-0',
 'Human papilloma virus 16+18+45 DNA [Presence] in Cervix by NAA with probe detection',
 60, 'HPV 16/18/45 extended panel'),

-- ── CCS EXCLUSION: Hysterectomy ICD-10 ──────────────────────────
('CCS','Exclusion','ICD10CM','Z90.710',
 'Acquired absence of both cervix and uterus',
 NULL, 'PRIMARY hysterectomy exclusion — cervix removed'),

('CCS','Exclusion','ICD10CM','Z90.711',
 'Acquired absence of uterus with remaining cervical stump',
 NULL, 'Uterus removed but cervix REMAINS — CCS still applies here'),

('CCS','Exclusion','ICD10CM','Z90.712',
 'Acquired absence of uterus, not otherwise specified',
 NULL, 'Hysterectomy NOS — use clinical judgment'),

('CCS','Exclusion','ICD10CM','Z90.72',
 'Acquired absence of ovaries, bilateral',
 NULL, 'Bilateral oophorectomy — may accompany hysterectomy'),

-- ── CCS EXCLUSION: Hysterectomy CPT codes ───────────────────────
('CCS','Exclusion','CPT','58150','Total abdominal hysterectomy, corpus and cervix',NULL,'Abdominal hysterectomy — cervix removed'),
('CCS','Exclusion','CPT','58152','Total abdominal hysterectomy, with colpo-urethropexy',NULL,NULL),
('CCS','Exclusion','CPT','58200','Total abdominal hysterectomy, including partial vaginectomy, with para-aortic and pelvic lymph node sampling',NULL,NULL),
('CCS','Exclusion','CPT','58210','Radical abdominal hysterectomy, with bilateral total pelvic lymphadenectomy',NULL,NULL),
('CCS','Exclusion','CPT','58240','Pelvic exenteration, complete, for gynecologic malignancy',NULL,NULL),
('CCS','Exclusion','CPT','58260','Vaginal hysterectomy, for uterus 250 g or less',NULL,'Vaginal hysterectomy — cervix typically removed'),
('CCS','Exclusion','CPT','58262','Vaginal hysterectomy, for uterus 250 g or less; with removal of tube(s), and/or ovary(s)',NULL,NULL),
('CCS','Exclusion','CPT','58263','Vaginal hysterectomy, for uterus 250 g or less; with removal of tube(s), and/or ovary(s), with repair of enterocele',NULL,NULL),
('CCS','Exclusion','CPT','58267','Vaginal hysterectomy, for uterus 250 g or less; with colpourethropexy',NULL,NULL),
('CCS','Exclusion','CPT','58270','Vaginal hysterectomy, for uterus 250 g or less; with repair of enterocele',NULL,NULL),
('CCS','Exclusion','CPT','58275','Vaginal hysterectomy, with total or partial vaginectomy',NULL,NULL),
('CCS','Exclusion','CPT','58280','Vaginal hysterectomy, with total or partial vaginectomy; with repair of enterocele',NULL,NULL),
('CCS','Exclusion','CPT','58290','Vaginal hysterectomy, for uterus greater than 250 g',NULL,NULL),
('CCS','Exclusion','CPT','58291','Vaginal hysterectomy, for uterus greater than 250 g; with removal of tube(s) and/or ovary(s)',NULL,NULL),
('CCS','Exclusion','CPT','58292','Vaginal hysterectomy, for uterus greater than 250 g; with removal of tube(s) and/or ovary(s), with repair of enterocele',NULL,NULL),
('CCS','Exclusion','CPT','58294','Vaginal hysterectomy, for uterus greater than 250 g; with repair of enterocele',NULL,NULL),
-- Laparoscopic hysterectomy codes
('CCS','Exclusion','CPT','58541','Laparoscopic supracervical hysterectomy, for uterus 250 g or less',NULL,'Supracervical — cervix RETAINED, may NOT be exclusion'),
('CCS','Exclusion','CPT','58542','Laparoscopic supracervical hysterectomy, for uterus 250 g or less; with removal of tube(s) and/or ovary(s)',NULL,NULL),
('CCS','Exclusion','CPT','58543','Laparoscopic supracervical hysterectomy, for uterus greater than 250 g',NULL,NULL),
('CCS','Exclusion','CPT','58544','Laparoscopic supracervical hysterectomy, for uterus greater than 250 g; with removal of tube(s) and/or ovary(s)',NULL,NULL),
('CCS','Exclusion','CPT','58550','Laparoscopic vaginal hysterectomy (LAVH), for uterus 250 g or less',NULL,'LAVH — cervix removed'),
('CCS','Exclusion','CPT','58552','LAVH, for uterus 250 g or less; with removal of tube(s) and/or ovary(s)',NULL,NULL),
('CCS','Exclusion','CPT','58553','LAVH, for uterus greater than 250 g',NULL,NULL),
('CCS','Exclusion','CPT','58554','LAVH, for uterus greater than 250 g; with removal of tube(s) and/or ovary(s)',NULL,NULL),
('CCS','Exclusion','CPT','58570','Laparoscopic total hysterectomy, for uterus 250 g or less',NULL,'Total laparoscopic hysterectomy — cervix removed'),
('CCS','Exclusion','CPT','58571','Laparoscopic total hysterectomy, for uterus 250 g or less; with removal of tube(s) and/or ovary(s)',NULL,NULL),
('CCS','Exclusion','CPT','58572','Laparoscopic total hysterectomy, for uterus greater than 250 g',NULL,NULL),
('CCS','Exclusion','CPT','58573','Laparoscopic total hysterectomy, for uterus greater than 250 g; with removal of tube(s) and/or ovary(s)',NULL,NULL),
('CCS','Exclusion','CPT','58575','Laparoscopic total hysterectomy, with bilateral salpingo-oophorectomy and omentectomy, for malignancy',NULL,NULL),

-- ── CCS EXCLUSION: Hospice ───────────────────────────────────────
('CCS','Exclusion','HCPCS','Q5003','Hospice care, nursing facility',NULL,'Hospice — CCS exclusion'),
('CCS','Exclusion','HCPCS','Q5004','Hospice care, custodial facility',NULL,NULL),
('CCS','Exclusion','HCPCS','Q5005','Hospice care, inpatient hospital',NULL,NULL),
('CCS','Exclusion','ICD10CM','Z51.5','Encounter for palliative care',NULL,NULL);

-- ================================================================
-- SECTION 8: VERIFICATION QUERIES
-- Run these after the inserts to confirm data loaded correctly
-- ================================================================

-- Total rows loaded
SELECT
    'TOTAL ROWS LOADED' AS check_name,
    COUNT(*) AS row_count
FROM reference.hedis_value_sets;

-- Rows per measure
SELECT
    measure_code,
    COUNT(*) AS total_codes,
    COUNT(CASE WHEN measure_component = 'Denominator' THEN 1 END) AS denominator_codes,
    COUNT(CASE WHEN measure_component = 'Numerator'   THEN 1 END) AS numerator_codes,
    COUNT(CASE WHEN measure_component = 'Exclusion'   THEN 1 END) AS exclusion_codes
FROM reference.hedis_value_sets
GROUP BY measure_code
ORDER BY measure_code;

-- Rows per code system
SELECT
    code_system,
    COUNT(*) AS code_count,
    COUNT(DISTINCT measure_code) AS measures_using_this_system
FROM reference.hedis_value_sets
GROUP BY code_system
ORDER BY code_count DESC;

-- Lookback window distribution
SELECT
    lookback_months,
    CASE
        WHEN lookback_months IS NULL THEN 'Historical (any date)'
        WHEN lookback_months = 12    THEN 'Annual (12 months)'
        WHEN lookback_months = 27    THEN 'BCS mammogram (27 months)'
        WHEN lookback_months = 36    THEN 'CCS Pap alone (3 years)'
        WHEN lookback_months = 60    THEN 'CCS co-test / sigmoidoscopy (5 years)'
        WHEN lookback_months = 120   THEN 'Colonoscopy (10 years)'
        ELSE CAST(lookback_months AS STRING) || ' months'
    END AS lookback_description,
    COUNT(*) AS code_count
FROM reference.hedis_value_sets
GROUP BY lookback_months
ORDER BY lookback_months NULLS FIRST;

-- Sample: BCS numerator codes
SELECT code, code_system, code_description, lookback_months
FROM reference.hedis_value_sets
WHERE measure_code = 'BCS'
  AND measure_component = 'Numerator'
ORDER BY code_system, code;

-- Sample: All exclusion codes across all measures
SELECT measure_code, code_system, code, code_description
FROM reference.hedis_value_sets
WHERE measure_component = 'Exclusion'
ORDER BY measure_code, code_system, code;

-- ================================================================
-- SECTION 9: HOW THE DLT PIPELINE USES THIS TABLE
-- (Reference queries — do not need to run, just for understanding)
-- ================================================================

/*
-- Example: Find all members with a mammogram in BCS numerator window
SELECT DISTINCT cp.member_id, cp.service_date, cp.procedure_code, vs.code_description
FROM silver.claims_procedure cp
JOIN reference.hedis_value_sets vs
    ON cp.procedure_code = vs.code
WHERE vs.measure_code      = 'BCS'
  AND vs.measure_component = 'Numerator'
  AND vs.is_active         = TRUE
  AND cp.claim_status      = 'Paid'
  AND cp.service_date >= ADD_MONTHS(TO_DATE('2025-12-31'), -vs.lookback_months);

-- Example: Find all exclusion evidence for COL measure
SELECT DISTINCT cd.member_id, cd.diagnosis_code, vs.code_description, vs.measure_component
FROM silver.claims_diagnoses cd
JOIN reference.hedis_value_sets vs
    ON cd.diagnosis_code = vs.code
WHERE vs.measure_code      = 'COL'
  AND vs.measure_component = 'Exclusion'
  AND vs.is_active         = TRUE;

-- Example: Find all diabetes denominator members for CDC
SELECT DISTINCT cd.member_id, cd.diagnosis_code, vs.code_description
FROM silver.claims_diagnoses cd
JOIN reference.hedis_value_sets vs
    ON cd.diagnosis_code = vs.code
WHERE vs.measure_code      = 'CDC'
  AND vs.measure_component = 'Denominator'
  AND vs.is_active         = TRUE
  AND YEAR(cd.service_date) = 2025;
*/

-- ================================================================
-- END OF SCRIPT
-- Expected output from verification:
--   TOTAL ROWS: ~260 rows
--   BCS  : ~23 rows (7 numerator + 16 exclusion)
--   COL  : ~50 rows (18 colonoscopy + 17 sigmoidoscopy + 9 FIT/other + 14 exclusion)
--   CDC  : ~65 rows (12 denominator + 6 HbA1c + 5 LDL + 13 eye + 10 nephropathy + 10 exclusion)
--   CBP  : ~35 rows (6 denominator + 5 BP LOINC + 18 exclusion)
--   CCS  : ~90 rows (14 pap CPT + 8 pap HCPCS + 7 HPV CPT + 7 HPV LOINC + 36 hysterectomy + 4 hospice)
-- ================================================================
