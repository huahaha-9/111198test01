with tab9:
    st.subheader("🚀 自動排班與手動調整審核")
    schedule_week_str = st.text_input("排班週次識別 (例如：2026-W34)：", value="2026-W34")

    if st.button("🚀 開始自動求解排班", type="primary"):
        # 模擬自動排班演算法產出的結果
        st.session_state.temp_schedule = pd.DataFrame([
            {"日期": "週一", "早班": "呈, 花藥", "晚班": "桂, 邱藥"},
            {"日期": "週二", "早班": "呈, 亭", "晚班": "桂, 品"},
            {"日期": "週三", "早班": "呈, 花藥", "晚班": "桂, 邱藥"},
            {"日期": "週四", "早班": "呈, 亭", "晚班": "桂, 品"},
            {"日期": "週五", "早班": "呈, 花藥", "晚班": "桂, 邱藥"},
            {"日期": "週六", "早班": "呈, 亭", "晚班": "桂, 品"},
            {"日期": "週日", "早班": "呈, 花藥", "晚班": "桂, 邱藥"}
        ])
        st.success(f"✅ 【{schedule_week_str}】自動排班計算完成！")

    if 'temp_schedule' in st.session_state:
        st.markdown(f"#### ✏️ 【{schedule_week_str}】班表手動調整與全規則防呆審核區")
        edited_schedule = st.data_editor(st.session_state.temp_schedule, num_rows="dynamic", key="manual_schedule_editor", use_container_width=True)
        
        st.divider()
        if st.button("💾 執行所有核心原則、會議與互斥檢查並發佈", type="primary"):
            has_error = False
            error_messages = []
            schedule_rows = edited_schedule.to_dict(orient="records")
            emp_df_current = st.session_state.emp_df
            conflict_rules = load_json(CONFLICT_FILE, [])
            meeting_rules = load_json(MEETING_FILE, {})
            
            # 建立人員屬性 Map
            emp_info_map = {}
            for _, r in emp_df_current.iterrows():
                emp_info_map[r["姓名"]] = {
                    "類型": r["類型"],
                    "藥師": bool(r["藥師"]),
                    "成熟人力": bool(r["成熟人力"])
                }

            def check_staff_rules(name_list, is_night, day_name, meeting_emps):
                """核心規則檢查邏輯"""
                errs = []
                effective_list = [e for e in name_list if e not in meeting_emps]
                
                # [1-05] 嚴禁全新人同班：檢查是否有成熟人力
                has_mature = any(emp_info_map.get(e, {}).get("成熟人力", False) for e in name_list)
                if not has_mature:
                    errs.append(f"❌ 【{day_name}】{('晚班' if is_night else '早班')} 全為新人，缺乏成熟人力指導！")

                # [1-16] 藥師晚班搭班防線
                pt_pharmacists = [e for e in name_list if emp_info_map.get(e, {}).get("藥師") and emp_info_map.get(e, {}).get("類型") == "PT"]
                if is_night and pt_pharmacists:
                    has_full = any(emp_info_map.get(e, {}).get("類型") == "正職" for e in effective_list)
                    has_mature_ppt = any(e for e in effective_list if emp_info_map.get(e, {}).get("成熟人力", True) and emp_info_map.get(e, {}).get("類型") != "PT")
                    if not has_full and not has_mature_ppt:
                        errs.append(f"❌ 【{day_name}】晚班有 PT 藥師 {pt_pharmacists}，必須搭配正職或成熟 PPT！")
                return errs

            # 逐日規則檢查
            history_data = load_json(HISTORY_14D_FILE, [])
            for row in schedule_rows:
                day_name = row.get("日期", "")
                m_list = [x.strip() for x in str(row.get("早班", "")).replace("，", ",").split(",") if x.strip()]
                n_list = [x.strip() for x in str(row.get("晚班", "")).replace("，", ",").split(",") if x.strip()]
                
                # [1-08/09] 人數規範 & [1-07] 不重複
                if len(m_list) != 2: error_messages.append(f"❌ 【{day_name}】早班必須剛好 2 人！")
                if not (2 <= len(n_list) <= 4): error_messages.append(f"❌ 【{day_name}】晚班需 2-4 人！")
                if set(m_list) & set(n_list): error_messages.append(f"❌ 【{day_name}】人員重複排班！")

                # 會議與成熟人力/藥師檢查
                meeting_emps = meeting_rules.get(day_name, [])
                error_messages.extend(check_staff_rules(m_list, False, day_name, meeting_emps))
                error_messages.extend(check_staff_rules(n_list, True, day_name, meeting_emps))

                # [1-15] 藥師不重疊
                if len([e for e in m_list if emp_info_map.get(e, {}).get("藥師")]) > 1: error_messages.append(f"❌ 【{day_name}】早班藥師重複！")
                if len([e for e in n_list if emp_info_map.get(e, {}).get("藥師")]) > 1: error_messages.append(f"❌ 【{day_name}】晚班藥師重複！")

                # [1-14] 互斥規則
                for c in conflict_rules:
                    if c[0] in m_list and c[1] in m_list: error_messages.append(f"❌ 【{day_name}】早班違規：{c[0]} 與 {c[1]} 互斥！")
                    if c[0] in n_list and c[1] in n_list: error_messages.append(f"❌ 【{day_name}】晚班違規：{c[0]} 與 {c[1]} 互斥！")

            # [1-01] 7休1 與 [2-05] 晚接早檢查
            for emp in EMPLOYEES:
                consecutive_count = 0
                last_was_night = False
                for idx, row in enumerate(schedule_rows):
                    day_name = row.get("日期", "")
                    m_list = [x.strip() for x in str(row.get("早班", "")).replace("，", ",").split(",")]
                    n_list = [x.strip() for x in str(row.get("晚班", "")).replace("，", ",").split(",")]
                    
                    if emp in m_list or emp in n_list:
                        if last_was_night and emp in m_list:
                            error_messages.append(f"⚠️ 違規【不能晚接早】：{emp} 前一天晚班，隔天【{day_name}】早班！")
                        consecutive_count += 1
                        if consecutive_count > 6:
                            error_messages.append(f"⚠️ 違規【7休1】：{emp} 連續上班超過 6 天！")
                        last_was_night = (emp in n_list)
                    else:
                        consecutive_count = 0
                        last_was_night = False

            if error_messages:
                st.error("⚠️ **排班規則檢查未通過：**")
                for err in list(set(error_messages)): st.markdown(f"- {err}")
            else:
                final_sched_all = load_json(FINAL_SCHEDULE_FILE, {})
                final_sched_all[schedule_week_str] = schedule_rows
                save_json(FINAL_SCHEDULE_FILE, final_sched_all)
                st.success(f"🎉 **完全符合規範！** 【{schedule_week_str}】班表已發佈！")