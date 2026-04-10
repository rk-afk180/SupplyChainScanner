import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Supply Chain Scanner",layout="wide")

st.markdown("""
<style>
.main { background : 0f2027; color: white; }
.card { background : rgba(255,255,255,0.05);border-radius: 10px; padding: 15px;margin-bottom: 10px;)
</style>
""",unsafe_allow_html=True)

st.title("Supply Chain Vulnerability Scanner)

repo_url=st.txt_input("Enter you GitHub Repository URL","")

if st.button("Start Scan"):
  if not repo_url.strip():
    st.warning("please enter a GitHub repository  URL first.")
  else:
    with st.spinner("Analyzing dependencies")
        try:
          response = requests.post("http://127.0.0.1:5001/scan", json={"repo_url": repo_url}
             if response.status_code == 200:
                    results = response.json()
             if results.get("status") == "success":
                        st.success("Analysis Complete")

                        m1, m2 = st.columns(2)
                        m1.metric("Total Libraries Scanned", results.get("total_scanned", 0))
                        
                        vuln_count = results.get("vulnerabilities_found", 0)
                        m2.metric("Vulnerable Libraries", vuln_count, 
                                  delta="Secure" if vuln_count == 0 else "Action Required",
                                  delta_color="normal" if vuln_count == 0 else "inverse")

                        vuln_libs = results.get("vulnerable_libraries", [])
                        
                        if not vuln_libs:
                            st.balloons()
                            st.info("Good news! No vulnerabilities detected in this project.")
                        else:
                            for lib in vuln_libs:
                                with st.expander(f"{lib['library_name']} (v{lib['current_version']}) - {lib['issue_count']} issues"):
                                    df = pd.DataFrame(lib["specific_issues"])
                                    
                                    df.rename(columns={
                                        "id": "Vulnerability ID",
                                        "summary": "Issue Summary",
                                        "solution": "Recommended Solution"
                                    }, inplace=True)
                                    
                                    df.rename(columns={
                                        "id": "CVE ID",
                                        "summary": "Description",
                                        "fixed_in": "Safe Version"
                                    }, inplace=True)
                                    
                                    st.dataframe(
                                        df, 
                                        use_container_width=True, 
                                        hide_index=True,
                                        column_config={
                                            "Recommended Solution": st.column_config.LinkColumn(
                                                "Recommended Solution",
                                                help="Click to view the official security report"
                                            )
                                        }
                                    )
                    else:
                        st.error(results.get("error", "An unknown error occurred."))
                else:
                    st.error(f"Server Error: {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to backend. Is your Flask app running on port 5000?")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")



