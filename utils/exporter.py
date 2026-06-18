import pandas as pd
import io
import base64
from datetime import datetime
from jinja2 import Template


def get_report_title(page_name, start_date, end_date, categories=None, regions=None, channels=None):
    title = f"数析坊 - {page_name} 分析报告"
    filters = []
    if start_date and end_date:
        filters.append(f"时间: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
    if categories and len(categories) > 0:
        filters.append(f"品类: {', '.join(categories)}")
    if regions and len(regions) > 0:
        filters.append(f"地区: {', '.join(regions)}")
    if channels and len(channels) > 0:
        filters.append(f"渠道: {', '.join(channels)}")
    subtitle = " | ".join(filters) if filters else "全部数据"
    return title, subtitle


def export_to_excel(raw_df, summary_dfs, sheet_names, title="数据分析报告"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if raw_df is not None and not raw_df.empty:
            raw_df.to_excel(writer, sheet_name='原始数据', index=False)

        for df, name in zip(summary_dfs, sheet_names):
            if df is not None and not df.empty:
                df.to_excel(writer, sheet_name=name[:31], index=False)

        summary_sheet = writer.book.create_sheet('报告信息', 0)
        summary_sheet['A1'] = title
        summary_sheet['A2'] = f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        summary_sheet['A3'] = f"数据记录数: {len(raw_df) if raw_df is not None else 0}"

    output.seek(0)
    return output.getvalue()


def fig_to_base64(fig):
    try:
        img_bytes = fig.to_image(format='png', width=1000, height=500, scale=2)
        return base64.b64encode(img_bytes).decode('utf-8')
    except Exception:
        return None


def generate_html_report(page_name, title, subtitle, kpi_data, figures, data_tables, analysis_date=None):
    figure_htmls = []
    for fig_name, fig in figures.items():
        img_b64 = fig_to_base64(fig)
        if img_b64:
            figure_htmls.append(f"""
                <div class="figure-block">
                    <h3>{fig_name}</h3>
                    <img src="data:image/png;base64,{img_b64}" alt="{fig_name}" style="max-width: 100%;" />
                </div>
            """)
        else:
            figure_htmls.append(f"""
                <div class="figure-block">
                    <h3>{fig_name}</h3>
                    <p style="color: #94a3b8; font-style: italic;">[图表无法自动渲染，请在看板中查看]</p>
                </div>
            """)

    kpi_html = ""
    if kpi_data:
        kpi_items = ""
        for k, v in kpi_data.items():
            kpi_items += f"<div class='kpi-card'><div class='kpi-label'>{k}</div><div class='kpi-value'>{v}</div></div>"
        kpi_html = f"<div class='kpi-container'>{kpi_items}</div>"

    table_htmls = []
    for table_name, df in data_tables.items():
        if df is not None and not df.empty:
            table_html = df.to_html(classes='data-table', index=False)
            table_htmls.append(f"""
                <div class="table-block">
                    <h3>{table_name}</h3>
                    {table_html}
                </div>
            """)

    report_date = analysis_date or datetime.now()
    template = Template("""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <style>
        body {
            font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
            background: #f8fafc;
            color: #1e293b;
            margin: 0;
            padding: 40px;
        }
        .report-container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 60px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }
        .report-header {
            text-align: center;
            margin-bottom: 40px;
            border-bottom: 3px solid #6366f1;
            padding-bottom: 30px;
        }
        .report-title {
            font-size: 32px;
            color: #1e293b;
            margin: 0 0 10px 0;
            font-weight: bold;
        }
        .report-subtitle {
            font-size: 16px;
            color: #64748b;
            margin: 0;
        }
        .report-meta {
            text-align: right;
            font-size: 13px;
            color: #94a3b8;
            margin-bottom: 30px;
        }
        .section-title {
            color: #6366f1;
            font-size: 20px;
            margin: 30px 0 20px 0;
            padding-left: 12px;
            border-left: 4px solid #6366f1;
        }
        .kpi-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .kpi-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .kpi-label {
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 8px;
        }
        .kpi-value {
            font-size: 28px;
            font-weight: bold;
        }
        .figure-block {
            margin-bottom: 35px;
            text-align: center;
            padding: 20px;
            background: #f8fafc;
            border-radius: 8px;
        }
        .figure-block h3 {
            color: #334155;
            margin-bottom: 15px;
            font-size: 16px;
        }
        .table-block {
            margin-bottom: 35px;
            overflow-x: auto;
        }
        .table-block h3 {
            color: #334155;
            margin-bottom: 15px;
            font-size: 16px;
        }
        .data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        .data-table th {
            background: #6366f1;
            color: white;
            padding: 10px 12px;
            text-align: left;
            font-weight: 500;
        }
        .data-table td {
            padding: 10px 12px;
            border-bottom: 1px solid #e2e8f0;
        }
        .data-table tr:nth-child(even) {
            background: #f8fafc;
        }
        .report-footer {
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
            text-align: center;
            color: #94a3b8;
            font-size: 12px;
        }
        @media print {
            body { padding: 0; background: white; }
            .report-container { box-shadow: none; padding: 30px; }
            .figure-block { page-break-inside: avoid; }
            .table-block { page-break-inside: avoid; }
        }
    </style>
</head>
<body>
    <div class="report-container">
        <div class="report-header">
            <h1 class="report-title">{{ title }}</h1>
            <p class="report-subtitle">{{ subtitle }}</p>
        </div>
        <div class="report-meta">
            生成时间：{{ report_date.strftime('%Y-%m-%d %H:%M:%S') }}<br>
            生成工具：数析坊电商数据分析看板
        </div>

        {% if kpi_html %}
        <h2 class="section-title">🎯 核心指标</h2>
        {{ kpi_html }}
        {% endif %}

        {% if figure_htmls %}
        <h2 class="section-title">📊 分析图表</h2>
        {% for fh in figure_htmls %}
            {{ fh }}
        {% endfor %}
        {% endif %}

        {% if table_htmls %}
        <h2 class="section-title">📋 数据明细</h2>
        {% for th in table_htmls %}
            {{ th }}
        {% endfor %}
        {% endif %}

        <div class="report-footer">
            © 2024 数析坊 (Data Workshop) · 数据驱动决策
        </div>
    </div>
</body>
</html>
    """)

    html_content = template.render(
        title=title,
        subtitle=subtitle,
        report_date=report_date,
        kpi_html=kpi_html,
        figure_htmls=figure_htmls,
        table_htmls=table_htmls
    )
    return html_content


def export_html_report(html_content):
    return html_content.encode('utf-8')


def get_download_buttons(page_name, html_report, excel_bytes, start_date, end_date, categories=None, regions=None, channels=None):
    import streamlit as st

    date_str = f"{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}"
    base_name = f"数析坊_{page_name}_{date_str}"

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📄 下载 HTML 报告（可转PDF）",
            data=html_report,
            file_name=f"{base_name}.html",
            mime="text/html",
            use_container_width=True,
            help="下载后可在浏览器打开，按 Ctrl+P 选择'另存为PDF'"
        )
    with col2:
        st.download_button(
            label="📊 下载 Excel 数据",
            data=excel_bytes,
            file_name=f"{base_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            help="包含原始数据和所有汇总分析 Sheet"
        )
