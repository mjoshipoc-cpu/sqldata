import pandas as pd
from datetime import datetime, timedelta
import logging
import os
import streamlit as st

# Configure logging with timestamp, function name, and message
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

server_name = os.getenv("HEDIS_SERVER")
database_name = os.getenv("HEDIS_DATABASE")

# Initialize MEASUREMENT_YEAR as None to avoid calling get_dynamic_measurement_year at import time
# MEASUREMENT_YEAR = 2024  # Hardcoded to 2024
MEASUREMENT_YEAR=int(st.session_state.get('MY','2024'))
logger.info("Script initialized with MEASUREMENT_YEAR set to %s", MEASUREMENT_YEAR)

def get_measurement_year_cutoff(measurement_year: int) -> datetime:
    """
    Determine the compliance cutoff date based on measurement year logic.
    """
    logger.info("Called with measurement_year=%s to determine cutoff date", measurement_year)
    today = datetime.today()
    if measurement_year < today.year:
        cutoff = datetime(measurement_year, 12, 31)
        logger.info("Measurement year %s is past, using cutoff date: %s", measurement_year, cutoff)
        return cutoff
    else:
        logger.info("Measurement year %s is current, using today's date: %s", measurement_year, today)
        return today

def parse_date(date_str):
    """
    Parse dates according to HEDIS date standards.
    """
    logger.info("Called to parse date string: %s", date_str)
    if pd.isna(date_str) or date_str in ["NULL", "NA", "Not Applicable"]:
        logger.info("Date string %s is invalid or marked as NA, returning None", date_str)
        return None
    try:
        if isinstance(date_str, (int, float)):
            parsed_date = pd.to_datetime(date_str, unit='D', origin='1899-12-30')
            logger.info("Parsed numeric date %s as %s", date_str, parsed_date)
            return parsed_date
        parsed_date = pd.to_datetime(date_str, errors='coerce')
        if pd.isna(parsed_date):
            logger.warning("Failed to parse date string %s, returning None", date_str)
            return None
        logger.info("Successfully parsed date string %s as %s", date_str, parsed_date)
        return parsed_date
    except ValueError as e:
        logger.error("ValueError while parsing date string %s: %s", date_str, str(e))
        return None

def has_diabetes_status(row, measure_type, idx):
    """
    Determine diabetes status for a given row.
    """
    logger.info("Called for measure_type=%s, row index=%s to determine diabetes status", measure_type, idx)
    diabetes_columns = ['Diabetes', 'Posg_diabetes', 'Posg diabetes', 'Posg_diat']
    acceptable_values = [
        "yes", "y", "true", "t", "1", "diabetic",
        "type 1 diabetes mellitus without complications", 
        "type 2 diabetes mellitus without complications",
        "type 1 diabetes", "type 2 diabetes", "diabetes mellitus"
    ]
    # Log the values of all diabetes-related columns
    diabetes_values = {col: row.get(col) for col in diabetes_columns if col in row and pd.notna(row[col])}
    logger.info("Diabetes columns for %s row %s: %s", measure_type, idx, diabetes_values)
    # Get the first non-None value from the diabetes columns
    diabetes_value = None
    for col in diabetes_columns:
        if col in row and pd.notna(row[col]):
            diabetes_value = str(row[col]).strip().lower()
            logger.info("Found diabetes value in column %s: %s", col, diabetes_value)
            break
    if diabetes_value is None:
        diabetes_value = ""
        logger.info("No diabetes value found, defaulting to empty string")
    # Check if the value matches any acceptable value
    has_diabetes = diabetes_value in acceptable_values
    logger.info("Diabetes status for %s row %s: %s (value: %s)", measure_type, idx, has_diabetes, diabetes_value)
    return has_diabetes

def merge_dob(df, member_df):
    """
    Merge member data with measure dataframe.
    """
    logger.info("Called to merge DOB with DataFrame of shape %s and member_df of shape %s", df.shape, member_df.shape)
    required_columns = ['Member_id', 'DOB', 'Gender', 'Hospice_Pallitative', 'Name']
    optional_columns = ['Provider', 'Diabetes', 'Posg_diabetes', 'Posg diabetes', 'Posg_diat']
    missing_required = [col for col in required_columns if col not in member_df.columns]
    if missing_required:
        logger.error("Missing required columns in member_df: %s", missing_required)
        raise ValueError(f"Missing required columns in member_df: {missing_required}")
    merge_columns = required_columns + [col for col in optional_columns if col in member_df.columns]
    # Check if any diabetes columns are present
    diabetes_columns_present = [col for col in optional_columns if col in member_df.columns]
    if not diabetes_columns_present:
        logger.warning("No diabetes-related columns (Diabetes, Posg_diabetes, Posg diabetes, Posg_diat) found in member_df")
    logger.info("Merging columns: %s", merge_columns)
    merged_df = df.merge(member_df[merge_columns], on='Member_id', how='left')
    logger.info("Merged DataFrame columns: %s, shape: %s", list(merged_df.columns), merged_df.shape)
    return merged_df

def detect_measure_type(df):
    """
    Detect measure type from dataframe based on columns.
    """
    logger.info("Called to detect measure type for DataFrame with columns: %s", list(df.columns))
    column_indicators = {
        'BCS': ['Mammogram_DOS', 'Bilateral_Mastectomy', 'Unilateral_Mastectomy_R', 'Unilateral_Mastectomy_L'],
        'HBD': ['HbA1c_DOS_page_No', 'ReHbA1c_DC', 'HbA1c_DC', 'HbA1c_DOS'],
        'CBP': ['Hypertension'],
        'BPD': ['Diabetes'],
        'EED': ['EYE_EXAM_Date', 'HAS_SEEN_OPTHOMETERIS', 'Retinal_or_dilated_eye_exam_result'],
        'COL': ['colectomy_DOS', 'colonoscopy_DOS', 'CT_colonoscopy_DOS', 'FIT_FOBT_DOS', 'Stool_DNA_DOS', 'Flexiable_Sigmoidscopy_Actual_date'],
        'CCS': ['HPV_test_DOS', 'PAP_test_DOS', 'Hysterectomy'],
        'LSD': ['Lead_Screening'],
        'PPC': ['Did_Member_Have_Delivery', 'Was_Postpartum_Care_Provided']
    }
    for measure, indicators in column_indicators.items():
        matching_indicators = [indicator for indicator in indicators if indicator in df.columns]
        if matching_indicators:
            logger.info("Detected measure type %s based on indicators: %s", measure, matching_indicators)
            return measure
    logger.error("Could not detect measure type from DataFrame columns: %s", list(df.columns))
    raise ValueError("Could not detect measure type from dataframe columns")

def apply_ncqa_compliance_checks(df, measure_type):
    # print(f"\nLOG1: {sorted(df.columns)}\n")
    """
    Apply NCQA compliance checks for the specified measure type.
    """
    logger.info("Called for measure_type=%s with DataFrame of shape %s", measure_type, df.shape)
    if df.empty:
        logger.warning("DataFrame for %s is empty, skipping compliance checks", measure_type)
        remark_col = f'Remark_{measure_type}'
        df[remark_col] = None
        df['Updated'] = None
        return df

    # Check for duplicate indices
    if df.index.duplicated().any():
        logger.warning("Duplicate indices found in DataFrame for %s. Resetting index...", measure_type)
        df = df.reset_index(drop=True)

    # Use the hardcoded MEASUREMENT_YEAR
    measurement_year = MEASUREMENT_YEAR
    if measurement_year is None:
        logger.error("Measurement Year is None for %s. Using default year 2024", measure_type)
        measurement_year = 2024  # Fallback default year
    logger.info("Using measurement year %s for %s", measurement_year, measure_type)

    current_date = get_measurement_year_cutoff(measurement_year)
    hpv_valid_from = current_date - timedelta(days=365 * 4)
    pap_valid_from = current_date - timedelta(days=365 * 2)
    colonoscopy_valid_from = current_date - timedelta(days=365 * 10)
    fit_valid_from = current_date - timedelta(days=365 * 1)
    ct_valid_from = current_date - timedelta(days=365 * 5)
    stool_dna_valid_from = current_date - timedelta(days=365 * 3)
    sigmoidoscopy_valid_from = current_date - timedelta(days=365 * 5)
    logger.info("Cutoff dates for %s - HPV: %s, PAP: %s, Colonoscopy: %s, FIT: %s, CT: %s, Stool DNA: %s, Sigmoidoscopy: %s",
                measure_type, hpv_valid_from, pap_valid_from, colonoscopy_valid_from, fit_valid_from,
                ct_valid_from, stool_dna_valid_from, sigmoidoscopy_valid_from)

    remarks = []
    for idx, row in df.iterrows():
        member_id = row.get('Member_id', 'Unknown')
        logger.info("Processing row %s for member_id=%s in measure %s", idx, member_id, measure_type)
        try:
            if pd.isna(row.get('Name')) or str(row.get('Name', '')).strip() == "":
                logger.info("Member_id=%s in %s excluded: No name", member_id, measure_type)
                remarks.append((f"Exclusion:{measure_type} - NN-NO Name", current_date.strftime("%Y-%m-%d")))
                continue

            print(f"C_LOG1: {type(row)}")
            print(f"C_LOG2: {row.get('Gender')}")

            if pd.isna(row.get('Gender')) or str(row.get('Gender', '')).strip() == "":
                logger.info("Member_id=%s in %s excluded: No gender", member_id, measure_type)
                remarks.append((f"Exclusion:{measure_type} - Ngender", current_date.strftime("%Y-%m-%d")))
                continue
            if 'Provider' in row and (pd.isna(row.get('Provider')) or str(row.get('Provider', '')).strip() == ""):
                logger.info("Member_id=%s in %s excluded: No provider info", member_id, measure_type)
                remarks.append((f"Exclusion:{measure_type} - No provider info in record", current_date.strftime("%Y-%m-%d")))
                continue
            dob = pd.to_datetime(row.get("DOB", None), errors='coerce')
            gender = str(row.get("Gender", "")).strip().lower()
            age = (current_date - dob).days / 365.25 if pd.notna(dob) else None
            logger.info("Member_id=%s in %s - DOB: %s, Gender: %s, Age: %s", member_id, measure_type, dob, gender, age)
            print(f"\nLOG2: {sorted(df.columns)}\n")
            if measure_type == "BCS":
                logger.info("Applying BCS compliance checks for member_id=%s", member_id)
                mammogram_date = pd.to_datetime(row.get("Mammogram_DOS", None), errors='coerce')
                bilateral = str(row.get("Bilateral_Mastectomy", "")).strip().lower() == "yes"
                unilateral_r = str(row.get("Unilateral_Mastectomy_R", "")).strip().lower() == "yes"
                unilateral_l = str(row.get("Unilateral_Mastectomy_L", "")).strip().lower() == "yes"
                unilateral_r_dos = parse_date(row.get("Unilateral_Mastectomy_R_DOS", None))
                unilateral_l_dos = parse_date(row.get("Unilateral_Mastectomy_L_DOS", None))
                logger.info("BCS details - Mammogram DOS: %s, Bilateral: %s, Unilateral R: %s, Unilateral L: %s, Unilateral R DOS: %s, Unilateral L DOS: %s",
                            mammogram_date, bilateral, unilateral_r, unilateral_l, unilateral_r_dos, unilateral_l_dos)
                if row['Hospice_Pallitative'] in ["Yes", "YES"]:
                    logger.info("Member_id=%s excluded from BCS: Hospice Care", member_id)
                    remarks.append(("Exclusion:BCS - Hospice Care", current_date.strftime("%Y-%m-%d")))
                elif pd.isna(dob):
                    logger.info("Member_id=%s excluded from BCS: Invalid DOB", member_id)
                    remarks.append(("Exclusion:BCS - Invalid DOB", current_date.strftime("%Y-%m-%d")))
                elif gender == "male":
                    logger.info("Member_id=%s excluded from BCS: Gender Male", member_id)
                    remarks.append(("Exclusion:BCS - Gender Male", current_date.strftime("%Y-%m-%d")))
                elif 50 <= age <= 74:
                    if bilateral:
                        logger.info("Member_id=%s excluded from BCS: Bilateral Mastectomy", member_id)
                        remarks.append(("Exclusion:BCS - Bilateral Mastectomy", current_date.strftime("%Y-%m-%d")))
                    elif unilateral_r or unilateral_l or pd.notna(unilateral_r_dos) or pd.notna(unilateral_l_dos):
                        logger.info("Member_id=%s excluded from BCS: Unilateral Mastectomy", member_id)
                        remarks.append(("Exclusion:BCS - Unilateral Mastectomy", current_date.strftime("%Y-%m-%d")))
                    elif pd.notna(mammogram_date) and (current_date - mammogram_date).days <= 990:
                        logger.info("Member_id=%s compliant with BCS: Mammogram within 990 days", member_id)
                        remarks.append(("Compliant:BCS - Mammogram", current_date.strftime("%Y-%m-%d")))
                    else:
                        logger.info("Member_id=%s non-compliant with BCS: No valid mammogram", member_id)
                        remarks.append(("Non-compliant:BCS", current_date.strftime("%Y-%m-%d")))
                else:
                    logger.info("Member_id=%s excluded from BCS: Age or Gender criteria not met", member_id)
                    remarks.append(("Exclusion:BCS - Age or Gender criteria not met", current_date.strftime("%Y-%m-%d")))

            elif measure_type == "HBD":
                logger.info("Applying HBD compliance checks for member_id=%s", member_id)
                hba1c_value = row.get("HbA1c_ReHbA1c", row.get("HbA1c_Result"))
                hba1c_date = (pd.to_datetime(row.get("ReHbA1c_DC"), errors='coerce') or 
                              pd.to_datetime(row.get("HbA1c_DC"), errors='coerce') or 
                              pd.to_datetime(row.get("HbA1c_DOS"), errors='coerce'))
                logger.info("HBD details - HbA1c Value: %s, HbA1c Date: %s", hba1c_value, hba1c_date)
                has_diabetes = has_diabetes_status(row, "HBD", idx)
                if row['Hospice_Pallitative'] in ["Yes", "YES"]:
                    logger.info("Member_id=%s excluded from HBD: Hospice Care", member_id)
                    remarks.append(("Exclusion:HBD - Hospice Care", current_date.strftime("%Y-%m-%d")))
                elif pd.isna(dob):
                    logger.info("Member_id=%s excluded from HBD: Invalid DOB", member_id)
                    remarks.append(("Exclusion:HBD - Invalid DOB", current_date.strftime("%Y-%m-%d")))
                elif not has_diabetes:
                    logger.info("Member_id=%s non-applicable for HBD: No diabetes", member_id)
                    remarks.append(("Non-applicable:HBD - No diabetes", current_date.strftime("%Y-%m-%d")))
                elif age < 18 or age > 75:
                    logger.info("Member_id=%s non-applicable for HBD: Age criteria not met", member_id)
                    remarks.append(("Non-applicable:HBD - Age criteria not met", current_date.strftime("%Y-%m-%d")))
                elif pd.notna(hba1c_date) and (current_date - hba1c_date).days <= 365:
                    if pd.isna(hba1c_value) or str(hba1c_value).strip() == "":
                        logger.info("Member_id=%s non-compliant with HBD: A1c screening hit but no result", member_id)
                        remarks.append(("Non-compliant:HBD - A1c screening hit but no result", current_date.strftime("%Y-%m-%d")))
                    else:
                        try:
                            hba1c_float = float(hba1c_value)
                            if hba1c_float < 8.0:
                                logger.info("Member_id=%s compliant with HBD: HbA1c < 8%%", member_id)
                                remarks.append(("Compliant:HBD", current_date.strftime("%Y-%m-%d")))
                            else:
                                logger.info("Member_id=%s non-compliant with HBD: HbA1c >= 8%%", member_id)
                                remarks.append(("Non-compliant:HBD - HbA1c >= 8%", current_date.strftime("%Y-%m-%d")))
                        except (ValueError, TypeError):
                            logger.info("Member_id=%s non-compliant with HBD: Invalid HbA1c value", member_id)
                            remarks.append(("Non-compliant:HBD - Invalid HbA1c", current_date.strftime("%Y-%m-%d")))
                elif pd.notna(hba1c_value) and str(hba1c_value).strip() != "":
                    logger.info("Member_id=%s non-compliant with HBD: No date of service", member_id)
                    remarks.append(("Non-compliant:HBD - ASNDOS:No date of service", current_date.strftime("%Y-%m-%d")))
                else:
                    logger.info("Member_id=%s non-compliant with HBD: Test date out of range", member_id)
                    remarks.append(("Non-compliant:HBD - Test date out of range", current_date.strftime("%Y-%m-%d")))

            elif measure_type == "CBP":
                logger.info("Applying CBP compliance checks for member_id=%s", member_id)
                bp_date = pd.to_datetime(row.get("BP_DOS"), errors='coerce')
                bp = str(row.get("BP", "140/90")).strip()
                if bp.upper() == 'NA':
                    bp = "140/90"
                try:
                    bp_values = bp.split('/')
                    systolic = float(bp_values[0]) if len(bp_values) > 0 and bp_values[0].strip() else 140
                    diastolic = float(bp_values[1]) if len(bp_values) > 1 and bp_values[1].strip() else 90
                except (ValueError, IndexError):
                    systolic, diastolic = 140, 90
                hypertension = str(row.get("Hypertension", "")).strip().lower() == "yes"
                logger.info("CBP details - BP DOS: %s, BP: %s (Systolic: %s, Diastolic: %s), Hypertension: %s",
                            bp_date, bp, systolic, diastolic, hypertension)
                if row['Hospice_Pallitative'] in ["Yes", "YES"]:
                    logger.info("Member_id=%s excluded from CBP: Hospice Care", member_id)
                    remarks.append(("Exclusion:CBP - Hospice Care", current_date.strftime("%Y-%m-%d")))
                elif pd.isna(dob):
                    logger.info("Member_id=%s excluded from CBP: Invalid DOB", member_id)
                    remarks.append(("Exclusion:CBP - Invalid DOB", current_date.strftime("%Y-%m-%d")))
                elif pd.notna(bp_date) and (current_date - bp_date).days <= 365 and 18 <= age <= 85:
                    if systolic < 140 and diastolic < 90:
                        if hypertension:
                            logger.info("Member_id=%s compliant with CBP: BP in range with hypertension", member_id)
                            remarks.append((f"Representative BP {bp} value in the valid range (HEDIS valid range)", current_date.strftime("%Y-%m-%d")))
                        else:
                            logger.info("Member_id=%s non-compliant with CBP: No hypertension", member_id)
                            remarks.append(("Non-compliant:CBP - Hypertension:No", current_date.strftime("%Y-%m-%d")))
                    elif systolic >= 140:
                        logger.info("Member_id=%s non-compliant with CBP: Systolic not in range", member_id)
                        remarks.append((f"Non-compliant:CBP - Systolic not in range, representative BP: {bp}", current_date.strftime("%Y-%m-%d")))
                    elif diastolic >= 90:
                        logger.info("Member_id=%s non-compliant with CBP: Diastolic not in range", member_id)
                        remarks.append((f"Non-compliant:CBP - Diastolic not in range, representative BP: {bp}", current_date.strftime("%Y-%m-%d")))
                else:
                    logger.info("Member_id=%s non-compliant with CBP: No recent BP", member_id)
                    remarks.append(("Non-compliant:CBP - No recent BP", current_date.strftime("%Y-%m-%d")))

            elif measure_type == "BPD":
                logger.info("Applying BPD compliance checks for member_id=%s", member_id)
                bp_date = pd.to_datetime(row.get("BP_DOS"), errors='coerce')
                bp = str(row.get("BP", "140/90")).strip()
                if bp.upper() == 'NA':
                    bp = "140/90"
                try:
                    bp_values = bp.split('/')
                    systolic = float(bp_values[0]) if len(bp_values) > 0 and bp_values[0].strip() else 140
                    diastolic = float(bp_values[1]) if len(bp_values) > 1 and bp_values[1].strip() else 90
                except (ValueError, IndexError):
                    systolic, diastolic = 140, 90
                logger.info("BPD details - BP DOS: %s, BP: %s (Systolic: %s, Diastolic: %s)", bp_date, bp, systolic, diastolic)
                has_diabetes = has_diabetes_status(row, "BPD", idx)
                if row['Hospice_Pallitative'] in ["Yes", "YES"]:
                    logger.info("Member_id=%s excluded from BPD: Hospice Care", member_id)
                    remarks.append(("Exclusion:BPD - Hospice Care", current_date.strftime("%Y-%m-%d")))
                elif pd.isna(dob):
                    logger.info("Member_id=%s excluded from BPD: Invalid DOB", member_id)
                    remarks.append(("Exclusion:BPD - Invalid DOB", current_date.strftime("%Y-%m-%d")))
                elif pd.notna(bp_date) and (current_date - bp_date).days <= 365 and 18 <= age <= 75:
                    if not has_diabetes:
                        logger.info("Member_id=%s non-applicable for BPD: No diabetes", member_id)
                        remarks.append(("Non-applicable:BPD - No diabetes found", current_date.strftime("%Y-%m-%d")))
                    elif has_diabetes and systolic < 140 and diastolic < 90:
                        logger.info("Member_id=%s compliant with BPD: BP in range with diabetes", member_id)
                        remarks.append((f"Representative BP {bp} value in the valid range (HEDIS valid range)", current_date.strftime("%Y-%m-%d")))
                    elif systolic >= 140:
                        logger.info("Member_id=%s non-compliant with BPD: Systolic not in range", member_id)
                        remarks.append((f"Non-compliant:BPD - Systolic not in range, representative BP: {bp}", current_date.strftime("%Y-%m-%d")))
                    elif diastolic >= 90:
                        logger.info("Member_id=%s non-compliant with BPD: Diastolic not in range", member_id)
                        remarks.append((f"Non-compliant:BPD - Diastolic not in range, representative BP: {bp}", current_date.strftime("%Y-%m-%d")))
                else:
                    logger.info("Member_id=%s non-compliant with BPD: No recent BP", member_id)
                    remarks.append(("Non-compliant:BPD - No recent BP", current_date.strftime("%Y-%m-%d")))

            elif measure_type == "EED":
                logger.info("Applying EED compliance checks for member_id=%s", member_id)
                exam_date = pd.to_datetime(row.get("EYE_EXAM_Date"), errors='coerce')
                has_seen_optometrist = str(row.get('HAS_SEEN_OPTHOMETERIS', '')).strip().lower()
                exam_both_eyes = str(row.get('EYE_EXAM_CONDUCTED_ON_BOTH_EYES', '')).strip().lower()
                exam_right_eye = str(row.get('EYE_EXAM_CONDUCTED_ON_RIGHT_EYE', '')).strip().lower()
                exam_left_eye = str(row.get('EYE_EXAM_CONDUCTED_ON_LEFT_EYE', '')).strip().lower()
                bilateral_enucleation = str(row.get('Bilateral_eye_enucleation', '')).strip().lower()
                bilateral_enucleation_dos = parse_date(row.get('Bilateral_eye_enucleation_Dos', None))
                retinal_exam_result = str(row.get('Retinal_or_dilated_eye_exam_result', '')).strip().lower()
                logger.info("EED details - Exam Date: %s, Seen Optometrist: %s, Both Eyes: %s, Right Eye: %s, Left Eye: %s, Bilateral Enucleation: %s, Bilateral DOS: %s, Retinal Result: %s",
                            exam_date, has_seen_optometrist, exam_both_eyes, exam_right_eye, exam_left_eye,
                            bilateral_enucleation, bilateral_enucleation_dos, retinal_exam_result)

                if row['Hospice_Pallitative'] in ["Yes", "YES"]:
                    logger.info("Member_id=%s excluded from EED: Hospice Care", member_id)
                    remarks.append(("Exclusion:EED - Hospice Care", current_date.strftime("%Y-%m-%d")))
                    continue
                if pd.isna(dob):
                    logger.info("Member_id=%s excluded from EED: Invalid DOB", member_id)
                    remarks.append(("Exclusion:EED - Invalid DOB", current_date.strftime("%Y-%m-%d")))
                    continue
                if age < 18 or age > 75:
                    logger.info("Member_id=%s non-applicable for EED: Age criteria not met", member_id)
                    remarks.append(("Non-applicable:EED - Age criteria not met", current_date.strftime("%Y-%m-%d")))
                    continue

                if has_seen_optometrist in ["no", ""] or pd.isna(row.get('HAS_SEEN_OPTHOMETERIS')):
                    logger.info("Member_id=%s non-compliant with EED: No optometrist visit", member_id)
                    remarks.append(("Non compliant - member didn't receive the appropriate eye exam", current_date.strftime("%Y-%m-%d")))
                    continue

                has_diabetes = has_seen_optometrist in ["yes", "y", "true", "1"]
                if not has_diabetes:
                    has_diabetes = has_diabetes_status(row, "EED", idx)
                if not has_diabetes:
                    logger.info("Member_id=%s non-applicable for EED: No diabetes or optometrist visit", member_id)
                    remarks.append(("Non-applicable:EED - No diabetes or optometrist visit", current_date.strftime("%Y-%m-%d")))
                    continue

                bilateral_missing = bilateral_enucleation in ["no", ""] or pd.isna(row.get('Bilateral_eye_enucleation'))
                if bilateral_missing and pd.notna(bilateral_enucleation_dos):
                    logger.info("Member_id=%s needs verification for EED: Bilateral enucleation status", member_id)
                    remarks.append(("Verify bilateral eye enucleation status", current_date.strftime("%Y-%m-%d")))
                    continue

                if bilateral_enucleation == "yes":
                    logger.info("Member_id=%s compliant with EED: Bilateral eye exam", member_id)
                    remarks.append(("Compliant - bilateral eye exam", current_date.strftime("%Y-%m-%d")))
                    continue
                if pd.notna(bilateral_enucleation_dos):
                    logger.info("Member_id=%s excluded from EED: Bilateral eye exam", member_id)
                    remarks.append(("Exclusion - bilateral eye exam", current_date.strftime("%Y-%m-%d")))
                    continue

                if exam_both_eyes in ["no", ""] or pd.isna(row.get('EYE_EXAM_CONDUCTED_ON_BOTH_EYES')):
                    logger.info("Member_id=%s non-compliant with EED: Eye exam details not found", member_id)
                    remarks.append(("Non compliant - eye exam details not found", current_date.strftime("%Y-%m-%d")))
                    continue

                right_eye_missing = exam_right_eye in ["no", "no evidence", ""] or pd.isna(row.get('EYE_EXAM_CONDUCTED_ON_RIGHT_EYE'))
                left_eye_missing = exam_left_eye in ["no", "no evidence", ""] or pd.isna(row.get('EYE_EXAM_CONDUCTED_ON_LEFT_EYE'))
                if right_eye_missing and left_eye_missing:
                    logger.info("Member_id=%s non-compliant with EED: No eye exam details for both eyes", member_id)
                    remarks.append(("Non compliant - eye exam details on right and left eyes not found", current_date.strftime("%Y-%m-%d")))
                    continue

                if right_eye_missing:
                    logger.info("Member_id=%s non-compliant with EED: No eye exam details for right eye", member_id)
                    remarks.append(("Non compliant - eye exam details on right eye not found", current_date.strftime("%Y-%m-%d")))
                    continue
                if left_eye_missing:
                    logger.info("Member_id=%s non-compliant with EED: No eye exam details for left eye", member_id)
                    remarks.append(("Non compliant - no evidence of eye exam details on left eye", current_date.strftime("%Y-%m-%d")))
                    continue

                if retinal_exam_result and retinal_exam_result != "no":
                    logger.info("Member_id=%s compliant with EED: Retinal exam result present", member_id)
                    remarks.append(("Compliant:EED", current_date.strftime("%Y-%m-%d")))
                    continue

                if pd.notna(exam_date):
                    if (current_date - exam_date).days > 365:
                        logger.info("Member_id=%s non-compliant with EED: Eye exam date out of timeframe", member_id)
                        remarks.append(("Non compliant - eye exam date is out of timeframes", current_date.strftime("%Y-%m-%d")))
                        continue

                logger.info("Member_id=%s non-compliant with EED: No eye exam found", member_id)
                remarks.append(("Non compliant - no eye exam found, the member is non-compliant", current_date.strftime("%Y-%m-%d")))

            elif measure_type == "COL":
                logger.info("Applying COL compliance checks for member_id=%s", member_id)
                if row['Hospice_Pallitative'] in ["Yes", "YES"]:
                    logger.info("Member_id=%s excluded from COL: Hospice Care", member_id)
                    remarks.append(("Exclusion:COL - Hospice Care", current_date.strftime("%Y-%m-%d")))
                    continue
                if pd.isna(dob):
                    logger.info("Member_id=%s excluded from COL: Invalid DOB", member_id)
                    remarks.append(("Exclusion:COL - Invalid DOB", current_date.strftime("%Y-%m-%d")))
                    continue
                if not (50 <= age <= 75):
                    logger.info("Member_id=%s excluded from COL: Age criteria not met", member_id)
                    remarks.append(("Exclusion:COL - Age criteria not met", current_date.strftime("%Y-%m-%d")))
                    continue

                total_colectomy = str(row.get("Total Colectomy", "")).strip().lower()
                total_colectomy_dos = parse_date(row.get("colectomy_DOS", None))
                logger.info("COL details - Total Colectomy: %s, Total Colectomy DOS: %s", total_colectomy, total_colectomy_dos)
                if total_colectomy == "yes" or pd.notna(total_colectomy_dos):
                    logger.info("Member_id=%s excluded from COL: Total Colectomy", member_id)
                    remarks.append(("Exclusion:COL - Total Colectomy", current_date.strftime("%Y-%m-%d")))
                    continue

                col_tests = [
                    ("colonoscopy", pd.to_datetime(row.get("colonoscopy_DOS"), errors='coerce'), colonoscopy_valid_from),
                    ("ct colonoscopy", pd.to_datetime(row.get("CT_colonoscopy_DOS"), errors='coerce'), ct_valid_from),
                    ("fit", pd.to_datetime(row.get("FIT_FOBT_DOS"), errors='coerce'), fit_valid_from),
                    ("stool dna", pd.to_datetime(row.get("Stool_DNA_DOS"), errors='coerce'), stool_dna_valid_from),
                    ("flexible sigmoidoscopy", pd.to_datetime(row.get("Flexible_Sigmoidoscopy_Actual_date", row.get("Flexiable_Sigmoidscopy_Actual_date")), errors='coerce'), sigmoidoscopy_valid_from)
                ]
                logger.info("COL screening tests: %s", [(test_name, date, valid_from) for test_name, date, valid_from in col_tests])

                valid_screenings = []
                for test_name, date, valid_from in col_tests:
                    if pd.notna(date) and date >= valid_from:
                        logger.info("Member_id=%s has valid %s screening on %s", member_id, test_name, date)
                        valid_screenings.append(test_name)

                colonoscopy_status = str(row.get("colonoscopy", "")).strip().lower()
                colonoscopy_date = col_tests[0][1]
                colonoscopy_out_of_date = pd.isna(colonoscopy_date) or (pd.notna(colonoscopy_date) and colonoscopy_date < colonoscopy_valid_from)
                colonoscopy_empty_or_no = colonoscopy_status in ["no", "", "none"] or pd.isna(row.get("colonoscopy"))
                logger.info("Colonoscopy status - Status: %s, Date: %s, Out of Date: %s, Empty/No: %s",
                            colonoscopy_status, colonoscopy_date, colonoscopy_out_of_date, colonoscopy_empty_or_no)

                if (total_colectomy in ["no", "", "none"] or pd.isna(row.get("Total Colectomy"))) and pd.isna(total_colectomy_dos) and (colonoscopy_out_of_date or colonoscopy_empty_or_no):
                    if valid_screenings and any(test_name != "colonoscopy" for test_name in valid_screenings):
                        screening_list = ", ".join(valid_screenings)
                        logger.info("Member_id=%s compliant with COL: Valid screenings - %s", member_id, screening_list)
                        remarks.append((f"Compliant:COL - Valid colorectal screening completed: {screening_list}", current_date.strftime("%Y-%m-%d")))
                        continue
                elif valid_screenings:
                    screening_list = ", ".join(valid_screenings)
                    logger.info("Member_id=%s compliant with COL: Valid screenings - %s", member_id, screening_list)
                    remarks.append((f"Compliant:COL - Valid colorectal screening completed: {screening_list}", current_date.strftime("%Y-%m-%d")))
                    continue

                colonoscopy_status = str(row.get("colonoscopy", "")).strip().lower()
                ct_colonoscopy_status = str(row.get("CT_colonoscopy", "")).strip().lower()
                fit_status = str(row.get("FIT_FOBT", "")).strip().lower()
                stool_dna_status = str(row.get("Stool_DNA", "")).strip().lower()
                sigmoidoscopy_status = str(row.get("Flexible_Sigmoidoscopy", row.get("Flexiable_Sigmoidscopy", ""))).strip().lower()
                logger.info("Screening statuses - Colonoscopy: %s, CT Colonoscopy: %s, FIT: %s, Stool DNA: %s, Sigmoidoscopy: %s",
                            colonoscopy_status, ct_colonoscopy_status, fit_status, stool_dna_status, sigmoidoscopy_status)

                def others_empty_or_no(exclude_test):
                    tests = [
                        ("colonoscopy", colonoscopy_status),
                        ("ct colonoscopy", ct_colonoscopy_status),
                        ("fit", fit_status),
                        ("stool dna", stool_dna_status),
                        ("flexible sigmoidoscopy", sigmoidoscopy_status)
                    ]
                    result = all(status in ["no", "", "none"] or pd.isna(row.get(test_name)) for test_name, status in tests if test_name != exclude_test)
                    logger.info("Checking if other screenings are empty for %s (excluding %s): %s", member_id, exclude_test, result)
                    return result

                for test_name, date, valid_from in col_tests:
                    test_status = {
                        "colonoscopy": colonoscopy_status,
                        "ct colonoscopy": ct_colonoscopy_status,
                        "fit": fit_status,
                        "stool dna": stool_dna_status,
                        "flexible sigmoidoscopy": sigmoidoscopy_status
                    }[test_name]
                    if test_status == "yes" and (pd.isna(date) or date < valid_from) and others_empty_or_no(test_name):
                        logger.info("Member_id=%s non-compliant with COL: %s screening not within timeframe", member_id, test_name)
                        remarks.append((f"Non-compliant:COL - {test_name}: No valid screening test within timeframe", current_date.strftime("%Y-%m-%d")))
                        break
                else:
                    logger.info("Member_id=%s non-compliant with COL: No specific screening failure identified", member_id)
                    remarks.append(("Non-compliant:COL", current_date.strftime("%Y-%m-%d")))

            elif measure_type == "CCS":
                gender=gender.strip().lower()
                logger.info("Applying CCS compliance checks for member_id=%s", member_id)
                pap_date = pd.to_datetime(row.get("PAP_test_DOS"), errors='coerce')
                hpv_date = pd.to_datetime(row.get("HPV_test_DOS"), errors='coerce')
                hysterectomy = str(row.get("Hysterectomy", "no")).strip().lower() == "yes"
                logger.info("CCS details - PAP DOS: %s, HPV DOS: %s, Hysterectomy: %s", pap_date, hpv_date, hysterectomy)
                if row['Hospice_Pallitative'] in ["Yes", "YES"]:
                    logger.info("Member_id=%s excluded from CCS: Hospice Care", member_id)
                    remarks.append(("Exclusion:CCS - Hospice Care", current_date.strftime("%Y-%m-%d")))
                elif pd.isna(dob):
                    logger.info("Member_id=%s excluded from CCS: Invalid DOB", member_id)
                    remarks.append(("Exclusion:CCS - Invalid DOB", current_date.strftime("%Y-%m-%d")))
                elif 21 <= age <= 64 and gender == "female":
                    if hysterectomy:
                        logger.info("Member_id=%s excluded from CCS: Hysterectomy", member_id)
                        remarks.append(("Exclusion:CCS - Hysterectomy", current_date.strftime("%Y-%m-%d")))
                    elif pd.notna(pap_date) and (current_date - pap_date).days <= 365 * 2:
                        logger.info("Member_id=%s compliant with CCS: PAP test within 2 years", member_id)
                        remarks.append(("Compliant:CCS - Pap test", current_date.strftime("%Y-%m-%d")))
                    elif pd.notna(hpv_date) and (current_date - hpv_date).days <= 365 * 4:
                        logger.info("Member_id=%s compliant with CCS: HPV test within 4 years", member_id)
                        remarks.append(("Compliant:CCS - HPV test", current_date.strftime("%Y-%m-%d")))
                    else:
                        logger.info("Member_id=%s non-compliant with CCS: No valid PAP or HPV test", member_id)
                        remarks.append(("Non-compliant:CCS", current_date.strftime("%Y-%m-%d")))
                else:
                    logger.info("Member_id=%s excluded from CCS: Age/Gender criteria not met", member_id)
                    remarks.append(("Exclusion:CCS - Age/Gender criteria not met", current_date.strftime("%Y-%m-%d")))

            elif measure_type == "LSD":
                logger.info("Applying LSD compliance checks for member_id=%s", member_id)
                if row['Hospice_Pallitative'] in ["Yes", "YES"]:
                    logger.info("Member_id=%s excluded from LSD: Hospice Care", member_id)
                    remarks.append(("Exclusion:LSD - Hospice Care", current_date.strftime("%Y-%m-%d")))
                elif pd.isna(dob):
                    logger.info("Member_id=%s excluded from LSD: Invalid DOB", member_id)
                    remarks.append(("Exclusion:LSD - Invalid DOB", current_date.strftime("%Y-%m-%d")))
                elif age <= 2:
                    lead_screening = str(row.get("Lead_Screening", "")).strip().lower() == "yes"
                    logger.info("LSD details - Lead Screening: %s", lead_screening)
                    if lead_screening:
                        logger.info("Member_id=%s compliant with LSD: Lead screening completed", member_id)
                        remarks.append(("Compliant:LSD", current_date.strftime("%Y-%m-%d")))
                    else:
                        logger.info("Member_id=%s non-compliant with LSD: No lead screening", member_id)
                        remarks.append(("Non-compliant:LSD", current_date.strftime("%Y-%m-%d")))
                else:
                    logger.info("Member_id=%s excluded from LSD: Age criteria not met", member_id)
                    remarks.append(("Exclusion:LSD - Age criteria not met", current_date.strftime("%Y-%m-%d")))

            elif measure_type == "PPC":
                gender=gender.strip().lower()
                logger.info("Applying PPC compliance checks for member_id=%s", member_id)
                if row['Hospice_Pallitative'] in ["Yes", "YES"]:
                    logger.info("Member_id=%s excluded from PPC: Hospice Care", member_id)
                    remarks.append(("Exclusion:PPC - Hospice Care", current_date.strftime("%Y-%m-%d")))
                elif pd.isna(dob):
                    logger.info("Member_id=%s excluded from PPC: Invalid DOB", member_id)
                    remarks.append(("Exclusion:PPC - Invalid DOB", current_date.strftime("%Y-%m-%d")))
                elif gender == "female":
                    delivery = str(row.get("Did_Member_Have_Delivery", "")).strip().lower() == "yes"
                    postpartum_care = str(row.get("Was_Postpartum_Care_Provided", "")).strip().lower() == "yes"
                    logger.info("PPC details - Delivery: %s, Postpartum Care: %s", delivery, postpartum_care)
                    if delivery and postpartum_care:
                        logger.info("Member_id=%s compliant with PPC: Delivery and postpartum care provided", member_id)
                        remarks.append(("Compliant:PPC", current_date.strftime("%Y-%m-%d")))
                    elif delivery:
                        logger.info("Member_id=%s non-compliant with PPC: No postpartum care", member_id)
                        remarks.append(("Non-compliant:PPC - No postpartum care", current_date.strftime("%Y-%m-%d")))
                    else:
                        logger.info("Member_id=%s non-applicable for PPC: No delivery", member_id)
                        remarks.append(("Non-applicable:PPC - No delivery", current_date.strftime("%Y-%m-%d")))
                else:
                    logger.info("Member_id=%s excluded from PPC: Gender criteria not met", member_id)
                    remarks.append(("Exclusion:PPC - Gender criteria not met", current_date.strftime("%Y-%m-%d")))

            else:
                logger.warning("Member_id=%s in %s: No compliance logic defined", member_id, measure_type)
                remarks.append(("No logic defined", current_date.strftime("%Y-%m-%d")))

        except Exception as e:
            logger.error("Error processing row %s for member_id=%s in measure %s: %s", idx, member_id, measure_type, str(e))
            remarks.append((f"Error:{measure_type} - Processing error: {str(e)}", current_date.strftime("%Y-%m-%d")))
    # print(f"\nLOG3: {sorted(df.columns)}\n")
    if len(remarks) != len(df):
        logger.error("Length mismatch - Remarks: %s, DataFrame: %s", len(remarks), len(df))
        raise ValueError(f"Length of remarks ({len(remarks)}) does not match DataFrame length ({len(df)})")

    remark_col = f'Remark_{measure_type}'
    logger.info("Assigning remarks to column %s for %s", remark_col, measure_type)
    df[[remark_col, 'Updated']] = pd.DataFrame(remarks, index=df.index)

    # print(f"\nLOG4: {sorted(df.columns)}\n")
    
    #AK & SYND commented below line on 2ndJune; Reason: Name filed is comning balnk/NR/NA for all measures , as below statement is dropping the Name column. "No need to drop any column here"
    # df.drop(columns=['DOB', 'Gender', 'Hospice_Pallitative', 'Name', 'Provider', 'Diabetes', 'Posg_diabetes', 'Posg diabetes', 'Posg_diat'], errors='ignore', inplace=True)

    # print(f"\nLOG5: {sorted(df.columns)}\n")
    
    logger.info("Completed compliance checks for %s, final DataFrame shape: %s", measure_type, df.shape)
    return df

def apply_compliance_to_df(df, member_df=None):
    """
    Process a single dataframe with compliance checks.
    """
    logger.info("Called with DataFrame of shape %s, member_df shape: %s", df.shape, member_df.shape if member_df is not None else "None")
    measure_type = detect_measure_type(df)
    if member_df is not None:
        logger.info("Merging member_df with columns: %s", list(member_df.columns))
        df = merge_dob(df, member_df)
    result_df = apply_ncqa_compliance_checks(df, measure_type)
    logger.info("Completed compliance processing for measure %s, returning DataFrame of shape %s", measure_type, result_df.shape)
    return result_df

def process_ncqa_hedis_2024(member_df=pd.DataFrame(), initialize_dataframes=True):
    """
    Process multiple dataframes for NCQA HEDIS 2024 compliance.
    """
    logger.info("Called with initialize_dataframes=%s, member_df shape: %s", initialize_dataframes, member_df.shape)
    if initialize_dataframes:
        logger.info("Initializing sample DataFrames for testing")
        df_bcs = pd.DataFrame(columns=['Member_id', 'Mammogram_DOS'])
        df_bcs.loc[0] = [4321, '2021-01-01']
        df_hbd = pd.DataFrame(columns=['Member_id', 'HbA1c_DOS', 'HbA1c_Result'])
        df_hbd.loc[0] = [4321, '2022-06-01', 7.5]
        df_cbp = pd.DataFrame(columns=['Member_id', 'BP_DOS', 'Hypertension'])
        df_cbp.loc[0] = [4321, '2022-06-01', 'yes']
        df_bpd = pd.DataFrame(columns=['Member_id', 'BP_DOS'])
        df_bpd.loc[0] = [4321, '2022-06-01']
        df_eed = pd.DataFrame(columns=['Member_id', 'EYE_EXAM_Date'])
        df_eed.loc[0] = [4321, '2022-06-01']
        df_col = pd.DataFrame(columns=['Member_id', 'colonoscopy_DOS'])
        df_col.loc[0] = [4321, '2020-01-01']
        df_ccs = pd.DataFrame(columns=['Member_id', 'PAP_test_DOS'])
        df_ccs.loc[0] = [4321, '2021-01-01']
        df_lsd = pd.DataFrame()
        df_ppc = pd.DataFrame()

        for df, cols in [
            (df_bcs, ['Mammogram_DOS', 'Bilateral_Mastectomy_DOS', 'Unilateral_Mastectomy_R_DOS', 'Unilateral_Mastectomy_L_DOS']),
            (df_hbd, ['ReHbA1c_DC', 'HbA1c_DC', 'HbA1c_DOS']),
            (df_cbp, ['BP_DOS']),
            (df_bpd, ['BP_DOS']),
            (df_eed, ['EYE_EXAM_Date', 'Bilateral_eye_DOS']),
            (df_col, ['colectomy_DOS', 'colonoscopy_DOS', 'CT_colonoscopy_DOS', 'FIT_FOBT_DOS', 'Stool_DNA_DOS', 'Flexiable_Sigmoidscopy_Actual_date']),
            (df_ccs, ['HPV_test_DOS', 'PAP_test_DOS']),
            (df_lsd, ['Lead_Screening_DOS']),
            (df_ppc, ['Delivery_DOS', 'Postpartum_Care_DOS']),
            (member_df, ['DOB'])
        ]:
            for col in cols:
                if col in df.columns:
                    logger.info("Parsing dates in column %s for DataFrame with columns: %s", col, list(df.columns))
                    df[col] = df[col].apply(parse_date)

        logger.info("Applying compliance checks to all measures")
        df_bcs = apply_compliance_to_df(df_bcs, member_df)
        df_hbd = apply_compliance_to_df(df_hbd, member_df)
        df_cbp = apply_compliance_to_df(df_cbp, member_df)
        df_bpd = apply_compliance_to_df(df_bpd, member_df)
        df_eed = apply_compliance_to_df(df_eed, member_df)
        df_col = apply_compliance_to_df(df_col, member_df)
        df_ccs = apply_compliance_to_df(df_ccs, member_df)
        df_lsd = apply_compliance_to_df(df_lsd, member_df)
        df_ppc = apply_compliance_to_df(df_ppc, member_df)

        logger.info("Completed processing all measures, returning DataFrames")
        return df_bcs, df_hbd, df_cbp, df_bpd, df_eed, df_col, df_ccs, df_lsd, df_ppc, member_df
    logger.info("initialize_dataframes=False, returning None for all measures except member_df")
    return None, None, None, None, None, None, None, None, None, member_df