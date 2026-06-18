import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from services.user_service import UserService


class TestUserServiceRFM:
    def test_rfm_normal(self, sample_orders_df):
        svc = UserService(sample_orders_df)
        rfm_df, level_stats = svc.get_rfm()
        assert not rfm_df.empty
        assert not level_stats.empty
        assert 'Recency' in rfm_df.columns
        assert 'Frequency' in rfm_df.columns
        assert 'Monetary' in rfm_df.columns
        assert '用户等级' in rfm_df.columns
        assert 'RFM_Score' in rfm_df.columns
        assert '用户数' in level_stats.columns
        assert '用户占比(%)' in level_stats.columns
        assert level_stats['用户占比(%)'].sum() == pytest.approx(100.0, abs=0.1)

    def test_rfm_empty(self, empty_df):
        rfm_df, level_stats = UserService(empty_df).get_rfm()
        assert rfm_df.empty
        assert level_stats.empty

    def test_rfm_single_user(self, single_row_df):
        rfm_df, level_stats = UserService(single_row_df).get_rfm()
        assert len(rfm_df) == 1
        assert rfm_df.iloc[0]['Frequency'] == 1

    def test_rfm_analysis_date(self, sample_orders_df):
        analysis_date = datetime(2026, 1, 1)
        svc = UserService(sample_orders_df, analysis_date)
        rfm_df, _ = svc.get_rfm()
        max_order_date = sample_orders_df['order_time'].max()
        expected_recency = (analysis_date - max_order_date).days
        assert rfm_df['Recency'].max() >= expected_recency

    def test_rfm_scores_range(self, sample_orders_df):
        rfm_df, _ = UserService(sample_orders_df).get_rfm()
        assert rfm_df['R_Score'].between(1, 5).all()
        assert rfm_df['F_Score'].between(1, 5).all()
        assert rfm_df['M_Score'].between(1, 5).all()

    def test_rfm_monotonicity(self, sample_orders_df):
        rfm_df, _ = UserService(sample_orders_df).get_rfm()
        high_freq = rfm_df[rfm_df['Frequency'] > rfm_df['Frequency'].median()]
        low_freq = rfm_df[rfm_df['Frequency'] <= rfm_df['Frequency'].median()]
        if not high_freq.empty and not low_freq.empty:
            assert high_freq['F_Score'].mean() >= low_freq['F_Score'].mean()


class TestUserServiceClassification:
    def test_high_value_user(self):
        row = pd.Series({'R_Rank': 0.2, 'F_Rank': 0.7, 'M_Rank': 0.7})
        assert UserService._classify_user(row) == '高价值用户'

    def test_high_value_boundary(self):
        row = pd.Series({'R_Rank': 0.4, 'F_Rank': 0.6, 'M_Rank': 0.6})
        assert UserService._classify_user(row) == '高价值用户'

    def test_potential_user(self):
        row = pd.Series({'R_Rank': 0.45, 'F_Rank': 0.35, 'M_Rank': 0.2})
        assert UserService._classify_user(row) == '潜力用户'

    def test_potential_user_by_monetary(self):
        row = pd.Series({'R_Rank': 0.45, 'F_Rank': 0.1, 'M_Rank': 0.5})
        assert UserService._classify_user(row) == '潜力用户'

    def test_sleeping_user(self):
        row = pd.Series({'R_Rank': 0.85, 'F_Rank': 0.1, 'M_Rank': 0.1})
        assert UserService._classify_user(row) == '沉睡用户'

    def test_sleeping_boundary(self):
        row = pd.Series({'R_Rank': 0.8, 'F_Rank': 0.5, 'M_Rank': 0.5})
        assert UserService._classify_user(row) == '沉睡用户'

    def test_churn_warning(self):
        row = pd.Series({'R_Rank': 0.6, 'F_Rank': 0.2, 'M_Rank': 0.2})
        assert UserService._classify_user(row) == '流失预警'

    def test_churn_boundary(self):
        row = pd.Series({'R_Rank': 0.5, 'F_Rank': 0.1, 'M_Rank': 0.1})
        assert UserService._classify_user(row) == '流失预警'

    def test_normal_user(self):
        row = pd.Series({'R_Rank': 0.42, 'F_Rank': 0.2, 'M_Rank': 0.2})
        assert UserService._classify_user(row) == '普通用户'

    def test_all_levels_covered(self, sample_orders_df):
        rfm_df, level_stats = UserService(sample_orders_df).get_rfm()
        valid_levels = {'高价值用户', '潜力用户', '流失预警', '沉睡用户', '普通用户'}
        for level in rfm_df['用户等级'].unique():
            assert level in valid_levels


class TestUserServiceRetention:
    def test_retention_normal(self, retention_df):
        svc = UserService(retention_df)
        retention, cohort = svc.get_retention()
        assert not retention.empty
        assert not cohort.empty
        if 0 in retention.columns:
            col0_vals = retention[0].dropna()
            if not col0_vals.empty:
                assert all(col0_vals == 100.0)

    def test_retention_empty(self, empty_df):
        retention, cohort = UserService(empty_df).get_retention()
        assert retention.empty
        assert cohort.empty

    def test_retention_month_alignment(self):
        records = []
        oid = 1
        for y, m in [(2024, 11), (2024, 12), (2025, 1), (2025, 2)]:
            for uid in ['U001', 'U002']:
                records.append({
                    'order_id': f'ORD{oid:04d}', 'user_id': uid,
                    'product_category': '电子产品', 'amount': 100.0,
                    'quantity': 1, 'order_time': pd.Timestamp(f'{y}-{m:02d}-15'),
                    'region': '北京', 'channel': 'APP',
                })
                oid += 1
        df = pd.DataFrame(records)
        retention, cohort = UserService(df).get_retention()
        if not retention.empty:
            assert len(retention) >= 2

    def test_retention_cross_year(self, cross_year_df):
        retention, cohort = UserService(cross_year_df).get_retention()
        if not retention.empty:
            idx_str = [str(i) for i in retention.index]
            assert any('2024' in s for s in idx_str)
            assert any('2025' in s for s in idx_str)

    def test_retention_decreasing_trend(self, retention_df):
        retention, _ = UserService(retention_df).get_retention()
        if not retention.empty and len(retention.columns) > 1:
            for idx in retention.index:
                row = retention.loc[idx].dropna()
                if len(row) > 1:
                    for i in range(1, len(row)):
                        assert row.iloc[i] <= row.iloc[0]


class TestUserServiceLevelOrders:
    def test_level_orders_normal(self, sample_orders_df):
        svc = UserService(sample_orders_df)
        rfm_df, _ = svc.get_rfm()
        levels = rfm_df['用户等级'].unique()
        if len(levels) > 0:
            orders = svc.get_user_level_orders(rfm_df, levels[0])
            assert '订单号' in orders.columns
            assert '金额(¥)' in orders.columns

    def test_level_orders_invalid_level(self, sample_orders_df):
        svc = UserService(sample_orders_df)
        rfm_df, _ = svc.get_rfm()
        orders = svc.get_user_level_orders(rfm_df, '不存在的等级')
        assert orders.empty

    def test_level_orders_empty_rfm(self, empty_df):
        svc = UserService(empty_df)
        rfm_df, _ = svc.get_rfm()
        orders = svc.get_user_level_orders(rfm_df, '高价值用户')
        assert orders.empty


class TestUserServiceSampling:
    def test_sampling_below_threshold(self, sample_orders_df):
        rfm_df, _ = UserService(sample_orders_df).get_rfm()
        result, was_sampled = UserService.sample_rfm_for_display(rfm_df)
        assert was_sampled is False
        assert len(result) == len(rfm_df)

    def test_sampling_above_threshold(self, large_rfm_df):
        result, was_sampled = UserService.sample_rfm_for_display(
            large_rfm_df, threshold=10000, sample_size=10000
        )
        assert was_sampled is True
        assert len(result) <= 10000
        assert len(result) > 0

    def test_sampling_preserves_levels(self, large_rfm_df):
        result, _ = UserService.sample_rfm_for_display(
            large_rfm_df, threshold=100, sample_size=50
        )
        original_levels = set(large_rfm_df['用户等级'].unique())
        sampled_levels = set(result['用户等级'].unique())
        assert sampled_levels == original_levels

    def test_sampling_empty(self, empty_df):
        result, was_sampled = UserService.sample_rfm_for_display(empty_df)
        assert was_sampled is False

    def test_sampling_none(self):
        result, was_sampled = UserService.sample_rfm_for_display(None)
        assert was_sampled is False

    def test_sampling_custom_threshold(self, large_rfm_df):
        result, was_sampled = UserService.sample_rfm_for_display(
            large_rfm_df, threshold=100, sample_size=50
        )
        assert was_sampled is True
        assert len(result) <= 50
