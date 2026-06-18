import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from utils.config import get as cfg


def _base_layout(title, height=None, **kwargs):
    return dict(
        title=title,
        title_x=cfg('theme.chart.title_x', 0.5),
        height=height or cfg('theme.chart.default_height', 440),
        plot_bgcolor=cfg('theme.chart.plot_bgcolor', 'white'),
        paper_bgcolor=cfg('theme.chart.paper_bgcolor', 'white'),
        margin=cfg('theme.chart.margin', {'l': 40, 'r': 40, 't': 60, 'b': 40}),
        font=dict(family=cfg('theme.chart.font_family', 'Microsoft YaHei, PingFang SC, sans-serif')),
        hovermode=cfg('theme.chart.hovermode', 'x unified'),
        **kwargs
    )


def _grid_axes(show_grid=True):
    grid_color = cfg('theme.chart.grid_color', '#f1f5f9')
    return dict(showgrid=show_grid, gridcolor=grid_color)


def _series_colors():
    return cfg('theme.colors.series', ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6'])


def _level_color_map():
    return cfg('theme.colors.level_colors', {
        '高价值用户': '#22c55e', '潜力用户': '#3b82f6',
        '流失预警': '#f59e0b', '沉睡用户': '#ef4444', '普通用户': '#94a3b8'
    })


class LineChart:
    def __init__(self, title="", height=None, fill=True):
        self.title = title
        self.height = height
        self.fill = fill
        self.fig = go.Figure()

    def add_line(self, x, y, name="", color=None, hover_template=None):
        primary = color or cfg('theme.colors.primary', '#6366f1')
        fillcolor = primary.replace('#', '')
        if len(fillcolor) == 6:
            r, g, b = int(fillcolor[:2], 16), int(fillcolor[2:4], 16), int(fillcolor[4:], 16)
            fill_rgba = f'rgba({r}, {g}, {b}, 0.1)'
        else:
            fill_rgba = 'rgba(99, 102, 241, 0.1)'

        self.fig.add_trace(go.Scatter(
            x=x, y=y,
            mode='lines+markers',
            name=name or self.title,
            line=dict(color=primary, width=3),
            marker=dict(size=7, color=primary),
            fill='tozeroy' if self.fill else None,
            fillcolor=fill_rgba if self.fill else None,
            hovertemplate=hover_template or f'{name}: %{{y:,.2f}}<extra></extra>'
        ))
        return self

    def render(self, use_container_width=True):
        self.fig.update_layout(**_base_layout(self.title, self.height),
                               xaxis=_grid_axes(), yaxis=_grid_axes())
        st.plotly_chart(self.fig, use_container_width=use_container_width)
        return self.fig


class BarChart:
    def __init__(self, title="", height=None, orientation='v'):
        self.title = title
        self.height = height
        self.orientation = orientation
        self.fig = go.Figure()

    def add_bar(self, x, y, name="", color=None, text=None,
                hover_template=None, secondary_y=False):
        colors = _series_colors()
        bar_color = color or colors[len(self.fig.data) % len(colors)]

        trace_kwargs = dict(
            x=x if self.orientation == 'v' else y,
            y=y if self.orientation == 'v' else x,
            name=name,
            marker_color=bar_color,
            hovertemplate=hover_template or f'{name}: %{{y:,.2f}}<extra></extra>',
            text=text,
            textposition='outside',
            orientation='v' if self.orientation == 'v' else 'h',
        )
        if secondary_y:
            trace_kwargs['yaxis'] = 'y2'

        self.fig.add_trace(go.Bar(**trace_kwargs))
        return self

    def add_colorscale_bar(self, x, y, colorscale='Blues', colorbar_title=""):
        self.fig.add_trace(go.Bar(
            x=x if self.orientation == 'v' else y,
            y=y if self.orientation == 'v' else x,
            orientation=self.orientation,
            marker=dict(color=y if self.orientation == 'v' else x,
                        colorscale=colorscale, showscale=True,
                        colorbar=dict(title=colorbar_title)),
            text=[f"¥{v:,.0f}" for v in (y if self.orientation == 'v' else x)],
            textposition='outside',
        ))
        return self

    def add_hline(self, y, line_dash="dash", line_color="", annotation_text="",
                  annotation_position="bottom right"):
        self.fig.add_hline(y=y, line_dash=line_dash, line_color=line_color,
                           annotation_text=annotation_text,
                           annotation_position=annotation_position)
        return self

    def with_dual_y(self, y1_title="", y2_title=""):
        self.fig.update_layout(
            yaxis=dict(title=y1_title),
            yaxis2=dict(title=y2_title, overlaying='y', side='right')
        )
        return self

    def render(self, use_container_width=True, **layout_kwargs):
        layout = _base_layout(self.title, self.height, **layout_kwargs)
        if self.orientation == 'v':
            layout['xaxis'] = _grid_axes()
            layout['yaxis'] = _grid_axes()
            if 'yaxis' not in layout_kwargs:
                layout.setdefault('yaxis', _grid_axes())
        else:
            layout['xaxis'] = _grid_axes()
            layout['yaxis'] = dict(showgrid=False)
        self.fig.update_layout(**layout)
        st.plotly_chart(self.fig, use_container_width=use_container_width)
        return self.fig


class PieChart:
    def __init__(self, title="", height=None, hole=None):
        self.title = title
        self.height = height
        self.hole = hole or cfg('theme.chart.pie_hole', 0.45)
        self.fig = go.Figure()

    def add_pie(self, labels, values, color_map=None, hover_template=None):
        colors = _series_colors()
        if color_map:
            color_discrete_map = color_map
        else:
            color_discrete_map = None

        self.fig.add_trace(go.Pie(
            labels=labels, values=values,
            hole=self.hole,
            marker=dict(colors=color_discrete_map or colors[:len(labels)]),
            textposition='inside',
            textinfo='label+percent',
            hovertemplate=hover_template or '类别: %{label}<br>数值: %{value:,.2f}<br>占比: %{percent}<extra></extra>'
        ))
        return self

    def add_pie_from_df(self, df, values_col, names_col, color_map=None):
        sorted_df = df.sort_values(values_col, ascending=False)
        return self.add_pie(
            labels=sorted_df[names_col],
            values=sorted_df[values_col],
            color_map=color_map
        )

    def render(self, use_container_width=True):
        self.fig.update_layout(**_base_layout(self.title, self.height),
                               legend=dict(orientation="h", yanchor="bottom",
                                           y=-0.1, xanchor="center", x=0.5),
                               showlegend=True)
        st.plotly_chart(self.fig, use_container_width=use_container_width)
        return self.fig


class HeatmapChart:
    def __init__(self, title="", height=None, colorscale='Blues'):
        self.title = title
        self.height = height
        self.colorscale = colorscale
        self.fig = go.Figure()

    def add_heatmap(self, z, x=None, y=None, text=None, colorbar_title="",
                    text_template='%{text:.1f}%', hover_template=None):
        self.fig.add_trace(go.Heatmap(
            z=z, x=x, y=y,
            colorscale=self.colorscale,
            text=text if text is not None else z,
            texttemplate=text_template,
            hovertemplate=hover_template or '行: %{y}<br>列: %{x}<br>值: %{z:.1f}<extra></extra>',
            colorbar=dict(title=colorbar_title)
        ))
        return self

    def add_heatmap_from_df(self, df, colorbar_title=""):
        x_labels = [f"第{c}月" for c in df.columns]
        y_labels = df.index.tolist()
        return self.add_heatmap(
            z=df.values, x=x_labels, y=y_labels,
            text=df.values, colorbar_title=colorbar_title
        )

    def render(self, use_container_width=True, x_title="", y_title=""):
        layout = _base_layout(self.title, self.height)
        layout['xaxis_title'] = x_title
        layout['yaxis_title'] = y_title
        self.fig.update_layout(**layout)
        st.plotly_chart(self.fig, use_container_width=use_container_width)
        return self.fig


class FunnelChart:
    def __init__(self, title="", height=None):
        self.title = title
        self.height = height
        self.fig = go.Figure()

    def add_funnel(self, stages, values, colors=None):
        if colors is None:
            series = _series_colors()
            colors = [series[i % len(series)] for i in range(len(stages))]

        self.fig.add_trace(go.Funnel(
            name=self.title or '转化漏斗',
            y=stages, x=values,
            textposition="inside",
            textinfo="value+percent previous",
            marker=dict(color=colors),
            connector={"fillcolor": "rgba(148, 163, 184, 0.25)"},
            hovertemplate='阶段: %{y}<br>人数: %{x:,}<extra></extra>'
        ))
        return self

    def render(self, use_container_width=True):
        self.fig.update_layout(**_base_layout(self.title, self.height))
        st.plotly_chart(self.fig, use_container_width=use_container_width)
        return self.fig


class WaterfallChart:
    def __init__(self, title="", height=None):
        self.title = title
        self.height = height
        self.fig = go.Figure()

    def add_waterfall(self, labels, values, measures):
        primary = cfg('theme.colors.primary', '#6366f1')
        success = cfg('theme.colors.success', '#22c55e')
        danger = cfg('theme.colors.danger', '#ef4444')
        text_list = [f"¥{v:,.0f}" for v in values]

        self.fig.add_trace(go.Waterfall(
            name=self.title or "瀑布图",
            orientation="v",
            measure=measures,
            x=labels, y=values,
            text=text_list,
            textposition="outside",
            connector={"line": {"color": "#94a3b8", "dash": "dot"}},
            increasing={"marker": {"color": success}},
            decreasing={"marker": {"color": danger}},
            totals={"marker": {"color": primary}}
        ))
        return self

    def render(self, use_container_width=True, y_title=""):
        layout = _base_layout(self.title, self.height)
        layout['yaxis_title'] = y_title
        layout['yaxis'] = _grid_axes()
        self.fig.update_layout(**layout)
        st.plotly_chart(self.fig, use_container_width=use_container_width)
        return self.fig


class Scatter3DChart:
    def __init__(self, title="", height=780):
        self.title = title
        self.height = height
        self.fig = go.Figure()

    def add_scatter_3d(self, df, x, y, z, color_col, color_map=None,
                       hover_data=None, opacity=0.7):
        if color_map is None:
            color_map = _level_color_map()
        fig = px.scatter_3d(
            df, x=x, y=y, z=z,
            color=color_col,
            color_discrete_map=color_map,
            hover_data=hover_data,
            opacity=opacity,
            size_max=8
        )
        self.fig = fig
        return self

    def render(self, use_container_width=True, x_title="", y_title="", z_title=""):
        self.fig.update_layout(
            title=self.title,
            title_x=cfg('theme.chart.title_x', 0.5),
            height=self.height,
            scene=dict(xaxis_title=x_title, yaxis_title=y_title, zaxis_title=z_title),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
        )
        st.plotly_chart(self.fig, use_container_width=use_container_width)
        return self.fig
