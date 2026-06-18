import pandas as pd
import numpy as np
from datetime import datetime

SAMPLE_THRESHOLD = 10000
SAMPLE_SIZE = 10000

USER_LEVELS = {
    '高价值用户': {'R': (0, 0.4), 'F': (0.6, 1.0), 'M': (0.6, 1.0)},
    '潜力用户': {'R': (0, 0.5), 'F': (0.3, 0.6), 'M': (0.3, 0.6)},
    '流失预警': {'R': (0.5, 0.8), 'F': (0, 0.4), 'M': (0, 0.4)},
    '沉睡用户': {'R': (0.8, 1.0), 'F': (0, 0.3), 'M': (0, 0.3)},
}


def calculate_rfm(df, analysis_date=None):
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()

    if analysis_date is None:
        analysis_date = df['order_time'].max()

    rfm = df.groupby('user_id').agg(
        Recency=('order_time', lambda x: (analysis_date - x.max()).days),
        Frequency=('order_id', 'count'),
        Monetary=('amount', 'sum')
    ).reset_index()

    rfm.columns = ['user_id', 'Recency', 'Frequency', 'Monetary']

    rfm['R_Score'] = pd.qcut(rfm['Recency'].rank(method='first'), q=5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm['F_Score'] = pd.qcut(rfm['Frequency'].rank(method='first'), q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm['M_Score'] = pd.qcut(rfm['Monetary'].rank(method='first'), q=5, labels=[1, 2, 3, 4, 5]).astype(int)

    rfm['R_Rank'] = rfm['Recency'].rank(pct=True)
    rfm['F_Rank'] = 1 - rfm['Frequency'].rank(pct=True)
    rfm['M_Rank'] = 1 - rfm['Monetary'].rank(pct=True)

    def classify_user(row):
        r, f, m = row['R_Rank'], row['F_Rank'], row['M_Rank']
        if r <= 0.4 and f >= 0.6 and m >= 0.6:
            return '高价值用户'
        elif r <= 0.5 and (f >= 0.3 or m >= 0.3):
            return '潜力用户'
        elif r >= 0.8:
            return '沉睡用户'
        elif r >= 0.5:
            return '流失预警'
        else:
            return '普通用户'

    rfm['用户等级'] = rfm.apply(classify_user, axis=1)
    rfm['RFM_Score'] = rfm['R_Score'] * 100 + rfm['F_Score'] * 10 + rfm['M_Score']

    level_stats = rfm.groupby('用户等级').agg(
        用户数=('user_id', 'count'),
        平均消费=('Monetary', 'mean'),
        平均频次=('Frequency', 'mean'),
        平均最近天数=('Recency', 'mean'),
        总消费=('Monetary', 'sum')
    ).reset_index()

    level_stats['用户占比(%)'] = (level_stats['用户数'] / level_stats['用户数'].sum() * 100).round(2)
    level_stats['消费占比(%)'] = (level_stats['总消费'] / level_stats['总消费'].sum() * 100).round(2)
    level_stats['平均消费'] = level_stats['平均消费'].round(2)
    level_stats['平均频次'] = level_stats['平均频次'].round(2)
    level_stats['平均最近天数'] = level_stats['平均最近天数'].round(1)

    return rfm, level_stats


def calculate_retention(df):
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()

    user_first = df.groupby('user_id')['order_time'].min().reset_index()
    user_first.columns = ['user_id', 'first_order_month']
    user_first['first_order_month'] = user_first['first_order_month'].dt.to_period('M')

    df_order = df.merge(user_first, on='user_id', how='left')
    df_order['order_month'] = df_order['order_time'].dt.to_period('M')
    df_order['cohort_index'] = (df_order['order_month'] - df_order['first_order_month']).apply(
        lambda x: x.n if hasattr(x, 'n') else (x.days // 30)
    )

    cohort_data = df_order.groupby(['first_order_month', 'cohort_index']).agg(
        用户数=('user_id', 'nunique')
    ).reset_index()

    cohort_pivot = cohort_data.pivot(
        index='first_order_month',
        columns='cohort_index',
        values='用户数'
    )

    cohort_size = cohort_pivot.iloc[:, 0]
    retention_matrix = cohort_pivot.divide(cohort_size, axis=0) * 100

    cohort_pivot_display = cohort_pivot.copy()
    cohort_pivot_display.index = cohort_pivot_display.index.astype(str)
    retention_display = retention_matrix.copy()
    retention_display.index = retention_display.index.astype(str)
    retention_display = retention_display.round(2)

    return retention_display, cohort_pivot_display


def get_user_level_orders(df, rfm_df, level_name):
    if rfm_df is None or rfm_df.empty:
        return pd.DataFrame()
    target_users = rfm_df[rfm_df['用户等级'] == level_name]['user_id'].unique()
    orders = df[df['user_id'].isin(target_users)].copy()
    if 'order_time' in orders.columns:
        orders['order_time'] = orders['order_time'].dt.strftime('%Y-%m-%d %H:%M')
    orders.columns = ['订单号', '用户ID', '品类', '金额(¥)', '数量',
                   '下单时间', '地区', '渠道']
    return orders.sort_values('金额(¥)', ascending=False)


def sample_rfm_for_display(rfm_df, threshold=SAMPLE_THRESHOLD, sample_size=SAMPLE_SIZE):
    if rfm_df is None or rfm_df.empty:
        return rfm_df, False
    if len(rfm_df) <= threshold:
        return rfm_df, False
    np.random.seed(42)
    sampled = rfm_df.groupby('用户等级', group_keys=False).apply(
        lambda x: x.sample(n=max(1, int(sample_size * len(x) / len(rfm_df))), random_state=42),
    ).reset_index(drop=True)
    return sampled, True
