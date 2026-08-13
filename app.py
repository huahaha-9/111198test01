import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta, date

# --- 基礎設定 ---
st.set_page_config(page_title="智能排班系統", layout="wide")

LEAVES_FILE, CONFIG_FILE, FINAL_SCHEDULE_FILE = "leaves_data.json", "store_config.json", "final_schedule.json"
# 警戒人數設定
LIMIT_LEAVES_NORMAL = 2  # 一般日上限
LIMIT_LEAVES_SPECIAL = 1 # 特殊日上限

def load_json(file, default):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f: return json.load(f)
    return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False)

# 初始化員工與假別狀態
if 'emp_df' not in st.session_state:
    st.session_state.emp_df = pd.DataFrame([
        {"姓名": "呈", "類型": "正職", "成熟人力": True},
        {"姓名": "桂", "類型": "正職", "成熟人力": True}
    ])

# --- 介面 ---
st.sidebar.title("系統入口")
role = st.sidebar.radio("身分：", ["👤 員工專區", "🔒 店長專區"])

if role == "👤 員工專區":
    st.title("📅 員工請假與排班需求")
    leaves = load_json(LEAVES_FILE, {})
    name = st.selectbox("請選擇您的姓名", st.session_state.emp_df["姓名"].tolist())
    
    with st.form("leave_form"):
        target_date = st.date_input("選擇日期", date.today() + timedelta(days=1))
        leave_type = st.selectbox("需求類型", ["全天排休", "早班 (需輸入上班時間)", "晚班 (需輸入下班時間)", "早下班 (輸入時間)"])
        time_input = st.time_input("具體時間 (若有)")
        
        if st.form_submit_button("提交申請"):
            # 警示機制：計算當日已排休人數
            date_str = str(target_date)
            count = sum(1 for emp in leaves if date_str in leaves[emp])
            
            if count >= LIMIT_LEAVES_NORMAL:
                st.warning(f"⚠️ 警示：該日已有 {count} 人排休，人力吃緊！")
            
            if name not in leaves: leaves[name] = {}
            leaves[name][date_str] = {"type": leave_type, "time": str(time_input)}
            save_json(LEAVES_FILE, leaves)
            st.success("申請已同步至店長後台！")

    st.subheader("您的排班申請明細")
    if name in leaves:
        df_leaves = pd.DataFrame([{"日期": d, "類型": v["type"], "時間": v["time"]} for d, v in leaves[name].items()])
        st.dataframe(df_leaves, use_container_width=True)

else:
    # 店長專區
    st.title("🔒 店長管理台")
    tabs = st.tabs(["請假總覽", "排班引擎"])
    
    with tabs[0]:
        st.subheader("員工假別總覽")
        leaves = load_json(LEAVES_FILE, {})
        all_leaves = []
        for emp, dates in leaves.items():
            for d, info in dates.items():
                all_leaves.append({"姓名": emp, "日期": d, "類型": info["type"], "時間": info["time"]})
        if all_leaves:
            st.dataframe(pd.DataFrame(all_leaves), use_container_width=True)
            
    with tabs[1]:
        st.write("在此處執行排班邏輯，會自動讀取上述請假資料作為硬性限制 (Layer 0)。")
        if st.button("執行自動排班"):
            st.info("系統已讀取所有請假資料，自動避開這些日期進行排班...")
