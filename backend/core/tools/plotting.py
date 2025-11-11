"""
HTML Plot Generation Utilities

A comprehensive plotting library that creates interactive HTML plots from array data
with automatic validation and support for 17 different chart types.

Author: Plot Utils
License: MIT
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from typing import Union, List, Optional, Dict, Any, Callable

from agents import function_tool

from backend.shared.logger import get_logger
logger = get_logger("PLOTTING_TOOLS")

# ============================================================================
# Validation Rules Configuration
# ============================================================================

VALIDATION_RULES = {
    'pie': {
        'checks': [
            (lambda r, c: c > 2, "Pie chart requires 1 or 2 columns"),
            (lambda r, c: r > 100, "Pie chart not suitable for more than 100 categories"),
            (lambda r, c: c == 1 and r > 50, "Pie chart with single column not recommended for more than 50 items"),
        ],
        'negative_check': True
    },
    'scatter': {
        'checks': [
            (lambda r, c: c < 2 and r < 2, "Scatter plot requires at least 2 data points or 2 columns"),
            (lambda r, c: c > 50, "Scatter plot not suitable for more than 50 series"),
        ]
    },
    'line': {
        'checks': [
            (lambda r, c: c < 1, "Line plot requires at least 1 column"),
            (lambda r, c: c > 20, "Line plot not recommended for more than 20 series"),
        ]
    },
    'bar': {
        'checks': [
            (lambda r, c: c < 1, "Bar plot requires at least 1 column"),
            (lambda r, c: r > 1000, "Bar plot not suitable for more than 1000 bars"),
            (lambda r, c: c > 30, "Bar plot not recommended for more than 30 grouped bars"),
        ]
    },
    'histogram': {
        'checks': [
            (lambda r, c: c > 10, "Histogram not recommended for more than 10 distributions"),
            (lambda r, c: r < 2, "Histogram requires at least 2 data points"),
        ]
    },
    'box': {
        'checks': [
            (lambda r, c: c > 20, "Box plot not recommended for more than 20 groups"),
            (lambda r, c: r < 5, "Box plot requires at least 5 data points per group"),
        ]
    },
    'heatmap': {
        'checks': [
            (lambda r, c: c < 2 or r < 2, "Heatmap requires at least 2x2 data"),
            (lambda r, c: c > 100 or r > 100, "Heatmap not recommended for matrices larger than 100x100"),
        ]
    },
    'area': {
        'checks': [
            (lambda r, c: c < 1, "Area plot requires at least 1 column"),
            (lambda r, c: c > 15, "Area plot not recommended for more than 15 series"),
        ]
    },
    'heatmap_1d': {
        'checks': [
            (lambda r, c: c > 1 and r > 1, "1D heatmap requires single row or column"),
            (lambda r, c: max(r, c) > 500, "1D heatmap not suitable for more than 500 values"),
        ]
    },
    'violin': {
        'checks': [
            (lambda r, c: c > 15, "Violin plot not recommended for more than 15 groups"),
            (lambda r, c: r < 10, "Violin plot requires at least 10 data points per group"),
        ]
    },
    'bubble': {
        'checks': [
            (lambda r, c: c < 3, "Bubble chart requires at least 3 columns (x, y, size)"),
            (lambda r, c: c > 51, "Bubble chart not suitable for more than 50 series"),
            (lambda r, c: r < 2, "Bubble chart requires at least 2 data points"),
        ]
    },
    'waterfall': {
        'checks': [
            (lambda r, c: c != 1, "Waterfall chart requires exactly 1 column"),
            (lambda r, c: r > 50, "Waterfall chart not recommended for more than 50 steps"),
            (lambda r, c: r < 2, "Waterfall chart requires at least 2 values"),
        ]
    },
    'radar': {
        'checks': [
            (lambda r, c: c < 3, "Radar chart requires at least 3 dimensions"),
            (lambda r, c: c > 20, "Radar chart not recommended for more than 20 dimensions"),
            (lambda r, c: r > 10, "Radar chart not recommended for more than 10 series"),
        ]
    },
    'funnel': {
        'checks': [
            (lambda r, c: c != 1, "Funnel chart requires exactly 1 column"),
            (lambda r, c: r > 15, "Funnel chart not recommended for more than 15 stages"),
            (lambda r, c: r < 2, "Funnel chart requires at least 2 stages"),
        ],
        'negative_check': True
    },
    'candlestick': {
        'checks': [
            (lambda r, c: c != 4, "Candlestick chart requires exactly 4 columns (O,H,L,C)"),
            (lambda r, c: r < 2, "Candlestick chart requires at least 2 time periods"),
            (lambda r, c: r > 1000, "Candlestick chart not recommended for more than 1000 periods"),
        ],
        'ohlc_check': True
    },
    'treemap': {
        'checks': [
            (lambda r, c: c < 1 or c > 2, "Treemap requires 1 or 2 columns"),
            (lambda r, c: r > 100, "Treemap not recommended for more than 100 items"),
            (lambda r, c: r < 2, "Treemap requires at least 2 items"),
        ],
        'positive_check': True
    },
    'scatter_3d': {
        'checks': [
            (lambda r, c: c < 3, "3D scatter requires at least 3 columns (x, y, z)"),
            (lambda r, c: c > 4, "3D scatter supports max 4 columns"),
            (lambda r, c: r < 2, "3D scatter requires at least 2 data points"),
            (lambda r, c: r > 10000, "3D scatter not recommended for more than 10000 points"),
        ]
    }
}


# ============================================================================
# Core Functions
# ============================================================================

def validate_data_for_plot(data: np.ndarray, plot_type: str, config: Dict[str, Any]) -> tuple[bool, str]:
    """Validate if data is suitable for the chosen plot type."""
    if data.size == 0:
        return False, "Data is empty"
    
    data = data.reshape(-1, 1) if data.ndim == 1 else data
    rows, cols = data.shape
    
    rules = VALIDATION_RULES.get(plot_type)
    if not rules:
        return True, ""
    
    # Run standard checks
    for check_func, error_msg in rules.get('checks', []):
        if check_func(rows, cols):
            return False, error_msg
    
    # Special checks
    if rules.get('negative_check') and np.any(data < 0):
        return False, f"{plot_type.capitalize()} chart cannot handle negative values"
    
    if rules.get('positive_check'):
        value_col = 0 if cols == 1 else 1
        if np.any(data[:, value_col] <= 0):
            return False, f"{plot_type.capitalize()} requires all values to be positive"
    
    if rules.get('ohlc_check'):
        for i in range(rows):
            o, h, l, c = data[i]
            if h < max(o, c) or l > min(o, c):
                return False, f"Invalid OHLC data at row {i}"
    
    return True, ""

@function_tool()
def get_suitable_plot_types(data: Union[List, np.ndarray, pd.DataFrame]) -> List[str]:
    """Get list of suitable plot types for the given data."""
    # Convert to numpy array
    arr = np.asarray(data if not isinstance(data, pd.DataFrame) else data.values)
    arr = arr.reshape(-1, 1) if arr.ndim == 1 else arr
    
    # Check each plot type
    suitable = []
    dummy_config = {}
    
    for plot_type in VALIDATION_RULES.keys():
        is_valid, _ = validate_data_for_plot(arr, plot_type, dummy_config)
        if is_valid:
            suitable.append(plot_type)
    
    return suitable


def _prepare_data(data: Union[List, np.ndarray, pd.DataFrame], config: Dict) -> np.ndarray:
    """Convert input data to numpy array."""
    if isinstance(data, pd.DataFrame):
        config['column_names'] = config.get('column_names') or data.columns.tolist()
        return data.values
    return np.asarray(data)


def _setup_defaults(data: np.ndarray, config: Dict) -> None:
    """Setup default configuration values."""
    data = data.reshape(-1, 1) if data.ndim == 1 else data
    rows, cols = data.shape
    
    # Default column names
    if not config.get('column_names'):
        config['column_names'] = ['Value'] if cols == 1 else [f'Series {i+1}' for i in range(cols)]
    
    # Default x values with extension support
    x_vals = config.get('x_values')
    if not x_vals:
        config['x_values'] = list(range(rows))
    elif len(x_vals) < rows:
        config['x_values'] = [str(x) for x in x_vals] + [str(i) for i in range(len(x_vals), rows)]


def _add_multi_trace(fig: go.Figure, data: np.ndarray, config: Dict, trace_type: Callable, **kwargs) -> None:
    """Helper to add multiple traces to a figure."""
    for i in range(data.shape[1]):
        fig.add_trace(trace_type(
            y=data[:, i],
            name=config['column_names'][i],
            **kwargs
        ))


def _update_axes(fig: go.Figure, config: Dict, **kwargs) -> go.Figure:
    """Helper to update figure axes."""
    fig.update_xaxes(title_text=config.get('x_label', 'X'))
    fig.update_yaxes(title_text=config.get('y_label', 'Y'))
    for key, value in kwargs.items():
        getattr(fig, f'update_{key}')(**value)
    return fig

@function_tool()
def create_html_plot(
    data: Union[List, np.ndarray, pd.DataFrame],
    plot_type: str = 'line',
    config: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Create an HTML plot from array data.
    
    Parameters:
    -----------
    data : array-like
        Input data as list, numpy array, or pandas DataFrame
    plot_type : str
        Type of plot (line, bar, scatter, pie, histogram, box, heatmap, area,
        heatmap_1d, violin, bubble, waterfall, radar, funnel, candlestick, treemap, scatter_3d)
    config : dict, optional
        Configuration: title, x_label, y_label, column_names, x_values, colors,
        width (800), height (600), stacked (False), orientation ('v')
    
    Returns:
    --------
    str or None: HTML string of plot, or None if data is not eligible
    """
    # Setup configuration
    config = {
        'title': 'Data Visualization', 'x_label': 'X', 'y_label': 'Y',
        'column_names': None, 'x_values': None, 'colors': None,
        'width': 800, 'height': 600, 'stacked': False, 'orientation': 'v',
        **(config or {})
    }
    
    # Prepare data
    data = _prepare_data(data, config)
    data = data.reshape(-1, 1) if data.ndim == 1 else data
    
    # Validate
    is_valid, error_msg = validate_data_for_plot(data, plot_type, config)
    if not is_valid:
        print(f"NOT ELIGIBLE: {error_msg}")
        return None
    
    # Setup defaults
    _setup_defaults(data, config)
    
    # Create plot
    try:
        plot_func = PLOT_CREATORS.get(plot_type)
        if not plot_func:
            print(f"NOT ELIGIBLE: Plot type '{plot_type}' is not supported")
            return None
        
        fig = plot_func(data, config)
        fig.update_layout(
            title=config['title'],
            width=config['width'],
            height=config['height'],
            template='plotly_white'
        )
        
        return fig.to_html(include_plotlyjs='cdn')
    
    except Exception as e:
        print(f"NOT ELIGIBLE: Error creating plot - {str(e)}")
        return None


# ============================================================================
# Plot Creation Functions
# ============================================================================

def create_line_plot(data: np.ndarray, config: Dict) -> go.Figure:
    """Create a line plot."""
    fig = go.Figure()
    for i in range(data.shape[1]):
        fig.add_trace(go.Scatter(
            x=config['x_values'], y=data[:, i],
            mode='lines+markers', name=config['column_names'][i]
        ))
    return _update_axes(fig, config)


def create_bar_plot(data: np.ndarray, config: Dict) -> go.Figure:
    """Create a bar plot."""
    fig = go.Figure()
    is_vertical = config['orientation'] == 'v'
    
    for i in range(data.shape[1]):
        fig.add_trace(go.Bar(
            x=config['x_values'] if is_vertical else data[:, i],
            y=data[:, i] if is_vertical else config['x_values'],
            name=config['column_names'][i],
            orientation=config['orientation']
        ))
    
    fig.update_layout(barmode='stack' if config['stacked'] else 'group')
    return _update_axes(fig, config)


def create_scatter_plot(data: np.ndarray, config: Dict) -> go.Figure:
    """Create a scatter plot."""
    fig = go.Figure()
    rows, cols = data.shape
    
    if cols == 1:
        fig.add_trace(go.Scatter(
            x=config['x_values'], y=data[:, 0],
            mode='markers', name=config['column_names'][0]
        ))
    elif cols == 2:
        fig.add_trace(go.Scatter(
            x=data[:, 0], y=data[:, 1],
            mode='markers', name='Data Points'
        ))
    else:
        for i in range(1, cols):
            fig.add_trace(go.Scatter(
                x=data[:, 0], y=data[:, i],
                mode='markers', name=config['column_names'][i]
            ))
    
    return _update_axes(fig, config)


def create_pie_plot(data: np.ndarray, config: Dict) -> go.Figure:
    """Create a pie chart."""
    rows, cols = data.shape
    labels = [str(x) for x in (config['x_values'][:rows] if cols == 1 else data[:, 0])]
    values = data[:, 0] if cols == 1 else data[:, 1]
    
    return go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.3)])


def create_histogram_plot(data: np.ndarray, config: Dict) -> go.Figure:
    """Create a histogram."""
    fig = go.Figure()
    for i in range(data.shape[1]):
        fig.add_trace(go.Histogram(
            x=data[:, i], name=config['column_names'][i], opacity=0.7
        ))
    
    fig.update_layout(barmode='overlay')
    return _update_axes(fig, config, yaxes={'title_text': 'Frequency'})


def create_box_plot(data: np.ndarray, config: Dict) -> go.Figure:
    """Create a box plot."""
    fig = go.Figure()
    _add_multi_trace(fig, data, config, go.Box)
    fig.update_yaxes(title_text=config['y_label'])
    return fig


def create_heatmap_plot(data: np.ndarray, config: Dict) -> go.Figure:
    """Create a 2D heatmap."""
    fig = go.Figure(data=go.Heatmap(z=data, colorscale='Viridis'))
    return _update_axes(fig, config)


def create_area_plot(data: np.ndarray, config: Dict) -> go.Figure:
    """Create an area plot."""
    fig = go.Figure()
    stacked = config['stacked']
    
    for i in range(data.shape[1]):
        fig.add_trace(go.Scatter(
            x=config['x_values'], y=data[:, i],
            mode='lines', name=config['column_names'][i],
            fill='tonexty' if i > 0 and stacked else 'tozeroy',
            stackgroup='one' if stacked else None
        ))
    
    return _update_axes(fig, config)


def create_heatmap_1d_plot(data: np.ndarray, config: Dict) -> go.Figure:
    """Create a 1D heatmap."""
    rows, cols = data.shape
    values = data.T if cols == 1 else data
    x_vals = config['x_values'][:len(values[0])] if len(values[0]) <= len(config['x_values']) else list(range(len(values[0])))
    
    fig = go.Figure(data=go.Heatmap(
        z=values, colorscale='Viridis', showscale=True,
        y=['Value'], x=x_vals
    ))
    
    fig.update_xaxes(title_text=config['x_label'])
    fig.update_yaxes(showticklabels=False)
    return fig


def create_violin_plot(data: np.ndarray, config: Dict) -> go.Figure:
    """Create a violin plot."""
    fig = go.Figure()
    _add_multi_trace(fig, data, config, go.Violin, box_visible=True, meanline_visible=True)
    fig.update_yaxes(title_text=config['y_label'])
    return fig


def create_bubble_plot(data: np.ndarray, config: Dict) -> go.Figure:
    """Create a bubble chart."""
    fig = go.Figure()
    rows, cols = data.shape
    marker = dict(
        size=data[:, 2], sizemode='area',
        sizeref=2.*max(data[:, 2])/(40.**2), sizemin=4
    )
    
    if cols == 3:
        fig.add_trace(go.Scatter(
            x=data[:, 0], y=data[:, 1],
            mode='markers', marker=marker, name='Data Points'
        ))
    else:
        for i in range(3, cols):
            fig.add_trace(go.Scatter(
                x=data[:, 0], y=data[:, 1],
                mode='markers', marker=marker, name=config['column_names'][i]
            ))
    
    return _update_axes(fig, config)


def create_waterfall_plot(data: np.ndarray, config: Dict) -> go.Figure:
    """Create a waterfall chart."""
    rows = data.shape[0]
    measures = ['relative'] * (rows - 1) + ['total']
    
    fig = go.Figure(go.Waterfall(
        name="", orientation="v", measure=measures,
        x=config['x_values'][:rows], y=data[:, 0],
        connector={"line": {"color": "rgb(63, 63, 63)"}}
    ))
    
    return _update_axes(fig, config)


def create_radar_plot(data: np.ndarray, config: Dict) -> go.Figure:
    """Create a radar chart."""
    fig = go.Figure()
    
    for i in range(data.shape[0]):
        name = str(config['x_values'][i]) if i < len(config['x_values']) else f'Series {i+1}'
        fig.add_trace(go.Scatterpolar(
            r=data[i, :], theta=config['column_names'],
            fill='toself', name=name
        ))
    
    fig.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True)
    return fig


def create_funnel_plot(data: np.ndarray, config: Dict) -> go.Figure:
    """Create a funnel chart."""
    rows = data.shape[0]
    return go.Figure(go.Funnel(
        y=config['x_values'][:rows], x=data[:, 0],
        textposition="inside", textinfo="value+percent initial"
    ))


def create_candlestick_plot(data: np.ndarray, config: Dict) -> go.Figure:
    """Create a candlestick chart."""
    rows = data.shape[0]
    fig = go.Figure(data=[go.Candlestick(
        x=config['x_values'][:rows],
        open=data[:, 0], high=data[:, 1],
        low=data[:, 2], close=data[:, 3]
    )])
    
    return _update_axes(fig, config)


def create_treemap_plot(data: np.ndarray, config: Dict) -> go.Figure:
    """Create a treemap."""
    rows, cols = data.shape
    labels = [str(x) for x in (config['x_values'][:rows] if cols == 1 else data[:, 0])]
    values = data[:, 0] if cols == 1 else data[:, 1]
    
    return go.Figure(go.Treemap(
        labels=labels, values=values, parents=[''] * rows,
        textinfo="label+value+percent parent"
    ))


def create_scatter_3d_plot(data: np.ndarray, config: Dict) -> go.Figure:
    """Create a 3D scatter plot."""
    marker = dict(size=5, line=dict(width=0.5, color='DarkSlateGrey'))
    
    if data.shape[1] == 4:
        marker.update(color=data[:, 3], colorscale='Viridis', showscale=True)
    
    fig = go.Figure(data=[go.Scatter3d(
        x=data[:, 0], y=data[:, 1], z=data[:, 2],
        mode='markers', marker=marker
    )])
    
    fig.update_layout(scene=dict(
        xaxis_title=config['x_label'],
        yaxis_title=config['y_label'],
        zaxis_title='Z'
    ))
    
    return fig


# Plot function registry
PLOT_CREATORS = {
    'line': create_line_plot,
    'bar': create_bar_plot,
    'scatter': create_scatter_plot,
    'pie': create_pie_plot,
    'histogram': create_histogram_plot,
    'box': create_box_plot,
    'heatmap': create_heatmap_plot,
    'area': create_area_plot,
    'heatmap_1d': create_heatmap_1d_plot,
    'violin': create_violin_plot,
    'bubble': create_bubble_plot,
    'waterfall': create_waterfall_plot,
    'radar': create_radar_plot,
    'funnel': create_funnel_plot,
    'candlestick': create_candlestick_plot,
    'treemap': create_treemap_plot,
    'scatter_3d': create_scatter_3d_plot,
}
