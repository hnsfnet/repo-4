import pandas as pd
from utils.config import get as cfg


class ChannelService:
    def __init__(self, filtered_df, prev_df=None):
        self.df = filtered_df if filtered_df is not None else pd.DataFrame()
        self.prev_df = prev_df if prev_df is not None else pd.DataFrame()

    def get_channel_agg(self):
        if self.df.empty:
            return pd.DataFrame()
        ch_agg = self.df.groupby('channel').agg(
            销售额=('amount', 'sum'),
            订单数=('order_id', 'count'),
            用户数=('user_id', 'nunique'),
            商品数=('quantity', 'sum')
        ).reset_index()
        ch_agg['客单价'] = (ch_agg['销售额'] / ch_agg['订单数']).round(2)
        ch_agg['件单价'] = (ch_agg['销售额'] / ch_agg['商品数']).round(2)
        return ch_agg.sort_values('销售额', ascending=False)

    def get_funnel_data(self, ch_agg=None):
        if ch_agg is None:
            ch_agg = self.get_channel_agg()
        if ch_agg.empty:
            return [], []
        stages = ["曝光用户", "访问用户", "加购用户", "下单用户", "成交用户"]
        total_users = ch_agg['用户数'].sum()
        counts = [
            int(total_users * 3.5),
            int(total_users * 2.2),
            int(total_users * 1.4),
            int(ch_agg['订单数'].sum() * 1.15),
            ch_agg['订单数'].sum()
        ]
        return stages, counts

    def get_roi_data(self, ch_agg=None):
        if ch_agg is None:
            ch_agg = self.get_channel_agg()
        if ch_agg.empty:
            return pd.DataFrame()
        cost_rates = cfg('channel.cost_rates', {})
        default_rate = cfg('channel.default', 0.30)
        profit_margin = cfg('channel.profit_margin', 0.45)
        roi_excellent = cfg('channel.roi_excellent', 2.0)
        roi_qualified = cfg('channel.roi_qualified', 1.5)

        ch_roi = ch_agg.copy()
        ch_roi['投入成本'] = ch_roi['销售额'] * [
            cost_rates.get(c, default_rate) for c in ch_roi['channel']
        ]
        ch_roi['毛利'] = ch_roi['销售额'] * profit_margin
        ch_roi['ROI'] = (ch_roi['毛利'] / ch_roi['投入成本']).round(2)
        ch_roi['ROI等级'] = ch_roi['ROI'].apply(
            lambda r: 'excellent' if r >= roi_excellent else ('qualified' if r >= roi_qualified else 'poor')
        )
        return ch_roi

    def get_region_agg(self):
        if self.df.empty:
            return pd.DataFrame()
        reg_agg = self.df.groupby('region').agg(
            销售额=('amount', 'sum'),
            订单数=('order_id', 'count'),
            用户数=('user_id', 'nunique')
        ).reset_index()
        reg_agg['客单价'] = (reg_agg['销售额'] / reg_agg['订单数']).round(2)
        return reg_agg.sort_values('销售额', ascending=False)

    def get_region_growth(self):
        if self.df.empty or self.prev_df.empty:
            return pd.DataFrame()
        cur_reg = self.get_region_agg()
        prev_reg = self.prev_df.groupby('region').agg(
            销售额=('amount', 'sum'),
            订单数=('order_id', 'count')
        ).reset_index()
        merged = cur_reg.merge(prev_reg, on='region', how='left', suffixes=('', '_prev'))
        merged['上期销售额'] = merged['销售额_prev'].fillna(0)
        merged['增速(%)'] = ((merged['销售额'] - merged['上期销售额']) / merged['上期销售额'].replace(0, 1) * 100).round(2)
        return merged[['region', '销售额', '上期销售额', '增速(%)', '订单数', '用户数', '客单价']]
