import streamlit as st
import sys
import os
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.data_loader import (
    load_raw_data, clean_data, detect_missing_values, detect_outliers,
    get_data_overview
)

st.set_page_config(
    page_title="数析坊 - 电商数据分析看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main {
        background-color: #f8fafc;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 {
        color: #1e293b;
    }
    .metric-card {
        background: white;
        padding: 1.2rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 数析坊")
st.caption("电商数据分析看板 · 数据驱动决策")

with st.spinner("正在加载并清洗数据..."):
    if 'raw_data' not in st.session_state:
        raw_df, err = load_raw_data()
        if err:
            st.error(f"❌ 数据加载失败：{err}")
            st.info("请确保 data/ 目录下存在 orders.csv 文件，包含以下字段：order_id, user_id, product_category, amount, quantity, order_time, region, channel")
            st.stop()
        st.session_state.raw_data = raw_df
        st.session_state.missing_stats = detect_missing_values(raw_df)

        try:
            outliers_df, lower_bound, upper_bound = detect_outliers(raw_df, 'amount')
        except Exception:
            outliers_df, lower_bound, upper_bound = None, None, None
        st.session_state.outliers = outliers_df
        st.session_state.outlier_bounds = (lower_bound, upper_bound)

        cleaned_df = clean_data(raw_df)
        st.session_state.clean_data = cleaned_df
        st.session_state.overview = get_data_overview(cleaned_df)
    else:
        raw_df = st.session_state.raw_data
        cleaned_df = st.session_state.clean_data

with st.sidebar:
    st.header("📋 数据概览")
    if 'overview' in st.session_state and st.session_state.overview:
        ov = st.session_state.overview
        st.info("✅ 数据已加载并缓存")

        st.metric("总行数", f"{ov['总行数']:,}")
        st.metric("时间范围", ov['时间范围'])

        col1, col2 = st.columns(2)
        col1.metric("用户数", f"{ov['用户数']:,}")
        col2.metric("订单数", f"{ov['订单数']:,}")
        col3, col4 = st.columns(2)
        col3.metric("品类数", ov['品类数'])
        col4.metric("地区数", ov['地区数'])

        st.divider()

    st.subheader("⚠️ 缺失值统计")
    ms = st.session_state.get('missing_stats')
    if ms is not None and not ms.empty:
        st.dataframe(ms, hide_index=True, use_container_width=True)
    else:
        st.success("无缺失值 ✅")

    st.subheader("🔍 异常值检测")
    outliers = st.session_state.get('outliers')
    lower_bound, upper_bound = st.session_state.get('outlier_bounds', (None, None))
    if outliers is not None and not outliers.empty:
        st.warning(f"检测到 {len(outliers)} 条异常记录 (IQR×3规则)")
        if lower_bound is not None and upper_bound is not None:
            st.caption(f"有效金额范围: ¥{lower_bound:.2f} ~ ¥{upper_bound:.2f}")
        with st.expander("查看异常记录"):
            st.dataframe(outliers[['order_id', 'amount', 'product_category', 'order_time']],
                         hide_index=True, use_container_width=True)
    else:
        st.success("无异常值 ✅")

    st.divider()
    st.subheader("📅 时间范围筛选")
    if 'overview' in st.session_state and st.session_state.overview:
        min_dt = ov['起始日期'].date()
        max_dt = ov['结束日期'].date()
        default_start = min_dt
        default_end = max_dt
        if (max_dt - min_dt).days > 90:
            default_start = max_dt - timedelta(days=90)

        date_range = st.date_input(
            "选择分析时间范围",
            value=(default_start, default_end),
            min_value=min_dt,
            max_value=max_dt,
            key="sidebar_date_range"
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            st.session_state.start_date = date_range[0]
            st.session_state.end_date = date_range[1]

st.success(f"🎉 数据加载完成！共清洗出 {len(cleaned_df)} 条有效订单记录。请在左侧选择页面进入分析。")

tab1, tab2, tab3 = st.tabs(["📑 项目说明", "🔍 数据预览", "🛠️ 功能导航"])

with tab1:
    st.markdown("""
    ## 关于数析坊

    **数析坊** 是一个基于 Python + Streamlit + Pandas + Plotly 的电商数据分析看板，
    提供从数据加载、清洗到多维度可视化分析的一站式解决方案。

    ### 核心功能
    - **数据清洗引擎**：自动检测并处理缺失值、异常值、重复值
    - **销售概览看板**：核心KPI、趋势分析、品类&地区分布
    - **多维度分析**：品类、渠道、地区三大维度深度剖析

    ### 技术栈
    - 🐍 Python + Pandas：数据处理与分析
    - 🚀 Streamlit：交互式Web框架
    - 📈 Plotly：交互式可视化图表
    """)

with tab2:
    st.subheader("原始数据预览")
    st.dataframe(st.session_state.raw_data.head(20), hide_index=True, use_container_width=True)
    st.subheader("清洗后数据预览")
    st.dataframe(st.session_state.clean_data.head(20), hide_index=True, use_container_width=True)

with tab3:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📊 [销售概览看板](销售概览)")
        st.caption("""
        - 核心指标卡片（总销售额、总订单数、客单价、环比增长率）
        - 销售额趋势折线图（日/周/月切换）
        - 品类销售占比饼图
        - 地区销售分布图
        """)
    with col2:
        st.markdown("### 🔬 [多维度分析](多维度分析)")
        st.caption("""
        - 品类分析：销售额/订单量对比、环比变化瀑布图
        - 渠道分析：转化漏斗、ROI对比
        - 地区分析：各省排名、增速对比
        """)
