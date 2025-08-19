import httpx
import sys
from pathlib import Path
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
import base64
from io import BytesIO


# Add project root to Python path to allow imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.shared.constants import ALPHA_VANTAGE_API_KEY, ALPHA_VANTAGE_BASE_URL
from backend.core.chart_storage import chart_storage

mcp = FastMCP("alpha_vantage")
async def make_request(params: Dict[str, Any]) -> Dict[str, Any]:
    """Alpha Vantage API'sine async istek gönder"""
    params['apikey'] = ALPHA_VANTAGE_API_KEY

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
        **({"extended_hours": str(extended_hours).lower()} if extended_hours is not None else {}),
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


@mcp.tool()
async def create_interactive_chart(
        symbol: str,
        period: str = "daily",
        chart_type: str = "candlestick",
        show_volume: bool = True,
        show_sma: bool = False,
        sma_period: int = 20,
        outputsize: str = "compact"
):
    """
    Creates interactive financial charts using Alpha Vantage data.

    Required:
        symbol (str): Stock symbol (e.g., "AAPL", "GOOGL")

    Optional:
        period (str): "intraday" | "daily" | "weekly" | "monthly" | "weekly_adjusted" | "monthly_adjusted"
        chart_type (str): "candlestick" | "line" | "area"
        show_volume (bool): Whether to display volume chart
        show_sma (bool): Whether to display Simple Moving Average
        sma_period (int): SMA period (default: 20)
        outputsize (str): "compact" | "full"

    Returns:
        dict: Interactive chart HTML and operation result
    """


    try:
        # 1. Uygun tool'u seçip veri çek
        data_response = None

        if period.lower() == "intraday":
            data_response = await get_intraday_data(
                symbol=symbol,
                interval="60min",
                outputsize=outputsize
            )
        elif period.lower() == "daily":
            data_response = await get_daily_data(
                symbol=symbol,
                outputsize=outputsize
            )
        elif period.lower() == "weekly":
            data_response = await get_weekly_data(symbol=symbol)
        elif period.lower() == "weekly_adjusted":
            data_response = await get_weekly_adjusted_data(symbol=symbol)
        elif period.lower() == "monthly":
            data_response = await get_monthly_data(symbol=symbol)
        elif period.lower() == "monthly_adjusted":
            data_response = await get_monthly_adjusted_data(symbol=symbol)
        else:
            return {"error": f"Desteklenmeyen period: {period}"}

        # 2. Hata kontrolü
        if "error" in data_response:
            return {"error": f"Veri çekme hatası: {data_response['error']}"}

        if "Error Message" in data_response:
            return {"error": f"Alpha Vantage hatası: {data_response['Error Message']}"}

        # 3. Veriyi DataFrame'e çevir
        # Alpha Vantage response'unda time series anahtarını bul
        time_series_key = None
        for key in data_response.keys():
            if "Time Series" in key:
                time_series_key = key
                break

        if not time_series_key:
            return {"error": "Time series verisi bulunamadı"}

        raw_data = data_response[time_series_key]
        df = pd.DataFrame.from_dict(raw_data, orient='index')
        df.index = pd.to_datetime(df.index)

        # Kolon isimlerini standardize et
        if len(df.columns) >= 5:
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        elif len(df.columns) == 4:
            df.columns = ['Open', 'High', 'Low', 'Close']

        # Numeric'e çevir ve sırala
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.sort_index()

        # Son 500 veri noktası (performans için)
        df = df.tail(500)

        # 4. SMA hesapla (istenirse)
        if show_sma and len(df) >= sma_period:
            df[f'SMA_{sma_period}'] = df['Close'].rolling(window=sma_period).mean()

        # 5. Plotly grafiği oluştur
        if show_volume and 'Volume' in df.columns:
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=(f'{symbol} {period.title()} Chart', 'Volume'),
                row_width=[0.2, 0.7]
            )
        else:
            fig = go.Figure()

        # Ana grafik tipi
        if chart_type == "candlestick":
            candlestick = go.Candlestick(
                x=df.index,
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                name=f"{symbol} OHLC",
                increasing=dict(line=dict(color='#00ff00')),
                decreasing=dict(line=dict(color='#ff0000'))
            )

            if show_volume and 'Volume' in df.columns:
                fig.add_trace(candlestick, row=1, col=1)
            else:
                fig.add_trace(candlestick)

        elif chart_type == "line":
            line_chart = go.Scatter(
                x=df.index,
                y=df['Close'],
                mode='lines',
                name=f"{symbol} Price",
                line=dict(color='#1f77b4', width=2)
            )

            if show_volume and 'Volume' in df.columns:
                fig.add_trace(line_chart, row=1, col=1)
            else:
                fig.add_trace(line_chart)

        elif chart_type == "area":
            area_chart = go.Scatter(
                x=df.index,
                y=df['Close'],
                mode='lines',
                fill='tonexty',
                name=f"{symbol} Price",
                line=dict(color='#1f77b4')
            )

            if show_volume and 'Volume' in df.columns:
                fig.add_trace(area_chart, row=1, col=1)
            else:
                fig.add_trace(area_chart)

        # SMA çizgisi ekle
        if show_sma and f'SMA_{sma_period}' in df.columns:
            sma_line = go.Scatter(
                x=df.index,
                y=df[f'SMA_{sma_period}'],
                mode='lines',
                name=f'SMA ({sma_period})',
                line=dict(color='#ff7f0e', width=2, dash='dash')
            )

            if show_volume and 'Volume' in df.columns:
                fig.add_trace(sma_line, row=1, col=1)
            else:
                fig.add_trace(sma_line)

        # Volume grafiği
        if show_volume and 'Volume' in df.columns:
            volume_bars = go.Bar(
                x=df.index,
                y=df['Volume'],
                name='Volume',
                marker=dict(color='rgba(158,202,225,0.6)')
            )
            fig.add_trace(volume_bars, row=2, col=1)

        # Layout ayarları
        fig.update_layout(
            title=f'{symbol} {period.title()} Interactive Chart - Alpha Vantage Data',
            template='plotly_white',
            height=600 if (show_volume and 'Volume' in df.columns) else 400,
            showlegend=True,
            xaxis_title='Date',
            yaxis_title='Price (USD)',
            hovermode='x unified'
        )

        # Range selector ekle
        fig.update_xaxes(
            rangeslider_visible=False,
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(step="all")
                ])
            )
        )

        # HTML olarak döndür
        chart_html = fig.to_html(
            include_plotlyjs='cdn',
            div_id=f"chart_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            config={'displayModeBar': True, 'responsive': True}
        )

        # Store chart HTML separately and get chart ID
        chart_id = chart_storage.store_chart(
            chart_html=chart_html,
            chart_type='interactive',
            symbol=symbol
        )

        # İstatistikler
        latest_price = float(df['Close'].iloc[-1])
        prev_price = float(df['Close'].iloc[-2]) if len(df) > 1 else latest_price
        change = latest_price - prev_price
        change_pct = (change / prev_price) * 100 if prev_price != 0 else 0

        stats = {
            "symbol": symbol,
            "latest_price": latest_price,
            "daily_change": change,
            "daily_change_pct": change_pct,
            "high_52w": float(df['High'].max()),
            "low_52w": float(df['Low'].min()),
            "period": period,
            "chart_type": chart_type,
            "data_points": len(df)
        }

        return {
            "success": True,
            "chart_id": chart_id,
            "stats": stats,
            "message": f"✅ {symbol} için {chart_type} grafiği başarıyla oluşturuldu ({len(df)} veri noktası)"
        }

    except Exception as e:
        return {"error": f"Grafik oluşturma hatası: {str(e)}"}


@mcp.tool()
async def create_comparison_chart(
        symbols: list,
        period: str = "daily",
        normalize: bool = True,
        outputsize: str = "compact"
):
    """
    Creates a comparison chart for multiple stocks.

    Required:
        symbols (list): List of stock symbols (e.g., ["AAPL", "GOOGL", "MSFT"])

    Optional:
        period (str): "daily" | "weekly" | "monthly"
        normalize (bool): Normalize prices as percentage change
        outputsize (str): "compact" | "full"

    Returns:
        dict: Comparison chart HTML and operation result
    """

    try:
        if len(symbols) > 5:
            return {"error": "En fazla 5 hisse senedi karşılaştırılabilir"}

        all_data = {}
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

        # Her sembol için veri çek
        for i, symbol in enumerate(symbols):
            if period.lower() == "daily":
                data_response = await get_daily_data(symbol=symbol, outputsize=outputsize)
            elif period.lower() == "weekly":
                data_response = await get_weekly_data(symbol=symbol)
            elif period.lower() == "monthly":
                data_response = await get_monthly_data(symbol=symbol)
            else:
                return {"error": f"Desteklenmeyen period: {period}"}

            if "error" in data_response or "Error Message" in data_response:
                continue

            # Veriyi işle
            time_series_key = None
            for key in data_response.keys():
                if "Time Series" in key:
                    time_series_key = key
                    break

            if time_series_key:
                raw_data = data_response[time_series_key]
                df = pd.DataFrame.from_dict(raw_data, orient='index')
                df.index = pd.to_datetime(df.index)
                df.columns = ['Open', 'High', 'Low', 'Close', 'Volume'][:len(df.columns)]
                df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
                df = df.sort_index().tail(252)  # Son 1 yıl

                all_data[symbol] = {
                    'data': df['Close'],
                    'color': colors[i % len(colors)]
                }

        if not all_data:
            return {"error": "Hiçbir sembol için veri alınamadı"}

        # Grafik oluştur
        fig = go.Figure()

        for symbol, info in all_data.items():
            data_series = info['data']

            if normalize:
                # İlk değere göre yüzde değişim
                data_series = ((data_series / data_series.iloc[0]) - 1) * 100

            fig.add_trace(go.Scatter(
                x=data_series.index,
                y=data_series,
                mode='lines',
                name=symbol,
                line=dict(color=info['color'], width=2)
            ))

        fig.update_layout(
            title=f'Stock Comparison - {", ".join(symbols)} ({period.title()})',
            template='plotly_white',
            height=500,
            xaxis_title='Date',
            yaxis_title='Normalized Price Change (%)' if normalize else 'Price (USD)',
            hovermode='x unified',
            showlegend=True
        )

        chart_html = fig.to_html(
            include_plotlyjs='cdn',
            div_id=f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            config={'displayModeBar': True, 'responsive': True}
        )

        # Store chart HTML separately and get chart ID
        chart_id = chart_storage.store_chart(
            chart_html=chart_html,
            chart_type='comparison',
            symbols=list(all_data.keys())
        )

        return {
            "success": True,
            "chart_id": chart_id,
            "symbols_processed": list(all_data.keys()),
            "message": f"✅ {len(all_data)} hisse senedi karşılaştırma grafiği oluşturuldu"
        }

    except Exception as e:
        return {"error": f"Karşılaştırma grafiği hatası: {str(e)}"}


if __name__ == "__main__":
    mcp.run(transport='stdio')
