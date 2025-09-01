import streamlit as st
import pandas as pd
import pyodbc
import os
import base64
import streamlit_extras.switch_page_button  as page_switcher


#UI
st.set_page_config(layout="wide",page_title="HEDISAbstrator.AI")

st.markdown(
    """
    <style>
    .user-greeting-container {
        position: fixed; 
        top: 40px; 
        right: 0; 
        background-color: white; 
        display: flex; 
        justify-content: flex-end; 
        align-items: center; 
        padding: 10px 20px; 
        z-index: 1000; 
        width: 100%; 
        box-sizing: border-box; 
    }
    .user-greeting {
        display: flex;
        align-items: center;
        #justify-content: fixed-end; /* Align to the right */
        #padding: 10px 20px; /* Spacing for the text and icon */
        font-size: 16px;
        font-weight: bold;
        color: black;
        margin-right: 80px;
    }
    .user-greeting img {
        width: 20px;
        height: 20px;
        margin-right: 10px; /* Space between the icon and text */
    }
    .title {
        font-size: 30px;
        font-weight: bold;
        color: white;
        padding-top: 10px;
        padding-bottom: 10px;
        #padding-bottom: 50px;
        padding-right: 20px;
        padding-left: 20px;
        text-align: center;
        background-color: #fb4e0b;
        position: fixed; /* Make the title fixed at the top */
        width: 76%; 
        top: 80px;
        z-index: 9999; /* Keep it above other elements */
        #top: 0;
    }
    
    .left {
        float: left;
    }
    .right {
        float: right;

    }  
    .text {
        color: #fb4e0b;
        font-size:50px;
        font-weight: bold;
        font-style: italic;
    }
    .small-header {
        font-size: 18px;
        font-weight: bold;
        color: #000000;
        padding-top: 50px;
        padding-bottom: 5px;
        text-align: left;
        z-index: 9999;
        #top: 0;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Displaying the icon and "Hi, user" message in the top-right corner --------------Newly Added-----------
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
        <span class="left">HEDISAbstrator.AI</span>
        <span class="right">EXL</span>
    </div>
    """, unsafe_allow_html=True)




# Set the background color function


# # Function to create database connection
# def create_connection():
#     return pyodbc.connect('DRIVER={SQL Server};'
#                           'SERVER=LAPTOP-AG7RJLSV\\SQLEXPRESS;'
#                           'DATABASE=demo;'
#                           'Trusted_Connection=yes;')



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
                            f.Pdf_filename AS [File Name], 
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

# def get_join_data(measure):
#     conn= create_connection()
#     #query=f"Select Height,Weight,BMI,Obese,Smoker,Drinker,Posg_presence,Depression_history,Hospice_or_Palliative_care,r.* from memberinfo l join {measure} r on l.Member_id=r.Member_id"
#     query=f"Select * from {measure} where is_active in (1) order by Member_id"
#     return pd.read_sql(query, conn)

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

# Load data
data1 = get_data()
print(f"data1: {len(data1)}")
#l1=["FileID","Name","Age","Gender","DOB","DOS_Gen"]
#data1=data1[l1]
measures=["BCS","CBP", "HBD","BPD","EED","CCS","COL","LSD","PPC"]
category = st.selectbox('**Select Measures**',measures)

#data=get_join_data(category)
data=get_measure_data(category)
print(f"data: {len(data)}")
data=filter_df(data,0)

#columns = list(data1.columns)+list(data.columns)
columns = list(data.columns)

# data1['File Name']=data1['File Name'].str.strip()
# data['FileID']=data['FileID'].str.strip()

# print(sorted(data1.columns))
# print(sorted(data.columns))

data= data1.merge(data,how='inner',on='Member_id').drop_duplicates(subset=['FileID',
'Member_id','is_active'],keep='last').reset_index(drop=True)

print(f"data: {len(data)}")

data.sort_values(by=['Insert_Date'],ascending=True, inplace=True)
#st.write(data)
data=filter_df(data,1)
columns = list(data.columns)
#selected_columns = st.multiselect('**Select Columns**', columns, default=columns[:7])  # Display only the first 6 columns

#Rearrange columns
rearranged_columns=[]
first_column=['Measurement_Year']
remaining_columns=[i for i in data.columns if i.strip() not in  first_column]

rearranged_columns.extend(first_column)
rearranged_columns.extend(remaining_columns)
data=data[rearranged_columns]

data["Member_id"]=data["Member_id"].astype(str).str.replace(","," ")
st.subheader("Data Repository")  #--------ADDED-------



# Display the header row --------ADDED-------
cols = st.columns(len(data.columns) + 1) # +1 for the button column --------ADDED-------
for i, col_name in enumerate(data.columns):
    with cols[i]:
        st.write(f"**{col_name}**")
with cols[len(data.columns)]:
    st.write("**Action**")

for index, row in data.iterrows():
    cols = st.columns(len(data.columns) + 1)
    for i, col_name in enumerate(data.columns):
        with cols[i]:
            st.write(row[col_name])
    with cols[len(data.columns)]:
        if row['Member_id'] != "Unknown" and ['Name'] is not None:
                    
            if st.button("View", key="review_member_button"+str(row['Member_id'])+str(row['Name'])):  
                st.session_state['member_name'] = row['Name']
                st.session_state['member_id'] = row['Member_id']
                st.session_state['FileID'] = row['FileID']
                page_switcher.switch_page("ReviewMember")
        # if st.button("View", key=f"view_details_{row['Member_id']}_{row['Name']}"):  
        #     # Redirect to 'ReviewMember' page with Member_id and FileID as query parameters 
        #     st.experimental_set_query_params(page="ReviewMember", Member_id=str(row['Member_id']), Name=str(row['Name']))  
        #     st.experimental_rerun()  

st.download_button(
    label="Export to CSV",
    data=data.to_csv(index=False).encode('utf-8'),
    file_name="exported_data.csv",
    mime="text/csv",
)

st.write("Click the button above to download the CSV file.")






# st.markdown("""
# <style>
#     .st-emotion-cache-1c7y2kd { /* This targets the st.columns container */
#         padding: 0px; /* Remove default padding */
#     }
#     .cell-content {
#         border: 1px solid #e6e9ef;
#         padding: 8px;
#         min-height: 40px; /* Ensure consistent cell height */
#         display: flex;
#         align-items: center;
#     }
#     .header-cell {
#         background-color: #f8f9fa;
#         font-weight: bold;
#     }
#     .scrollable-table-container {
#         height: 400px; /* Specific height */
#         overflow-y: auto; /* Scrollable bar */
#         border: 1px solid #e6e9ef; /* Outer border for the scrollable area */
#         border-radius: 5px;
#         margin-top: 10px; /* Space from subheader */
#     }
# </style>
# """, unsafe_allow_html=True)

# # Create the scrollable container
# with st.container():
#     st.markdown('<div class="scrollable-table-container">', unsafe_allow_html=True)

#     # Display the header row
#     header_cols = st.columns(len(data.columns) + 1)
#     for i, col_name in enumerate(data.columns):
#         with header_cols[i]:
#             st.markdown(f"<div class=\'cell-content header-cell\'>{col_name}</div>", unsafe_allow_html=True)
#     with header_cols[len(data.columns)]:
#         st.markdown("<div class=\'cell-content header-cell\'>Action</div>", unsafe_allow_html=True)

#     # Display data rows
#     for index, row in data.iterrows():
#         cols = st.columns(len(data.columns) + 1)
#         for i, col_name in enumerate(data.columns):
#             with cols[i]:
#                 st.markdown(f"<div class=\'cell-content\'>{row[col_name]}</div>", unsafe_allow_html=True)
#         with cols[len(data.columns)]:
#             # Streamlit buttons cannot be directly inside st.markdown with unsafe_allow_html=True
#             # So, we place the button directly in the column, and its container will get the border from the CSS.
#             # The 'cell-content' div is not wrapped around the button here, as st.button creates its own div.
#             # We rely on the parent st.columns styling for the button cell.
#             if row["Member_id"] != "Unknown" and row["Name"] is not None: # Corrected ['Name'] to row['Name']
#                 if st.button("View", key="review_member_button"+str(row['Member_id'])+str(row['Name'])):
#                     st.session_state["member_name"] = row["Name"]
#                     st.session_state["member_id"] = row["Member_id"]
#                     st.session_state["FileID"] = row["FileID"]
#                     page_switcher.switch_page("ReviewMember")
#     st.markdown("</div>", unsafe_allow_html=True) # Close the scrollable container
# # --------ADDED-------

# st.download_button(
#     label="Export to CSV",
#     data=data.to_csv(index=False).encode("utf-8"),
#     file_name="exported_data.csv",
#     mime="text/csv",
# )

# st.write("Click the button above to download the CSV file.")





# # Display the header row --------ADDED-------
# cols = st.columns(len(data.columns) + 1) # +1 for the button column --------ADDED-------
# for i, col_name in enumerate(data.columns):
#     with cols[i]:
#         st.write(f"**{col_name}**")
# with cols[len(data.columns)]:
#     st.write("**Action**")

# for index, row in data.iterrows():
#     cols = st.columns(len(data.columns) + 1)
#     for i, col_name in enumerate(data.columns):
#         with cols[i]:
#             st.write(row[col_name])
#     with cols[len(data.columns)]:
#         if row['Member_id'] != "Unknown" and ['Name'] is not None:
                    
#             if st.button("View", key="review_member_button"+str(row['Member_id'])+str(row['Name'])):  
#                 st.session_state['member_name'] = row['Name']
#                 st.session_state['member_id'] = row['Member_id']
#                 st.session_state['FileID'] = row['FileID']
#                 page_switcher.switch_page("ReviewMember")
#         # if st.button("View", key=f"view_details_{row['Member_id']}_{row['Name']}"):  
#         #     # Redirect to 'ReviewMember' page with Member_id and FileID as query parameters 
#         #     st.experimental_set_query_params(page="ReviewMember", Member_id=str(row['Member_id']), Name=str(row['Name']))  
#         #     st.experimental_rerun()  

# st.download_button(
#     label="Export to CSV",
#     data=data.to_csv(index=False).encode('utf-8'),
#     file_name="exported_data.csv",
#     mime="text/csv",
# )

# st.write("Click the button above to download the CSV file.")




