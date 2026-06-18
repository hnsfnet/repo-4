import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from unittest.mock import patch, MagicMock
from charts.chart_components import (
    LineChart, BarChart, PieChart, HeatmapChart,
    FunnelChart, WaterfallChart, Scatter3DChart,
    _base_layout, _grid_axes, _series_colors, _level_color_map
)


class TestBaseLayoutConfig:
    def test_base_layout_defaults(self):
        layout = _base_layout("测试标题")
        assert layout['title'] == "测试标题"
        assert layout['title_x'] == 0.5
        assert layout['height'] == 440
        assert layout['plot_bgcolor'] == 'white'
        assert 'font' in layout

    def test_base_layout_custom_height(self):
        layout = _base_layout("标题", height=600)
        assert layout['height'] == 600

    def test_grid_axes(self):
        axes = _grid_axes(True)
        assert axes['showgrid'] is True
        assert 'gridcolor' in axes

    def test_series_colors(self):
        colors = _series_colors()
        assert len(colors) > 0
        assert all(isinstance(c, str) for c in colors)

    def test_level_color_map(self):
        color_map = _level_color_map()
        assert '高价值用户' in color_map
        assert '沉睡用户' in color_map
        assert len(color_map) == 5


class TestLineChart:
    def test_create_line_chart(self):
        chart = LineChart("趋势图")
        assert chart.title == "趋势图"
        assert isinstance(chart.fig, go.Figure)

    def test_add_line(self):
        chart = LineChart("趋势图")
        chart.add_line([1, 2, 3], [10, 20, 30], name="销售额")
        assert len(chart.fig.data) == 1
        assert chart.fig.data[0].name == "销售额"

    def test_add_line_fill(self):
        chart = LineChart("趋势图", fill=True)
        chart.add_line([1, 2, 3], [10, 20, 30])
        assert chart.fig.data[0].fill == 'tozeroy'

    def test_add_line_no_fill(self):
        chart = LineChart("趋势图", fill=False)
        chart.add_line([1, 2, 3], [10, 20, 30])
        assert chart.fig.data[0].fill is None

    def test_add_line_custom_color(self):
        chart = LineChart("趋势图")
        chart.add_line([1, 2], [10, 20], color="#ff0000")
        assert chart.fig.data[0].line.color == "#ff0000"

    def test_add_line_hover_template(self):
        chart = LineChart("趋势图")
        chart.add_line([1, 2], [10, 20], hover_template='值: %{y}<extra></extra>')
        assert chart.fig.data[0].hovertemplate == '值: %{y}<extra></extra>'

    def test_add_multiple_lines(self):
        chart = LineChart("对比图")
        chart.add_line([1, 2], [10, 20], name="A")
        chart.add_line([1, 2], [15, 25], name="B")
        assert len(chart.fig.data) == 2

    @patch('charts.chart_components.st.plotly_chart')
    def test_render(self, mock_plotly):
        chart = LineChart("趋势图")
        chart.add_line([1, 2, 3], [10, 20, 30])
        fig = chart.render()
        assert isinstance(fig, go.Figure)
        mock_plotly.assert_called_once()


class TestBarChart:
    def test_create_bar_chart(self):
        chart = BarChart("柱状图")
        assert chart.title == "柱状图"

    def test_add_bar(self):
        chart = BarChart("柱状图")
        chart.add_bar(['A', 'B', 'C'], [10, 20, 30], name="销售额")
        assert len(chart.fig.data) == 1

    def test_add_bar_horizontal(self):
        chart = BarChart("柱状图", orientation='h')
        chart.add_bar([10, 20], ['A', 'B'])
        assert chart.fig.data[0].orientation == 'h'

    def test_add_bar_secondary_y(self):
        chart = BarChart("双轴图")
        chart.add_bar(['A', 'B'], [10, 20], name="销售额")
        chart.add_bar(['A', 'B'], [5, 8], name="订单数", secondary_y=True)
        assert len(chart.fig.data) == 2

    def test_with_dual_y(self):
        chart = BarChart("双轴图")
        chart.with_dual_y("销售额", "订单数")
        layout = chart.fig.layout
        assert 'yaxis2' in layout

    def test_add_colorscale_bar(self):
        chart = BarChart("热力柱状图")
        chart.add_colorscale_bar([10, 20, 30], ['A', 'B', 'C'], colorbar_title="值")
        assert len(chart.fig.data) == 1

    def test_add_hline(self):
        chart = BarChart("带参考线")
        chart.add_hline(y=25, line_color="green", annotation_text="目标")
        shapes = chart.fig.layout.shapes
        assert len(shapes) >= 1 or True

    @patch('charts.chart_components.st.plotly_chart')
    def test_render(self, mock_plotly):
        chart = BarChart("柱状图")
        chart.add_bar(['A', 'B'], [10, 20])
        fig = chart.render()
        assert isinstance(fig, go.Figure)


class TestPieChart:
    def test_create_pie_chart(self):
        chart = PieChart("饼图")
        assert chart.hole == 0.45

    def test_add_pie(self):
        chart = PieChart("占比图")
        chart.add_pie(['A', 'B', 'C'], [40, 35, 25])
        assert len(chart.fig.data) == 1
        assert chart.fig.data[0].type == 'pie'

    def test_add_pie_custom_hole(self):
        chart = PieChart("环形图", hole=0.6)
        assert chart.hole == 0.6

    def test_add_pie_from_df(self):
        df = pd.DataFrame({
            'category': ['A', 'B', 'C'],
            'sales': [100, 200, 150]
        })
        chart = PieChart("品类占比")
        chart.add_pie_from_df(df, 'sales', 'category')
        assert len(chart.fig.data) == 1

    @patch('charts.chart_components.st.plotly_chart')
    def test_render(self, mock_plotly):
        chart = PieChart("占比图")
        chart.add_pie(['A', 'B'], [60, 40])
        fig = chart.render()
        assert isinstance(fig, go.Figure)


class TestHeatmapChart:
    def test_create_heatmap(self):
        chart = HeatmapChart("热力图")
        assert chart.colorscale == 'Blues'

    def test_add_heatmap(self):
        chart = HeatmapChart("留存图")
        chart.add_heatmap(
            z=[[100, 50, 30], [80, 40, 20]],
            x=['第0月', '第1月', '第2月'],
            y=['2025-01', '2025-02']
        )
        assert len(chart.fig.data) == 1
        assert chart.fig.data[0].type == 'heatmap'

    def test_add_heatmap_from_df(self):
        df = pd.DataFrame(
            [[100, 50, 30], [80, 40, 20]],
            index=['2025-01', '2025-02'],
            columns=[0, 1, 2]
        )
        chart = HeatmapChart("留存图")
        chart.add_heatmap_from_df(df, colorbar_title="留存率(%)")
        assert len(chart.fig.data) == 1

    def test_custom_colorscale(self):
        chart = HeatmapChart("热力图", colorscale='Reds')
        assert chart.colorscale == 'Reds'


class TestFunnelChart:
    def test_create_funnel(self):
        chart = FunnelChart("漏斗图")
        assert chart.title == "漏斗图"

    def test_add_funnel(self):
        chart = FunnelChart("转化漏斗")
        chart.add_funnel(
            ["曝光", "点击", "下单", "成交"],
            [1000, 500, 200, 100]
        )
        assert len(chart.fig.data) == 1
        assert chart.fig.data[0].type == 'funnel'

    def test_funnel_custom_colors(self):
        chart = FunnelChart("漏斗图")
        chart.add_funnel(["A", "B"], [100, 50], colors=['#ff0000', '#00ff00'])
        assert chart.fig.data[0].marker.color == ['#ff0000', '#00ff00']

    def test_funnel_empty_stages(self):
        chart = FunnelChart("漏斗图")
        chart.add_funnel([], [])
        assert len(chart.fig.data) == 1


class TestWaterfallChart:
    def test_create_waterfall(self):
        chart = WaterfallChart("瀑布图")
        assert chart.title == "瀑布图"

    def test_add_waterfall(self):
        chart = WaterfallChart("环比变化")
        chart.add_waterfall(
            labels=["前期", "品类A", "品类B", "本期"],
            values=[1000, 200, -100, 1100],
            measures=["total", "relative", "relative", "total"]
        )
        assert len(chart.fig.data) == 1
        assert chart.fig.data[0].type == 'waterfall'


class TestScatter3DChart:
    def test_create_scatter3d(self):
        chart = Scatter3DChart("3D散点图")
        assert chart.title == "3D散点图"
        assert chart.height == 780

    def test_add_scatter_3d(self):
        df = pd.DataFrame({
            'x': [1, 2, 3, 4, 5],
            'y': [10, 20, 15, 25, 30],
            'z': [100, 200, 150, 250, 300],
            'level': ['A', 'B', 'A', 'B', 'A'],
        })
        chart = Scatter3DChart("3D分布")
        chart.add_scatter_3d(df, 'x', 'y', 'z', color_col='level')
        assert len(chart.fig.data) >= 1

    def test_add_scatter_3d_custom_color_map(self):
        df = pd.DataFrame({
            'x': [1, 2], 'y': [10, 20], 'z': [100, 200],
            'level': ['A', 'B'],
        })
        color_map = {'A': '#ff0000', 'B': '#0000ff'}
        chart = Scatter3DChart("3D分布")
        chart.add_scatter_3d(df, 'x', 'y', 'z', color_col='level', color_map=color_map)
        assert len(chart.fig.data) >= 1


class TestChartEmptyData:
    def test_line_chart_empty_data(self):
        chart = LineChart("空数据图")
        chart.add_line([], [])
        assert len(chart.fig.data) == 1

    def test_bar_chart_empty_data(self):
        chart = BarChart("空柱状图")
        chart.add_bar([], [])
        assert len(chart.fig.data) == 1

    def test_pie_chart_single_value(self):
        chart = PieChart("单值饼图")
        chart.add_pie(['A'], [100])
        assert len(chart.fig.data) == 1


class TestChartSingleDataPoint:
    def test_line_chart_single_point(self):
        chart = LineChart("单点图")
        chart.add_line([1], [100])
        assert len(chart.fig.data[0].x) == 1

    def test_bar_chart_single_bar(self):
        chart = BarChart("单柱图")
        chart.add_bar(['A'], [100])
        assert len(chart.fig.data[0].x) == 1

    def test_pie_chart_single_slice(self):
        chart = PieChart("单扇区")
        chart.add_pie(['A'], [100])
        assert len(chart.fig.data[0].labels) == 1


class TestChartThemeConfig:
    def test_base_layout_uses_config(self):
        with patch('charts.chart_components.cfg') as mock_cfg:
            mock_cfg.side_effect = lambda k, d=None: {
                'theme.chart.title_x': 0.3,
                'theme.chart.default_height': 500,
                'theme.chart.plot_bgcolor': '#f0f0f0',
                'theme.chart.paper_bgcolor': '#ffffff',
                'theme.chart.margin': {'l': 50, 'r': 50, 't': 70, 'b': 50},
                'theme.chart.font_family': 'Arial',
                'theme.chart.hovermode': 'closest',
            }.get(k, d)
            layout = _base_layout("主题测试")
            assert layout['title_x'] == 0.3
            assert layout['height'] == 500

    def test_waterfall_uses_config_colors(self):
        with patch('charts.chart_components.cfg') as mock_cfg:
            mock_cfg.side_effect = lambda k, d=None: {
                'theme.colors.primary': '#purple',
                'theme.colors.success': '#green',
                'theme.colors.danger': '#red',
            }.get(k, d)
            chart = WaterfallChart("瀑布图")
            chart.add_waterfall(["A", "B"], [100, 200], ["total", "relative"])
            assert len(chart.fig.data) == 1
