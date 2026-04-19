import streamlit as st
import requests
import pandas as pd
import datetime

st.set_page_config(page_title="CivicFix", page_icon="🏙️", layout="wide")

# Theme / Aesthetics settings via CSS
st.markdown("""
<style>
    .report-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .status-badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 15px;
        font-weight: bold;
        color: white;
    }
    .status-Reported { background-color: #ffc107; color: black !important; }
    .status-Under_Review { background-color: #17a2b8; }
    .status-In_Progress { background-color: #007bff; }
    .status-Fixed { background-color: #28a745; }
</style>
""", unsafe_allow_html=True)

API_URL = "http://127.0.0.1:5000"

st.title("🏙️ CivicFix - Public Dashboard")
st.write("Welcome to CivicFix! Together we can fix our city. See reported issues below or report a new one.")

def fetch_stats():
    try:
        response = requests.get(f"{API_URL}/issues/dashboard/stats")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        pass
    return {"total_reported": 0, "fixed_issues": 0, "pending_issues": 0}

def fetch_issues():
    try:
        response = requests.get(f"{API_URL}/issues")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        pass
    return []

stats = fetch_stats()
col1, col2, col3 = st.columns(3)
col1.metric("Total Reported", stats['total_reported'])
col2.metric("Pending Issues", stats['pending_issues'])
col3.metric("Fixed Issues", stats['fixed_issues'])

st.divider()

st.subheader("📍 Recent Issues")

issues = fetch_issues()

if not issues:
    st.info("No issues reported yet. Be the first to report!")
else:
    # Filter options
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        status_filter = st.selectbox("Filter by Status", ["All", "Reported", "Under Review", "In Progress", "Fixed"])
    with filter_col2:
        category_filter = st.selectbox("Filter by Category", ["All", "Pothole", "Manhole", "Flooding", "Other"])

    filtered_issues = []
    for issue in issues:
        if status_filter != "All" and issue['status'] != status_filter: continue
        if category_filter != "All" and issue['category'] != category_filter: continue
        filtered_issues.append(issue)

    if filtered_issues:
        for issue in filtered_issues:
            status_class = f"status-badge status-{issue['status'].replace(' ', '_')}"
            
            with st.container():
                st.markdown(f'<div class="report-card">', unsafe_allow_html=True)
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    if issue.get('image_url'):
                        st.image(issue['image_url'], use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/300x200?text=No+Image", use_container_width=True)
                
                with col2:
                    st.markdown(f"### {issue['title']}")
                    st.markdown(f"<span class='{status_class}'>{issue['status']}</span> <span style='margin-left: 10px; color: #666;'>{issue['category']}</span>", unsafe_allow_html=True)
                    st.write(f"**Location:** {issue['location_text']}")
                    st.write(issue['description'])
                    
                    st.caption(f"Reported by {issue['citizen_username']} on {issue['created_at'][:10]} | ❤️ {issue['votes']} Votes")
                
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.write("No issues match the selected filters.")
