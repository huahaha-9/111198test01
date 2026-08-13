import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date

# --- 檔案儲存設定 ---
LEAVES_FILE = "leaves_data.json"
def load_json(f, d): return json.load(open(f, "r", encoding="utf-8")) if os.path.exists(f) else d
def save_json(f, d): json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False)

st.set_page_config(page_title="藥局智能排班系統", layout="wide")

if 'emp_df' not in st.session_state:
    st.session_state.emp_df = pd.DataFrame([
        {"姓名": "呈", "類型": "正職", "藥師": False, "成熟人力": True},
        {"姓名": "桂", "類型": "正職", "藥師": False, "成熟人力": True},
        {"姓名": "花藥", "類型": "正職", "藥師": True, "成熟人力": True},
        {"姓名": "品", "類型": "PT", "藥師": False, "成熟人力": False}
    ])

# 彈性工時計算
def get_lost_hours(req_type, time_str):
    if req_type == "早班提早下班" and time_str != "無": return (1700 - int(time_str)) / 100
    if req_type == "晚班晚上班" and time_str != "無": return (int(time_str) - 1400) / 100
    return 0

# --- 側邊欄 ---
role = st.sidebar.radio("請選擇身分：", ["👤 員工專區", "🔒 店長專區"])

# --- 員工專區 ---
if role == "👤 員工專區":
    st.title("📅 員工排班申請")
    leaves = load_json(LEAVES_FILE, {})
    name = st.selectbox("請選擇姓名", st.session_state.emp_df["姓名"].tolist())
    
    with st.form("leave_form"):
        target_date = st.date_input("選擇日期", min_value=date.today())
        req_type = st.selectbox("需求類型", ["全天排休", "正常早班", "正常晚班", "早班提早下班", "晚班晚上班"])
        
        extra_time = "無"
        times = [f"{h:02d}{m:02d}" for h in range(8, 23) for m in [0, 30]]
        
        if req_type == "早班提早下班":
            extra_time = st.selectbox("選擇下班時間", [t for t in times if "0900" <= t <= "1700"])
        elif req_type == "晚班晚上班":
            extra_time = st.selectbox("選擇上班時間", [t for t in times if "1400" <= t <= "1800"])
            
        if st.form_submit_button("送出申請"):
            d_str = str(target_date)
            if name not in leaves: leaves[name] = {}
            leaves[name][d_str] = {"type": req_type, "time": extra_time}
            save_json(LEAVES_FILE, leaves)
            st.success(f"✅ 登記成功！")
            st.rerun()

    # --- 即時顯示申請清單（優化時間呈現） ---
    st.divider()
    st.subheader(f"📋 {name} 的排班/請假清單")
    if name in leaves and leaves[name]:
        display_data = []
        for d, v in leaves[name].items():
            t_type = v["type"]
            t_val = v["time"]
            
            # 轉換更直覺的顯示文字，避免出現「無」
            if t_type == "全天排休":
                time_display = "休假 (全天)"
            elif t_type == "正常早班":
                time_display = "09:00 - 17:00 (正常早班)"
            elif t_type == "正常晚班":
                time_display = "14:00 - 22:00 (正常晚班)"
            elif t_type == "早班提早下班":
                time_display = f"09:00 - {t_val[:2]}:{t_val[2:]} (早班提早下班)"
            elif t_type == "晚班晚上班":
                time_display = f"{t_val[:2]}:{t_val[2:]} - 22:00 (晚班晚上班)"
            else:
                time_display = t_val

            display_data.append({"日期": d, "項目類型": t_type, "當日班別與時間": time_display})
            
        st.table(pd.DataFrame(display_data).sort_values(by="日期"))
    else:
        st.info("目前沒有申請記錄。")

# --- 店長專區 ---
else:
    st.title("🔒 店長管理後台")
    tabs = st.tabs(["👥 人員管理", "🚀 自動排班與檢核"])
    
    with tabs[0]:
        st.session_state.emp_df = st.data_editor(st.session_state.emp_df, num_rows="dynamic")
    
    with tabs[1]:
        if st.button("🚀 執行排班檢核"):
            leaves = load_json(LEAVES_FILE, {})
            emp_info = {r["姓名"]: {"類型": r["類型"], "藥師": bool(r["藥師"]), "成熟人力": bool(r["成熟人力"])} for _, r in st.session_state.emp_df.iterrows()}
            
            schedule = [{"日期": "2026-08-14", "早班": ["呈", "花藥"], "晚班": ["桂", "品"]}]
            
            for row in schedule:
                d = row["日期"]
                for staff in row["早班"] + row["晚班"]:
                    if staff in leaves and d in leaves[staff]:
                        req = leaves[staff][d]
                        lost = get_lost_hours(req["type"], req["time"])
                        if lost > 0:
                            st.warning(f"⚠️ 【工時警示】{staff} 在 {d} 申請 {req['type']}，工時縮減 {lost} 小時。")
                st.success(f"✅ {d} 排班檢核完成。")
