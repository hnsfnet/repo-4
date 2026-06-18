import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import tempfile
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)


@pytest.fixture
def sample_orders_df():
    np.random.seed(42)
    n = 100
    categories = ['电子产品', '服装', '食品', '家居', '图书']
    channels = ['APP', '小程序', 'H5', 'PC端']
    regions = ['北京', '上海', '广东', '浙江', '四川', '湖北']
    user_ids = [f'U{i:03d}' for i in range(1, 21)]

    start = datetime(2025, 1, 1)
    dates = [start + timedelta(days=np.random.randint(0, 365)) for _ in range(n)]

    df = pd.DataFrame({
        'order_id': [f'ORD{i:05d}' for i in range(1, n + 1)],
        'user_id': np.random.choice(user_ids, n),
        'product_category': np.random.choice(categories, n),
        'amount': np.round(np.random.uniform(10, 2000, n), 2),
        'quantity': np.random.randint(1, 10, n),
        'order_time': sorted(dates),
        'region': np.random.choice(regions, n),
        'channel': np.random.choice(channels, n),
    })
    return df


@pytest.fixture
def small_orders_df():
    return pd.DataFrame({
        'order_id': ['ORD001', 'ORD002', 'ORD003'],
        'user_id': ['U001', 'U001', 'U002'],
        'product_category': ['电子产品', '服装', '食品'],
        'amount': [1000.0, 500.0, 200.0],
        'quantity': [2, 1, 3],
        'order_time': pd.to_datetime(['2025-01-15', '2025-02-20', '2025-03-10']),
        'region': ['北京', '上海', '广东'],
        'channel': ['APP', '小程序', 'H5'],
    })


@pytest.fixture
def single_row_df():
    return pd.DataFrame({
        'order_id': ['ORD001'],
        'user_id': ['U001'],
        'product_category': ['电子产品'],
        'amount': [500.0],
        'quantity': [1],
        'order_time': pd.to_datetime(['2025-06-01']),
        'region': ['北京'],
        'channel': ['APP'],
    })


@pytest.fixture
def empty_df():
    return pd.DataFrame()


@pytest.fixture
def orders_with_nulls_df():
    return pd.DataFrame({
        'order_id': ['ORD001', 'ORD002', 'ORD003', 'ORD004'],
        'user_id': ['U001', 'U002', 'U001', 'U003'],
        'product_category': ['电子产品', None, '服装', '食品'],
        'amount': [1000.0, None, 300.0, 200.0],
        'quantity': [2, 1, 1, 3],
        'order_time': pd.to_datetime(['2025-01-15', '2025-02-20', '2025-03-10', '2025-04-05']),
        'region': ['北京', None, '上海', '广东'],
        'channel': ['APP', '小程序', None, 'H5'],
    })


@pytest.fixture
def retention_df():
    dates = []
    user_ids = []
    orders = []
    oid = 1

    users_by_month = {
        '2025-01': ['U001', 'U002', 'U003'],
        '2025-02': ['U002', 'U003', 'U004'],
        '2025-03': ['U003', 'U004', 'U005'],
    }
    return_rates = {
        ('U002', '2025-02'): True,
        ('U003', '2025-02'): True,
        ('U003', '2025-03'): True,
        ('U004', '2025-03'): True,
    }

    for month, users in users_by_month.items():
        for u in users:
            dt = pd.Timestamp(month + '-15')
            orders.append({
                'order_id': f'ORD{oid:03d}',
                'user_id': u,
                'product_category': '电子产品',
                'amount': 100.0,
                'quantity': 1,
                'order_time': dt,
                'region': '北京',
                'channel': 'APP',
            })
            oid += 1

    for (uid, month), _ in return_rates.items():
        dt = pd.Timestamp(month + '-20')
        orders.append({
            'order_id': f'ORD{oid:03d}',
            'user_id': uid,
            'product_category': '服装',
            'amount': 200.0,
            'quantity': 1,
            'order_time': dt,
            'region': '上海',
            'channel': '小程序',
        })
        oid += 1

    return pd.DataFrame(orders)


@pytest.fixture
def large_rfm_df():
    np.random.seed(42)
    n = 15000
    return pd.DataFrame({
        'user_id': [f'U{i:05d}' for i in range(n)],
        'Recency': np.random.randint(0, 365, n),
        'Frequency': np.random.randint(1, 50, n),
        'Monetary': np.round(np.random.uniform(100, 50000, n), 2),
        'R_Score': np.random.randint(1, 6, n),
        'F_Score': np.random.randint(1, 6, n),
        'M_Score': np.random.randint(1, 6, n),
        'R_Rank': np.random.uniform(0, 1, n),
        'F_Rank': np.random.uniform(0, 1, n),
        'M_Rank': np.random.uniform(0, 1, n),
        'RFM_Score': np.random.randint(111, 556, n),
        '用户等级': np.random.choice(['高价值用户', '潜力用户', '流失预警', '沉睡用户', '普通用户'], n),
    })


@pytest.fixture
def sample_csv_file(tmp_path):
    csv_content = """order_id,user_id,product_category,amount,quantity,order_time,region,channel
ORD001,U001,电子产品,1500.0,2,2025-01-15 10:30,北京,APP
ORD002,U002,服装,500.0,1,2025-02-20 14:00,上海,小程序
ORD003,U001,食品,200.0,3,2025-03-10 09:15,广东,H5
ORD004,U003,家居,800.0,1,2025-04-05 16:45,浙江,PC端
ORD005,U002,图书,150.0,2,2025-05-12 11:00,四川,APP
"""
    csv_path = tmp_path / "test_orders.csv"
    csv_path.write_text(csv_content, encoding='utf-8-sig')
    return str(csv_path)


@pytest.fixture
def missing_cols_csv_file(tmp_path):
    csv_content = """order_id,user_id,amount
ORD001,U001,1500.0
"""
    csv_path = tmp_path / "bad_orders.csv"
    csv_path.write_text(csv_content, encoding='utf-8-sig')
    return str(csv_path)


@pytest.fixture
def empty_csv_file(tmp_path):
    csv_path = tmp_path / "empty_orders.csv"
    csv_path.write_text("", encoding='utf-8-sig')
    return str(csv_path)


@pytest.fixture
def prev_period_df():
    np.random.seed(99)
    n = 50
    categories = ['电子产品', '服装', '食品', '家居', '图书']
    channels = ['APP', '小程序', 'H5', 'PC端']
    regions = ['北京', '上海', '广东', '浙江', '四川']
    user_ids = [f'U{i:03d}' for i in range(1, 16)]

    start = datetime(2024, 1, 1)
    dates = [start + timedelta(days=np.random.randint(0, 180)) for _ in range(n)]

    return pd.DataFrame({
        'order_id': [f'PORD{i:05d}' for i in range(1, n + 1)],
        'user_id': np.random.choice(user_ids, n),
        'product_category': np.random.choice(categories, n),
        'amount': np.round(np.random.uniform(10, 1500, n), 2),
        'quantity': np.random.randint(1, 8, n),
        'order_time': sorted(dates),
        'region': np.random.choice(regions, n),
        'channel': np.random.choice(channels, n),
    })


@pytest.fixture
def cross_year_df():
    records = []
    oid = 1
    for month in ['2024-11', '2024-12', '2025-01', '2025-02']:
        for uid in ['U001', 'U002']:
            records.append({
                'order_id': f'ORD{oid:04d}',
                'user_id': uid,
                'product_category': '电子产品',
                'amount': 500.0,
                'quantity': 1,
                'order_time': pd.Timestamp(f'{month}-15'),
                'region': '北京',
                'channel': 'APP',
            })
            oid += 1
    return pd.DataFrame(records)
