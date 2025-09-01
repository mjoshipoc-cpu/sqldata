import streamlit as st
import pandas as pd
import pyodbc
import os
import base64
import streamlit_extras.switch_page_button  as page_switcher
# ---MODIFY---- Import necessary libraries for ag-grid implementation
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode, DataReturnMode


#UI
st.set_page_config(layout="wide",page_title="HEDISAbstractor.AI")

# CSS for UI
st.markdown(
    """
    <style>
    /* ------------AI CHANGES------- Import Google Fonts for better typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* ------------AI CHANGES------- Global font and base styles */
    .stApp {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #FFFFFF 0%, #FFFFFF 100%);
        min-height: 100vh;
    }
    
    /* ------------AI CHANGES------- Main content area with glassmorphism effect */
    .main .block-container {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
        padding: 2rem;
        margin-top: 2rem;
    }
    
    /* ------------AI CHANGES------- Enhanced user greeting container */
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
        border-bottom: 1px solid rgba(251, 78, 11, 0.1);
    }
    
    /* ------------AI CHANGES------- Enhanced user greeting with animation */
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
    
    /* ------------AI CHANGES------- Enhanced title with gradient and animation */
    .title {
        font-size: 32px;
        font-weight: 700;
        color: white;
        padding: 10px;
        text-align: center;
        background: linear-gradient(135deg, #fb4e0b 0%, #ff6b35 100%);
        position: fixed;
        width: 80%;
        top: 82px;
        z-index: 9999;
        border-radius: 0 0 20px 20px;
        box-shadow: 0 8px 32px rgba(251, 78, 11, 0.4);
        backdrop-filter: blur(5px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        animation: slideDown 0.6s ease-out;
    }
    
    /* ------------AI CHANGES------- Title animation */
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
    
    .left {
        float: left;
    }
    .right {
        float: right;
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
st.markdown("""
                <style>
                div.stButton > button:first-child {
                    background-color: #fb4e0b; /* orange */
                    color: white;
                    border: 1px solid #000000;
                    border-radius: 8px;
                    padding: 5px 12px; /* Decreased padding */
                    text-align: center;
                    text-decoration: none;
                    display: inline-block;
                    font-size: 12px; /* Decreased font size */
                    margin: 4px 2px;
                    cursor: pointer;
                    -webkit-transition-duration: 0.4s; /* Safari */
                    transition-duration: 0.4s;
                }
                div.stButton > button:first-child:hover {
                    background-color: white;
                    color: black;
                    border: 1px solid #000000;
                }
                </style>""", unsafe_allow_html=True)

st.markdown(
    """
    <div class="user-greeting-container">
    <div class="user-greeting">
        <img src="https://img.icons8.com/ios/452/user-male-circle.png" alt="user icon" />
        Hi, Ayush
    </div>
</div>
    """,
    unsafe_allow_html=True
)#------Till Here-----------------

# Header
st.markdown("""
    <div class="title">
        <span class="left">HEDISAbstractor.AI</span>
        <span class="right">EXL</span>
    </div>
    """, unsafe_allow_html=True)



# Database connection (unchanged)
server_name = os.getenv('HEDIS_SERVER')
database_name = os.getenv('HEDIS_DATABASE')
#database_name= "Hedis2"
db_config = {
    'Driver': os.getenv('HEDIS_DRIVER', 'ODBC Driver 17 for SQL Server'),
    'Server': server_name,
    'Database': database_name,
    'Trusted_Connection': os.getenv('HEDIS_TRUSTED_CONNECTION', 'yes')
}

def create_connection():
    conn_str = (
        f"DRIVER={db_config['Driver']};"
        f"SERVER={db_config['Server']};"
        f"DATABASE={db_config['Database']};"
        f"Trusted_Connection={db_config['Trusted_Connection']};"
    )
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SET DATEFORMAT ymd;")
        return conn
    except pyodbc.Error as e:
        st.error(f"Database connection error: {str(e)}", icon="🚨")
        return None
 

# Function to get data from the database


def get_data():
    conn = create_connection()
    query = f""" SELECT distinct m.Member_id AS Member_id, 
                            
                            f.Measurement_Year,
                            m.Name AS Name, 
                            m.Gender, 
                            m.DOB,
                            m.FileID,
                            f.is_active
                            
                        FROM file_info f
                        right JOIN memberinfo m ON f.FileID = m.Member_id and  (f.is_active = 1) 
                        WHERE (m.is_active = 1) and m.FILEID is not Null

                        """
    return pd.read_sql(query, conn)


# Function to update data in the database
def update_data(index, column, value):
    conn = create_connection()
    cursor = conn.cursor()
    query = f"UPDATE memberinfo SET {column} = ? WHERE Member_id = ?"  # Replace with your index and column names
    cursor.execute(query, (value, index))
    conn.commit()

def get_measure_data(measure):
    conn= create_connection()
    #query=f"Select Height,Weight,BMI,Obese,Smoker,Drinker,Posg_presence,Depression_history,Hospice_or_Palliative_care,r.* from memberinfo l join {measure} r on l.Member_id=r.Member_id"
    query=f"Select * from {measure} where is_active in (1)"
    return pd.read_sql(query, conn)

def filter_df(df,flag):
    non_page_columns = [col for col in df.columns if 'page' not in col]
    if flag:
        # If flag is True, remove 'page' columns
        elements_to_remove = ["is_active","Updated_date","Insert_Date","Updated_date"]
    else:
        elements_to_remove = ["Name","FileID", "is_active","Remark"]
    non_page = [item for item in non_page_columns if item not in elements_to_remove]
    new_df = df[non_page]
    return new_df


# Function to convert DataFrame to CSV and create download link
def get_csv_download_link(df, filename="data.csv"):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()  # Encode to base64
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download CSV File</a>'
    return href


# Streamlit app
st.title('')

# Initialize session state
if 'files_name' not in st.session_state:
    st.session_state['files_name']=None
if 'member_id' not in st.session_state:
    st.session_state['member_id'] = None

# Custom JavaScript for View button renderer
view_button_renderer = JsCode('''
    class ViewBtnCellRenderer {
        init(params) {
            this.params = params;
            this.eGui = document.createElement('div');
            this.eGui.innerHTML = `
             <span>
                <style>
                .btn_view {
                  background-color: #007bff;
                  border: none;
                  color: white;
                  text-align: center;
                  text-decoration: none;
                  display: inline-block;
                  font-size: 12px;
                  font-weight: bold;
                  height: 2.5em;
                  width: 6em;
                  cursor: pointer;
                  border-radius: 4px;
                  margin: 2px;
                }

                .btn_view:hover {
                  background-color: #0056b3;
                }
                </style>
                <button id='view-button' 
                    class="btn_view" 
                    >👁️ View</button>
             </span>
          `;
        }

        getGui() {
            return this.eGui;
        }
    };
    ''')

#  Custom JavaScript for Summary button renderer
summary_button_renderer = JsCode('''
    class SummaryBtnCellRenderer {
        init(params) {
            this.params = params;
            this.eGui = document.createElement('div');
            this.eGui.innerHTML = `
             <span>
                <style>
                .btn_summary {
                  background-color: #28a745;
                  border: none;
                  color: white;
                  text-align: center;
                  text-decoration: none;
                  display: inline-block;
                  font-size: 12px;
                  font-weight: bold;
                  height: 2.5em;
                  width: 6em;
                  cursor: pointer;
                  border-radius: 4px;
                  margin: 2px;
                }

                .btn_summary:hover {
                  background-color: #218838;
                }
                </style>
                <button id='summary-button' 
                    class="btn_summary" 
                    >📋</button>
             </span>
          `;
        }

        getGui() {
            return this.eGui;
        }
    };
    ''')

# ---MODIFY---- JavaScript function to handle View button clicks
view_button_click = JsCode('''
    function(e) {
        let api = e.api;
        let rowIndex = e.rowIndex;
        let rowData = e.data;
        
        // Store data in session storage for Streamlit to access
        sessionStorage.setItem('selected_member_name', rowData.Name || '');
        sessionStorage.setItem('selected_member_id', rowData.Member_id || '');
        sessionStorage.setItem('selected_file_id', rowData.FileID || '');
        sessionStorage.setItem('button_clicked', 'view');
        
        // Trigger a custom event to notify Streamlit
        window.parent.postMessage({
            type: 'streamlit:componentReady',
            data: {
                action: 'view',
                member_name: rowData.Name,
                member_id: rowData.Member_id,
                file_id: rowData.FileID
            }
        }, '*');
    }
    ''')

# ---MODIFY---- JavaScript function to handle Summary button clicks
summary_button_click = JsCode('''
    function(e) {
        let api = e.api;
        let rowIndex = e.rowIndex;
        let rowData = e.data;
        
        // Store data in session storage for Streamlit to access
        sessionStorage.setItem('selected_member_name', rowData.Name || '');
        sessionStorage.setItem('selected_member_id', rowData.Member_id || '');
        sessionStorage.setItem('selected_file_id', rowData.FileID || '');
        sessionStorage.setItem('button_clicked', 'summary');
        
        // Trigger a custom event to notify Streamlit
        window.parent.postMessage({
            type: 'streamlit:componentReady',
            data: {
                action: 'summary',
                member_name: rowData.Name,
                member_id: rowData.Member_id,
                file_id: rowData.FileID
            }
        }, '*');
    }
    ''')

# ---MODIFY---- Function to create dynamic grid configuration
def create_dynamic_grid_config(dataframe):
    """
    Create a dynamic grid configuration that adapts to the dataframe structure
    """
    gb = GridOptionsBuilder.from_dataframe(dataframe)
    
    # ---MODIFY---- Configure each column dynamically
    for col in dataframe.columns:
        gb.configure_column(
            col, 
            resizable=True, 
            sortable=True, 
            filter=True,
            autoHeight=True,
            wrapText=True,
            cellStyle={'textAlign': 'center', 'fontSize': '14px'}
        )
    
    # ---MODIFY---- Add View button column
    gb.configure_column(
        'View', 
        headerTooltip='Click to view member details',
        editable=False, 
        filter=False,
        sortable=False,
        onCellClicked=view_button_click,
        cellRenderer=view_button_renderer,
        autoHeight=True,
        width=100,
        suppressMovable=True,
        lockPosition='right'
    )
    
    # ---MODIFY---- Add Summary button column
    gb.configure_column(
        'Summary', 
        headerTooltip='Click to view member summary',
        editable=False, 
        filter=False,
        sortable=False,
        onCellClicked=summary_button_click,
        cellRenderer=summary_button_renderer,
        autoHeight=True,
        width=100,
        suppressMovable=True,
        lockPosition='right'
    )
    
    # ---MODIFY---- Configure grid options for better performance and appearance
    gb.configure_default_column(
        resizable=True,
        filterable=True,
        sortable=True,
        editable=False
    )
    
    gb.configure_grid_options(
        domLayout='normal',
        enableRangeSelection=True,
        rowSelection='single',
        suppressRowClickSelection=True,
        animateRows=True,
        rowHeight=50,
        headerHeight=50
    )
    
    # ---MODIFY---- Configure pagination for large datasets
    gb.configure_pagination(
        enabled=True,
        paginationAutoPageSize=False,
        paginationPageSize=20
    )
    
    return gb.build()

# ---MODIFY---- Main application function
def main():
    
    # # ---MODIFY---- Custom CSS for better styling
    # st.markdown("""
    # <style>
    #     .main-header {
    #         background: linear-gradient(90deg, #83898C, #D6DBDD);
    #         color: white;
    #         padding: 10px;
    #         border-radius: 5px;
    #         text-align: center;
    #         margin-bottom: 10px;
    #     }
        
    #     .grid-container {
    #         border: 1px solid #007bff;
    #         border-radius: 5px;
    #         padding: 5px;
    #         background-color: #f8f9fa;
    #     }
        
    #     .metrics-container {
    #         background-color: white;
    #         padding: 8px;
    #         border-radius: 4px;
    #         box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    #         margin: 5px 0;
    #     }
    # </style>
    # """, unsafe_allow_html=True)
    
    # # ---MODIFY---- Header section
    # st.markdown('<div class="main-header"><h3>📊 Member Data Repository</h3></div>', unsafe_allow_html=True)
    
    # Load data (keeping original data loading logic)
    data1 = get_data()
    print(f"data1: {len(data1)}")
    measures = ["BCS", "CBP", "HBD", "BPD", "EED", "CCS", "COL", "LSD", "PPC"]
    
    # ---MODIFY---- Enhanced measure selection with styling
    col1, col2= st.columns([1,2])
    with col1:
        category = st.selectbox(
            '**Select Measures**', 
            measures,
            help="Choose a measure to filter the data"
        )

    # Data processing (keeping original logic)
    data = get_measure_data(category)
    print(f"data: {len(data)}")
    data = filter_df(data, 0)
    
    columns = list(data.columns)
    
    data = data1.merge(data, how='inner', on='Member_id').drop_duplicates(
        subset=['FileID', 'Member_id', 'is_active'], keep='last'
    ).reset_index(drop=True)
    print(f"data: {len(data)}")
    
    data.sort_values(by=['Insert_Date'], ascending=True, inplace=True)
    data = filter_df(data, 1)
    data_merge = data.copy()
    
    # Rearrange columns (keeping original logic)
    rearranged_columns = []
    first_column = ['Measurement_Year']
    remaining_columns = [i for i in data.columns if i.strip() not in first_column]
    
    rearranged_columns.extend(first_column)
    rearranged_columns.extend(remaining_columns)
    data = data[rearranged_columns]
    
    data["Member_id"] = data["Member_id"].astype(str).str.replace(",", " ")
    
    # ---MODIFY---- Dynamic column limitation based on screen size
    #max_cols = st.sidebar.slider("Maximum Columns to Display", 3, len(data.columns), 6)
    max_cols=6
    data_display = data.iloc[:, 0:max_cols]

    
    # ---MODIFY---- Add button columns to dataframe for ag-grid
    data_display['View'] = ''
    data_display['Summary'] = ''
    
    # ---MODIFY---- Display metrics
    st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
    col1, col2, col3= st.columns(3)
    # with col1:
    #     st.metric("Total Records", len(data_display))
    with col1:
        st.metric("Selected Measure", category)
    with col2:
        st.metric("Columns Displayed", max_cols)
    with col3:
        st.metric("Pages", (len(data_display) // 20) + 1)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ---MODIFY---- Create and display the dynamic ag-grid
    st.markdown('<div class="grid-container">', unsafe_allow_html=True)
    
    grid_options = create_dynamic_grid_config(data_display)
    
    # ---MODIFY---- Render the ag-grid with enhanced options
    grid_response = AgGrid(
        data_display,
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.NO_UPDATE,
        fit_columns_on_grid_load=True,
        enable_enterprise_modules=False,
        height=600,
        width='100%',
        theme='streamlit',
        allow_unsafe_jscode=True,
        custom_css={
            ".ag-header-cell-text": {"font-weight": "bold", "color": "#007bff"},
            ".ag-row": {"font-size": "14px"},
            ".ag-cell": {"display": "flex", "align-items": "center", "justify-content": "center"}
        }
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ---MODIFY---- Handle button clicks through session state
    if 'grid_key' not in st.session_state:
        st.session_state.grid_key = 0
    
    # ---MODIFY---- Check for selected rows and handle navigation
    if grid_response['selected_rows'] is not None and len(grid_response['selected_rows']) > 0:
        selected_row = grid_response['selected_rows'][0]
        
        # Check if this is a button click by examining the selected row
        if 'Member_id' in selected_row and selected_row['Member_id'] != "Unknown":
            st.session_state['member_name'] = selected_row.get('Name', '')
            st.session_state['member_id'] = selected_row.get('Member_id', '')
            st.session_state['FileID'] = selected_row.get('FileID', '')
            
            # Display selected row information
            st.success(f"Selected: {selected_row.get('Name', 'Unknown')} (ID: {selected_row.get('Member_id', 'Unknown')})")
            
            # ---MODIFY---- Add navigation buttons
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("🔍 Go to Review Page", key="nav_review"):
                    st.switch_page("pages/2_ReviewMember.py")
            with col2:
                if st.button("📋 Go to Summary Page", key="nav_summary"):
                    st.switch_page("pages/5_Summarization.py")
    
    # ---MODIFY---- Enhanced download section
    st.markdown("---")
    # st.markdown("### 📥 Export Data")
    
    col1, col2,col3= st.columns([0.1, 0.1, 0.7])
    with col1:
        st.download_button(
            label="📊 Export Filtered Data to CSV",
            data=grid_response['data'].to_csv(index=False).encode('utf-8'),
            file_name=f"member_data_{category}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            help="Download the currently filtered and sorted data"
        )
    with col2:    
        st.download_button(
            label="📊 Export All Data to CSV",
            data=data_merge.to_csv(index=False).encode('utf-8'),
            file_name=f"all_member_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            help="Download the complete dataset"
        )
    

if __name__ == "__main__":
    main()
