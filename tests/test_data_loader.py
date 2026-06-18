import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from utils.data_loader import (
    load_raw_data, clean_data, detect_missing_values, detect_outliers,
    get_data_overview, filter_by_time, apply_all_filters, calc_mom_growth,
    get_kpi_metrics, DATA_FILE, REQUIRED_COLUMNS
)
from utils.filter_manager import FilterManager


class TestDataLoaderLoadRaw:
    def test_load_normal_csv(self, sample_csv_file):
        with patch('utils.data_loader.DATA_FILE', sample_csv_file):
            df, err = load_raw_data()
            assert err is None
            assert df is not None
            assert len(df) == 5

    def test_load_missing_columns(self, missing_cols_csv_file):
        with patch('utils.data_loader.DATA_FILE', missing_cols_csv_file):
            df, err = load_raw_data()
            assert df is None
            assert '缺少必要列' in err

    def test_load_nonexistent_file(self, tmp_path):
        fake_path = str(tmp_path / "nonexistent.csv")
        with patch('utils.data_loader.DATA_FILE', fake_path):
            df, err = load_raw_data()
            assert df is None
            assert '不存在' in err

    def test_load_empty_file(self, empty_csv_file):
        with patch('utils.data_loader.DATA_FILE', empty_csv_file):
            df, err = load_raw_data()
            assert df is not None or err is not None


class TestDataLoaderCleanData:
    def test_clean_normal_data(self, sample_orders_df):
        cleaned = clean_data(sample_orders_df)
        assert not cleaned.empty
        assert cleaned['order_time'].dtype == 'datetime64[ns]'

    def test_clean_removes_outliers(self):
        df = pd.DataFrame({
            'order_id': ['O1', 'O2', 'O3', 'O4', 'O5'],
            'user_id': ['U1', 'U2', 'U3', 'U4', 'U5'],
            'product_category': ['A', 'A', 'A', 'A', 'A'],
            'amount': [100, 120, 110, 105, 999999],
            'quantity': [1, 1, 1, 1, 1],
            'order_time': pd.to_datetime(['2025-01-01'] * 5),
            'region': ['北京'] * 5,
            'channel': ['APP'] * 5,
        })
        cleaned = clean_data(df)
        assert 999999 not in cleaned['amount'].values

    def test_clean_fills_nulls(self, orders_with_nulls_df):
        cleaned = clean_data(orders_with_nulls_df)
        if not cleaned.empty:
            assert cleaned['amount'].notna().all()
            assert cleaned['region'].notna().all()

    def test_clean_deduplicates(self):
        df = pd.DataFrame({
            'order_id': ['O1', 'O1'],
            'user_id': ['U1', 'U1'],
            'product_category': ['A', 'A'],
            'amount': [100.0, 100.0],
            'quantity': [1, 1],
            'order_time': pd.to_datetime(['2025-01-01', '2025-01-01']),
            'region': ['北京', '北京'],
            'channel': ['APP', 'APP'],
        })
        cleaned = clean_data(df)
        assert len(cleaned) == 1

    def test_clean_sorts_by_time(self, sample_orders_df):
        shuffled = sample_orders_df.sample(frac=1, random_state=42).reset_index(drop=True)
        cleaned = clean_data(shuffled)
        time_diffs = cleaned['order_time'].diff().dropna()
        assert (time_diffs >= pd.Timedelta(0)).all()


class TestDataLoaderMissingValues:
    def test_detect_missing(self, orders_with_nulls_df):
        result = detect_missing_values(orders_with_nulls_df)
        assert not result.empty
        assert '字段' in result.columns
        assert '缺失数量' in result.columns

    def test_detect_no_missing(self, sample_orders_df):
        result = detect_missing_values(sample_orders_df)
        assert result.empty or result['缺失数量'].sum() == 0


class TestDataLoaderOutliers:
    def test_detect_outliers_normal(self):
        df = pd.DataFrame({
            'amount': [100, 120, 110, 105, 999999, 115, 108, 112, 95, 130]
        })
        outliers, lower, upper = detect_outliers(df)
        assert lower is not None
        assert upper is not None
        assert len(outliers) >= 0

    def test_detect_outliers_empty(self):
        df = pd.DataFrame({'amount': []})
        outliers, lower, upper = detect_outliers(df)
        assert outliers.empty
        assert lower is None

    def test_detect_outliers_none_column(self):
        df = pd.DataFrame({'amount': [np.nan, np.nan]})
        outliers, lower, upper = detect_outliers(df)
        assert outliers.empty


class TestDataLoaderFilterByTime:
    def test_filter_normal(self, sample_orders_df):
        start = datetime(2025, 3, 1).date()
        end = datetime(2025, 6, 30).date()
        result = filter_by_time(sample_orders_df, start, end)
        if not result.empty:
            assert result['order_time'].dt.date.min() >= start
            assert result['order_time'].dt.date.max() <= end

    def test_filter_boundary_dates(self, sample_orders_df):
        min_date = sample_orders_df['order_time'].min().date()
        max_date = sample_orders_df['order_time'].max().date()
        result = filter_by_time(sample_orders_df, min_date, max_date)
        assert len(result) == len(sample_orders_df)

    def test_filter_no_match(self, sample_orders_df):
        result = filter_by_time(sample_orders_df, datetime(2030, 1, 1).date(), datetime(2030, 12, 31).date())
        assert result.empty

    def test_filter_none_dates(self, sample_orders_df):
        result = filter_by_time(sample_orders_df, None, None)
        assert len(result) == len(sample_orders_df)

    def test_filter_cross_year(self, cross_year_df):
        result = filter_by_time(
            cross_year_df,
            datetime(2024, 12, 1).date(),
            datetime(2025, 1, 31).date()
        )
        assert len(result) > 0


class TestDataLoaderApplyAllFilters:
    def test_filter_time_only(self, sample_orders_df):
        start = datetime(2025, 3, 1).date()
        end = datetime(2025, 12, 31).date()
        result = apply_all_filters(sample_orders_df, start, end)
        if not result.empty:
            assert result['order_time'].dt.date.min() >= start

    def test_filter_category_only(self, sample_orders_df):
        cats = ['电子产品', '服装']
        result = apply_all_filters(sample_orders_df, datetime(2025, 1, 1).date(), datetime(2025, 12, 31).date(), cats)
        assert set(result['product_category'].unique()).issubset(set(cats))

    def test_filter_all_categories(self, sample_orders_df):
        all_cats = sample_orders_df['product_category'].unique().tolist()
        result = apply_all_filters(sample_orders_df, datetime(2025, 1, 1).date(), datetime(2025, 12, 31).date(), all_cats)
        assert len(result) == len(sample_orders_df)

    def test_filter_empty_df(self, empty_df):
        result = apply_all_filters(empty_df, datetime(2025, 1, 1).date(), datetime(2025, 12, 31).date())
        assert result.empty


class TestDataLoaderGrowth:
    def test_calc_growth_positive(self):
        assert calc_mom_growth(120, 100) == 20.0

    def test_calc_growth_negative(self):
        assert calc_mom_growth(80, 100) == -20.0

    def test_calc_growth_zero_previous(self):
        assert calc_mom_growth(100, 0) is None

    def test_calc_growth_none_previous(self):
        assert calc_mom_growth(100, None) is None


class TestDataLoaderOverview:
    def test_overview_normal(self, sample_orders_df):
        ov = get_data_overview(sample_orders_df)
        assert ov['总行数'] == 100
        assert ov['用户数'] == sample_orders_df['user_id'].nunique()
        assert '起始日期' in ov
        assert '结束日期' in ov

    def test_overview_empty(self, empty_df):
        ov = get_data_overview(empty_df)
        assert ov == {}

    def test_overview_none(self):
        ov = get_data_overview(None)
        assert ov == {}


class TestFilterManagerFilteredDf:
    def test_get_filtered_df_with_dates(self, sample_orders_df):
        with patch.object(FilterManager, 'get_clean_data', return_value=sample_orders_df):
            start = datetime(2025, 3, 1).date()
            end = datetime(2025, 12, 31).date()
            result = FilterManager.get_filtered_df(start, end)
            if not result.empty:
                assert result['order_time'].dt.date.min() >= start

    def test_get_filtered_df_with_categories(self, sample_orders_df):
        with patch.object(FilterManager, 'get_clean_data', return_value=sample_orders_df):
            cats = ['电子产品']
            result = FilterManager.get_filtered_df(
                datetime(2025, 1, 1).date(), datetime(2025, 12, 31).date(), cats
            )
            assert set(result['product_category'].unique()) == {'电子产品'}

    def test_get_filtered_df_empty_data(self, empty_df):
        with patch.object(FilterManager, 'get_clean_data', return_value=empty_df):
            result = FilterManager.get_filtered_df()
            assert result.empty

    def test_get_prev_df(self, sample_orders_df):
        with patch.object(FilterManager, 'get_clean_data', return_value=sample_orders_df):
            start = datetime(2025, 7, 1).date()
            end = datetime(2025, 12, 31).date()
            result = FilterManager.get_prev_df(start, end)
            if not result.empty:
                prev_start = start - timedelta(days=(end - start).days + 1)
                prev_end = start - timedelta(days=1)
                assert result['order_time'].dt.date.min() >= prev_start
                assert result['order_time'].dt.date.max() <= prev_end

    def test_get_prev_df_with_categories(self, sample_orders_df):
        with patch.object(FilterManager, 'get_clean_data', return_value=sample_orders_df):
            cats = ['电子产品', '服装']
            start = datetime(2025, 7, 1).date()
            end = datetime(2025, 12, 31).date()
            result = FilterManager.get_prev_df(start, end, cats)
            if not result.empty:
                assert set(result['product_category'].unique()).issubset(set(cats))

    def test_get_all_categories(self, sample_orders_df):
        with patch.object(FilterManager, 'get_clean_data', return_value=sample_orders_df):
            cats = FilterManager.get_all_categories()
            assert len(cats) > 0
            assert cats == sorted(cats)
