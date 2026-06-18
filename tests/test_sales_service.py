import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from services.sales_service import SalesService


class TestSalesServiceKPI:
    def test_kpi_normal_data(self, sample_orders_df):
        svc = SalesService(sample_orders_df)
        kpi = svc.get_kpi()
        assert kpi['total_sales'] == sample_orders_df['amount'].sum()
        assert kpi['total_orders'] == 100
        assert kpi['avg_order_value'] > 0
        assert kpi['sales_mom'] is None
        assert kpi['orders_mom'] is None

    def test_kpi_with_prev_period(self, sample_orders_df, prev_period_df):
        svc = SalesService(sample_orders_df, sample_orders_df, prev_period_df)
        kpi = svc.get_kpi()
        assert kpi['sales_mom'] is not None
        assert kpi['orders_mom'] is not None
        assert kpi['aov_mom'] is not None
        assert isinstance(kpi['sales_mom'], float)

    def test_kpi_empty_df(self, empty_df):
        svc = SalesService(empty_df)
        kpi = svc.get_kpi()
        assert kpi['total_sales'] == 0
        assert kpi['total_orders'] == 0
        assert kpi['avg_order_value'] == 0
        assert kpi['sales_mom'] is None

    def test_kpi_single_row(self, single_row_df):
        svc = SalesService(single_row_df)
        kpi = svc.get_kpi()
        assert kpi['total_sales'] == 500.0
        assert kpi['total_orders'] == 1
        assert kpi['avg_order_value'] == 500.0

    def test_kpi_none_df(self):
        svc = SalesService(None)
        kpi = svc.get_kpi()
        assert kpi['total_sales'] == 0

    def test_growth_calculation(self):
        assert SalesService._calc_growth(120, 100) == 20.0
        assert SalesService._calc_growth(80, 100) == -20.0
        assert SalesService._calc_growth(100, 0) is None
        assert SalesService._calc_growth(100, None) is None

    def test_kpi_mom_positive_growth(self):
        cur = pd.DataFrame({
            'order_id': ['O1', 'O2'], 'user_id': ['U1', 'U2'],
            'product_category': ['A', 'A'], 'amount': [200.0, 300.0],
            'quantity': [1, 1], 'order_time': pd.to_datetime(['2025-06-01', '2025-06-02']),
            'region': ['北京', '上海'], 'channel': ['APP', 'APP'],
        })
        prev = pd.DataFrame({
            'order_id': ['O3'], 'user_id': ['U3'],
            'product_category': ['A'], 'amount': [100.0],
            'quantity': [1], 'order_time': pd.to_datetime(['2025-05-01']),
            'region': ['北京'], 'channel': ['APP'],
        })
        svc = SalesService(cur, cur, prev)
        kpi = svc.get_kpi()
        assert kpi['sales_mom'] == 400.0
        assert kpi['orders_mom'] == 100.0


class TestSalesServiceRepeatRate:
    def test_repeat_rate_normal(self, sample_orders_df):
        svc = SalesService(sample_orders_df)
        rate, repeat_users, total = svc.get_repeat_rate()
        assert total == sample_orders_df['user_id'].nunique()
        assert 0 <= rate <= 100
        assert repeat_users >= 0

    def test_repeat_rate_single_order(self, single_row_df):
        rate, repeat_users, total = SalesService(single_row_df).get_repeat_rate()
        assert rate == 0.0
        assert repeat_users == 0

    def test_repeat_rate_all_repeat(self, small_orders_df):
        rate, repeat_users, total = SalesService(small_orders_df).get_repeat_rate()
        assert repeat_users >= 1
        assert rate > 0

    def test_repeat_rate_empty(self, empty_df):
        rate, repeat_users, total = SalesService(empty_df).get_repeat_rate()
        assert rate == 0
        assert repeat_users == 0
        assert total == 0


class TestSalesServiceTrend:
    def test_trend_daily(self, sample_orders_df):
        svc = SalesService(sample_orders_df)
        trend = svc.get_trend('D')
        assert not trend.empty
        assert '时间(日)' in trend.columns
        assert '销售额' in trend.columns

    def test_trend_weekly(self, sample_orders_df):
        trend = SalesService(sample_orders_df).get_trend('W')
        assert not trend.empty
        assert '时间(周)' in trend.columns

    def test_trend_monthly(self, sample_orders_df):
        trend = SalesService(sample_orders_df).get_trend('M')
        assert not trend.empty
        assert '时间(月)' in trend.columns

    def test_trend_empty_df(self, empty_df):
        trend = SalesService(empty_df).get_trend('D')
        assert trend.empty

    def test_trend_single_row(self, single_row_df):
        trend = SalesService(single_row_df).get_trend('D')
        assert len(trend) == 1


class TestSalesServiceCategorySales:
    def test_category_sales_normal(self, sample_orders_df):
        result = SalesService(sample_orders_df).get_category_sales()
        assert not result.empty
        assert '销售额' in result.columns
        assert '订单数' in result.columns
        assert '客单价' in result.columns
        assert '占比' in result.columns
        assert result['占比'].sum() == pytest.approx(1.0, abs=0.01)
        assert result.iloc[0]['销售额'] >= result.iloc[-1]['销售额']

    def test_category_sales_empty(self, empty_df):
        result = SalesService(empty_df).get_category_sales()
        assert result.empty

    def test_category_sales_single_category(self):
        df = pd.DataFrame({
            'order_id': ['O1', 'O2'], 'user_id': ['U1', 'U2'],
            'product_category': ['电子产品', '电子产品'],
            'amount': [100.0, 200.0], 'quantity': [1, 1],
            'order_time': pd.to_datetime(['2025-01-01', '2025-01-02']),
            'region': ['北京', '上海'], 'channel': ['APP', 'APP'],
        })
        result = SalesService(df).get_category_sales()
        assert len(result) == 1
        assert result.iloc[0]['销售额'] == 300.0


class TestSalesServiceRegionSales:
    def test_region_sales_normal(self, sample_orders_df):
        result = SalesService(sample_orders_df).get_region_sales()
        assert not result.empty
        assert '销售额' in result.columns
        assert '客单价' in result.columns

    def test_region_sales_empty(self, empty_df):
        assert SalesService(empty_df).get_region_sales().empty


class TestSalesServiceTopOrders:
    def test_top_orders_default(self, sample_orders_df):
        result = SalesService(sample_orders_df).get_top_orders()
        assert len(result) <= 20
        assert '订单号' in result.columns
        assert result.iloc[0]['金额(¥)'] >= result.iloc[-1]['金额(¥)']

    def test_top_orders_custom_n(self, sample_orders_df):
        result = SalesService(sample_orders_df).get_top_orders(5)
        assert len(result) == 5

    def test_top_orders_empty(self, empty_df):
        assert SalesService(empty_df).get_top_orders().empty


class TestSalesServiceWaterfall:
    def test_waterfall_normal(self, sample_orders_df, prev_period_df):
        svc = SalesService(sample_orders_df, sample_orders_df, prev_period_df)
        result = svc.get_waterfall_data()
        assert result is not None
        assert result[0][2] == 'total'
        assert result[-1][2] == 'total'
        for item in result[1:-1]:
            assert item[2] == 'relative'

    def test_waterfall_no_prev(self, sample_orders_df):
        svc = SalesService(sample_orders_df)
        assert svc.get_waterfall_data() is None

    def test_waterfall_empty(self, empty_df):
        assert SalesService(empty_df).get_waterfall_data() is None

    def test_waterfall_totals_consistency(self, sample_orders_df, prev_period_df):
        svc = SalesService(sample_orders_df, sample_orders_df, prev_period_df)
        result = svc.get_waterfall_data()
        initial_total = result[0][1]
        final_total = result[-1][1]
        relative_sum = sum(item[1] for item in result[1:-1])
        assert abs(initial_total + relative_sum - final_total) < 1.0
