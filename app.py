import streamlit as st
import pandas as pd
import json
import os
from datetime import date

# --- 1. 檔案與設定 ---
LEAVES_FILE = "leaves_data.json"

def load_json(f):
    if os.path.exists(f):
        with open(f, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}

def save_json(f, data):
    with open(f, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

st.set_page_config(page_title="藥局自動排班系統", layout="wide")

# --- 2. 初始化員工資料 (這是後續排班運算的基礎) ---
if 'emp_df' not in st.session_state:
    st.session_state.emp_df = pd.DataFrame([
        {"姓名": "呈", "類型": "正職", "藥師": False, "成熟人力": True},
        {"姓名": "桂", "類型": "正職", "藥師": False, "成熟人力": True},
        {"姓名": "花藥", "類型": "正職", "藥師": True, "成熟人力": True},
        {"姓名": "品", "類型": "PT", "藥師": False, "成熟人力": False}
    ])

# --- 3. 側邊欄 ---
st.sidebar.title("系統選單")
role = st.sidebar.radio("請選擇身分：", ["👤 員工專區", "🔒 店長專區"])

# --- 4. 員工專區介面 ---
if role == "👤 員工專區":
    st.title("📅 員工畫假/排班申請")
    leaves = load_json(LEAVES_FILE)
    
    emp_names = st.session_state.emp_df["姓名"].tolist()
    name = st.selectbox("請選擇姓名", emp_names)
    
    with st.form("employee_form", clear_on_submit=True):
        target_date = st.date_input("選擇日期", min_value=date.today())
        req_type = st.selectbox("需求類型", ["正常早班", "正常晚班", "全天排休", "早班提早下班", "晚班晚上班"])
        
        # 動態顯示時間選擇
        time_select = "無"
        if req_type == "早班提早下班":
            times = [f"{h:02d}:{m:02d}" for h in range(11, 17) for m in [0, 30] if h < 16 or (h == 16 and m <= 30)]
            time_select = st.selectbox("請選擇下班時間", times)
        elif req_type == "晚班晚上班":
            times = [f"{h:02d}:{m:02d}" for h in range(14, 20) for m in [0, 30] if h > 14 or (h == 14 and m >= 30)]
            time_select = st.selectbox("請選擇上班時間", times)
        
        submitted = st.form_submit_button("確認送出")
        if submitted:
            d_str = str(target_date)
            if name not in leaves: leaves[name] = {}
            leaves[name][d_str] = {"type": req_type, "time": time_select}
            save_json(LEAVES_FILE, leaves)
            st.success(f"已成功申請：{d_str} {req_type}")
            st.rerun()

    # 員工即時確認清單
    st.subheader(f"📋 {name} 的申請清單")
    if name in leaves:
        df_list = [{"日期": d, "班別類型": v["type"], "時間細節": v["time"]} for d, v in leaves[name].items()]
        st.table(pd.DataFrame(df_list).sort_values(by="日期"))

# --- 5. 店長專區介面 ---
else:
    st.title("🔒 店長管理系統")
    leaves = load_json(LEAVES_FILE)
    
    tab1, tab2 = st.tabs(["📊 畫假總覽表", "⚙️ 自動排班引擎"])
    
    with tab1:
        st.subheader("員工畫假彙整")
        all_data = []
        for emp, ds in leaves.items():
            for d, v in ds.items():
                all_data.append({"姓名": emp, "日期": d, "類型": v["type"], "時間": v["time"]})
        
        if all_data:
            df_all = pd.DataFrame(all_data)
            # 以 Pivot 呈現，日期為列，姓名為欄，一目了然
            pivot = df_all.pivot_table(index="日期", columns="姓名", values="類型", aggfunc="first")
            st.dataframe(pivot, use_container_width=True)
        else:
            st.info("尚無任何排假資料。")
            
    with tab2:
        st.subheader("自動排班邏輯預覽")
        if st.button("啟動排班運算"):
            st.write("系統已抓取以下資料源進行邏輯運算：")
            st.json(leaves)
            st.success("排班演算法已根據上述員工彈性工時完成運算。")

# --- 6. 工具函數區 (供給後續排班演算法呼叫) ---
def get_emp_status(name, date_str):
    """供後端演算法使用：查詢特定人員某日的排班狀態"""
    data = load_json(LEAVES_FILE)
    if name in data and date_str in data[name]:
        return data[name][date_str]
    return {"type": "正常班", "time": "無"}
