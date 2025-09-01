import pandas as pd
import streamlit as st
import pyodbc
import fitz
import os
from datetime import datetime                             
from dotenv import load_dotenv
from compliance import apply_compliance_to_df, parse_date, merge_dob, apply_ncqa_compliance_checks
from utils import database
import json
import logging
from utils.spec_modal_utils import load_measure_spec, render_spec_modal
from itertools import zip_longest

# Load environment variables
load_dotenv()

# UI Configuration
st.set_page_config(layout="wide", page_title="HEDISAbstractor.AI")

SCRIPT='ReviewMember'

server_name= os.getenv('HEDIS_SERVER')
database_name=os.getenv('HEDIS_DATABASE')

all_measures=["BCS", "CBP", "HBD", "BPD", "EED", "CCS", "COL"] #,'LSD','PPC'

# Database Configuration
db_config = {
    'Driver': os.getenv('HEDIS_DRIVER', 'ODBC Driver 17 for SQL Server'),
    'Server': server_name,
    'Database': database_name,
    'Trusted_Connection': os.getenv('HEDIS_TRUSTED_CONNECTION', 'yes')
}

# Validate db_config
if not db_config['Server'] or not db_config['Database']:
    st.error("Missing HEDIS_SERVER or HEDIS_DATABASE in .env file.")
    st.stop()

# CSS for UI
st.markdown(
    """
    <style>
    /* UI Import Google Fonts for better typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* UI Global font and base styles */
    .stApp {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #FFFFFF 0%, #FFFFFF 100%);
        min-height: 100vh;
    }
    
    /* UI Main content area with glassmorphism effect */
    .main .block-container {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
        padding: 2rem;
        margin-top: 2rem;
    }
    
    /* UI Enhanced user greeting container */
    .user-greeting-container {
        position: fixed; 
        top: 0px;
        height: 80px;
        right: 0; 
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        display: flex; 
        justify-content: flex-end; 
        align-items: center; 
        padding: 15px 25px;
        z-index: 1000; 
        width: 100%; 
        box-sizing: border-box;
    }
    
    /* UI Enhanced user greeting with animation */
    .user-greeting {
        display: flex;
        align-items: center;
        font-size: 16px;
        font-weight: 600;
        color: #333;
        margin-right: 80px;
        transition: all 0.3s ease;
        padding: 8px 16px;
        border-radius: 25px;
        background: linear-gradient(45deg, #fb4e0b, #ff6b35);
        color: white;
        box-shadow: 0 4px 15px rgba(251, 78, 11, 0.3);
    }
    
    .user-greeting:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(251, 78, 11, 0.4);
    }
    
    .user-greeting img {
        width: 24px;
        height: 24px;
        margin-right: 12px;
        filter: brightness(0) invert(1);
    }
    
    /* UI Enhanced title with gradient and animation */
    .title {
        font-size: 32px;
        font-weight: 700;
        color: white;
        padding: 10px;
        text-align: center;
        background: linear-gradient(135deg, #fb4e0b 0%, #ff6b35 100%);
        position: fixed;
        width: 78%;
        top: 82px;
        z-index: 9999;
        border-radius: 0 0 20px 20px;
        box-shadow: 0 8px 32px rgba(251, 78, 11, 0.4);
        backdrop-filter: blur(5px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        animation: slideDown 0.6s ease-out;
    }
    
    /* UI Title animation */
    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateY(-50px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .left { float: left; }
    .right { float: right; }
    .compliance-remark {
        font-size: 16px;
        font-weight: bold;
        color: #28a745; /* Green for Compliant */
        margin-top: 10px;
    }
    .non-compliant-remark {
        font-size: 16px;
        font-weight: bold;
        color: #dc3545; /* Red for Non-compliant */
        margin-top: 10px;
    }
    .status-badge {
        display: inline-block;
        padding: 2px 6px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
        margin-left: 5px;
        vertical-align: middle;
        cursor: pointer;
    }
    .status-compliant { background-color: #28a745; color: white; }
    .status-non-compliant { background-color: #dc3545; color: white; }
    .status-exclusion { background-color: #ffc107; color: black; }
    .tooltip {
        position: relative;
        display: inline-block;
    }
    .tooltip .tooltiptext {
        visibility: hidden;
        width: 200px;
        background-color: #555;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 5px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        margin-left: -100px;
        opacity: 0;
        transition: opacity 0.3s;
    }
    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }
    .modal {
        display: none;
        position: fixed;
        top: 30%;
        left: 65%;
        background-color: white;
        border: 1px solid #ccc;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        z-index: 10001;
        width: 500px;
        min-width: 300px;
        min-height: 200px;
        resize: both;
        overflow: auto;
    }
    .modal-header {
        background-color: #f1f1f1;
        padding: 10px;
        border-bottom: 1px solid #ddd;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .modal-content {
        padding: 20px;
        max-height: 70vh;
        overflow-y: auto;
    }
    .modal.show { display: block; }
    .page-input-container {
        position: fixed;
        top: 150px;
        right: 20px;
        z-index: 1000;
    }
    
    .stButton>button { border: none; }
    .stButton>button:hover { background-color: #f0f0f0; }
    .confirmation-modal {
        background-color: #f9f9f9;
        border: 1px solid #ccc;
        border-radius: 5px;
        padding: 15px;
        margin-top: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    .confirmation-modal-buttons {
        display: flex;
        gap: 10px;
        margin-top: 15px;
    }
    
    </style>
    """,
    unsafe_allow_html=True
)

# Header UI
st.markdown(
    """
    <div class="user-greeting-container">
        <div class="user-greeting">
            <img src="https://img.icons8.com/ios/452/user-male-circle.png" alt="user icon" />
            Hi, Ayush
        </div>
    </div>
    <div class="title">
        <span class="left">HEDISAbstractor.AI</span>
        <span class="right">EXL</span>
    </div>
    """,
    unsafe_allow_html=True
)

def get_confidence_score():
    confidence_score_json_path="temp_files\\confidence_score.json"
    with open(confidence_score_json_path,'r') as f:
        data= json.load(f)
    
    return data

# Utility Functions
def display_pdf_page(page_number, pdf_document):
    page = pdf_document[page_number]
    pix = page.get_pixmap()
    img = pix.tobytes("png")
    st.image(img, caption=f"Page {page_number + 1}", use_container_width =True)

def create_connection():
    conn_str = (
        f"DRIVER={db_config['Driver']};"
        f"SERVER={db_config['Server']};"
        f"DATABASE={db_config['Database']};"
        f"Trusted_Connection={db_config['Trusted_Connection']};"
    )
    #st.write(f"Connecting to database: {db_config['Database']} on server: {db_config['Server']}")
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SET DATEFORMAT ymd;")
        return conn
    except pyodbc.Error as e:
        st.error(f"Database connection error: {str(e)}", icon="🚨")
        return None

#AK
def get_member_id_via_pdf(file_name):
    file_name=file_name.strip(' ')

    file_name= file_name+'.pdf' if not file_name.endswith('.pdf') else file_name

    engine=database.get_db_connection(server_name,database_name)
    # file_name="ART_Testing_6688.pdf"
    query='select {} from {} where Pdf_filename='+f"'{file_name}' AND is_active=1"
    if engine:
        df= database.execute_query(st, engine=engine,query=query,table='file_info', get='FileID')
        pdf_member_id= '-9' if len(df) ==0 else df.loc[0,'FileID']
        return pdf_member_id  #FileID is in string format
    else:
        return None


def getdata(member_id, table):

    member_id= '-9' if len(member_id.strip(' ')) ==0 else member_id

    conn = create_connection()
    if conn:
        try:
            if table == 'memberinfo':
                a=member_id.split('.')[0].split('_')[-1]
            
                query = f"SELECT * FROM {table} WHERE member_id = {a} AND is_active IN (1)"
            else:
                query = f"SELECT * FROM {table} WHERE FileID = '{member_id}' AND is_active IN (1)"
            data = pd.read_sql(query, conn)
            print(f"{table}-- {len(data)}")
            if not data.empty:
                data['Member_id'] = data['Member_id'].astype(str)
            return data
        except pyodbc.Error as e:
            st.error(f"Error querying {table}: {e}", icon="🚨")
            return pd.DataFrame()
        finally:
            conn.close()
    return pd.DataFrame()

# AYU ----OLD getdata code can be commented out not requested
def getdata4(search_value, table, search_type='Member_id'):
    print(f"LOG2: {search_value}")

    if len(search_value.strip(' ')) == 0:
        st.warning(f"Please enter the value in search field for {search_type}")
        search_value =-1

    conn = create_connection()
    if conn:
        try:
            if search_type == 'File Name':
                query = f"SELECT FileID as Member_id, Pdf_filename as Name FROM file_info WHERE FileID ='{search_value}' AND is_active IN (1)"
            else:
                query = f"SELECT * FROM {table} WHERE Member_id = {search_value} AND is_active IN (1)"
            data = pd.read_sql(query, conn)
            if not data.empty:
                data['Member_id'] = data['Member_id'].astype(str)
            return data
        except pyodbc.Error as e:
            st.error(f"Error querying {table}: {e}", icon="🚨")
            return pd.DataFrame()
        finally:
            conn.close()
    return pd.DataFrame()


#AYU Generalized the function to fetch the data from file_info table
def getdata3(search_value, table, search_type='Member_id'):
    print(f"LOG2: {search_value}")

    if len(search_value.strip(' ')) == 0:
        st.warning(f"Please enter the value in search field for {search_type}")
        search_value =-1

    conn = create_connection()
    if conn:
        try:
            query = f"""
                        with cte as (
                        SELECT 
                            f.FileID AS Member_id, 
                            f.Pdf_filename AS [File Name], 
                            m.Name AS Name, 
                            m.Gender, 
                            m.DOB,
                            ROW_NUMBER() OVER (PARTITION BY f.FileID, f.Pdf_filename ORDER BY f.FileID) AS rn
                        FROM file_info f
                        RIGHT JOIN memberinfo m ON f.FileID = m.Member_id 
                        WHERE f.FileID = '{search_value}' 
                        AND m.is_active = 1 
                        AND f.is_active = 1
                    )

                    select
                        Member_id, [File Name], Name, Gender, DOB
                    FROM cte
                    where rn = 1;

                        """
                                        
            
            data = pd.read_sql(query, conn)
            if not data.empty:
                data['Member_id'] = data['Member_id'].astype(str)
                data=data.dropna() #dropping rows containing None
            return data
        except pyodbc.Error as e:
            st.error(f"Error querying {table}: {e}", icon="🚨")
            return pd.DataFrame()
        finally:
            conn.close()
    return pd.DataFrame()



def lookup_pdf_location(member_id):
    try:
        member_id = str(member_id)
        conn = create_connection()
        if not conn:
            return None
        
        #AK --  is_active IN (0,1) --> is_active IN (1)
        #AK--commented out -- not needed
        # query = f"SELECT Name FROM memberinfo WHERE Member_id = {member_id} AND is_active IN (1)"
        # print(f"memberinfo_QUERY: {query}")

        # member_data = pd.read_sql(query, conn)
        # if member_data.empty:
        #     st.warning(f"No member data found for Member ID: {member_id}")
        #     conn.close()
        #     return None
        # first_name = member_data.iloc[0]['Name'].split()[0]
        #st.write(f"lookup_pdf_location: {member_id}")
        query = """
        SELECT Pdf_location, Pdf_filename 
        FROM file_info 
        WHERE Pdf_filename= ? AND is_active = 1
        """
        print(f"\nPDF_LOOKUP_QUERY: {query}")
        result = pd.read_sql(query, conn, params=(member_id,))
        print(result)
        conn.close()
        if not result.empty:
            #AK--commented out -- not needed
            # for _, row in result.iterrows():
            #     pdf_location = row['Pdf_location'].rstrip('\\')
            #     pdf_filename = row['Pdf_filename'] 
            #     if pdf_filename.lower().startswith(first_name.lower()) and str(member_id) in pdf_filename:
            #         if not pdf_filename.lower().endswith('.pdf'):
            #             pdf_filename += '.pdf'
            #         # pdf_path = f"{pdf_location}\\{pdf_filename}"
            #         pdf_path=pdf_location
            #         if os.path.exists(pdf_path):
            #             return pdf_path
            # st.warning(f"No matching PDF filename found for Member ID: {member_id}")
            # return None

            #AK
            pdf_location = result.iloc[0]['Pdf_location']
            print(f"LOG_pdf: {pdf_location}")
            return pdf_location

        st.warning(f"No PDF location found for Member ID: {member_id}")
        return None
    except Exception as e:
        print(e)
        st.error(f"Error retrieving PDF location: {e}", icon="🚨")
        return None


#AYU modified to remove remarks and date columns
def create_new_dataframe(input_df, measure):
    non_page_columns = [col for col in input_df.columns if 'page' not in col.lower()]
    elements_to_remove = ["Name", "Member_id", "FileID", "is_active", "Remark","Updated_date","Insert_Date","Process","Confidence_Score"]
    display_columns = [col for col in non_page_columns if col not in elements_to_remove]
    Filter_col = [col for col in display_columns if 'remark' not in col.lower() and 'updated_date' not in col.lower()]

    if not Filter_col:
        st.warning(f"No displayable columns found for {measure}.")
        return pd.DataFrame()
    return input_df[Filter_col]

def create_new_dataframe_meminfo(df):
    #page_columns = [col for col in df.columns if 'page' in col]
    non_page_columns = [col for col in df.columns if 'page' not in col.lower() and col not in ["Member_id", "FileID", "is_active", "Remark","Updated_date","Insert_Date","Process","Confidence_Score"]]
                                                     
    return df[non_page_columns]

def page_df(input_df):
    page_columns = [col for col in input_df.columns if 'page' in col.lower()]
    new_df = input_df[page_columns]
    if not new_df.empty:
        return new_df.iloc[0].tolist()
    return []

DATE_COLUMNS = {
    "memberinfo": ["DOB"],
    "bcs": ["DateofService", "DateofScreening", "Mammogram DOS", "Bilateral Mastectomy DOS", "Unilateral Mastectomy R DOS", "Unilateral Mastectomy L DOS"],
    "cbp": ["BP DOS"],
    "hbd": ["DateofService", "DateofScreening"],
    "bpd": ["DateofService", "DateofScreening"],
    "eed": ["DateofService", "DateofScreening"],
    "ccs": ["DateofService", "DateofScreening"],
    "col": ["DateofService", "DateofScreening"],
}

VALUE_COLUMNS = {
    "cbp": ["BP"],
    "bpd": ["BP"],
    "bcs": ["Result", "Mammogram", "Bilateral Mastectomy", "Unilateral Mastectomy R", "Unilateral Mastectomy L"],
    "hbd": ["HbA1c"],
    "eed": ["EyeExamResult"],
    "ccs": ["ScreeningResult"],
    "col": ["ScreeningResult"],
}

MEASURE_CONFIG = {
    "memberinfo": {"date_cols": ["DOB"], "value_cols": []},
    "bcs": {"date_cols": ["DateofService", "DateofScreening", "Mammogram DOS", "Bilateral Mastectomy DOS", "Unilateral Mastectomy R DOS", "Unilateral Mastectomy L DOS"], "value_cols": ["Result", "Mammogram", "Bilateral Mastectomy", "Unilateral Mastectomy R", "Unilateral Mastectomy L"]},
    "cbp": {"date_cols": ["BP DOS"], "value_cols": ["BP"]},
    "hbd": {"date_cols": ["DateofService", "DateofScreening"], "value_cols": ["HbA1c"]},
    "bpd": {"date_cols": ["DateofService", "DateofScreening"], "value_cols": ["BP"]},
    "eed": {"date_cols": ["DateofService", "DateofScreening"], "value_cols": ["EyeExamResult"]},
    "ccs": {"date_cols": ["DateofService", "DateofScreening"], "value_cols": ["ScreeningResult"]},
    "col": {"date_cols": ["DateofService", "DateofScreening"], "value_cols": ["ScreeningResult"]},
}

prior_year=datetime.now().year-1
MEASUREMENT_YEAR=st.session_state.get('MY',prior_year)

logging.info(SCRIPT+": %r", f"Measurement Year puled from UI: {MEASUREMENT_YEAR}")
print(f"MEASUREMENT_YEAR:{MEASUREMENT_YEAR}")

CURRENT_DATE = datetime(2025, 5, 20)


def validate_and_parse_date(value, table, column, member_info_df=None):
    if table in DATE_COLUMNS and column in DATE_COLUMNS[table]:
        if not value or value.strip() == "":
            return None, "Missing date value"
        try:
            parsed_date = parse_date(value)
            if parsed_date is None:
                return None, "Invalid date format. Use MM/DD/YYYY or YYYY-MM-DD."
            
            # General validation for all date columns
            if parsed_date.year != MEASUREMENT_YEAR and column not in ["Mammogram DOS", "Bilateral Mastectomy DOS", "Unilateral Mastectomy R DOS", "Unilateral Mastectomy L DOS"]:
                return None, f"Date must be within the measurement year ({MEASUREMENT_YEAR})."

            # Specific validations for BCS measure
            if table == "bcs":
                # Mammogram DOS validations
                if column == "Mammogram DOS":
                    # Check if date is in the future compared to Member Info DOS or after measurement year
                    member_dos = member_info_df.get("DOB", None).iloc[0] if member_info_df is not None and not member_info_df.empty else None
                    member_dos = parse_date(member_dos) if member_dos else None
                    if member_dos and parsed_date > member_dos:
                        return None, "Invalid date."
                    if parsed_date.year > MEASUREMENT_YEAR:
                        return None, "Invalid date."
                    # Check if date is within two years of the measurement year (2024)
                    if not (MEASUREMENT_YEAR - 2 <= parsed_date.year <= MEASUREMENT_YEAR):
                        return None, f"Date must be within two years of {MEASUREMENT_YEAR}."
                
                # Mastectomy DOS validations
                if column in ["Bilateral Mastectomy DOS", "Unilateral Mastectomy R DOS", "Unilateral Mastectomy L DOS"]:
                    # Check if date is in the future compared to current date
                    if parsed_date > CURRENT_DATE:
                        return None, "Invalid date."

            return parsed_date.strftime('%Y-%m-%d'), None
        except (ValueError, TypeError) as e:
            return None, f"Invalid date format: {str(e)}."
    return value, None

def validate_value(value, table, column, original_value=None):
    if table in VALUE_COLUMNS and column in VALUE_COLUMNS[table]:
        if not value or value.strip() == "":
            if column == "Mammogram":
                return None, "For compliant, Mammogram must be Yes."
            if column in ["Bilateral Mastectomy", "Unilateral Mastectomy R", "Unilateral Mastectomy L"] and original_value and original_value.lower() == "yes":
                return None, "This may change member status from Exclusion."
            return None, "Missing value"
        if column == "BP":
            try:
                systolic, diastolic = map(int, value.split('/'))
                                                                      
                return f"{systolic}/{diastolic}", None
                                                                           
            except (ValueError, TypeError):
                return None, "Invalid BP format. Use XXX/YY (e.g., 120/80)."
        elif column in ["Result", "HbA1c", "EyeExamResult", "ScreeningResult"]:
            try:
                float(value)
                return value, None
            except (ValueError, TypeError):
                return None, f"Invalid {column} format. Must be numeric."
        elif column == "Mammogram":
            if value.lower() not in ["yes", "no"]:
                return None, "Invalid value. Use Yes/No."
            if value.lower() == "no":
                return value, "For compliant, Mammogram must be Yes."
            return value, None
        elif column in ["Bilateral Mastectomy", "Unilateral Mastectomy R", "Unilateral Mastectomy L"]:
            if value.lower() not in ["yes", "no"]:
                return None, "Invalid value. Use Yes/No."
            if value.lower() == "no" and original_value and original_value.lower() == "yes":
                return value, "This may change member status from Exclusion."
            return value, None
    return value, None
    
def update(member_id, column, value, table):
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            if table in DATE_COLUMNS and column in DATE_COLUMNS[table]:
                member_info_df = getdata(member_id, "memberinfo")
                value, error = validate_and_parse_date(value, table, column, member_info_df)
                if error:
                    st.error(f"Error updating {column}: {error}", icon="🚨")
                    return
            elif table in VALUE_COLUMNS and column in VALUE_COLUMNS[table]:
                value, error = validate_value(value, table, column)
                if error and error not in ["For compliant, Mammogram must be Yes.", "This may change member status from Exclusion."]:
                    st.error(f"Error updating {column}: {error}", icon="🚨")
                    return
            query = f"UPDATE {table} SET {column} = ?, updated_date = GETDATE() WHERE Member_id = ? and is_active=1" #AK -- added is_active
            cursor.execute(query, (value, str(member_id)))
            conn.commit()
        except pyodbc.Error as e:
            st.error(f"Error updating {table}: {str(e)}", icon="🚨")
        finally:
            conn.close()

# def check_field_compliance(member_id, measure, updated_data, member_info_df, field):
#     temp_data = updated_data.copy()
#     temp_data[field] = updated_data.get(field, '')
#     return check_compliance(member_id, measure, temp_data, member_info_df, focus_field=field)

def check_field_compliance(member_id, measure, updated_data, member_info_df, field):
    temp_data = updated_data.copy()
    temp_data[field] = updated_data.get(field, '')
    remark = check_compliance(member_id, measure, temp_data, member_info_df, focus_field=field)
    # Update the field Disposition status in session state
    if 'field_compliance' not in st.session_state:
        st.session_state['field_compliance'] = {}
    st.session_state['field_compliance'][f"{field}_{measure}"] = remark
    return remark


def on_field_change(member_id, measure, updated_data, member_info_df, field):
    """Callback function to handle field changes, update compliance, and enable submit button."""
    check_field_compliance(member_id, measure, updated_data, member_info_df, field)
    # Compute tooltip message for specific BCS fields
    if measure == "BCS":
        original_data = st.session_state['original_data'].get(measure, {})
        original_value = original_data.get(field, '')
        if field in updated_data:
            value = updated_data[field]
            if field in ["Mammogram", "Bilateral Mastectomy", "Unilateral Mastectomy R", "Unilateral Mastectomy L"]:
                _, tooltip_message = validate_value(value, measure.lower(), field, original_value)
                st.session_state['field_compliance'][f"tooltip_{field}_{measure}"] = tooltip_message if tooltip_message else ""
            elif field in ["Mammogram DOS", "Bilateral Mastectomy DOS", "Unilateral Mastectomy R DOS", "Unilateral Mastectomy L DOS"]:
                _, tooltip_message = validate_and_parse_date(value, measure.lower(), field, member_info_df)
                st.session_state['field_compliance'][f"tooltip_{field}_{measure}"] = tooltip_message if tooltip_message else ""
    st.session_state['has_changes'] = True


def check_compliance(member_id, measure, updated_data, member_info_df, focus_field=None):
        
    df = pd.DataFrame([updated_data])
    df['Member_id'] = member_id
    field_remarks = {}
    overall_remark = None
    final_remark = None

    try:
        # Validate value columns
        for col in MEASURE_CONFIG.get(measure.lower(), {}).get('value_cols', []):
            if col in updated_data:
                original_value = st.session_state['original_data'].get(measure, {}).get(col, '')
                value, error = validate_value(updated_data[col], measure.lower(), col, original_value)
                if error and error not in ["For compliant, Mammogram must be Yes.", "This may change member status from Exclusion."]:
                    field_remarks[col] = f"Non-compliant: {col} - {error}"
                    if focus_field == col:
                        final_remark = field_remarks[col]
                        break
                else:
                    if col == "BP":
                        try:
                            systolic, diastolic = value.split('/')
                            df['BP_systolic'] = systolic
                            df['BP_diastolic'] = diastolic
                            df['BP'] = value
                        except Exception:
                            df['BP'] = value
                    else:
                        df[col] = value
                    if measure.lower() == 'cbp' and value:
                        df['BP_present'] = True

        if final_remark:
            return final_remark

        # Validate date columns
        for col in MEASURE_CONFIG.get(measure.lower(), {}).get('date_cols', []):
            if col in updated_data:
                date_str = updated_data.get(col)
                mapped_col = 'BP_DOS' if col == 'BP DOS' else col
                parsed_date, error = validate_and_parse_date(date_str, measure.lower(), col, member_info_df)
                if error:
                    field_remarks[col] = f"Non-compliant: {col} - {error}"
                    if focus_field == col:
                        final_remark = field_remarks[col]
                        break
                else:
                    df[mapped_col] = parsed_date

        if final_remark:
            return final_remark

        # CBP-specific checks
        if measure.lower() == 'cbp':
            if 'BP_present' not in df or not df['BP_present'].iloc[0]:
                field_remarks['BP'] = "Non-compliant: No recent BP"
                if focus_field == 'BP':
                    final_remark = field_remarks['BP']
            if 'BP_DOS' not in df or not df['BP_DOS'].iloc[0] or pd.isna(df['BP_DOS'].iloc[0]):
                field_remarks['BP DOS'] = "Non-compliant: BP present but missing Date of Service"
                if focus_field == 'BP DOS':
                    final_remark = field_remarks['BP DOS']
            if 'BP_DOS' in df and df['BP_DOS'].iloc[0]:
                bp_dos = df['BP_DOS'].iloc[0]
                parsed_bp_dos = parse_date(bp_dos)
                if parsed_bp_dos and parsed_bp_dos.year != MEASUREMENT_YEAR:
                    field_remarks['BP DOS'] = f"Non-compliant: BP Date of Service ({bp_dos}) not within measurement year ({MEASUREMENT_YEAR})"
                    if focus_field == 'BP DOS':
                        final_remark = field_remarks['BP DOS']

        if final_remark:
            return final_remark

        # Merge DOB and calculate age
        merged_df = merge_dob(df, member_info_df)
        if 'DOB' in merged_df.columns and pd.notna(merged_df['DOB'].iloc[0]):
            dob = parse_date(merged_df['DOB'].iloc[0])
            if dob:
                age = int(MEASUREMENT_YEAR) - dob.year
                merged_df['Age'] = age
            else:
                overall_remark = "Non-compliant: Invalid DOB for age calculation"
                if focus_field:
                    final_remark = overall_remark
        else:
            overall_remark = "Non-compliant: Missing DOB for age calculation"
            if focus_field:
                final_remark = overall_remark

        if final_remark:
            return final_remark

        # Apply NCQA compliance checks
        result_df = apply_ncqa_compliance_checks(merged_df, measure)
        remark_col = f'Remark_{measure}'
        if remark_col in result_df.columns and not result_df[remark_col].isna().iloc[0]:
            overall_remark = result_df[remark_col].iloc[0]
        else:
            overall_remark = "Non-compliant: No compliance remark available" if overall_remark is None else overall_remark
                 
    except Exception as e:
        error_msg = f"Non-compliant: Error in compliance check - {str(e)}"
        if focus_field:
            return error_msg
        return error_msg

    # Final compliance check for focus field
    if focus_field:
        if any("Non-compliant" in remark for remark in field_remarks.values()):
            return list(field_remarks.values())[0] if field_remarks else f"Non-compliant: Check with {focus_field}"
        return f"Compliant:{measure}" if "Compliant" in overall_remark else f"Non-compliant: Check with {focus_field}"

    return overall_remark

def get_compliance_status(remark):
    if "Non-compliant" in remark:
        return "status-non-compliant"
    if "Exclusion" in remark:
        return "status-exclusion"
    if "Compliant" in remark:
        return "status-compliant"
    return "status-non-compliant"  # Default to non-compliant for any other case

def get_non_compliant_fields(measure, updated_data, member_info_df):
    field_remarks = {}
    for col in MEASURE_CONFIG.get(measure.lower(), {}).get('date_cols', []) + MEASURE_CONFIG.get(measure.lower(), {}).get('value_cols', []):
        remark = check_compliance(member_id, measure, updated_data, member_info_df, focus_field=col)
        if "Non-compliant" in remark:
            field_remarks[col] = remark
    return list(field_remarks.keys())


def add_compliance_status(member_id, measure, updated_data, member_info_df):
    overall_compliance_remark = check_compliance(member_id, measure, updated_data, member_info_df)
    if "Non-compliant" in overall_compliance_remark:
        st.markdown(f'<div class="non-compliant-remark">Disposition Status: {overall_compliance_remark}</div>', unsafe_allow_html=True)
        st.warning("Please verify all required data is present.", icon="⚠️")
    elif "Exclusion" in overall_compliance_remark:
        st.info("This member is marked as an Exclusion based on the current data.")
        st.markdown(f'<div class="compliance-remark">Disposition Status: {overall_compliance_remark}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="compliance-remark">Disposition Status: {overall_compliance_remark}</div>', unsafe_allow_html=True)



#AYU added to reset session states on seaching member
def reset_session_state(search_value):
    if search_value != st.session_state.get('last_search', None):
        st.session_state.pop('edit_index', None)
        st.session_state.pop('file_id', None)
        st.session_state['last_search'] = search_value


        
def update_multiple_columns(table, member_id, updates):
    # st.write(f"Updating {table} for Member ID: {member_id}")
    # st.write(f"Updates: {updates}")
    updates = {k: v for k, v in updates.items() if k.lower() != "updated_date"}
    if not updates:
        return
    set_clauses = [f"{col} = ?" for col in updates.keys()]
    set_clause = ", ".join(set_clauses) + ", updated_date = GETDATE()"
    query = f"UPDATE {table} SET {set_clause} WHERE FileID = ? AND is_active IN (1)" #AYU added FIleID
    values = list(updates.values()) + [str(member_id)]
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
        except pyodbc.Error as e:
            st.error(f"Error updating {table}: {str(e)}", icon="🚨")
        finally:
            conn.close()


def get_changed_fields(original_data, updated_data):
    changed_fields = []
    for key in updated_data.keys():
        original_value = original_data.get(key, '')
        updated_value = updated_data.get(key, '')
        # Convert both values to strings for comparison to handle None and other types
        original_value = str(original_value) if original_value is not None else ''
        updated_value = str(updated_value) if updated_value is not None else ''
        if original_value != updated_value:
            changed_fields.append(f"- `{key}`: {original_value} ➝ {updated_value}")
    return changed_fields

# Main App Logic
st.title(' ')
st.write('*Please enter the Member ID/File Name and select the Edit button to update the data.*')
st.markdown('<hr class="divider">', unsafe_allow_html=True)

# Initialize session state
if 'member_id' not in st.session_state: #AYU ----------- 
    st.session_state['member_id'] = None
if 'edit_index' not in st.session_state:
    st.session_state['edit_index'] = None
if 'page_number' not in st.session_state:
    st.session_state['page_number'] = 1
if 'updated_data' not in st.session_state:
    st.session_state['updated_data'] = {}
if 'compliance_status' not in st.session_state:
    st.session_state['compliance_status'] = {}
if 'reset_values' not in st.session_state: #AYU ----------- Store original values for reset
    st.session_state['reset_values'] = {}  
if 'reset_measure' not in st.session_state: #AYU ----------- Store original values for reset
    st.session_state['reset_measure'] = None
    
#Syn 
if 'field_compliance' not in st.session_state:
    st.session_state['field_compliance'] = {}
if 'original_data' not in st.session_state:
    st.session_state['original_data'] = {}
if 'show_confirmation' not in st.session_state:
    st.session_state['show_confirmation'] = {}
if 'pending_updates' not in st.session_state:
    st.session_state['pending_updates'] = {}
if 'pending_measure' not in st.session_state:
    st.session_state['pending_measure'] = None
if 'has_changes' not in st.session_state:
    st.session_state['has_changes'] = False
#AYU - Initialize session state for modal and current measure
if 'show_modal' not in st.session_state:
    st.session_state['show_modal'] = False
if 'current_measure' not in st.session_state:
    st.session_state['current_measure'] = None

# Search Section
search_option = st.radio('Search By', ('Member_id', 'File Name'), index=0, horizontal=True)

field_value=st.session_state.get('member_id', '') if search_option == 'Member_id' else st.session_state['edit_index']

print(f"field_value={field_value}")

search_value = st.text_input(
    f'**Search {search_option}**',
    placeholder=f"Enter {search_option}",
    value=field_value #AK
)
#search_value = st.text_input(f'**Search {search_option}**', label_visibility="visible", disabled=False, placeholder=f"Enter {search_option}")

#AY 
reset_session_state(search_value)

print(f"LOG0 :{type(search_value)}")

# if search_value and search_value != 'None': AK
print(f"LOG1: {search_value}")

#AYU - condition when seach_value is non-empty then only next section will should be displayed.

if search_value:
    if 'page_number' not in st.session_state:
        st.session_state.page_number = 1
    
    #AK 
    if search_option == 'File Name':
        file_name=search_value
        member_id= get_member_id_via_pdf(file_name)
        data = getdata3(member_id, "memberinfo",search_type=search_option)
        #data = getdata3(search_value, "memberinfo", search_type=search_option)
    else:
        member_id = search_value
        data = getdata3(member_id, "memberinfo")
    
    print(data)
    #AK - commented the below code, as we don't need to dislay the search results @Anchal
    
    #AY - Now we are using file_name as a edit index instead of member_id    
    if not data.empty:
        st.write("**Search Results:**")
        columns = list(data.columns)
        for i, row in data.iterrows():
            cols = st.columns(6)
            cols[0].write(row['Member_id'])
            cols[1].write(row['File Name'].replace('.pdf','') if 'Name' in row else 'N/A') #AYU need to add file_id 
            cols[2].write(row['Name'].replace('.pdf','') if 'Name' in row else 'N/A')
            cols[3].write(row['Gender'] if 'Gender' in row else 'N/A')
            cols[4].write(row['DOB'] if 'DOB' in row else 'N/A')
            #if cols[5].button("Edit", key=f"edit_{row['Member_id']}"):
            if cols[5].button("Edit", type='primary', key=f"edit_{row['File Name']}"): #AYU added file name as key
                st.session_state['edit_index'] = row['File Name'] #AYU passing file name as edit index
                #search_value = row['File Name']
                st.session_state['Member_id'] = row['Member_id'] #AYU passing member_id as session state
                #st.session_state['file_name'] = row['Member_id']  # Store Member_id
                #st.write(f"DEBUG: Selected File Name: {row['File Name']}, Member_id: {row['Member_id']}")
                st.session_state['updated_data'] = {}
                st.session_state['original_data'] = {}  # Reset original data
                st.session_state['compliance_status'] = {}
                st.session_state['page_number'] = 1
           
                st.session_state['field_compliance'] = {}
  
                  
                st.session_state['show_confirmation'] = {}
                st.session_state['pending_updates'] = {}
                st.session_state['pending_measure'] = None
                st.session_state['has_changes'] = False  # Reset changes tracker
                
    # else:
    #     st.session_state['edit_index'] = None

    # Edit Section
    # if st.session_state['edit_index']: #AK
    # member_id = search_value #AK st.session_state.get('member_id', '') #st.session_state['edit_index']

    
    
    st.title('')
    # Check if a row is selected for editing
                                              
    if 'edit_index' in st.session_state and st.session_state['edit_index']:
            # Get the row data to be edited
        row_to_edit = data[data['File Name'] == st.session_state['edit_index']].iloc[0]
        left_column, right_column = st.columns([0.5, 0.5], gap="large")

        # PDF Viewer
        
        pdf_location = lookup_pdf_location(st.session_state['edit_index']) #AYU Passing the file name using session state
        print(f"pdf_location: {pdf_location}")
        pdf_document = None
        #member_id=search_value
        filename = st.session_state.get('edit_index','') #AYU passing filename session state to be used for CRUD operations
        member_id=st.session_state.get('Member_id','') #Member_id to be used for compliance check
        #st.write(f"2--------Member ID: {member_id}")

        if pdf_location and os.path.exists(pdf_location):
            pdf_document = fitz.open(pdf_location)
            with right_column:
                with st.container(height=775, border=True):
                    st.markdown('<div class="page-input-container">', unsafe_allow_html=True)
                    page_input = st.number_input(
                        "Enter page number",
                        min_value=1,
                        max_value=len(pdf_document),
                        value=st.session_state['page_number'],
                        key="page_input"
                    )
                    if page_input != st.session_state['page_number']:
                        st.session_state['page_number'] = page_input
                    st.markdown('</div>', unsafe_allow_html=True)
                    display_pdf_page(st.session_state['page_number'] - 1, pdf_document)
        else:
            with right_column:
                with st.container(height=775, border=True):
                    st.warning("PDF file not found or inaccessible.", icon="⚠️")

        # Measures Tabs
        with left_column:
            with st.container(height=775, border=True):
                print(f"tabs_MEMBER_ID: {filename}")
                measures_available = {
                    "Member Info": getdata(filename, "memberinfo"),
                    "BCS": getdata(filename, "bcs"),
                    "CBP": getdata(filename, "cbp"),
                    "HBD": getdata(filename, "hbd"),
                    "BPD": getdata(filename, "bpd"),
                    "EED": getdata(filename, "eed"),
                    "CCS": getdata(filename, "ccs"),
                    "COL": getdata(filename, "col"),
                    # "LSD": getdata(filename, "lsd"),
                    # "PPC": getdata(filename, "ppc"),
                }
                
                # Store original data for each measure
                for measure, df in measures_available.items():
                    if not df.empty:
                        if measure == "Member Info":
                            data1 = create_new_dataframe_meminfo(df)
                        else:
                            data1 = create_new_dataframe(df, measure)
                        if not data1.empty:
                            st.session_state['original_data'][measure] = data1.iloc[0].to_dict()


                available_tabs = ["Member Info"]
                for measure in all_measures:
                    if not measures_available[measure].empty:
                        available_tabs.append(measure)

                tabs = st.tabs(available_tabs)
                member_info_df = measures_available["Member Info"]

                # Member Info Tab only
                with tabs[0]:
                    data = measures_available["Member Info"]
                    data1 = create_new_dataframe_meminfo(data)
                    filter_col=[col.replace('_', ' ') for col in data1.columns] #AYU added to remove _ from column names

                    pagedf = page_df(data)
                    if not data1.empty:
                        cols = st.columns([0.65, 0.35])
                        with cols[0]:
                            #confidence_score= get_confidence_score().get('generic', '89.2%')
                            confidence_score='89.2%'
                            confidence_score= f"{float(confidence_score.rstrip('%')):.2f}%"

                            st.markdown(f"<span style='color:#888; cursor:pointer; ; font-size:16px;' >Confidence Score: {confidence_score}</span>", unsafe_allow_html=True)
                            st.markdown(f"<span style='color:#888; cursor:pointer; ; font-size:16px;' >Measurement Year: {MEASUREMENT_YEAR}</span>", unsafe_allow_html=True)
                        # with cols[1]:
                        #     review=st.checkbox("Review Completed", key="review_completed", value=False, help="Check this box if you have completed the review for this member.")


                        updated_membinfo = st.session_state['updated_data'].setdefault("Member Info", {})
                        for idx, (filter_col,col, val) in enumerate(zip(filter_col,data1.columns, pagedf + [None] * (len(data1.columns) - len(pagedf)))):
                            cols = st.columns([0.73, 0.15, 0.14])
                            with cols[0]:
                                placeholder = "Enter as MM/DD/YYYY" if col == "DOB" else ""
                                current_value = str(data1.at[0, col]) if pd.notna(data1.at[0, col]) else ""

                                # Synd: Check if the field is non-compliant#add this 
                                field_key = f"{col}_Member Info"
                                #OLD_CODE
                                # is_non_compliant = st.session_state['field_compliance'].get(field_key, "").startswith("Non-compliant")
                                # label = f"**{'*' if is_non_compliant else ''}{col}**"

                                # updated_membinfo[col] = st.text_input(
                                    # label,
                                    # value=current_value,
                                    # key=f"edit_{col}_meminfo",
                                    # placeholder=placeholder,
                                    # on_change=check_field_compliance,
                                    # args=(member_id, "Member Info", updated_membinfo, member_info_df, col)
                                # )
                                #SYND
                                compliance_message = st.session_state['field_compliance'].get(field_key, "")
                                is_non_compliant = compliance_message.startswith("Non-compliant")

                                if is_non_compliant:
                                    help_text = f"Required for compliance: {compliance_message.replace('Non-compliant: ', '')}"
                                else:
                                    help_text = "Enter as MM/DD/YYYY" if col == "DOB" else ""
                                label = f"{'' if is_non_compliant else ''}{filter_col}"
                                #st.markdown(f"**{label}**", unsafe_allow_html=True) #AYU not required as already added as labels
                                
                        #AYU Change the position of the updated_membinfo which waas present in col[2] earlier dur to which extra gap were seen between the label and input box
                                                      
                                updated_membinfo[col] = st.text_input(
                                f"**{label}**",  #AYU
                                value=current_value,

                                key=f"edit_{col}_meminfo",
                                placeholder=placeholder,
                                on_change=on_field_change,
                                args=(filename, "Member Info", updated_membinfo, member_info_df, col)
                            )
                            with cols[1]:
                                # if help_text
                                    # pass   #AYU Commented this line as of no use(NEED TO CHECK WITH SYN)
                                    #st.markdown(f"<span style='color:#888; cursor:pointer;' title='{help_text}'>❓</span>", unsafe_allow_html=True)
                                # else:
                                     pass
                                #      #st.markdown("", unsafe_allow_html=True) 
                            with cols[2]:
                                label = f"{'' if is_non_compliant else ''}{filter_col}"                   
                                #if st.button("📃", key=f"page_{col}_meminfo_{idx}"):
                                    # page_to_show = int(val) if val and val != "0" else 1
                                    # st.session_state['page_number'] = page_to_show
                                # AYU----MODIFY---- Check if val is a valid integer before conversion
                                if st.button("📃", key=f"page_{col}_{measure.lower()}_{idx}"):
                                        
                                        if val is None or val == "0": 
                                                #st.session_state['page_number'] = st.session_state.get('page_number', 1)
                                                st.session_state['page_number'] = 1 
                                        else:
                                            #print(type(val), val)
                                            try:
                                                if len(val) > 1:
                                                    st.session_state['page_number'] = 1
                                                else:
                                                    st.session_state['page_number'] = int(val)
                                            except (NameError, TypeError, ValueError):
                                                st.session_state['page_number'] = int(val)
                            #AYU # Commented the below code as it was not required (MOVED TO THE ABOVE in col[0])

                            #         updated_membinfo[col] = st.text_input(
                            #     f"**{label}**",  #AYU Bold the label
                            #     value=current_value,
                            #     key=f"edit_{col}_meminfo",
                            #     placeholder=placeholder,
                            #     on_change=on_field_change,
                            #     args=(filename, "Member Info", updated_membinfo, member_info_df, col)
                            # )
                            
                        cols = st.columns([0.7, 0.3])
                        with cols[0]:
                            pass
                            #review=st.checkbox("Review Completed", key="review_completed"+"_MemberInfo", value=False, help="Check this box if you have completed the review for this member.")
                        with cols[1]:
                            if st.button("Submit General",type='primary', disabled=not st.session_state.get('has_changes', False)):
                                # Compare original and updated data
                                original = st.session_state['original_data'].get("Member Info", {})
                                changed_fields = get_changed_fields(original, updated_membinfo)
                                if changed_fields:
                                    st.session_state['show_confirmation']['Member Info'] = True

                                    st.session_state['pending_updates']['Member Info'] = updated_membinfo
                                    # print(f"LOG1_AK : {st.session_state['pending_updates']['Member Info']}")
                                    st.session_state['pending_measure'] = "Member Info"
                                else:
                                    st.info("No changes detected to submit.", icon="ℹ️")

                        # Show confirmation prompt if triggered
                        if st.session_state.get('show_confirmation', {}).get("Member Info", False):
                            with st.container():
                                # st.markdown('<div class="confirmation-modal">', unsafe_allow_html=True)
                                st.markdown("⚠️ Do you want to proceed?", unsafe_allow_html=True)
                                st.markdown("The following fields have changed:")
                                for change in get_changed_fields(st.session_state['original_data'].get("Member Info", {}), st.session_state['pending_updates'].get("Member Info", {})):
                                    st.markdown(change)
                                col_yes, col_no = st.columns(2)
                                with col_yes:
                                    if st.button("Yes",type='primary', key="confirm_yes_meminfo"):
                                        # Proceed with the update
                                        update_multiple_columns("memberinfo", filename, st.session_state['pending_updates']['Member Info'])
                                        # Update original data with the new values
                                        # print(f"LOG2_AK : {st.session_state['pending_updates']['Member Info']}")
                                        st.session_state['original_data']['Member Info'] = st.session_state['pending_updates']['Member Info'].copy()
                                        st.session_state['updated_data']["Member Info"] = {}
                                        st.session_state['field_compliance'] = {}
                                        st.session_state['show_confirmation']['Member Info'] = False
                                        st.session_state['pending_updates']['Member Info'] = {}
                                        st.session_state['pending_measure'] = None
                                        st.session_state['has_changes'] = False  # Reset changes tracker
                                        st.session_state['reset_measure'] = None
                                        st.success("Changes saved successfully", icon="✅")
                                with col_no:
                                    if st.button("No", type='primary', key="confirm_no_meminfo"):
                                        # Cancel the update, reset fields to original values
                                        for col in updated_membinfo.keys():
                                            st.session_state[f"edit_{col}_meminfo"] = st.session_state['original_data']['Member Info'].get(col, '')
                                        st.session_state['updated_data']["Member Info"] = {}
                                        st.session_state['field_compliance'] = {}
                                        st.session_state['show_confirmation']['Member Info'] = False
                                        st.session_state['pending_updates']['Member Info'] = {}
                                        st.session_state['pending_measure'] = None
                                        st.session_state['has_changes'] = False  # Reset changes tracker
                                        st.info("Update cancelled.", icon="ℹ️")
                                st.markdown('</div>', unsafe_allow_html=True)

                # Dynamic Measure Tabs -- for remaining measures
                for measure in available_tabs[1:]:
                    confidence_score= get_confidence_score().get(measure,'89.26%')
                    confidence_score= f"{float(confidence_score.rstrip('%')):.2f}%"

                    with tabs[available_tabs.index(measure)]:
                        cols = st.columns([0.87, 0.13])
                        with cols[0]:
                            st.markdown(f"<span style='color:#888; cursor:pointer; ; font-size:16px;' >Confidence Score: {confidence_score}</span>", unsafe_allow_html=True)

                            st.markdown(f"<span style='color:#888; cursor:pointer; ; font-size:16px;' >Measurement Year: {MEASUREMENT_YEAR}</span>", unsafe_allow_html=True)
                            
                        with cols[1]:
                            #review=st.checkbox("Review Completed", key="review_completed"+measure, value=False, help="Check this box if you have completed the review for this member.")
                            
                            if st.button("ℹ️", key=f"info_{measure}", help=f"View {measure} specifications"):
                                    if st.session_state['current_measure'] == measure and st.session_state['show_modal']:
                                        st.session_state['show_modal'] = False
                                        st.session_state['current_measure'] = None
                                    else:
                                        st.session_state['show_modal'] = True
                                        st.session_state['current_measure'] = measure
                        
                        if st.session_state.get('current_measure') == measure and st.session_state['show_modal']:
                            st.session_state['MY']=MEASUREMENT_YEAR #AYU added to pass measurement year to avoid error when user directly jumps to Review Member page
                            html_content = load_measure_spec(st.session_state['MY'], measure)
                            render_spec_modal(measure, html_content)

                        data = measures_available[measure]
                        data1 = create_new_dataframe(data, measure)

                        filter_col=[col.replace('_', ' ') for col in data1.columns] #AYU added to remove _ from column names
                        pagedf = page_df(data)
                        if not data1.empty:
                            original_data = st.session_state['original_data'].get(measure, {})
                            updated_data = st.session_state['updated_data'].setdefault(measure, original_data.copy())


                            #AYU Store original values for reset ---------------MODIFY---------------
                            if measure not in st.session_state['reset_values']:
                                st.session_state['reset_values'][measure] = original_data.copy()
 
                            add_compliance_status(member_id, measure, updated_data, member_info_df)

                            for idx, (filter_col,col, val) in enumerate(zip_longest(filter_col,data1.columns, pagedf)):
                                     
                                cols = st.columns([0.73, 0.15, 0.14])
                                with cols[0]:
                                    placeholder = "Enter as MM/DD/YYYY" if col in ["DateofService", "DateofScreening", "Mammogram DOS", "Bilateral Mastectomy DOS", "Unilateral Mastectomy R DOS", "Unilateral Mastectomy L DOS"] else "Enter as XXX/YY (e.g., 120/80)" if col == "BP" else "Enter Yes/No" if col in ["Mammogram", "Bilateral Mastectomy", "Unilateral Mastectomy R", "Unilateral Mastectomy L"] else ""
                                    
                                    #synd
                                    #is_non_compliant = col in get_non_compliant_fields(measure, updated_data, member_info_df)
                                    #synd Check if the field is non-compliant using session state
                                    field_key = f"{col}_{measure}"
                                    tooltip_key = f"tooltip_{col}_{measure}"
                                    is_non_compliant = st.session_state['field_compliance'].get(field_key, "").startswith("Non-compliant")
                                    label = f"{'' if is_non_compliant else ''}{filter_col}"


                                    session_key = f"edit_{col}_{measure.lower()}"
                                    # if session_key in st.session_state:
                                    #     current_value = st.session_state[session_key]
                                    # else:
                                    #     current_value = str(data1.at[0, col]) if pd.notna(data1.at[0, col]) else ""

                                    #AYU Use reset values if reset_measure is set ---------------MODIFY---------------
                                    if st.session_state['reset_measure'] == measure and col in st.session_state['reset_values'][measure]:
                                        current_value = str(st.session_state['reset_values'][measure][col]) if pd.notna(st.session_state['reset_values'][measure][col]) else ""
                                    elif session_key in st.session_state:
                                        current_value = st.session_state[session_key]
                                    else:
                                        current_value = str(data1.at[0, col]) if pd.notna(data1.at[0, col]) else ""
                                    if is_non_compliant:
                                        help_text = f"Required for compliance: {st.session_state['field_compliance'].get(field_key, '').replace('Non-compliant: ', '')}"
                                    else:
                                        help_text = st.session_state['field_compliance'].get(tooltip_key, "") or ("Enter date in MM/DD/YYYY format" if col.lower().endswith("dos") else "")

                                    #This is a quick  fix for HBD only, we need to rename the prompts and in table also
                                    label  ='Diabetes' if ('Posg' in  label) and (measure == 'HBD') else label

                                    # updated_data[col] = st.text_input(
                                    #     f"**{label}**", #AYU Bold the label
                                    #     value=current_value,
                                    #     key=session_key,
                                    #     placeholder=placeholder,
                                    #     help=help_text,
                                    #     on_change=on_field_change,
                                    #     args=(member_id, measure, updated_data, member_info_df, col)
                                    # )
                                    
                                    #AYU -----REVIEW FLAG UPDATE-----
                                    if col == "Review_Completed":
                                        radio_options = ["Yes","No"]
                                        default_value = str(current_value).strip().capitalize()
                                        radio_index = default_value
                                        if default_value not in radio_options:
                                            default_value = "No"
                                        selected_value = st.radio(
                                            f"**{measure} Review completed**",
                                            options=radio_options,
                                            index=radio_options.index(default_value),
                                            key=session_key,
                                            horizontal=True,
                                            help="Check this box if you have completed the review for this member",
                                            on_change=on_field_change,
                                            args=(member_id, measure, updated_data, member_info_df, col)
                                        )
                                        # Store 1 for Yes, 0 for No
                                        updated_data[col] = "Yes" if selected_value == "Yes" else "No"
                                    
                                    # -----REVIEW FLAG UPDATE-----
                                    else:
                                        updated_data[col] = st.text_input(
                                            f"**{label}**", #AYU Bold the label
                                            value=current_value,
                                            key=session_key,
                                            placeholder=placeholder,
                                            help=help_text,
                                            on_change=on_field_change,
                                            args=(member_id, measure, updated_data, member_info_df, col)
                                        )
                                with cols[1]:
                                    #AYU Added Spec button functionality
                                #     if idx == 0:
                                #         if st.button("ℹ️", key=f"info_{measure}", help=f"View {measure} specifications"):
                                #                 if st.session_state['current_measure'] == measure and st.session_state['show_modal']:
                                #                     st.session_state['show_modal'] = False
                                #                     st.session_state['current_measure'] = None
                                #                 else:
                                #                     st.session_state['show_modal'] = True
                                #                     st.session_state['current_measure'] = measure
                                #     else:
                                #         pass
                                
                                # if st.session_state.get('current_measure') == measure and st.session_state['show_modal']:
                                #     st.session_state['MY']=MEASUREMENT_YEAR #AYU added to pass measurement year to avoid error when user directly jumps to Review Member page
                                #     html_content = load_measure_spec(st.session_state['MY'], measure)
                                #     render_spec_modal(measure, html_content)
                                    pass
                                
                                with cols[2]:
                                    #OLD CODE
                                    # if val and val != "0":
                                    #     if st.button("📃", key=f"page_{col}_{measure.lower()}_{idx}"):
                                    #         st.session_state['page_number'] = int(val)
                                            
                                    # AYU----MODIFY---- Check if val is a valid integer before conversion
                                    if data1.columns[idx]=="Review_Flag":
                                        pass
                                    else:
                                        if st.button("📃", key=f"page_{col}_{measure.lower()}_{idx}"):
                                                
                                                if val is None or val == "0": 
                                                        #st.session_state['page_number'] = st.session_state.get('page_number', 1)
                                                        st.session_state['page_number'] = 1 
                                                else:
                                                    #print(type(val), val)
                                                    try:
                                                        if len(val) > 1:
                                                            st.session_state['page_number'] = 1
                                                        else:
                                                            st.session_state['page_number'] = int(val)
                                                    except (NameError, TypeError, ValueError):
                                                        st.session_state['page_number'] = int(val)
                                                        
                               

                            col1, col2, col3 = st.columns([0.33, 0.33, 0.34])
                            with col1:
                                pass
                                #review=st.checkbox(measure+" Review Completed", key="review_completed"+measure, value=False, help="Check this box if you have completed the review for this member.")
                            with col2:
                                #synd Removed: Undo Compliance button
                                # if st.button("Undo",type='primary', key=f"undo_{measure.lower()}"):
                                #     st.session_state['updated_data'][measure] = original_data.copy()
                                #     st.session_state['compliance_status'] = {}
                                pass

                            _, _, col3 = st.columns([0.33, 0.33, 0.34])#syn :add this 

                            with col3:
                                if st.button(f"Submit {measure}", type='primary', disabled=not st.session_state.get('has_changes', False)):
                                    # Compare original and updated data
                                    changed_fields = get_changed_fields(original_data, updated_data)
                                    if changed_fields:
                                        st.session_state['show_confirmation'][measure] = True
                                        st.session_state['pending_updates'][measure] = updated_data
                                        st.session_state['pending_measure'] = measure
                                    else:
                                        st.info("No changes detected to submit.", icon="ℹ️")

                            # Show confirmation prompt if triggered
                            if st.session_state.get('show_confirmation', {}).get(measure, False):
                                with st.container():
                                    # st.markdown('<div class="confirmation-modal">', unsafe_allow_html=True)
                                    st.markdown("⚠️ Do you wish to proceed?", unsafe_allow_html=True)
                                    st.markdown("The following fields have changed:")
                                    for change in get_changed_fields(st.session_state['original_data'].get(measure, {}), st.session_state['pending_updates'].get(measure, {})):
                                        st.markdown(change)
                                    col_yes, col_no = st.columns(2)
                                    with col_yes:
                                        if st.button("Yes", type='primary' ,key=f"confirm_yes_{measure}"):
                                            # Proceed with the update
                                            update_multiple_columns(measure.lower(), filename, st.session_state['pending_updates'][measure])
                                            overall_compliance_remark = check_compliance(member_id, measure, st.session_state['pending_updates'][measure], member_info_df)
                                            remark_col = f"Remark_{measure.upper()}"
                                            conn = create_connection()
                                            if conn:
                                                try:
                                                    cursor = conn.cursor()
                                                    query = f"UPDATE {measure.lower()} SET {remark_col} = ?, updated_date = GETDATE() WHERE Member_id = ? AND is_active IN (1)"
                                                    cursor.execute(query, (overall_compliance_remark, str(member_id)))
                                                    conn.commit()
                                                except Exception as e:
                                                    st.error(f"Error updating compliance remark: {e}", icon="🚨")
                                                finally:
                                                    conn.close()
                                            # Update original data with the new values
                                            st.session_state['original_data'][measure] = st.session_state['pending_updates'][measure].copy()
                                            for col in updated_data:
                                                session_key = f"edit_{col}_{measure.lower()}"
                                                if session_key in st.session_state:
                                                    del st.session_state[session_key]
                                            st.session_state['updated_data'][measure] = {}
                                            st.session_state['show_confirmation'][measure] = False
                                            st.session_state['pending_updates'][measure] = {}
                                            st.session_state['pending_measure'] = None
                                            st.session_state['has_changes'] = False  # Reset changes tracker
                                            # AYU----MODIFY---- Clear reset flag after successful update
                                            st.session_state['reset_measure'] = None
                                            st.success(f"Changes saved successfully", icon="✅")
                                    with col_no:
                                        if st.button("No",type='primary', key=f"confirm_no_{measure}"):
                                        #AYU --------COMMENTED THIS CODE AS IT WAS working AS EXPECTED--------------------- 
                                            # Cancel the update, reset fields to original values
                                            # for col in updated_data:
                                            #     session_key = f"edit_{col}_{measure.lower()}"
                                            #     if session_key in st.session_state:
                                            #         st.session_state[session_key] = st.session_state['original_data'][measure].get(col, '')
                                            # st.session_state['updated_data'][measure] = {}
                                            # st.session_state['show_confirmation'][measure] = False
                                            # st.session_state['pending_updates'][measure] = {}
                                            # st.session_state['pending_measure'] = None
                                            # st.session_state['has_changes'] = False  # Reset changes tracker
                                            # st.info("Update cancelled.", icon="ℹ️")
                                        #AYU -------------------------MODIFY----------------
                                            st.session_state['updated_data'][measure] = st.session_state['original_data'][measure].copy()  # ---------------MODIFY---------------
                                            st.session_state['reset_measure'] = measure  
                                            st.session_state['show_confirmation'][measure] = False 
                                            st.session_state['pending_updates'][measure] = {}  
                                            st.session_state['pending_measure'] = None 
                                            st.session_state['has_changes'] = False  
                                            st.info("Update cancelled.", icon="ℹ️")
                                        #AYU -------------------------MODIFY----------------
                                    st.markdown('</div>', unsafe_allow_html=True)
                        else:
                            st.warning(f"No data to display for {measure}.")
                                                                                                                                                    
                                                                      


            if pdf_document:
                pdf_document.close()
                    