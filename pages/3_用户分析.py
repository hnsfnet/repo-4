import streamlit as st
import sys
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_loader import filter_by_time
from utils.analytics import calculate_rfm, calculate_retention, get_user_level_orders
from utils.exporter import get_report_title, export_to_excel, generate_html_report, export_html_report, get_download_buttons

st.set_page_config(
    page_title="用户分析 - 数析坊",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    .stMetric { background: white; padding: 1rem; border-radius: 12px;
                 box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    .export-area {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #7dd3fc;
        margin-bottom: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("👥 用户行为分析")

if 'clean_data' not in st.session_state:
    st.warning("⚠️ 数据尚未加载，请先返回首页加载数据")
    st.stop()

cleaned_df = st.session_state.clean_data
full_df = cleaned_df.copy()

if 'start_date' not in st.session_state:
    ov = st.session_state.overview
    st.session_state.start_date = ov['起始日期'].date()
    st.session_state.end_date = ov['结束日期'].date()

with st.sidebar:
    st.header("📋 数据概览")
    ov = st.session_state.overview
    st.metric("总行数", f"{ov['总行数']:,}")
    st.metric("时间范围", ov['时间范围'])
    st.divider()

    st.subheader("📅 时间范围筛选")
    min_dt = ov['起始日期'].date()
    max_dt = ov['结束日期'].date()

    preset = st.selectbox(
        "快捷选择",
        options=["全部时间", "最近7天", "最近30天", "最近90天", "最近半年", "自定义"],
        index=5,
        key="user_preset"
    )
    if preset == "最近7天":
        sd, ed = max_dt - timedelta(days=7), max_dt
    elif preset == "最近30天":
        sd, ed = max_dt - timedelta(days=30), max_dt
    elif preset == "最近90天":
        sd, ed = max_dt - timedelta(days=90), max_dt
    elif preset == "最近半年":
        sd, ed = max_dt - timedelta(days=180), max_dt
    elif preset == "全部时间":
        sd, ed = min_dt, max_dt
    else:
        sd = st.session_state.start_date
        ed = st.session_state.end_date

    date_range = st.date_input(
        "分析时间范围",
        value=(sd, ed),
        min_value=min_dt,
        max_value=max_dt,
        key="user_date_range"
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_dt, max_dt

    st.divider()
    st.subheader("🏷️ 品类筛选")
    all_categories = sorted(cleaned_df['product_category'].unique())
    selected_categories = st.multiselect(
        "选择分析品类",
        options=all_categories,
        default=all_categories,
        key="user_category_filter"
    )

    st.divider()
    st.subheader("🎯 RFM 参数")
    rfm_analysis_date = st.date_input(
        "RFM 分析日期",
        value=end_date,
        min_value=min_dt,
        max_value=max_dt + timedelta(days=30),
        key="rfm_analysis_date"
    )

time_filtered = filter_by_time(cleaned_df, start_date, end_date)

if selected_categories:
    time_filtered = time_filtered[time_filtered['product_category'].isin(selected_categories)]

filtered_df = time_filtered

st.info(f"📅 当前分析区间：**{start_date.strftime('%Y-%m-%d')}** 至 **{end_date.strftime('%Y-%m-%d')}** | 共 **{len(filtered_df):,}** 条订单")
if selected_categories and len(selected_categories) < len(all_categories):
    st.caption(f"🏷️ 已选品类：{', '.join(selected_categories)}")

with st.container():
    st.markdown('<div class="export-area">', unsafe_allow_html=True)
    col_title, col_exp = st.columns([3, 1])
    with col_title:
        st.subheader("📤 报表导出")
        st.caption("导出当前页面的图表与数据，包含筛选条件")
    with col_exp:
        rfm_df, level_stats = calculate_rfm(filtered_df, rfm_analysis_date)
        retention_df, cohort_df = calculate_retention(filtered_df)

        rep_title, rep_subtitle = get_report_title(
            "用户分析", start_date, end_date,
            categories=selected_categories if len(selected_categories) < len(all_categories) else None
        )

        kpi_dict = {}
        figures_dict = {}
        tables_dict = {}
        summary_dfs = []
        sheet_names = []

        if not filtered_df.empty:
            total_users = filtered_df['user_id'].nunique()
            total_orders = len(filtered_df)
            avg_order = filtered_df['amount'].sum() / total_orders if total_orders > 0 else 0
            kpi_dict = {
                "分析用户数": f"{total_users:,} 人",
                "订单总数": f"{total_orders:,} 单",
                "平均客单价": f"¥{avg_order:,.2f}",
                "RFM 分析日": rfm_analysis_date.strftime('%Y-%m-%d')
            }

        if not level_stats.empty:
            fig_level = go.Figure()
            fig_level.add_trace(go.Bar(
                x=level_stats['用户等级'],
                y=level_stats['用户数'],
                marker_color=['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#94a3b8'],
                text=level_stats.apply(lambda x: f"{x['用户数']}人<br>{x['用户占比(%)']}%", axis=1),
                hovertemplate='等级: %{x}<br>用户数: %{y} 人<extra></extra>'
            ))
            fig_level.update_layout(title="用户等级分布", title_x=0.5, height=380)
            figures_dict["用户等级分布"] = fig_level
            tables_dict["用户等级统计"] = level_stats
            summary_dfs.append(level_stats)
            sheet_names.append("用户等级统计")

        if not rfm_df.empty:
            fig_rfm_scatter = px.scatter_3d(
                rfm_df,
                x='Recency',
                y='Frequency',
                z='Monetary',
                color='用户等级',
                color_discrete_map={
                    '高价值用户': '#22c55e',
                    '潜力用户': '#3b82f6',
                    '流失预警': '#f59e0b',
                    '沉睡用户': '#ef4444',
                    '普通用户': '#94a3b8'
                },
                hover_data=['user_id', 'RFM_Score'],
                opacity=0.7,
                size_max=8
            )
            fig_rfm_scatter.update_layout(
                title="RFM 三维分布",
                title_x=0.5,
                scene=dict(
                    xaxis_title='最近购买(天)',
                    yaxis_title='购买频次',
                    zaxis_title='消费金额(¥)'
                ),
                height=500
            )
            figures_dict["RFM 三维分布"] = fig_rfm_scatter
            tables_dict["用户 RFM 明细"] = rfm_df
            summary_dfs.append(rfm_df)
            sheet_names.append("RFM明细")

        if not retention_df.empty:
            fig_heatmap = go.Figure(data=go.Heatmap(
                z=retention_df.values,
                x=retention_df.columns,
                y=retention_df.index,
                colorscale='Blues',
                text=retention_df.values,
                texttemplate='%{text:.1f}%',
                hovertemplate='首次购买: %{y}<br>第 %{x} 月<br>留存率: %{z:.1f}%<extra></extra>',
                colorbar=dict(title="留存率(%)")
            ))
            fig_heatmap.update_layout(
                title="用户留存率热力图",
                title_x=0.5,
                xaxis_title="后续月份",
                yaxis_title="首次购买月份",
                height=450
            )
            figures_dict["用户留存热力图"] = fig_heatmap
            tables_dict["留存率矩阵"] = retention_df
            tables_dict["用户规模矩阵"] = cohort_df
            summary_dfs.append(retention_df)
            summary_dfs.append(cohort_df)
            sheet_names.append("留存率矩阵")
            sheet_names.append("用户规模矩阵")

        html_report = generate_html_report(
            "用户分析", rep_title, rep_subtitle, kpi_dict,
            figures_dict, tables_dict
        )
        excel_bytes = export_to_excel(
            filtered_df, summary_dfs, sheet_names,
            title=f"{rep_title} - {rep_subtitle}"
        )

        with st.popover("📥 导出报表", use_container_width=True):
            get_download_buttons(
                "用户分析",
                export_html_report(html_report),
                excel_bytes,
                start_date, end_date,
                categories=selected_categories if len(selected_categories) < len(all_categories) else None
            )
    st.markdown('</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📊 RFM 分析", "🔥 用户留存分析"])

with tab1:
    st.subheader("📊 RFM 用户价值分析")

    if filtered_df.empty:
        st.warning("所选时间段内无数据")
    else:
        rfm_df, level_stats = calculate_rfm(filtered_df, rfm_analysis_date)

        if not level_stats.empty:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("👥 分析用户数", f"{len(rfm_df):,} 人")
            m2.metric("⭐ 高价值用户",
                      f"{level_stats[level_stats['用户等级'] == '高价值用户']['用户数'].sum():,} 人" if '高价值用户' in level_stats['用户等级'].values else "0 人")
            m3.metric("⚠️ 流失预警",
                      f"{level_stats[level_stats['用户等级'] == '流失预警']['用户数'].sum():,} 人" if '流失预警' in level_stats['用户等级'].values else "0 人")
            m4.metric("💤 沉睡用户",
                      f"{level_stats[level_stats['用户等级'] == '沉睡用户']['用户数'].sum():,} 人" if '沉睡用户' in level_stats['用户等级'].values else "0 人")

            st.divider()

            c1, c2 = st.columns([1, 1.5])

            with c1:
                fig_level = go.Figure()
                level_order = ['高价值用户', '潜力用户', '流失预警', '沉睡用户', '普通用户']
                level_colors = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#94a3b8']
                plot_levels = [l for l in level_order if l in level_stats['用户等级'].values]
                plot_colors = [level_colors[level_order.index(l)] for l in plot_levels]

                fig_level.add_trace(go.Bar(
                    x=plot_levels,
                    y=[level_stats[level_stats['用户等级'] == l]['用户数'].values[0] for l in plot_levels],
                    marker_color=plot_colors,
                    text=[f"{level_stats[level_stats['用户等级'] == l]['用户数'].values[0]} 人<br>{level_stats[level_stats['用户等级'] == l]['用户占比(%)'].values[0]}%" for l in plot_levels],
                    hovertemplate='等级: %{x}<br>用户数: %{y} 人<extra></extra>'
                ))
                fig_level.update_layout(
                    title="各等级用户数量分布",
                    title_x=0.5,
                    height=380,
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    yaxis_showgrid=True, yaxis_gridcolor='#f1f5f9'
                )
                st.plotly_chart(fig_level, use_container_width=True)

                fig_level_pie = px.pie(
                    level_stats,
                    values='消费占比(%)',
                    names='用户等级',
                    color='用户等级',
                    color_discrete_map=dict(zip(level_order, level_colors)),
                    hole=0.45,
                    title='各等级消费贡献占比'
                )
                fig_level_pie.update_traces(textposition='inside', textinfo='label+percent')
                fig_level_pie.update_layout(height=380, title_x=0.5)
                st.plotly_chart(fig_level_pie, use_container_width=True)

            with c2:
                fig_rfm_scatter = px.scatter_3d(
                    rfm_df,
                    x='Recency',
                    y='Frequency',
                    z='Monetary',
                    color='用户等级',
                    color_discrete_map=dict(zip(level_order, level_colors)),
                    hover_data={
                        'user_id': True,
                        'Recency': ':,.0f',
                        'Frequency': ':,.0f',
                        'Monetary': ':,.2f',
                        'RFM_Score': True,
                        '用户等级': True
                    },
                    opacity=0.7,
                    size_max=8
                )
                fig_rfm_scatter.update_layout(
                    title="RFM 三维分布（点击图例可筛选）",
                    title_x=0.5,
                    scene=dict(
                        xaxis_title='最近购买 (天)',
                        yaxis_title='购买频次 (次)',
                        zaxis_title='消费金额 (¥)'
                    ),
                    height=780,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_rfm_scatter, use_container_width=True)

            st.divider()
            st.subheader("🔍 等级下钻")
            selected_level = st.selectbox(
                "选择用户等级查看详情",
                options=plot_levels,
                key="drill_down_level"
            )

            if selected_level:
                level_orders = get_user_level_orders(filtered_df, rfm_df, selected_level)
                level_users = rfm_df[rfm_df['用户等级'] == selected_level]

                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.metric("该等级用户数", f"{len(level_users):,} 人")
                sc2.metric("总消费金额", f"¥{level_users['Monetary'].sum():,.0f}")
                sc3.metric("平均消费", f"¥{level_users['Monetary'].mean():,.0f}")
                sc4.metric("平均频次", f"{level_users['Frequency'].mean():.1f} 次")

                st.markdown(f"#### 📋 {selected_level} - 订单明细（TOP 50）")
                st.dataframe(
                    level_orders.head(50),
                    hide_index=True,
                    use_container_width=True
                )

            st.divider()
            st.markdown("#### 📑 RFM 评分明细")
            show_rfm = rfm_df[['user_id', 'Recency', 'Frequency', 'Monetary',
                             'R_Score', 'F_Score', 'M_Score', 'RFM_Score', '用户等级']].copy()
            show_rfm.columns = ['用户ID', '最近购买(天)', '购买频次(次)', '消费金额(¥)',
                                'R评分', 'F评分', 'M评分', 'RFM总分', '用户等级']
            show_rfm = show_rfm.sort_values('RFM总分', ascending=False)
            st.dataframe(show_rfm, hide_index=True, use_container_width=True)

with tab2:
    st.subheader("🔥 用户留存分析")

    if filtered_df.empty:
        st.warning("所选时间段内无数据")
    else:
        retention_df, cohort_df = calculate_retention(filtered_df)

        if retention_df.empty or cohort_df.empty:
            st.info("⚠️ 当前数据不足以计算留存率，请扩大时间范围或更换筛选条件")
        else:
            rm1, rm2, rm3 = st.columns(3)
            rm1.metric("首次购买用户分组", f"{len(retention_df)} 组")
            avg_retention = retention_df.iloc[:, 1:].mean().mean() if len(retention_df.columns) > 1 else 0
            rm2.metric("平均次月留存率", f"{avg_retention:.2f}%")
            new_users = cohort_df.iloc[:, 0].sum()
            rm3.metric("总新用户数", f"{new_users:,} 人")

            st.divider()
            rc1, rc2 = st.columns(2)

            with rc1:
                fig_heatmap = go.Figure(data=go.Heatmap(
                    z=retention_df.values,
                    x=[f"第{c}月" for c in retention_df.columns],
                    y=retention_df.index,
                    colorscale='Blues',
                    text=retention_df.values,
                    texttemplate='%{text:.1f}%',
                    hovertemplate='首次购买: %{y}<br>时间: %{x}<br>留存率: %{z:.1f}%<extra></extra>',
                    colorbar=dict(title="留存率(%)")
                ))
                fig_heatmap.update_layout(
                    title="用户留存率热力图",
                    title_x=0.5,
                    xaxis_title="首次购买后的时间",
                    yaxis_title="首次购买月份",
                    height=500,
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)

            with rc2:
                fig_cohort = go.Figure(data=go.Heatmap(
                    z=cohort_df.values,
                    x=[f"第{c}月" for c in cohort_df.columns],
                    y=cohort_df.index,
                    colorscale='Greens',
                    text=cohort_df.values,
                    texttemplate='%{text}',
                    hovertemplate='首次购买: %{y}<br>时间: %{x}<br>活跃用户: %{text} 人<extra></extra>',
                    colorbar=dict(title="用户数")
                ))
                fig_cohort.update_layout(
                    title="各月活跃用户规模",
                    title_x=0.5,
                    xaxis_title="首次购买后的时间",
                    yaxis_title="首次购买月份",
                    height=500,
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )
                st.plotly_chart(fig_cohort, use_container_width=True)

            st.divider()
            st.markdown("#### 📋 留存率数据明细")
            display_ret = retention_df.copy()
            display_ret.columns = [f"第{c}月留存(%)" for c in display_ret.columns]
            display_ret.index.name = "首次购买月份"
            st.dataframe(display_ret, use_container_width=True)

            st.markdown("#### 📋 用户规模数据明细")
            display_cohort = cohort_df.copy()
            display_cohort.columns = [f"第{c}月活跃(人)" for c in display_cohort.columns]
            display_cohort.index.name = "首次购买月份"
            st.dataframe(display_cohort, use_container_width=True)
