import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from streamlit.testing.v1 import AppTest
from unittest.mock import patch, MagicMock
import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)


class TestAppStartup:
    def test_app_loads_without_data(self):
        at = AppTest.from_file(os.path.join(ROOT_DIR, "app.py"), default_timeout=30)
        with patch('utils.data_loader.load_raw_data', return_value=(None, "数据文件不存在")):
            at.run(timeout=30)
            assert any("数据加载失败" in str(w.value) for w in at.warning) or \
                   any("数据尚未加载" in str(w.value) for w in at.warning) or \
                   not at.exception

    def test_app_loads_with_data(self, sample_csv_file):
        at = AppTest.from_file(os.path.join(ROOT_DIR, "app.py"), default_timeout=30)
        with patch('utils.data_loader.DATA_FILE', sample_csv_file):
            at.run(timeout=30)
            assert not at.exception


class TestSalesOverviewPage:
    def test_page_loads(self):
        page_path = os.path.join(ROOT_DIR, "pages", "1_销售概览.py")
        if os.path.exists(page_path):
            at = AppTest.from_file(page_path, default_timeout=30)
            with patch.dict('streamlit.session_state', {
                'clean_data': pd.DataFrame(),
                'overview': {},
            }, clear=False):
                at.run(timeout=30)
                assert not at.exception


class TestFilterConsistency:
    def test_filter_by_time_consistency(self, sample_orders_df):
        from utils.data_loader import filter_by_time, apply_all_filters
        start = datetime(2025, 3, 1).date()
        end = datetime(2025, 12, 31).date()

        result1 = filter_by_time(sample_orders_df, start, end)
        result2 = apply_all_filters(sample_orders_df, start, end)
        assert len(result1) == len(result2)

    def test_category_filter_consistency(self, sample_orders_df):
        from utils.data_loader import apply_all_filters
        start = datetime(2025, 1, 1).date()
        end = datetime(2025, 12, 31).date()
        cats = ['电子产品', '服装']

        result = apply_all_filters(sample_orders_df, start, end, cats)
        assert set(result['product_category'].unique()).issubset(set(cats))
        for _, row in result.iterrows():
            assert row['order_time'].date() >= start
            assert row['order_time'].date() <= end

    def test_combined_filter(self, sample_orders_df):
        from utils.data_loader import apply_all_filters
        start = datetime(2025, 6, 1).date()
        end = datetime(2025, 12, 31).date()
        cats = ['电子产品']

        result = apply_all_filters(sample_orders_df, start, end, cats)
        assert all(result['product_category'] == '电子产品')
        assert all(result['order_time'].dt.date >= start)
        assert all(result['order_time'].dt.date <= end)


class TestExportIntegration:
    def test_excel_export_with_filtered_data(self, sample_orders_df):
        from utils.data_loader import apply_all_filters
        from utils.exporter import export_to_excel

        start = datetime(2025, 3, 1).date()
        end = datetime(2025, 12, 31).date()
        filtered = apply_all_filters(sample_orders_df, start, end)

        cat_agg = filtered.groupby('product_category').agg(
            销售额=('amount', 'sum'), 订单数=('order_id', 'count')
        ).reset_index()

        excel_bytes = export_to_excel(filtered, [cat_agg], ["品类汇总"], title="导出测试")
        assert isinstance(excel_bytes, bytes)
        assert len(excel_bytes) > 0

    def test_html_report_with_service_data(self, sample_orders_df):
        from services.sales_service import SalesService
        from utils.exporter import generate_html_report, get_report_title

        svc = SalesService(sample_orders_df)
        kpi = svc.get_kpi()
        cat_sales = svc.get_category_sales()

        title, subtitle = get_report_title("销售概览", datetime(2025, 1, 1), datetime(2025, 12, 31))
        kpi_dict = {
            "总销售额": f"¥{kpi['total_sales']:,.0f}",
            "总订单数": f"{kpi['total_orders']:,} 单",
        }

        html = generate_html_report(
            "销售概览", title, subtitle, kpi_dict, {}, {"品类汇总": cat_sales}
        )
        assert "销售概览" in html
        assert f"¥{kpi['total_sales']:,.0f}" in html


class TestServiceChainIntegration:
    def test_sales_service_with_filter(self, sample_orders_df):
        from utils.data_loader import apply_all_filters
        from services.sales_service import SalesService

        start = datetime(2025, 6, 1).date()
        end = datetime(2025, 12, 31).date()
        filtered = apply_all_filters(sample_orders_df, start, end)
        svc = SalesService(filtered)
        kpi = svc.get_kpi()

        assert kpi['total_sales'] == filtered['amount'].sum()
        assert kpi['total_orders'] == len(filtered)

    def test_user_service_with_filter(self, sample_orders_df):
        from utils.data_loader import apply_all_filters
        from services.user_service import UserService

        start = datetime(2025, 3, 1).date()
        end = datetime(2025, 12, 31).date()
        filtered = apply_all_filters(sample_orders_df, start, end)
        svc = UserService(filtered)
        rfm_df, level_stats = svc.get_rfm()

        if not rfm_df.empty:
            rfm_users = set(rfm_df['user_id'].unique())
            filtered_users = set(filtered['user_id'].unique())
            assert rfm_users == filtered_users

    def test_channel_service_with_filter(self, sample_orders_df):
        from utils.data_loader import apply_all_filters
        from services.channel_service import ChannelService

        start = datetime(2025, 3, 1).date()
        end = datetime(2025, 12, 31).date()
        cats = ['电子产品', '服装']
        filtered = apply_all_filters(sample_orders_df, start, end, cats)
        svc = ChannelService(filtered)
        ch_agg = svc.get_channel_agg()

        if not ch_agg.empty:
            for _, row in ch_agg.iterrows():
                assert row['销售额'] > 0


class TestConfigIntegration:
    def test_config_loads(self):
        from utils.config import get_config
        config = get_config()
        assert 'app' in config
        assert 'theme' in config
        assert 'data' in config

    def test_config_get_key(self):
        from utils.config import get
        app_name = get('app.name')
        assert app_name == '数析坊'

    def test_config_get_nested(self):
        from utils.config import get
        primary = get('theme.colors.primary')
        assert primary is not None
        assert primary.startswith('#')

    def test_config_default_value(self):
        from utils.config import get
        val = get('nonexistent.key', 'default_val')
        assert val == 'default_val'

    def test_config_series_colors(self):
        from utils.config import get
        colors = get('theme.colors.series', [])
        assert len(colors) >= 5
