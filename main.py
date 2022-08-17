import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from ast import literal_eval as make_tuple
from PIL import Image

# Replace with your Datacake Credentials and Workspace UUID
token = "4a4352bd064fa5bab32c8917721d2eebef1261ad"
workspace = "1bac80b6-af05-4ac7-be56-49f899841131"
headers = {"Authorization": f"Token {token}"}

# GraphQL Query helper function
def run_query(query):
    request = requests.post('https://api.datacake.co/graphql/', json={'query': query}, headers=headers)
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(request.status_code, query))

# Helper class to convert GraphQL dictionary parsed from JSON to Python Object
class DictObj:
    def __init__(self, in_dict:dict):
        for key, val in in_dict.items():
            if isinstance(val, (list, tuple)):
               setattr(self, key, [DictObj(x) if isinstance(x, dict) else x for x in val])
            else:
               setattr(self, key, DictObj(val) if isinstance(val, dict) else val)

# Actual Datacake Query
query = """
query {{
  allDevices(inWorkspace:"{workspace}") {{
    online
    verboseName
    id
    serialNumber
    roleFields {{
      field {{
        fieldName
        verboseFieldName
      }}
      value
      chartData
      role
    }}
  }}
}}
""".format(workspace=workspace)

# Run Datacake GraphQL query
a = time.time()
result = run_query(query)
my_obj = DictObj(result)
b = time.time()

# Precalculations and KPI Generation
try:
    total = 0
    locations = []
    for device in my_obj.data.allDevices:
        for field in device.roleFields:
            if field.role == "PRIMARY":
                total = total + float(field.value)
            if field.role == "DEVICE_LOCATION":
                # we need to adapt location data to Streamlit
                try:
                    location = make_tuple(field.value)
                    locations.append(list(location))
                except Exception as e:
                    print("failed parsing coords")
    total = total / len(my_obj.data.allDevices)
except Exception as e:
    print(e)

# -------------------------------------------------------------------------------------------------------------------
# Streamlit Stuff

st.set_page_config(layout="wide")

image = Image.open('dtck@2x.jpg')
st.image(image, width=200) 

col1, col2 = st.columns(2)

# KPIs and Header
with col1:
    num = len(my_obj.data.allDevices)
    time_delta = b - a   
    st.title("Datacake GraphQL Custom Dashboard Demonstration")
    st.write("We are using Streamlit to build a Dashboard that fetches air quality data from Datacake GraphQL API.")    
    st.metric(label="Number of Devices", value=f"{num} Devices")
    st.metric(label="Average Dust", value=f"{round(total, 2)} µg/m3")
    st.metric(label="Query Execution Time", value=f"{round(time_delta, 2)} Seconds")        

# Map
with col2:
    mapdata = pd.DataFrame(locations,columns=['latitude', 'longitude'])
    st.map(mapdata, zoom=1)

# Separator
st.markdown("""<hr style="height:4px;border:none;color:#555;background-color:#555;" /> """, unsafe_allow_html=True)
st.header("Device Overview")
st.write("The following data represents individual data.")

# Single device elements
for device in my_obj.data.allDevices:

    with st.expander(device.verboseName, expanded=True):

        st.subheader(device.verboseName)
        st.caption(device.serialNumber)

        col1, col2 = st.columns([1, 2])

        with col1:
            for field in device.roleFields:
                if field.role == "PRIMARY":
                    delta = 0
                    try:
                        delta = field.chartData[-1] - field.chartData[0]
                    except Exception as e:
                        print(e)
                    st.metric(label="PM10 Dust", value=f"{round(float(field.value),2)} µg/m3", delta=f"{round(float(delta), 2)} µg/m3")

                if field.role == "SECONDARY":
                    st.metric(label="Temperature", value=f"{round(float(field.value),2)} °C")

        with col2:
            for field in device.roleFields:
                if field.role == "PRIMARY":
                    chart_data = pd.DataFrame(np.array(field.chartData))
                    st.area_chart(chart_data)
