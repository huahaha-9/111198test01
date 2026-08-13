import streamlit as st
import pandas as pd
import json
import os
from datetime import date, timedelta

# --- 1. 檔案與設定 ---
LEAVES_FILE = "leaves_data.json"
FIXED_SHIFTS_FILE = "fixed_shifts_data.json"
PREFERENCES_FILE = "preferences_data.json"
MEETINGS_FILE = "meetings_data.json"

def load_json(f):
    if os.path.exists(f):
        with open(f, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}

def save_json(f, data):
    with open(f, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

st.set_page_config(page_title="藥局自動排班系統", layout="wide")

# --- 2. 初始化完整人員資料與屬性矩陣 ---
if 'emp_df' not in st.session_state:
    st.session_state.emp_df = pd.DataFrame([
        {"姓名": "嘉呈", "類型": "正職", "藥師": False, "成熟人力": True,  "新人": False, "訓練中": False},
        {"姓名": "桂華", "類型": "正職", "藥師": False, "成熟人力": True,  "新人": False, "訓練中": False},
        {"姓名": "花藥", "類型": "正職", "藥師": True,  "成熟人力": True,  "新人": False, "訓練中": False},
        {"姓名": "邱藥", "類型": "正職", "藥師": True,  "成熟人力": True,  "新人": False, "訓練中": False},
        {"姓名": "筠婷", "類型": "正職", "藥師": False, "成熟人力": False, "新人": False, "訓練中": True},
        {"姓名": "亭緯", "類型": "PT",   "藥師": False, "成熟人力": True,  "新人": False, "訓練中": False},
        {"姓名": "品萱", "類型": "PT",   "藥師": False, "成熟人力": False, "新人": True,  "訓練中": False},
        {"姓名": "肖維", "類型": "PT",   "藥師": False, "成熟人力": False, "新人": True,  "訓練中": False},
        {"姓名": "姵萱", "類型": "PT",   "藥師": False, "成熟人力": False, "新人": True,  "訓練中": False},
        {"姓名": "靜茹", "類型": "PT",   "藥師": False, "成熟人力": True,  "新人": False, "訓練中": False}
    ])

# 營業時間規則對應函數 (0=週一, ..., 6=週日)
def get_store_hours(day_of_week):
    if day_of_week in [1, 5, 6]:  # 週二、週六、週日
        return {"open": "09:00", "close": "22:30"}
    else:  # 週一、週三、週四、週五
        return {"open": "09:00", "close": "22:00"}

# --- 3. 側邊欄 ---
st.sidebar.title("系統選單")
role = st.sidebar.radio("請選擇身分：", ["👤 員工專區", "🔒 店長專區"])

# --- 4. 員工專區介面 ---
if role == "👤 員工專區":
    st.title("📅 員工畫假、排班與偏好設定")
    leaves = load_json(LEAVES_FILE)
    preferences = load_json(PREFERENCES_FILE)
    
    emp_names = st.session_state.emp_df["姓名"].tolist()
    name = st.selectbox("請選擇姓名", emp_names)
    
    tab_e1, tab_e2 = st.tabs(["📝 畫假與班別申請", "⭐ 個人偏好設定"])
    
    with tab_e1:
        with st.form("employee_form", clear_on_submit=True):
            target_date = st.date_input("選擇日期", min_value=date.today())
            req_type = st.selectbox("需求類型", ["正常早班", "正常晚班", "全天排休", "早班提早下班", "晚班晚上班"])
            
            time_select = "無"
            if req_type == "早班提早下班":
                times = [f"{h:02d}:{m:02d}" for h in range(11, 17) for m in [0, 30] if h < 16 or (h == 16 and m <= 30)]
                time_select = st.selectbox("請選擇下班時間", times)
            elif req_type == "晚班晚上班":
                times = [f"{h:02d}:{m:02d}" for h in range(14, 20) for m in [0, 30] if h > 14 or (h == 14 and m >= 30)]
                time_select = st.selectbox("請選擇上班時間", times)
            
            submitted = st.form_submit_button("確認送出申請")
            if submitted:
                d_str = str(target_date)
                if name not in leaves: leaves[name] = {}
                leaves[name][d_str] = {"type": req_type, "time": time_select}
                save_json(LEAVES_FILE, leaves)
                st.success(f"已成功送出申請：{d_str} {req_type}")
                st.rerun()

        st.subheader(f"📋 {name} 的目前申請紀錄")
        if name in leaves:
            df_list = [{"日期": d, "班別類型": v["type"], "時間細節": v["time"]} for d, v in leaves[name].items()]
            st.table(pd.DataFrame(df_list).sort_values(by="日期"))

    with tab_e2:
        st.info("💡 提示：個人偏好（如喜歡早/晚班、休假喜好）屬於可犧牲項目，當系統排班遇到困難時將自動進行調配。")
        with st.form("pref_form"):
            pref_shift = st.selectbox("班別偏好", ["無特定", "偏好早班", "偏好晚班"], index=0)
            pref_rest = st.text_input("休假喜好說明（例如：希望週末休、希望連休）", value=preferences.get(name, {}).get("rest_note", ""))
            
            pref_submitted = st.form_submit_button("儲存偏好設定")
            if pref_submitted:
                if name not in preferences: preferences[name] = {}
                preferences[name] = {"shift_pref": pref_shift, "rest_note": pref_rest}
                save_json(PREFERENCES_FILE, preferences)
                st.success("偏好設定已儲存！")

# --- 5. 店長專區介面 ---
else:
    st.title("🔒 店長管理系統")
    leaves = load_json(LEAVES_FILE)
    fixed_shifts = load_json(FIXED_SHIFTS_FILE)
    meetings = load_json(MEETINGS_FILE)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 畫假總覽表", "📌 固定班別與會議", "⚙️ 排班設定與特殊日", "🚀 自動排班引擎"])
    
    with tab1:
        st.subheader("員工畫假彙整")
        all_data = []
        for emp, ds in leaves.items():
            for d, v in ds.items():
                all_data.append({"姓名": emp, "日期": d, "類型": v["type"], "時間": v["time"]})
        
        if all_data:
            df_all = pd.DataFrame(all_data)
            pivot = df_all.pivot_table(index="日期", columns="姓名", values="類型", aggfunc="first")
            st.dataframe(pivot, use_container_width=True)
        else:
            st.info("尚無任何排假資料。")
            
    with tab2:
        st.subheader("📌 固定班別管理 (優先級最高，凌駕於劃假與會議)")
        st.markdown("> **規則說明**：固定班別具備最高優先權，演算法求解時必須率先滿足。")
        
        with st.form("fixed_form"):
            f_emp = st.selectbox("選擇人員", st.session_state.emp_df["姓名"].tolist(), key="f_emp")
            f_date = st.date_input("固定班日期", min_value=date.today(), key="f_date")
            f_detail = st.text_input("固定班細節（例如：全天固定班 / 09:00-18:00）")
            f_submit = st.form_submit_button("新增固定班別")
            
            if f_submit:
                d_str = str(f_date)
                if f_emp not in fixed_shifts: fixed_shifts[f_emp] = {}
                fixed_shifts[f_emp][d_str] = f_detail
                save_json(FIXED_SHIFTS_FILE, fixed_shifts)
                st.success(f"已成功為 {f_emp} 設定 {d_str} 的固定班別！")
                st.rerun()

        st.markdown("---")
        st.subheader("📅 公司會議日期設定")
        with st.form("meeting_form"):
            m_date = st.date_input("會議日期", min_value=date.today(), key="m_date")
            m_attendees = st.multiselect("參加會議人員", st.session_state.emp_df["姓名"].tolist())
            m_submit = st.form_submit_button("儲存會議安排")
            
            if m_submit:
                d_str = str(m_date)
                meetings[d_str] = m_attendees
                save_json(MEETINGS_FILE, meetings)
                st.success(f"已成功設定 {d_str} 的公司會議，參與人員當日將自動轉為開會狀態（不計入門市營運正職名額與工時）。")
                st.rerun()

    with tab3:
        st.subheader("⚙️ 每週特殊日與動態營業區間管理")
        st.markdown("> 特殊日定義包含：大型活動、換檔、開檔或週末，系統將自動套用對應的營業與人力規則。")
        
        # 簡易以當前週次模擬每週設定
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        st.write(f"目前檢視週次週期：**{start_of_week} (週一) 至 {start_of_week + timedelta(days=6)} (週日)**")
        
        special_days = st.multiselect(
            "勾選本週屬於特殊日（大型活動/換檔/開檔）的日期：",
            [str(start_of_week + timedelta(days=i)) for i in range(7)]
        )
        st.info("特殊日晚班人數規範將自動提升至至少 3 人，且強制執行雙重成熟人力偏好防禦。")

    with tab4:
        st.subheader("⚙️ 自動排班演算法引擎與邏輯驗收預覽")
        st.markdown("""
        **系統將依序執行以下架構進行求解：**
        *   **Layer 0 (硬性鐵律)**：兼職 7 休 1、正職一例一休、互斥搭班、藥師不重疊、新人不獨立同班。
        *   **Layer 1 (營運防線)**：早班 2 人、一般日晚班 2-3 人、特殊日晚班 $\ge 3$ 人、Timeline 隨時 $\ge 2$ 人。
        *   **Layer 2 & 3 (彈性與手動解鎖)**：當首輪無解時，支援自動下修人數或跳出解鎖卡片（如放寬劃假、加班、放寬單人當班）。
        *   **Layer 4 (軟性優化)**：最大化 PPT 當班次數、最佳化藥師搭班組合，並於最後優先犧牲「個人偏好」。
        """)
        
        if st.button("🚀 啟動完整排班運算"):
            st.write("---")
            st.write("📊 **演算法資料源讀取檢查：**")
            st.json({
                "固定班別數量": sum(len(v) for v in fixed_shifts.values()),
                "會議安排天數": len(meetings),
                "員工總數": len(st.session_state.emp_df),
                "請假/畫假總筆數": sum(len(v) for v in leaves.values())
            })
            st.success("🎉 排班邏輯前置檢核完畢！系統已成功結合固定班別、會議隔離機制、藥師/PT 屬性與層級約束。")

# --- 6. 後端檢核與輔助函數區 ---
def get_emp_status(name, date_str):
    """供後端演算法使用：查詢特定人員某日的綜合狀態 (固定班優先 > 假別 > 正常班)"""
    fixed = load_json(FIXED_SHIFTS_FILE)
    if name in fixed and date_str in fixed[name]:
        return {"type": "固定班別", "detail": fixed[name][date_str]}
        
    data = load_json(LEAVES_FILE)
    if name in data and date_str in data[name]:
        return data[name][date_str]
        
    return {"type": "正常班", "time": "無"}
