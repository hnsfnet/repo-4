import pytest
import pandas as pd
import numpy as np
from services.channel_service import ChannelService


class TestChannelServiceAgg:
    def test_channel_agg_normal(self, sample_orders_df):
        result = ChannelService(sample_orders_df).get_channel_agg()
        assert not result.empty
        assert '销售额' in result.columns
        assert '订单数' in result.columns
        assert '客单价' in result.columns
        assert '件单价' in result.columns
        assert result.iloc[0]['销售额'] >= result.iloc[-1]['销售额']

    def test_channel_agg_empty(self, empty_df):
        assert ChannelService(empty_df).get_channel_agg().empty

    def test_channel_agg_single_channel(self):
        df = pd.DataFrame({
            'order_id': ['O1', 'O2'], 'user_id': ['U1', 'U2'],
            'product_category': ['A', 'A'], 'amount': [100.0, 200.0],
            'quantity': [1, 2], 'order_time': pd.to_datetime(['2025-01-01', '2025-01-02']),
            'region': ['北京', '上海'], 'channel': ['APP', 'APP'],
        })
        result = ChannelService(df).get_channel_agg()
        assert len(result) == 1
        assert result.iloc[0]['销售额'] == 300.0


class TestChannelServiceFunnel:
    def test_funnel_normal(self, sample_orders_df):
        svc = ChannelService(sample_orders_df)
        stages, counts = svc.get_funnel_data()
        assert len(stages) == 5
        assert len(counts) == 5
        assert stages[0] == "曝光用户"
        assert stages[-1] == "成交用户"
        for i in range(len(counts) - 1):
            assert counts[i] >= counts[i + 1]

    def test_funnel_empty(self, empty_df):
        stages, counts = ChannelService(empty_df).get_funnel_data()
        assert stages == []
        assert counts == []

    def test_funnel_with_precomputed_agg(self, sample_orders_df):
        svc = ChannelService(sample_orders_df)
        ch_agg = svc.get_channel_agg()
        stages, counts = svc.get_funnel_data(ch_agg)
        assert len(stages) == 5

    def test_funnel_ratio_reasonable(self, sample_orders_df):
        _, counts = ChannelService(sample_orders_df).get_funnel_data()
        if counts:
            assert counts[0] > 0
            assert counts[-1] > 0
            assert counts[0] >= counts[-1]


class TestChannelServiceROI:
    def test_roi_normal(self, sample_orders_df):
        svc = ChannelService(sample_orders_df)
        ch_agg = svc.get_channel_agg()
        roi = svc.get_roi_data(ch_agg)
        assert not roi.empty
        assert '投入成本' in roi.columns
        assert '毛利' in roi.columns
        assert 'ROI' in roi.columns
        assert 'ROI等级' in roi.columns
        for level in roi['ROI等级']:
            assert level in ('excellent', 'qualified', 'poor')

    def test_roi_empty(self, empty_df):
        assert ChannelService(empty_df).get_roi_data().empty

    def test_roi_formula(self):
        df = pd.DataFrame({
            'order_id': ['O1'], 'user_id': ['U1'],
            'product_category': ['A'], 'amount': [1000.0],
            'quantity': [2], 'order_time': pd.to_datetime(['2025-01-01']),
            'region': ['北京'], 'channel': ['APP'],
        })
        svc = ChannelService(df)
        ch_agg = svc.get_channel_agg()
        roi = svc.get_roi_data(ch_agg)
        assert len(roi) == 1
        row = roi.iloc[0]
        expected_cost = 1000.0 * 0.15
        expected_profit = 1000.0 * 0.45
        expected_roi = round(expected_profit / expected_cost, 2)
        assert row['投入成本'] == pytest.approx(expected_cost)
        assert row['毛利'] == pytest.approx(expected_profit)
        assert row['ROI'] == pytest.approx(expected_roi, abs=0.01)

    def test_roi_levels(self, sample_orders_df):
        svc = ChannelService(sample_orders_df)
        ch_agg = svc.get_channel_agg()
        roi = svc.get_roi_data(ch_agg)
        excellent = roi[roi['ROI等级'] == 'excellent']
        qualified = roi[roi['ROI等级'] == 'qualified']
        poor = roi[roi['ROI等级'] == 'poor']
        if not excellent.empty:
            assert (excellent['ROI'] >= 2.0).all()
        if not poor.empty:
            assert (poor['ROI'] < 1.5).all()


class TestChannelServiceRegion:
    def test_region_agg_normal(self, sample_orders_df):
        result = ChannelService(sample_orders_df).get_region_agg()
        assert not result.empty
        assert '销售额' in result.columns
        assert result.iloc[0]['销售额'] >= result.iloc[-1]['销售额']

    def test_region_agg_empty(self, empty_df):
        assert ChannelService(empty_df).get_region_agg().empty

    def test_region_growth_normal(self, sample_orders_df, prev_period_df):
        svc = ChannelService(sample_orders_df, prev_period_df)
        result = svc.get_region_growth()
        assert not result.empty
        assert '增速(%)' in result.columns
        assert '上期销售额' in result.columns

    def test_region_growth_no_prev(self, sample_orders_df):
        svc = ChannelService(sample_orders_df)
        assert svc.get_region_growth().empty

    def test_region_growth_empty(self, empty_df):
        assert ChannelService(empty_df, empty_df).get_region_growth().empty

    def test_region_growth_new_region(self):
        cur = pd.DataFrame({
            'order_id': ['O1', 'O2'], 'user_id': ['U1', 'U2'],
            'product_category': ['A', 'A'], 'amount': [500.0, 300.0],
            'quantity': [1, 1], 'order_time': pd.to_datetime(['2025-06-01', '2025-06-02']),
            'region': ['北京', '新疆'], 'channel': ['APP', 'APP'],
        })
        prev = pd.DataFrame({
            'order_id': ['O3'], 'user_id': ['U3'],
            'product_category': ['A'], 'amount': [200.0],
            'quantity': [1], 'order_time': pd.to_datetime(['2025-05-01']),
            'region': ['北京'], 'channel': ['APP'],
        })
        svc = ChannelService(cur, prev)
        result = svc.get_region_growth()
        xinjiang = result[result['region'] == '新疆']
        if not xinjiang.empty:
            assert xinjiang.iloc[0]['上期销售额'] == 0
