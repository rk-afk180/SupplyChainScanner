import streamlit as st
import requests
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="RepoShield | Stealth Audit", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    
    [data-testid="stAppViewContainer"] {
        background-color: #020205;
        background-image: 
            linear-gradient(rgba(188, 19, 254, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(188, 19, 254, 0.05) 1px, transparent 1px);
        background-size: 30px 30px;
        color: #d1d1e0;
        font-family: 'JetBrains Mono', monospace;
    }

    #matrix-canvas {
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        z-index: -1;
        opacity: 0.15;
    }

    .hero-title {
        font-size: 85px;
        font-weight: 700;
        background: linear-gradient(to right, #00fff2, #bc13fe, #00fff2);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-top: 10px;
        letter-spacing: -4px;
        animation: shine 4s linear infinite;
        filter: drop-shadow(0 0 15px rgba(188, 19, 254, 0.6));
    }

    @keyframes shine {
        to { background-position: 200% center; }
    }

    .stTextInput input {
        background: rgba(10, 10, 21, 0.8) !important;
        border: 1px solid #bc13fe !important;
        color: #00fff2 !important;
        height: 55px;
        border-radius: 8px 0 0 8px !important;
        box-shadow: inset 0 0 10px rgba(188, 19, 254, 0.2);
    }
    
    .stButton>button {
        background: linear-gradient(90deg, #bc13fe, #7a10f7) !important;
        color: #fff !important;
        height: 55px;
        width: 100%;
        font-weight: 700 !important;
        border-radius: 0 8px 8px 0 !important;
        border: none !important;
        transition: 0.3s all;
    }
    
    .stButton>button:hover {
        box-shadow: 0 0 30px rgba(188, 19, 254, 0.8);
        transform: translateY(-2px);
    }

    .status-card {
        background: rgba(15, 15, 30, 0.95);
        border: 1px solid rgba(188, 19, 254, 0.3);
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
    }

    [data-testid="stMetricValue"] { color: #00fff2 !important; text-shadow: 0 0 10px rgba(0, 255, 242, 0.5); }
    </style>
""", unsafe_allow_html=True)

st.components.v1.html("""
<canvas id="matrix-canvas"></canvas>
<script>
const canvas = document.getElementById('matrix-canvas');
const ctx = canvas.getContext('2d');

canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

const charSet = "01010101ABCDEFVULN";
const fontSize = 16;
const columns = canvas.width / fontSize;
const drops = [];

for (let x = 0; x < columns; x++) {
    drops[x] = Math.random() * -100; 
}

function draw() {
    ctx.fillStyle = "rgba(2, 2, 5, 0.15)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for (let i = 0; i < drops.length; i++) {
        const text = charSet[Math.floor(Math.random() * charSet.length)];
        const opacity = Math.random() > 0.9 ? 1 : 0.6;
        ctx.fillStyle = `rgba(188, 19, 254, ${opacity})`; 
        
        ctx.font = fontSize + "px monospace";
        ctx.fillText(text, i * fontSize, drops[i] * fontSize);

        if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
            drops[i] = 0;
        }

        drops[i] += 0.8;
    }
}

window.addEventListener('resize', () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
});

setInterval(draw, 35);
</script>
""", height=0)

st.markdown('<h1 class="hero-title">REPOSHIELD</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align:center; color:#4a4a6a; letter-spacing:10px; margin-top:-20px; font-weight:bold;">VULNERABILITY SCANNING PROTOCOL V3.6</p>', unsafe_allow_html=True)

st.write("##")
c1, c2 = st.columns([4, 1])
with c1:
    url = st.text_input("", placeholder="TERMINAL PROMPT > ENTER TARGET REPOSITORY URL...", label_visibility="collapsed")
with c2:
    run = st.button("INITIATE SCAN")

if run:
    if not url:
        st.error("X_ERROR: TARGET_NULL_EXCEPTION")
    else:
        log_area = st.empty()
        log_text = ""
        steps = [
            "Establishing Encrypted Handshake...", 
            "Fetching Manifest...", 
            "Deep Parsing Dependency Tree...", 
            "Cross-referencing OSV Database...", 
            "Mapping Cyber Risk Matrix..."
        ]
        
        for s in steps:
            log_text += f"{s}<br>"
            log_area.markdown(f'''
                <div style="background:rgba(5, 5, 16, 0.85); color:#00fff2; padding:15px; border-left:3px solid #bc13fe; 
                font-family:'JetBrains Mono', monospace; font-size:13px; border-radius:4px; box-shadow: 0 5px 15px rgba(0,0,0,0.3);">
                    {log_text}
                </div>
            ''', unsafe_allow_html=True)
            time.sleep(0.4)

        try:
            res = requests.post("http://127.0.0.1:5001/scan", json={"repo_url": url}, timeout=60)
            data = res.json()
            
            if data.get("status") == "success":
                vulns = data.get("vulnerable_libraries", [])
                total = data.get("total_scanned", 1)
                found = data.get("vulnerabilities_found", 0)
                score = 100 - (found/total*100)

                st.write("##")
                col_sum, col_met = st.columns([2, 1])
                with col_sum:
                    status_c = '#00fff2' if found==0 else '#ff2a6d'
                    header_text = 'SYSTEM_SECURE' if found==0 else 'BREACH_DETECTED'
                    st.markdown(f"""
                    <div class="status-card" style="border-left: 5px solid {status_c};">
                        <h2 style="margin:0; color:{status_c}; letter-spacing:2px;">
                            {header_text}
                        </h2>
                        <p style="color:#6a6a8a; font-size:14px; margin-top:5px;">
                            Core Integrity: {score:.1f}% | Total Analysis Nodes: {total}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                with col_met:
                    st.metric("HEALTH", f"{score:.1f}%")
                    st.metric("THREATS", found)

                st.divider()

                g1, g2, g3 = st.columns([1, 1.4, 0.4])
                
                with g1:
                    fig_p = px.pie(values=[total-found, found], names=['Secure', 'Vulnerable'], hole=0.8, 
                                 color_discrete_sequence=['#00fff2', '#ff2a6d'])
                    fig_p.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(t=0,b=0,l=0,r=0))
                    st.plotly_chart(fig_p, use_container_width=True)

                with g2:
                    if found > 0:
                        libs = [v['library_name'] for v in vulns]
                        vals = [[len(v['specific_issues'])] for v in vulns]
                        
                        fig_h = go.Figure(data=go.Heatmap(
                            z=vals, x=['THREAT_LEVEL'], y=libs,
                            ygap=20, 
                            colorscale=[[0, '#00fff2'], [0.5, '#bc13fe'], [1, '#ff2a6d']],
                            showscale=False
                        ))
                        
                        fig_h.update_layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            height=300,
                            xaxis=dict(visible=False),
                            yaxis=dict(showgrid=True, gridcolor='rgba(188,19,254,0.1)', griddash='dot', color="#bc13fe"),
                            margin=dict(t=10,b=10,l=0,r=0)
                        )
                        st.plotly_chart(fig_h, use_container_width=True)
                    else:
                        st.markdown("<div style='height:300px; display:flex; align-items:center; justify-content:center; color:#00fff2; border:1px dashed #2a2a4a; border-radius:12px; background:rgba(0,255,242,0.02);'>[ GRID_STABLE_NO_RISK_FOUND ]</div>", unsafe_allow_html=True)

                with g3:
                    st.markdown("<p style='font-size:10px; color:#4a4a6a; text-align:center;'>RISK_LEGEND</p>", unsafe_allow_html=True)
                    for label, color in [("CRITICAL", "#ff2a6d"), ("STABLE", "#bc13fe"), ("SECURE", "#00fff2")]:
                        st.markdown(f'<div style="background:{color}; color:#000; padding:6px; font-size:10px; font-weight:700; text-align:center; border-radius:4px; margin-bottom:8px; box-shadow:0 0 10px {color}44;">{label}</div>', unsafe_allow_html=True)

                st.write("##")
                st.markdown("### NEURAL_DATABASE_LOGS")
                for lib in vulns:
                    with st.expander(f"{lib['library_name']} — Version: {lib['current_version']}"):
                        for issue in lib['specific_issues']:
                            st.markdown(f"<span style='color:#ff2a6d'>**VULN_ID:**</span> `{issue['id']}`", unsafe_allow_html=True)
                            st.write(f"**Context:** {issue['summary']}")
                            st.success(f"**Remediation:** {issue['solution']}")
                            
                            pm = "npm i" if "package" in url else "pip install --upgrade"
                            st.code(f"{pm} {lib['library_name']}@latest", language="bash")
            else:
                st.error("CONNECTION_FAILED: API_OFFLINE_OR_INVALID_REPO")
        except Exception as e:
            st.error(f"FATAL_ERROR: {e}")

st.markdown("<br><center><p style='color:#2a2a4a; font-size:10px;'>REPOSHIELD V3.6 | ENCRYPTED MATRIX ENGINE | STEALTH_MODE: ON</p></center>", unsafe_allow_html=True)
