import streamlit as st
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.filter_manager import FilterManager
from services.sales_service import SalesService
from utils.exporter import get_report_title, export_to_excel, generate_html_report, export_html_report, get_download_buttons
from charts.chart_components import LineChart, PieChart, BarChart
from utils.config import get as cfg

st.set_page_config(
    page_title="销售概览 - 数析坊",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    .stMetric { background: white; padding: 1rem; border-radius: 12px;
                 box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    .element-container > div > div > .stMetric { margin-top: 0 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 销售概览看板")

if 'clean_data' not in st.session_state:
    st.warning("⚠️ 数据尚未加载，请先返回首页加载数据")
    st.stop()

FilterManager.init_session_defaults(st.session_state.overview)
filters = FilterManager.render_sidebar("overview")
filtered_df = FilterManager.get_filtered_df(filters['start_date'], filters['end_date'], filters['categories'])
full_df = FilterManager.get_clean_data()
svc = SalesService(filtered_df, full_df)
kpi = svc.get_kpi()

start_date = filters['start_date']
end_date = filters['end_date']
selected_categories = filters['categories']
all_categories = filters['all_categories']

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
        rep_title, rep_subtitle = get_report_title(
            "销售概览", start_date, end_date,
            categories=selected_categories if len(selected_categories) < len(all_categories) else None
        )
        kpi_dict = {}
        figures_dict = {}
        tables_dict = {}
        summary_dfs = []
        sheet_names = []

        if not filtered_df.empty:
            kpi_dict = {
                "总销售额": f"¥{kpi['total_sales']:,.0f}",
                "总订单数": f"{kpi['total_orders']:,} 单",
                "客单价": f"¥{kpi['avg_order_value']:,.2f}",
                "销售额环比": f"{kpi['sales_mom']:+.2f}%" if kpi['sales_mom'] is not None else "-"
            }

            if 'freq' not in st.session_state:
                st.session_state.freq = 'D'
            freq = st.session_state.get('freq', 'D')
            trend_df = svc.get_trend(freq)
            if not trend_df.empty:
                fig_trend_exp = LineChart(f"销售额趋势（按{'日周月'['DWM'.index(freq)]}）").add_line(
                    trend_df.iloc[:, 0], trend_df['销售额'], hover_template='时间: %{x}<br>销售额: ¥%{y:,.2f}<extra></extra>'
                ).fig
                figures_dict["销售额趋势"] = fig_trend_exp
                tables_dict["销售额趋势数据"] = trend_df
                summary_dfs.append(trend_df)
                sheet_names.append("销售额趋势")

            cat_sales_exp = svc.get_category_sales()
            if not cat_sales_exp.empty:
                fig_pie_exp = PieChart("品类销售占比").add_pie_from_df(cat_sales_exp, '销售额', 'product_category').fig
                figures_dict["品类销售占比"] = fig_pie_exp
                tables_dict["品类销售汇总"] = cat_sales_exp
                summary_dfs.append(cat_sales_exp)
                sheet_names.append("品类销售汇总")

            region_sales_exp = svc.get_region_sales()
            if not region_sales_exp.empty:
                tables_dict["地区销售汇总"] = region_sales_exp
                summary_dfs.append(region_sales_exp)
                sheet_names.append("地区销售汇总")

        html_report = generate_html_report(
            "销售概览", rep_title, rep_subtitle, kpi_dict, figures_dict, tables_dict
        )
        excel_bytes = export_to_excel(
            filtered_df, summary_dfs, sheet_names,
            title=f"{rep_title} - {rep_subtitle}"
        )
        with st.popover("📥 导出报表", use_container_width=True):
            get_download_buttons(
                "销售概览", export_html_report(html_report), excel_bytes,
                start_date, end_date,
                categories=selected_categories if len(selected_categories) < len(all_categories) else None
            )
    st.markdown('</div>', unsafe_allow_html=True)

st.subheader("🎯 核心指标")

def format_metric(label, value, mom, prefix="", suffix=""):
    delta = None
    delta_color = "normal"
    if mom is not None:
        delta = f"{mom:+.2f}%"
        delta_color = "normal" if mom >= 0 else "inverse"
    st.metric(label, f"{prefix}{value:,.2f}{suffix}", delta=delta, delta_color=delta_color)

c1, c2, c3, c4 = st.columns(4)
with c1:
    format_metric("💰 总销售额", kpi['total_sales'], kpi['sales_mom'], prefix="¥")
with c2:
    format_metric("📦 总订单数", kpi['total_orders'], kpi['orders_mom'], suffix=" 单")
with c3:
    format_metric("💎 客单价", kpi['avg_order_value'], kpi['aov_mom'], prefix="¥")
with c4:
    repeat_rate, repeat_users, total_users = svc.get_repeat_rate()
    if total_users > 0:
        st.metric("🔁 复购率", f"{repeat_rate:.2f}%", delta=f"复购用户 {repeat_users} 人")
    else:
        st.metric("🔁 复购率", "0.00%")

st.divider()

st.subheader("📈 销售额趋势分析")
t_col1, t_col2 = st.columns([1, 4])
with t_col1:
    freq_label = st.radio("时间粒度", options=["日", "周", "月"], horizontal=True, index=0)
    freq_map = {"日": "D", "周": "W", "月": "M"}
    freq = freq_map[freq_label]
    st.session_state.freq = freq

trend_df = svc.get_trend(freq)
if not trend_df.empty:
    LineChart(f"销售额趋势（按{freq_label}）").add_line(
        trend_df.iloc[:, 0], trend_df['销售额'],
        hover_template='时间: %{x}<br>销售额: ¥%{y:,.2f}<extra></extra>'
    ).render()
else:
    st.warning("所选时间段内无数据")

st.divider()

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("🥧 品类销售占比")
    if not filtered_df.empty:
        cat_sales = svc.get_category_sales()
        PieChart("各品类销售额占比").add_pie_from_df(
            cat_sales, '销售额', 'product_category'
        ).render()
    else:
        st.warning("所选时间段内无数据")

with col_b:
    st.subheader("🗺️ 地区销售分布")
    if not filtered_df.empty:
        region_sales = svc.get_region_sales().sort_values('销售额', ascending=True)
        BarChart("各省份销售额排名（热力着色）", orientation='h').add_colorscale_bar(
            x=region_sales['销售额'], y=region_sales['region'],
            colorscale='Blues', colorbar_title="销售额"
        ).render()
    else:
        st.warning("所选时间段内无数据")

st.divider()
st.subheader("📋 数据明细（TOP 20）")
if not filtered_df.empty:
    show_df = svc.get_top_orders(20)
    st.dataframe(show_df, hide_index=True, use_container_width=True)
