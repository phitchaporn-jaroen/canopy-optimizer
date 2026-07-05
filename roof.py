import streamlit as st
import numpy as np
import plotly.graph_objects as go
from shapely.geometry import Polygon

# --- 1. CONFIG & STYLE ---
st.set_page_config(page_title="Canopy Optimizer", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetric"] { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; }
    .custom-card { background-color: #EFF6FF; border-left: 5px solid #3B82F6; border-radius: 6px; padding: 12px; margin: 15px 0; }
    html, body, [class*="css"] { font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

st.title("☀️ Canopy Shade Optimizer")
st.caption("ระบบคำนวณระดับผ้าใบอัจฉริยะ ปรับระดับเอียงรับแนวแสงแดดเพื่อร่มเงาสูงสุดตามหลักวิศวกรรม")

# --- 2. SIDEBAR: PARAMETERS ---
st.sidebar.header("📐 ตั้งค่ารูปทรงผ้าใบ")
shape_type = st.sidebar.selectbox("เลือกรูปทรงผ้าใบ", ["สี่เหลี่ยม", "สามเหลี่ยมด้านเท่า", "วงกลม"])

if shape_type == "สี่เหลี่ยม":
    W = st.sidebar.number_input("ความกว้าง W (เมตร)", min_value=0.1, value=1.0, step=0.1)
    L = st.sidebar.number_input("ความยาว L (เมตร)", min_value=0.1, value=1.0, step=0.1)
elif shape_type == "สามเหลี่ยมด้านเท่า":
    S = st.sidebar.number_input("ความยาวด้าน (เมตร)", min_value=0.1, value=1.0, step=0.1)
else: # วงกลม
    R = st.sidebar.number_input("รัศมี (เมตร)", min_value=0.1, value=1.0, step=0.1)

H_start = st.sidebar.number_input("ความสูงเสาเริ่มต้น H (เมตร)", min_value=0.1, value=1.0, step=0.1)
building_ori = st.sidebar.slider("ทิศโครงสร้าง (องศาจากทิศ N)", 0, 360, 0, step=15)

st.sidebar.header("📅 วันเวลาและพิกัดแดด")
month = st.sidebar.selectbox(
    "เลือกเดือนที่จำลอง", 
    ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"],
    index=6
)
hour = st.sidebar.slider("เวลาจำลอง (น.)", 6, 18, 8, step=1)

build_rad = np.radians(building_ori)

# --- 3. GEOMETRY GENERATION ---
def rotate_point(x, y, angle):
    return x * np.cos(angle) - y * np.sin(angle), x * np.sin(angle) + y * np.cos(angle)

base_coords = []
if shape_type == "สี่เหลี่ยม":
    # ลำดับเสาตามเข็มนาฬิกา: เสา 1(ซ้ายล่าง), เสา 4(ซ้ายบน), เสา 3(ขวาบน), เสา 2(ขวาล่าง) เพื่อให้แมปกับรูปภาพผังเดิมของคุณ
    pts = [(-W/2, -L/2), (W/2, -L/2), (W/2, L/2), (-W/2, L/2)]
    post_labels = ["เสา 1", "เสา 2", "เสา 3", "เสา 4"]
elif shape_type == "สามเหลี่ยมด้านเท่า":
    h = S * np.sqrt(3) / 2
    pts = [(0, 2*h/3), (-S/2, -h/3), (S/2, -h/3)]
    post_labels = ["เสา 1 (ยอด)", "เสา 2 (ซ้าย)", "เสา 3 (ขวา)"]
else: # วงกลม
    angles = np.linspace(0, 2*np.pi, 33)[:-1]
    pts = [(R * np.cos(a), R * np.sin(a)) for a in angles]
    post_indices = [8, 0, 24, 16] 
    post_labels = ["จุดเหนือ (N)", "จุดตะวันออก (E)", "จุดใต้ (S)", "จุดตะวันตก (W)"]

base_coords = [rotate_point(p[0], p[1], build_rad) for p in pts]
poly_canopy_base = Polygon(base_coords)
area_base = poly_canopy_base.area

# --- 4. SOLAR CALCULATIONS (ความแม่นยำสูงสากล) ---
def get_sun_pos_by_month(h, m_name):
    months_dict = {
        "มกราคม": 15, "กุมภาพันธ์": 46, "มีนาคม": 74, "เมษายน": 105, 
        "พฤษภาคม": 135, "มิถุนายน": 166, "กรกฎาคม": 196, "สิงหาคม": 227, 
        "กันยายน": 258, "ตุลาคม": 288, "พฤศจิกายน": 319, "ธันวาคม": 349
    }
    day_of_year = months_dict.get(m_name, 196)
    
    declination = 23.45 * np.sin(np.radians(360 / 365 * (day_of_year - 80)))
    latitude = 13.7 # ประเทศไทย
    
    hour_angle = (h - 12) * 15
    
    sin_alt = (np.sin(np.radians(latitude)) * np.sin(np.radians(declination)) + 
               np.cos(np.radians(latitude)) * np.cos(np.radians(declination)) * np.cos(np.radians(hour_angle)))
    alt = np.degrees(np.arcsin(sin_alt))
    alt = max(1.0, min(89.9, alt))
    
    cos_az = ((np.sin(np.radians(declination)) - np.sin(np.radians(latitude)) * np.sin(np.radians(alt))) / 
              (np.cos(np.radians(latitude)) * np.cos(np.radians(alt))))
    cos_az = max(-1.0, min(1.0, cos_az))
    az = np.degrees(np.arccos(cos_az))
    
    if hour > 12:
        az = 360 - az
        
    return alt, az

alt_deg, az_deg = get_sun_pos_by_month(hour, month)
alt_rad, az_rad = np.radians(alt_deg), np.radians(az_deg)

# เวกเตอร์ตำแหน่งดวงอาทิตย์ (ทิศสากล: แกน +Y คือทิศเหนือ, แกน +X คือทิศตะวันออก)
sun_x = np.sin(az_rad) * np.cos(alt_rad)
sun_y = np.cos(az_rad) * np.cos(alt_rad)
sun_z = np.sin(alt_rad)

# เวกเตอร์การทอดของแสง (ทอดสวนทางจากตัวดวงอาทิตย์ลงพื้นราบ)
sun_vec = np.array([-sun_x, -sun_y, -sun_z])

# มุกเอียงผ้าใบเพื่อให้ระนาบตั้งฉากรับเงาได้สมบูรณ์แบบที่สุด
optimal_tilt_deg = 90.0 - alt_deg 

# --- 5. FLAT SHADOW (ก่อนปรับระดับ) ---
shadow_pts_flat = []
for bc in base_coords:
    t = -H_start / sun_vec[2]
    shadow_pts_flat.append((bc[0] + t*sun_vec[0], bc[1] + t*sun_vec[1]))
poly_shadow_flat = Polygon(shadow_pts_flat)
area_total_shadow_flat = poly_shadow_flat.area
intersect_flat = poly_canopy_base.intersection(poly_shadow_flat)
area_opt_flat = intersect_flat.area if not intersect_flat.is_empty else 0.0
percent_flat = (area_opt_flat / area_base) * 100

# --- 6. OPTIMIZED SHADOW (ปรับปรุงตรรกะดึงเสารับแดดให้ถูกต้องตามหลักฟิสิกส์) ---
# คำนวณระยะห่างตามแนวโปรเจกชันของแสง
rope_diffs = [(bc[0] * sun_x + bc[1] * sun_y) for bc in base_coords]
max_d, min_d = max(rope_diffs), min(rope_diffs)
range_d = max_d - min_d if max_d != min_d else 1.0

# แก้ไขจุดนี้: เสาที่อยู่ใกล้ดวงอาทิตย์ที่สุด (ค่า r มากที่สุด) จะต้องถูก "ลดระดับลงต่ำสุด" เพื่อบังแดดเฉียง
# ส่วนเสาที่อยู่ไกลแดดที่สุด (ค่า r น้อยที่สุด) จะอยู่คงเดิมที่ความสูงเสาสูงสุด
reductions_m = [((r - min_d) / range_d) * H_start * np.cos(alt_rad) * 0.75 for r in rope_diffs] 
reductions_cm = [r * 100 for r in reductions_m]

roof_coords_opt = [np.array([base_coords[i][0], base_coords[i][1], H_start - reductions_m[i]]) for i in range(len(base_coords))]

# คำนวватьเงาของผ้าใบเอียงอัจฉริยะ
shadow_pts_full = []
for rp in roof_coords_opt:
    t = -rp[2] / sun_vec[2]
    shadow_pts_full.append((rp[0] + t*sun_vec[0], rp[1] + t*sun_vec[1]))
poly_shadow_full = Polygon(shadow_pts_full)
area_total_shadow_opt = poly_shadow_full.area

intersect_opt = poly_canopy_base.intersection(poly_shadow_full)
area_opt = intersect_opt.area if not intersect_opt.is_empty else 0.0
percent_opt = (area_opt / area_base) * 100

# --- 7. DISPLAY METRICS ---
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1: 
    st.metric(label=f"🕒 จำลองช่วง: {month}", value=f"{hour}:00 น.", delta=f"☀️ ทิศ:{az_deg:.1f}° | เงย:{alt_deg:.1f}°")
with col_m2: 
    st.metric(label="📐 รูปทรงผ้าใบหลังคา", value=shape_type, delta=f"พื้นที่: {area_base:.2f} ตร.ม.")
with col_m3: 
    st.metric(label="📐 มุมเอียงที่ดีที่สุด (Optimal)", value=f"{optimal_tilt_deg:.1f}°", delta="เอียงรับเงามากที่สุด")
with col_m4: 
    st.metric(label="👥 ประสิทธิภาพร่มเงาใต้หลังคา", value=f"{percent_opt:.1f} %", delta=f"เงารวมพื้น: {area_total_shadow_opt:.2f} ตร.ม.")

st.write("---")

# --- 8. VISUALIZATION ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📍 ผังหน้างาน (Site Blueprint)")
    fig_site = go.Figure()
    
    cx = [p[0] for p in base_coords] + [base_coords[0][0]]
    cy = [p[1] for p in base_coords] + [base_coords[0][1]]
    fig_site.add_trace(go.Scatter(x=cx, y=cy, mode="lines", line=dict(color="#1E293B", width=3, dash="dash"), showlegend=False))
    
    if not poly_shadow_full.is_empty:
        sfx, sfy = poly_shadow_full.exterior.xy
        fig_site.add_trace(go.Scatter(x=list(sfx), y=list(sfy), fill="toself", fillcolor="rgba(148, 163, 184, 0.4)", line=dict(color="rgba(148, 163, 184, 0.6)", width=1), name="เงารวมทั้งหมด"))

    if not intersect_opt.is_empty:
        six, siy = intersect_opt.exterior.xy
        fig_site.add_trace(go.Scatter(x=list(six), y=list(siy), fill="toself", fillcolor="rgba(30, 41, 59, 0.7)", line=dict(width=0), name="เงาใต้ชายคา"))

    if shape_type != "วงกลม":
        for i, label in enumerate(post_labels):
            fig_site.add_trace(go.Scatter(x=[base_coords[i][0]], y=[base_coords[i][1]], mode="markers+text", 
                                          text=[f"<b>{label}</b><br>{reductions_cm[i]:.1f}cm"], 
                                          textposition="top center", marker=dict(color="blue", size=12), showlegend=False))
    else:
        for i, idx in enumerate(post_indices):
            fig_site.add_trace(go.Scatter(x=[base_coords[idx][0]], y=[base_coords[idx][1]], mode="markers+text", 
                                          text=[f"<b>{post_labels[i]}</b><br>{reductions_cm[idx]:.1f}cm"], 
                                          textposition="top center", marker=dict(color="blue", size=12), showlegend=False))

    max_cy = max(cy) if len(cy) > 0 else 1.0
    fig_site.add_annotation(x=0, y=max_cy * 1.5, text="<b>⬆️ ทิศเหนือ (N)</b>", showarrow=False, font=dict(color="#EF4444", size=15))

    fig_site.update_layout(height=500, plot_bgcolor='white', xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1))
    st.plotly_chart(fig_site, use_container_width=True)

with col_right:
    st.subheader("📦 โมเดล 3 มิติ (3D Simulation)")
    fig_3d = go.Figure()
    
    rx, ry, rz = zip(*roof_coords_opt)
    fig_3d.add_trace(go.Mesh3d(x=rx, y=ry, z=rz, color='#06B6D4', opacity=0.6, name="ผ้าใบหลังคา"))
    
    if not poly_shadow_full.is_empty:
        sfx, sfy = poly_shadow_full.exterior.xy
        fig_3d.add_trace(go.Mesh3d(x=list(sfx), y=list(sfy), z=[0]*len(sfx), color='#334155', opacity=0.5, name="บริเวณเงารวมทั้งหมด"))
    
    draw_idx = range(len(base_coords)) if shape_type != "วงกลม" else post_indices
    for i in draw_idx:
        fig_3d.add_trace(go.Scatter3d(x=[base_coords[i][0], base_coords[i][0]], y=[base_coords[i][1], base_coords[i][1]], 
                                      z=[0, roof_coords_opt[i][2]], mode='lines', line=dict(color='#1E293B', width=4), showlegend=False))
    
    fig_3d.update_layout(height=500, margin=dict(l=0, r=0, b=0, t=0),
                        scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(range=[0, H_start+0.5], title="Height (m)")))
    st.plotly_chart(fig_3d, use_container_width=True)

# --- 9. TABLES ---
st.markdown('<div class="custom-card"><p style="font-weight:bold; color:#1E40AF;">🛠️ คู่มือระยะผูกเชือกติดตั้งหน้างานจริง (Site Guide)</p></div>', unsafe_allow_html=True)
if shape_type != "วงกลม":
    guide_data = {
        "ตำแหน่ง": post_labels,
        "ระยะลดจากยอดเสา": [f"ลดลง {r:.1f} ซม." if r >= 0.5 else "0 ซม. (ระดับสูงสุด)" for r in reductions_cm],
        "ความสูงผ้าใบจริง (แกน Z)": [f"{roof_coords_opt[i][2]:.2f} เมตร" for i in range(len(base_coords))]
    }
else:
    guide_data = {
        "จุดทิศหลัก": post_labels,
        "ระยะลดจากระดับเดิม": [f"ลดลง {reductions_cm[idx]:.1f} ซม." if reductions_cm[idx] >= 0.5 else "0 ซม. (ระดับสูงสุด)" for idx in post_indices],
        "ความสูงผ้าใบจุดนี้": [f"{roof_coords_opt[idx][2]:.2f} เมตร" for idx in post_indices]
    }
st.table(guide_data)

st.write("---")
st.subheader("📊 ตารางวิเคราะห์เปรียบเทียบดัชนีประสิทธิภาพเชิงลึก")
st.table({
    "ตัวชี้วัดประสิทธิภาพ (Performance Metrics)": [
        "พื้นที่เงาตกกระทบรวมทั้งหมด (Total Shade Area)", 
        "พื้นที่ร่มเงาที่ใช้งานได้ใต้ชายคา (Net Effective Shade)", 
        "อัตราครอบคลุมร่มเงาใต้ชายคา (Shade Coverage Ratio)"
    ],
    "❌ หลังคาแบบราบปกติ (ก่อนปรับระดับ)": [f"{area_total_shadow_flat:.2f} ตร.ม.", f"{area_opt_flat:.2f} ตร.ม.", f"{percent_flat:.1f} %"],
    "✨ หลังคาแบบปรับระดับ (Optimized Frame)": [f"{area_total_shadow_opt:.2f} ตร.ม.", f"{area_opt:.2f} ตร.ม.", f"{percent_opt:.1f} %"],
    "📈 ส่วนต่างการพัฒนา (Delta Gain)": [f"{area_total_shadow_opt - area_total_shadow_flat:+.2f} ตร.ม.", f"{area_opt - area_opt_flat:+.2f} ตร.ม.", f"{percent_opt - percent_flat:+.1f} %"]
})
