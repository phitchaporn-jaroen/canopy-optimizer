import streamlit as st
import numpy as np
import plotly.graph_objects as go
from shapely.geometry import Polygon

# --- 1. UI/UX CONFIGURATION & RESPONSIVE CSS ---
st.set_page_config(page_title="Canopy Optimizer", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    [data-testid="stMetric"] {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px;
    }
    .custom-card {
        background-color: #EFF6FF;
        border-left: 5px solid #3B82F6;
        border-radius: 6px;
        padding: 12px;
        margin: 15px 0;
    }
    html, body, [class*="css"] {
        font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("☀️ Canopy Shade Optimizer")
st.caption("ระบบคำนวณและจำลองระดับผ้าใบอัจฉริยะเพื่อร่มเงาสูงสุด")

# --- 2. INPUT PARAMETERS (SIDEBAR) ---
st.sidebar.header("📐 ตั้งค่าโครงสร้าง")
# ปรับค่าเริ่มต้น (value) เป็น 1.0 ตามต้องการ
W = st.sidebar.number_input("ความกว้าง W (เมตร)", min_value=0.1, value=1.0, step=0.1)
L = st.sidebar.number_input("ความยาว L (เมตร)", min_value=0.1, value=1.0, step=0.1)
H_start = st.sidebar.number_input("ความสูงเสา H (เมตร)", min_value=0.1, value=1.0, step=0.1)
building_ori = st.sidebar.slider("ทิศโครงสร้าง (องศาจากทิศ N)", 0, 360, 0, step=15)

st.sidebar.write("---")
st.sidebar.header("⏰ เวลาจำลอง")
hour = st.sidebar.slider("เวลา (น.)", 6, 18, 10, step=1)

build_rad = np.radians(building_ori)

# --- 3. CORE MATHEMATICS & OPTIMIZATION ---
def get_sun_pos(h):
    alt = 90 - abs(12 - h) * 12
    az = 90 + (h - 6) * 15
    return max(5, alt), az

alt_deg, az_deg = get_sun_pos(hour)
alt_rad, az_rad = np.radians(alt_deg), np.radians(az_deg)
sun_vec = np.array([np.cos(alt_rad)*np.sin(az_rad), np.cos(alt_rad)*np.cos(az_rad), -np.sin(alt_rad)])

def rotate_point(x, y, angle):
    return x * np.cos(angle) - y * np.sin(angle), x * np.sin(angle) + y * np.cos(angle)

base_coords = [
    rotate_point(-W/2, -L/2, build_rad),
    rotate_point(W/2, -L/2, build_rad),
    rotate_point(W/2, L/2, build_rad),
    rotate_point(-W/2, L/2, build_rad)
]
poly_canopy_base = Polygon(base_coords)
area_base = poly_canopy_base.area

rope_diffs = [(bc[0] * np.sin(az_rad) + bc[1] * np.cos(az_rad)) for bc in base_coords]
max_d, min_d = max(rope_diffs), min(rope_diffs)
range_d = max_d - min_d if max_d != min_d else 1.0
reductions_m = [((max_d - r) / range_d) * H_start * np.cos(alt_rad) for r in rope_diffs]
reductions_cm = [r * 100 for r in reductions_m]

roof_coords_opt = [np.array([base_coords[i][0], base_coords[i][1], H_start - reductions_m[i]]) for i in range(4)]

def get_shadow_analysis(roof_pts):
    shadow_pts = []
    for rp in roof_pts:
        t = -rp[2] / sun_vec[2]
        shadow_pts.append((rp[0] + t*sun_vec[0], rp[1] + t*sun_vec[1]))
    poly_shadow = Polygon(shadow_pts)
    intersect = poly_canopy_base.intersection(poly_shadow)
    return intersect, intersect.area if not intersect.is_empty else 0.0

shadow_poly_flat, area_flat = get_shadow_analysis([np.array([base_coords[i][0], base_coords[i][1], H_start]) for i in range(4)])
shadow_poly_opt, area_opt = get_shadow_analysis(roof_coords_opt)

percent_opt = (area_opt / area_base) * 100
gain_area = area_opt - area_flat
gain_percent = percent_opt - (area_flat / area_base * 100)

normal_vec = np.cross(roof_coords_opt[1] - roof_coords_opt[0], roof_coords_opt[3] - roof_coords_opt[0])
normal_vec /= np.linalg.norm(normal_vec)
roof_tilt = np.degrees(np.arccos(normal_vec[2]))
roof_azimuth = (np.degrees(np.arctan2(normal_vec[0], normal_vec[1])) + 360) % 360

def get_direction_abbr(azimuth):
    if (azimuth >= 337.5) or (azimuth < 22.5): return "N"
    elif azimuth < 67.5: return "NE"
    elif azimuth < 112.5: return "E"
    elif azimuth < 157.5: return "SE"
    elif azimuth < 202.5: return "S"
    elif azimuth < 247.5: return "SW"
    elif azimuth < 292.5: return "W"
    else: return "NW"

# --- 4. SUMMARY METRICS ---
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.metric(label="🕒 เวลาจำลอง", value=f"{hour}:00 น.", delta=f"Alt {alt_deg:.1f}° | Az {az_deg:.1f}° ({get_direction_abbr(az_deg)})", delta_color="off")
with col_m2:
    st.metric(label="🏠 มุมเอียงผ้าใบ", value=f"{roof_tilt:.1f}°", delta=f"ทิศทางลาดเอียง: {get_direction_abbr(roof_azimuth)}", delta_color="off")
with col_m3:
    st.metric(label="👥 ประสิทธิภาพร่มเงาใต้หลังคา", value=f"{percent_opt:.1f} %", delta=f"พื้นที่เงา: {area_opt:.1f} ตร.ม.")

st.write("---")

# --- 5. VISUALIZATION ---
col_chart1, col_chart2 = st.columns([1, 1])

with col_chart1:
    st.subheader("📋 ผังหน้างานจริง (Site Blueprint)")
    
    fig_site = go.Figure()
    cx = [base_coords[0][0], base_coords[1][0], base_coords[2][0], base_coords[3][0], base_coords[0][0]]
    cy = [base_coords[0][1], base_coords[1][1], base_coords[2][1], base_coords[3][1], base_coords[0][1]]
    
    fig_site.add_trace(go.Scatter(x=cx, y=cy, mode="lines", line=dict(color="#1E293B", width=3, dash="dash"), showlegend=False))
    
    if not shadow_poly_opt.is_empty:
        sx, sy = shadow_poly_opt.exterior.xy
        fig_site.add_trace(go.Scatter(x=list(sx), y=list(sy), fill="toself", fillcolor="rgba(148, 163, 184, 0.5)", line=dict(color="#94A3B8", width=1), name="Shade"))
    
    fig_site.add_trace(go.Scatter(x=[c[0] for c in base_coords], y=[c[1] for c in base_coords], mode="markers", marker=dict(color="blue", size=18), showlegend=False))
    
    labels = ["เสา 1", "เสา 2", "เสา 3", "เสา 4"]
    offsets = [(-10, -25), (10, -25), (10, 25), (-10, 25)]
    for i in range(4):
        fig_site.add_annotation(
            x=base_coords[i][0], y=base_coords[i][1],
            text=f"<b>{labels[i]}</b><br>ลด <b>{reductions_cm[i]:.1f} ซม.</b>",
            showarrow=False, xshift=offsets[i][0], yshift=offsets[i][1],
            font=dict(color="#1E293B", size=14)
        )
    
    fig_site.add_annotation(x=0, y=max(cy)*1.35, text="<b>⬆️ N</b>", showarrow=False, font=dict(color="#EF4444", size=16))
    
    fig_site.update_layout(
        height=450, plot_bgcolor='white', margin=dict(l=10, r=10, b=10, t=10),
        xaxis=dict(visible=False, fixedrange=True),
        yaxis=dict(visible=False, scaleanchor="x", scaleratio=1, fixedrange=True)
    )
    st.plotly_chart(fig_site, use_container_width=True)

with col_chart2:
    st.subheader("📦 โมเดล 3 มิติ (3D Simulation)")
    fig_3d = go.Figure()
    for i in range(4):
        fig_3d.add_trace(go.Scatter3d(x=[base_coords[i][0], base_coords[i][0]], y=[base_coords[i][1], base_coords[i][1]], z=[0, H_start], mode='lines', line=dict(color='#334155', width=3), showlegend=False))
    
    rx = [c[0] for c in roof_coords_opt] + [roof_coords_opt[0][0]]
    ry = [c[1] for c in roof_coords_opt] + [roof_coords_opt[0][1]]
    rz = [c[2] for c in roof_coords_opt] + [roof_coords_opt[0][2]]
    fig_3d.add_trace(go.Mesh3d(x=rx, y=ry, z=rz, color='#06B6D4', opacity=0.5))
    
    if not shadow_poly_opt.is_empty:
        fig_3d.add_trace(go.Mesh3d(x=list(sx), y=list(sy), z=[0]*len(sx), color='#475569', opacity=0.6))
        
    fig_3d.update_layout(
        height=450, margin=dict(l=0, r=0, b=0, t=0),
        scene=dict(
            xaxis=dict(title="", showticklabels=False),
            yaxis=dict(title="", showticklabels=False),
            zaxis=dict(range=[0, H_start+0.5], title="Height (m)")
        )
    )
    st.plotly_chart(fig_3d, use_container_width=True)

# --- 6. DATA TABLES ---
st.write("---")
st.markdown('<div class="custom-card"><p class="highlight-title">🛠️ คู่มือระยะผูกเชือกติดตั้งหน้างานจริง</p></div>', unsafe_allow_html=True)

st.table({
    "เสาโครงสร้าง": ["เสา 1 (หน้า-ซ้าย)", "เสา 2 (หน้า-ขวา)", "เสา 3 (หลัง-ขวา)", "เสา 4 (หลัง-ซ้าย)"],
    "🎯 ระยะลดจากยอดเสา": [f"ลดลง {r:.1f} ซม." if r >= 0.5 else "0 ซม. (ยอดเสาเดิม)" for r in reductions_cm],
    "ความสูงผ้าใบจริง": [f"{roof_coords_opt[i][2]:.2f} เมตร" for i in range(4)]
})

with st.expander("📊 ดูตารางวิเคราะห์ดัชนีประสิทธิภาพเชิงลึก"):
    st.table({
        "ตัวชี้วัด (Metrics)": ["พื้นที่ร่มเงาสุทธิ", "อัตราครอบคลุม", "มุมลาดเอียงผ้าใบ"],
        "❌ แบบราบปกติ": [f"{area_flat:.1f} ตร.ม.", f"{(area_flat/area_base*100):.1f} %", "0.0°"],
        "✨ แบบปรับระดับ": [f"{area_opt:.1f} ตร.ม.", f"{percent_opt:.1f} %", f"{roof_tilt:.1f}°"],
        "📈 ผลต่างพัฒนา": [f"+ {gain_area:.1f} ตร.ม.", f"+ {gain_percent:.1f} %", f"เอียงไปทิศ {get_direction_abbr(roof_azimuth)}"]
    })
