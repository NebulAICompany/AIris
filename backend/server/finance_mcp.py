import httpx
import sys
from pathlib import Path
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
import uuid

# Add project root to Python path to allow imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.shared.constants import (
    ALPHA_VANTAGE_API_KEY,
    ALPHA_VANTAGE_BASE_URL,
    CHARTS_DIR,
)

# Setup logging for chart operations using loguru
from loguru import logger

chart_logger = logger.bind(name="CHART_OPERATIONS")

mcp = FastMCP("finance")

# Global chart data storage
all_chart_data = []


async def make_request(params: Dict[str, Any]) -> Dict[str, Any]:
    """Alpha Vantage API'sine async istek gönder"""
    params["apikey"] = ALPHA_VANTAGE_API_KEY

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(ALPHA_VANTAGE_BASE_URL, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def get_intraday_data(
    symbol: str,
    interval: str,
    outputsize: str = None,
    adjusted: bool = None,
    extended_hours: bool = None,
    month: str = None,
):
    """
    Fetch intraday OHLCV data from Alpha Vantage.

    Required:
        symbol (str): Stock ticker (e.g., "IBM")
        interval (str): "1min" | "5min" | "15min" | "30min" | "60min"

    Optional:
        outputsize (str): "compact" or "full"
        adjusted (bool): True/False
        extended_hours (bool): True/False
        month (str): YYYY-MM format (e.g., "2009-01")

    Returns:
        dict: Intraday time series data with OHLCV values covering current and 20+ years of historical data
    """

    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": symbol,
        "interval": interval,
        **({"outputsize": outputsize} if outputsize else {}),
        **({"adjusted": str(adjusted).lower()} if adjusted is not None else {}),
        **(
            {"extended_hours": str(extended_hours).lower()}
            if extended_hours is not None
            else {}
        ),
        **({"month": month} if month else {}),
    }

    return await make_request(params)


@mcp.tool()
async def get_daily_data(
    symbol: str,
    outputsize: str = None,
):
    """
    Fetch daily OHLCV time series data from Alpha Vantage.

    Required:
        symbol (str): Stock ticker (e.g., "IBM")

    Optional:
        outputsize (str): "compact" or "full"

    Returns:
        dict: Raw daily time series data with OHLCV values covering 20+ years of historical data
    """

    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        **({"outputsize": outputsize} if outputsize else {}),
    }

    return await make_request(params)


@mcp.tool()
async def get_weekly_data(
    symbol: str,
):
    """
    Fetch weekly OHLCV time series data from Alpha Vantage.

    Required:
        symbol (str): Stock ticker (e.g., "IBM")

    Returns:
        dict: Weekly time series data with OHLCV values covering 20+ years of historical data
    """

    params = {
        "function": "TIME_SERIES_WEEKLY",
        "symbol": symbol,
    }

    return await make_request(params)


@mcp.tool()
async def get_weekly_adjusted_data(
    symbol: str,
):
    """
    Fetch weekly adjusted OHLCV time series data from Alpha Vantage.

    Required:
        symbol (str): Stock ticker (e.g., "IBM")

    Returns:
        dict: Weekly adjusted time series data with OHLCV values, adjusted close, volume and dividend covering 20+ years of historical data
    """

    params = {
        "function": "TIME_SERIES_WEEKLY_ADJUSTED",
        "symbol": symbol,
    }

    return await make_request(params)


@mcp.tool()
async def get_monthly_data(
    symbol: str,
):
    """
    Fetch monthly OHLCV time series data from Alpha Vantage.

    Required:
        symbol (str): Stock ticker (e.g., "IBM")

    Returns:
        dict: Monthly time series data with OHLCV values covering 20+ years of historical data
    """

    params = {
        "function": "TIME_SERIES_MONTHLY",
        "symbol": symbol,
    }

    return await make_request(params)


@mcp.tool()
async def get_monthly_adjusted_data(
    symbol: str,
):
    """
    Fetch monthly adjusted OHLCV time series data from Alpha Vantage.

    Required:
        symbol (str): Stock ticker (e.g., "IBM")

    Returns:
        dict: Monthly adjusted time series data with OHLCV values, adjusted close, volume and dividend covering 20+ years of historical data
    """

    params = {
        "function": "TIME_SERIES_MONTHLY_ADJUSTED",
        "symbol": symbol,
    }

    return await make_request(params)


@mcp.tool()
async def get_global_quote(
    symbol: str,
):
    """
    Fetch latest price and volume information for a ticker from Alpha Vantage.

    Required:
        symbol (str): Stock ticker (e.g., "IBM")

    Returns:
        dict: Latest price and volume information for the specified ticker
    """

    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
    }

    return await make_request(params)


# Chart management functions
def get_chart_datas():
    chart_logger.info(
        f"📊 get_chart_datas() called - Returning {len(all_chart_data)} charts"
    )
    for i, chart in enumerate(all_chart_data):
        chart_logger.info(
            f"  Chart {i+1}: {type(chart)} - Length: {len(str(chart)) if chart else 0}"
        )
    return all_chart_data


def set_chart_data(data):
    global all_chart_data
    chart_logger.info(f"📊 set_chart_data() called with data type: {type(data)}")
    chart_logger.info(f"  Data length: {len(str(data)) if data else 0}")
    chart_logger.info(f"  Data preview: {str(data)[:200] if data else 'None'}...")
    all_chart_data = data
    chart_logger.info(
        f"  Global all_chart_data updated - Now contains {len(all_chart_data)} charts"
    )


@mcp.tool()
async def create_stock_chart(
    symbols: list,
    period: str = "daily",
    chart_type: str = "candlestick",
    time_range_days: int = 30,
    include_volume: bool = True,
    include_ma: bool = True,
    ma_period: int = 20,
    subplot_layout: str = "single",
    outputsize: str = "compact",
):
    """
    Creates comprehensive stock charts using Alpha Vantage data with multiple layout options.
    Implements QuantStart methodology for advanced subplot configurations.

    Required:
        symbols (list): List of stock symbols (e.g., ["AAPL", "MSFT"])

    Optional:
        period (str): "daily" | "weekly" | "monthly" | "intraday"
        chart_type (str): "candlestick" | "line" | "area"
        time_range_days (int): Number of days to display (default: 30)
        include_volume (bool): Whether to show volume chart
        include_ma (bool): Whether to show moving average
        ma_period (int): Moving average period (default: 20)
        subplot_layout (str): "single" | "grid" | "vertical" | "quantstart"
        outputsize (str): "compact" | "full"

    Returns:
        dict: Chart HTML and operation result
    """
    try:
        # Ensure CHARTS_DIR exists
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        chart_logger.info(f"📁 Charts directory ensured: {CHARTS_DIR}")
        chart_logger.info(f"🚀 Starting chart creation for symbols: {symbols}")

        if len(symbols) > 6:
            return {"error": "En fazla 6 hisse senedi analiz edilebilir"}

        stock_data = {}
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

        # Her sembol için veri toplama
        for symbol in symbols:
            try:
                data_response = None

                if period.lower() == "intraday":
                    data_response = await get_intraday_data(
                        symbol=symbol, interval="60min", outputsize=outputsize
                    )
                elif period.lower() == "daily":
                    data_response = await get_daily_data(
                        symbol=symbol, outputsize=outputsize
                    )
                elif period.lower() == "weekly":
                    data_response = await get_weekly_data(symbol=symbol)
                elif period.lower() == "monthly":
                    data_response = await get_monthly_data(symbol=symbol)
                else:
                    continue

                if "error" in data_response or "Error Message" in data_response:
                    continue

                # Time series verisini bul
                time_series_key = None
                for key in data_response.keys():
                    if "Time Series" in key:
                        time_series_key = key
                        break

                if not time_series_key:
                    continue

                # DataFrame'e çevir
                raw_data = data_response[time_series_key]
                df = pd.DataFrame.from_dict(raw_data, orient="index")
                df.index = pd.to_datetime(df.index)

                # Kolon isimlerini standardize et - QuantStart yaklaşımı
                if len(df.columns) >= 5:
                    # AlphaVantage adjusted data için
                    if "adjusted_close" in str(df.columns).lower():
                        df.columns = [
                            "open",
                            "high",
                            "low",
                            "close",
                            "adjusted_close",
                            "volume",
                        ][: len(df.columns)]
                    else:
                        df.columns = ["Open", "High", "Low", "Close", "Volume"]
                elif len(df.columns) == 4:
                    df.columns = ["Open", "High", "Low", "Close"]

                # Numeric'e çevir ve sırala
                for col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df = df.sort_index()

                # Tarih filtreleme
                if time_range_days and time_range_days > 0:
                    df = df.tail(time_range_days)

                # Moving Average hesapla - QuantStart metoduyla
                if include_ma and len(df) >= ma_period:
                    close_col = (
                        "adjusted_close" if "adjusted_close" in df.columns else "Close"
                    )
                    df[f"MA{ma_period}"] = (
                        df[close_col].rolling(window=ma_period).mean()
                    )

                stock_data[symbol] = df

            except Exception:
                continue

        if not stock_data:
            return {"error": "Hiçbir sembol için veri alınamadı"}

        # Grafik oluşturma
        fig = None
        symbols_list = list(stock_data.keys())

        if subplot_layout == "quantstart" and len(symbols_list) >= 5:
            fig = make_subplots(
                rows=3,
                cols=2,
                specs=[
                    [{"colspan": 2, "secondary_y": True}, None],
                    [{"secondary_y": True}, {"secondary_y": True}],
                    [{"secondary_y": True}, {"secondary_y": True}],
                ],
                subplot_titles=symbols_list,
                x_title="Date",
                y_title="OHLC",
            )

            plot_symbols = [symbols_list[0], symbols_list[0]] + symbols_list[1:5]

            for i, symbol in enumerate(plot_symbols):
                # QuantStart exact logic
                if i == 1:
                    row = 1
                    col = 1
                else:
                    row = (i // 2) + 1
                    col = (i % 2) + 1

                df = stock_data[symbol]
                close_col = (
                    "adjusted_close" if "adjusted_close" in df.columns else "Close"
                )

                fig.add_trace(
                    go.Candlestick(
                        x=df.index,
                        open=df["open"] if "open" in df.columns else df["Open"],
                        high=df["high"] if "high" in df.columns else df["High"],
                        low=df["low"] if "low" in df.columns else df["Low"],
                        close=df[close_col],
                        name="OHLC",
                    ),
                    row=row,
                    col=col,
                )

                if include_volume and (
                    "volume" in df.columns or "Volume" in df.columns
                ):
                    vol_col = "volume" if "volume" in df.columns else "Volume"
                    fig.add_trace(
                        go.Bar(
                            x=df.index,
                            y=df[vol_col],
                            opacity=0.1,
                            marker=dict(color="blue"),
                            name="volume",
                        ),
                        row=row,
                        col=col,
                        secondary_y=True,
                    )

                if include_ma and f"MA{ma_period}" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[f"MA{ma_period}"],
                            line=dict(color="black", width=1),
                            name=f"{ma_period} day MA",
                            yaxis="y2",
                        ),
                        row=row,
                        col=col,
                        secondary_y=False,
                    )

                fig.layout.yaxis2.showgrid = False

            fig.update_layout(
                showlegend=False,
                title_text=f"OHLC data for {', '.join(symbols_list)}",
                title_xref="paper",
                title_x=0.5,
                title_xanchor="center",
            )
            fig.update_xaxes(rangeslider_visible=False)

        elif subplot_layout == "single" and len(symbols_list) == 1:
            symbol = symbols_list[0]
            df = stock_data[symbol]
            close_col = "adjusted_close" if "adjusted_close" in df.columns else "Close"

            if include_volume and ("volume" in df.columns or "Volume" in df.columns):
                fig = make_subplots(
                    rows=2,
                    cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.03,
                    subplot_titles=(f"{symbol} {chart_type.title()}", "Volume"),
                    row_width=[0.7, 0.3],
                )

                # Ana grafik
                if chart_type == "candlestick":
                    fig.add_trace(
                        go.Candlestick(
                            x=df.index,
                            open=df["open"] if "open" in df.columns else df["Open"],
                            high=df["high"] if "high" in df.columns else df["High"],
                            low=df["low"] if "low" in df.columns else df["Low"],
                            close=df[close_col],
                            name=f"{symbol} OHLC",
                            increasing=dict(line=dict(color="#00ff00")),
                            decreasing=dict(line=dict(color="#ff0000")),
                        ),
                        row=1,
                        col=1,
                    )
                elif chart_type == "line":
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[close_col],
                            mode="lines",
                            name=f"{symbol} Price",
                            line=dict(color=colors[0], width=2),
                        ),
                        row=1,
                        col=1,
                    )
                elif chart_type == "area":
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[close_col],
                            mode="lines",
                            fill="tonexty",
                            name=f"{symbol} Price",
                            line=dict(color=colors[0]),
                        ),
                        row=1,
                        col=1,
                    )

                # Moving Average
                if include_ma and f"MA{ma_period}" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[f"MA{ma_period}"],
                            mode="lines",
                            name=f"MA({ma_period})",
                            line=dict(color="orange", width=2, dash="dash"),
                        ),
                        row=1,
                        col=1,
                    )

                # Volume
                vol_col = "volume" if "volume" in df.columns else "Volume"
                fig.add_trace(
                    go.Bar(
                        x=df.index,
                        y=df[vol_col],
                        name="Volume",
                        marker=dict(color="rgba(158,202,225,0.6)"),
                    ),
                    row=2,
                    col=1,
                )

            else:
                fig = go.Figure()

                # Ana grafik
                if chart_type == "candlestick":
                    fig.add_trace(
                        go.Candlestick(
                            x=df.index,
                            open=df["open"] if "open" in df.columns else df["Open"],
                            high=df["high"] if "high" in df.columns else df["High"],
                            low=df["low"] if "low" in df.columns else df["Low"],
                            close=df[close_col],
                            name=f"{symbol} OHLC",
                            increasing=dict(line=dict(color="#00ff00")),
                            decreasing=dict(line=dict(color="#ff0000")),
                        )
                    )
                elif chart_type == "line":
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[close_col],
                            mode="lines",
                            name=f"{symbol} Price",
                            line=dict(color=colors[0], width=2),
                        )
                    )
                elif chart_type == "area":
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[close_col],
                            mode="lines",
                            fill="tonexty",
                            name=f"{symbol} Price",
                            line=dict(color=colors[0]),
                        )
                    )

                # Moving Average
                if include_ma and f"MA{ma_period}" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[f"MA{ma_period}"],
                            mode="lines",
                            name=f"MA({ma_period})",
                            line=dict(color="orange", width=2, dash="dash"),
                        )
                    )

            fig.update_layout(
                title=f"{symbol} Stock Analysis",
                template="plotly_white",
                height=(
                    600
                    if (
                        include_volume
                        and ("volume" in df.columns or "Volume" in df.columns)
                    )
                    else 400
                ),
                showlegend=True,
                xaxis_title="Date",
                yaxis_title="Price (USD)",
                hovermode="x unified",
            )

        # GRID LAYOUT
        elif subplot_layout == "grid":
            rows = (len(symbols_list) + 1) // 2
            cols = 2 if len(symbols_list) > 1 else 1

            specs = []
            for _ in range(rows):
                row_specs = []
                for _ in range(cols):
                    row_specs.append({"secondary_y": True} if include_volume else {})
                specs.append(row_specs)

            fig = make_subplots(
                rows=rows,
                cols=cols,
                specs=specs,
                subplot_titles=symbols_list,
                vertical_spacing=0.08,
                horizontal_spacing=0.05,
            )

            for i, symbol in enumerate(symbols_list):
                row = (i // cols) + 1
                col = (i % cols) + 1
                df = stock_data[symbol]
                color = colors[i % len(colors)]
                close_col = (
                    "adjusted_close" if "adjusted_close" in df.columns else "Close"
                )

                # Ana grafik
                if chart_type == "candlestick":
                    fig.add_trace(
                        go.Candlestick(
                            x=df.index,
                            open=df["open"] if "open" in df.columns else df["Open"],
                            high=df["high"] if "high" in df.columns else df["High"],
                            low=df["low"] if "low" in df.columns else df["Low"],
                            close=df[close_col],
                            name=f"{symbol}",
                            showlegend=False,
                            increasing=dict(line=dict(color="#00ff00")),
                            decreasing=dict(line=dict(color="#ff0000")),
                        ),
                        row=row,
                        col=col,
                    )
                elif chart_type == "line":
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[close_col],
                            mode="lines",
                            name=f"{symbol}",
                            line=dict(color=color, width=2),
                            showlegend=False,
                        ),
                        row=row,
                        col=col,
                    )
                elif chart_type == "area":
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[close_col],
                            mode="lines",
                            fill="tonexty",
                            name=f"{symbol}",
                            line=dict(color=color),
                            showlegend=False,
                        ),
                        row=row,
                        col=col,
                    )

                # Moving Average
                if include_ma and f"MA{ma_period}" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[f"MA{ma_period}"],
                            mode="lines",
                            name=f"{symbol} MA",
                            line=dict(color="orange", width=1, dash="dash"),
                            showlegend=False,
                        ),
                        row=row,
                        col=col,
                    )

                # Volume
                if include_volume and (
                    "volume" in df.columns or "Volume" in df.columns
                ):
                    vol_col = "volume" if "volume" in df.columns else "Volume"
                    fig.add_trace(
                        go.Bar(
                            x=df.index,
                            y=df[vol_col],
                            name=f"{symbol} Volume",
                            opacity=0.3,
                            marker_color=dict(color=color),
                            showlegend=False,
                        ),
                        row=row,
                        col=col,
                        secondary_y=True,
                    )

            fig.update_layout(
                title="Multi-Stock Analysis (Grid Layout)",
                height=300 * rows,
                showlegend=False,
                template="plotly_white",
            )

        else:
            specs = [
                [{"secondary_y": True}] if include_volume else [{}]
                for _ in symbols_list
            ]

            fig = make_subplots(
                rows=len(symbols_list),
                cols=1,
                specs=specs,
                subplot_titles=symbols_list,
                vertical_spacing=0.05,
            )

            for i, symbol in enumerate(symbols_list):
                row = i + 1
                df = stock_data[symbol]
                color = colors[i % len(colors)]
                close_col = (
                    "adjusted_close" if "adjusted_close" in df.columns else "Close"
                )

                # Ana grafik
                if chart_type == "candlestick":
                    fig.add_trace(
                        go.Candlestick(
                            x=df.index,
                            open=df["open"] if "open" in df.columns else df["Open"],
                            high=df["high"] if "high" in df.columns else df["High"],
                            low=df["low"] if "low" in df.columns else df["Low"],
                            close=df[close_col],
                            name=f"{symbol}",
                            showlegend=False,
                            increasing=dict(line=dict(color="#00ff00")),
                            decreasing=dict(line=dict(color="#ff0000")),
                        ),
                        row=row,
                        col=1,
                    )
                elif chart_type == "line":
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[close_col],
                            mode="lines",
                            name=f"{symbol}",
                            line=dict(color=color, width=2),
                            showlegend=False,
                        ),
                        row=row,
                        col=1,
                    )
                elif chart_type == "area":
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[close_col],
                            mode="lines",
                            fill="tonexty",
                            name=f"{symbol}",
                            line=dict(color=color),
                            showlegend=False,
                        ),
                        row=row,
                        col=1,
                    )

                # Moving Average
                if include_ma and f"MA{ma_period}" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[f"MA{ma_period}"],
                            mode="lines",
                            name=f"{symbol} MA",
                            line=dict(color="orange", width=1, dash="dash"),
                            showlegend=False,
                        ),
                        row=row,
                        col=1,
                    )

                # Volume
                if include_volume and (
                    "volume" in df.columns or "Volume" in df.columns
                ):
                    vol_col = "volume" if "volume" in df.columns else "Volume"
                    fig.add_trace(
                        go.Bar(
                            x=df.index,
                            y=df[vol_col],
                            name=f"{symbol} Volume",
                            opacity=0.3,
                            marker_color=dict(color=color),
                            showlegend=False,
                        ),
                        row=row,
                        col=1,
                        secondary_y=True,
                    )

            fig.update_layout(
                title="Multi-Stock Analysis (Vertical Layout)",
                height=400 * len(symbols_list),
                showlegend=False,
                template="plotly_white",
            )

        if fig is None:
            return {"error": "Grafik oluşturulamadı"}

        # Ortak layout ayarları
        fig.update_xaxes(rangeslider_visible=False)

        # Range selector ekle (sadece single layout için)
        if subplot_layout == "single":
            fig.update_xaxes(
                rangeselector=dict(
                    buttons=list(
                        [
                            dict(
                                count=1, label="1M", step="month", stepmode="backward"
                            ),
                            dict(
                                count=3, label="3M", step="month", stepmode="backward"
                            ),
                            dict(
                                count=6, label="6M", step="month", stepmode="backward"
                            ),
                            dict(count=1, label="1Y", step="year", stepmode="backward"),
                            dict(step="all"),
                        ]
                    )
                )
            )

        # HTML'e çevir
        chart_logger.info("🔄 Converting chart to HTML...")
        chart_html = fig.to_html(
            include_plotlyjs="cdn",
            div_id=f"stock_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            config={"displayModeBar": True, "responsive": True},
        )

        chart_logger.info(f"✅ HTML generated successfully - Length: {len(chart_html)}")
        chart_logger.info(f"  HTML preview: {chart_html[:300]}...")

        chart_logger.info("📊 Setting chart data in global variable...")
        set_chart_data(chart_html)

        chart_id = str(uuid.uuid4())
        chart_file = CHARTS_DIR / f"{chart_id}.html"

        chart_logger.info(f"💾 Saving chart to file: {chart_file}")
        try:
            with open(chart_file, "w", encoding="utf-8") as f:
                f.write(chart_html)
            chart_logger.info(f"✅ Chart saved successfully to {chart_file}")
        except Exception as e:
            chart_logger.error(f"❌ Error saving chart to file: {e}")

        chart_logger.info(f"🎯 Chart operation completed - ID: {chart_id}")
        return {
            "message": f"✅ {len(symbols_list)} hisse için {chart_type} grafiği oluşturuldu ({subplot_layout} layout)"
        }

    except Exception as e:
        return {"error": f"Stock chart oluşturma hatası: {str(e)}"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
