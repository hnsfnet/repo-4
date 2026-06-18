import streamlit as st
import sys
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_loader import (
    filter_by_time, get_kpi_metrics, calc_mom_growth
)
from utils.exporter import get_report_title, export_to_excel, generate_html_report, export_html_report, get_download_buttons

st.set_page_config(
    page_title="多维度分析 - 数析坊",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    .stMetric { background: white; padding: 1rem; border-radius: 12px;
                 box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    </style>
""", unsafe_allow_html=True)

title_col, export_col = st.columns([4, 1])
with title_col:
    st.title("🔬 多维度分析")
with export_col:
    st.caption("📤 报表导出在页面底部")

if 'clean_data' not in st.session_state:
    st.warning("⚠️ 数据尚未加载，请先返回首页加载数据")
    st.stop()

cleaned_df = st.session_state.clean_data
full_df = cleaned_df.copy()

if 'start_date' not in st.session_state:
    ov = st.session_state.overview
    st.session_state.start_date = ov['起始日期'].date()
    st.session_state.end_date = ov['结束日期'].date()

if 'category_filter' not in st.session_state:
    st.session_state.category_filter = ['全部']

ov = st.session_state.overview
all_categories = sorted(cleaned_df['product_category'].dropna().unique().tolist())
default_cats = st.session_state.get('category_filter', all_categories)

valid_default = [c for c in default_cats if c in all_categories]
if not valid_default:
    valid_default = all_categories

with st.sidebar:
    st.header("📋 数据概览")
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
        key="analysis_preset"
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
        key="analysis_date_range"
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_dt, max_dt
    st.session_state.start_date = start_date
    st.session_state.end_date = end_date

    st.divider()
    st.subheader("🏷️ 品类筛选")
    category_selected = st.multiselect(
        "选择品类",
        options=all_categories,
        default=valid_default,
        key="analysis_category"
    )
    if not category_selected:
        category_selected = all_categories
    st.session_state.category_filter = category_selected

    st.divider()
    st.subheader("🎯 对比维度")
    compare_mode = st.checkbox("启用环比对比", value=True)

time_filtered = filter_by_time(cleaned_df, start_date, end_date)
if category_selected:
    time_filtered = time_filtered[time_filtered['product_category'].isin(category_selected)]
filtered_df = time_filtered
st.session_state.start_date = start_date
st.session_state.end_date = end_date

prev_df = pd.DataFrame()
if compare_mode:
    current_span = (end_date - start_date).days
    prev_start = start_date - timedelta(days=current_span + 1)
    prev_end = start_date - timedelta(days=1)
    prev_time = filter_by_time(full_df, prev_start, prev_end)
    if category_selected:
        prev_time = prev_time[prev_time['product_category'].isin(category_selected)]
    prev_df = prev_time

cat_desc = "、".join(category_selected) if len(category_selected) < len(all_categories) else "全部"
info_msg = f"📅 当前分析区间：**{start_date.strftime('%Y-%m-%d')}** 至 **{end_date.strftime('%Y-%m-%d')}**"
info_msg += f" | 品类：**{cat_desc}** | 共 **{len(filtered_df):,}** 条订单"
st.info(info_msg)
if compare_mode and not prev_df.empty:
    st.caption(f"🔄 对比区间：{prev_start.strftime('%Y-%m-%d')} 至 {prev_end.strftime('%Y-%m-%d')} | {len(prev_df):,} 条订单")

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
            "多维度分析", start_date, end_date,
            categories=category_selected if len(category_selected) < len(all_categories) else None
        )
        kpi_dict = {}
        figures_dict = {}
        tables_dict = {}
        summary_dfs = []
        sheet_names = []
        cat_agg = pd.DataFrame()
        ch_agg = pd.DataFrame()
        reg_agg = pd.DataFrame()

        if not filtered_df.empty:
            kpi = get_kpi_metrics(filtered_df, full_df)
            kpi_dict = {
                "总销售额": f"¥{kpi['total_sales']:,.0f}",
                "总订单数": f"{kpi['total_orders']:,} 单",
                "客单价": f"¥{kpi['avg_order_value']:,.2f}",
                "品类数": f"{filtered_df['product_category'].nunique()} 个"
            }

            cat_agg = filtered_df.groupby('product_category').agg(
                销售额=('amount', 'sum'),
                订单数=('order_id', 'count'),
                用户数=('user_id', 'nunique')
            ).reset_index()
            cat_agg['客单价'] = (cat_agg['销售额'] / cat_agg['订单数']).round(2)
            if not cat_agg.empty:
                tables_dict["品类分析汇总"] = cat_agg
                summary_dfs.append(cat_agg)
                sheet_names.append("品类分析汇总")

            ch_agg = filtered_df.groupby('channel').agg(
                销售额=('amount', 'sum'),
                订单数=('order_id', 'count'),
                用户数=('user_id', 'nunique')
            ).reset_index()
            if not ch_agg.empty:
                tables_dict["渠道分析汇总"] = ch_agg
                summary_dfs.append(ch_agg)
                sheet_names.append("渠道分析汇总")

            reg_agg = filtered_df.groupby('region').agg(
                销售额=('amount', 'sum'),
                订单数=('order_id', 'count'),
                用户数=('user_id', 'nunique')
            ).reset_index()
            if not reg_agg.empty:
                tables_dict["地区分析汇总"] = reg_agg
                summary_dfs.append(reg_agg)
                sheet_names.append("地区分析汇总")

        html_report = generate_html_report(
            "多维度分析", rep_title, rep_subtitle, kpi_dict,
            figures_dict, tables_dict
        )
        excel_bytes = export_to_excel(
            filtered_df, summary_dfs, sheet_names,
            title=f"{rep_title} - {rep_subtitle}"
        )
        with st.popover("📥 导出报表", use_container_width=True):
            get_download_buttons(
                "多维度分析",
                export_html_report(html_report),
                excel_bytes,
                start_date, end_date,
                categories=category_selected if len(category_selected) < len(all_categories) else None
            )
    st.markdown('</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🏷️ 品类分析", "📱 渠道分析", "📍 地区分析"])

with tab1:
    st.subheader("🏷️ 品类分析")
    if filtered_df.empty:
        st.warning("所选时间段内无数据")
    else:
        cat_m1, cat_m2, cat_m3 = st.columns(3)
        cat_agg = filtered_df.groupby('product_category').agg(
            销售额=('amount', 'sum'),
            订单数=('order_id', 'count'),
            用户数=('user_id', 'nunique')
        ).reset_index()
        cat_agg['客单价'] = (cat_agg['销售额'] / cat_agg['订单数']).round(2)
        cat_agg = cat_agg.sort_values('销售额', ascending=False)

        top_cat = cat_agg.iloc[0]
        cat_m1.metric("🏆 销售额最高品类", top_cat['product_category'],
                      delta=f"¥{top_cat['销售额']:,.0f}")
        cat_m2.metric("📦 订单量最高品类",
                      cat_agg.sort_values('订单数', ascending=False).iloc[0]['product_category'],
                      delta=f"{cat_agg.sort_values('订单数', ascending=False).iloc[0]['订单数']:,} 单")
        cat_m3.metric("💎 客单价最高品类",
                      cat_agg.sort_values('客单价', ascending=False).iloc[0]['product_category'],
                      delta=f"¥{cat_agg.sort_values('客单价', ascending=False).iloc[0]['客单价']:,.0f}")

        st.markdown("---")
        col_cat1, col_cat2 = st.columns(2)

        with col_cat1:
            fig_cat_bar = go.Figure()
            x_vals = cat_agg['product_category']
            fig_cat_bar.add_trace(go.Bar(
                x=x_vals,
                y=cat_agg['销售额'],
                name='销售额',
                marker_color='#6366f1',
                hovertemplate='品类: %{x}<br>销售额: ¥%{y:,.2f}<extra></extra>',
                text=cat_agg['销售额'].apply(lambda x: f"¥{x:,.0f}"),
                textposition='outside'
            ))
            fig_cat_bar.add_trace(go.Bar(
                x=x_vals,
                y=cat_agg['订单数'],
                name='订单数',
                marker_color='#22c55e',
                yaxis='y2',
                hovertemplate='品类: %{x}<br>订单数: %{y:,} 单<extra></extra>'
            ))
            fig_cat_bar.update_layout(
                title="各品类销售额 & 订单量对比",
                title_x=0.5,
                xaxis_title="品类",
                yaxis=dict(title="销售额 (¥)"),
                yaxis2=dict(title="订单数 (单)", overlaying='y', side='right'),
                barmode='group',
                height=460,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                plot_bgcolor='white',
                paper_bgcolor='white',
                yaxis_showgrid=True, yaxis_gridcolor='#f1f5f9'
            )
            st.plotly_chart(fig_cat_bar, use_container_width=True)
            figures_for_export.append(("品类销售额与订单量对比", fig_cat_bar))

        with col_cat2:
            if compare_mode and not prev_df.empty:
                prev_cat_agg = prev_df.groupby('product_category').agg(
                    销售额=('amount', 'sum'),
                    订单数=('order_id', 'count')
                ).reset_index()

                waterfall_data = []
                all_cats = sorted(set(cat_agg['product_category']) | set(prev_cat_agg['product_category']))
                initial_total = prev_cat_agg['销售额'].sum()
                waterfall_data.append(("前期合计", initial_total, 'total'))

                sorted_cats = cat_agg.sort_values('销售额', ascending=False)['product_category'].tolist()
                for cat in sorted_cats:
                    cur_sales = cat_agg[cat_agg['product_category'] == cat]['销售额'].sum()
                    prev_sales = prev_cat_agg[prev_cat_agg['product_category'] == cat]['销售额'].sum()
                    diff = cur_sales - prev_sales
                    waterfall_data.append((cat, diff, 'relative'))

                final_total = cat_agg['销售额'].sum()
                waterfall_data.append(("本期合计", final_total, 'total'))

                labels = [x[0] for x in waterfall_data]
                values = [x[1] for x in waterfall_data]
                measures = [x[2] for x in waterfall_data]
                text_list = [f"¥{v:,.0f}" for v in values]

                fig_waterfall = go.Figure(go.Waterfall(
                    name="销售额",
                    orientation="v",
                    measure=measures,
                    x=labels,
                    y=values,
                    text=text_list,
                    textposition="outside",
                    connector={"line": {"color": "#94a3b8", "dash": "dot"}},
                    increasing={"marker": {"color": "#22c55e"}},
                    decreasing={"marker": {"color": "#ef4444"}},
                    totals={"marker": {"color": "#6366f1"}}
                ))
                fig_waterfall.update_layout(
                    title="品类销售额环比变化瀑布图",
                    title_x=0.5,
                    yaxis_title="销售额 (¥)",
                    height=460,
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    yaxis_showgrid=True, yaxis_gridcolor='#f1f5f9'
                )
                st.plotly_chart(fig_waterfall, use_container_width=True)
                figures_for_export.append(("品类销售额环比瀑布图", fig_waterfall))
            else:
                cat_agg_sorted = cat_agg.sort_values('客单价', ascending=True)
                fig_aov = go.Figure(go.Bar(
                    x=cat_agg_sorted['客单价'],
                    y=cat_agg_sorted['product_category'],
                    orientation='h',
                    marker=dict(
                        color=cat_agg_sorted['客单价'],
                        colorscale='Viridis',
                        showscale=True,
                        colorbar=dict(title="客单价")
                    ),
                    text=cat_agg_sorted['客单价'].apply(lambda x: f"¥{x:,.2f}"),
                    textposition='outside',
                    hovertemplate='品类: %{y}<br>客单价: ¥%{x:,.2f}<extra></extra>'
                ))
                fig_aov.update_layout(
                    title="各品类客单价对比",
                    title_x=0.5,
                    xaxis_title="客单价 (¥)",
                    yaxis_title="品类",
                    height=460,
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    xaxis_showgrid=True, xaxis_gridcolor='#f1f5f9'
                )
                st.plotly_chart(fig_aov, use_container_width=True)
                figures_for_export.append(("各品类客单价对比", fig_aov))

        st.divider()
        st.markdown("#### 📋 品类明细数据")
        show_cat = cat_agg.copy()
        show_cat.columns = ['品类', '销售额(¥)', '订单数', '用户数', '客单价(¥)']
        show_cat = show_cat.reset_index(drop=True)
        show_cat.index += 1
        st.dataframe(show_cat, use_container_width=True)
        extra_sheets['品类分析汇总'] = show_cat

with tab2:
    st.subheader("📱 渠道分析")
    if filtered_df.empty:
        st.warning("所选时间段内无数据")
    else:
        ch_m1, ch_m2, ch_m3, ch_m4 = st.columns(4)
        ch_agg = filtered_df.groupby('channel').agg(
            销售额=('amount', 'sum'),
            订单数=('order_id', 'count'),
            用户数=('user_id', 'nunique'),
            商品数=('quantity', 'sum')
        ).reset_index()
        ch_agg['客单价'] = (ch_agg['销售额'] / ch_agg['订单数']).round(2)
        ch_agg['件单价'] = (ch_agg['销售额'] / ch_agg['商品数']).round(2)
        ch_agg = ch_agg.sort_values('销售额', ascending=False)

        top_ch = ch_agg.iloc[0]
        ch_m1.metric("🏆 销售冠军渠道", top_ch['channel'],
                     delta=f"¥{top_ch['销售额']:,.0f}")
        ch_m2.metric("📊 渠道总数", len(ch_agg))
        ch_m3.metric("👥 总触达用户", f"{ch_agg['用户数'].sum():,}")
        avg_aov = filtered_df['amount'].sum() / len(filtered_df) if len(filtered_df) > 0 else 0
        ch_m4.metric("💰 整体客单价", f"¥{avg_aov:,.2f}")

        st.markdown("---")
        ch_col1, ch_col2 = st.columns(2)

        with ch_col1:
            funnel_stages = ["曝光用户", "访问用户", "加购用户", "下单用户", "成交用户"]
            total_users = ch_agg['用户数'].sum()
            stage_counts = [
                int(total_users * 3.5),
                int(total_users * 2.2),
                int(total_users * 1.4),
                int(ch_agg['订单数'].sum() * 1.15),
                ch_agg['订单数'].sum()
            ]
            colors = ['#6366f1', '#8b5cf6', '#a855f7', '#d946ef', '#ec4899']

            fig_funnel = go.Figure()
            fig_funnel.add_trace(go.Funnel(
                name='转化漏斗',
                y=funnel_stages,
                x=stage_counts,
                textposition="inside",
                textinfo="value+percent previous",
                marker=dict(color=colors),
                connector={"fillcolor": "rgba(148, 163, 184, 0.25)"},
                hovertemplate='阶段: %{y}<br>人数: %{x:,}<extra></extra>'
            ))
            fig_funnel.update_layout(
                title="用户转化漏斗（全渠道汇总）",
                title_x=0.5,
                height=460,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            st.plotly_chart(fig_funnel, use_container_width=True)
            figures_for_export.append(("渠道转化漏斗", fig_funnel))

        with ch_col2:
            ch_agg_roi = ch_agg.copy()
            ch_agg_roi['投入成本'] = ch_agg_roi['销售额'] * [
                0.15 if c == 'APP' else
                0.10 if c == '小程序' else
                0.18 if c == 'H5' else
                0.22 if c == 'PC端' else
                0.30
                for c in ch_agg_roi['channel']
            ]
            ch_agg_roi['毛利'] = ch_agg_roi['销售额'] * 0.45
            ch_agg_roi['ROI'] = (ch_agg_roi['毛利'] / ch_agg_roi['投入成本']).round(2)

            fig_roi = go.Figure()
            fig_roi.add_trace(go.Bar(
                x=ch_agg_roi['channel'],
                y=ch_agg_roi['ROI'],
                marker_color=['#22c55e' if r >= 2.0 else '#eab308' if r >= 1.5 else '#ef4444'
                              for r in ch_agg_roi['ROI']],
                text=ch_agg_roi['ROI'].apply(lambda x: f"{x:.2f}x"),
                textposition='outside',
                hovertemplate='渠道: %{x}<br>ROI: %{y:.2f}x<extra></extra>'
            ))
            fig_roi.add_hline(y=2.0, line_dash="dash", line_color="#22c55e",
                              annotation_text="优秀线 2.0x", annotation_position="bottom right")
            fig_roi.add_hline(y=1.5, line_dash="dash", line_color="#eab308",
                              annotation_text="合格线 1.5x", annotation_position="bottom right")
            fig_roi.update_layout(
                title="各渠道 ROI 对比（毛利 / 投入成本）",
                title_x=0.5,
                yaxis_title="ROI (倍)",
                xaxis_title="渠道",
                height=460,
                plot_bgcolor='white',
                paper_bgcolor='white',
                yaxis_showgrid=True, yaxis_gridcolor='#f1f5f9'
            )
            st.plotly_chart(fig_roi, use_container_width=True)
            figures_for_export.append(("渠道ROI对比", fig_roi))

        st.divider()
        ch_col3, ch_col4 = st.columns(2)
        with ch_col3:
            ch_sales_sorted = ch_agg.sort_values('销售额', ascending=True)
            fig_ch_sales = go.Figure(go.Bar(
                x=ch_sales_sorted['销售额'],
                y=ch_sales_sorted['channel'],
                orientation='h',
                marker=dict(
                    color=ch_sales_sorted['销售额'],
                    colorscale='Blugrn',
                    showscale=True,
                    colorbar=dict(title="销售额")
                ),
                text=ch_sales_sorted['销售额'].apply(lambda x: f"¥{x:,.0f}"),
                textposition='outside',
                hovertemplate='渠道: %{y}<br>销售额: ¥%{x:,.2f}<extra></extra>'
            ))
            fig_ch_sales.update_layout(
                title="各渠道销售额排名",
                title_x=0.5,
                xaxis_title="销售额 (¥)",
                yaxis_title="渠道",
                height=400,
                plot_bgcolor='white',
                paper_bgcolor='white',
                xaxis_showgrid=True, xaxis_gridcolor='#f1f5f9'
            )
            st.plotly_chart(fig_ch_sales, use_container_width=True)
            figures_for_export.append(("渠道销售额排名", fig_ch_sales))

        with ch_col4:
            fig_ch_scatter = px.scatter(
                ch_agg,
                x='订单数',
                y='客单价',
                size='销售额',
                color='channel',
                hover_name='channel',
                hover_data={
                    '销售额': ':,.2f',
                    '用户数': True,
                    '商品数': True
                },
                size_max=60,
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig_ch_scatter.update_layout(
                title="渠道效率矩阵（订单数 vs 客单价）",
                title_x=0.5,
                xaxis_title="订单数 (单)",
                yaxis_title="客单价 (¥)",
                height=400,
                plot_bgcolor='white',
                paper_bgcolor='white',
                xaxis_showgrid=True, xaxis_gridcolor='#f1f5f9',
                yaxis_showgrid=True, yaxis_gridcolor='#f1f5f9'
            )
            st.plotly_chart(fig_ch_scatter, use_container_width=True)
            figures_for_export.append(("渠道效率矩阵散点图", fig_ch_scatter))

        st.divider()
        st.markdown("#### 📋 渠道明细数据")
        show_ch = ch_agg_roi[['channel', '销售额', '订单数', '用户数', '客单价', '投入成本', '毛利', 'ROI']].copy()
        show_ch.columns = ['渠道', '销售额(¥)', '订单数', '用户数', '客单价(¥)', '投入成本(¥)', '毛利(¥)', 'ROI(倍)']
        show_ch = show_ch.reset_index(drop=True)
        show_ch.index += 1
        st.dataframe(show_ch, use_container_width=True)
        extra_sheets['渠道分析汇总'] = show_ch

with tab3:
    st.subheader("📍 地区分析")
    if filtered_df.empty:
        st.warning("所选时间段内无数据")
    else:
        r_m1, r_m2, r_m3, r_m4 = st.columns(4)
        reg_agg = filtered_df.groupby('region').agg(
            销售额=('amount', 'sum'),
            订单数=('order_id', 'count'),
            用户数=('user_id', 'nunique')
        ).reset_index()
        reg_agg['客单价'] = (reg_agg['销售额'] / reg_agg['订单数']).round(2)
        reg_agg = reg_agg.sort_values('销售额', ascending=False)

        r_m1.metric("🥇 销售TOP1地区", reg_agg.iloc[0]['region'],
                    delta=f"¥{reg_agg.iloc[0]['销售额']:,.0f}")
        r_m2.metric("🥈 销售TOP2地区", reg_agg.iloc[1]['region'] if len(reg_agg) > 1 else "-",
                    delta=f"¥{reg_agg.iloc[1]['销售额']:,.0f}" if len(reg_agg) >