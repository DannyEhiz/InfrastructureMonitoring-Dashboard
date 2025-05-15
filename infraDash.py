import streamlit as st 
from streamlit_extras.stylable_container import stylable_container
from streamlit_option_menu import option_menu
import datetime
from datetime import datetime, timedelta
import threading
import time, requests
import os
import schedule, subprocess
import queue
from streamlit_autorefresh import st_autorefresh
# import shelve
import signal
import atexit
import gc # Garbage collector
# from memory_profiler import profile
# import tracemalloc
# import objgraph
from infraChatInstruction import googleModelInstruction
from connection import connectClientDB
import logging
from logging.handlers import RotatingFileHandler
import psutil
import ast
from streamlit_chat import message
from tinydb import TinyDB, Query, where

st.set_page_config(
    page_title = 'InfraObservatory', 
    page_icon = ':bar_chart:',
    layout = 'wide'
)


st.markdown("""
    <style>
        .reportview-container {
            margin-top: -2em;
        }
        #MainMenu {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        #stDecoration {display:none;}
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def importLibraries():
    import plotly.express as px 
    import plotly.graph_objects as go 
    import sqlite3 
    import pathlib 
    from streamlit.components.v1 import html 
    import streamlit_antd_components as antd 
    import streamlit_shadcn_ui as shad 
    import pandas as pd        
    import numpy as np 
    import json 
    import warnings 
    warnings.filterwarnings('ignore') 
    from calculations import InfraCalculate as inf 
    return go, px, sqlite3, pathlib, html, antd, pd, np,  json, warnings, inf, shad 
go,  px, sqlite3, pathlib, html, antd, pd, np, json, warnings, inf, shad = importLibraries() 


import logging
from logging.handlers import RotatingFileHandler
import os

# Logger setup should run once per Streamlit rerun
logger = logging.getLogger('dashboard_logger')

# Avoid duplicate handlers on reruns
if logger.hasHandlers():
    logger.handlers.clear()
logger.setLevel(logging.DEBUG)
os.makedirs('logs', exist_ok=True)

# Formatter for logs
log_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)s | %(name)s | %(module)s | %(funcName)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Rotating handler for general logs (INFO and above)
file_handler_info = RotatingFileHandler(
    'logs/app.log', maxBytes=5*1024*1024, backupCount=7
)
file_handler_info.setLevel(logging.INFO)
file_handler_info.setFormatter(log_formatter)

# Rotating handler for errors (ERROR and above)
file_handler_error = RotatingFileHandler(
    'logs/error.log', maxBytes=5*1024*1024, backupCount=10
)
file_handler_error.setLevel(logging.ERROR)
file_handler_error.setFormatter(log_formatter)

# Attach handlers to logger
logger.addHandler(file_handler_info)
logger.addHandler(file_handler_error)


@st.cache_data(ttl=120) # Cache for 2 minutes
def fetch_data():
    try:
        conn = sqlite3.connect('EdgeDB.db')
        query = "SELECT * FROM Infra_Utilization;"
        dataset = pd.read_sql_query(query, conn)
        reduceInt = ['CPUUsage', 'MemoryUsage', 'DiskUsage', 'TotalDiskSpaceGB', 'TotalFreeDiskGB', 'TotalMemory', 'DiskLatency', 'ReadLatency', 'WriteLatency']
        dataset[reduceInt] = dataset[reduceInt].apply(pd.to_numeric, downcast='integer') # reduce to the barest int memory scale
        turnToCategory = [ 'NetworkTrafficReceived', 'NetworkTrafficSent', 'NetworkTrafficAggregate']
        dataset[turnToCategory] = dataset[turnToCategory].astype('category') # turn large numbers to categories
        conn.close()
        logger.info("Data fetched successfully from SQLite database.")
        return dataset
    except Exception as e:
        logger.error(f"Error fetching data: {e}", exc_info=True)
    finally:
        del conn, dataset
        gc.collect()
        del gc.garbage[:]


# get the full data
if 'fullData' in globals() or 'fullData' in locals():
    fullData.drop(fullData.index, inplace=True) 
    fullData = None
gc.collect()
del gc.garbage[:]
fullData = fetch_data()
availableHosts = fullData.Hostname.unique().tolist()

# Config Variables 
@st.cache_resource()
def getConfig():
    with open('config.json') as config_file:
        configVar = json.load(config_file)
    return configVar
configVar = getConfig()
clientServer = configVar['client_server']
clientDB = configVar['client_db']
clientDBUserName = configVar['client_db_username']
clientDBPass = configVar['client_db_password']
client_table_name1 = configVar['client_table_name1']
client_table_name2 = configVar['client_table_name2']

# import bootstrap 
# @st.cache_resource()
# def css_cdn():
#     return  st.markdown('<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">', unsafe_allow_html=True)
# css_cdn()

#Load css file
@st.cache_resource()
def load_css(filePath:str):
    with open(filePath) as f:
        st.html(f'<style>{f.read()}</style>')
css_path = pathlib.Path('style.css')
load_css(css_path)

    # Create a sub process that runs the dataRefresh on a seperate resource (updates the data using a seperate resource)
    # Schedules this dataRefresh to take place every 3minutes 
    # then runs the entire sub process and scheduling every 3minutes on a different thread so it doesnt disturb the dashboard 
# Function to run dataRefresh.py
# def run_data_refresh():
#     """Calls the dataRefresh.py script as a separate process."""
#     subprocess.run(["python", "dataRefresh2.py"])
#     gc.collect()
#     # print(f"Data refresh completed at {time.strftime('%Y-%m-%d %H:%M:%S')}")

# def schedule_data_refresh():
#     """Schedules the data refresh task to run every 2 minutes.""" 
#     schedule.every(2).minutes.do(run_data_refresh)
#     while True:
#         schedule.run_pending()
#         gc.collect()
#         # time.sleep(10)  # Sleep for 2 minutes

# # Keep a refresh history db to know if the refresh has been started
# def saveRefreshHistory():
#     with shelve.open('interfaceRefresh.db') as db:
#         db['hasRefreshed'] = True 
# def checkRefreshHistory():
#     with shelve.open('interfaceRefresh.db') as db:
#         return True if 'hasRefreshed' in db else False 

# this is so that a new instance of the refresh thread will not be called upon page reload
# if not checkRefreshHistory(): #If the refreshed hasnt been started
#     # Start the scheduler in a separate thread
#     data_refresh_thread = threading.Thread(target=schedule_data_refresh, daemon=True)
#     data_refresh_thread.start()
#     st.session_state['data_refresh_thread'] = data_refresh_thread
#     saveRefreshHistory()
#     gc.collect()
# else:
#     pass
 
# Register a function to delete the interface refresh history upon exit of program 
def deleteRefreshHistory():
    if os.path.exists('interfaceRefresh.db'):
        os.remove('interfaceRefresh.db')
    else:
        pass
atexit.register(deleteRefreshHistory)

maxdate = fullData.LogTimestamp.max()
if 'autoDataRefreshHelper' not in st.session_state:
    st.session_state['autoDataRefreshHelper'] = 0
if 'latestLog' not in st.session_state:
    st.session_state['latestlog'] = datetime.now()

# Get the maximum date from the data and use it as the stop date at default
if 'stopDate' not in st.session_state:
    st.session_state['stopDate'] = maxdate
    st.session_state['usageMonitor'] = 0  # monitor the number of times the has been ran.

if 'startDate' not in st.session_state:
    st.session_state['startDate'] = (datetime.strptime(maxdate, "%Y-%m-%d %H:%M:%S") - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")  # Start should be set to 2hours before the stop date

if 'startTime' not in st.session_state:
    st.session_state['startTime'] = "00:00:00"  # Default start time

if 'stopTime' not in st.session_state:
    st.session_state['stopTime'] = "23:59:59"  # Default stop time

if 'timeDisplay' not in st.session_state:
    st.session_state['timeDisplay'] = 'RelativeTime' 

color_continuous_scales = [
                        (0.0, "#F93827"),  # Red for 0 to 70
                        (0.7, "#F93827"),  # Red continues until 70
                        (0.7, "#FFF574"),  # Yellow starts at 70
                        (0.85, "#FFF574"), # Yellow continues until 85
                        (0.85, "#00FF9C"), # Green starts at 85
                        (1.0, "#00FF9C")   # Green continues until 100
                    ]

# st.session_state.latestlog = inf(fullData).latestLog

# A callback function to update the data when the user selects a new date or time
def updateDateAndTime():
    if st.session_state.datech:
        # Check if the user selected one or both dates
        if len(st.session_state.datech) == 2:
            start_, stop_ = st.session_state.datech
        else:
            # Default stop date to the start date if only one date is selected
            start_ = st.session_state.datech[0]
            stop_ = start_ + timedelta(days=1)  
    if st.session_state.strTime:
        st.session_state['startTime'] = st.session_state.strTime
    if  st.session_state.stpTime:   
        st.session_state['stopTime'] = st.session_state.stpTime
    st.session_state['startDate'] = f"{start_} {st.session_state['startTime']}"
    st.session_state['stopDate'] = f"{stop_} {st.session_state['stopTime']}"
    st.session_state['autoDataRefreshHelper'] += 1
 
# Navigation Bar Top 
head1, head2, head3 = st.columns([1, 4, 1])
with head2:
    head2.markdown(""" 
    <div class="heading">
            <p style=" font-size: 2.7rem; font-weight: bold; color: white; text-align: center; font-family: "Source Sans Pro", sans-serif">Infrastructure Monitoring System</p>
    </div>""", unsafe_allow_html=True)


# collect problems to display on the frontend 
with sqlite3.connect('EdgeDB.db') as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='openProblems';")
    table_exists = cursor.fetchone()
    if table_exists:
        allProblems = pd.read_sql('select * from openProblems', conn)
        allProblems['first_breach_date'] = pd.to_datetime(allProblems['first_breach_date'])

        nows = datetime.now().strftime("%Y:%m:%d, 00:00:00")
        totalOpen = allProblems[allProblems['status'] =='OPEN'].shape[0]

        totalClose = allProblems[
            (allProblems['status'] == 'CLOSED') &  
            (allProblems['first_breach_date'].apply(lambda x: x.strftime("%Y:%m:%d, 00:00:00")) >= nows) 
        ].shape[0]
    


# tab2, "🗃 Chat With Metrics",
tab1,tab2,  tab3 = st.tabs(["📈 System Metrics", "🗃 Chat With Metrics", ":clock2: Alert Configurations"])
with tab1:
    st_autorefresh(interval=1 * 60 * 1000, key="interfaceRefresher")
    containerOne = tab1.container()
    with containerOne:
        extra, col1, col2, col3, col4, col5, col6, col7, col8 = containerOne.columns([1.3,0.8, 0.6, 0.6, 0.6, 1, 1, 0.6, 0.6])
        with extra:
            st.markdown(f"""
            <div style="display: flex; justify-content: space-around; width: 100%">
                <div style="border: 1px solid #716C6C; margin-top:2px; padding-top: 5px; width: 130px; text-align: center; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2); height: 58px; font-family: 'Arial', sans-serif; margin-right: 5px">
                    <div style="font-weight: bold; font-size: 12px; padding-top:3px">Open Problem</div>
                    <div style="color: #FF1700; font-size: 15px; ">{totalOpen}</div>
                </div>
                <div style="border: 1px solid #716C6C;margin-top: 2px; padding-top: 5px; width: 130px; text-align: center; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2); height: 58px; font-family: 'Arial', sans-serif;margin-left: 5px">
                    <div style="font-weight: bold; font-size: 12px; padding-top:3px">Closed Problem</div>
                    <div style="color: #b3f361; font-size: 15px;">{totalClose}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)


        metricCheck = fullData.groupby('Hostname').agg( 
            LogTimestamp=('LogTimestamp', 'last'),
            CPUUsage=('CPUUsage', 'last'), 
            MemoryUsage=('MemoryUsage', 'last'), 
            TotalFreeDisk=('TotalFreeDiskGB', 'last'), 
        ).reset_index()
        highCPUUsageCount = metricCheck[metricCheck['CPUUsage'] > 85].shape[0]
        highMemUsageCount = metricCheck[metricCheck['MemoryUsage'] > 85].shape[0]
        lowDiskSpaceCount = metricCheck[metricCheck['TotalFreeDisk'] < 10].shape[0]

        with col2:
            st.warning(f"CPU: {highCPUUsageCount}")
            # shad.badges([(f"CPU {calc.highCPUUsageCount}", "destructive")], class_name="flex gap-2",)
        with col3:
            st.warning(f"Mem: {highMemUsageCount}")
            # shad.badges([(f"Mem {calc.highMemUsageCount}", "destructive")], class_name="flex gap-2",)
        with col4:
            st.warning(f"Low Disk: {lowDiskSpaceCount}")
            # shad.badges([(f"Disk {calc.highDiskUsageCount}", "destructive")], class_name="flex gap-2",)
        allProblems, totalClose, totalOpen = None, None, None
        gc.collect()
        del gc.garbage[:]
        
        twoDaysAwayFromFulldataMinDate = pd.to_datetime(fullData.LogTimestamp.min()).strftime('%Y-%m-%d')

        def timeChange(): # A nudge to tell if the time filter is clicked, so as to adjust the data supplied to the dashboard
            st.session_state['timeChange'] = True
            return st.session_state['timeChange']

        with col7:
            st.number_input(label='Time Range', min_value=1, max_value=60, step=1, key='timeRange', help='Select the range of time you want view data for. This is only applicable when you select Relative Time', value = 5, on_change=timeChange)
            st.session_state['timeClicked'] = True
        with col8:
            st.selectbox(label='Time Unit', options=['Minutes', 'Hours', 'Days'], key='timeUnit', help='Select the unit of time for the range you selected. This is only applicable when you select Relative Time', index=0, on_change=timeChange)
            st.session_state['timeClicked'] = True
    
        allProblems, totalClose, totalOpen = None , None, None
        del allProblems, totalClose, totalOpen
        gc.collect()
        del gc.garbage[:]
        # Date and Time set Up -------------------------------------- 
        # with col5:
        #     st.selectbox(label='Time Selection Type', options=['Relative Time', 'Date And Time'], key='timeType', help='Select the type of time range you want to use. Relative Time allows you to select a time range from the current time, while Date and Time allows you to select a specific time range', index=0, )
        # if st.session_state.timeType == 'Relative Time':
        #     with col6:
        #         st.number_input(label='Select Time Range', min_value=1, max_value=60, step=1, key='timeRange', help='Select the range of time you want view data for. This is only applicable when you select Relative Time')
        #     with col7:
        #         st.selectbox(label='Select Time Unit', options=['Minutes', 'Hours', 'Days'], key='timeUnit', help='Select the unit of time for the range you selected. This is only applicable when you select Relative Time')
        #     st.session_state['timeDisplay'] = 'RelativeTime'
        # else:
        #     controlDates = col6.date_input(
        #             "Preferred Date Range",
        #             value=(st.session_state['startDate'], st.session_state['stopDate']), min_value= (pd.to_datetime(twoDaysAwayFromFulldataMinDate) - timedelta(days=2)).strftime('%Y-%m-%d')  ,
        #             max_value=fullData.LogTimestamp.max(),
        #             format="YYYY-MM-DD", 
        #             help='Select Start and Stop Date. If you select only start date, the app automatically selects the nextday as the stop date. Endeavour to select the start and stop dates to ensure your intended range is depicted correctly',
        #             on_change=updateDateAndTime, key = 'datech')
        #     starttime = col7.time_input('Start Time', step = 300, help = 'Specify the start time for your selected date range. This time indicates when the data extraction or analysis should begin onthe start date', key = 'strTime', on_change=updateDateAndTime)
        #     stoptime = col8.time_input('Stop Time', step = 300, help = 'Specify the stop time for your selected date range. This time marks when the data extraction or analysis should end on the stop date', key = 'stpTime', on_change=updateDateAndTime)
        #     st.session_state['timeDisplay'] = 'DateAndTime'
    if st.session_state.timeUnit == 'Minutes':
        startdate = (datetime.strptime(maxdate, "%Y-%m-%d %H:%M:%S") - timedelta(minutes=st.session_state.timeRange)).strftime("%Y-%m-%d %H:%M:%S")
        st.session_state['data'] = fullData[fullData.LogTimestamp >= startdate]
        st.session_state.data['HostAndIP'] = st.session_state['data']['Hostname'] + ' ' + st.session_state['data']['IPAddress'].str.replace('"', '')
    elif st.session_state.timeUnit == 'Hours':
        startdate = (datetime.strptime(maxdate, "%Y-%m-%d %H:%M:%S") - timedelta(hours=st.session_state.timeRange)).strftime("%Y-%m-%d %H:%M:%S")
        st.session_state['data'] = fullData[fullData.LogTimestamp >= startdate]
        st.session_state.data['HostAndIP'] = st.session_state['data']['Hostname'] + ' ' + st.session_state['data']['IPAddress'].str.replace('"', '')
    elif st.session_state.timeUnit == 'Days':
        startdate = (datetime.strptime(maxdate, "%Y-%m-%d %H:%M:%S") - timedelta(days=st.session_state.timeRange)).strftime("%Y-%m-%d %H:%M:%S")
        st.session_state['data'] = fullData[fullData.LogTimestamp >= startdate]
        st.session_state.data['HostAndIP'] = st.session_state['data']['Hostname'] + ' ' + st.session_state['data']['IPAddress'].str.replace('"', '')
    else:
        pass 

    # st.write(st.session_state['data'].sort_values(ascending = False, by = 'LogTimestamp'))
    if st.session_state['data'].empty:
        st.error('data is empty')
        st.session_state["data_empty"] = True
    else:
        st.session_state["data_empty"] = False

    # TODO: timeChange should be set to False
    # keep track any change in time so the data can be reloaded 
    if 'timeChange' in st.session_state and st.session_state.timeChange:
        st.session_state['filteredData'] = st.session_state['data'] # !important: this is needed to refresh the data if there be an update in the data

    

    def updateFilter(): # Define a callback function to update the data when  filters selected
           # Apply each filter dynamically
           st.session_state['filteredData'] = st.session_state['data']
           if st.session_state.ao != "Default":
               st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']["ApplicationOwner"] == st.session_state.ao]
           if st.session_state.an != "Default":
               st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']["ApplicationName"] == st.session_state.an]
           if st.session_state.vend != "Default":
               st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']["vendor"] == st.session_state.vend]
           if st.session_state.dc != "Default":
               st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']["DataCenter"] == st.session_state.dc]
           if st.session_state.mz != "Default":
               st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']["ManagementZone"] == st.session_state.mz]
           if st.session_state.oss != "Default":
               st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']["OS"] == st.session_state.oss]

           st.session_state.filter_is_clicked = True # an indicator to know if filter is clicked

 
    # we need the data to rerun upon refresh so to update the data and we need to reinstate the user state 
    def filter_state_handler():
        st.session_state['filteredData'] = st.session_state.data.sort_values(ascending = False, by = 'LogTimestamp')
        if 'filter_is_clicked' in st.session_state:  #! important: Chcecks if the filter has been intercted with
            updateFilter()  # reinstate the user filter state

    filter_state_handler()  #! important: restores the users selected filter 
    
    del fullData
    fullData = None
    gc.collect()
    del gc.garbage[:]

    # get total servers from sqlite3 
    @st.cache_resource(ttl=120) # Cache for 1 minute
    def total_servers():
        with sqlite3.connect('EdgeDB.db') as conn:
            query = "SELECT COUNT(DISTINCT IPAddress) FROM Infra_Utilization;"
            cursor = conn.cursor()
            cursor.execute(query)
            totalServers = cursor.fetchone()[0]
            return totalServers
    totalServers=total_servers()      

    @st.fragment
    def filters():
        #  -------------------------------------------------- Filters Container --------------------------------------------------
        with stylable_container(
                key="container_with_borders",
                css_styles="""{
                        # background: #7474A3;
                        box-shadow: rgba(0, 0, 0, 0.15) 0px 5px 15px 0px;
                        border-radius: 0.3rem;
                        padding-bottom: 5px;
                        margin-top: -10px
                    }"""):
  
            appOwnerOptions = [option for option in st.session_state['filteredData']['ApplicationOwner'].unique().tolist()+['Default'] if option in st.session_state['filteredData']['ApplicationOwner'].unique().tolist()  or option == 'Default']
            appNameOptions = [option for option in st.session_state['filteredData']['ApplicationName'].unique().tolist()+['Default'] if option in st.session_state['filteredData']['ApplicationName'].unique().tolist()  or option == 'Default']
            vendorOptions = [option for option in st.session_state['filteredData']['vendor'].unique().tolist()+['Default'] if option in st.session_state['filteredData']['vendor'].unique().tolist()  or option == 'Default']
            dataCenterOptions = [option for option in st.session_state['filteredData']['DataCenter'].unique().tolist()+['Default'] if option in st.session_state['filteredData']['DataCenter'].unique().tolist()  or option == 'Default']
            mgtZoneOptions = [option for option in st.session_state['filteredData']['ManagementZone'].unique().tolist()+['Default'] if option in st.session_state['filteredData']['ManagementZone'].unique().tolist()  or option == 'Default']
            osOptions = [option for option in st.session_state['filteredData']['OS'].unique().tolist()+['Default'] if option in st.session_state['filteredData']['OS'].unique().tolist()  or option == 'Default']  
                    
            col7, appOwner, appName, vendor, dataCenter, mgtZone, os = st.columns([3, 1.3, 1.3, 1, 1, 1.3, 1.3])
            appOwner.selectbox('Application Owner', appOwnerOptions, index=len(appOwnerOptions)-1, key='ao', on_change=updateFilter)
            appName.selectbox('Application Name', appNameOptions, index=len(appNameOptions)-1, key='an', on_change=updateFilter)
            vendor.selectbox('Vendor', vendorOptions, index=len(vendorOptions)-1, key='vend', on_change=updateFilter, args=('vend', 'vendor'))
            dataCenter.selectbox('Data Center', dataCenterOptions, index=len(dataCenterOptions)-1, key='dc', on_change=updateFilter)
            mgtZone.selectbox('Management Zone', mgtZoneOptions, index=len(mgtZoneOptions)-1, key='mz', on_change=updateFilter)
            os.selectbox('Operating System', osOptions, index=len(osOptions)-1, key='oss', on_change=updateFilter)    

            st.session_state['selectedServer'] = st.session_state['filteredData'].HostAndIP.iloc[0] if not st.session_state['filteredData'].empty else "No servers available"
            # st.session_state['metricData'] = st.session_state['filteredData'].query("HostAndIP == @st.session_state['selectedServer']")

        serverMetrics()
 
    if 'filter_is_clicked' not in st.session_state: # important declaration to register filter_is_clicked in session_state.
        st.session_state.filter_is_clicked = False # an indicator to know if filter is clicked

        # ------------------------------------------------------- Server Metrics Container -------------------------------------------------------
    @st.fragment
    def serverMetrics(): 
        def updateServerMetrics(): # Callback function to update the server metrics when a new server is selected
            if st.session_state.serverList != 'Reset Selection':
                #! We need to do 2 things: 
                    #! 1. We need to filter the data to suit the selected serverList.  
                    #! 2. if the selected serverList is not in the HostAndIP column, we need to reset the serverList to the selectedServer (above in line 450)
                updateFilter() # refresh the filteredData to update it while also restoring the user selected top filter
                #* we check if the selected serverList is in the filteredData, if it is, we filter the data to suit the selected serverList
                #* but if not, restore the serverList to st.session_state['selectedServer'] variable so to acomodate the new hostAndIPs there
                if st.session_state['serverList'] in st.session_state['filteredData']['HostAndIP'].unique().tolist():
                        st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']['HostAndIP'] == st.session_state['serverList']]
                else:
                    st.session_state['serverList'] = st.session_state.selectedServer
                
                gc.collect()
            else:
                updateFilter() # if the selected serverList is resetSelection, reset the filteredData to default by recalling the updateFilter
                
        if 'serverListLoaded' in st.session_state and st.session_state['serverListLoaded']:
            updateServerMetrics()

          

        # if the filter is changed or the time is changed, reload the data to match with the updated data
        # if st.session_state.filter_is_clicked or ('timeChange' in st.session_state and st.session_state.timeChange):
        #     st.session_state['metricData'] = st.session_state.filteredData
        #     st.session_state.filter_is_clicked = False # reset filterCLicked indicator
        #     st.session_state.timeChange = False

        #- at the intial refresh, metricData will not exist, create it
        #- because we will delete the metricData later to avoid memory leakage, we have to save the user selections so that we can restore the user selection again upon refresh
        # if 'metricData' not in st.session_state: # if metricData is not in session state, create it
        #     if 'serverList' in st.session_state: # check if user has previosuly selected something, if they have, restore the data to the users selection
        #         st.session_state['metricData'] = st.session_state['filteredData'].query("HostAndIP == @st.session_state['serverList']") # restore data to user selection
        #     else: # but if they havent, cotinue with the fulldata
        #         st.session_state['metricData'] = st.session_state.filteredData      
    
        containerTwo = st.container()
        with containerTwo:
            col1, col2, col3, col4, col5, col6, col7, col8 = containerTwo.columns([2,1.5,2,1,1,1,1,1])
            with col1:
                col1.markdown(f"""
                        <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: -7px; padding-top: 5px; align-items: center; justify-content: space-between; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Op System</p>
                                <p style="margin-top: -15px; font-size: 14px; color: #B3F361; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{st.session_state.filteredData.OS.iloc[0] if 'serverList' in st.session_state else st.session_state['filteredData'].query("HostAndIP == @st.session_state['selectedServer']")['OS'].iloc[0] }</p>
                        </div> """, unsafe_allow_html= True) # ! use the selected ServerList info if its available in sessionState, else use intial selected server
            with col2:
                col2.markdown(f"""
                        <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: -7px; padding-top: 5px; align-items: center; justify-content: space-between; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Hostname</p>
                                <p style="margin-top: -15px; font-size: 14px; color: #B3F361; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{st.session_state.filteredData.HostAndIP.iloc[0] if 'serverList' in st.session_state else st.session_state['filteredData'].query("HostAndIP == @st.session_state['selectedServer']")['HostAndIP'].iloc[0]} </p>
                        </div> """, unsafe_allow_html= True)
            with col3:
                col3.markdown(f"""
                        <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: -7px; padding-top: 5px; align-items: center; justify-content: space-between; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >IP Address</p>
                                <p style="margin-top: -15px; font-size: 14px; color: #B3F361; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{st.session_state.filteredData.IPAddress.iloc[0] if 'serverList' in st.session_state else st.session_state['filteredData'].query("HostAndIP == @st.session_state['selectedServer']")['IPAddress'].iloc[0]}</p>
                        </div> """, unsafe_allow_html= True)
            with col4:
                col4.markdown(f"""
                        <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: -7px; padding-top: 5px; align-items: center; justify-content: space-between; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Total Server</p>
                                <p style="margin-top: -15px; font-size: 14px; color: #B3F361; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{totalServers if totalServers is not None else "No data available"}</p>
                        </div> """, unsafe_allow_html= True)
            with col5:
                col5.markdown(f"""
                        <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: -7px; padding-top: 5px; align-items: center; justify-content: space-between; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Active Server</p>
                                <p style="margin-top: -15px; font-size: 14px; color: #B3F361; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{len(st.session_state.data[st.session_state.data.LogTimestamp >=pd.to_datetime(st.session_state.data.LogTimestamp) - timedelta(minutes= 2)].Hostname.unique())}</p>
                        </div> """, unsafe_allow_html= True)
            with col6:
                col6.markdown(f"""
                        <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: -7px; padding-top: 5px; align-items: center; justify-content: space-between; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >App Name</p>
                                <p style="margin-top: -15px; font-size: 14px; color: #B3F361; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{st.session_state.filteredData.ApplicationName.iloc[0] if 'serverList' in st.session_state else st.session_state['filteredData'].query("HostAndIP == @st.session_state['selectedServer']")['ApplicationName'].iloc[0]}</p>
                        </div> """, unsafe_allow_html= True)
            with col7:
                col7.markdown(f"""
                        <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: -7px; padding-top: 5px; align-items: center; justify-content: space-between; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >App Owner</p>
                                <p style="margin-top: -15px; font-size: 14px; color: #B3F361; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{st.session_state.filteredData.ApplicationOwner.iloc[0] if 'serverList' in st.session_state else st.session_state['filteredData'].query("HostAndIP == @st.session_state['selectedServer']")['ApplicationOwner'].iloc[0]}</p>
                        </div> """, unsafe_allow_html= True)
            with col8:
                col8.markdown(f"""
                        <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: -7px; padding-top: 5px; align-items: center; justify-content: space-between; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Mgt Zone</p>
                                <p style="margin-top: -15px; font-size: 14px; color: #B3F361; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{st.session_state.filteredData.ManagementZone.iloc[0] if 'serverList' in st.session_state else st.session_state['filteredData'].query("HostAndIP == @st.session_state['selectedServer']")['ManagementZone'].iloc[0]}</p>
                        </div> """, unsafe_allow_html= True)

   
            containerTwo.markdown('<br>', unsafe_allow_html=True)
        antd.divider(label='Infrastructure Analysis', icon='house', align='center', color='gray')
        # VISUALS 
        with stylable_container(
                    key="visual_container20",
                    css_styles="""{
                    background: #1F2D2D;
                                # border: 1px solid rgba(49, 51, 63, 0.2);
                                # box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
                                border-radius: 1.5rem;
                                padding: 20px 20px 20px 20px;
                                margin-top: -10px;
                            }"""):
            # Preprocess the Metric data for visuals 

                              
            col1, col2, col3, col4 = st.columns([2,5,1,2], border = True)
            with col1:
                #! important: We dont want 'Reset Filter' to be there if the user has not selected any filter, so we use the all_present logic.
                #! all_present logic checks if all the hosts in filteredData is in data, if yes, it means the user has not selectd any filter and so it doesnt add 'Reset Filter' to the serverList options,  it only ads 'Reset Filter' if the user has slected a severList filter
                # all(i in st.session_state.filteredData.HostAndIP.unique().tolist() for i in st.session_state.data.HostAndIP.unique().tolist())
                all_present = set(st.session_state.data.HostAndIP.unique().tolist()).issubset(set(st.session_state.filteredData.HostAndIP.unique().tolist()))
                if all_present:
                    server_list_options = st.session_state.filteredData.HostAndIP.unique().tolist()
                else:
                    server_list_options = st.session_state.filteredData.HostAndIP.unique().tolist() + ['Reset Selection']
                if col1.selectbox('Server List',options=server_list_options, key='serverList',  help='Select a server to view its metrics', index = 0):
                    st.session_state['serverListLoaded'] = True

            viz = st.session_state['filteredData'].query("HostAndIP == @st.session_state['serverList']") 
            if viz.empty:
                @st.dialog('Server selection: Cannot Reset Selection With One Option')
                def defaulting():
                    st.markdown(
                        f"""
                        <div style="background-color: #FFDDC1; padding: 15px; border-radius: 8px; border: 1px solid #FF5733;">
                            <h4 style="color: #FF5733; font-family: Arial, sans-serif; margin-bottom: 10px;">Notice:</h4>
                            <p style="color: #333; font-size: 14px; font-family: Tahoma, Verdana;">
                                There is only one server available under your selection. The "Reset Selection" option cannot be used in this case.
                                <br>Select "Default" in filters to view all available servers.
                               <br> Defaulting to the available server(s): <strong style="color: #FF5733;">{st.session_state.filteredData.HostAndIP.iloc[0]}</strong>.
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                defaulting()
                viz = st.session_state['filteredData']
            vizData = viz[['HostAndIP', 'LogTimestamp', 'CPUUsage', 'MemoryUsage', 'DiskUsage', 'TotalDiskSpaceGB', 'TotalFreeDiskGB', 'TotalMemory', 'NetworkTrafficReceived', 'NetworkTrafficSent', 'NetworkTrafficAggregate']]
            vizData['LogTimestamp'] = pd.to_datetime(vizData['LogTimestamp'])
            vizData = vizData.set_index('LogTimestamp')
            # Group using pd.Grouper
            vizData = vizData.groupby(pd.Grouper(freq='1min')).agg({
                'HostAndIP': 'last',
                'CPUUsage': 'last',
                'MemoryUsage': 'last',
                'DiskUsage': 'last',
                'TotalMemory': 'last',
                'TotalFreeDiskGB': 'last',
                'TotalDiskSpaceGB': 'last',
                'NetworkTrafficReceived': 'last',
                'NetworkTrafficSent': 'last',
                'NetworkTrafficAggregate': 'last'
            })

            latestTime = vizData.index[-1]

            # Handle null values for the last index position
            currentCPU = vizData['CPUUsage'].iloc[-1] if pd.notnull(vizData['CPUUsage'].iloc[-1]) else vizData['CPUUsage'].loc[vizData['CPUUsage'].last_valid_index()]
            currentMemory = vizData['MemoryUsage'].iloc[-1] if pd.notnull(vizData['MemoryUsage'].iloc[-1]) else vizData['MemoryUsage'].loc[vizData['MemoryUsage'].last_valid_index()]
            currentDisk = vizData['DiskUsage'].iloc[-1] if pd.notnull(vizData['DiskUsage'].iloc[-1]) else vizData['DiskUsage'].loc[vizData['DiskUsage'].last_valid_index()]
            currentTotalDisk = vizData['TotalDiskSpaceGB'].iloc[-1] if pd.notnull(vizData['TotalDiskSpaceGB'].iloc[-1]) else vizData['TotalDiskSpaceGB'].loc[vizData['TotalDiskSpaceGB'].last_valid_index()]
            currentDiskAvail = vizData['TotalFreeDiskGB'].iloc[-1] if pd.notnull(vizData['TotalFreeDiskGB'].iloc[-1]) else vizData['TotalFreeDiskGB'].loc[vizData['TotalFreeDiskGB'].last_valid_index()]
            currentTotalMemory = vizData['TotalMemory'].iloc[-1] if pd.notnull(vizData['TotalMemory'].iloc[-1]) else vizData['TotalMemory'].loc[vizData['TotalMemory'].last_valid_index()]

            with col2:
                netType = col2.selectbox('Network Bound', ['Received and Sent', 'Aggregate'], index = 0, label_visibility = 'collapsed')
                if netType == 'Received and Sent':
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=vizData.index, y=vizData['NetworkTrafficReceived'].astype(float), fill='tozeroy', mode='lines', line=dict(color='#00FF9C'), name='Traffic Received'))
                    fig.add_trace(go.Scatter(x=vizData.index, y=vizData['NetworkTrafficSent'].astype(float), fill='tonexty', mode='lines', line=dict(color='#FFF574'),name='Traffic Sent'  ))
                    fig.update_layout(
                        xaxis_title='Time', yaxis_title='InBound and OutBound Network Reception', height=300, margin=dict(l=0, r=0, t=10, b=0))
                    st.plotly_chart(fig, use_container_width=True)

                elif netType == 'Aggregate':
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=vizData.index, y=vizData['NetworkTrafficAggregate'].astype(float), fill='tozeroy', mode='lines', line=dict(color='green') ))
                    fig.update_layout(
                        # title=f"CPU Usage In Last {output}",
                        xaxis_title='Time', yaxis_title='Aggregate Network Reception', height=300, margin=dict(l=0,  r=0, t=10, b=0  ))     
                    st.plotly_chart(fig, use_container_width=True)
            with col3:
                calc2 = inf(st.session_state['filteredData'])
                col3.metric(label = 'Total Disk Space(GB)', value = round(currentTotalDisk,1), delta = None, border=True)
                percRemaining = (calc2.currentFreeDisk / calc2.currentTotalDisk) * 100
                col3.metric(label = 'Free Disk(GB)', value = round(currentDiskAvail, 1), delta =None,  border=True)
                col3.metric(label='Memory(GB)', value = round(currentTotalMemory, 1), delta = None, border=True)
            with col4:
                fig1 = go.Figure(go.Indicator(
                    mode = "gauge+number+delta",
                    value = currentCPU,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    # title = {'text': "Current CPU Load(%)", 'font': {'size': 18}},
                    # delta = {'reference': 400, 'increasing': {'color': "RebeccaPurple"}},
                    gauge = {
                        'axis': {'range': [1, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                        'bar': {'color': '#00FF9C' if currentCPU <= 75 else '#FFF574' if currentCPU <= 85 else '#F93827'},
                        # 'bgcolor': "white",
                        'borderwidth': 1, 'bordercolor': "white",
                        'steps': [
                            {'range': [0, 70], 'color': '#F0F2F6'},
                            {'range': [70, 85], 'color': '#E7D283'},
                            {'range': [85, 100], 'color': '#FFDBDB'}],
                        'threshold': {
                            'line': {'color': "red", 'width': 1},
                            'thickness': 0.75,
                            'value': 80}}))
                fig1.update_layout( 
                    height=115,
                    # paper_bgcolor='lightgray',  
                    paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
                    # plot_bgcolor='cyan',
                    margin=dict(l=0, r=0, t=40, b=10) ,
                    title={'text': "Current CPU Load(%)", 'font': {'size': 12}, 'x': 0.3},) # Remove extra space around the gauge
                col4.plotly_chart(fig1, use_container_width=True)
                
                fig2 = go.Figure(go.Indicator(
                    mode = "gauge+number+delta",
                    value = currentMemory,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    # title = {'text': "Current Memory Load(%)", 'font': {'size': 18}},
                    # delta = {'reference': 400, 'increasing': {'color': "RebeccaPurple"}},
                    gauge = {
                        'axis': {'range': [1, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                        'bar': {'color': '#00FF9C' if currentMemory <= 70 else '#FFF574' if currentMemory <= 85 else '#F93827'},
                        'bgcolor': "gray",
                        'borderwidth': 1,
                        'bordercolor': "white",
                        'steps': [
                            {'range': [0, 70], 'color': '#F0F2F6'},
                            {'range': [70, 85], 'color': '#E7D283'},
                            {'range': [85, 100], 'color': '#FFDBDB'}],
                        'threshold': {
                            'line': {'color': "red", 'width': 1},
                            'thickness': 0.75,
                            'value': 80}}))
                fig2.update_layout(
                    height=115,
                    # paper_bgcolor='lightgray',  
                    paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
                    # plot_bgcolor='cyan',
                    margin=dict(l=0, r=0, t=40, b=10) ,
                    title={'text': "Current Memory Load(%)", 'font': {'size': 12}, 'x': 0.3},) # Remove extra space around the gauge
                col4.plotly_chart(fig2)
                
                fig3 = go.Figure(go.Indicator(
                    mode = "gauge+number+delta",
                    value = currentDisk,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    # title = {'text': "Current Disk Load(%)", 'font': {'size': 18}},
                    # delta = {'reference': 400, 'increasing': {'color': "RebeccaPurple"}},
                    gauge = {
                        'axis': {'range': [1, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                        'bar': {'color': '#00FF9C' if currentDisk <= 75 else '#FFF574' if currentDisk <= 85 else '#F93827'},
                        # 'bgcolor': "white",
                        'borderwidth': 1,
                        'bordercolor': "white",
                        'steps': [
                            {'range': [0, 70], 'color': '#F0F2F6'},
                            {'range': [70, 85], 'color': '#E7D283'},
                            {'range': [85, 100], 'color': '#FFDBDB'}],
                        'threshold': {
                            'line': {'color': "red", 'width': 1},
                            'thickness': 0.75,
                            'value': 80}}))
                fig3.update_layout(
                    height=115,
                    width = 500,
                    # paper_bgcolor='lightgray',  
                    paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
                    # plot_bgcolor='cyan',
                    margin=dict(l=0, r=0, t=40, b=10) ,
                    title={'text': "Current Disk Load(%)", 'font': {'size': 12}, 'x': 0.3},) # Remove extra space around the gauge
                col4.plotly_chart(fig3, use_container_width=True)
        st.session_state['filteredData']  = None
        del st.session_state['filteredData']        
        gc.collect()
        del gc.garbage[:]
        # -------------------------------------------- 2nd row -----------------------------------------------
        # with stylable_container(
        #     key="visual_container2",
        #     css_styles="""{
        #                 # border: 1px solid rgba(49, 51, 63, 0.2);
        #                 box-shadow: rgba(14, 30, 37, 0.12) 0px 2px 4px 0px, rgba(14, 30, 37, 0.32) 0px 2px 16px 0px;
        #                 border-radius: 0.3rem;
        #                 padding: 5px 10px;
        #                 margin-top: -10px;
        #             }"""):
        
        if len(st.session_state['startDate']) == 10 or len(st.session_state['stopDate']) == 10:
            date1 = datetime.strptime(st.session_state['startDate']+' 00:00:00', "%Y-%m-%d %H:%M:%S")
            date2 = datetime.strptime(st.session_state['stopDate']+' 00:00:00', "%Y-%m-%d %H:%M:%S")
        else:
            date1 = datetime.strptime(st.session_state['startDate'], "%Y-%m-%d %H:%M:%S")
            date2 = datetime.strptime(st.session_state['stopDate'], "%Y-%m-%d %H:%M:%S")
        difference = date2 - date1
        days = difference.days
        hours = difference.seconds//3600
        if days > 0 and hours > 0:
            output = f"{days} days and {hours} hours"
        elif days > 0 and hours == 0:
            output = f"{days} days"
        else:
            output = f"{hours} hours"
   

        col1, col2, col3 = st.columns([1,1,1], border = False)
        # Define thresholds and colors
        thresholds = [0, 70, 85, 100]
        colours = ['#00FF9C', '#FFF574', '#F93827']
        threshold_labels = ['0 - 70', '70 - 85', '85+']
        with col1:
            with stylable_container(
                    key="visual_container21",
                    css_styles="""{
                                # border: 1px solid rgba(49, 51, 63, 0.2);
                                box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                border-radius: 1.5rem;
                                padding: 5px 10px;
                                margin-top: 10px;
                                # background: #1F2D2D;
                            }"""):
                    # fig = go.Figure()
                    # fig.add_trace(go.Scatter(x=vizData.index, y=vizData['CPUUsage'], fill='tozeroy', mode='lines', connectgaps=False, line=dict(color='green') ))
                    # fig.update_layout(
                    #     title=f"CPU Usage In Last {output}",
                    #     xaxis_title='Time', yaxis_title='Percentage Usage', height=300, margin=dict(l=0,  r=30, t=40, b=10  ))     
                    # st.plotly_chart(fig, use_container_width=True)
                    fig = go.Figure()
                    if not st.session_state.data.empty:
                        for i in range(len(thresholds) - 1):
                            fig.add_trace(go.Scatter(
                                x=[vizData.index[0], vizData.index[-1], vizData.index[-1], vizData.index[0]],
                                y=[thresholds[i], thresholds[i], thresholds[i + 1], thresholds[i + 1]],
                                fill='toself',  # Fill the area
                                fillcolor=colours[i],
                                line=dict(color='rgba(255,255,255,0)'),  # Transparent line
                            ))
                        # Add the line plot after the filled areas
                        fig.add_trace(go.Scatter(x=vizData.index, y=vizData['CPUUsage'], mode='lines', connectgaps=True, line=dict(color='blue', width=2)))
                        fig.update_layout(
                            showlegend=False,
                            title={'text': f"CPU Usage In Last {st.session_state.timeRange} {st.session_state.timeUnit}", 'x': 0.3},
                            yaxis=dict(range=[-10, 100]),  # Adjust Y-axis limits based on your thresholds
                            xaxis_title = None, yaxis_title = None, height = 350, margin=dict(l=0,  r=0, t=40, b=10  ))
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        None
                    
        with col2:
            with stylable_container(
                    key="visual_container21",
                    css_styles="""{
                                # border: 1px solid rgba(49, 51, 63, 0.2);
                                box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                # border-radius: 0.3rem;
                                padding: 5px 10px;
                                margin-top: 10px;
                            }"""):
                    fig = go.Figure()
                    if not st.session_state.data.empty:
                        for i in range(len(thresholds) - 1):
                            fig.add_trace(go.Scatter(
                                x=[vizData.index[0], vizData.index[-1], vizData.index[-1], vizData.index[0]],
                                y=[thresholds[i], thresholds[i], thresholds[i + 1], thresholds[i + 1]],
                                fill='toself',  # Fill the area
                                fillcolor=colours[i],
                                line=dict(color='rgba(255,255,255,0)'),  # Transparent line
                            ))
                        # Add the line plot after the filled areas
                        fig.add_trace(go.Scatter(x=vizData.index, y=vizData['MemoryUsage'], mode='lines', connectgaps=True, line=dict(color='blue', width=2)))
                        fig.update_layout(
                            showlegend=False,
                            title={'text': f"Memory Usage In Last {st.session_state.timeRange} {st.session_state.timeUnit}", 'x': 0.3},
                            yaxis=dict(range=[-10, 100]),  # Adjust Y-axis limits based on your thresholds
                            xaxis_title = None, yaxis_title = None, height = 350, margin=dict(l=0,  r=0, t=40, b=10  ))
                        st.plotly_chart(fig, use_container_width=True)  
                    else:
                        None
        with col3:
            with stylable_container(
                    key="visual_container21",
                    css_styles="""{
                                # border: 1px solid rgba(49, 51, 63, 0.2);
                                box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                # border-radius: 0.3rem;
                                padding: 5px 10px;
                                margin-top: 10px;
                            }"""):
                    fig = go.Figure()
                    if not st.session_state.data.empty:
                        for i in range(len(thresholds) - 1):
                            fig.add_trace(go.Scatter(
                                x=[vizData.index[0], vizData.index[-1], vizData.index[-1], vizData.index[0]],
                                y=[thresholds[i], thresholds[i], thresholds[i + 1], thresholds[i + 1]],
                                fill='toself',  # Fill the area
                                fillcolor=colours[i],
                                line=dict(color='rgba(255,255,255,0)'),  # Transparent line
                            ))
                        # Add the line plot after the filled areas
                        fig.add_trace(go.Scatter(x=vizData.index, y=vizData['DiskUsage'], mode='lines', connectgaps=True, line=dict(color='blue', width=2)))
                        fig.update_layout(
                            showlegend=False,
                            title={'text': f"Disk Usage In Last {st.session_state.timeRange} {st.session_state.timeUnit}", 'x': 0.3},
                            yaxis=dict(range=[-10, 100]),  # Adjust Y-axis limits based on your thresholds
                            xaxis_title = None, yaxis_title = None, height = 350, margin=dict(l=0,  r=0, t=40, b=10  ))
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        None
                        
            viz, vizData = None, None
            del viz, vizData
            gc.collect()
            del gc.garbage[:]
            
    filters()
        # -------------------------------------------- 3rd row -----------------------------------------------

    @st.fragment
    def pivotTable24hrs(value):
            fullData = fetch_data()
            usageData = fullData[['LogTimestamp', 'Hostname', 'IPAddress',  'CPUUsage', 'DiskUsage', 'MemoryUsage', 'NetworkTrafficReceived', 'NetworkTrafficSent', 'NetworkTrafficAggregate']]
            usageData['HostAndIP'] = usageData['Hostname'] + usageData['IPAddress']
            usageData['LogTimestamp'] = pd.to_datetime(usageData['LogTimestamp'])
            # startTime = str(usageData.LogTimestamp.max() - timedelta(hours=24))
            start_time = usageData['LogTimestamp'].max() - timedelta(hours=24)
            usageData = usageData[usageData['LogTimestamp'] >= start_time]
            usageData['NetworkTrafficReceived'] = usageData['NetworkTrafficReceived'].astype(float)
            usageData['NetworkTrafficSent'] = usageData['NetworkTrafficSent'].astype(float)
            usageData['NetworkTrafficAggregate'] = usageData['NetworkTrafficAggregate'].astype(float)
            
            usageData.set_index('LogTimestamp', inplace = True)
            usageData = usageData[['HostAndIP', 'CPUUsage', 'DiskUsage', 'MemoryUsage', 'NetworkTrafficReceived', 'NetworkTrafficSent', 'NetworkTrafficAggregate']]

            usageData = usageData.groupby('HostAndIP').resample('h').agg({'CPUUsage': 'mean', 'DiskUsage': 'mean', 'MemoryUsage': 'mean', 'NetworkTrafficReceived': 'last', 'NetworkTrafficSent': 'last', 'NetworkTrafficAggregate': 'last'})
            usageData.reset_index(inplace = True)
            usageData['hour'] = usageData['LogTimestamp'].dt.strftime('%Y-%m-%d %H:00')
            # usageData =  pd.pivot_table(usageData, index = 'HostAndIP', columns = 'hour', values = 'CPUUsage').fillna(0).applymap(lambda x: f"{x:.2f}".rstrip('0').rstrip('.'))
            if st.session_state['data_empty'] == False:
                usageData =  pd.pivot_table(usageData, index = 'HostAndIP', columns = 'hour', values = value).fillna(0).applymap(lambda x: round(x, 2))
            else:
                return None
            from matplotlib.colors import LinearSegmentedColormap
            colors = ["#00FF9C", "#FFF574", "#F93827"]  # Green -> Yellow -> Red
            custom_cmap = LinearSegmentedColormap.from_list("GnYlRd", colors)
            result= st.write(usageData.style.background_gradient(cmap=custom_cmap, axis=1, vmin=0, vmax=100))
            del usageData, fullData
            usageData, fullData = None, None
            gc.collect()
            del gc.garbage[:]
            return result

    @st.fragment
    def miniHeatMap():
        with stylable_container(
                    key="visual_container30",
                    css_styles="""{
                                # border: 1px solid rgba(49, 51, 63, 0.2);
                                # box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
                                border-radius: 1.5rem;
                                padding: 20px 20px 20px 20px;
                                margin-top: 10px;
                                background: #1F2D2D;
                            }"""):
            with st.container(height = 550, border=False):
                col1, col2 = st.columns([5,1.8], border = True)
                with col1:
                    col11, col22 = col1.columns([1, 5])
                    with col11:
                        options = ['CPUUsage', 'DiskUsage', 'MemoryUsage', 'NetworkTrafficReceived', 'NetworkTrafficSent', 'NetworkTrafficAggregate']
                        col11.selectbox('Metric Selector', options, key='metricTableValue',  help='View the information of your chosen metric in the last 24hrs', index = 0)
                    with col22:
                        col22.markdown(f"""
                            
                            <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: 1px; padding-top: 5px; align-items: center; justify-content: space-between; height:68px; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                                <p style="font-size: 18px; font-weight: bold; text-align: center;">24Hrs Metric Display Table</p>
                                <p style="margin-top: -15px; font-size: 16px; text-align: center; font-family: Tahoma, Verdana;">
                                    Overview of {st.session_state.metricTableValue} Across All Servers in the Last 24 Hours of Your Selected Timeframe
                                </p>
                            </div>
                            </div> """, unsafe_allow_html= True)
                    pivotTable24hrs(st.session_state.metricTableValue)
    
                twoMinutes = pd.to_datetime(st.session_state['data']['LogTimestamp']) - timedelta(minutes=2)
                heatmapData1 = st.session_state['data'][st.session_state['data']['LogTimestamp'] >= twoMinutes][['HostAndIP', 'DriveLetter', 'CPUUsage', 'DiskUsage', 'MemoryUsage']]
                heatmapData1 = heatmapData1.groupby(['HostAndIP']).agg({
                                                                        'CPUUsage': 'last',
                                                                        'DiskUsage': 'last',
                                                                        'MemoryUsage': 'last',
                                                                    }).reset_index()
                for i in heatmapData1.columns:
                    heatmapData1[i] = heatmapData1[i].replace(0, 1e-6)

                # rename the hostandIP column for fitting into chart 
                heatmapData1['HostAndIP_trunc'] = heatmapData1['HostAndIP'].apply(lambda x: x[:15]+'...' if len(x) > 15 else x)
                with col2:
                    col20, col21 = col2.columns([1, 1])
                    with col20:
                        option1 = col20.selectbox('Metric Selector', ['CPUUsage', 'DiskUsage', 'MemoryUsage'], key='heatmap',  help="Displays a information of active servers' resource consumption. Use the dropdown to select resource of interest", index = 0) 
                    with col21:
                        option2 = col21.selectbox('Select prefered plot type', ['Heatmap', 'Barchart'], index = 0, help='Choose either barchart or heatmap to represent your information')

                    if option1 == 'CPUUsage':
                        # heatmapData1 = heatmapData1.groupby(['HostAndIP'])[['CPUUsage']].mean().reset_index()
                        if option2 == 'Heatmap':             
                            figs = px.treemap(data_frame=heatmapData1,path=['HostAndIP_trunc'], values = [1] * len(heatmapData1), color=heatmapData1['CPUUsage'], color_continuous_scale=[(0.0, "#00FF9C"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ], range_color=(0, 100), hover_data={ 'CPUUsage': ':.2f',  'HostAndIP': True,   }, height = 400 )
                        else:
                            figs = px.bar(data_frame=heatmapData1, y='HostAndIP_trunc', x='CPUUsage', color='CPUUsage', text = 'CPUUsage', color_continuous_scale=[(0.0, "#00FF9C"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ], range_color=(0, 100), hover_data={ 'CPUUsage': ':.2f',  'HostAndIP': True,   }, height = 400 )
                            figs.update_traces(textposition='inside')
                            figs.update_layout(
                                yaxis = dict(showgrid = False, showline = False),
                                yaxis_title=None, xaxis_title = None,
                                xaxis = dict(showgrid = True, showline = False, )
                                )                        

                    elif option1 == 'DiskUsage':
                        # heatmapData1 = heatmapData1.groupby(['HostAndIP'])[['DiskUsage']].mean().reset_index()
                        if option2 == 'Heatmap':
                            figs = px.treemap(data_frame=heatmapData1,path=['HostAndIP_trunc'], values = heatmapData1['DiskUsage'], color=heatmapData1['DiskUsage'], color_continuous_scale=[ (0.0, "#00FF9C"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ], range_color=(0, 100) , hover_data={ 'DiskUsage': ':.2f',  'HostAndIP': True }, height = 400)
                        else:
                            figs = px.bar(data_frame=heatmapData1, y='HostAndIP_trunc', x='DiskUsage', color='DiskUsage', text = 'DiskUsage', color_continuous_scale=[(0.0, "#00FF9C"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ], range_color=(0, 100), hover_data={ 'DiskUsage': ':.2f',  'HostAndIP': True,   }, height = 400 ) 
                            figs.update_traces(textposition='inside')
                            figs.update_layout(
                                yaxis = dict(showgrid = False, showline = False),
                                yaxis_title=None, xaxis_title = None,
                                xaxis = dict(showgrid = True, showline = False, )
                                )                        

                    elif option1 == 'MemoryUsage':
                        # heatmapData1 = heatmapData1.groupby(['HostAndIP'])[['MemoryUsage']].mean().reset_index()
                        if option2 == 'Heatmap':
                            figs = px.treemap(data_frame=heatmapData1,path=['HostAndIP_trunc'], values = heatmapData1['MemoryUsage'], color=heatmapData1['MemoryUsage'], color_continuous_scale=[(0.0, "#00FF9C"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ], range_color=(0, 100) , hover_data={ 'MemoryUsage': ':.2f',  'HostAndIP': True}, height = 400)
                        else:
                            figs = px.bar(data_frame=heatmapData1, y='HostAndIP_trunc', x='MemoryUsage', color='MemoryUsage', text = 'MemoryUsage', color_continuous_scale=[(0.0, "#00FF9C"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ], range_color=(0, 100), hover_data={ 'MemoryUsage': ':.2f',  'HostAndIP': True,   }, height = 400 ) 
                            figs.update_traces(textposition='inside')
                            figs.update_layout(
                                yaxis = dict(showgrid = False, showline = False),
                                yaxis_title=None, xaxis_title = None,
                                xaxis = dict(showgrid = True, showline = False, )
                                )
                            

                    # figs.update_traces(
                    #     hovertemplate="<b>Host and IP:</b> %{customdata[1]}<br>"
                    #   "<b>Value:</b> %{color:.2f}%<extra></extra>")
                    figs.update_layout(
                        showlegend=False,
                        margin=dict(l=0, r=0, t=0, b=0),  # Remove margins
                        uniformtext=dict(minsize=10, mode='hide'),  # Manage text size and visibility
                    )
                    figs.update(layout_coloraxis_showscale=False)  # hiding color-bar 
                    col2.plotly_chart(figs, use_container_width=True)
        del heatmapData1
        gc.collect()
    miniHeatMap()


        # -------------------------------------------- 4th row -----------------------------------------------

    @st.fragment
    def heatMap():    
        dataWtihLastValues = (st.session_state['data'].sort_values(by='LogTimestamp').groupby('HostAndIP', as_index=False).last())[['HostAndIP', 'ManagementZone', 'ApplicationName', 'CPUUsage', 'DiskUsage', 'MemoryUsage']]
        # dataWtihLastValues['HostAndIP'] = dataWtihLastValues['HostAndIP'].apply(lambda x: x[:15]+'...' if len(x) > 15 else x)  
        dataWtihLastValues['ManagementZone'].fillna('Unknown', inplace=True)
        dataWtihLastValues['ApplicationName'].fillna('Unknown', inplace=True)

        for i in dataWtihLastValues:
            if dataWtihLastValues[i].dtypes != 'O':
                dataWtihLastValues[i] = dataWtihLastValues[i].replace(0, 1e-6)

        with stylable_container(
                    key="visual_container30",
                    css_styles="""{
                                # border: 1px solid rgba(49, 51, 63, 0.2);
                                # box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
                                border-radius: 1.5rem;
                                padding: 20px 20px 20px 20px;
                                margin-top: 10px;
                            }"""):    

            with st.container(border = False, height = 500):
                col21, col22 = st.columns([1, 5], border =False)
                with col21:
                    treeSel = col21.selectbox('Select the metric to display', ['Storage Utilization', 'Application CPU Consumption', 'Application Memory Consumption'], key='treeSel', index = 0)
                
                    treemap_titles = [["Storage Utilization", "Visualizing Most Recent Disk Space Distribution Across Servers Classified Under Individual Management Zones (Based On The Selected Timeframe)"],
                        ["Application CPU Consumption", "Insights into the Most Recent CPU Resource Consumption Across Different Servers Classified Under Individual Management Zone"], 
                        ["Application Memory Consumption", "Insights into the Most Recent Memory Resource Consumption Across Different Servers Classified Under Individual Management Zone"]]
            
                    topTitle = treemap_titles[0][0] if treeSel == 'Storage Utilization' else treemap_titles[1][0] if treeSel == 'Application CPU Consumption' else treemap_titles[2][0]
                    bodytitle = treemap_titles[0][1] if treeSel == 'Storage Utilization' else treemap_titles[1][1] if treeSel == 'Application CPU Consumption' else treemap_titles[2][1]

                with col22:
                    col22.markdown(f"""
                        <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: 1px; padding-top: 5px; align-items: center; justify-content: space-between; height:68px; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                            <p style="font-size: 18px; font-weight: bold; text-align: center;">{topTitle}</p>
                            <p style="margin-top: -15px; font-size: 16px; text-align: center; font-family: Tahoma, Verdana;">
                                {bodytitle}
                            </p>
                        </div>
                        </div> """, unsafe_allow_html= True)
          
                if treeSel == 'Storage Utilization':
                        figs = px.treemap(
                            data_frame=dataWtihLastValues, 
                            path=['ManagementZone', 'HostAndIP'],  
                            values=dataWtihLastValues['DiskUsage'],  
                            color=dataWtihLastValues['DiskUsage'],  
                            color_continuous_scale=[(0.0, "#00FF9C"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ],  # Gradient: red -> yellow -> green
                            range_color=(0, 100),  # Dynamic color range
                            hover_data={'DiskUsage': ':.2f', 'HostAndIP': True}, 
                            height=400)
                        figs.update_traces(
                            hovertemplate=
                                        "<b>Host and IP:</b> %{customdata[1]}<br>"
                                        "<b>Percentage UsedSpace:</b> %{color:.2f}<extra></extra>")
                        figs.update_layout(
                            margin=dict(l=0, r=0, t=0, b=0),
                            uniformtext=dict(minsize=13, mode='hide'), )
                        st.plotly_chart(figs, use_container_width=True)      
                elif treeSel == 'Application CPU Consumption':
                        figs = px.treemap(
                            data_frame=dataWtihLastValues, 
                            path=['ManagementZone', 'HostAndIP'],  
                            values=dataWtihLastValues['CPUUsage'],  
                            color=dataWtihLastValues['CPUUsage'],  
                            color_continuous_scale=[(0.0, "#00FF9C"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ],  # Gradient: red -> yellow -> green
                            range_color=(0, 100),  # Dynamic color range
                            hover_data={'CPUUsage': ':.2f', 'HostAndIP': True}, 
                            height=400)
                        figs.update_traces(
                            hovertemplate= 
                                        "<b>Host and IP:</b> %{customdata[1]}<br>"
                                        "<b>Percentage CPUusage:</b> %{color:.2f}<extra></extra>")
                        figs.update_layout(
                            margin=dict(l=0, r=0, t=0, b=0),
                            uniformtext=dict(minsize=13, mode='hide'))
                        st.plotly_chart(figs, use_container_width=True)                            
                elif treeSel == 'Application Memory Consumption':
                        figs = px.treemap(
                            data_frame=dataWtihLastValues, 
                            path=['ManagementZone',  'HostAndIP'],  
                            values=dataWtihLastValues['MemoryUsage'], 
                            color=dataWtihLastValues['MemoryUsage'], 
                            color_continuous_scale=[(0.0, "#00FF9C"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ],  # Gradient: red -> yellow -> green
                            range_color=(0, 100), # Dynamic color range
                            hover_data={'MemoryUsage': ':.2f', 'HostAndIP': True}, 
                            height=400)
                        figs.update_traces(
                            hovertemplate=
                                        "<b>Host and IP:</b> %{customdata[1]}<br>"
                                        "<b>Net Traffic Agg:</b> %{color:.2f}<extra></extra>")
                        figs.update_layout(
                            margin=dict(l=0, r=0, t=0, b=0),
                            uniformtext=dict(minsize=13, mode='hide'), )
                        st.plotly_chart(figs, use_container_width=True)   
        del dataWtihLastValues
        gc.collect()
    heatMap()



    def serviceUptime(
        df: pd.DataFrame,  # type: ignore
        expected_log_interval_minutes: int = 1,
        missing_data_threshold_minutes: int = 15,
        hostname_col: str = "Hostname",
        ip_col: str = "IPAddress",
        timestamp_col: str = "LogTimestamp",
        lookback_hours: int = 24
    ) -> pd.DataFrame:  # type: ignore
        """
        Calculates the service uptime percentage for each server within a given timeframe (last N hours).
        """

        if df.empty:
            return pd.DataFrame()

        # 1. Prepare Data
        data = df  # Avoid modifying the original DataFrame
        data["HostAndIP"] = data[hostname_col] + data[ip_col]
        data[timestamp_col] = pd.to_datetime(data[timestamp_col])

        # Only consider logs within the last `lookback_hours`
        end_time = data[timestamp_col].max().floor("H")
        start_time = end_time - timedelta(hours=lookback_hours - 1)
        data = data[data[timestamp_col].between(start_time, end_time)]

        all_servers = data["HostAndIP"].unique()

        # 2. Create Hourly Bins
        hourly_bins = pd.DataFrame(
            pd.date_range(start=start_time, end=end_time, freq="H"), columns=["Hour"]
        )
        hourly_bins["key"] = 0  # temporary key for cross join
        servers_df = pd.DataFrame(all_servers, columns=["HostAndIP"])
        servers_df["key"] = 0  # temporary key for cross join
        all_hours = pd.merge(hourly_bins, servers_df, on="key").drop("key", axis=1)

        # 3. Mark Active Hours
        data["Hour"] = data[timestamp_col].dt.floor("H")
        data = data.drop_duplicates(subset=["HostAndIP", "Hour"])
        active_hours = data[["HostAndIP", "Hour"]].drop_duplicates()
        all_hours = pd.merge(all_hours, active_hours, on=["HostAndIP", "Hour"], how="left", indicator=True)
        all_hours["Active"] = all_hours["_merge"] == "both"
        all_hours.drop(columns="_merge", inplace=True)

        # 4. Handling Missing Data
        all_hours["Missing"] = False
        for server in all_servers:
            server_data = all_hours.query("HostAndIP == @server").sort_values(by='Hour')
            for index, row in server_data.iterrows():
                if not row['Active']:
                    try:
                        next_time = server_data.iloc[index + 1]['Hour']
                    except IndexError:
                        next_time = row['Hour']
                    time_diff = next_time - row['Hour']
                    if time_diff > timedelta(minutes=missing_data_threshold_minutes):
                        all_hours.loc[index, "Missing"] = True

        # 5. Calculate Uptime
        uptime_by_server = (
            all_hours.groupby("HostAndIP")
            .agg(
                total_hours=("Hour", "count"),
                active_hours=("Active", "sum"),
                missing_hours=("Missing", "sum")
            )
            .reset_index()
        )
        uptime_by_server["Uptime(%)"] = round(
            (uptime_by_server["active_hours"] / uptime_by_server["total_hours"]) * 100, 2
        )

        uptime_by_server = uptime_by_server.sort_values("Uptime(%)", ascending=False)
        del data, all_servers, hourly_bins, servers_df, all_hours, active_hours
        gc.collect()
        return uptime_by_server

    

    # serviceUptimeDadta['HostAndIP'] = serviceUptimeDadta['Hostname'] + serviceUptimeDadta['IPAddress']


    @st.fragment
    def displayAndHostAvailability():
        with stylable_container(
                    key="visual_container30",
                    css_styles="""{
                                # border: 1px solid rgba(49, 51, 63, 0.2);
                                # box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
                                border-radius: 1.5rem;
                                padding: 20px 20px 20px 20px;
                                margin-top: 10px;
                            }"""):    
            with st.container(border = False, height = 550):
                st.markdown("""
                    <div class="container metrics text-center" style="border-radius: 0.8rem; height: 4rem; margin-top: 1px; margin-bottom: 1rem; padding-top: 5px; align-items: center; justify-content: space-between; height:68px; background-color: #0C3245; border-bottom: 1px solid #B3F361; ">
                    <p style="font-size: 18px; font-weight: bold; text-align: center; margin-top: 10px">Overview of Resource Availability and Server Uptime In The Last 24Hours</p>
                    </div>
                    </div> """, unsafe_allow_html= True)
                
                fullData = fetch_data()
                usageData = fullData
                usageData['LogTimestamp'] = pd.to_datetime(usageData['LogTimestamp'])
                usageData['HostAndIP'] = usageData['Hostname'] + usageData['IPAddress']
                # last2minutes = pd.to_datetime(usageData['LogTimestamp'].max()) - timedelta(minutes=2)
                # filtered_data = usageData[usageData['LogTimestamp'] >= last2minutes]
                # Create a new DataFrame where each row corresponds to a drive on a server
                quickMetricTable = usageData[['HostAndIP', 'DriveLetter', 'ManagementZone', 
                                                'ApplicationName', 'ApplicationOwner', 'TotalDiskSpaceGB', 
                                                'TotalFreeDiskGB', 'DiskUsage', 'CPUUsage', 'MemoryUsage', 
                                                'DataCenter']]
                # Remove duplicates to ensure a unique row for each server-drive combination
                quickMetricTable = quickMetricTable.drop_duplicates(subset=['HostAndIP', 'DriveLetter'])
                quickMetricTable.rename(columns={
                    'HostAndIP': 'Hostname and IP',
                    'TotalDiskSpaceGB': 'DiskSpace (GB)',
                    'TotalFreeDiskGB': 'DiskAvailable (GB)',
                    'DiskUsage': 'DiskUsed (%)',
                    'CPUUsage': 'CPU Usage (%)',
                    'MemoryUsage': 'Memory Usage (%)',
                    'Datacenter': 'Data Center'
                }, inplace=True)
                quickMetricTable['Last Seen'] = quickMetricTable['Hostname and IP'].map(
                    lambda server: usageData[usageData['HostAndIP'] == server]['LogTimestamp'].max())
                quickMetricTable['Last Seen (Days Ago)'] = quickMetricTable['Hostname and IP'].map(
                    lambda server: (datetime.now() - usageData[usageData['HostAndIP'] == server]['LogTimestamp'].max()).total_seconds() // 86400)
                quickMetricTable['Last Seen (Hours Ago)'] = quickMetricTable['Hostname and IP'].map(
                    lambda server: (datetime.now() - usageData[usageData['HostAndIP'] == server]['LogTimestamp'].max()).total_seconds() // 3600)
                         
                quickMetricTable.set_index('Hostname and IP',  inplace=True)
                #Give duplicate hostnames a suffix of 0 - 1 etc to differentiate it from the latter
                quickMetricTable.index = quickMetricTable.index.to_series().astype(str) + "_" + quickMetricTable.groupby(level=0).cumcount().astype(str)
                st.session_state['quickMetricTable'] = quickMetricTable   

                last24 = pd.to_datetime(fullData['LogTimestamp'].max()) - timedelta(hours=24)
                serviceUptimeDadta = fullData[pd.to_datetime(fullData.LogTimestamp) >= last24]

                serviceData= serviceUptime(serviceUptimeDadta)
                serviceData.sort_values(by ='Uptime(%)', ascending=False, inplace=True)
                serviceData.reset_index(inplace = True, drop = True)


                col1, col2, col3 = st.columns([2,1.6,1.3], border=True)
                from matplotlib.colors import LinearSegmentedColormap
                colors = ["#00FF9C", "#FFF574", "#F93827"]  # Green -> Yellow -> Red
                custom_cmap = LinearSegmentedColormap.from_list("GnYlRd", colors)
                # result= st.write(usageData.style.background_gradient(cmap=custom_cmap, axis=1, vmin=0, vmax=100))
                with col1:
                    col1.write(st.session_state['quickMetricTable'].style.background_gradient(cmap=custom_cmap, axis=1, vmin=0, vmax=100))
                with col2:
                    serviceData2 = serviceData.set_index('HostAndIP')
                    col2.dataframe(serviceData2.style.background_gradient(cmap='Blues'), use_container_width=True)
                with col3:
                    serviceData['HostAndIP_trunc'] = serviceData['HostAndIP'].apply(lambda x: x[:14]+'...' if len(x) > 14 else x)
                    with col3.container(height=420):
                        figs = px.bar(data_frame=serviceData, y='HostAndIP_trunc', x='Uptime(%)', text = 'Uptime(%)', color='Uptime(%)', color_continuous_scale= color_continuous_scales, range_color=(0, 100), hover_data={ 'Uptime(%)': ':.2f',  'HostAndIP': True,   }, height = 350, title = 'Server Uptime' )   
                        figs.update_traces(textposition='inside' )
                        figs.update_layout(
                            xaxis=dict(
                                title="Uptime(%)",
                                showgrid=True,
                                showline=False,
                            ),
                            yaxis=dict(
                                # title="Host and IP",
                                # tickmode="array",
                                # tickvals=serviceData['HostAndIP'],  # List all servers
                                showgrid=False,
                                showline=False,
                                # automargin=True,
                                # fixedrange=True,  # Allow scrolling
                                # showticklabels=False
                            ),
                            yaxis_title=None, xaxis_title = None,
                            # barmode="group",
                            # yaxis=dict(showticklabels=False),  # Hide y-axis tick labels
                            margin=dict(l=0, r=0, t=40, b=0),  # Remove margins
                            uniformtext=dict(minsize=10)  # Adjust text visibility
                        )   
                        # figs.update_yaxes(
                        #     fixedrange=False,  # Allow scrolling
                        #     showticklabels=True,  # Show tick labels
                        # )            
                        figs.update(layout_coloraxis_showscale=False)  # hiding color-bar 
                        st.plotly_chart(figs, use_container_width=True)                    
        del usageData, quickMetricTable, st.session_state['quickMetricTable'], serviceData, serviceData2, serviceUptimeDadta, fullData
        usageData, quickMetricTable, st.session_state['quickMetricTable'], serviceData, serviceData2, serviceUptimeDadta, fullData = None, None, None, None, None, None, None
        gc.collect()
        del gc.garbage[:]
    displayAndHostAvailability()


@st.dialog('Empty Data Alert', width ='small')
def emptinessDataCheck():
    st.session_state["data_empty"] = True
    st.write('No data available. Your start date will be set to the earliest available date on your data')
    st.markdown("<br>", unsafe_allow_html=True)
    st.write('The earliest date')
    # st.rerun()
        
if st.session_state['data'].empty:
    emptinessDataCheck()


# Creating a rerun and kill process 
def kill_process():
    """Kills the current Python process."""
    st.session_state.process_killed = True
    os.kill(os.getpid(), signal.SIGTERM)  # Send a termination signal
if 'process_killed' not in st.session_state:
    st.session_state['process_killed'] = False


with tab1:
    opens, closes = st.columns([1,4])
    with opens:
        rerun, stop = opens.columns([1,1])
        with rerun:
            if st.button('Manual App Rerun'):
                st.rerun(scope='app')

    with st.expander(expanded=False, label='View Active DataFrame'):
        st.write(st.session_state.data.sort_values(by = 'LogTimestamp', ascending = False).reset_index(drop=True).set_index('Hostname'))

# with shelve.open('alertDB.db') as db:
#     db['latestTime'] = st.session_state.data.LogTimestamp.max()


# ---------------------------------- tempDB scripting -------------------------------------------
def retrieveRecord(fileName: str, tableName: str, itemListName: str) -> list | None:
    """
    Retrieve a list of items from a document inside a TinyDB table.

    Args:
        fileName (str): Path to the TinyDB database file.
        tableName (str): Name of the table to query.
        itemListName (str): Name field of the document to retrieve.

    Returns:
        List or None: List of items if document exists, else None.
    """
    if not os.path.isfile(fileName):
        # raise FileNotFoundError(f"Database file '{fileName}' does not exist")
        return None
    db = TinyDB(fileName)
    try:
        if tableName not in db.tables():
            return None

        record = db.table(tableName).get(where('name') == itemListName)
        return record['value'] if record else None
    finally:
        db.close() 
    
def updateRecord(filename: str, tableName: str, itemListName: str, itemToAdd, append = True):
    """
    Append or replace items in the document's value list inside TinyDB.

    Args:
        filename (str): Path to TinyDB file.
        tableName (str): Name of the table.
        itemListName (str): Document identifier ('name' field value).
        itemToAdd: Item to add or set.
        append (bool): If True, append item to list. If False, replace list with item.

    Raises:
        Exception: If file or table does not exist.
    """
    if os.path.isfile(filename):
        db = TinyDB(filename)
        if tableName in db.tables():
            records = db.table(tableName).get(Query().name==itemListName)
            if records:
                records = records['value']
                if append:
                    records.append(itemToAdd)
                    db.table(tableName).update({'value': records}, where('name')==itemListName)
                else:
                     db.table(tableName).update({'value': [itemToAdd]}, where('name')==itemListName)
            else:
                db.table(tableName).insert({'name': itemListName, 'value': [itemToAdd]})
        else:
            raise Exception('table does not exist')
    else:
        raise Exception('db_file does not exist')
    

def createRecord(fileName: str, tableName: str, itemListName: str):
    """
    Create a new document with an empty list under the specified table.

    Args:
        fileName (str): Path to the TinyDB database file.
        tableName (str): Name of the table to create the document in.
        itemListName (str): Name field of the document.

    Raises:
        Exception: If table already exists in the database.
    """
    db = TinyDB(fileName)
    if tableName in db.tables():
        raise Exception('Tablename already exist. Use Update function instead')
    else:
        db.table(tableName).insert({'name': itemListName, 'value':[]})


def tableIsExisting(fileName: str, tableName: str):
    """
    Check if a table already exists in the TinyDB database file.

    Args:
        fileName (str): Path to the TinyDB database file.
        tableName (str): Name of the table to check.

    Returns:
        bool: True if the table exists, False otherwise.
    """
    if os.path.isfile(fileName):
        db = TinyDB(fileName)
        return True if tableName in db.tables() else False
    else:
        return False


def removeItemFromRecord(fileName, tableName, itemListName, itemToRemove):
    """
    Remove an item from the list stored in a document within a TinyDB table.

    Args:
        fileName (str): Path to the TinyDB database file.
        tableName (str): Name of the table containing the document.
        itemListName (str): Name field of the document.
        itemToRemove: Item to remove from the list.

    Side Effects:
        Prints success or failure messages to console.
    """
    if os.path.isfile(fileName):
        db = TinyDB(fileName)
        if tableName in db.tables():
            try:
                record = db.table(tableName).get(where('name')==itemListName)
                if record:
                    current_list = list(record['value'])
                    if itemToRemove in current_list:
                        current_list.remove(itemToRemove)
                        db.table(tableName).update({'value': current_list}, where('name') == itemListName)
                        st.toast(f'{itemToRemove} successfully removed from the email registry')
                    else:
                        st.toast(f"{itemToRemove} not found in '{itemListName}'.")
                else:
                    st.toast(f"No record found for '{itemListName}'.")
            finally:
                db.close()
# --------------------------------------------------------------------------------------------





@st.fragment
def threshold():
        firsts, seconds, thirds = st.columns([2,3,2])
        with seconds:
            first, second, third = st.columns([1,1, 1])
            first.number_input('CPU Usage Alert Threshold', min_value=1, max_value= 100, step=1, value=85, key='cpuThresh')
            second.number_input('Memory Usage Alert Threshold', min_value=1, max_value= 100, step=1, value=85, key='memThresh')
            third.number_input('Free Disk Space Threshold', min_value=1, max_value= 100, step=1, value=10, key='diskThresh')

            with shelve.open('alertDB.db') as db:
                db['cpuThresh'] = st.session_state.cpuThresh
                db['memThresh'] = st.session_state.memThresh
                db['diskThresh'] = st.session_state.diskThresh
            
            # --------------- Emails To Notify -------------
            st.markdown("<br>", unsafe_allow_html =True)
            antd.divider(label='Email Registration', icon='house', align='center', color='green')

            def saveEmail(email):
                with shelve.open('alertDB.db') as db:
                    emails = db.get('emails', [])
                    if email not in emails:
                        emails.append(email)
                    db['emails'] = emails
            def collectEmail():
                with shelve.open('alertDB.db') as db:
                    return db.get('emails', [])
            firstss, secondss = st.columns([1, 2])
            firstss.text_input(label='Register Emails', key='newEmail')

            if st.session_state.newEmail:
                saveEmail(st.session_state.newEmail)
            emails = collectEmail() if collectEmail() else [] # Collect emails for multiselect
            # Get previously selected emails for default value
            with shelve.open('alertDB.db') as db:
                defaultemails = db.get('selectedEmails', [])
            selected_emails = secondss.multiselect(
                label='Choose emails to notify',
                options=emails,
                key='registeredEmails',
                default=defaultemails
            )
            # Save selected emails back to the database
            with shelve.open('alertDB.db') as db:
                db['selectedEmails'] = selected_emails
            global emailLists 
            emailLists = selected_emails

            # --------------- Servers To Ignore -------------
            st.markdown("<br>", unsafe_allow_html =True)
            antd.divider(label='Servers To Ignore', align='center', color='green')
            def saveIgnoredServers(selected_servers):
                """Save the selected ignored servers to the database."""
                with shelve.open('alertDB.db') as db:
                    db['ignoredServers'] = selected_servers
            def collectIgnoredServers():
                """Retrieve the list of ignored servers from the database."""
                with shelve.open('alertDB.db') as db:
                    return db.get('ignoredServers', [])
            # Retrieve the current list of ignored servers
            ignored_servers = collectIgnoredServers()
            ignored_servers = [i for i in ignored_servers if i in availableHosts]
            # Create a multiselect widget for selecting servers to ignore
            selected_ignored_servers = st.multiselect(
                label='Select servers to ignore',
                options=availableHosts,
                default=ignored_servers,
                key='ignoredServers'
            )
            # Save the updated list of ignored servers when the selection changes
            if selected_ignored_servers != ignored_servers:
                saveIgnoredServers(selected_ignored_servers)

            # --------------------- Type Of Alert -----------------------
            st.markdown("<br>", unsafe_allow_html =True)
            antd.divider(label='Alert Type', icon='house', align='center', color='green')
            email, slack = st.columns([1,1], border=True)
            with email:
                email_alert =  st.toggle('Email Alert Notification', value = True )
                email_ai = st.toggle('Activate Email AI Analysis', disabled=True if not email_alert else False, value=False if not email_alert else True)
                with shelve.open('alertDB.db') as db:
                    if email_alert:
                        db['emailAlert'] = True
                    else:
                        db['emailAlert'] = False
                    if email_ai:
                        db['useAI_email'] = True
                    else:
                        db['useAI_email'] = False

            with slack:
                slack_alert =  st.toggle('Slack Alert Notification', value=False if email_alert else True, disabled=True if email_alert else False )
                slack_ai = st.toggle('Activate Slack AI Analysis',  disabled=True if not slack_alert else False, value=False if not slack_alert else True)
                with shelve.open('alertDB.db') as db:
                    if slack_alert:
                        db['slackAlert'] = True
                    else:
                        db['slackAlert'] = False
                    if slack_ai:
                        db['useAI_slack'] = True
                    else:      
                        db['useAI_slack'] = False 

with sqlite3.connect('EdgeDB.db') as conn:
    conn.execute('PRAGMA journal_mode=WAL')
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS alertUsers (
            Username TEXT,
            Active INT,
            MgtZone TEXT,
            Server_List TEXT,
            IPAddress TEXT,
            CPU_thresh TEXT,
            MEM_thresh TEXT,
            DISK_thresh TEXT,
            Emails TEXT,
            AlertType TEXT,
            Alerting_AI TEXT,
            dateCreated TEXT
        )
    """)

    conn.commit()

def retrieveAlertName():
   with sqlite3.connect('EdgeDB.db') as conn:
    query = "select Username from alertUsers"
    names = pd.read_sql_query(query, conn)
    if names['Username'].any():
        return [i.lower() for i in names['Username']]
    else:
        return []

def overwrite(alertingType,  alerting_ai):
    with sqlite3.connect('EdgeDB.db') as conn:
        c = conn.cursor()
        query = """
            UPDATE alertUsers
            SET Username = ?,
                Active = ?,
                MgtZone = ?,
                Server_List = ?,
                IPAddress = ?,
                CPU_thresh = ?,
                MEM_thresh = ?,
                DISK_thresh = ?,
                Emails = ?,
                AlertType = ?,
                Alerting_AI = ?,
                dateCreated = ?
            WHERE Username = ?
        """
        c.execute(query, (
            st.session_state.regName.lower(), 1, st.session_state.regMgtZone, st.session_state.servList, st.session_state.ipList, st.session_state.cpuThresh, st.session_state.memThresh, st.session_state.diskThresh, emailLists, alertingType,  alerting_ai, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  st.session_state.regName.lower()
        ))
        conn.commit()
    st.toast(f'Overwritten existing alert {st.session_state.regName}')


# with stylable_container(
#     key="visual_container31",
#     css_styles="""{
#                 box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
#                 border-radius: 1.5rem;
#                 padding: 20px 20px 20px 20px;
#                 margin-top: 10px;
#                 background-color: #202B28
#             }"""): 
    st.markdown("""
    <style>
        div[data-testid="stSegmentedControl"] {
            display: flex;
            justify-content: center; /* Center horizontally */
            align-items: center; /* Center vertically */
        }
    </style>
""", unsafe_allow_html=True)
    
@st.fragment
def alerting():
    df = st.session_state.data
    head1, head2, head3 = st.columns([1.5,2,1.5], gap='large')

    overSelect= head2.segmented_control(label='todo', label_visibility="hidden", options=['Register New Alerts', 'Registered Alerts', 'Deactivate Alerts', 'Open Tickets' ],selection_mode='single', default ='Register New Alerts')

    if overSelect == 'Register New Alerts':
        if 'default_table_shown' in st.session_state:
            del st.session_state['default_table_shown']
        left, middle, right = st.columns([2,3.5,2], gap='large')   
        with middle:
            with st.container(border=False):
                st.markdown("<br>", unsafe_allow_html =True)
                ntag, mgtz, servs = st.columns([1.5,1.5,3])
                regName = ntag.text_input(label='Name Tag', key='regName')
                serverOptions = [' '] + df['ManagementZone'].unique().tolist()
                regMgtZone = mgtz.selectbox(label='Management Zone', placeholder='Choose a mgt zone', options=serverOptions,disabled=True if not regName else False, key='regMgtZone')
                if regMgtZone:
                    import ast
                    servers = df[df['ManagementZone'] == regMgtZone]['Hostname'].unique().tolist()
                    serverlists = servs.multiselect(label='Currently Selected Servers', options=servers, default =servers, disabled=True if not regName else False)
                    ips = []
                    for i in serverlists:
                        ip_address = ast.literal_eval(df[df['Hostname'] == i]['IPAddress'].unique().tolist()[0])
                        # Check if the result is a list
                        if isinstance(ip_address, list):
                            ips.extend(ip_address)  # Add each item in the list to ips
                        else:
                            ips.append(ip_address)  # Add the single IP address

                    # Clean up the IP addresses
                    for index, item in enumerate(ips):
                        ips[index] = str(item).replace('"', '').replace('[', '').replace(']', '')
                    # ips=[i.replace('"', '').replace('[','').replace(']','') for i in ips]

                    st.markdown("<br>", unsafe_allow_html=True)

                # --------------------- Register Threshods -----------------------
                antd.divider(label='Threshold Configuration', align='center', color='green')
                first, second, third = st.columns([1,1, 1])
                cpuThresh=first.number_input('CPU Usage Alert Threshold', min_value=1, max_value= 100, step=1, value=85, key='cpuThresh')
                memThresh=second.number_input('Memory Usage Alert Threshold', min_value=1, max_value= 100, step=1, value=85, key='memThresh')
                diskThresh=third.number_input('Free Disk Space Threshold', step=1, value=10, key='diskThresh')

                # --------------------- Register Email -----------------------
                st.markdown("<br>", unsafe_allow_html =True)
                antd.divider(label='Register Email ', align='center', color='green')
                # def saveEmail(email):
                #     with shelve.open('alertDB.db') as db:
                #         emails = db.get('emails', [])
                #         if email not in emails:
                #             emails.append(email)
                #         db['emails'] = emails
                # def collectEmail():
                #     with shelve.open('alertDB.db') as db:
                #         return db.get('emails', [])
                firstss, secondss = st.columns([1, 2])
                firstss.text_input(label='Register Emails', key='newEmail')

                if st.session_state.newEmail:
                    if not tableIsExisting('tinyDatabase.json', 'emailTable'):
                        createRecord('tinyDatabase.json', 'emailTable', 'registeredEmails')
                    if st.session_state.newEmail not in retrieveRecord('tinyDatabase.json', 'emailTable', 'registeredEmails'):
                        updateRecord('tinyDatabase.json', 'emailTable', 'registeredEmails', st.session_state.newEmail, append=True)

                emailss = retrieveRecord('tinyDatabase.json', 'emailTable', 'registeredEmails') if retrieveRecord('tinyDatabase.json', 'emailTable', 'registeredEmails') else [] # Collect emails for multiselect
                emailss = set(emailss)
                # Get previously selected emails for default value
                # with shelve.open('alertDB.db') as db:
                #     defaultemails = db.get('selectedEmails', [])
                # @st.fragment
                # def selEmails(emailList):
                #     selected_emails = secondss.multiselect(
                #         label='Choose emails to notify',
                #         options=emailss,
                #         key='registeredEmails',
                #     # default=set(defaultemails)
                #     )
                # selEmails(emailss)
                selected_emails = secondss.multiselect(
                        label='Choose emails to notify',
                        options=emailss,
                        key='registeredEmails',
                    # default=set(defaultemails)
                    )
                # Save selected emails back to the database
                # with shelve.open('alertDB.db') as db:
                #     db['selectedEmails'] = selected_emails
                # global emailLists 
                emailLists = selected_emails
                emailLists = json.dumps(emailLists)

                # --------------------- Type Of Alert -----------------------
                st.markdown("<br>", unsafe_allow_html =True)
                antd.divider(label='Alert Type', icon='house', align='center', color='green')
                email, slack = st.columns([1,1], border=True, gap='large')
                with email:
                    # disabled=True if not email_alert else False
                    email_alert =  st.toggle('Email Alert Notification', value = True )
                    email_ai = st.toggle('Activate Email AI Analysis', disabled=True , value=False if not email_alert else True)
                    # with shelve.open('alertDB.db') as db:
                    #     if email_alert:
                    #         db['emailAlert'] = True
                    #     else:
                    #         db['emailAlert'] = False
                    #     if email_ai:
                    #         db['useAI_email'] = True
                    #     else:
                    #         db['useAI_email'] = False
                with slack:
                    slack_alert =  st.toggle('Slack Alert Notification', value=False if email_alert else True, disabled=True if email_alert else False,key='slackalert' )
                    slack_ai = st.toggle('Activate Slack AI Analysis',  disabled=True if not slack_alert else False, value=False if not slack_alert else True)
                    # with shelve.open('alertDB.db') as db:
                    #     if slack_alert:
                    #         db['slackAlert'] = True
                    #     else:
                    #         db['slackAlert'] = False
                    #     if slack_ai:
                    #         db['useAI_slack'] = True
                    #     else:      
                    #         db['useAI_slack'] = False 
                alertingType = 'email' if email_alert else 'slack' if slack_alert else None 
                alerting_ai = 'email_ai' if email_ai else 'slack_ai' if slack_ai else None 
                st.markdown("<br>", unsafe_allow_html =True)

                oneSide, mid, twoSide, threeSide = st.columns([1,0.3, 2,1])
                oneSide.markdown("<br>", unsafe_allow_html=True)
                if oneSide.button('Register Alert', disabled=True if not serverlists else False, use_container_width=True):
                    # if the name is not in existing name, register it, or if its there, raise a flag that ask whether to overwrite or not, if yes to overwrite, then overwrite it, else dont overwrite it
                    existingNames = retrieveAlertName()
                    server_list_json = json.dumps(serverlists)
                    ip_list_json = json.dumps(ips)
                    st.session_state['ipList'] = ip_list_json
                    st.session_state['servList'] = server_list_json
                    
                    if not existingNames or regName.lower() not in existingNames :
                        with sqlite3.connect('EdgeDB.db') as conn:
                            c = conn.cursor()
                            c.execute("INSERT INTO alertUsers (Username, Active, MgtZone, Server_List, IPAddress, CPU_thresh, MEM_thresh, DISK_thresh, Emails, AlertType, Alerting_AI, dateCreated) VALUES (?,?, ?,?, ?, ?,?,?,?,?,?, ?)", 
                                    (regName.lower(), 1, regMgtZone, server_list_json, ip_list_json, cpuThresh, memThresh, diskThresh, emailLists, alertingType, alerting_ai,  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                        st.toast('Alert registration successful')
                    elif regName.lower() in existingNames:
                        right.markdown("<br><br><br>", unsafe_allow_html=True)
                        right.info('Alert!!!. Tagname already exist') 
                        st.toast('Confirm Overwrite or Cancel!!!')
                        right.markdown("""
                            <p style="font-size: 18px; font-weight: bold; text-align: center; margin-top: 10px; margin-bottom:-5px">Overwrite Existing Alert? </p>""", unsafe_allow_html= True)
                        right1, right2, right3, right4 = right.columns([1.5,1,1,1.5])
                        with right2:
                            if st.button('Yes', use_container_width=True, on_click=overwrite, args=(alertingType, alerting_ai)):
                                st.toast(f'Update alert name {regName} done')
                        with right3:
                            if st.button('No', use_container_width=True):
                                st.toast('Regsitration Cancel!!!')

                removeEmail = twoSide.text_input(label = 'Delete Email', label_visibility='hidden', placeholder='Remove an email from the email registry', )
                threeSide.markdown("<br>", unsafe_allow_html=True)
                if threeSide.button('Remove Email', disabled=True if not removeEmail else False, use_container_width=True):
                    removeItemFromRecord('tinyDatabase.json', 'emailTable', 'registeredEmails', removeEmail)
                    # with shelve.open('alertDB.db') as db:
                    #     emails = db.get('emails', [])
                    #     if removeEmail in emails:
                    #         emails.remove(removeEmail)
                    #         db['emails'] = emails
                    #         st.toast(f'{removeEmail} removed from the list')
                    #         time.sleep(1)
                    #     else:
                    #         st.toast(f'{removeEmail} not found in the list')
                    #         time.sleep(1)
                    st.rerun(scope='fragment')

    elif overSelect =='Registered Alerts':
        if 'default_table_shown' in st.session_state:
            del st.session_state['default_table_shown']
        left, middle, right = st.columns([2,3.5,2], gap='large')   
        with middle:
            with st.container(border=False):
                space1, space2, space3 = st.columns([0.6,3,1.5])
                searchName = space2.text_input("Alert Finder", placeholder="Search Alerts By Nametag, MgtZone, Servers, Emails or 'All'", label_visibility='hidden')
                try:
                    with sqlite3.connect('EdgeDB.db') as conn:
                        alert_users = pd.read_sql_query('select * from alertUsers', conn)
                        alert_users['Active']= alert_users['Active'].astype(bool)
                    space3.markdown("<br>", unsafe_allow_html=True)
                    import ast 
                    emails= [email for j in alert_users.Emails.unique().tolist() for email in ast.literal_eval(j)]
                    serverss= [server for j in alert_users.Server_List.unique().tolist() for server in ast.literal_eval(j)]
                    if space3.button('Search Alerts'):
                        if searchName.lower() == 'all' or not searchName:
                            st.dataframe(alert_users.set_index(['Username', 'Active']))
                        elif searchName in alert_users.Username.unique().tolist() :
                            st.dataframe(alert_users[alert_users.Username == searchName], hide_index=True)
                        elif searchName in alert_users.MgtZone.unique().tolist():
                            st.dataframe(alert_users[alert_users.MgtZone == searchName], hide_index=True)
                        elif searchName in emails:
                            keep = []
                            for i in range(len(alert_users.Emails)):
                                if searchName in [i for j in alert_users[['Emails']].iloc[i] for i in ast.literal_eval(j)]:
                                    keep.append(i)
                            if keep:
                                st.dataframe(alert_users.iloc[keep], hide_index=True)
                            else:
                                st.toast('Alert Registry Not Found !!!')
                        elif searchName in serverss:
                            keep = []
                            for i in range(len(alert_users.Server_List)):
                                if searchName in [i for j in alert_users[['Server_List']].iloc[i] for i in ast.literal_eval(j)]:
                                    keep.append(i)
                            if keep:
                                st.dataframe(alert_users.iloc[keep], hide_index=True)
                            else:
                                st.toast('Alert Registry Not Found !!!')
                        else:
                            st.toast('Alert Registry Not Found !!!')
                except Exception:
                    st.error('Alert Registry Not Found')
                        
    elif overSelect =='Deactivate Alerts':
        if 'default_table_shown' in st.session_state:
            del st.session_state['default_table_shown']
        def update_alert_activation(username, is_active):
            try:
                with sqlite3.connect('EdgeDB.db') as conn:
                    conn.execute(
                        "UPDATE alertUsers SET Active = ? WHERE Username = ?",
                        (int(is_active), username)
                    )
                    conn.commit()
            except Exception as e:
                st.error(f"Error updating activation status: {e}")
        left, middle, right = st.columns([2,4,2], gap='large')   
        with middle:
            with st.container(border=False):
                st.markdown('<br><br>', unsafe_allow_html=True)
                st.markdown("<p>Click or unclick the Active column to activate or deativate alert</p>", unsafe_allow_html=True)
                try:
                    with sqlite3.connect('EdgeDB.db') as conn:
                        alert_users= pd.read_sql_query('SELECT * FROM alertUsers', conn)
                        alert_users['Active']= alert_users['Active'].astype(bool)
                    alert_users.set_index(['Username'], inplace = True)
                    st.session_state['original_df'] = alert_users
                    edited_df = st.data_editor(
                        alert_users,
                        key="alert_activation_editor",
                        column_config={
                            "Active": st.column_config.CheckboxColumn(
                                label="Active",
                                help="Toggle to activate or deactivate the alert",
                            ),
                            "Server_List": st.column_config.TextColumn(
                                label="Servers",
                                help="List of servers",
                            ),
                            "Emails": st.column_config.TextColumn(
                                label="Emails",
                                help="List of emails",
                            ),
                            "IPAddress": st.column_config.TextColumn(
                                label='IPAddress'
                            )

                        },
                        disabled=["Server_List", "Emails"],  # Prevent editing other columns
                        use_container_width=True,
                        num_rows="dynamic",
                    )

                    if not edited_df.equals(st.session_state['original_df']):
                        change=st.session_state['original_df'].compare(edited_df)
                        if not change.empty:
                            if 'Active' in change.columns.levels[0]:
                                for i in change.index:
                                    new_status=edited_df.loc[i, 'Active']
                                    update_alert_activation(i, new_status)
                                    st.toast("Alert activation status updated successfully")

                except Exception as e:
                    st.error(f'Seems you are trying to create a new alert here. Pls revert to the Register Page')

    elif overSelect == 'Open Tickets':
        # st_autorefresh(interval=1 * 60 * 1000, key="interfaceRefresher2")
        # if 'default_table_shown' in st.session_state:
        #     del st.session_state.default_table_shown
        left, middle, right = st.columns([2, 4, 2], gap='large')
        with middle:
            with st.container(border=False):
                outs, space1, space2, space3 = st.columns([0.5, 0.6, 2.4, 1])
                searchProblem = space2.text_input("Problem Finder", placeholder="Search Problems By Alert username, Server, Metric, Status or 'All'", label_visibility='hidden', )
                outs.markdown("<br>", unsafe_allow_html=True)
                opened = outs.button('Open', use_container_width=True)
                space1.markdown("<br>", unsafe_allow_html=True)
                closed = space1.button('Closed', use_container_width=True)
                st.markdown("<br>", unsafe_allow_html=True)

                from matplotlib.colors import LinearSegmentedColormap
                colors = ["orange", "blue"]  # Orange for OPEN (0), Blue for CLOSED (1)
                custom_cmap = LinearSegmentedColormap.from_list("OpenClosed", colors)

                try:
                    with sqlite3.connect('EdgeDB.db') as conn:
                        open_problems = pd.read_sql_query('SELECT * FROM openProblems', conn)
                        open_problems.drop(['id', 'time_active'], axis=1, inplace=True)
                        open_problems.sort_values(by = 'first_breach_date', ascending=False, inplace=True)

                    # Display the default table when the tab is switched to
                    if "default_table_shown" not in st.session_state:
                        st.session_state["default_table_shown"] = True
                        st.dataframe(open_problems.set_index(['alert_username']), use_container_width=True)

                    def timeDifference(x):
                        log_time = datetime.strptime(x, "%Y-%m-%d %H:%M:%S")
                        now = datetime.now()
                        time_difference = abs(now - log_time)
                        hours, remainder = divmod(time_difference.total_seconds(), 3600)
                        minutes, seconds = divmod(remainder, 60)
                        times = f"{int(hours)}:{int(minutes):02d}:{int(seconds):02d}"
                        return times

                    if opened:
                        st.session_state["default_table_shown"] = False  # Reset default table flag
                        open_problems = open_problems[open_problems['status'] == 'OPEN']
                        open_problems['timeActive'] = open_problems.first_breach_date.apply(lambda x: timeDifference(x))
                        st.dataframe(open_problems.reset_index(drop=True), use_container_width=True, )
                        st.session_state.default_table_shown = True

                    if closed:
                        st.session_state["default_table_shown"] = False  # Reset default table flag
                        open_problems = open_problems[open_problems['status'] == 'CLOSED']
                        st.dataframe(open_problems.set_index(['alert_username']), use_container_width=True)

                    space3.markdown("<br>", unsafe_allow_html=True)
                    if space3.button('Search Problems', use_container_width=True):
                        st.session_state["default_table_shown"] = False  # Reset default table flag
                        if searchProblem.lower() == 'all' or not searchProblem:
                            st.dataframe(open_problems.set_index(['alert_username', 'status']), height=500)
                        elif searchProblem in open_problems.alert_username.unique().tolist():
                            st.dataframe(open_problems[open_problems.alert_username == searchProblem], hide_index=True)
                        elif searchProblem in open_problems.server.unique().tolist():
                            st.dataframe(open_problems[open_problems.server == searchProblem], hide_index=True)
                        elif searchProblem in open_problems.metric.unique().tolist():
                            st.dataframe(open_problems[open_problems.metric == searchProblem], hide_index=True)
                        elif searchProblem in open_problems.status.unique().tolist():
                            st.dataframe(open_problems[open_problems.status == searchProblem], hide_index=True)
                        else:
                            st.toast('Problem Registry Not Found !!!')
                except Exception as e:
                    st.error(f'Problem Registry Not Found: {e}')
                    print('There is a problem', e)



            

                         
    
                  
    
with tab3:
    st.markdown("<br>", unsafe_allow_html =True)
    alerting()
    st.markdown("<br>", unsafe_allow_html =True)
    st.markdown("<br>", unsafe_allow_html =True)
    
    # thresholds()

    # antd.divider(label='Alert Notification Configuration', icon='house', align='center', color='yellow')
    # threshold()

# ------------------------ Alerting for high CPU, Memory, and Disk Usage. --------------------------------------- 
fullData = fetch_data()
# def saveLastRow():
#     with shelve.open('keepLastRow.db') as db:
#         db['lastRow'] = len(fullData)
#         db['previouslyLoaded'] = True       
# def retrieveLastRow():
#     with shelve.open('keepLastRow.db') as db:
#         return db.get('lastRow', 0), db.get('previouslyLoaded', False)
def deleteKeepLastRow():
    if os.path.exists('keepLastRow.db'):
        os.remove('keepLastRow.db')
    else:
        pass

# call the alerting script to create an alert if the set conditions are met
# def startAlertingProcess():
#     """Runs the alerting logic in a separate thread."""
#     from alerting import alertOut
#     def run_alerting():
#         try:
#             alertOut(emailLists)  # Call the alerting function directly
#         except Exception as e:
#             logger.error(f"Error in alerting process: {e}", exc_info=True)
#             # print(f"Error in alerting process: {e}")

#     # Start the alerting thread
#     alertThreading = threading.Thread(target=run_alerting, daemon=True)
#     alertThreading.start()

# get the latest update time from edgeDB
with sqlite3.connect('EdgeDB.db') as conn:
    query = f"""select last_update_time from latestLogTime
                order by last_update_time desc limit 1;
            """
    cursor = conn.cursor()
    cursor.execute(query)
    last_update_time = cursor.fetchone()[0]

# A logic to check if the data has been updated 
if 'data_updated' not in st.session_state:
    st.session_state.data_updated = last_update_time
data_is_updated = last_update_time != st.session_state.data_updated

# A function to run the email script 
def run_email_script():
    try:
        # Start the subprocess
        process = subprocess.Popen(['python', 'alerting.py'])
        # Wait for the process to complete
        process.wait()
    except Exception as e:
        print(f"Error running email script: {e}")
    finally:
        # Ensure the process is terminated
        if process.poll() is None:  # Check if the process is still running
            process.terminate()

        process = None  # Release the process object
        gc.collect()
        del gc.garbage[:]
 


 
# if data_is_updated:
#     checkData = fullData[fullData.LogTimestamp > st.session_state.data_updated]  #! Using the latest log saved in session_state because that was the latest log of the data before it was updated
#     checkData['HostAndIP'] = checkData['Hostname'] + checkData['IPAddress']
#     st.session_state.data_updated = last_update_time # update the session_state latest log
    
#     # Exclude ignored servers
#     with shelve.open('alertDB.db') as db:
#         ignoredServers = db.get('ignoredServers', [])
#     checkData = checkData[~checkData['Hostname'].isin(ignoredServers)]

#     highCPU = checkData[checkData['CPUUsage'] > st.session_state.cpuThresh]
#     highMem = checkData[checkData['MemoryUsage'] > st.session_state.memThresh]
#     highDisk = checkData[checkData['TotalFreeDiskGB'] < st.session_state.diskThresh]

#     def alertConcerns(info, item):
#         with shelve.open('alertDB.db') as db:
#             db[info] = item
   
#     critical = [i for i in highCPU.HostAndIP if i in highMem.HostAndIP and i in highDisk.HostAndIP]
#     countCritical = len(critical)
#     countHighCPU = len(highCPU.Hostname.unique())
#     countHighMem = len(highMem.Hostname.unique())
#     countHighDisk = len(highDisk.Hostname.unique())

#     if countHighCPU > 0 or countHighMem > 0 or countHighDisk > 0 or countCritical > 0:
#         alertConcerns('maxLastTime', checkData.LogTimestamp.max()) # Save earliest time after last alert
#         alertConcerns('minLastTime', checkData.LogTimestamp.min()) # Save earliest time after last alert

#         if countCritical > 0:
#             alertConcerns('critical_servers', critical)
#             alertConcerns('critical', True)
#         else:
#             alertConcerns('critical', False)
#             alertConcerns('critical_servers', None)

#         if countHighCPU > 0:
#             alertConcerns('highCPU_servers', [i for i in highCPU.Hostname.unique()]) 
#             alertConcerns('highCPU', True)
#         else:
#             alertConcerns('highCPU_servers', []) 
#             alertConcerns('highCPU', False)

#         if countHighMem > 0:
#             alertConcerns('highMem_servers', [i for i in highMem.Hostname.unique()])
#             alertConcerns('highMem', True)
#         else:
#             alertConcerns('highMem_servers', [])
#             alertConcerns('highMem', False)
            
#         if countHighDisk > 0:
#             alertConcerns('highDisk_servers', [i for i in highDisk.Hostname.unique()])
#             alertConcerns('highDisk', True)
#         else:
#             alertConcerns('highDisk_servers', [])
#             alertConcerns('highDisk', False)


         
#     else:
#         alertConcerns('critical_servers', [])
#         alertConcerns('critical', False)

#         alertConcerns('highCPU_servers', [])
#         alertConcerns('highCPU', False)

#         alertConcerns('highMem_servers', [])
#         alertConcerns('highMem', False)

#         alertConcerns('highDisk_servers', [])
#         alertConcerns('highDisk', False)

#     checkData, highCPU, highMem, highDisk, fullData = None, None, None, None, None
#     del checkData, highCPU, highMem, highDisk, fullData
#     gc.collect()
#     del gc.garbage[:]
# else:
#     saveLastRow()
atexit.register(deleteKeepLastRow)

# Function to start the alerting process in a separate thread




    # with stop:
    #     if st.button('Stop App'):
    #         if os.path.exists('interfaceRefresh.db'):
    #             os.remove('interfaceRefresh.db')
    #         kill_process()

    # if st.session_state.process_killed:
    #     st.toast("Stopping app...")
    #     st.stop()

# st.session_state['usageMonitor'] += 1



        # if fourth.button('Register'):
        #         st.toast('Registered new alert thresholds')

############################################################# CHAT #########################################################


def genModel():
    import google.generativeai as genai
    gemini_api = 'AIzaSyCbwfzBjY9ucaZdPd8apShPgrF-EuN_sPQ'
    # gemini_api = 'AIzaSyDeP_zjRubaAZOBE4iDe7nNFoiJyE3xF-w'
    genai.configure(api_key=gemini_api)
    generation_config = {
    "temperature": 2,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 15000,
    "response_mime_type": "text/plain",
    }
    safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    ]

    model = genai.GenerativeModel(
                            # model_name="gemini-1.5-pro",
                            model_name ="gemini-2.0-flash-thinking-exp-01-21",
                            safety_settings=safety_settings,
                            generation_config=generation_config,
                            system_instruction=googleModelInstruction()
    )
    return model

# def saveHistory(history, filename='chatHistory.db'):
#     with shelve.open(filename) as db:
#         db['history'] = history
    
# def loadHistory(filename='chatHistory.db'):
#     with shelve.open(filename) as db:
#         return db.get('history', [])

# history_ = loadHistory()

# @st.fragment
def naturalLanguage():
    modellingData = fetch_data()
    modellingData['HostAndIP'] = modellingData['Hostname'] + modellingData['IPAddress']
    modellingData['LogTimestamp'] = pd.to_datetime(modellingData['LogTimestamp'])

    def query_gpt(prompt):
        convo = genModel().start_chat(history= history_)
        convo.send_message(prompt)
        model_response = convo.last.text
        if prompt:
            history_.append({"role": "user", "parts": [prompt]})
            history_.append({"role": "model", "parts": [convo.last.text]})
            saveHistory(history_)
        return model_response
    
    chat, frame = st.columns([1,3], border = True)
    if prompt := st.chat_input('Chat with your data'):
        chat.chat_message('human').write(prompt)
        response = query_gpt(prompt)
        st.write(response)
        if response.split(']')[0] == '[PP': 
            chat.chat_message('ai').write('Here is your requested data. You can download it by hovering over the dataframe and clicking on the download icon at the top right corner of the table')
            # chat.chat_message('ai').write(response)
            output = response.split(']', 1)[1]
            
            try:
                # Evaluate the query
                output = eval(output)
                # Handle different output types
                if isinstance(output, pd.DataFrame):
                    frame.dataframe(output, use_container_width=True)
                    if output.empty: 
                        frame.info('No condition was met. The specifics you requested were not found in the database')
                        frame.warning('You can ask the chat to show all information on the table so to enable you see what youare not referencing correctly')
                elif isinstance(output, pd.Series):
                    frame.write(output.to_frame())  # Convert to DataFrame for display
                elif isinstance(output, list):
                    frame.write(pd.Series(output))
                elif isinstance(output, (int, float, str)):
                    frame.write(f'There are {output}')
                else:
                    with frame:
                        st.warning("Unhandled Output Type: Please reframe your request.")
                        st.markdown(
                            """
                            <div style="background-color: #FFB433; padding: 10px; text-color: white;">
                                <strong>Helpful Tips:</strong>
                                <ul>
                                    <li>You can request the system to provide the SQL query related to your question. <br>To do this, simply copy and paste the following syntax:<br>
                                    <b>Give an alternative SQL Query to the question I just asked you</b><br>
                                    This will generate an SQL query that you can use in the SQL Query tab to obtain your desired output.</li>
                                </ul>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    frame.write(output)
                    frame.write(response)
            except Exception as e:
                frame.error(f"Error occurred: {e}")
            
        elif response.split(']')[0] == '[NP':
            chat.chat_message('ai').write(response.split(']', 1)[1])
    if not prompt:
        
        chat.warning('No prompt yet.')
        frame.warning('Nothing to display')
    # st.write(response)
    st.markdown(
        """
        <div style="background-color: #e7f3fe; padding: 10px; border-left: 6px solid #2196F3; color: #333;">
            <strong>Info:</strong>
            <ul>
                <li>The agent remembers your previous discussion and tables. You can chat based on previously discussed table of data and ask questions around it.</li>
                <li>If the returned DataFrame is empty, then it means none of the conditions in your query were met.</li>
                <li>Check again and be sure of the specifics of your query.</li>
                <li>If you are querying specifics, ensure you are right with the name or spelling of the specific.</li>
                <li>Please be clear and direct as possible to ensure your request is processed with accuracy.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )

    modellingData, output = None, None
    del modellingData , output
    gc.collect()
    del gc.garbage[:]

@st.fragment
def sqlQuery():
    chats, frames = st.columns([1.5,3], border = True)
    if query := chats.text_area('SQL Query', height= 200, placeholder='Write your SQL query here'):
        try:
            with connectClientDB(clientServer, clientDB, clientDBUserName, clientDBPass) as conn:
                output = pd.read_sql_query(query, conn)
        except Exception as e:
            output = f'Got an error: {e}'
            logger.error(f"Error executing SQL query: {e}", exc_info=True)

        if isinstance(output, pd.DataFrame):
            frames.dataframe(output)
        elif isinstance(output, str):
            frames.warning(output)

    if not query:
        chats.warning('No sql query yet')
        frames.warning('Table retrieved from SQL db')
    

    output = None
    del output
    gc.collect()
    del gc.garbage[:]



@st.fragment
def aiAnalyser():
    data = fetch_data()
    st.markdown('<br>', unsafe_allow_html=True)
    hold1, mgtZone, server, buttonPress, hold2 = st.columns([0.2, 1.5,3,1, 0.2])
    selMgt = mgtZone.selectbox('Management Zone', options=[i for i in data.ManagementZone.unique().tolist()], key='mgtZone')
    selServers= server.multiselect('Selected Servers', options=[i for i in data[data.ManagementZone == st.session_state.mgtZone].Hostname.unique().tolist()])
    if selServers:
        if not tableIsExisting('tinyDatabase.json', 'AutoAI_server'):
            createRecord('tinyDatabase.json', 'AutoAI_server', 'servers')
        updateRecord('tinyDatabase.json', 'AutoAI_server', 'servers', selServers[0], append = False)
        sel_selServers = retrieveRecord('tinyDatabase.json', 'AutoAI_server', 'servers')

        # with shelve.open('prefServers.db') as db:
        #     db['server'] = selServers
        #     sel_selServers= db['server']
        st.session_state['preferedServers'] = selServers
        st.session_state['sel_mgtZone'] = selMgt
        server_ispresent = True
    else:
        server_ispresent = False
        st.session_state['preferedServers'] = []
    buttonPress.markdown("<br>", unsafe_allow_html=True)
    generateOut = buttonPress.button('Expert Analysis', use_container_width=True, disabled=True if not server_ispresent else False)
    
    st.markdown('<br>', unsafe_allow_html=True)
    profile = 'aiAnalysis'
    with stylable_container(
                key="visual_container35",
                css_styles="""{
                            # border: 1px solid rgba(49, 51, 63, 0.2);
                            # box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                            box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
                            border-radius: 1.5rem;
                            padding: 20px 20px 20px 20px;
                            margin-top: 10px;
                        }"""):
        if generateOut:
            with st.spinner(f'Generating expert analysis on {", ".join(sel_selServers)}...'):
                payload = {
                    'expert_type': 'aiAnalysis'
                }
                try:
                    response = requests.post("http://127.0.0.1:3000/aiAnalysis_expert",
                                            json={'expert_type': 'aiAnalysis'},
                                            stream=True)
                    if response.status_code == 200:
                        full_response = ""
                        placeholder = st.empty()
                        for chunk in response.iter_content(chunk_size=128, decode_unicode=True):
                            full_response += chunk
                            placeholder.markdown(full_response + "▌")  # Cursor effect
                        placeholder.markdown(full_response)  # Final result
                        st.toast("Expert Analysis Complete!")
                    else:
                        st.error(f"Error {response.status_code} :- {response.text}")         
                except Exception:
                    pass
    data = None
    del data
    gc.collect()
    del gc.garbage[:]


# data = fetch_data()
# modellingData = data.sort_values(by = 'LogTimestamp', ascending=False).reset_index(drop=True)
# modellingData['HostAndIP'] = modellingData['Hostname'] + modellingData['IPAddress']
# modellingData['LogTimestamp'] = pd.to_datetime(modellingData['LogTimestamp'])


@st.fragment
def selfAnalyser():
    st.markdown('<br>', unsafe_allow_html=True)
    with stylable_container(
                key="visual_container36",
                css_styles="""{
                            # border: 1px solid rgba(49, 51, 63, 0.2);
                            # box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                            box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
                            border-radius: 1.5rem;
                            padding: 20px 20px 20px 20px;
                            margin-top: 10px;
                        }"""):
        
        if 'queryHistory' not in st.session_state:
            st.session_state.queryHistory = []

        chat, frame = st.columns([1,2], border = True)
        prompt = st.chat_input('Chat with your data', key='selfAnalyze')
        if prompt:
            chat.chat_message('human').write(prompt)
            st.markdown("<br>", unsafe_allow_html=True)

            payload = {'prompt': prompt,
                       'histories': st.session_state.queryHistory}
            
            responses = requests.post("http://127.0.0.1:3000/selfAnalysis_expert",
                                            json=payload,
                                            stream=True)
            if responses.status_code == 200:
                full_responses = ""
                placeholders = st.empty()
                for chunk in responses.iter_content(chunk_size=128, decode_unicode=True):
                    full_responses += chunk
                #     placeholders.markdown(full_responses + "▌")
                # placeholders.markdown(full_responses)  # Final result 
                st.toast("Query Replied!")

                assistant_reply = full_responses

                st.session_state.queryHistory.append({
                    "role": "user",
                    "content": prompt
                })
                st.session_state.queryHistory.append({
                    "role": "assistant",
                    "content": assistant_reply
                })
            else:
                st.error(f"Error {responses.status_code} :- {responses.text}")
            if full_responses.split(']')[0] == '[PP': 
                frame.chat_message('ai').write('Here is your requested data. You can download it by hovering over the dataframe and clicking on the download icon at the top right corner of the table')

                output = full_responses.split(']', 1)[1]
                try: # Evaluate the query
                    output = eval(output)
                    if isinstance(output, pd.DataFrame):
                        with st.container(border=False):
                            st.dataframe(output.set_index('Hostname'), use_container_width=True)
                        if output.empty: 
                            frame.info('No condition was met. The specifics you requested were not found in the database')
                            frame.warning('You can ask the chat to show all information on the table so to enable you see what you are not referencing correctly')
                    elif isinstance(output, pd.Series):
                        with st.container(height=400, border=None):
                            st.write(output.to_frame())
                    elif isinstance(output, list):
                        frame.markdown('<br>', unsafe_allow_html=True)
                        frame.write(pd.Series(output))
                    elif isinstance(output, (int, float, str)):
                        frame.markdown('<br>', unsafe_allow_html=True)
                        frame.write(f'There are {output}')
                    else:
                        with frame:
                            st.warning("Unhandled Output Type: Please reframe your request.")
                            st.markdown(
                                """
                                <br>
                                <div style="background-color: #FFB433; padding: 10px; text-color: white;">
                                    <strong>Helpful Tips:</strong>
                                    <ul>
                                        <li>You can request the system to provide the SQL query related to your question. <br>To do this, simply copy and paste the following syntax:<br>
                                        <b>Give an alternative SQL Query to the question I just asked you</b><br>
                                        This will generate an SQL query that you can use in the SQL Query tab to obtain your desired output.</li>
                                    </ul>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        # frame.write(output)
                        # frame.write(full_responses)
                except Exception as e:
                    frame.error(f"Error occurred: {e}")
                
            elif full_responses.split(']')[0] == '[NP':
                frame.chat_message('ai').write(full_responses.split(']', 1)[1])

            st.session_state.conversation_history = st.session_state.conversation_history[-5:]
        if not prompt:
            chat.warning('No prompt yet.')
            frame.warning('Expert Response')        
   
@st.fragment
def conversational():
    with stylable_container(
        key="visual_container37",
        css_styles="""{
                    # border: 1px solid rgba(49, 51, 63, 0.2);
                    # box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                    box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
                    border-radius: 1.5rem;
                    padding: 20px 20px 20px 20px;
                    margin-top: 10px;
                }"""): 

        st.markdown("<br>", unsafe_allow_html=True)   
        if 'conversation_history' not in st.session_state:
            st.session_state.conversation_history = []

        chat, frame = st.columns([1, 2], border=False)

        if prompt := st.chat_input('Chat with your data', key = 'uni'):
            chat.chat_message('human').write(prompt)

            payload = {'prompts': prompt,
                       'history': st.session_state.conversation_history}
            try:
                with st.spinner("Thinking..."):
                    responsess = requests.post("http://127.0.0.1:3000/conversation_expert", json=payload,  stream=True)

                if responsess.status_code == 200:
                    full_responsess = ""
                    placeholderss = frame.empty()
                    for chunk in responsess.iter_content(chunk_size=128, decode_unicode=True):
                        full_responsess += chunk
                        placeholderss.markdown(full_responsess + "▌")
                    placeholderss.markdown(full_responsess)  # Final result 
                    st.toast("Query Replied!")
                    assistant_reply = full_responsess

                    st.session_state.conversation_history.append({
                        "role": "user",
                        "content": prompt
                    })
                    st.session_state.conversation_history.append({
                        "role": "assistant",
                        "content": assistant_reply
                    })

                else:
                    assistant_reply = "Sorry, backend error occurred."

            except Exception as e:
                st.warning(f"Error occurred: {e}")
                assistant_reply = "Sorry I couldn't think of an answer to that."

            # Keep only last 10 history
            st.session_state.conversation_history = st.session_state.conversation_history[-5:]

        if not prompt:
            chat.chat_message('human').write('Your prompt goes here.')
            frame.chat_message('ai').write('Hello there! I am your telemetry conversational AI assistant. You want to converse with your data?')
    # st.write(st.session_state.conversation_history)



with tab2:
    col1, col2, col3 = st.columns([1,4,1])
    with col2:
        tabs1, tabs2, tabs3, tabs4, tabs5 = st.tabs(['Natural-Language Query', 'Auto-Expert Analysis', 'Conversational Query', 'SQL Query', 'Feedback'])
        with tabs1:
            tab1.markdown("<br>", unsafe_allow_html=True)
            selfAnalyser()
        with tabs2:
            aiAnalyser()
        with tabs3:
            conversational()
        with tabs4:
            st.markdown("<br>", unsafe_allow_html=True)
            sqlQuery()


fullData = None
del fullData
gc.collect()
gc.garbage[:]