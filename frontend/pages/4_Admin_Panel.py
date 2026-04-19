import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Admin Panel", page_icon="🛠️")

API_URL = "http://127.0.0.1:5000"

st.title("🛠️ Admin Panel")

if "user" not in st.session_state or st.session_state["user"]["role"] != "admin":
    st.error("Access Denied. You must be logged in as an administrator.")
else:
    st.write("Manage all reported issues here.")
    
    try:
        res = requests.get(f"{API_URL}/issues")
        if res.status_code == 200:
            issues = res.json()
            
            if not issues:
                st.info("No issues to manage.")
            else:
                # Convert to dataframe for nicer display
                df = pd.DataFrame(issues)
                df = df[['id', 'title', 'category', 'status', 'votes', 'location_text', 'created_at']]
                df['created_at'] = df['created_at'].str[:10] # format date
                
                # We can't edit dataframes easily with complex logic in default Streamlit table
                # So we render individual rows and select boxes to update status
                
                st.subheader("Update Issue Status")
                
                for issue in issues:
                    with st.expander(f"ID: {issue['id']} | {issue['title']} - Current Status: {issue['status']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            new_status = st.selectbox(
                                "Set Status", 
                                ["Reported", "Under Review", "In Progress", "Fixed"], 
                                index=["Reported", "Under Review", "In Progress", "Fixed"].index(issue['status']),
                                key=f"status_select_{issue['id']}"
                            )
                        
                        with col2:
                            st.write("") # spacer
                            st.write("") # spacer
                            if st.button("Update Status", key=f"update_btn_{issue['id']}"):
                                admin_token = st.session_state["token"]
                                headers = {"Authorization": admin_token}
                                payload = {"status": new_status}
                                
                                try:
                                    update_res = requests.put(f"{API_URL}/issues/{issue['id']}/status", json=payload, headers=headers)
                                    if update_res.status_code == 200:
                                        st.success(f"Issue {issue['id']} status updated to {new_status}")
                                        st.rerun()
                                    else:
                                        st.error("Failed to update status." + update_res.text)
                                except requests.exceptions.ConnectionError:
                                    st.error("Could not connect to API.")
                                    
                        st.write(f"**Description:** {issue['description']}")
                        st.write(f"**Location:** {issue['location_text']}")
                        if issue.get('image_url'):
                            st.image(issue['image_url'], width=300)

    except requests.exceptions.ConnectionError:
        st.error("Could not connect to backend API to fetch issues.")
