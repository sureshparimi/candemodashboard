import streamlit as st
import pandas as pd
import requests
import base64
import os
import plotly.graph_objects as go
import numpy as np

# Constants
USERNAME = os.environ.get("USER_NAME")
API_TOKEN = os.environ.get("API_TOKEN")
BASE_URL = os.environ.get("BASE_URL")

# PowerBI style modern colors
colors = ['#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#34495e', '#e74c3c', '#1abc9c', '#f1c40f']

# Functions
def fetch_data(url, params=None):
    auth_str = f"{USERNAME}:{API_TOKEN}"
    encoded_auth = base64.b64encode(auth_str.encode()).decode()
    headers = {"Authorization": f"Basic {encoded_auth}", "Accept": "application/json"}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def get_projects():
    url = f"{BASE_URL}/rest/api/3/project"
    return {project['key']: project['name'] for project in fetch_data(url)}

def get_fix_versions(project_key):
    url = f"{BASE_URL}/rest/api/3/project/{project_key}/versions"
    versions = fetch_data(url)
    return [version['name'] for version in versions]

def get_issues(jql):
    url = f"{BASE_URL}/rest/api/3/search"
    params = {"jql": jql, "expand": "changelog,issuelinks"}
    return fetch_data(url, params).get('issues', [])

def fetch_issue_data(issue):
    try:
        cat_scope = issue['fields'].get('customfield_10079', {}).get('value', "Not updated")
        jira_key = issue.get('key', "Unknown")
        summary = issue['fields'].get('summary', "Not updated")
        issue_type = issue['fields'].get('issuetype', {}).get('name', "Not updated")
        status = issue['fields'].get('status', {}).get('name', "Not updated")
        fix_version = issue['fields'].get('fixVersions', [])[0]['name'] if issue['fields'].get('fixVersions') else "Not updated"
        project = issue['fields']['project']['key']
        it_portal_sr_cr = issue['fields'].get('customfield_10065', "Not updated")
        
        comments = ""
        if jira_key == "Unknown":
            comments += "Error: JIRA Key is missing. "
        if summary == "Not updated":
            comments += "Error: Summary is missing. "
        if issue_type == "Not updated":
            comments += "Error: Issue Type is missing. "
        if status == "Not updated":
            comments += "Error: Status is missing. "
        if fix_version == "Not updated":
            comments += "Error: Fix Version is missing. "
        if project == "Not updated":
            comments += "Error: Project is missing. "
        if it_portal_sr_cr == "Not updated":
            comments += "Error: IT Portal / SR / CR is missing. "
        
        return {
            'JIRA Key': jira_key,
            'Summary': summary,
            'Type': issue_type,
            'Status': status,
            'Fix Version': fix_version,
            'Project': project,
            'CAT Scope': cat_scope,
            'IT Portal / SR / CR': it_portal_sr_cr,
            'Comments': comments if comments else ""  
        }
    except Exception as e:
        error_message = str(e)
        if hasattr(e, 'response') and e.response and 'errorMessages' in e.response.json():
            error_message = ", ".join(e.response.json()['errorMessages'])
        return {
            'JIRA Key': "Unknown",
            'Comments': f"Error in 'fetch_issue_data': {error_message}"
        }

def process_issues(selected_fix_versions, selected_project_keys):
    data = []
    for selected_project_key in selected_project_keys:
        for selected_fix_version in selected_fix_versions:
            jql_query = f'project = {selected_project_key} AND fixVersion = "{selected_fix_version}"'
            issues = get_issues(jql_query)
            data.extend([fetch_issue_data(issue) for issue in issues])
    return pd.DataFrame(data)

def display_insight(insight, df):
    st.subheader(insight)
    if insight == 'Issue Distribution by Type':
        issue_type_count = df['Type'].value_counts()
        fig = go.Figure(data=[go.Bar(x=issue_type_count.index, y=issue_type_count.values, orientation='h')])
        fig.update_layout(title='Issue Distribution by Type', yaxis_title='Issue Type', xaxis_title='Count', template='plotly_dark')
        fig.update_traces(marker=dict(color=colors))
        st.plotly_chart(fig)
    elif insight == 'Issue Status Distribution':
        status_count = df['Status'].value_counts()
        fig = go.Figure(data=[go.Bar(x=status_count.values, y=status_count.index, orientation='h')])
        fig.update_layout(title='Issue Status Distribution', yaxis_title='Issue Status', xaxis_title='Count', template='plotly_dark')
        fig.update_traces(marker=dict(color=colors))
        st.plotly_chart(fig)
    elif insight == 'Fix Version Status':
        fix_version_count = df['Fix Version'].value_counts()
        fig = go.Figure(data=[go.Bar(x=fix_version_count.values, y=fix_version_count.index, orientation='h')])
        fig.update_layout(title='Fix Version Status', yaxis_title='Fix Version', xaxis_title='Count', template='plotly_dark')
        fig.update_traces(marker=dict(color=colors))
        st.plotly_chart(fig)
    elif insight == 'Project-wise Issue Count':
        project_count = df['Project'].value_counts()
        fig = go.Figure(data=[go.Bar(x=project_count.values, y=project_count.index, orientation='h')])
        fig.update_layout(title='Project-wise Issue Count', yaxis_title='Project', xaxis_title='Count', template='plotly_dark')
        fig.update_traces(marker=dict(color=colors))
        st.plotly_chart(fig)
    elif insight == 'Issue Distribution by CAT Scope':
        cat_scope_count = df['CAT Scope'].value_counts()
        fig = go.Figure(data=[go.Bar(x=cat_scope_count.values, y=cat_scope_count.index, orientation='h')])
        fig.update_layout(title='Issue Distribution by CAT Scope', yaxis_title='CAT Scope', xaxis_title='Count', template='plotly_dark')
        fig.update_traces(marker=dict(color=colors))
        st.plotly_chart(fig)
    elif insight == 'Issue Distribution by IT Portal / SR / CR':
        it_portal_count = df['IT Portal / SR / CR'].value_counts()
        fig = go.Figure(data=[go.Bar(x=it_portal_count.values, y=it_portal_count.index, orientation='h')])
        fig.update_layout(title='Issue Distribution by IT Portal / SR / CR', yaxis_title='IT Portal / SR / CR', xaxis_title='Count', template='plotly_dark')
        fig.update_traces(marker=dict(color=colors))
        st.plotly_chart(fig)

def main():
    st.set_page_config(
        page_title="Dashboard",
        page_icon=":traffic_light:",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    projects = get_projects()
    if not projects:
        st.error("Error fetching projects.")
        return

    selected_project_keys = st.sidebar.multiselect("Select Project", options=list(projects.keys()))
    if not selected_project_keys:
        st.warning("Please select at least one project.")
        return

    fix_versions = []
    for selected_project_key in selected_project_keys:
        fix_versions += get_fix_versions(selected_project_key)

    selected_fix_versions = st.sidebar.multiselect("Select Fix Versions", options=list(set(fix_versions)))
    if not selected_fix_versions:
        st.warning("Please select at least one fix version.")
        return

    insights = [
        'Issue Distribution by Type', 
        'Issue Status Distribution', 
        'Fix Version Status', 
        'Project-wise Issue Count', 
        'Issue Distribution by CAT Scope', 
        'Issue Distribution by IT Portal / SR / CR'
    ]
    selected_insights = st.sidebar.multiselect("Select Insights", options=insights, default=['Issue Distribution by Type'])

    for selected_fix_version in selected_fix_versions:
        df = process_issues([selected_fix_version], selected_project_keys)
        if df.empty:
            st.warning(f"No data found for the selected project(s): {', '.join([projects[key] for key in selected_project_keys])} and fix version '{selected_fix_version}'.")
            continue

        df.index = range(1, len(df) + 1)  # Start row number from 1

        st.markdown('---')  # Add a horizontal line

        # Display Projects selected and Fix Version selected
        st.write("# Dashboard")  # Title moved to top left
        st.markdown(
            f'<div style="display: flex; flex-wrap: wrap; gap: 10px;">'
            f'<div><p style="color:black;"><b>Projects selected:</b> {", ".join([projects[key] for key in selected_project_keys])}</p></div>'
            f'<div><p style="color:black;"><b>Fix Version selected:</b> {selected_fix_versions}</p></div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # Display KPI Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total issue count", df.shape[0])
        
        if 'Type' in df.columns:  # Check if 'Type' column exists in the DataFrame
            col2.metric("Total Stories", df[df['Type'] == 'Story'].shape[0])
            col3.metric("Total Defects", df[df['Type'] == 'Defect'].shape[0])
            col4.metric("Total Epics", df[df['Type'] == 'Epic'].shape[0])
        else:
            col2.warning("No data available")
            col3.warning("No data available")
            col4.warning("No data available")

        # Display Dataframe
        st.subheader("Data Summary:")
        st.dataframe(df, width=700)  # Adjusted width to fit container in a column

        # Display Insights
        st.subheader("Insights:")
        insights_row = [selected_insights[i:i+2] for i in range(0, len(selected_insights), 2)]  # Split insights into rows of 2
        for insights_pair in insights_row:
            cols = st.columns(len(insights_pair))
            for col, insight in zip(cols, insights_pair):
                display_insight(insight, df)

if __name__ == "__main__":
    main()
