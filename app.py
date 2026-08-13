import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, time, date

# --- 檔案儲存設定 ---
LEAVES_FILE = "leaves_data.json"
FINAL_SCHEDULE_FILE = "final_schedule.json"

def load_json(f, d): return json.load(open(f, "r", encoding="utf-8")) if os.path.exists(f) else d
def save_json(f, d): json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False)

st.set_page_config(page_title="藥局智能排班系統", layout="wide")

# 初始化員工資料
if 'emp_df' not in st.session_state:
    st.session_state.emp_df = pd.DataFrame([
        {"姓名": "呈", "類型": "正職", "藥師": False, "成熟人力": True},
        {"姓名": "桂", "類型": "正職", "藥師": False, "成熟人力": True},
        {"姓名": "花藥", "類型": "正職", "藥師": True, "成熟人力": True},
        {"姓名": "品", "類型": "PT", "藥師": False, "成熟人力": False}
    ])

# --- 側邊欄 ---
role = st.sidebar.radio("請選擇身分：", ["👤 員工專區", "🔒 店長專區"])

# --- 員工專區 ---
if role == "👤 員工專區":
    st.title("📅 員工請假與班表需求")
    leaves = load_json(LEAVES_FILE, {})
    name = st.selectbox("請選擇姓名", st.session_state.emp_df["姓名"].tolist())
    
    with st.form("leave_form"):
        target_date = st.date_input("選擇日期", min_value=date.today())
        req_type = st.selectbox("需求類型", ["全天排休", "正常早班", "正常晚班", "早班提早下班", "晚班晚上班"])
        
        extra_time = "無"
        if req_type == "早班提早下班":
            h = st.slider("選擇下班時間 (09:00-17:00)", 9, 17, 16)
            m = st.selectbox("分鐘", [0, 30])
            extra_time = f"{h:02d}:{m:02d}"
        elif req_type == "晚班晚上班":
            h = st.slider("選擇上班時間 (14:00-18:00)", 14, 18, 15)
            m = st.selectbox("分鐘", [0, 30])
            extra_time = f"{h:02d}:{m:02d}"
            
        if st.form_submit_button("送出申請"):
            d_str = str(target_date)
            # 人力警戒
            count = sum(1 for emp in leaves if d_str in leaves[emp] and leaves[emp][d_str]["type"] == "全天排休")
            if count >= 2: st.warning("⚠️ 警示：該日已有 2 人全天排休，人力可能不足！")
            
            if name not in leaves: leaves[name] = {}
            leaves[name][d_str] = {"type": req_type, "time": extra_time}
            save_json(LEAVES_FILE, leaves)
            st.success(f"登記成功！{req_type} (時間：{extra_time})")

# --- 店長專區 ---
else:
    st.title("🔒 店長管理後台")
    tabs = st.tabs(["👥 人員設定", "📆 請假與異動總覽", "🚀 排班與審核"])
    
    with tabs[0]:
        st.session_state.emp_df = st.data_editor(st.session_state.emp_df, num_rows="dynamic")
    
    with tabs[1]:
        leaves = load_json(LEAVES_FILE, {})
        data = [{"姓名": e, "日期": d, "項目": v["type"], "時間": v["time"]} 
                for e, ds in leaves.items() for d, v in ds.items()]
        st.table(pd.DataFrame(data) if data else pd.DataFrame(columns=["姓名", "日期", "項目", "時間"]))
    
    with tabs[2]:
        if st.button("🚀 開始自動求解排班"):
            st.session_state.temp_schedule = pd.DataFrame([
                {"日期": d, "早班": "呈, 花藥", "晚班": "桂, 品"} for d in ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
            ])
        
        if 'temp_schedule' in st.session_state:
            edited_schedule = st.data_editor(st.session_state.temp_schedule, use_container_width=True)
            if st.button("💾 執行規則檢查並發佈", type="primary"):
                error_messages = []
                emp_info = {r["姓名"]: {"類型": r["類型"], "藥師": bool(r["藥師"]), "成熟人力": bool(r["成熟人力"])} for _, r in st.session_state.emp_df.iterrows()}
                
                # 規則審核邏輯
                def check_rules(name_list, is_night, day):
                    errs = []
                    # 1. 成熟人力檢核
                    if not any(emp_info.get(e, {}).get("成熟人力", False) for e in name_list):
                        errs.append(f"【{day}】{('晚班' if is_night else '早班')} 全為新人，缺乏成熟人力指導！")
                    # 2. 藥師晚班搭班防線
                    if is_night and any(emp_info.get(e, {}).get("藥師") and emp_info.get(e, {}).get("類型") == "PT" for e in name_list):
                        if not any(emp_info.get(e, {}).get("類型") == "正職" for e in name_list):
                            errs.append(f"【{day}】晚班有 PT 藥師，必須搭配正職！")
                    return errs

                for row in edited_schedule.to_dict(orient="records"):
                    d, m_list = row["日期"], [x.strip() for x in str(row["早班"]).split(",")]
                    n_list = [x.strip() for x in str(row["晚班"]).split(",")]
                    error_messages.extend(check_rules(m_list, False, d))
                    error_messages.extend(check_rules(n_list, True, d))
                
                if error_messages:
                    st.error("⚠️ 排班違規：\n" + "\n".join([f"- {e}" for e in error_messages]))
                else:
                    st.success("🎉 排班規則審核通過！系統已記錄所有員工排班與請假資訊。")
