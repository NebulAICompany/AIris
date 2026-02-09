from typing import Optional, List
from e2b_code_interpreter import Sandbox
from pydantic import BaseModel, Field
from langchain.tools import tool
from dotenv import load_dotenv
import uuid
from datetime import datetime, timedelta
from backend.shared.constants import CHARTS_DIR, CHART_DATA_FILE
from backend.core.tools.finance import (
    calculate_sma,
    calculate_ema,
    calculate_bollinger_bands,
    calculate_rsi,
    calculate_macd,
    get_eod_data,
)
import json
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from backend.shared.logger import get_logger

logger = get_logger("PLOTTING")

load_dotenv()



def get_missing_dates(df):
    """Identify missing business days in a DataFrame with a DateTimeIndex."""
    # Ensure index is datetime
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
        
    start_date = df.index.min().normalize()
    end_date = df.index.max().normalize()
    
    # Generate expected business days
    expected = pd.bdate_range(start=start_date, end=end_date)
    
    # Get present dates (normalized to midnight)
    present = df.index.normalize().unique()
    
    # Find missing days
    missing_business_days = expected.difference(present)
    
    # Format as strings for Plotly
    skip_dates = [d.strftime("%Y-%m-%d") for d in missing_business_days]
    return skip_dates


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
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Chart Preview</title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            background: #f5f7fa;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                         Roboto, Helvetica, Arial, sans-serif;
        }}

        .chart-wrapper {{
            background: #ffffff;
            padding: 16px;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
            width: 100%;
        }}

        .chart-wrapper img {{
            width: 100%;
            height: auto;
            border-radius: 12px;
            display: block;
        }}

    </style>
</head>

<body>
    <div class="chart-wrapper">
        <img src="data:image/png;base64,{png_base64}" alt="Chart Image" />
    </div>
    <script>
        const observer = new ResizeObserver(() => {{
            const height = document.querySelector('.chart-wrapper').getBoundingClientRect().height;
            window.parent.postMessage({{ height }}, '*');
        }});
        observer.observe(document.querySelector('.chart-wrapper'));
        
        // Initial send
        window.addEventListener('load', () => {{
             const height = document.querySelector('.chart-wrapper').getBoundingClientRect().height;
             window.parent.postMessage({{ height }}, '*');
        }});
    </script>
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
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
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
        period: "daily"
        chart_type: "candlestick", "ohlc", "line", or "area" (default "candlestick").
        date_from: Start date in YYYY-MM-DD format for getting data from. If not provided, 90 days ago will be used.
        date_to: End date in YYYY-MM-DD format for getting data to. If not provided, today's date will be used.
        include_volume: Whether to show a volume subplot (default True).
        technical_indicators: List of indicators such as "sma", "ema", "bollinger", "rsi", "macd".
        layout_style: "professional", "dark", or "minimal" (default "professional").
    """

    try:
        if date_from is None:
            date_from = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        if date_to is None:
            date_to = datetime.now().strftime("%Y-%m-%d")
        time_range_days = (datetime.strptime(date_to, "%Y-%m-%d") - datetime.strptime(date_from, "%Y-%m-%d")).days
        logger.info(f"Creating financial stock chart for symbols: {symbols}, period: {period}, chart_type: {chart_type}, date_from: {date_from}, date_to: {date_to}, time_range_days: {time_range_days}, include_volume: {include_volume}, technical_indicators: {technical_indicators}, layout_style: {layout_style}")
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
                "primary": ["#2962FF", "#00C853", "#FF6D00", "#6200EA"], # Distinct TradingView-style Blue
                "secondary": ["#82B1FF", "#B9F6CA", "#FFD180", "#EA80FC"],
                "background": "#FFFFFF",
                "grid": "#F2F4F7",
                "text": "#101828", # Slate 900
                "candlestick_up": "#089981", # TradingView Green
                "candlestick_down": "#F23645", # TradingView Red
                "volume": "rgba(41, 98, 255, 0.15)",
                "fill_opacity": 0.1,
            },
            "dark": {
                "primary": ["#2962FF", "#00BFA5", "#FFAB00", "#D500F9"],
                "secondary": ["#2979FF", "#64FFDA", "#FFD740", "#E040FB"],
                "background": "#131722", # TradingView Dark Background
                "grid": "#2A2E39", # Subtle Dark Grid
                "text": "#D1D4DC",
                "candlestick_up": "#089981",
                "candlestick_down": "#F23645",
                "volume": "rgba(41, 98, 255, 0.15)",
                "fill_opacity": 0.15,
            },
            "minimal": {
                "primary": ["#111827", "#4B5563", "#9CA3AF", "#E5E7EB"],
                "secondary": ["#374151", "#6B7280", "#D1D5DB", "#F3F4F6"],
                "background": "#FFFFFF",
                "grid": "transparent",
                "text": "#111827",
                "candlestick_up": "#111827",
                "candlestick_down": "#9CA3AF",
                "volume": "rgba(17, 24, 39, 0.05)",
                "fill_opacity": 0.05,
            },
        }

        color_scheme = COLORS.get(layout_style, COLORS["professional"])

        # Fetch data for all symbols
        stock_data = {}
        failed_symbols = []

        for symbol in symbols:
            try:
                # CURRENT SUBSCRIPTION DOES NOT SUPPORT INTRDAY. KEPT THIS PART FOR FUTURE WORK
                # Fetch market data with increased limits
                # if period.lower() == "intraday":
                #     response = get_intraday_data.func(
                #         symbols=symbol,
                #         interval="1hour",
                #         date_from=date_from,
                #         date_to=date_to,
                #         limit=min(time_range_days * 12, 1000),
                #     )
                # else:
                response = get_eod_data.func(
                    symbols=symbol,
                    date_from=date_from,
                    date_to=date_to,
                    limit=min(max(time_range_days, 250), 1000)
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
                        calculate_bollinger_bands(df["close"]))

                if "rsi" in technical_indicators:
                    df["RSI"] = calculate_rsi(df["close"])

                if "macd" in technical_indicators:
                    df["MACD"], df["MACD_Signal"], df["MACD_Histogram"] = (
                        calculate_macd(df["close"]))

                stock_data[symbol] = df

            except Exception as e:
                failed_symbols.append(symbol)
                continue

        if not stock_data:
            return {"error": f"Could not retrieve data for any symbols. Failed: {', '.join(failed_symbols)}"}

        successful_symbols = list(stock_data.keys())

        # Create chart layout
        subplot_count = len(successful_symbols)
        has_rsi = "rsi" in technical_indicators
        has_macd = "macd" in technical_indicators
        has_volume = include_volume and any(
            "volume" in df.columns for df in stock_data.values())

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
            vertical_spacing=0.06,  # Reduced spacing for more chart area
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
                            line=dict(color=color_scheme["candlestick_up"], width=2)),
                        decreasing=dict(
                            line=dict(color=color_scheme["candlestick_down"], width=2)),
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
                            line=dict(color=color_scheme["candlestick_up"], width=2)),
                        decreasing=dict(
                            line=dict(color=color_scheme["candlestick_down"], width=2)),
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
                        fillcolor=f"rgba{tuple(list(bytes.fromhex(color.lstrip('#'))) + [color_scheme.get('fill_opacity', 0.1)])}",
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

        # Optimized height calculation for single-page view
        # Base height + (per-symbol height) + (per-indicator height)
        # But capped at a reasonable max height to ensure it fits on screen
        calculated_height = 400 + (250 * subplot_count) + (150 * extra_rows)
        # Cap the height at 850px to ensure it fits on most screens
        final_height = min(calculated_height, 850)

        fig.update_layout(
            title=dict(
                text=f"{', '.join(successful_symbols)} Analysis",
                x=0.01,
                y=0.99,
                xanchor="left",
                yanchor="top",
                font=dict(
                    size=26,
                    color=color_scheme["text"],
                    family='Inter, Segoe UI, Roboto, Arial, sans-serif',
                    weight="bold",
                ),
                pad=dict(t=12, b=8),
            ),
            template="plotly_white" if layout_style != "dark" else "plotly_dark",
            plot_bgcolor=color_scheme["background"],
            paper_bgcolor=color_scheme["background"],
            font=dict(
                color=color_scheme["text"],
                family='Inter, Segoe UI, Roboto, Arial, sans-serif',
                size=14,
            ),
            height=final_height,
            margin=dict(l=32, r=32, t=80, b=48, pad=8),
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor="#22223B" if layout_style == "dark" else "#FFFFFF",
                bordercolor="#2962FF",
                font_size=15,
                font_family='Inter, Segoe UI, Roboto, Arial, sans-serif',
                font_color="#2962FF",
                namelength=-1,
            ),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(255,255,255,0.85)" if layout_style != "dark" else "rgba(19,23,34,0.85)",
                bordercolor="#E5E7EB",
                borderwidth=1,
                font=dict(size=13, color=color_scheme["text"]),
                itemclick="toggleothers",
                itemdoubleclick="toggle",
                itemsizing="constant",
                title_text="Seriler",
                title_font=dict(size=14, color="#2962FF"),
                groupclick="toggleitem",
            ),
            xaxis=dict(
                rangeslider=dict(visible=False),
                rangeselector=dict(
                    buttons=[
                        dict(count=7, label="1Hf", step="day", stepmode="backward"),
                        dict(count=1, label="1Ay", step="month", stepmode="backward"),
                        dict(count=3, label="3Ay", step="month", stepmode="backward"),
                        dict(count=6, label="6Ay", step="month", stepmode="backward"),
                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                        dict(step="all", label="Tümü"),
                    ],
                    bgcolor=color_scheme.get("grid", "#f8f9fa"),
                    activecolor=color_scheme["primary"][0],
                    font=dict(size=13),
                    y=1.0,
                    x=0.25,
                    xanchor="left",
                    bordercolor="rgba(0,0,0,0)",
                    borderwidth=0,
                ),
                tickfont=dict(size=13, color=color_scheme.get("secondary", ["#888"])[0]),
                showspikes=True,
                spikemode="across+toaxis",
                spikedash="solid",
                spikecolor="#2962FF",
                spikethickness=2,
                showline=True,
                linecolor="#2962FF",
                mirror=True,
                showgrid=True,
                gridcolor=color_scheme["grid"],
                gridwidth=1,
            ),
        )

        # Calculate missing dates for rangebreaks (skip weekends and holidays)
        # Use data from the first successful symbol as reference
        if successful_symbols:
            ref_symbol = successful_symbols[0]
            ref_df = stock_data[ref_symbol]
            skip_dates = get_missing_dates(ref_df)
            
            fig.update_xaxes(
                rangebreaks=[
                    dict(bounds=["sat", "mon"]),  # hide weekends
                    dict(values=skip_dates),      # hide missing business days
                ]
            )

        # Manually adjust annotation positions to sit in the gaps
        # This fixes the issue where titles overlap with chart lines despite spacing
        fig.for_each_annotation(lambda a: a.update(yshift=6))  # Shift up by 15 pixels

        # Style all subplots
        fig.update_xaxes(
            gridcolor=color_scheme["grid"],
            gridwidth=1.2,
            showline=True,
            linecolor="#2962FF",
            linewidth=2,
            zeroline=False,
            mirror=True,
            showspikes=True,
            spikethickness=2,
            spikedash="solid",
            spikecolor="#2962FF",
            spikemode="across+toaxis",
            ticks="outside",
            tickfont=dict(size=13, color=color_scheme.get("secondary", ["#888"])[0]),
            title_font=dict(size=15, color="#2962FF"),
        )
        fig.update_yaxes(
            gridcolor=color_scheme["grid"],
            gridwidth=1.2,
            showline=True,
            linecolor="#2962FF",
            linewidth=2,
            zeroline=False,
            mirror=True,
            tickfont=dict(size=13, color=color_scheme.get("secondary", ["#888"])[0]),
            ticks="outside",
            showspikes=True,
            spikethickness=2,
            spikedash="solid",
            spikecolor="#2962FF",
            spikemode="across+toaxis",
            title_font=dict(size=15, color="#2962FF"),
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
