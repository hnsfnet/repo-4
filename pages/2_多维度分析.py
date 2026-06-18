import streamlit as st
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.filter_manager import FilterManager
from services.sales_service import SalesService
from services.channel_service import ChannelService
from utils.exporter import get_report_title, export_to_excel, generate_html_report, export_html_report, get_download_buttons
from charts.chart_components import BarChart, WaterfallChart, FunnelChart, HeatmapChart
from utils.config import get as cfg

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

st.title("🔬 多维度分析")

if 'clean_data' not in st.session_state:
    st.warning("⚠️ 数据尚未加载，请先返回首页加载数据")
    st.stop()

FilterManager.init_session_defaults(st.session_state.overview)
filters = FilterManager.render_sidebar("analysis", show_compare=True)
filtered_df = FilterManager.get_filtered_df(filters['start_date'], filters['end_date'], filters['categories'])
full_df = FilterManager.get_clean_data()

start_date = filters['start_date']
end_date = filters['end_date']
selected_categories = filters['categories']
all_categories = filters['all_categories']
compare_mode = filters['compare_mode']

prev_df = pd.DataFrame()
if compare_mode:
    prev_df = FilterManager.get_prev_df(start_date, end_date, selected_categories)

sales_svc = SalesService(filtered_df, full_df, prev_df)
channel_svc = ChannelService(filtered_df, prev_df)

cat_desc = "、".join(selected_categories) if len(selected_categories) < len(all_categories) else "全部"
info_msg = f"📅 当前分析区间：**{start_date.strftime('%Y-%m-%d')}** 至 **{end_date.strftime('%Y-%m-%d')}**"
info_msg += f" | 品类：**{cat_desc}** | 共 **{len(filtered_df):,}** 条订单"
st.info(info_msg)
if compare_mode and not prev_df.empty:
    from datetime import timedelta
    current_span = (end_date - start_date).days
    prev_start = start_date - timedelta(days=current_span + 1)
    prev_end = start_date - timedelta(days=1)
    st.caption(f"🔄 对比区间：{prev_start.strftime('%Y-%m-%d')} 至 {prev_end.strftime('%Y-%m-%d')} | {len(prev_df):,} 条订单")

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
            "多维度分析", start_date, end_date,
            categories=selected_categories if len(selected_categories) < len(all_categories) else None
        )
        kpi_dict = {}
        figures_dict = {}
        tables_dict = {}
        summary_dfs = []
        sheet_names = []

        if not filtered_df.empty:
            kpi = sales_svc.get_kpi()
            kpi_dict = {
                "总销售额": f"¥{kpi['total_sales']:,.0f}",
                "总订单数": f"{kpi['total_orders']:,} 单",
                "客单价": f"¥{kpi['avg_order_value']:,.2f}",
                "品类数": f"{filtered_df['product_category'].nunique()} 个"
            }

            cat_agg = sales_svc.get_category_sales()
            if not cat_agg.empty:
                tables_dict["品类分析汇总"] = cat_agg
                summary_dfs.append(cat_agg)
                sheet_names.append("品类分析汇总")

            ch_agg = channel_svc.get_channel_agg()
            if not ch_agg.empty:
                tables_dict["渠道分析汇总"] = ch_agg
                summary_dfs.append(ch_agg)
                sheet_names.append("渠道分析汇总")

            reg_agg = channel_svc.get_region_agg()
            if not reg_agg.empty:
                tables_dict["地区分析汇总"] = reg_agg
                summary_dfs.append(reg_agg)
                sheet_names.append("地区分析汇总")

        html_report = generate_html_report(
            "多维度分析", rep_title, rep_subtitle, kpi_dict, figures_dict, tables_dict
        )
        excel_bytes = export_to_excel(
            filtered_df, summary_dfs, sheet_names,
            title=f"{rep_title} - {rep_subtitle}"
        )
        with st.popover("📥 导出报表", use_container_width=True):
            get_download_buttons(
                "多维度分析", export_html_report(html_report), excel_bytes,
                start_date, end_date,
                categories=selected_categories if len(selected_categories) < len(all_categories) else None
            )
    st.markdown('</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🏷️ 品类分析", "📱 渠道分析", "📍 地区分析"])

with tab1:
    st.subheader("🏷️ 品类分析")
    if filtered_df.empty:
        st.warning("所选时间段内无数据")
    else:
        cat_agg = sales_svc.get_category_sales()

        cat_m1, cat_m2, cat_m3 = st.columns(3)
        top_cat = cat_agg.iloc[0]
        cat_m1.metric("🏆 销售额最高品类", top_cat['product_category'], delta=f"¥{top_cat['销售额']:,.0f}")
        top_order_cat = cat_agg.sort_values('订单数', ascending=False).iloc[0]
        cat_m2.metric("📦 订单量最高品类", top_order_cat['product_category'], delta=f"{top_order_cat['订单数']:,} 单")
        top_aov_cat = cat_agg.sort_values('客单价', ascending=False).iloc[0]
        cat_m3.metric("💎 客单价最高品类", top_aov_cat['product_category'], delta=f"¥{top_aov_cat['客单价']:,.0f}")

        st.markdown("---")
        col_cat1, col_cat2 = st.columns(2)

        with col_cat1:
            bar = BarChart("各品类销售额 & 订单量对比", height=460)
            bar.add_bar(
                x=cat_agg['product_category'], y=cat_agg['销售额'],
                name='销售额',
                text=cat_agg['销售额'].apply(lambda x: f"¥{x:,.0f}"),
                hover_template='品类: %{x}<br>销售额: ¥%{y:,.2f}<extra></extra>'
            )
            bar.add_bar(
                x=cat_agg['product_category'], y=cat_agg['订单数'],
                name='订单数', secondary_y=True,
                hover_template='品类: %{x}<br>订单数: %{y:,} 单<extra></extra>'
            )
            bar.with_dual_y(y1_title="销售额 (¥)", y2_title="订单数 (单)")
            bar.render(barmode='group', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5))

        with col_cat2:
            if compare_mode and not prev_df.empty:
                waterfall_data = sales_svc.get_waterfall_data()
                if waterfall_data:
                    labels = [x[0] for x in waterfall_data]
                    values = [x[1] for x in waterfall_data]
                    measures = [x[2] for x in waterfall_data]
                    WaterfallChart("品类销售额环比变化瀑布图", height=460).add_waterfall(
                        labels, values, measures
                    ).render(y_title="销售额 (¥)")
            else:
                cat_aov = cat_agg.sort_values('客单价', ascending=True)
                BarChart("各品类客单价对比", height=460, orientation='h').add_colorscale_bar(
                    x=cat_aov['客单价'], y=cat_aov['product_category'],
                    colorscale='Viridis', colorbar_title="客单价"
                ).render()

        st.divider()
        st.markdown("#### 📋 品类明细数据")
        show_cat = cat_agg.copy()
        show_cat.columns = ['品类', '销售额(¥)', '订单数', '用户数', '客单价(¥)', '占比']
        show_cat = show_cat.reset_index(drop=True)
        show_cat.index += 1
        st.dataframe(show_cat, use_container_width=True)

with tab2:
    st.subheader("📱 渠道分析")
    if filtered_df.empty:
        st.warning("所选时间段内无数据")
    else:
        ch_agg = channel_svc.get_channel_agg()
        ch_roi = channel_svc.get_roi_data(ch_agg)

        ch_m1, ch_m2, ch_m3, ch_m4 = st.columns(4)
        top_ch = ch_agg.iloc[0]
        ch_m1.metric("🏆 销售冠军渠道", top_ch['channel'], delta=f"¥{top_ch['销售额']:,.0f}")
        ch_m2.metric("📊 渠道总数", len(ch_agg))
        ch_m3.metric("👥 总触达用户", f"{ch_agg['用户数'].sum():,}")
        avg_aov = filtered_df['amount'].sum() / len(filtered_df) if len(filtered_df) > 0 else 0
        ch_m4.metric("💰 整体客单价", f"¥{avg_aov:,.2f}")

        st.markdown("---")
        ch_col1, ch_col2 = st.columns(2)

        with ch_col1:
            stages, counts = channel_svc.get_funnel_data(ch_agg)
            if stages:
                FunnelChart("用户转化漏斗（全渠道汇总）", height=460).add_funnel(stages, counts).render()

        with ch_col2:
            roi_colors = [cfg('theme.colors.success', '#22c55e') if r == 'excellent'
                          else cfg('theme.colors.warning', '#eab308') if r == 'qualified'
                          else cfg('theme.colors.danger', '#ef4444')
                          for r in ch_roi['ROI等级']]
            roi_bar = BarChart("各渠道 ROI 对比（毛利 / 投入成本）", height=460)
            roi_bar.fig.add_trace(__import__('plotly.graph_objects', fromlist=['Bar']).Bar(
                x=ch_roi['channel'], y=ch_roi['ROI'],
                marker_color=roi_colors,
                text=ch_roi['ROI'].apply(lambda x: f"{x:.2f}x"),
                textposition='outside',
                hovertemplate='渠道: %{x}<br>ROI: %{y:.2f}x<extra></extra>'
            ))
            roi_excellent = cfg('channel.roi_excellent', 2.0)
            roi_qualified = cfg('channel.roi_qualified', 1.5)
            roi_bar.add_hline(roi_excellent, line_color=cfg('theme.colors.success', '#22c55e'),
                              annotation_text=f"优秀线 {roi_excellent}x")
            roi_bar.add_hline(roi_qualified, line_color=cfg('theme.colors.warning', '#eab308'),
                              annotation_text=f"合格线 {roi_qualified}x")
            roi_bar.render(yaxis_title="ROI (倍)", xaxis_title="渠道")

        st.divider()
        ch_col3, ch_col4 = st.columns(2)
        with ch_col3:
            ch_sales_sorted = ch_agg.sort_values('销售额', ascending=True)
            BarChart("各渠道销售额排名", height=400, orientation='h').add_colorscale_bar(
                x=ch_sales_sorted['销售额'], y=ch_sales_sorted['channel'],
                colorscale='Blugrn', colorbar_title="销售额"
            ).render()

        with ch_col4:
            import plotly.express as px
            fig_ch_scatter = px.scatter(
                ch_agg, x='订单数', y='客单价', size='销售额', color='channel',
                hover_name='channel',
                hover_data={'销售额': ':,.2f', '用户数': True, '商品数': True},
                size_max=60, color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig_ch_scatter.update_layout(
                title="渠道效率矩阵（订单数 vs 客单价）",
                title_x=0.5, xaxis_title="订单数 (单)", yaxis_title="客单价 (¥)",
                height=400, plot_bgcolor='white', paper_bgcolor='white',
                xaxis=dict(showgrid=True, gridcolor='#f1f5f9'),
                yaxis=dict(showgrid=True, gridcolor='#f1f5f9')
            )
            st.plotly_chart(fig_ch_scatter, use_container_width=True)

        st.divider()
        st.markdown("#### 📋 渠道明细数据")
        show_ch = ch_roi[['channel', '销售额', '订单数', '用户数', '客单价', '投入成本', '毛利', 'ROI']].copy()
        show_ch.columns = ['渠道', '销售额(¥)', '订单数', '用户数', '客单价(¥)', '投入成本(¥)', '毛利(¥)', 'ROI(倍)']
        show_ch = show_ch.reset_index(drop=True)
        show_ch.index += 1
        st.dataframe(show_ch, use_container_width=True)

with tab3:
    st.subheader("📍 地区分析")
    if filtered_df.empty:
        st.warning("所选时间段内无数据")
    else:
        reg_agg = channel_svc.get_region_agg()

        r_m1, r_m2, r_m3, r_m4 = st.columns(4)
        r_m1.metric("🥇 销售TOP1地区", reg_agg.iloc[0]['region'], delta=f"¥{reg_agg.iloc[0]['销售额']:,.0f}")
        if len(reg_agg) > 1:
            r_m2.metric("🥈 销售TOP2地区", reg_agg.iloc[1]['region'], delta=f"¥{reg_agg.iloc[1]['销售额']:,.0f}")
        else:
            r_m2.metric("🥈 销售TOP2地区", "-")
        total_reg = len(reg_agg)
        avg_reg_sales = reg_agg['销售额'].mean() if total_reg > 0 else 0
        r_m3.metric("📊 地区总数", total_reg)
        r_m4.metric("💰 平均地区销售额", f"¥{avg_reg_sales:,.0f}")

        st.markdown("---")
        r_col1, r_col2 = st.columns(2)

        with r_col1:
            top_n = min(15, len(reg_agg))
            top_reg = reg_agg.head(top_n).sort_values('销售额', ascending=True)
            BarChart(f"TOP{top_n} 省份销售额排名", height=500, orientation='h').add_colorscale_bar(
                x=top_reg['销售额'], y=top_reg['region'],
                colorscale='Blues', colorbar_title="销售额"
            ).render()

        with r_col2:
            if compare_mode and not prev_df.empty:
                reg_growth = channel_svc.get_region_growth()
                if not reg_growth.empty:
                    growth_sorted = reg_growth.sort_values('增速(%)', ascending=True)
                    growth_colors = [cfg('theme.colors.success', '#22c55e') if v >= 0
                                     else cfg('theme.colors.danger', '#ef4444')
                                     for v in growth_sorted['增速(%)']]
                    growth_bar = BarChart("各地区销售额增速对比", height=500, orientation='h')
                    growth_bar.fig.add_trace(__import__('plotly.graph_objects', fromlist=['Bar']).Bar(
                        x=growth_sorted['增速(%)'], y=growth_sorted['region'],
                        orientation='h', marker_color=growth_colors,
                        text=growth_sorted['增速(%)'].apply(lambda x: f"{x:+.1f}%"),
                        textposition='outside',
                        hovertemplate='地区: %{y}<br>增速: %{x:+.1f}%<extra></extra>'
                    ))
                    growth_bar.render(xaxis_title="增速 (%)", yaxis_title="地区")
            else:
                st.info("启用环比对比可查看地区增速")

        st.divider()
        st.markdown("#### 📋 地区明细数据")
        show_reg = reg_agg.copy()
        show_reg.columns = ['地区', '销售额(¥)', '订单数', '用户数', '客单价(¥)']
        show_reg = show_reg.reset_index(drop=True)
        show_reg.index += 1
        st.dataframe(show_reg, use_container_width=True)
