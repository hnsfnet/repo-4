import streamlit as st
import pandas as pd
from datetime import timedelta
from utils.config import get as cfg


class FilterManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def init_session_defaults(overview):
        if 'start_date' not in st.session_state:
            st.session_state.start_date = overview['起始日期'].date()
            st.session_state.end_date = overview['结束日期'].date()
        if 'category_filter' not in st.session_state:
            st.session_state.category_filter = []

    @staticmethod
    def get_clean_data():
        return st.session_state.get('clean_data', pd.DataFrame())

    @staticmethod
    def get_overview():
        return st.session_state.get('overview', {})

    @staticmethod
    def get_all_categories():
        df = FilterManager.get_clean_data()
        if df.empty:
            return []
        return sorted(df['product_category'].dropna().unique().tolist())

    @staticmethod
    def render_sidebar(page_key, show_compare=False, show_rfm_date=False):
        ov = FilterManager.get_overview()
        if not ov:
            return {}

        cleaned_df = FilterManager.get_clean_data()
        all_categories = FilterManager.get_all_categories()

        result = {'compare_mode': False, 'rfm_analysis_date': None}

        with st.sidebar:
            st.header("📋 数据概览")
            st.metric("总行数", f"{ov.get('总行数', 0):,}")
            st.metric("时间范围", ov.get('时间范围', '-'))
            st.divider()

            st.subheader("📅 时间范围筛选")
            min_dt = ov['起始日期'].date()
            max_dt = ov['结束日期'].date()

            presets = cfg('sidebar.presets', [])
            preset_labels = [p['label'] for p in presets]
            default_label = cfg('sidebar.default_preset', '自定义')
            default_idx = preset_labels.index(default_label) if default_label in preset_labels else len(preset_labels) - 1

            preset = st.selectbox(
                "快捷选择",
                options=preset_labels,
                index=default_idx,
                key=f"{page_key}_preset"
            )

            sd, ed = None, None
            for p in presets:
                if p['label'] == preset:
                    if p['days'] == 0:
                        sd, ed = min_dt, max_dt
                    elif p['days'] > 0:
                        sd = max_dt - timedelta(days=p['days'])
                        ed = max_dt
                    break
            if sd is None:
                sd = st.session_state.get('start_date', min_dt)
                ed = st.session_state.get('end_date', max_dt)

            date_range = st.date_input(
                "分析时间范围",
                value=(sd, ed),
                min_value=min_dt,
                max_value=max_dt,
                key=f"{page_key}_date_range"
            )
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = date_range
            else:
                start_date, end_date = min_dt, max_dt

            st.session_state.start_date = start_date
            st.session_state.end_date = end_date
            result['start_date'] = start_date
            result['end_date'] = end_date

            st.divider()
            st.subheader("🏷️ 品类筛选")
            stored_cats = st.session_state.get('category_filter', all_categories)
            valid_default = [c for c in stored_cats if c in all_categories]
            if not valid_default:
                valid_default = all_categories

            selected_categories = st.multiselect(
                "选择品类",
                options=all_categories,
                default=valid_default,
                key=f"{page_key}_category"
            )
            if not selected_categories:
                selected_categories = all_categories
            st.session_state.category_filter = selected_categories
            result['categories'] = selected_categories
            result['all_categories'] = all_categories

            if show_compare:
                st.divider()
                st.subheader("🎯 对比维度")
                result['compare_mode'] = st.checkbox("启用环比对比", value=True, key=f"{page_key}_compare")

            if show_rfm_date:
                st.divider()
                st.subheader("🎯 RFM 参数")
                result['rfm_analysis_date'] = st.date_input(
                    "RFM 分析日期",
                    value=end_date,
                    min_value=min_dt,
                    max_value=max_dt + timedelta(days=30),
                    key=f"{page_key}_rfm_date"
                )

        return result

    @staticmethod
    def get_filtered_df(start_date=None, end_date=None, categories=None):
        cleaned_df = FilterManager.get_clean_data()
        if cleaned_df.empty:
            return cleaned_df

        if start_date is None:
            start_date = st.session_state.get('start_date')
        if end_date is None:
            end_date = st.session_state.get('end_date')

        result = cleaned_df.copy()
        if start_date and end_date:
            mask = (result['order_time'].dt.date >= start_date) & (result['order_time'].dt.date <= end_date)
            result = result[mask]

        all_cats = cleaned_df['product_category'].dropna().unique().tolist()
        if categories and set(categories) != set(all_cats):
            result = result[result['product_category'].isin(categories)]

        st.session_state.filtered_df = result
        return result

    @staticmethod
    def get_prev_df(start_date, end_date, categories=None):
        full_df = FilterManager.get_clean_data()
        if full_df.empty or start_date is None or end_date is None:
            return pd.DataFrame()
        current_span = (end_date - start_date).days
        prev_start = start_date - timedelta(days=current_span + 1)
        prev_end = start_date - timedelta(days=1)
        prev_df = full_df[(full_df['order_time'].dt.date >= prev_start) &
                          (full_df['order_time'].dt.date <= prev_end)]
        if categories:
            all_cats = full_df['product_category'].dropna().unique().tolist()
            if set(categories) != set(all_cats):
                prev_df = prev_df[prev_df['product_category'].isin(categories)]
        return prev_df
