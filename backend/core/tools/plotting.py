import numpy as np
import pandas as pd
import plotly.graph_objects as go
from typing import Union, List, Optional, Dict, Any, Callable
import json
import re
from datetime import datetime
import uuid
from io import StringIO

from agents import function_tool

from backend.shared.logger import get_logger
from backend.shared.constants import CHARTS_DIR, CHART_DATA_FILE

logger = get_logger("PLOTTING_TOOLS")

# ============================================================================
# Chart Management Functions
# ============================================================================

def get_chart_datas():
    """Get chart data from JSON file storage"""
    try:
        if not CHART_DATA_FILE.exists():
            return []

        with open(CHART_DATA_FILE, "r", encoding="utf-8") as f:
            chart_data = json.load(f)

        return chart_data
    except Exception as e:
        logger.error(f"Error reading chart data: {e}")
        return []


def set_chart_data(data):
    """Set chart data to JSON file storage - overwrites file each time"""
    try:
        # Ensure CHARTS_DIR exists
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)

        # Overwrite file with new chart data (don't append)
        with open(CHART_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([data], f, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Error saving chart data: {e}")


def clear_chart_datas():
    """Clear chart data from JSON file storage"""
    try:
        if CHART_DATA_FILE.exists():
            # Clear the file by writing an empty list
            with open(CHART_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        else:
            logger.info("Chart data file does not exist, nothing to clear")
    except Exception as e:
        logger.error(f"Error clearing chart data: {e}")


# ============================================================================
# Data Extraction and Parsing Functions
# ============================================================================

@function_tool()
def extract_data_from_text(
    text: str,
    data_format: str = "auto"
):
    """
    Extract structured data from text in various formats.
    
    Parameters:
    -----------
    text : str
        Input text containing data (table, CSV, JSON, list, etc.)
    data_format : str
        Format hint: "auto", "table", "csv", "json", "list", "key-value"
        Default is "auto" which attempts to detect the format
    
    Returns:
    --------
    dict: Extracted structured data with 'success' key and 'data' key, or error message
    
    Examples:
    ---------
    # Markdown table
    text = '''
    | Product | Sales | Revenue |
    |---------|-------|---------|
    | A       | 100   | 5000    |
    | B       | 150   | 7500    |
    '''
    
    # CSV-like text
    text = '''
    Product,Sales,Revenue
    A,100,5000
    B,150,7500
    '''
    
    # JSON
    text = '''
    {
        "Product": ["A", "B"],
        "Sales": [100, 150],
        "Revenue": [5000, 7500]
    }
    '''
    """
    try:
        text = text.strip()
        
        # Auto-detect format
        if data_format == "auto":
            if text.startswith("{") or text.startswith("["):
                data_format = "json"
            elif "|" in text and "---" in text:
                data_format = "table"
            elif "," in text or "\t" in text:
                data_format = "csv"
            elif ":" in text and "\n" in text:
                data_format = "key-value"
            else:
                data_format = "list"
        
        # Parse based on format
        result = None
        if data_format == "json":
            result = _parse_json(text)
        elif data_format == "table":
            result = _parse_markdown_table(text)
        elif data_format == "csv":
            result = _parse_csv(text)
        elif data_format == "key-value":
            result = _parse_key_value(text)
        elif data_format == "list":
            result = _parse_list(text)
        else:
            logger.warning(f"Unknown data format: {data_format}")
            return json.dumps({"success": False, "error": f"Unknown data format: {data_format}"})
        
        if result is None:
            return json.dumps({"success": False, "error": "Failed to parse data"})
        
        return json.dumps({"success": True, "data": result})
            
    except Exception as e:
        logger.error(f"Error extracting data from text: {e}")
        return json.dumps({"success": False, "error": str(e)})


def _parse_json(text: str) -> Optional[Union[List, Dict]]:
    """Parse JSON formatted text"""
    try:
        data = json.loads(text)
        return data
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return None


def _parse_markdown_table(text: str) -> Optional[Dict]:
    """Parse markdown table into dictionary format"""
    try:
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        
        # Find header row (contains |)
        header_idx = None
        for i, line in enumerate(lines):
            if "|" in line and not line.replace("-", "").replace("|", "").replace(" ", ""):
                continue  # Skip separator row
            if "|" in line:
                header_idx = i
                break
        
        if header_idx is None:
            return None
        
        # Extract headers
        header_line = lines[header_idx]
        headers = [h.strip() for h in header_line.split("|") if h.strip()]
        
        # Extract data rows (skip separator)
        data_rows = []
        for i, line in enumerate(lines[header_idx + 1:], start=header_idx + 1):
            if "|" in line and not line.replace("-", "").replace("|", "").replace(" ", ""):
                continue  # Skip separator
            if "|" in line:
                row = [cell.strip() for cell in line.split("|") if cell.strip()]
                if len(row) == len(headers):
                    data_rows.append(row)
        
        # Convert to dictionary format
        result = {header: [] for header in headers}
        for row in data_rows:
            for header, value in zip(headers, row):
                # Try to convert to number
                try:
                    if "." in value:
                        result[header].append(float(value))
                    else:
                        result[header].append(int(value))
                except (ValueError, AttributeError):
                    result[header].append(value)
        
        return result
        
    except Exception as e:
        logger.error(f"Markdown table parsing error: {e}")
        return None


def _parse_csv(text: str) -> Optional[Dict]:
    """Parse CSV/TSV formatted text"""
    try:
        # Detect delimiter
        delimiter = "," if "," in text else "\t"
        
        # Use pandas for robust CSV parsing
        df = pd.read_csv(StringIO(text), delimiter=delimiter)
        
        # Convert to dictionary
        result = {}
        for column in df.columns:
            result[column] = df[column].tolist()
        
        return result
        
    except Exception as e:
        logger.error(f"CSV parsing error: {e}")
        return None


def _parse_key_value(text: str) -> Optional[Dict]:
    """Parse key-value pairs from text"""
    try:
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        result = {"labels": [], "values": []}
        
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                
                result["labels"].append(key)
                
                # Try to convert to number
                try:
                    if "." in value:
                        result["values"].append(float(value))
                    else:
                        result["values"].append(int(value))
                except ValueError:
                    result["values"].append(value)
        
        return result if result["labels"] else None
        
    except Exception as e:
        logger.error(f"Key-value parsing error: {e}")
        return None


def _parse_list(text: str) -> Optional[List]:
    """Parse list of numbers from text"""
    try:
        # Extract all numbers from text
        numbers = re.findall(r'-?\d+\.?\d*', text)
        
        if not numbers:
            return None
        
        # Convert to appropriate type
        result = []
        for num in numbers:
            try:
                if "." in num:
                    result.append(float(num))
                else:
                    result.append(int(num))
            except ValueError:
                continue
        
        return result if result else None
        
    except Exception as e:
        logger.error(f"List parsing error: {e}")
        return None


@function_tool()
def convert_to_plottable_format(
    data: str,
    format_type: str = "auto"
):
    """
    Convert various data formats into plottable format (list, numpy array, or DataFrame).
    
    Parameters:
    -----------
    data : str or dict
        Input data in various formats. If dict with 'success' key, it's from extract_data_from_text
    format_type : str
        Target format: "auto", "list", "array", "dataframe"
        Default is "auto" which chooses the most appropriate format
    
    Returns:
    --------
    dict: Result with 'success' key and either 'data' or 'error' key
    """
    try:
        # If data is JSON string, parse it
        if isinstance(data, str):
            try:
                data = json.loads(data)
                # If it's a result from extract_data_from_text, unwrap it
                if isinstance(data, dict) and "success" in data:
                    if not data.get("success"):
                        return json.dumps(data)
                    data = data.get("data", data)
                    # Check if data is still a JSON string (double-encoded)
                    if isinstance(data, str):
                        try:
                            data = json.loads(data)
                        except (json.JSONDecodeError, ValueError):
                            pass
            except (json.JSONDecodeError, ValueError):
                # Not JSON, that's okay - will be handled later
                pass
        
        # Determine target format
        if format_type == "auto":
            if isinstance(data, dict):
                format_type = "dataframe"
            elif isinstance(data, list):
                format_type = "array"
            else:
                format_type = "list"
        
        # Convert to target format
        result = None
        if format_type == "dataframe":
            if isinstance(data, dict):
                try:
                    result = pd.DataFrame(data)
                except ValueError as e:
                    # If scalar values, try wrapping in a list
                    if "scalar" in str(e).lower():
                        result = pd.DataFrame([data])
                    else:
                        raise
            elif isinstance(data, list):
                result = pd.DataFrame(data)
            elif isinstance(data, pd.DataFrame):
                result = data
            else:
                result = pd.DataFrame([data])
                
        elif format_type == "array":
            if isinstance(data, dict):
                # Convert dict to 2D array
                values = list(data.values())
                result = np.array(values).T
            elif isinstance(data, list):
                result = np.array(data)
            elif isinstance(data, np.ndarray):
                result = data
            elif isinstance(data, pd.DataFrame):
                result = data.values
            else:
                result = np.array([data])
                
        elif format_type == "list":
            if isinstance(data, dict):
                result = list(data.values())
            elif isinstance(data, list):
                result = data
            elif isinstance(data, np.ndarray):
                result = data.tolist()
            elif isinstance(data, pd.DataFrame):
                result = data.values.tolist()
            else:
                result = [data]
        
        if result is None:
            return json.dumps({"success": False, "error": "Failed to convert data"})
        
        # Convert result to serializable format
        if isinstance(result, pd.DataFrame):
            return json.dumps({"success": True, "data": result.to_dict('list'), "format": "dataframe"})
        elif isinstance(result, np.ndarray):
            return json.dumps({"success": True, "data": result.tolist(), "format": "array"})
        else:
            return json.dumps({"success": True, "data": result, "format": "list"})
        
    except Exception as e:
        logger.error(f"Error converting to plottable format: {e}")
        return json.dumps({"success": False, "error": str(e)})


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
    # Check if data is valid
    if not isinstance(data, np.ndarray):
        return False, "Data must be a numpy array"
    
    if data.size == 0:
        return False, "Data is empty"
    
    # Handle scalar or 0-d arrays
    if data.ndim == 0:
        data = data.reshape(1, 1)
    elif data.ndim == 1:
        data = data.reshape(-1, 1)
    
    # Ensure data has 2 dimensions after reshaping
    if data.ndim != 2:
        return False, f"Data must be 2-dimensional after reshaping, got {data.ndim} dimensions"
    
    # Now safely unpack shape
    try:
        rows, cols = data.shape
    except (ValueError, TypeError) as e:
        return False, f"Cannot unpack data shape: {str(e)}, shape: {data.shape}"
    
    rules = VALIDATION_RULES.get(plot_type)
    if not rules:
        return True, ""
    
    # Run standard checks
    for check_func, error_msg in rules.get('checks', []):
        if check_func(rows, cols):
            return False, error_msg
    
    # Special checks
    if rules.get('negative_check'):
        try:
            # Try to check for negative values, but handle non-numeric data
            if np.any(data < 0):
                return False, f"{plot_type.capitalize()} chart cannot handle negative values"
        except (TypeError, ValueError):
            # Data contains non-numeric values, try checking only numeric columns
            try:
                # For pie charts with labels and values, check only the values column
                if plot_type == 'pie' and cols == 2:
                    # Assume second column is values
                    if np.any(data[:, 1].astype(float) < 0):
                        return False, f"{plot_type.capitalize()} chart cannot handle negative values"
                else:
                    # Try to convert to numeric and check
                    numeric_data = pd.to_numeric(data.flatten(), errors='coerce')
                    if np.any(numeric_data < 0):
                        return False, f"{plot_type.capitalize()} chart cannot handle negative values"
            except Exception:
                # If all checks fail, skip negative check for this data
                pass
    
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
def get_suitable_plot_types(data: str):
    """Get list of suitable plot types for the given data.
    
    Parameters:
    -----------
    data : str
        JSON string output from convert_to_plottable_format or raw data string
    """
    try:
        # Parse JSON string input if needed
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, ValueError):
                # If not JSON, treat as raw data
                pass
        
        # Handle dict input from convert_to_plottable_format
        if isinstance(data, dict):
            if "success" in data:
                if not data.get("success"):
                    return json.dumps(data)
                data = data["data"]
            # Check if data value is still a JSON string (double-encoded)
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except (json.JSONDecodeError, ValueError):
                    pass
        
        # Convert to numpy array
        if isinstance(data, dict):
            # If it's still a dict (column-based data), convert properly
            # For data like {"labels": [...], "values": [...]}, we need to transpose
            try:
                df = pd.DataFrame(data)
                arr = df.values
            except Exception:
                # If DataFrame conversion fails, try list of values
                data = list(data.values())
                arr = np.asarray(data).T if data else np.array([])
        else:
            arr = np.asarray(data)
        
        # Check if array is empty
        if arr.size == 0:
            return json.dumps({"success": False, "error": "Data is empty, cannot determine suitable plot types"})
        
        arr = arr.reshape(-1, 1) if arr.ndim == 1 else arr
        
        # Check each plot type
        suitable = []
        dummy_config = {}
        
        for plot_type in VALIDATION_RULES.keys():
            try:
                is_valid, _ = validate_data_for_plot(arr, plot_type, dummy_config)
                if is_valid:
                    suitable.append(plot_type)
            except Exception:
                # Skip this plot type if validation fails
                continue
        
        return json.dumps({"success": True, "plot_types": suitable})
    
    except Exception as e:
        logger.error(f"Error getting suitable plot types: {e}")
        return json.dumps({"success": False, "error": str(e)})


def _prepare_data(data: Union[List, np.ndarray, pd.DataFrame, Dict], config: Dict) -> np.ndarray:
    """Convert input data to numpy array."""
    if isinstance(data, pd.DataFrame):
        config['column_names'] = config.get('column_names') or data.columns.tolist()
        return data.values
    elif isinstance(data, dict):
        # If it's a dict with column data, convert to DataFrame first
        try:
            df = pd.DataFrame(data)
            config['column_names'] = config.get('column_names') or df.columns.tolist()
            return df.values
        except Exception:
            # If can't convert to DataFrame, try to get values
            values = list(data.values())
            return np.asarray(values).T if values else np.array([])
    return np.asarray(data)


def _setup_defaults(data: np.ndarray, config: Dict) -> None:
    """Setup default configuration values."""
    if data.size == 0:
        return  # Can't setup defaults for empty data
    
    # Handle scalar or 0-d arrays
    if data.ndim == 0:
        data = data.reshape(1, 1)
    elif data.ndim == 1:
        data = data.reshape(-1, 1)
    
    if data.ndim != 2:
        return  # Can't setup defaults for non-2D data
    
    try:
        rows, cols = data.shape
    except (ValueError, TypeError):
        return  # Can't unpack shape
    
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
    data: str,
    plot_type: str = 'line',
    config: str = None
):
    """
    Create an HTML plot from array data and save it to charts directory.
    
    Parameters:
    -----------
    data : str
        JSON string output from convert_to_plottable_format or raw data string
    plot_type : str
        Type of plot (line, bar, scatter, pie, histogram, box, heatmap, area,
        heatmap_1d, violin, bubble, waterfall, radar, funnel, candlestick, treemap, scatter_3d)
    config : str, optional
        JSON string with configuration: title, x_label, y_label, column_names, x_values, colors,
        width (800), height (600), stacked (False), orientation ('v')
    
    Returns:
    --------
    str: JSON string with success message and chart details, or error dict
    """
    # Parse config if it's a JSON string
    if config and isinstance(config, str):
        try:
            config = json.loads(config)
        except (json.JSONDecodeError, ValueError):
            config = {}
    
    # Setup configuration
    config = {
        'title': 'Data Visualization', 'x_label': 'X', 'y_label': 'Y',
        'column_names': None, 'x_values': None, 'colors': None,
        'width': 800, 'height': 600, 'stacked': False, 'orientation': 'v',
        **(config or {})
    }
    
    try:
        # Parse data if it's a JSON string
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, ValueError):
                # If not JSON, can't process - return error
                return json.dumps({"success": False, "error": "Data must be valid JSON string from convert_to_plottable_format"})
        
        # Handle dict input from convert_to_plottable_format
        if isinstance(data, dict):
            if "success" in data:
                if not data.get("success"):
                    return json.dumps(data)
                data = data["data"]
            # Check if data value is still a JSON string (double-encoded)
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except (json.JSONDecodeError, ValueError):
                    pass
        
        # Prepare data
        data = _prepare_data(data, config)
        
        # Check if data is empty
        if data.size == 0:
            return json.dumps({"success": False, "error": "Data is empty after preparation"})
        
        # Handle scalar or 0-d arrays
        if data.ndim == 0:
            data = data.reshape(1, 1)
        elif data.ndim == 1:
            data = data.reshape(-1, 1)
        
        # Validate
        is_valid, error_msg = validate_data_for_plot(data, plot_type, config)
        if not is_valid:
            logger.warning(f"Data validation failed: {error_msg}")
            return json.dumps({"success": False, "error": error_msg})
    
        # Setup defaults
        _setup_defaults(data, config)
        
        # Create plot
        plot_func = PLOT_CREATORS.get(plot_type)
        if not plot_func:
            logger.warning(f"Plot type '{plot_type}' is not supported")
            return json.dumps({"success": False, "error": f"Plot type '{plot_type}' is not supported"})
        
        fig = plot_func(data, config)
        fig.update_layout(
            title=config['title'],
            width=config['width'],
            height=config['height'],
            template='plotly_white'
        )
        
        # Generate chart HTML
        chart_html = fig.to_html(include_plotlyjs='cdn')
        
        # Generate unique chart ID and save
        chart_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save chart file
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        chart_file = CHARTS_DIR / f"{chart_id}.html"
        
        # Get data info safely
        try:
            if data.ndim == 2:
                rows, cols = data.shape
            elif data.ndim == 1:
                rows, cols = len(data), 1
            else:
                rows, cols = 1, 1
        except (ValueError, TypeError):
            rows, cols = 1, 1
        
        # Create chart metadata
        chart_data = {
            "filename": f"{chart_id}.html",
            "data": chart_html,
            "reference": chart_id,
            "type": "text/html",
            "plot_type": plot_type,
            "title": config['title'],
            "data_shape": {"rows": int(rows), "cols": int(cols)},
            "column_names": config['column_names'],
            "created_at": datetime.now().isoformat(),
            "file_path": str(chart_file),
            "config": {
                "width": config['width'],
                "height": config['height'],
                "x_label": config['x_label'],
                "y_label": config['y_label'],
            }
        }
        
        # Save chart data and file
        set_chart_data(chart_data)
        
        try:
            with open(chart_file, "w", encoding="utf-8") as f:
                f.write(chart_html)
            logger.info(f"Chart saved successfully: {chart_file}")
        except Exception as e:
            logger.error(f"Error saving chart file: {e}")
        
        return json.dumps({
            "success": True,
            "message": f"Chart created successfully: {config['title']}",
            "plot_type": plot_type,
            "data_points": f"{rows} rows × {cols} columns",
            "chart_id": chart_id
        })
    
    except Exception as e:
        logger.error(f"Error creating plot: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


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
