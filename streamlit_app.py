import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots

# Set page configuration
st.set_page_config(
    page_title="Wedding Rainfall Analysis",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add title and description
st.title("Wedding Rainfall Analysis")
st.markdown("""
This application helps predict the likelihood of rain on your wedding day based on historical rainfall data.
Select your parameters and view rainfall patterns for your chosen location and date.
""")

# Function definitions from the notebook
@st.cache_data(ttl=3600, show_spinner=False)
def get_df(years=[2022, 2023, 2024]):
    
    # Data collection
    df = []
    for year in years:
        try:
            df.append(pd.read_csv(f"/workspace/wedding_rainfall_analysis/dataset/rain_{year}.csv", encoding="EUC-KR"))
        except:
            st.warning(f"Data file rain_{year}.csv not found. Either no data for this year or filename is incorrect.")
    
    if not df:
        st.error("No data files were loaded. Please check the year range and try again.")
        st.stop()
        
    df = pd.concat(df, axis=0)

    # Add English columns
    df['location'] = df['지점명']
    df['rain'] = df['강수량(mm)']

    # Preprocess date data
    df['datetime'] = pd.to_datetime(df['일시'])
    df['date'] = df['datetime'].dt.date
    
    return df


@st.cache_data(ttl=3600)
def get_df_lo_dt_eff(df, start_hour=11, end_hour=19):
    df_eff = df[(df['datetime'].dt.hour >= start_hour) & (df['datetime'].dt.hour <= end_hour)]
    df_lo_dt_eff = df_eff.groupby(['location', 'date'])['rain'].sum().reset_index()
    df_lo_dt_eff.columns = ['location', 'date', 'total_rain']
    df_lo_dt_eff = df_lo_dt_eff.pivot(index='date', columns='location', values='total_rain').fillna(0).astype(float)
    df_lo_dt_eff.index = pd.to_datetime(df_lo_dt_eff.index)

    return df_lo_dt_eff

@st.cache_data(ttl=3600)
def get_df_mon_day_eff(df_lo_dt_eff, location='서울', year_start=2022, year_end=2024):
    df_ = df_lo_dt_eff.reset_index()
    df_['date'] = pd.to_datetime(df_['date'])
    df_['years'] = df_['date'].dt.year
    df_['months'] = df_['date'].dt.month
    df_['days'] = df_['date'].dt.day
    df_['hours'] = df_['date'].dt.hour

    mask = (df_['years'] >= year_start) & (df_['years'] <= year_end)
    df_ = df_[mask]
    
    if location not in df_.columns:
        st.error(f"Location '{location}' not found in the dataset. Please choose a different location.")
        st.stop()
        
    df_lo_dt_eff_seoul = df_[[location, 'months', 'days']].copy()
    df_mon_day_eff = df_lo_dt_eff_seoul.groupby(['months', 'days'])[location].mean().reset_index()
    df_mon_day_eff.columns = ['months', 'days', 'avg_rain']
    df_mon_day_eff = df_mon_day_eff.pivot(index='months', columns='days', values='avg_rain')
    return df_mon_day_eff

@st.cache_data(ttl=3600)
def get_df_mon_day_year_eff(df_lo_dt_eff, location='서울', year_start=2022, year_end=2024, months=1, days=1):
    df_ = df_lo_dt_eff.reset_index()
    df_['date'] = pd.to_datetime(df_['date'])
    df_['years'] = df_['date'].dt.year
    df_['months'] = df_['date'].dt.month
    df_['days'] = df_['date'].dt.day
    df_['hours'] = df_['date'].dt.hour

    mask = (df_['months'] == months) & (df_['days'] == days)
    df_ = df_[mask]
    
    if location not in df_.columns:
        st.error(f"Location '{location}' not found in the dataset. Please choose a different location.")
        st.stop()
        
    df_lo_dt_eff_seoul = df_[[location, 'years']].copy()
    df_mon_day_year_eff = df_lo_dt_eff_seoul.groupby(['years'])[location].mean().reset_index()
    df_mon_day_year_eff.columns = ['years', 'avg_rain']
    return df_mon_day_year_eff

# Function to display analysis
def display_analysis(location, year_start, year_end, start_hour, end_hour, selected_month, selected_day):
    with st.spinner("Generating analysis, please wait..."):
        try:
            # Run the analysis with the selected parameters
            if 'full_data' not in st.session_state or 'data_years' not in st.session_state or set(st.session_state['data_years']) != set(range(year_start, year_end+1)):
                # Load new data
                collected_years = list(range(year_start, year_end+1))
                df = get_df(years=collected_years)
                st.session_state['full_data'] = df
                st.session_state['data_years'] = collected_years
            else:
                # Use cached data
                df = st.session_state['full_data']
            
            # Filter and process the data
            df_lo_dt_eff = get_df_lo_dt_eff(df, start_hour=start_hour, end_hour=end_hour)
            df_mon_day_eff = get_df_mon_day_eff(df_lo_dt_eff, location=location, 
                                            year_start=year_start, year_end=year_end)
            
            # Check if the location exists in the dataset
            if df_mon_day_eff is None:
                st.error(f"Location '{location}' not found in the dataset. Please choose a different location.")
                return None
            
            df_mon_day_year_eff = get_df_mon_day_year_eff(df_lo_dt_eff, location=location, 
                                                    year_start=year_start, year_end=year_end, 
                                                    months=selected_month, days=selected_day)
            
            if df_mon_day_year_eff is None:
                st.error(f"Location '{location}' not found in the dataset. Please choose a different location.")
                return None
            
            # Create a subplot with 1 row and 2 columns
            fig = make_subplots(rows=1, cols=2, 
                            subplot_titles=[
                                f"Average Rainfall in {location} ({year_start}-{year_end})",
                                f"Rainfall on {selected_month}/{selected_day} ({start_hour}-{end_hour}h)"
                            ],
                            column_widths=[0.6, 0.4])
            
            # Add heatmap to the first column - with clickable points
            heatmap = px.imshow(
                df_mon_day_eff,
                color_continuous_scale='blues',
                labels=dict(x="Day", y="Month", color="Avg Rain (mm)"),
            ).data[0]
            
            fig.add_trace(heatmap, row=1, col=1)
            
            # Update the x and y axis to show all ticks
            fig.update_xaxes(
                title_text="Day",
                tickmode='linear',
                tick0=1,
                dtick=1,
                row=1, 
                col=1
            )

            fig.update_yaxes(
                title_text="Month",
                tickmode='linear',
                tick0=1,
                dtick=1,
                row=1, 
                col=1
            )

            # Update colorbar to be closer to the heatmap
            fig.update_traces(
                colorbar=dict(
                    title="Avg Rain (mm)",
                    x=0.46,
                    thickness=20,
                    len=0.75
                ),
                selector=dict(type="heatmap")
            )

            # Add bar chart to the second column
            bar = px.bar(
                df_mon_day_year_eff,
                x='years',
                y='avg_rain',
                color_discrete_sequence=['blue'],
                labels={'years': 'Year', 'avg_rain': 'Average Rain (mm)'}
            ).data[0]
            
            fig.add_trace(bar, row=1, col=2)
            
            # Update layout
            fig.update_layout(
                height=600,
                showlegend=False,
                title_text=f"Wedding Rainfall Analysis for {location}",
                margin=dict(l=60, r=60, t=80, b=60)  # add margins
            )
            
            # Update x-axis of second subplot
            fig.update_xaxes(tickangle=-45, row=1, col=2)
            
            # Update colorbar
            fig.update_traces(
                colorbar=dict(
                    title="Avg Rain (mm)",
                    x=0.46
                ),
                selector=dict(type="heatmap")
            )
            
            # Enable clicking on the heatmap
            fig.update_layout(clickmode='event+select')
            
            # Store the dataframe in session state for clicking interaction
            st.session_state['df_mon_day_eff'] = df_mon_day_eff
            
            # Show the figure in Streamlit
            heatmap_chart = st.plotly_chart(fig, use_container_width=True)
            
            # # Show some statistics
            # col1, col2 = st.columns(2)
            
            # with col1:
            #     st.subheader("Monthly Statistics")
            #     monthly_avg = df_mon_day_eff.mean(axis=1).reset_index()
            #     monthly_avg.columns = ['Month', 'Average Rainfall']
            #     st.dataframe(monthly_avg, use_container_width=True)
                
            # with col2:
            #     st.subheader(f"Statistics for {selected_month}/{selected_day}")
            #     stats = {
            #         'Average rainfall (mm)': df_mon_day_year_eff['avg_rain'].mean(),
            #         'Maximum rainfall (mm)': df_mon_day_year_eff['avg_rain'].max(),
            #         'Years with rainfall': (df_mon_day_year_eff['avg_rain'] > 0).sum(),
            #         'Years without rainfall': (df_mon_day_year_eff['avg_rain'] == 0).sum(),
            #         'Rainfall probability': f"{(df_mon_day_year_eff['avg_rain'] > 0).mean() * 100:.1f}%"
            #     }
            #     st.dataframe(pd.DataFrame([stats]), use_container_width=True)
            
            return df_mon_day_eff
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.error("Some years might not have data available. Try a more recent range.")
            return None

# Initialize session state
if 'selected_month' not in st.session_state:
    st.session_state['selected_month'] = 5
if 'selected_day' not in st.session_state:
    st.session_state['selected_day'] = 26
if 'df_mon_day_eff' not in st.session_state:
    st.session_state['df_mon_day_eff'] = None
if 'last_click' not in st.session_state:
    st.session_state['last_click'] = None

# Sidebar for inputs
st.sidebar.header("Wedding Settings")

# Add cache control to sidebar
st.sidebar.subheader("Cache Control")
cache_status = "🟢 Using cached data" if 'full_data' in st.session_state else "🔄 No data cached yet"
st.sidebar.info(cache_status)

# Cache clearing button
if 'full_data' in st.session_state:
    if st.sidebar.button("Clear Cache and Reload Data"):
        # Clear specific items from session state
        for key in ['full_data', 'data_years', 'df_mon_day_eff']:
            if key in st.session_state:
                del st.session_state[key]
        
        # Clear function caches
        get_df.clear()
        get_df_lo_dt_eff.clear()
        get_df_mon_day_eff.clear()
        get_df_mon_day_year_eff.clear()
        
        st.sidebar.success("Cache cleared! Data will be reloaded on next analysis.")
        st.experimental_rerun()

# Location dropdown
locations = ['강릉', '강진군', '강화', '거제', '거창', '경주시', '고산', '고창', '고창군', '고흥', '광양시',
   '광주', '구미', '군산', '금산', '김해시', '남원', '남해', '대관령', '대구', '대구(기)', '대전',
   '동두천', '동해', '목포', '문경', '밀양', '백령도', '보령', '보성군', '보은', '봉화', '부산',
   '부안', '부여', '북강릉', '북부산', '북창원', '북춘천', '산청', '상주', '서귀포', '서산', '서울',
   '서청주', '성산', '세종', '속초', '수원', '순창군', '순천', '안동', '양산시', '양평', '여수',
   '영광군', '영덕', '영월', '영주', '영천', '완도', '울릉도', '울산', '울진', '원주', '의령군',
   '의성', '이천', '인제', '인천', '임실', '장수', '장흥', '전주', '정선군', '정읍', '제주', '제천',
   '주암', '진도(첨찰산)', '진도군', '진주', '창원', '천안', '철원', '청송군', '청주', '추풍령',
   '춘천', '충주', '태백', '통영', '파주', '포항', '함양군', '합천', '해남', '홍성', '홍천',
   '흑산도']

location = st.sidebar.selectbox("Location", options=locations, index=locations.index('서울'))

# Year range - using slider
st.sidebar.subheader("Year Range")
year_range = st.sidebar.slider(
    "Select Year Range",
    min_value=1994,
    max_value=2024,
    value=(2012, 2024),
    step=1
)
year_start, year_end = year_range

# Hours range - using slider
st.sidebar.subheader("Hours Range (Wedding Time)")
hour_range = st.sidebar.slider(
    "Select Hour Range",
    min_value=0,
    max_value=23,
    value=(11, 13),
    step=1
)
start_hour, end_hour = hour_range

# Specific date
st.sidebar.subheader("Specific Date to Analyze")
col1, col2 = st.sidebar.columns(2)
selected_month = col1.number_input("Month", min_value=1, max_value=12, value=5, step=1)
selected_day = col2.number_input("Day", min_value=1, max_value=31, value=26, step=1)

# Handle invalid dates
if selected_month in [4, 6, 9, 11] and selected_day > 30:
    st.sidebar.warning("Selected month has only 30 days. Day will be set to 30.")
    selected_day = 30
elif selected_month == 2:
    if selected_day > 29:
        st.sidebar.warning("February has at most 29 days. Day will be set to 28.")
        selected_day = 28

# Generate button
generate_button = st.sidebar.button("Generate Analysis", type="primary")

# Main content area
if generate_button:
    # Run analysis with current settings
    df_mon_day_eff = display_analysis(
        location, 
        year_start, 
        year_end, 
        start_hour, 
        end_hour, 
        selected_month, 
        selected_day
    )
else:
    # Show instructions when page first loads
    st.markdown("""
    ## How to use this app
    
    1. Select your wedding location from the dropdown menu
    2. Adjust the year range slider to analyze historical data
    3. Set the time range for your wedding using the hour slider
    4. Click "Generate Analysis" to see rainfall patterns
    5. Click on any date in the heatmap to see detailed statistics for that specific date
    
    ## Interactive Features
    
    - **Heatmap clicking**: Click on any day in the heatmap to analyze that specific date
    - **Sliders**: Easily adjust date ranges and times
    - **Statistics**: View detailed rainfall statistics for your selected date
    
    ## About the data
    
    This app uses historical rainfall data from the Korean Meteorological Administration.
    Data is available for different locations across Korea from 1994 to 2024.
    """)
    
# Add a footer
st.markdown("""
---
Developed for wedding planning | Data source: Korean Meteorological Administration
""")