import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta, date

# --- 基礎設定 ---
st.set_page_config(page_title="全通用型藥局智能排班系統", page_icon="💊", layout="wide")

DAY_NAMES = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
LEAVES_FILE, CONFIG_FILE, PERSONAL_SHIFTS_FILE = "leaves_data.json", "store_config.json", "personal_shifts.json"
HISTORY_14D_FILE, FINAL_SCHEDULE_FILE, SPECIAL_DAYS_FILE = "history_14d_data.json", "final_schedule.json", "special_days.json"
WORK_HOURS_FILE, CONFLICT_FILE, MEETING_FILE = "work_hours_config.json", "conflict_rules.json", "meeting_rules.json"

def load_json(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f: return json.load(f)
        except: return default_val
    return default_val

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False)

if 'emp_df' not in st.session_state:
    st.session_state.emp_df = pd.DataFrame([
        {"姓名": "呈", "類型": "正職", "藥師": False, "成熟人力": True, "最少天數": 5, "最多天數": 5, "偏好": "偏好早班"},
        {"姓名": "桂", "類型": "正職", "藥師": False, "成熟人力": True, "最少天數": 5, "最多天數": 5, "偏好": "偏好晚班"},
        {"姓名": "花藥", "類型": "正職", "藥師": True, "成熟人力": True, "最少天數": 5, "最多天數": 5, "偏好": "無偏好"},
        {"姓名": "品", "類型": "PT", "藥師": False, "成熟人力": False, "最少天數": 2, "最多天數": 5, "偏好": "無偏好"}
    ])

EMPLOYEES = st.session_state.emp_df["姓名"].dropna().tolist()

# --- 介面呈現 ---
st.sidebar.title("🔐 系統權限")
user_role = st.sidebar.radio("請選擇身分：", ["👤 員工專區", "🔒 店長管理後台"])

if user_role == "👤 員工專區":
    st.title("💊 員工專區")
    final_sched_all = load_json(FINAL_SCHEDULE_FILE, {})
    if final_sched_all:
        target = st.selectbox("查看班表：", list(final_sched_all.keys()))
        st.dataframe(pd.DataFrame(final_sched_all[target]), use_container_width=True)
    st.stop()

# 店長後台檢查
store_config = load_json(CONFIG_FILE, {"店長密碼": "1234"})
if st.sidebar.text_input("輸入店長密碼：", type="password") != store_config.get("店長密碼", "1234"):
    st.warning("⚠️ 請輸入正確密碼")
    st.stop()

st.title("💊 藥局智能排班系統 (店長後台)")
tabs = st.tabs(["👥 人員", "⚔️ 互斥", "🗣️ 會議", "🚀 自動排班與審核"])

with tabs[0]:
    st.session_state.emp_df = st.data_editor(st.session_state.emp_df, num_rows="dynamic")

with tabs[1]:
    conflict_rules = load_json(CONFLICT_FILE, [])
    c1, c2 = st.selectbox("A", EMPLOYEES), st.selectbox("B", EMPLOYEES)
    if st.button("新增互斥"):
        conflict_rules.append(sorted([c1, c2]))
        save_json(CONFLICT_FILE, conflict_rules)
        st.rerun()

with tabs[2]:
    meeting_rules = load_json(MEETING_FILE, {})
    day = st.selectbox("選擇星期", DAY_NAMES)
    emps = st.multiselect("參與會議人員", EMPLOYEES)
    if st.button("儲存會議"):
        meeting_rules[day] = emps
        save_json(MEETING_FILE, meeting_rules)

with tabs[3]:
    schedule_week_str = st.text_input("週次識別", value="2026-W34")
    if st.button("🚀 開始自動排班"):
        st.session_state.temp_schedule = pd.DataFrame([{"日期": d, "早班": "呈, 花藥", "晚班": "桂, 品"} for d in DAY_NAMES])
    
    if 'temp_schedule' in st.session_state:
        edited_schedule = st.data_editor(st.session_state.temp_schedule, use_container_width=True)
        if st.button("💾 執行規則檢查並發佈", type="primary"):
            error_messages = []
            emp_info = {r["姓名"]: {"類型": r["類型"], "藥師": bool(r["藥師"]), "成熟人力": bool(r["成熟人力"])} for _, r in st.session_state.emp_df.iterrows()}
            
            def check_rules(name_list, is_night, day, m_emps):
                errs = []
                # 規則 1-05: 成熟人力
                if not any(emp_info.get(e, {}).get("成熟人力", False) for e in name_list):
                    errs.append(f"{day} {('晚班' if is_night else '早班')} 全為新人，缺乏指導！")
                # 規則 1-16: 藥師晚班防線
                pt_ph = [e for e in name_list if emp_info.get(e, {}).get("藥師") and emp_info.get(e, {}).get("類型") == "PT"]
                if is_night and pt_ph:
                    if not any(emp_info.get(e, {}).get("類型") == "正職" for e in name_list):
                        errs.append(f"{day} 晚班 PT 藥師需搭配正職！")
                return errs

            # 循環檢核每一天
            for row in edited_schedule.to_dict(orient="records"):
                day, m_list = row["日期"], [x.strip() for x in str(row["早班"]).split(",")]
                n_list = [x.strip() for x in str(row["晚班"]).split(",")]
                
                # 檢查人數
                if len(m_list) != 2: error_messages.append(f"{day} 早班人數不符")
                # 執行檢查
                m_errs = check_rules(m_list, False, day, load_json(MEETING_FILE, {}).get(day, []))
                n_errs = check_rules(n_list, True, day, load_json(MEETING_FILE, {}).get(day, []))
                error_messages.extend(m_errs + n_errs)

            if error_messages:
                st.error("\n".join(error_messages))
            else:
                final = load_json(FINAL_SCHEDULE_FILE, {})
                final[schedule_week_str] = edited_schedule.to_dict(orient="records")
                save_json(FINAL_SCHEDULE_FILE, final)
                st.success("發佈成功！")
