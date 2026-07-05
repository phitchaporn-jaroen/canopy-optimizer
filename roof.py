import streamlit as st
import numpy as np
import plotly.graph_objects as go
from shapely.geometry import Polygon
import pandas as pd

# --- 1. CONFIG & STYLE (ธีมพาสเทล คาเฟ่มินิมอล น่ารัก อบอุ่น) ---
st.set_page_config(page_title="Cozy Canopy", layout="wide")

st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 14px; color: #4A4A4A; font-family: 'Kanit', sans-serif; }
    
    .custom-card { 
        background-color: #F0FDF4; 
        border-left: 5px solid #BBF7D0; 
        border-radius: 12px; 
        padding: 12px; 
        margin: 15px 0; 
    }
    
    .custom-card-blue { 
        background-color: #F0F9FF; 
        border-left: 5px solid #BAE6FD; 
        border-radius: 12px; 
        padding: 12px; 
        margin: 15px 0; 
    }
    
    [data-testid="stMetric"] { 
        background-color: #FFF7ED; 
        border: 2px dashed #FFEDD5; 
        border-radius: 16px; 
        padding: 12px; 
    }
    
    .responsive-table-container {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        margin-bottom: 25px;
    }
    
    .stTable table {
        width: 100% !important;
        border-collapse: collapse !important;
        border-radius: 16px !important;
        overflow: hidden !important;
        border: 1px solid #E5E7EB !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
    }
    
    .stTable th {
        background: linear-gradient(135deg, #FFEDD5 0%, #FED7AA 100%) !important;
        color: #7C2D12 !important;
        font-weight: 700 !important;
        text-align: center !important;
        padding: 14px 12px !important;
        font-size: 14px !important;
        border-bottom: 2px solid #FDBA74 !important;
    }
    
    .stTable td {
        padding: 14px 12px !important;
        text-align: center !important;
        border-bottom: 1px solid #F3F4F6 !important;
        font-size: 13.5px !important;
    }
    
    .stTable td:first-child, .stTable th:first-child {
        text-align: left !important;
        font-weight: 600 !important;
        background-color: #FAFAFA !important;
        color: #1F2937 !important;
        padding-left: 16px !important;
    }
    
    .stTable tbody tr:nth-child(even) { background-color: #FDFBF7 !important; }
    .stTable tbody tr:hover { background-color: #FEF3C7 !important; transition: background-color 0.2s ease !important; }
    
    .stTable td:nth-child(2) { color: #0284C7 !important; font-weight: 500; }
    .stTable td:nth-child(3) { color: #B45309 !important; font-weight: bold !important; }
    .stTable td:nth-child(4) { color: #15803D !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🌈 Cozy Canopy Shade")
st.caption("🏡 คำนวณระดับผ้าใบรับร่มเงาให้บ้านคุณเย็นสบายที่สุด")

# --- 2. SIDEBAR: PARAMETERS ---
st.sidebar.header("📐 รูปทรงผ้าใบ")
shape_type = st.sidebar.selectbox("เลือกทรงผ้าใบ", ["สี่เหลี่ยม", "สามเหลี่ยมด้านเท่า", "วงกลม"])

if shape_type == "สี่เหลี่ยม":
    W = st.sidebar.number_input("กว้าง W (ม.)", min_value=0.1, value=1.0, step=0.1)
    L = st.sidebar.number_input("ยาว L (ม.)", min_value=0.1, value=1.0, step=0.1)
    diag_span = np.sqrt(W**2 + L**2) 
elif shape_type == "สามเหลี่ยมด้านเท่า":
    S = st.sidebar.number_input("ความยาวด้าน (ม.)", min_value=0.1, value=1.0, step=0.1)
    diag_span = S * np.sqrt(3) / 2
else: 
    R = st.sidebar.number_input("รัศมี (ม.)", min_value=0.1, value=1.0, step=0.1)
    diag_span = 2 * R

H_start = st.sidebar.number_input("ความสูงเสาเริ่มต้น H (ม.)", min_value=0.1, value=1.0, step=0.1)
building_ori = st.sidebar.slider("หมุนทิศตัวบ้าน (องศาจากทิศ N)", 0, 360, 0, step=15)

st.sidebar.header("📅 วันเวลาที่ต้องการดูเงา")
month = st.sidebar.selectbox(
    "เลือกเดือน", 
    ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"],
    index=6
)

# แก้ไขครั้งสุดท้าย: ปรับช่วงเวลาเป็น 7.00 น. - 17.00 น. และบังคับมีพิกัด .00
hour = st.sidebar.slider("เวลา (น.)", min_value=7, max_value=17, value=9, step=1)

build_rad = np.radians(building_ori)

# --- 3. MATH & SOLAR FUNCTIONS ---
def rotate_point(x, y, angle):
    return x * np.cos(angle) - y * np.sin(angle), x * np.sin(angle) + y * np.cos(angle)

def get_sun_pos_by_month(h_input, m_name):
    months_dict = {
        "มกราคม": 15, "กุมภาพันธ์": 46, "มีนาคม": 74, "เมษายน": 105, 
        "พฤษภาคม": 135, "มิถุนายน": 166, "กรกฎาคม": 196, "สิงหาคม": 227, 
        "กันยายน": 258, "ตุลาคม": 288, "พฤศจิกายน": 319, "ธันวาคม": 349
    }
    day_of_year = months_dict.get(m_name, 196)
    declination = 23.45 * np.sin(np.radians(360 / 365 * (day_of_year - 80)))
    latitude = 13.7
    hour_angle = (h_input - 12) * 15
    
    sin_alt = (np.sin(np.radians(latitude)) * np.sin(np.radians(declination)) + 
               np.cos(np.radians(latitude)) * np.cos(np.radians(declination)) * np.cos(np.radians(hour_angle)))
    alt = np.degrees(np.arcsin(sin_alt))
    alt = max(1.0, min(89.9, alt))
    
    cos_az = ((np.sin(np.radians(declination)) - np.sin(np.radians(latitude)) * np.sin(np.radians(alt))) / 
              (np.cos(np.radians(latitude)) * np.cos(np.radians(alt))))
    cos_az = max(-1.0, min(1.0, cos_az))
    az = np.degrees(np.arccos(cos_az))
    if h_input > 12:
        az = 360 - az
    return alt, az

# --- 4. GEOMETRY GENERATION ---
if shape_type == "สี่เหลี่ยม":
    pts = [(-W/2, -L/2), (W/2, -L/2), (W/2, L/2), (-W/2, L/2)]
    post_labels = ["เสา 1 (ซ้ายล่าง)", "เสา 2 (ขวาล่าง)", "เสา 3 (ขวาบน)", "เสา 4 (ซ้ายบน)"]
    target_indices = [0, 1, 2, 3]
elif shape_type == "สามเหลี่ยมด้านเท่า":
    h_tri = S * np.sqrt(3) / 2
    pts = [(0, 2*h_tri/3), (-S/2, -h_tri/3), (S/2, -h_tri/3)]
    post_labels = ["เสา 1 (ยอด)", "เสา 2 (ซ้าย)", "เสา 3 (ขวา)"]
    target_indices = [0, 1, 2]
else: 
    angles = np.linspace(0, 2*np.pi, 65)[:-1]
    pts = [(R * np.cos(a), R * np.sin(a)) for a in angles]
    target_indices = [16, 0, 48, 32]  
    post_labels = ["จุดเหนือ (N)", "จุดตะวันออก (E)", "จุดใต้ (S)", "จุดตะวันตก (W)"]

base_coords = [rotate_point(p[0], p[1], -build_rad) for p in pts]
poly_canopy_base = Polygon(base_coords)
area_base = poly_canopy_base.area

# --- 5. SOLAR VECTOR CALCULATIONS ---
alt_deg, az_deg = get_sun_pos_by_month(hour, month)
alt_rad, az_rad = np.radians(alt_deg), np.radians(az_deg)

sun_x = np.sin(az_rad)
sun_y = np.cos(az_rad)
sun_z = np.tan(alt_rad)

optimal_face_azimuth_deg = (az_deg + 180) % 360

# --- 6. SHADOW PROJECTION: FLAT TYPE ---
shadow_pts_flat = []
for bc in base_coords:
    t_flat = H_start / sun_z
    shadow_pts_flat.append((bc[0] - t_flat * sun_x, bc[1] - t_flat * sun_y))
poly_shadow_flat = Polygon(shadow_pts_flat)
area_total_shadow_flat = poly_shadow_flat.area

intersect_flat = poly_canopy_base.intersection(poly_shadow_flat)
area_opt_flat = intersect_flat.area if not intersect_flat.is_empty else 0.0
percent_flat = (area_opt_flat / area_base) * 100 if area_base > 0 else 0.0

# --- 7. SHADOW PROJECTION: OPTIMIZED SLOPE TYPE ---
rope_diffs = [(bc[0] * sun_x + bc[1] * sun_y) for bc in base_coords]
max_d, min_d = max(rope_diffs), min(rope_diffs)
proj_span = max_d - min_d if (max_d - min_d) > 0 else 1.0

H_min_allowed = H_start * 0.3  
delta_z_max = H_start - H_min_allowed

ideal_tilt_deg = max(10.0, min(50.0, 90.0 - alt_deg))
ideal_delta_z = proj_span * np.tan(np.radians(ideal_tilt_deg))

if ideal_delta_z <= delta_z_max:
    use_delta_z = ideal_delta_z
    optimal_tilt_deg = ideal_tilt_deg
else:
    use_delta_z = delta_z_max
    optimal_tilt_deg = np.degrees(np.arctan2(use_delta_z, proj_span))

roof_coords_opt = []
for i, bc in enumerate(base_coords):
    ratio = (rope_diffs[i] - min_d) / proj_span
    z_height = H_start - (ratio * use_delta_z)
    roof_coords_opt.append(np.array([bc[0], bc[1], z_height]))

shadow_pts_full = []
for rp in roof_coords_opt:
    t_opt = rp[2] / sun_z
    shadow_pts_full.append((rp[0] - t_opt * sun_x, rp[1] - t_opt * sun_y))
poly_shadow_full = Polygon(shadow_pts_full)
area_total_shadow_opt = poly_shadow_full.area

intersect_opt = poly_canopy_base.intersection(poly_shadow_full)
area_opt = intersect_opt.area if not intersect_opt.is_empty else 0.0

if area_opt > area_base:
    area_opt = area_base
percent_opt = (area_opt / area_base) * 100 if area_base > 0 else 0.0

# --- 8. DISPLAY METRICS ---
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1: 
    st.metric(
        label="☀️ ตำแหน่งดวงอาทิตย์", 
        value=f"มุมสูง {alt_deg:.1f}°", 
        delta=f"ทิศทาง {az_deg:.1f}° ({hour}.00 น.)"
    )
with col_m2: st.metric(label="📐 ขนาดผ้าใบ", value=f"{area_base:.1f} ตร.ม.", delta=shape_type)
with col_m3: 
    st.metric(
        label="📐 มุมเอียงหลังคา", 
        value=f"{optimal_tilt_deg:.1f}°", 
        delta=f"ทิศลาดต่ำ: {optimal_face_azimuth_deg:.1f}°"
    )
with col_m4: st.metric(label="🍀 พื้นที่ร่มเงาจริง", value=f"{percent_opt:.1f} %", delta=f"{area_opt:.2f} ตร.ม.")

st.write("---")

# --- 9. PRE-CALCULATE TIE POINTS FOR 2D LABELS ---
tie_hints = {}
for idx, actual_idx in enumerate(target_indices):
    canopy_z_m = roof_coords_opt[actual_idx][2]
    drop_from_top_cm = (H_start - canopy_z_m) * 100
    if drop_from_top_cm < 0.5:
        tie_hints[actual_idx] = "ผูกหัวเสา"
    else:
        tie_hints[actual_idx] = f"รูดลง {drop_from_top_cm:.1f} ซม."

# --- 10. VISUALIZATION (2D & 3D) ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📍 ผังร่มเงาบนพื้น (2D)")
    fig_site = go.Figure()
    cx = [p[0] for p in base_coords] + [base_coords[0][0]]
    cy = [p[1] for p in base_coords] + [base_coords[0][1]]
    fig_site.add_trace(go.Scatter(x=cx, y=cy, mode="lines", line=dict(color="#4B5563", width=2, dash="dash"), name="ขอบเขตเสาผ้าใบ"))
    
    if not poly_shadow_full.is_empty and poly_shadow_full.geom_type in ["Polygon", "MultiPolygon"]:
        sfx, sfy = poly_shadow_full.exterior.xy
        fig_site.add_trace(go.Scatter(x=list(sfx), y=list(sfy), fill="toself", fillcolor="rgba(148, 163, 184, 0.25)", line=dict(color="rgba(148, 163, 184, 0.5)", width=1), name="เงารวมบนพื้น"))
        
    if not intersect_opt.is_empty and intersect_opt.geom_type in ["Polygon", "MultiPolygon"]:
        six, siy = intersect_opt.exterior.xy
        fig_site.add_trace(go.Scatter(x=list(six), y=list(siy), fill="toself", fillcolor="rgba(34, 197, 94, 0.45)", line=dict(color="#16A34A", width=2), name="ร่มเงาใต้ผ้าใบ"))

    for idx, i in enumerate(target_indices):
        label = post_labels[idx]
        short_name = label.split(" ")[0] if shape_type == "วงกลม" else label.split(" ")[0] + " " + label.split(" ")[1]
        hint_text = tie_hints.get(i, "")
        combined_text = f"<b>{short_name}</b><br><span style='color:#16A34A; font-size:11px;'>{hint_text}</span>"
        
        fig_site.add_trace(go.Scatter(
            x=[base_coords[i][0]], y=[base_coords[i][1]], 
            mode="markers+text", 
            text=[combined_text], 
            textposition="top center", 
            marker=dict(color="#0EA5E9", size=10), 
            showlegend=False
        ))

    max_cy = max(cy) if len(cy) > 0 else 1.0
    fig_site.add_annotation(x=0, y=max_cy * 1.6, text="<b>⬆️ ทิศเหนือ (N)</b>", showarrow=False, font=dict(color="#EF4444", size=14))
    fig_site.update_layout(height=420, plot_bgcolor='white', xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1), margin=dict(l=10, r=10, b=10, t=10))
    st.plotly_chart(fig_site, use_container_width=True)

with col_right:
    st.subheader("📦 จำลองหลังคาเอียงตามทิศแดด (3D)")
    fig_3d = go.Figure()
    
    rx, ry, rz = zip(*roof_coords_opt)
    rx_l, ry_l, rz_l = list(rx) + [rx[0]], list(ry) + [ry[0]], list(rz) + [rz[0]]
    fig_3d.add_trace(go.Scatter3d(x=rx_l, y=ry_l, z=rz_l, mode='lines', line=dict(color='#0EA5E9', width=5), name="ผ้าใบลาดเอียง"))
    
    if shape_type == "สี่เหลี่ยม":
        fig_3d.add_trace(go.Mesh3d(x=list(rx), y=list(ry), z=list(rz), i=[0, 0], j=[1, 2], k=[2, 3], color='#38BDF8', opacity=0.6, showlegend=False))
    elif shape_type == "สามเหลี่ยมด้านเท่า":
        fig_3d.add_trace(go.Mesh3d(x=list(rx), y=list(ry), z=list(rz), i=[0], j=[1], k=[2], color='#38BDF8', opacity=0.6, showlegend=False))
    else:
        fig_3d.add_trace(go.Mesh3d(x=list(rx), y=list(ry), z=list(rz), alphahull=0, color='#38BDF8', opacity=0.6, showlegend=False))
    
    if not poly_shadow_full.is_empty and poly_shadow_full.geom_type in ["Polygon", "MultiPolygon"]:
        sfx, sfy = poly_shadow_full.exterior.xy
        sfz = [0.0] * len(sfx)
        fig_3d.add_trace(go.Scatter3d(x=list(sfx), y=list(sfy), z=sfz, mode='lines', line=dict(color='rgba(75, 85, 99, 0.6)', width=2), showlegend=False))
        fig_3d.add_trace(go.Mesh3d(x=list(sfx), y=list(sfy), z=sfz, alphahull=0 if shape_type == "วงกลม" else None, color='#CBD5E1', opacity=0.5, name="เงาบนพื้น"))

    draw_idx = range(len(base_coords)) if shape_type != "วงกลม" else target_indices
    for i in draw_idx:
        current_z = roof_coords_opt[i][2]
        fig_3d.add_trace(go.Scatter3d(
            x=[base_coords[i][0], base_coords[i][0]], 
            y=[base_coords[i][1], base_coords[i][1]], 
            z=[0, current_z], 
            mode='lines', line=dict(color='#64748B', width=4), showlegend=False
        ))
    
    fig_3d.update_layout(height=420, margin=dict(l=0, r=0, b=0, t=0), scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(range=[0, H_start+0.5], title="สูง (ม.)")))
    st.plotly_chart(fig_3d, use_container_width=True)

# --- 11. TABLE 1: คู่มือระยะจุดผูกผ้าใบจริงบนเสา (แก้ไขตามบรีฟครั้งสุดท้าย: แสดงหน่วย ซม. ที่หัวคอลัมน์ และตัดเมตรออก) ---
st.markdown('<div class="custom-card"><p style="font-weight:bold; color:#15803D; margin:0; font-size:15px;">🛠️ ตารางที่ 1: คู่มือระดับจุดผูกผ้าใบหน้างาน</p></div>', unsafe_allow_html=True)

guide_table_rows = []
for idx, actual_idx in enumerate(target_indices):
    canopy_z_m = roof_coords_opt[actual_idx][2]
    drop_from_top_cm = (H_start - canopy_z_m) * 100
    
    ratio = (rope_diffs[actual_idx] - min_d) / proj_span
    horizontal_offset_m = ratio * (use_delta_z / np.tan(np.radians(optimal_tilt_deg))) if optimal_tilt_deg > 0 else 0.0
    horizontal_offset_cm = horizontal_offset_m * 100

    if drop_from_top_cm < 0.5:
        tie_point_str = "หัวเสาสูงสุด"
    else:
        tie_point_str = f"รูดต่ำลง {drop_from_top_cm:.1f}"

    # ตัดการแสดงผลตัวเลขและหน่วยเมตรออกตามคำสั่ง เหลือเพียงตัวเลขพิกัด ซม. ล้วน ๆ
    canopy_z_str = f"{canopy_z_m*100:.1f}"
    horiz_offset_str = f"{horizontal_offset_cm:.1f}"
    ref_label = post_labels[idx] if shape_type == "วงกลม" else post_labels[idx].split(" ")[0] + " " + post_labels[idx].split(" ")[1]

    guide_table_rows.append({
        "เสาอ้างอิง": ref_label,
        "📍 จุดผูกบนเสา (ซม.)": tie_point_str,
        "🌍 ความสูงพิกัดพื้น (ซม.)": canopy_z_str,
        "📐 ระยะห่างจากเสา (ซม.)": horiz_offset_str
    })

df_guide = pd.DataFrame(guide_table_rows)
st.markdown('<div class="responsive-table-container">', unsafe_allow_html=True)
st.table(df_guide)
st.markdown('</div>', unsafe_allow_html=True)

# --- 12. TABLE 2: วิเคราะห์ประสิทธิภาพตามเวลา ---
st.markdown('<div class="custom-card-blue"><p style="font-weight:bold; color:#0369A1; margin:0; font-size:15px;">📊 ตารางที่ 2: วิเคราะห์เปรียบเทียบร่มเงาใต้ชายคา</p></div>', unsafe_allow_html=True)

compare_table_data = {
    "ตัวชี้วัดประสิทธิภาพ": [
        "เงาตกกระทบรวมบนพื้น (ตร.ม.)", 
        "ร่มเงาใช้งานได้จริงใต้ผ้าใบ (ตร.ม.)", 
        "อัตราครอบคลุมร่มเงา (%)"
    ],
    "❌ แบบราบ": [f"{area_total_shadow_flat:.2f}", f"{area_opt_flat:.2f}", f"{percent_flat:.1f} %"],
    "✨ แบบเอียงสโลป": [f"{area_total_shadow_opt:.2f}", f"{area_opt:.2f}", f"{percent_opt:.1f} %"],
    "📈 ส่วนต่างที่เพิ่ม": [f"{area_total_shadow_opt - area_total_shadow_flat:+.2f}", f"{area_opt - area_opt_flat:+.2f}", f"{percent_opt - percent_flat:+.1f} %"]
}
df_compare = pd.DataFrame(compare_table_data)
st.markdown('<div class="responsive-table-container">', unsafe_allow_html=True)
st.table(df_compare)
st.markdown('</div>', unsafe_allow_html=True)
