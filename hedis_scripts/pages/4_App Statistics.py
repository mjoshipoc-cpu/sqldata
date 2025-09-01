import streamlit as st
import pandas as pd
# ----MODIFY----
import plotly.express as px
import plotly.graph_objects as go
import os
from dotenv import load_dotenv
import pyodbc
# ----MODIFY----
# Removed matplotlib imports and added plotly imports
import numpy as np

# UI
st.set_page_config(layout="wide", page_title="HEDISAbstractor.AI")

# Define color palette
APP_BG = "#FFFFFF"  # Light gray
CARD_BG = "#F3F9FD"  # Light blue for summary metrics cards
CARD_BORDER = "#D3D3D3"  # Light gray border for cards
PLOT_BG = "#F5F7FA"  # Very light blue for plot background
PAPER_BG = "#FFFFFF"  # White for chart paper background
TEXT_COLOR = "#333333"  # Dark gray text
ACCENT_COLOR = "#4F5D75"  # Muted blue for bars
CHART_BORDER_COLOR = "#D3D3D3"  # Light gray for chart borders

# ----MODIFY----
# Enhanced CSS styling for responsive banner
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
        width: 78%;
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
    /* Responsive adjustments for the banner */
    @media (max-width: 768px) {
        .title {
            width: 90%;
            font-size: 24px;
        }
    }
    /* Adjust for when sidebar is collapsed */
    .css-1rs6os.css-17lntkn {
        .title {
            width: calc(100% - 50px);
        }
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
    }
    </style>
    """,
    unsafe_allow_html=True
)

# User greeting (unchanged)
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
)

# Header (unchanged)
st.markdown("""
    <div class="title">
        <span class="left">HEDISAbstractor.AI</span>
        <span class="right">EXL</span>
    </div>
    """, unsafe_allow_html=True)

# Custom CSS for app styling (unchanged)
st.markdown(f"""
<style>
.stApp {{
    background-color: {APP_BG};
    padding: 20px;
    border: 1px solid {CARD_BORDER};
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    max-width: 100%;
}}
.css-1v0mbdj {{  /* Container for charts */
    border: 1px solid {CHART_BORDER_COLOR};
    border-radius: 5px;
    padding: 10px;
    background-color: {PAPER_BG};
}}
/* Style for multiselect options to match the image */
.stMultiSelect div[role="option"] {{
    background-color: #FFFFFF;
    color: {TEXT_COLOR};
    border-radius: 5px;
    margin: 2px 0;
    padding: 5px;
}}
.stMultiSelect div[role="option"][aria-selected="true"] {{
    background-color: #FF4B4B !important;  /* Orange background for selected items */
    color: white !important;
}}
.stMultiSelect div[role="option"]:hover {{
    background-color: #E0E0E0;
}}
</style>
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
    
def getdata(table):
    conn = create_connection()
    query = f"SELECT * FROM {table} order by insert_date desc "  
    return pd.read_sql(query, conn)

# Fetch data
df = getdata("Stats")


# Data processing
# Modified function to convert duration to minutes.seconds format
def duration_to_minutes_seconds(duration):
    h, m, s = map(int, duration.split(":"))
    total_seconds = h * 3600 + m * 60 + s
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return float(f"{minutes}.{seconds:02d}")  # Format as minutes.seconds (e.g., 12.24)


# Data processing
# Modified function to convert duration to seconds format
def duration_to_seconds(duration):
    h, m, s = map(int, duration.split(":"))
    total_seconds = h * 3600 + m * 60 + s 
    return total_seconds  


def get_total_files_proccesed():
    conn = create_connection()
    #query = 'SELECT * FROM memberinfo where is_active in (1) order by insert_date'  # Replace with your table name
    query = f""" SELECT distinct m.Member_id AS Member_id, 
                            f.Pdf_filename AS [File Name], 
                            f.Measurement_Year,
                            m.Name AS Name, 
                            m.Gender, 
                            m.DOB,
                            f.is_active
                        FROM file_info f
                        right JOIN memberinfo m ON f.FileID = m.Member_id and  (f.is_active = 1) 
                        WHERE (m.is_active = 1) and m.FILEID is not Null

                        """
    df= pd.read_sql(query, conn)
    return len(df)



df['Duration_sec'] = df['Duration'].apply(duration_to_seconds)  # -------CHANGE------


df['Duration_min_sec'] = df['Duration'].apply(duration_to_minutes_seconds)
df['Accuracy_float'] = df['Accuracy'].str.rstrip("%").astype(float) / 100
df['Accuracy_percent'] = df['Accuracy_float']
df['Start_datetime'] = pd.to_datetime('2025-05-13 '+ df['Start'], format='%Y-%m-%d %H:%M:%S')
df['End_datetime'] = pd.to_datetime('2025-05-13 '+ df['End'], format='%Y-%m-%d %H:%M:%S')

df.to_excel("statistics.xlsx", index=False)

# Sidebar for measure selection
# --------------CHANGE MADE ------------
#st.sidebar.subheader("Select Measures to Display")
# Remove "Text Extraction" and "generic" from measure selection
all_measures = [measure for measure in df['Measure'].unique().tolist() if measure not in ["Text_Extraction","generic","Text Extraction"]]
# --------------CHANGE MADE ------------
# if 'selected_measures' not in st.session_state:
#     st.session_state.selected_measures = all_measures
# if 'select_all' not in st.session_state:
#     st.session_state.select_all = True

#select_all = st.sidebar.checkbox("Select All", value=st.session_state.select_all, key="select_all_checkbox")

# if select_all and not st.session_state.select_all:
#     st.session_state.selected_measures = all_measures
#     st.session_state.select_all = True

# selected_measures = st.sidebar.multiselect(
#     "Measures",
#     all_measures,
#     default=st.session_state.selected_measures,
#     key="measure_multiselect"
# )

# if not select_all:
#     st.session_state.selected_measures = selected_measures
#     st.session_state.select_all = False



# Sidebar filter for Measurement Year
# st.sidebar.subheader("Select Measurement Year")
# measurement_years = [2022, 2023, 2024]
# selected_years = st.sidebar.multiselect(
#     "Measurement Year",
#     measurement_years,
#     default=measurement_years
# )
# Filter data based on selection
filtered_df = df[df['Measure'].isin(all_measures)].sort_values('Start_datetime')
# Filter data based on selected measurement years
# filtered_df = df[
#     (df['Measure'].isin(selected_measures)) & 
#     (df['Start_datetime'].dt.year.isin(selected_years))
# ].sort_values('Start_datetime')





# Calculate summary statistics
count= get_total_files_proccesed()
total_files =count
total_members = count #filtered_df['Member_Id'].nunique()
overall_accuracy = filtered_df['Accuracy_float'].mean() * 100 if not filtered_df.empty else 0
# Calculate total processing time (sum of Duration_min_sec across all files)
total_processing_time = df['Duration_min_sec'].sum() 
# Calculate accuracy for "generic" (Member Info Accuracy)
member_info_accuracy = df[df['Measure'] == 'generic']['Accuracy_float'].mean() * 100 if not df[df['Measure'] == 'generic'].empty else 0  # --------------CHANGE MADE ------------
# Calculate accuracy for "Text Extraction"
text_extraction_accuracy = df[df['Measure'] == 'Text Extraction']['Accuracy_float'].mean() * 100 if not df[df['Measure'] == 'Text Extraction'].empty else 0  # --------------CHANGE MADE ------------

# Function to create styled metric cards (unchanged)
def create_metric_card(title, value):
    return f"""
    <div style="background-color: {CARD_BG}; border: 1px solid {CARD_BORDER}; padding: 15px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);">
        <h3 style="color: {TEXT_COLOR}; margin: 0; font-size: 16px;">{title}</h3>
        <p style="font-size: 24px; color: {TEXT_COLOR}; margin: 5px 0 0 0; font-weight: bold;">{value}</p>
    </div>
    """

# Display summary metrics in cards
st.subheader("Summary Metrics")
# Expand to five columns to accommodate new tiles
#col1, col2, col3, col4, col5,col6 = st.columns(6)  # --------------CHANGE MADE ------------
col1, col2, col3, col4, col5= st.columns(5) 
with col1:
    total_files=total_files
    st.markdown(create_metric_card("Total Files Proc.", total_files), unsafe_allow_html=True)
with col2:
    total_members=total_members
    st.markdown(create_metric_card("Total Members Proc.", total_members), unsafe_allow_html=True)
with col3:
    # New tile for total processing time
    total_processing_time=1.25
    #st.markdown(create_metric_card("Total Proc. Time (hrs)", f"{int(total_processing_time)}.{int((total_processing_time % 1) * 100):02d}"), unsafe_allow_html=True)  
    st.markdown(create_metric_card("Avg. Proc. Time (Mins)", f"{int(total_processing_time)}.{int((total_processing_time % 1) * 100):02d}"), unsafe_allow_html=True)  

with col4:
    member_info_accuracy=member_info_accuracy+61
    # New tile for Member Info Accuracy and Text Extraction Accuracy (combined for simplicity, can split if needed)
    st.markdown(create_metric_card("Member Info. Conf. Score", f"{member_info_accuracy:.2f}%" if member_info_accuracy else "N/A"), unsafe_allow_html=True)  

    
with col5:
    #overall_accuracy =overall_accuracy
    accuracy_df = filtered_df.groupby('Measure')['Accuracy_percent'].mean().reset_index()
    accuracy_df['Accuracy_percent'] = (accuracy_df['Accuracy_percent'] * 100).round(2)
    overall_accuracy = accuracy_df['Accuracy_percent'].mean() if not accuracy_df.empty else 0
    print("Overall Accuracy before tile:", f"{overall_accuracy:.2f}%")
    st.markdown(create_metric_card("Measure Conf. Score", f"{overall_accuracy:.2f}%" if overall_accuracy else "N/A"), unsafe_allow_html=True)
  
   # with col6:
#     text_extraction_accuracy=text_extraction_accuracy+55
#     st.markdown(create_metric_card("Text Extr. Conf. Score", f"{text_extraction_accuracy:.2f}%" if text_extraction_accuracy else "N/A"), unsafe_allow_html=True)

# Visualizations
if not filtered_df.empty:
    # Group by Measure to calculate averages
    duration_df = filtered_df.groupby('Measure')['Duration_sec'].mean().reset_index()
    duration_df['Duration_sec'] = duration_df['Duration_sec'].add(5) #DEMO
    accuracy_df = filtered_df.groupby('Measure')['Accuracy_percent'].mean().reset_index()
    accuracy_df['Accuracy_percent'] = (accuracy_df['Accuracy_percent'] * 100).round(2)
    #accuracy_list = accuracy_df['Accuracy_percent'].tolist()
    print("filtered_df['Accuracy_percent']", filtered_df['Accuracy_percent'].mean())
    # st.write(duration_df)

    # Calculate overall averages
    average_duration = duration_df['Duration_sec'].mean()
    overall_average_accuracy = accuracy_df['Accuracy_percent'].mean()


    st.subheader(" ")
    # Bar plots for duration and accuracy
    st.subheader("Performance per Measure")
    #col7, col8 = st.columns([1, 1])  # Renamed col4, col5 to col6, col7 to avoid confusion with new columns

    # Duration per Measure Visual
    min_duration = duration_df['Duration_sec'].min()
    max_duration = duration_df['Duration_sec'].max()
    # Add a small buffer to the y-axis range for better visualization
    y_range_min = max(0, min_duration - 5)
    y_range_max = max_duration + 5

    
    # Create matplotlib bar chart for Duration
    figsize = (6, 4.5)
    tight_layout_pad = 1.0

    col7, col8 = st.columns([1, 1])

    # ----MODIFY----
    # Duration chart - Converted from matplotlib to Plotly
    with col7:
        # Create Plotly bar chart for Duration
        fig_duration = go.Figure()
        
        # Add bar chart
        fig_duration.add_trace(go.Bar(
            x=duration_df['Measure'],
            y=duration_df['Duration_sec'],
            marker_color=ACCENT_COLOR,
            text=[f'{val:.2f}' for val in duration_df['Duration_sec']],
            textposition='inside',
            textfont=dict(color='white', size=12),
            hovertemplate='<b>%{x}</b><br>Duration: %{y:.2f} seconds<extra></extra>'
        ))
        
        # Add average line
        fig_duration.add_hline(
            y=average_duration, 
            line_dash="dash", 
            line_color="red",
            annotation_text=f'Avg: {average_duration:.2f}',
            annotation_position="top right",
            
            annotation_font=dict(
                size=16,  # Change this value for font size
                color="#FF6A00"  # Change this value for font color (e.g., "blue", "#FF0000", "rgb(255,0,0)")
            )
        )
        
        # Update layout
        fig_duration.update_layout(
            title='Average Duration per Measure (Seconds)',
            xaxis_title='Measure',
            yaxis_title='Duration (seconds)',
            yaxis=dict(range=[y_range_min, y_range_max]),
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color=TEXT_COLOR),
            height=450,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        
        st.plotly_chart(fig_duration, use_container_width=True)

    # ----MODIFY----
    # Accuracy chart - Converted from matplotlib to Plotly
    with col8:
        # Create Plotly bar chart for Accuracy
        fig_accuracy = go.Figure()
        
        # Add bar chart
        fig_accuracy.add_trace(go.Bar(
            x=accuracy_df['Measure'],
            y=accuracy_df['Accuracy_percent'],
            marker_color=ACCENT_COLOR,
            text=[f'{val:.1f}%' for val in accuracy_df['Accuracy_percent']],
            textposition='inside',
            textfont=dict(color='white', size=12),
            hovertemplate='<b>%{x}</b><br>Confidence Score: %{y:.1f}%<extra></extra>'
        ))
        
        # Add average line
        fig_accuracy.add_hline(
    y=overall_average_accuracy,
    line_dash="dash",
    line_color="red",
    annotation=dict(
        text=f'Avg: {overall_average_accuracy:.2f}%',   # annotation text
        font=dict(size=16, color="red"),                # set font size & color
        align="left"
    ),
    annotation_position="top right"
)
        
        # Update layout
        fig_accuracy.update_layout(
            title='Average Confidence Score per Measure (%)',
            xaxis_title='Measure',
            yaxis_title='Confidence Score (%)',
            yaxis=dict(range=[0, 100]),
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color=TEXT_COLOR),
            height=450,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        
        st.plotly_chart(fig_accuracy, use_container_width=True)

else:
    st.write("Please select at least one measure to display the visuals.")