from e2b_code_interpreter import Sandbox
from pydantic import BaseModel, Field
from langchain.tools import tool
from dotenv import load_dotenv
import uuid
from datetime import datetime
from backend.shared.constants import CHARTS_DIR, CHART_DATA_FILE
from backend.core.tools.finance import (
    calculate_sma,
    calculate_ema,
    calculate_bollinger_bands,
    calculate_rsi,
    calculate_macd,
    get_intraday_data,
    get_eod_data,
)
import json
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

load_dotenv()


def set_chart_data(data):
    """Set chart data to JSON file storage - overwrites file each time"""
    try:
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)

        # Overwrite file with new chart data (don't append)
        with open(CHART_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([data], f, ensure_ascii=False, indent=2)

    except Exception as e:
        pass


@tool(parse_docstring=True)
def create_custom_chart_from_code(code: str) -> dict:
    """Create custom charts by executing Python code in a sandboxed environment.

    Use this tool for non-financial visualizations such as statistical plots,
    scientific charts, and custom data analysis with libraries like matplotlib,
    seaborn, or plotly.

    Args:
        code: Complete Python code that generates and saves one or more charts.
            The code must include all required imports and a save call
            (for example, plt.savefig()).
    """
    sandbox = None
    try:
        # Create sandbox and execute code
        sandbox = Sandbox.create(timeout=30)
        execution = sandbox.run_code(code)

        if not execution.results:
            return {"error": "No results from code execution"}

        first_result = execution.results[0]

        # Check if PNG was generated
        if first_result.png:
            # Generate unique chart ID
            chart_id = f"chart_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Get base64 PNG data (already base64 encoded from sandbox)
            png_base64 = first_result.png

            # Create HTML wrapper with embedded PNG
            chart_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chart</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background: white;
        }}
        img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 0 auto;
        }}
    </style>
</head>
<body>
    <img src="data:image/png;base64,{png_base64}" alt="Chart" />
</body>
</html>
"""

            # Save HTML file
            chart_file = CHARTS_DIR / f"{chart_id}.html"
            CHARTS_DIR.mkdir(parents=True, exist_ok=True)

            with open(chart_file, "w", encoding="utf-8") as f:
                f.write(chart_html)

            # Create chart metadata
            chart_data = {
                "filename": f"{chart_id}.html",
                "data": chart_html,
                "reference": chart_id,
                "type": "text/html",
                "chart_type": "custom_plot",
                "created_at": datetime.now().isoformat(),
                "file_path": str(chart_file),
            }

            # Save chart data
            set_chart_data(chart_data)

            return "chart created successfully"
    except Exception as e:
        return f"Error executing code: {str(e)}"
    finally:
        if sandbox:
            try:
                sandbox.kill()
            except:
                pass


@tool(parse_docstring=True)
def create_financial_stock_chart(
    symbols: List[str],
    period: str = "daily",
    chart_type: str = "candlestick",
    time_range_days: int = 180,
    include_volume: bool = True,
    technical_indicators: Optional[List[str]] = None,
    layout_style: str = "professional",
) -> dict:
    """Create professional financial stock charts with technical indicators.

    Use this tool for stock price charts (candlestick, OHLC, line, area),
    technical analysis (SMA, EMA, Bollinger Bands, RSI, MACD), and volume analysis
    for up to 4 symbols.

    Args:
        symbols: List of stock symbols (for example, ["AAPL", "MSFT"]). Maximum 4 symbols.
        period: "daily" or "intraday" (default "daily").
        chart_type: "candlestick", "ohlc", "line", or "area" (default "candlestick").
        time_range_days: Number of days of historical data to display (default 180, max 1000).
        include_volume: Whether to show a volume subplot (default True).
        technical_indicators: List of indicators such as "sma", "ema", "bollinger", "rsi", "macd".
        layout_style: "professional", "dark", or "minimal" (default "professional").
    """

    try:
        # Input validation and defaults
        if not symbols or len(symbols) == 0:
            return {"error": "At least one stock symbol is required"}

        if len(symbols) > 4:
            return {"error": "Maximum 4 symbols allowed for optimal visualization"}

        # Set default technical indicators if none provided
        if technical_indicators is None:
            technical_indicators = ["sma"]

        # Ensure charts directory exists
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)

        # Modern color palette
        COLORS = {
            "professional": {
                "primary": ["#2E86C1", "#E74C3C", "#F39C12", "#8E44AD"],
                "secondary": ["#5DADE2", "#EC7063", "#F7C71A", "#BB8FCE"],
                "background": "#FFFFFF",
                "grid": "#F8F9FA",
                "text": "#2C3E50",
                "candlestick_up": "#00C851",
                "candlestick_down": "#FF4444",
                "volume": "rgba(70, 130, 180, 0.5)",
            },
            "dark": {
                "primary": ["#00D4AA", "#FF6B6B", "#4ECDC4", "#45B7D1"],
                "secondary": ["#96CEB4", "#FECA57", "#FF9FF3", "#54A0FF"],
                "background": "#1E1E1E",
                "grid": "#2D2D2D",
                "text": "#FFFFFF",
                "candlestick_up": "#00D4AA",
                "candlestick_down": "#FF6B6B",
                "volume": "rgba(0, 212, 170, 0.3)",
            },
            "minimal": {
                "primary": ["#6C5CE7", "#00B894", "#FDCB6E", "#E17055"],
                "secondary": ["#A29BFE", "#00CEC9", "#FDCB6E", "#FD79A8"],
                "background": "#FDFDFD",
                "grid": "#F1F2F6",
                "text": "#2D3436",
                "candlestick_up": "#00B894",
                "candlestick_down": "#E17055",
                "volume": "rgba(108, 92, 231, 0.4)",
            },
        }

        color_scheme = COLORS.get(layout_style, COLORS["professional"])

        # Fetch data for all symbols
        stock_data = {}
        failed_symbols = []

        for symbol in symbols:
            try:
                # Fetch market data with increased limits
                if period.lower() == "intraday":
                    response = get_intraday_data.func(
                        symbols=symbol,
                        interval="1hour",
                        limit=min(time_range_days * 12, 1000),
                    )
                else:
                    response = get_eod_data.func(
                        symbols=symbol, limit=min(max(time_range_days, 250), 1000)
                    )

                if (
                    "error" in response
                    or "data" not in response
                    or not response["data"]
                ):
                    failed_symbols.append(symbol)
                    continue

                # Process data
                df = pd.DataFrame(response["data"])
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date").sort_index()

                # Ensure numeric columns
                numeric_cols = ["open", "high", "low", "close", "volume"]
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")

                # Validate required data
                required_cols = ["open", "high", "low", "close"]
                if not all(col in df.columns for col in required_cols):
                    failed_symbols.append(symbol)
                    continue

                # Drop rows with missing OHLC data
                df = df.dropna(subset=required_cols)

                if len(df) == 0:
                    failed_symbols.append(symbol)
                    continue

                # Limit data to requested time range
                if time_range_days > 0:
                    df = df.tail(time_range_days)

                # Calculate technical indicators
                if "sma" in technical_indicators:
                    df["SMA_20"] = calculate_sma(df["close"], 20)
                    df["SMA_50"] = calculate_sma(df["close"], 50)

                if "ema" in technical_indicators:
                    df["EMA_12"] = calculate_ema(df["close"], 12)
                    df["EMA_26"] = calculate_ema(df["close"], 26)

                if "bollinger" in technical_indicators:
                    df["BB_Upper"], df["BB_Middle"], df["BB_Lower"] = (
                        calculate_bollinger_bands(df["close"])
                    )

                if "rsi" in technical_indicators:
                    df["RSI"] = calculate_rsi(df["close"])

                if "macd" in technical_indicators:
                    df["MACD"], df["MACD_Signal"], df["MACD_Histogram"] = (
                        calculate_macd(df["close"])
                    )

                stock_data[symbol] = df

            except Exception as e:
                failed_symbols.append(symbol)
                continue

        if not stock_data:
            return {
                "error": f"Could not retrieve data for any symbols. Failed: {', '.join(failed_symbols)}"
            }

        successful_symbols = list(stock_data.keys())

        # Create chart layout
        subplot_count = len(successful_symbols)
        has_rsi = "rsi" in technical_indicators
        has_macd = "macd" in technical_indicators
        has_volume = include_volume and any(
            "volume" in df.columns for df in stock_data.values()
        )

        # Calculate subplot rows
        extra_rows = 0
        if has_volume:
            extra_rows += 1
        if has_rsi:
            extra_rows += 1
        if has_macd:
            extra_rows += 1

        total_rows = subplot_count + extra_rows
        row_heights = []

        # Main price charts get more height
        for _ in range(subplot_count):
            row_heights.append(
                0.65 / subplot_count if extra_rows > 0 else 1.0 / subplot_count
            )

        # Technical indicator rows get optimized heights
        if has_volume:
            row_heights.append(0.18 if extra_rows > 1 else 0.4)
        if has_rsi:
            row_heights.append(0.085 if extra_rows > 1 else 0.3)
        if has_macd:
            row_heights.append(0.085 if extra_rows > 1 else 0.3)

        # Create subplot specifications
        specs = [[{"secondary_y": False}] for _ in range(total_rows)]
        subplot_titles = []

        for symbol in successful_symbols:
            latest_price = stock_data[symbol]["close"].iloc[-1]
            price_change = (
                stock_data[symbol]["close"].iloc[-1]
                - stock_data[symbol]["close"].iloc[-2]
                if len(stock_data[symbol]) > 1
                else 0
            )
            change_pct = (
                (price_change / stock_data[symbol]["close"].iloc[-2] * 100)
                if len(stock_data[symbol]) > 1
                and stock_data[symbol]["close"].iloc[-2] != 0
                else 0
            )

            change_symbol = "+" if price_change >= 0 else ""
            subplot_titles.append(
                f"{symbol} - ${latest_price:.2f} ({change_symbol}{change_pct:.2f}%)"
            )

        if has_volume:
            subplot_titles.append("Volume")
        if has_rsi:
            subplot_titles.append("RSI")
        if has_macd:
            subplot_titles.append("MACD")

        # Create the figure
        fig = make_subplots(
            rows=total_rows,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.015,  # Reduced spacing for more chart area
            subplot_titles=subplot_titles,
            specs=specs,
            row_heights=row_heights,
        )

        # Plot main price charts
        for i, symbol in enumerate(successful_symbols):
            df = stock_data[symbol]
            row = i + 1
            color = color_scheme["primary"][i % len(color_scheme["primary"])]

            # Main price chart
            if chart_type == "candlestick":
                fig.add_trace(
                    go.Candlestick(
                        x=df.index,
                        open=df["open"],
                        high=df["high"],
                        low=df["low"],
                        close=df["close"],
                        name=f"{symbol}",
                        increasing=dict(
                            line=dict(color=color_scheme["candlestick_up"], width=2)
                        ),
                        decreasing=dict(
                            line=dict(color=color_scheme["candlestick_down"], width=2)
                        ),
                        showlegend=True,
                    ),
                    row=row,
                    col=1,
                )
            elif chart_type == "ohlc":
                fig.add_trace(
                    go.Ohlc(
                        x=df.index,
                        open=df["open"],
                        high=df["high"],
                        low=df["low"],
                        close=df["close"],
                        name=f"{symbol}",
                        increasing=dict(
                            line=dict(color=color_scheme["candlestick_up"], width=2)
                        ),
                        decreasing=dict(
                            line=dict(color=color_scheme["candlestick_down"], width=2)
                        ),
                        showlegend=True,
                    ),
                    row=row,
                    col=1,
                )
            elif chart_type == "line":
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df["close"],
                        mode="lines",
                        name=f"{symbol}",
                        line=dict(color=color, width=3),
                        showlegend=True,
                    ),
                    row=row,
                    col=1,
                )
            elif chart_type == "area":
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df["close"],
                        mode="lines",
                        fill="tonexty",
                        name=f"{symbol}",
                        line=dict(color=color, width=2),
                        fillcolor=f"rgba{tuple(list(bytes.fromhex(color.lstrip('#'))) + [0.1])}",
                        showlegend=True,
                    ),
                    row=row,
                    col=1,
                )

            # Add technical indicators
            if "sma" in technical_indicators:
                if "SMA_20" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["SMA_20"],
                            mode="lines",
                            name=f"{symbol} SMA(20)",
                            line=dict(
                                color="#FFA500",  # Orange - more visible
                                width=3,
                                dash="dash",
                            ),
                            showlegend=True,
                            opacity=0.9,
                        ),
                        row=row,
                        col=1,
                    )

                if "SMA_50" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["SMA_50"],
                            mode="lines",
                            name=f"{symbol} SMA(50)",
                            line=dict(
                                color="#9932CC",  # Purple - more visible
                                width=3,
                                dash="dot",
                            ),
                            showlegend=True,
                            opacity=0.9,
                        ),
                        row=row,
                        col=1,
                    )

            if "ema" in technical_indicators:
                if "EMA_12" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["EMA_12"],
                            mode="lines",
                            name=f"{symbol} EMA(12)",
                            line=dict(
                                color=color_scheme["primary"][
                                    i % len(color_scheme["primary"])
                                ],
                                width=1.5,
                                dash="dash",
                            ),
                            opacity=0.8,
                            showlegend=True,
                        ),
                        row=row,
                        col=1,
                    )

            if "bollinger" in technical_indicators:
                if all(
                    col in df.columns for col in ["BB_Upper", "BB_Middle", "BB_Lower"]
                ):
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["BB_Upper"],
                            mode="lines",
                            name=f"{symbol} BB Upper",
                            line=dict(color="rgba(128,128,128,0.5)", width=1),
                            showlegend=False,
                        ),
                        row=row,
                        col=1,
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["BB_Lower"],
                            mode="lines",
                            name=f"{symbol} BB Lower",
                            line=dict(color="rgba(128,128,128,0.5)", width=1),
                            fill="tonexty",
                            fillcolor="rgba(128,128,128,0.1)",
                            showlegend=False,
                        ),
                        row=row,
                        col=1,
                    )

        # Add volume chart with improved visibility
        current_row = len(successful_symbols) + 1
        if has_volume:
            for i, symbol in enumerate(successful_symbols):
                df = stock_data[symbol]
                if "volume" in df.columns:
                    # Color volume bars based on price movement
                    colors = []
                    for j in range(len(df)):
                        if j > 0:
                            if df["close"].iloc[j] >= df["close"].iloc[j - 1]:
                                colors.append(
                                    "rgba(0, 200, 81, 0.7)"
                                )  # Green for up days
                            else:
                                colors.append(
                                    "rgba(255, 68, 68, 0.7)"
                                )  # Red for down days
                        else:
                            colors.append("rgba(100, 149, 237, 0.7)")  # Default blue

                    fig.add_trace(
                        go.Bar(
                            x=df.index,
                            y=df["volume"],
                            name=f"{symbol} Volume",
                            marker_color=colors,
                            showlegend=False,
                        ),
                        row=current_row,
                        col=1,
                    )
            current_row += 1

        # Add RSI chart
        if has_rsi:
            for i, symbol in enumerate(successful_symbols):
                df = stock_data[symbol]
                if "RSI" in df.columns:
                    color = color_scheme["primary"][i % len(color_scheme["primary"])]
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["RSI"],
                            mode="lines",
                            name=f"{symbol} RSI",
                            line=dict(color=color, width=3),  # Increased width
                            showlegend=False,
                        ),
                        row=current_row,
                        col=1,
                    )

            # Add RSI reference lines
            fig.add_hline(
                y=70,
                line_dash="dash",
                line_color="red",
                opacity=0.5,
                row=current_row,
                col=1,
            )
            fig.add_hline(
                y=30,
                line_dash="dash",
                line_color="green",
                opacity=0.5,
                row=current_row,
                col=1,
            )
            fig.add_hline(
                y=50,
                line_dash="dot",
                line_color="gray",
                opacity=0.3,
                row=current_row,
                col=1,
            )

            current_row += 1

        # Add MACD chart
        if has_macd:
            for i, symbol in enumerate(successful_symbols):
                df = stock_data[symbol]
                if all(
                    col in df.columns
                    for col in ["MACD", "MACD_Signal", "MACD_Histogram"]
                ):
                    color = color_scheme["primary"][i % len(color_scheme["primary"])]

                    # MACD line
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["MACD"],
                            mode="lines",
                            name=f"{symbol} MACD",
                            line=dict(color=color, width=3),  # Increased width
                            showlegend=False,
                        ),
                        row=current_row,
                        col=1,
                    )

                    # Signal line
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df["MACD_Signal"],
                            mode="lines",
                            name=f"{symbol} Signal",
                            line=dict(
                                color=color_scheme["secondary"][
                                    i % len(color_scheme["secondary"])
                                ],
                                width=3,  # Increased width
                            ),
                            showlegend=False,
                        ),
                        row=current_row,
                        col=1,
                    )

                    # Histogram
                    colors_hist = [
                        "green" if x >= 0 else "red" for x in df["MACD_Histogram"]
                    ]
                    fig.add_trace(
                        go.Bar(
                            x=df.index,
                            y=df["MACD_Histogram"],
                            name=f"{symbol} Histogram",
                            marker_color=colors_hist,
                            opacity=0.6,
                            showlegend=False,
                        ),
                        row=current_row,
                        col=1,
                    )

        # Update layout with modern styling
        fig.update_layout(
            title=dict(
                text=f"Professional Stock Analysis: {', '.join(successful_symbols)}",
                x=0.5,
                font=dict(
                    size=24, color=color_scheme["text"], family="Arial, sans-serif"
                ),
            ),
            template="plotly_white" if layout_style != "dark" else "plotly_dark",
            plot_bgcolor=color_scheme["background"],
            paper_bgcolor=color_scheme["background"],
            font=dict(color=color_scheme["text"], family="Arial, sans-serif"),
            height=300
            + (450 * len(successful_symbols))
            + (200 * extra_rows),  # Increased height
            margin=dict(l=60, r=60, t=120, b=100),  # Optimized margins
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.05,
                xanchor="center",
                x=0.5,
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="rgba(0,0,0,0.2)",
                borderwidth=1,
            ),
            xaxis=dict(
                rangeslider=dict(visible=False),
                rangeselector=dict(
                    buttons=list(
                        [
                            dict(count=7, label="7D", step="day", stepmode="backward"),
                            dict(
                                count=30, label="30D", step="day", stepmode="backward"
                            ),
                            dict(
                                count=60, label="60D", step="day", stepmode="backward"
                            ),
                            dict(
                                count=90, label="90D", step="day", stepmode="backward"
                            ),
                            dict(step="all", label="ALL"),
                        ]
                    ),
                    bgcolor=color_scheme["grid"],
                    activecolor=color_scheme["primary"][0],
                ),
            ),
        )

        # Style all subplots
        fig.update_xaxes(
            gridcolor=color_scheme["grid"],
            showline=True,
            linecolor=color_scheme["grid"],
            mirror=True,
        )
        fig.update_yaxes(
            gridcolor=color_scheme["grid"],
            showline=True,
            linecolor=color_scheme["grid"],
            mirror=True,
        )

        # Generate unique chart ID and save
        chart_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Convert to HTML with modern configuration
        chart_html = fig.to_html(
            include_plotlyjs="cdn",
            div_id=f"professional_stock_chart_{timestamp}",
            config={
                "displayModeBar": True,
                "responsive": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": [
                    "drawline",
                    "drawopenpath",
                    "drawclosedpath",
                    "drawcircle",
                    "drawrect",
                    "eraseshape",
                ],
                "modeBarButtonsToRemove": ["pan2d", "lasso2d"],
                "toImageButtonOptions": {
                    "format": "png",
                    "filename": f"stock_chart_{timestamp}",
                    "height": 800,
                    "width": 1200,
                    "scale": 2,
                },
            },
        )

        # Save chart file
        chart_file = CHARTS_DIR / f"{chart_id}.html"

        # Create chart metadata
        chart_data = {
            "filename": f"{chart_id}.html",
            "data": chart_html,
            "reference": chart_id,
            "type": "text/html",
            "symbols": successful_symbols,
            "chart_type": chart_type,
            "period": period,
            "time_range_days": time_range_days,
            "technical_indicators": technical_indicators,
            "layout_style": layout_style,
            "created_at": datetime.now().isoformat(),
            "file_path": str(chart_file),
            "data_points": sum(len(df) for df in stock_data.values()),
            "failed_symbols": failed_symbols,
        }

        # Save chart data and file
        set_chart_data(chart_data)

        try:
            with open(chart_file, "w", encoding="utf-8") as f:
                f.write(chart_html)
        except Exception as e:
            pass  # Silent fail for file writing issues

        success_message = (
            f"Chart created: {', '.join(successful_symbols)} | {chart_type.title()}"
        )

        if failed_symbols:
            success_message += f" | Failed: {', '.join(failed_symbols)}"

        return {"message": success_message}

    except Exception as e:
        return {"error": f"Chart creation failed: {str(e)}"}
