import pandas as pd
from utils.config import get as cfg


class SalesService:
    def __init__(self, filtered_df, full_df=None, prev_df=None):
        self.df = filtered_df if filtered_df is not None else pd.DataFrame()
        self.full_df = full_df if full_df is not None else self.df
        self.prev_df = prev_df if prev_df is not None else pd.DataFrame()

    def get_kpi(self):
        if self.df.empty:
            return {
                'total_sales': 0, 'total_orders': 0, 'avg_order_value': 0,
                'sales_mom': None, 'orders_mom': None, 'aov_mom': None
            }
        total_sales = self.df['amount'].sum()
        total_orders = len(self.df)
        avg_order_value = total_sales / total_orders if total_orders > 0 else 0

        sales_mom = orders_mom = aov_mom = None
        if not self.prev_df.empty:
            prev_sales = self.prev_df['amount'].sum()
            prev_orders = len(self.prev_df)
            prev_aov = prev_sales / prev_orders if prev_orders > 0 else 0
            sales_mom = self._calc_growth(total_sales, prev_sales)
            orders_mom = self._calc_growth(total_orders, prev_orders)
            aov_mom = self._calc_growth(avg_order_value, prev_aov)

        return {
            'total_sales': total_sales,
            'total_orders': total_orders,
            'avg_order_value': avg_order_value,
            'sales_mom': sales_mom,
            'orders_mom': orders_mom,
            'aov_mom': aov_mom
        }

    @staticmethod
    def _calc_growth(current, previous):
        if previous is None or previous == 0:
            return None
        return (current - previous) / previous * 100

    def get_repeat_rate(self):
        if self.df.empty:
            return 0, 0, 0
        total_users = self.df['user_id'].nunique()
        order_counts = self.df.groupby('user_id').size()
        repeat_users = (order_counts > 1).sum()
        repeat_rate = repeat_users / total_users * 100 if total_users > 0 else 0
        return repeat_rate, repeat_users, total_users

    def get_trend(self, freq='D'):
        if self.df.empty:
            return pd.DataFrame()
        freq_map = {'D': '日', 'W': '周', 'M': '月'}
        agg = self.df.set_index('order_time').resample(freq).agg(
            销售额=('amount', 'sum'),
            订单数=('order_id', 'count'),
            客单价=('amount', 'mean')
        ).reset_index()
        agg['order_time'] = agg['order_time'].dt.strftime('%Y-%m-%d')
        agg.columns = [f'时间({freq_map.get(freq, freq)})', '销售额', '订单数', '客单价']
        return agg

    def get_category_sales(self):
        if self.df.empty:
            return pd.DataFrame()
        cat_agg = self.df.groupby('product_category').agg(
            销售额=('amount', 'sum'),
            订单数=('order_id', 'count'),
            用户数=('user_id', 'nunique')
        ).reset_index()
        cat_agg['客单价'] = (cat_agg['销售额'] / cat_agg['订单数']).round(2)
        cat_agg['占比'] = cat_agg['销售额'] / cat_agg['销售额'].sum()
        return cat_agg.sort_values('销售额', ascending=False)

    def get_region_sales(self):
        if self.df.empty:
            return pd.DataFrame()
        reg_agg = self.df.groupby('region').agg(
            销售额=('amount', 'sum'),
            订单数=('order_id', 'count'),
            用户数=('user_id', 'nunique')
        ).reset_index()
        reg_agg['客单价'] = (reg_agg['销售额'] / reg_agg['订单数']).round(2)
        return reg_agg

    def get_top_orders(self, n=20):
        if self.df.empty:
            return pd.DataFrame()
        show_df = self.df.sort_values('amount', ascending=False).head(n)[
            ['order_id', 'user_id', 'product_category', 'amount', 'quantity',
             'order_time', 'region', 'channel']
        ].copy()
        show_df['order_time'] = show_df['order_time'].dt.strftime('%Y-%m-%d %H:%M')
        show_df.columns = ['订单号', '用户ID', '品类', '金额(¥)', '数量',
                           '下单时间', '地区', '渠道']
        return show_df

    def get_waterfall_data(self):
        if self.df.empty or self.prev_df.empty:
            return None
        cat_agg = self.get_category_sales()
        prev_cat_agg = self.prev_df.groupby('product_category').agg(
            销售额=('amount', 'sum'),
            订单数=('order_id', 'count')
        ).reset_index()

        waterfall_data = []
        initial_total = prev_cat_agg['销售额'].sum()
        waterfall_data.append(("前期合计", initial_total, 'total'))

        for _, row in cat_agg.iterrows():
            cat = row['product_category']
            cur_sales = row['销售额']
            prev_sales = prev_cat_agg[prev_cat_agg['product_category'] == cat]['销售额'].sum()
            waterfall_data.append((cat, cur_sales - prev_sales, 'relative'))

        final_total = cat_agg['销售额'].sum()
        waterfall_data.append(("本期合计", final_total, 'total'))
        return waterfall_data
