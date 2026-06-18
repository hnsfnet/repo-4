import streamlit as st
import sys
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_loader import (
    filter_by_time, get_kpi_metrics, aggregate_sales_by_time,
    get_data_overview, apply_all_filters
)
from utils.exporter import get_report_title, export_to_excel, generate_html_report, export_html_report, get_download_buttons

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
        index=5
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
        key="page_date_range"
    )
    st.divider()
    st.subheader("🏷️ 品类筛选")
    all_categories = sorted(cleaned_df['product_category'].unique())
    selected_categories = st.multiselect(
        "选择分析品类",
        options=all_categories,
        default=all_categories,
        key="overview_category_filter"
    )

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_dt, max_dt

time_filtered = filter_by_time(cleaned_df, start_date, end_date)
if selected_categories:
    time_filtered = time_filtered[time_filtered['product_category'].isin(selected_categories)]
filtered_df = apply_all_filters(cleaned_df, start_date, end_date, selected_categories)
st.session_state.filtered_df = filtered_df
kpi = get_kpi_metrics(filtered_df, full_df)

st.info(f"📅 当前分析区间：**{start_date.strftime('%Y-%m-%d')}** 至 **{end_date.strftime('%Y-%m-%d')}** | 共 **{len(filtered_df):,}** 条订单")
if selected_categories and len(selected_categories) < len(all_categories):
    st.caption(f"🏷️ 已选品类：{', '.join(selected_categories)}")

with st.container():
    st.markdown("""
    <div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); padding: 1rem; border-radius: 10px; border: 1px solid #7dd3fc; margin-bottom: 1.5rem;">
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
        cat_sales_exp = pd.DataFrame()
        region_sales_exp = pd.DataFrame()
        trend_df = pd.DataFrame()

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
            trend_df = aggregate_sales_by_time(filtered_df, freq)
            if not trend_df.empty:
                freq_label_map = {"D": "日", "W": "周", "M": "月"}
                freq_label = freq_label_map.get(freq, "日")
                fig_trend_exp = go.Figure()
                fig_trend_exp.add_trace(go.Scatter(
                    x=trend_df.iloc[:, 0],
                    y=trend_df['销售额'],
                    mode='lines+markers',
                    line=dict(color='#6366f1', width=3),
                    marker=dict(size=7, color='#6366f1'),
                    fill='tozeroy',
                    fillcolor='rgba(99, 102, 241, 0.1)'
                ))
                fig_trend_exp.update_layout(
                    title=f"销售额趋势（按{freq_label}）",
                    title_x=0.5, height=420
                )
                figures_dict["销售额趋势"] = fig_trend_exp
                tables_dict["销售额趋势数据"] = trend_df
                summary_dfs.append(trend_df)
                sheet_names.append("销售额趋势")

            cat_sales_exp = filtered_df.groupby('product_category').agg(
                销售额=('amount', 'sum'),
                订单数=('order_id', 'count')
            ).reset_index()
            if not cat_sales_exp.empty:
                fig_pie_exp = px.pie(
                    cat_sales_exp, values='销售额', names='product_category',
                    hole=0.45, title='品类销售占比'
                )
                figures_dict["品类销售占比"] = fig_pie_exp
                tables_dict["品类销售汇总"] = cat_sales_exp
                summary_dfs.append(cat_sales_exp)
                sheet_names.append("品类销售汇总")

            region_sales_exp = filtered_df.groupby('region').agg(
                销售额=('amount', 'sum'),
                订单数=('order_id', 'count')
            ).reset_index()
            if not region_sales_exp.empty:
                tables_dict["地区销售汇总"] = region_sales_exp
                summary_dfs.append(region_sales_exp)
                sheet_names.append("地区销售汇总")

        html_report = generate_html_report(
            "销售概览", rep_title, rep_subtitle, kpi_dict,
            figures_dict, tables_dict
        )
        excel_bytes = export_to_excel(
            filtered_df, summary_dfs, sheet_names,
            title=f"{rep_title} - {rep_subtitle}"
        )

        with st.popover("📥 导出报表", use_container_width=True):
            get_download_buttons(
                "销售概览",
                export_html_report(html_report),
                excel_bytes,
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
    if len(filtered_df) > 0:
        total_users = filtered_df['user_id'].nunique()
        repeat_users = filtered_df.groupby('user_id').size().where(lambda x: x > 1).dropna().shape[0]
        repeat_rate = repeat_users / total_users * 100 if total_users > 0 else 0
        st.metric("🔁 复购率", f"{repeat_rate:.2f}%", delta=f"复购用户 {repeat_users} 人")
    else:
        st.metric("🔁 复购率", "0.00%")

st.divider()

st.subheader("📈 销售额趋势分析")
t_col1, t_col2 = st.columns([1, 4])
with t_col1:
    freq_label = st.radio(
        "时间粒度",
        options=["日", "周", "月"],
        horizontal=True,
        index=0
    )
    freq_map = {"日": "D", "周": "W", "月": "M"}
    freq = freq_map[freq_label]
    st.session_state.freq = freq

trend_df = aggregate_sales_by_time(filtered_df, freq)

if not trend_df.empty:
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=trend_df.iloc[:, 0],
        y=trend_df['销售额'],
        mode='lines+markers',
        name='销售额',
        line=dict(color='#6366f1', width=3),
        marker=dict(size=7, color='#6366f1'),
        fill='tozeroy',
        fillcolor='rgba(99, 102, 241, 0.1)',
        hovertemplate='时间: %{x}<br>销售额: ¥%{y:,.2f}<extra></extra>'
    ))
    fig_trend.update_layout(
        title=f"销售额趋势（按{freq_label}）",
        title_x=0.5,
        xaxis_title="时间",
        yaxis_title="销售额 (¥)",
        hovermode="x unified",
        height=420,
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(showgrid=True, gridcolor='#f1f5f9'),
        yaxis=dict(showgrid=True, gridcolor='#f1f5f9')
    )
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.warning("所选时间段内无数据")

st.divider()

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("🥧 品类销售占比")
    if not filtered_df.empty:
        cat_sales = filtered_df.groupby('product_category').agg(
            销售额=('amount', 'sum'),
            订单数=('order_id', 'count')
        ).reset_index().sort_values('销售额', ascending=False)
        cat_sales['占比'] = cat_sales['销售额'] / cat_sales['销售额'].sum()

        fig_pie = px.pie(
            cat_sales,
            values='销售额',
            names='product_category',
            title='各品类销售额占比',
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_pie.update_traces(
            textposition='inside',
            textinfo='label+percent',
            hovertemplate='品类: %{label}<br>销售额: ¥%{value:,.2f}<br>占比: %{percent}<extra></extra>'
        )
        fig_pie.update_layout(
            height=440,
            title_x=0.5,
            legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.warning("所选时间段内无数据")

with col_b:
    st.subheader("🗺️ 地区销售分布")
    if not filtered_df.empty:
        region_sales = filtered_df.groupby('region').agg(
            销售额=('amount', 'sum'),
            订单数=('order_id', 'count')
        ).reset_index().sort_values('销售额', ascending=True)

        fig_region = go.Figure()
        fig_region.add_trace(go.Bar(
            x=region_sales['销售额'],
            y=region_sales['region'],
            orientation='h',
            marker=dict(
                color=region_sales['销售额'],
                colorscale='Blues',
                showscale=True,
                colorbar=dict(title="销售额")
            ),
            hovertemplate='地区: %{y}<br>销售额: ¥%{x:,.2f}<extra></extra>',
            text=region_sales['销售额'].apply(lambda x: f"¥{x:,.0f}"),
            textposition='outside'
        ))
        fig_region.update_layout(
            title="各省份销售额排名（热力着色）",
            title_x=0.5,
            xaxis_title="销售额 (¥)",
            yaxis_title="地区",
            height=440,
            margin=dict(l=80, r=40, t=60, b=40),
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(showgrid=True, gridcolor='#f1f5f9')
        )
        st.plotly_chart(fig_region, use_container_width=True)
    else:
        st.warning("所选时间段内无数据")

st.divider()
st.subheader("📋 数据明细（TOP 20）")
if not filtered_df.empty:
    show_df = filtered_df.sort_values('amount', ascending=False).head(20)[
        ['order_id', 'user_id', 'product_category', 'amount', 'quantity',
         'order_time', 'region', 'channel']
    ].copy()
    show_df['order_time'] = show_df['order_time'].dt.strftime('%Y-%m-%d %H:%M')
    show_df.columns = ['订单号', '用户ID', '品类', '金额(¥)', '数量',
                       '下单时间', '地区', '渠道']
    st.dataframe(show_df, hide_index=True, use_container_width=True)
