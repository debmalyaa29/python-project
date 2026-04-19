import streamlit as st
import requests

st.set_page_config(page_title="My Issues", page_icon="📋")

API_URL = "http://127.0.0.1:5000"

st.title("📋 My Reported Issues")

st.markdown("""
<style>
    .report-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .status-badge { display: inline-block; padding: 5px 10px; border-radius: 15px; font-weight: bold; color: white; }
    .status-Reported { background-color: #ffc107; color: black !important; }
    .status-Under_Review { background-color: #17a2b8; }
    .status-In_Progress { background-color: #007bff; }
    .status-Fixed { background-color: #28a745; }
</style>
""", unsafe_allow_html=True)

if "user" not in st.session_state:
    st.warning("Please login to see your issues.")
else:
    user_id = st.session_state["user"]["id"]
    
    try:
        res = requests.get(f"{API_URL}/issues?user_id={user_id}")
        if res.status_code == 200:
            issues = res.json()
            if not issues:
                st.info("You haven't reported any issues yet.")
            else:
                for issue in issues:
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
                            st.caption(f"Reported on {issue['created_at'][:10]} | ❤️ {issue['votes']} Votes")
                        st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.error("Failed to fetch issues.")
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to backend API.")

st.divider()

st.title("🗳️ Upvote Others' Issues")
st.write("Browse all issues and upvote the ones you want fixed first!")

if st.button("Refresh All Issues"):
    st.rerun()

try:
    res = requests.get(f"{API_URL}/issues")
    if res.status_code == 200:
        all_issues = res.json()
        for issue in all_issues:
            if issue['citizen_id'] == user_id: continue # Don't show own issues for voting
            
            with st.expander(f"{issue['title']} - ❤️ {issue['votes']}"):
                st.write(f"**Category:** {issue['category']} | **Status:** {issue['status']}")
                st.write(f"**Description:** {issue['description']}")
                st.write(f"**Location:** {issue['location_text']}")
                
                # Check if current user voted
                if st.button(f"Toggle Vote ❤️", key=f"vote_btn_{issue['id']}"):
                    try:
                        vote_res = requests.post(f"{API_URL}/issues/{issue['id']}/vote", json={"user_id": user_id})
                        if vote_res.status_code in [200, 201]:
                            st.success("Vote registered/removed!")
                            st.rerun()
                        else:
                            st.error("Failed to register vote.")
                    except requests.exceptions.ConnectionError:
                        st.error("Could not connect to API.")
except requests.exceptions.ConnectionError:
    st.error("Could not fetch issues.")
