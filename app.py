import json
import time
import os
import requests
import threading
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta


# Content
st.set_page_config(
    page_title="Croner", 
    page_icon="favicon.ico"
    )
st.title("Welcome croners! This is webapp called Croner!")
st.write("The name is derived from cron... right!? ;)")

WIZARD_SERVICE = os.getenv("WIZARD_SERVICE")
WIZARD_PORT = os.getenv("WIZARD_PORT")

class Croner:
    def __init__(self, wizard_service, wizard_port):
        self.url = f"http://{wizard_service}:{wizard_port}/create_pod"

    def report_date(self):
        self.start_date = st.sidebar.date_input("Start date to generate report")
        self.end_date = st.sidebar.date_input("End date to generate report")
    
    def generate_report(self, start_date, end_date):
        command = f"create_pod,croner-pod-{str(int(time.time()))},timetrace,report,--start,{start_date},--end,{end_date},-o,json,-f,data/reports/latest"
        self.post_request(command)
        
    def show_data(self):
        with open('data/reports/latest', 'r') as f:
            data = json.load(f)
        table_data = []
        for project in data:
            table_data.append([project, '', '', ''])
            for record in data[project]['records']:
                start_time = datetime.fromisoformat(record['start']).strftime('%Y-%m-%d %H:%M:%S')
                end_time = datetime.fromisoformat(record['end']).strftime('%Y-%m-%d %H:%M:%S')
                duration_hours = round((datetime.fromisoformat(record['end']) - datetime.fromisoformat(record['start'])).total_seconds() / 3600, 2)
                table_data.append(['', start_time, end_time, duration_hours])

            total_hours = round(data[project]['total'] / 3600000000000, 2)
            table_data.append(['', '', '', f'Total: {total_hours} hours'])
        
        self.df = pd.DataFrame(table_data, columns=['Project', 'Start Time', 'End Time', 'Duration'])
        self.csv = self.df.to_csv(index=False).encode('utf-8')
        st.table(self.df)

    def convert_df(self):
        return self.df.to_csv(index=False).encode('utf-8')

    def start_project(self, project_name):
        if f"{project_name}.json" in os.listdir('data/projects'):
            command = f"create_pod,croner-pod-{str(int(time.time()))},timetrace,start,{project_name}"
            self.post_request(command)
        else:
            command = f"create_pod,croner-pod-{str(int(time.time()))},timetrace,create,project,{project_name}"
            self.post_request(command)
            time.sleep(10)
            command = f"create_pod,croner-pod-{str(int(time.time()))},timetrace,start,{project_name}"
            self.post_request(command)

    def stop_project(self):
        command = f"create_pod,croner-pod-{str(int(time.time()))},timetrace,stop"
        self.post_request(command)

    def post_request(self, command):
        data = {"text": command}
        json_data = json.dumps(data)
        headers = {"Content-Type": "application/json"}
        thread = threading.Thread(target=requests.post, args=(self.url, ), kwargs={"headers": headers, "data": json_data})
        thread.start()
        time.sleep(8)
    
    def list_projects(self):
        folder_path = "data/projects"
        file_list = os.listdir(folder_path)

        # Filter only the JSON files that were created in the last 2 months
        one_month_ago = datetime.now() - timedelta(days=60)
        json_files = [f for f in file_list if f.endswith(".json") and os.path.getctime(os.path.join(folder_path, f)) >= one_month_ago.timestamp()]

        # Show the JSON files in a Streamlit table
        if json_files:
            st.write("Projects:")
            table_data = [{"Projects": os.path.splitext(f)[0]} for f in json_files]
            st.table(table_data)
        else:
            st.write("No JSON files created in the last month.")


# Define the Streamlit app
def app():

    # creating croner app object
    croner_app = Croner(WIZARD_SERVICE, WIZARD_PORT)

    # Create a dropdown menu to select the page
    page = st.sidebar.selectbox("Select a page", ["Track Project", "Report", "Experimental"])

    # Track Project page
    if page == "Track Project":
        # Add a text input and two buttons side by side
        col1, col2 = st.columns(2)
        project_name = col1.text_input("Enter the project name")
        if col2.button("Start"):
            # Send the curl command1
            croner_app.start_project(project_name)
            st.write(f"Project {project_name} started")
            col2.button("Stop", key="stop")
        elif col2.button("Stop", key="stop"):
            # Send the curl command2
            croner_app.stop_project()
            st.write(f"Project {project_name} stopped")
        croner_app.list_projects()
        
    # Report page
    elif page == "Report":
        # Call the show_data() function to retrieve the data from the JSON database
        if st.button("Reload"):
            croner_app.show_data()
        croner_app.report_date()
        generate = st.sidebar.button("Generate")
        if generate:
            croner_app.generate_report(croner_app.start_date, croner_app.end_date)
        croner_app.show_data()
        st.download_button(
                            "Download",
                            croner_app.csv,
                            "data/report.csv",
                            "text/csv",
                            key='download-csv'
                            )
    
    # Experimental page
    elif page == "Experimental":
        st.write("TODO, page to edit records")

# Run the Streamlit app
if __name__ == "__main__":
    app()