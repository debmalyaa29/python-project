import streamlit as st
import requests

st.set_page_config(page_title="Login / Register", page_icon="🔐")

API_URL = "http://127.0.0.1:5000"

st.title("🔐 Login / Register")

if "user" in st.session_state:
    st.success(f"Already logged in as {st.session_state['user']['username']} ({st.session_state['user']['role']})")
    if st.button("Logout"):
        del st.session_state["user"]
        del st.session_state["token"]
        st.rerun()
else:
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            l_username = st.text_input("Username")
            l_password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                payload = {"username": l_username, "password": l_password}
                try:
                    res = requests.post(f"{API_URL}/auth/login", json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state["user"] = data["user"]
                        st.session_state["token"] = data["token"]
                        st.success("Logged in successfully!")
                        st.rerun()
                    else:
                        st.error(res.json().get("error", "Login failed"))
                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to backend API.")

    with tab2:
        st.subheader("Register (Citizen or Admin)")
        with st.form("register_form"):
            r_username = st.text_input("Username")
            r_password = st.text_input("Password", type="password")
            r_role = st.selectbox("Role", ["citizen", "admin"])
            submitted = st.form_submit_button("Register")

            if submitted:
                payload = {"username": r_username, "password": r_password, "role": r_role}
                try:
                    res = requests.post(f"{API_URL}/auth/register", json=payload)
                    if res.status_code == 201:
                        st.success("Registered successfully! Please login.")
                    else:
                        st.error(res.json().get("error", "Registration failed"))
                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to backend API.")
