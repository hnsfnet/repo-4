import pandas as pd
import numpy as np
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
DATA_FILE = os.path.join(DATA_DIR, 'orders.csv')

REQUIRED_COLUMNS = ['order_id', 'user_id', 'product_category', 'amount', 'quantity',
                    'order_time', 'region', 'channel']


def load_raw_data():
    if not os.path.exists(DATA_FILE):
        return None, f"数据文件不存在：{DATA_FILE}"
    try:
        df = pd.read_csv(DATA_FILE, encoding='utf-8-sig')
        missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing_cols:
            return None, f"缺少必要列：{', '.join(missing_cols)}"
        return df, None
    except Exception as e:
        return None, f"读取数据失败：{str(e)}"


def detect_missing_values(df):
    missing_stats = df.isnull().sum().reset_index()
    missing_stats.columns = ['字段', '缺失数量']
    missing_stats['缺失占比(%)'] = (missing_stats['缺失数量'] / len(df) * 100).round(2)
    missing_stats = missing_stats[missing_stats['缺失数量'] > 0]
    return missing_stats


def detect_outliers(df, column='amount', threshold=3):
    if df[column].dropna().empty:
        return pd.DataFrame(), None, None
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - threshold * IQR
    upper_bound = Q3 + threshold * IQR
    outliers = df[(df[column] < lower_bound) | (df[column] > upper_bound)]
    return outliers, lower_bound, upper_bound


def clean_data(df):
    cleaned = df.copy()
    cleaned['order_time'] = pd.to_datetime(cleaned['order_time'], errors='coerce')
    cleaned = cleaned.dropna(subset=['order_time'])
    
    if 'amount' in cleaned.columns:
        outliers_df, lower_bound, upper_bound = detect_outliers(cleaned, 'amount')
        if not outliers_df.empty:
            cleaned = cleaned[~cleaned.index.isin(outliers_df.index)]
        cleaned['amount'] = cleaned['amount'].fillna(cleaned['amount'].median())
        cleaned = cleaned[cleaned['amount'] >= 0]
    
    if 'quantity' in cleaned.columns:
        cleaned['quantity'] = cleaned['quantity'].fillna(cleaned['quantity'].median()).astype(int)
        cleaned = cleaned[cleaned['quantity'] > 0]
    
    if 'region' in cleaned.columns:
        cleaned['region'] = cleaned['region'].fillna('未知')
    
    if 'channel' in cleaned.columns:
        cleaned['channel'] = cleaned['channel'].fillna('未知')
    
    for col in ['order_id', 'user_id', 'product_category']:
        if col in cleaned.columns:
            cleaned[col] = cleaned[col].fillna('未知')
    
    cleaned = cleaned.drop_duplicates(subset=['order_id'], keep='first')
    cleaned = cleaned.sort_values('order_time').reset_index(drop=True)
    
    return cleaned


def get_data_overview(df):
    if df is None or df.empty:
        return {}
    overview = {
        '总行数': len(df),
        '时间范围': f"{df['order_time'].min().strftime('%Y-%m-%d')} 至 {df['order_time'].max().strftime('%Y-%m-%d')}",
        '起始日期': df['order_time'].min(),
        '结束日期': df['order_time'].max(),
        '用户数': df['user_id'].nunique(),
        '订单数': df['order_id'].nunique(),
        '品类数': df['product_category'].nunique(),
        '地区数': df['region'].nunique(),
        '渠道数': df['channel'].nunique(),
    }
    return overview


def filter_by_time(df, start_date, end_date):
    if df is None or df.empty:
        return df
    mask = (df['order_time'].dt.date >= start_date) & (df['order_time'].dt.date <= end_date)
    return df[mask]


def calc_mom_growth(current, previous):
    if previous is None or previous == 0:
        return None
    return (current - previous) / previous * 100


def get_kpi_metrics(df, full_df=None):
    if df is None or df.empty:
        return {
            'total_sales': 0, 'total_orders': 0, 'avg_order_value': 0,
            'sales_mom': None, 'orders_mom': None, 'aov_mom': None
        }
    total_sales = df['amount'].sum()
    total_orders = len(df)
    avg_order_value = total_sales / total_orders if total_orders > 0 else 0

    sales_mom = orders_mom = aov_mom = None
    if full_df is not None and not full_df.empty:
        min_date = df['order_time'].min()
        current_span = (df['order_time'].max() - min_date).days
        prev_start = min_date - pd.Timedelta(days=current_span + 1)
        prev_end = min_date - pd.Timedelta(days=1)
        prev_df = full_df[(full_df['order_time'].dt.date >= prev_start.date()) &
                          (full_df['order_time'].dt.date <= prev_end.date())]
        if not prev_df.empty:
            prev_sales = prev_df['amount'].sum()
            prev_orders = len(prev_df)
            prev_aov = prev_sales / prev_orders if prev_orders > 0 else 0
            sales_mom = calc_mom_growth(total_sales, prev_sales)
            orders_mom = calc_mom_growth(total_orders, prev_orders)
            aov_mom = calc_mom_growth(avg_order_value, prev_aov)

    return {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'avg_order_value': avg_order_value,
        'sales_mom': sales_mom,
        'orders_mom': orders_mom,
        'aov_mom': aov_mom
    }


def aggregate_sales_by_time(df, freq='D'):
    if df is None or df.empty:
        return pd.DataFrame()
    freq_map = {'D': '日', 'W': '周', 'M': '月'}
    agg = df.set_index('order_time').resample(freq).agg(
        销售额=('amount', 'sum'),
        订单数=('order_id', 'count'),
        客单价=('amount', 'mean')
    ).reset_index()
    agg['order_time'] = agg['order_time'].dt.strftime('%Y-%m-%d')
    agg.columns = [f'时间({freq_map.get(freq, freq)})', '销售额', '订单数', '客单价']
    return agg
