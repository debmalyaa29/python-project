import streamlit as st
import requests

st.set_page_config(page_title="Report Issue", page_icon="📸")

API_URL = "http://127.0.0.1:5000"

st.title("📸 Report an Issue")

if "user" not in st.session_state:
    st.warning("Please login to report an issue.")
else:
    st.write("Help keep our city safe by reporting infrastructure issues here.")
    
    with st.form("report_form", clear_on_submit=True):
        title = st.text_input("Issue Title", placeholder="e.g. Broken pothole on Elm St")
        description = st.text_area("Description", placeholder="Describe the severity and location further")
        category = st.selectbox("Category", ["Pothole", "Manhole", "Flooding", "Other"])
        location_text = st.text_input("Precise Location", placeholder="e.g. 123 Elm St, near intersection")
        image_file = st.file_uploader("Upload Photo (Cloudinary)", type=["jpg", "jpeg", "png"])
        
        submitted = st.form_submit_button("Submit Report")
        
        if submitted:
            if not title or not description or not location_text:
                st.error("Please fill out all text fields.")
            else:
                with st.spinner("Submitting your report (this may take a bit if uploading an image)..."):
                    data = {
                        "user_id": st.session_state["user"]["id"],
                        "title": title,
                        "description": description,
                        "category": category,
                        "location_text": location_text
                    }
                    
                    files = {}
                    if image_file:
                        files = {"image": image_file}
                        
                    try:
                        res = requests.post(f"{API_URL}/issues", data=data, files=files)
                        if res.status_code == 201:
                            st.success("Report submitted successfully!")
                            st.balloons()
                        else:
                            st.error(res.json().get("error", "Failed to submit report"))
                    except requests.exceptions.ConnectionError:
                        st.error("Could not connect to backend API.")
