import streamlit as st
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.filter_manager import FilterManager
from services.user_service import UserService
from utils.exporter import get_report_title, export_to_excel, generate_html_report, export_html_report, get_download_buttons
from charts.chart_components import BarChart, PieChart, HeatmapChart, Scatter3DChart
from utils.config import get as cfg

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
        padding: 1rem; border-radius: 10px; border: 1px solid #7dd3fc;
        margin-bottom: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("👥 用户行为分析")

if 'clean_data' not in st.session_state:
    st.warning("⚠️ 数据尚未加载，请先返回首页加载数据")
    st.stop()

FilterManager.init_session_defaults(st.session_state.overview)
filters = FilterManager.render_sidebar("user", show_rfm_date=True)
filtered_df = FilterManager.get_filtered_df(filters['start_date'], filters['end_date'], filters['categories'])

start_date = filters['start_date']
end_date = filters['end_date']
selected_categories = filters['categories']
all_categories = filters['all_categories']
rfm_analysis_date = filters['rfm_analysis_date']

svc = UserService(filtered_df, rfm_analysis_date)

st.info(f"📅 当前分析区间：**{start_date.strftime('%Y-%m-%d')}** 至 **{end_date.strftime('%Y-%m-%d')}** | 共 **{len(filtered_df):,}** 条订单")
if len(selected_categories) < len(all_categories):
    st.caption(f"🏷️ 已选品类：{', '.join(selected_categories)}")

with st.container():
    gradient_start = cfg('theme.colors.gradient_start', '#f0f9ff')
    gradient_end = cfg('theme.colors.gradient_end', '#e0f2fe')
    gradient_border = cfg('theme.colors.gradient_border', '#7dd3fc')
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {gradient_start} 0%, {gradient_end} 100%); padding: 1rem; border-radius: 10px; border: 1px solid {gradient_border}; margin-bottom: 1.5rem;">
    """, unsafe_allow_html=True)
    col_title, col_exp = st.columns([3, 1])
    with col_title:
        st.subheader("📤 报表导出")
        st.caption("导出当前页面的图表与数据，包含筛选条件")
    with col_exp:
        rfm_df, level_stats = svc.get_rfm()
        retention_df, cohort_df = svc.get_retention()

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
            level_order = ['高价值用户', '潜力用户', '流失预警', '沉睡用户', '普通用户']
            level_colors_map = cfg('theme.colors.level_colors', {})
            plot_levels = [l for l in level_order if l in level_stats['用户等级'].values]
            plot_colors = [level_colors_map.get(l, '#94a3b8') for l in plot_levels]

            fig_level = BarChart("用户等级分布", height=380)
            fig_level.fig.add_trace(__import__('plotly.graph_objects', fromlist=['Bar']).Bar(
                x=plot_levels,
                y=[level_stats[level_stats['用户等级'] == l]['用户数'].values[0] for l in plot_levels],
                marker_color=plot_colors,
                text=[f"{level_stats[level_stats['用户等级'] == l]['用户数'].values[0]}人"
                      for l in plot_levels],
                hovertemplate='等级: %{x}<br>用户数: %{y} 人<extra></extra>'
            ))
            figures_dict["用户等级分布"] = fig_level.fig
            tables_dict["用户等级统计"] = level_stats
            summary_dfs.append(level_stats)
            sheet_names.append("用户等级统计")

        if not rfm_df.empty:
            rfm_display, _ = UserService.sample_rfm_for_display(rfm_df)
            fig_rfm = Scatter3DChart("RFM 三维分布", height=500)
            fig_rfm.add_scatter_3d(
                rfm_display, 'Recency', 'Frequency', 'Monetary',
                color_col='用户等级',
                hover_data={'user_id': True, 'RFM_Score': True}
            )
            figures_dict["RFM 三维分布"] = fig_rfm.fig
            tables_dict["用户 RFM 明细"] = rfm_df
            summary_dfs.append(rfm_df)
            sheet_names.append("RFM明细")

        if not retention_df.empty:
            fig_heatmap = HeatmapChart("用户留存率热力图", height=450)
            fig_heatmap.add_heatmap_from_df(retention_df, colorbar_title="留存率(%)")
            figures_dict["用户留存热力图"] = fig_heatmap.fig
            tables_dict["留存率矩阵"] = retention_df
            tables_dict["用户规模矩阵"] = cohort_df
            summary_dfs.append(retention_df)
            summary_dfs.append(cohort_df)
            sheet_names.append("留存率矩阵")
            sheet_names.append("用户规模矩阵")

        html_report = generate_html_report(
            "用户分析", rep_title, rep_subtitle, kpi_dict, figures_dict, tables_dict
        )
        excel_bytes = export_to_excel(
            filtered_df, summary_dfs, sheet_names,
            title=f"{rep_title} - {rep_subtitle}"
        )
        with st.popover("📥 导出报表", use_container_width=True):
            get_download_buttons(
                "用户分析", export_html_report(html_report), excel_bytes,
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
        rfm_df, level_stats = svc.get_rfm()
        level_order = ['高价值用户', '潜力用户', '流失预警', '沉睡用户', '普通用户']
        level_colors_map = cfg('theme.colors.level_colors', {})
        level_colors = [level_colors_map.get(l, '#94a3b8') for l in level_order]

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
                plot_levels = [l for l in level_order if l in level_stats['用户等级'].values]
                plot_colors = [level_colors[level_order.index(l)] for l in plot_levels]

                fig_level = BarChart("各等级用户数量分布", height=380)
                fig_level.fig.add_trace(__import__('plotly.graph_objects', fromlist=['Bar']).Bar(
                    x=plot_levels,
                    y=[level_stats[level_stats['用户等级'] == l]['用户数'].values[0] for l in plot_levels],
                    marker_color=plot_colors,
                    text=[f"{level_stats[level_stats['用户等级'] == l]['用户数'].values[0]} 人<br>{level_stats[level_stats['用户等级'] == l]['用户占比(%)'].values[0]}%"
                          for l in plot_levels],
                    hovertemplate='等级: %{x}<br>用户数: %{y} 人<extra></extra>'
                ))
                fig_level.render()

                PieChart('各等级消费贡献占比', height=380).add_pie(
                    labels=level_stats['用户等级'],
                    values=level_stats['消费占比(%)'],
                    color_map=[level_colors_map.get(l, '#94a3b8') for l in level_stats['用户等级']]
                ).render()

            with c2:
                rfm_plot_df, rfm_was_sampled = UserService.sample_rfm_for_display(rfm_df)
                scatter_title = "RFM 三维分布（点击图例可筛选）"
                if rfm_was_sampled:
                    scatter_title += f" — 采样展示 {len(rfm_plot_df):,}/{len(rfm_df):,} 条"
                Scatter3DChart(scatter_title, height=780).add_scatter_3d(
                    rfm_plot_df, 'Recency', 'Frequency', 'Monetary',
                    color_col='用户等级',
                    hover_data={
                        'user_id': True, 'Recency': ':,.0f',
                        'Frequency': ':,.0f', 'Monetary': ':,.2f',
                        'RFM_Score': True, '用户等级': True
                    }
                ).render(x_title='最近购买 (天)', y_title='购买频次 (次)', z_title='消费金额 (¥)')

            st.divider()
            st.subheader("🔍 等级下钻")
            selected_level = st.selectbox(
                "选择用户等级查看详情",
                options=plot_levels,
                key="drill_down_level"
            )

            if selected_level:
                level_orders = svc.get_user_level_orders(rfm_df, selected_level)
                level_users = rfm_df[rfm_df['用户等级'] == selected_level]

                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.metric("该等级用户数", f"{len(level_users):,} 人")
                sc2.metric("总消费金额", f"¥{level_users['Monetary'].sum():,.0f}")
                sc3.metric("平均消费", f"¥{level_users['Monetary'].mean():,.0f}")
                sc4.metric("平均频次", f"{level_users['Frequency'].mean():.1f} 次")

                st.markdown(f"#### 📋 {selected_level} - 订单明细（TOP 50）")
                st.dataframe(level_orders.head(50), hide_index=True, use_container_width=True)

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
        retention_df, cohort_df = svc.get_retention()

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
                HeatmapChart("用户留存率热力图", height=500, colorscale='Blues').add_heatmap_from_df(
                    retention_df, colorbar_title="留存率(%)"
                ).render(x_title="首次购买后的时间", y_title="首次购买月份")

            with rc2:
                HeatmapChart("各月活跃用户规模", height=500, colorscale='Greens').add_heatmap_from_df(
                    cohort_df, colorbar_title="用户数"
                ).render(x_title="首次购买后的时间", y_title="首次购买月份")

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
