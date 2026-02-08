import os
from io import BytesIO
from typing import Optional

import matplotlib.pyplot as plt
from matplotlib.transforms import blended_transform_factory
import mplfinance as mpf
import pandas as pd
import numpy as np

try:
    from signal_monitor.logger import logger
except Exception:
    from logger import logger

try:
    from signal_monitor.metals_data_sources import fetch_metals_klines
except Exception:
    from metals_data_sources import fetch_metals_klines  # type: ignore[import-not-found]


def _normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    rename_map = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
        "timestamp": "Date",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    if "Date" in df.columns:
        df = df.set_index("Date")
    for col in ("Open", "High", "Low", "Close", "Volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    if not df.empty:
        df = df.sort_index()
    return df


def _build_style():
    up = "#26A69A"
    down = "#EF5350"
    grid = "#2A2E39"
    face = "#131722"
    edge = "#888888"
    mc = mpf.make_marketcolors(
        up=up,
        down=down,
        edge=edge,
        wick=edge,
        volume=down,
        inherit=True,
    )
    return mpf.make_mpf_style(
        base_mpf_style="nightclouds",
        marketcolors=mc,
        facecolor=face,
        figcolor=face,
        gridcolor=grid,
        gridstyle="-",
        rc={
            "axes.edgecolor": grid,
            "axes.labelcolor": "#E0E0E0",
            "xtick.color": "#C7C7C7",
            "ytick.color": "#C7C7C7",
            "font.size": 9,
        },
    )


def _build_addplots(df: pd.DataFrame):
    addplots = []
    close = df["Close"]
    ema_fast = close.ewm(span=21, adjust=False).mean()
    ema_slow = close.ewm(span=50, adjust=False).mean()
    addplots.append(mpf.make_addplot(ema_fast, color="#4DD0E1", width=1.0))
    addplots.append(mpf.make_addplot(ema_slow, color="#FFD54F", width=1.0))
    if "Volume" in df.columns:
        typical = (df["High"] + df["Low"] + df["Close"]) / 3.0
        vwap = (typical * df["Volume"]).cumsum() / df["Volume"].replace(0, np.nan).cumsum()
        addplots.append(mpf.make_addplot(vwap, color="#B388FF", width=0.9))
    return addplots


def _apply_axis_style(ax, label: str) -> None:
    ax.set_facecolor("#131722")
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")
    ax.set_ylabel(label, color="#C7C7C7", fontsize=9)
    ax.tick_params(axis="y", colors="#C7C7C7")
    ax.tick_params(axis="x", colors="#C7C7C7")
    ax.grid(True, color="#2A2E39", linewidth=0.6, alpha=0.9)


def _add_last_price_marker(ax, df: pd.DataFrame) -> None:
    if df.empty:
        return
    last_close = float(df["Close"].iloc[-1])
    prev_close = float(df["Close"].iloc[-2]) if len(df) > 1 else last_close
    delta = last_close - prev_close
    pct = (delta / prev_close * 100.0) if prev_close else 0.0
    color = "#26A69A" if delta >= 0 else "#EF5350"
    ax.axhline(last_close, color=color, linewidth=1.0, alpha=0.8)
    transform = blended_transform_factory(ax.transAxes, ax.transData)
    ax.text(
        1.005,
        last_close,
        f"{last_close:,.2f}",
        transform=transform,
        ha="left",
        va="center",
        color="#0B0F14",
        fontsize=8,
        bbox={
            "boxstyle": "round,pad=0.25",
            "facecolor": color,
            "edgecolor": color,
        },
        clip_on=False,
    )
    return pct


def generate_metals_chart(
    symbol: str,
    interval: str = "1h",
    limit: int = 200,
    save_to_file: bool = False,
    output_path: Optional[str] = None,
) -> Optional[bytes]:
    interval = (os.getenv("NOFX_METALS_CHART_INTERVAL") or interval).strip()
    df = fetch_metals_klines(symbol, interval=interval, limit=limit, force_refresh=True)
    if df is None or df.empty:
        logger.warning("Metals chart skipped: missing klines for %s", symbol)
        return None
    df = _normalize_ohlc(df)
    df = df.tail(limit)
    if df.empty:
        return None
    df = df.sort_index()
    style = _build_style()
    addplots = _build_addplots(df)
    plot_kwargs = {
        "show_nontrading": False,
        "tight_layout": True,
    }
    if len(df.index) > 1:
        plot_kwargs["xlim"] = (df.index[0], df.index[-1])
    fig, axes = mpf.plot(
        df,
        type="candle",
        style=style,
        volume=True,
        addplot=addplots,
        panel_ratios=(3, 1),
        returnfig=True,
        title="",
        figratio=(16, 9),
        figscale=float(os.getenv("NOFX_METALS_CHART_FIGSCALE", "1.1") or 1.1),
        datetime_format="%b %d %H:%M",
        **plot_kwargs,
    )
    if axes:
        ax = axes[0]
        _apply_axis_style(ax, "Price")
        pct = _add_last_price_marker(ax, df)
        last = df.iloc[-1]
        title = f"{symbol.upper()} · {interval} · {last['Close']:,.2f} ({pct:+.2f}%)"
        ax.set_title(title, color="#EAECEF", fontsize=12, fontweight="bold", pad=12)
        ohlc_line = (
            f"O {last['Open']:,.2f}  H {last['High']:,.2f}  "
            f"L {last['Low']:,.2f}  C {last['Close']:,.2f}"
        )
        ax.text(
            0.01,
            0.98,
            ohlc_line,
            transform=ax.transAxes,
            ha="left",
            va="top",
            color="#9AA0A6",
            fontsize=9,
        )
        if len(axes) > 2:
            _apply_axis_style(axes[2], "Volume")
        fig.text(
            0.01,
            0.02,
            "ValueScan • Binance Klines",
            color="#8A8F98",
            fontsize=8,
        )
    buf = BytesIO()
    dpi = int(os.getenv("NOFX_METALS_CHART_DPI", "180") or 180)
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    image_data = buf.getvalue()
    buf.close()
    if save_to_file and output_path:
        try:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(image_data)
            logger.info("Metals chart saved: %s", output_path)
        except Exception as exc:
            logger.warning("Metals chart save failed: %s", exc)
    return image_data


def generate_metals_chart_async(symbol: str, callback=None, **kwargs) -> str:
    try:
        from concurrent.futures import ThreadPoolExecutor
        import threading
        import time
    except Exception:
        chart_data = generate_metals_chart(symbol, **kwargs)
        if callback and callable(callback):
            callback("metals_sync", symbol, chart_data)
        return "metals_sync"

    if not hasattr(generate_metals_chart_async, "_executor"):
        max_workers = int(os.getenv("NOFX_METALS_CHART_WORKERS", "2") or 2)
        generate_metals_chart_async._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="MetalsChartGen",
        )
        generate_metals_chart_async._tasks = {}
        generate_metals_chart_async._lock = threading.Lock()

    executor = generate_metals_chart_async._executor
    tasks = generate_metals_chart_async._tasks
    lock = generate_metals_chart_async._lock

    with lock:
        task_id = f"metals_chart_{int(time.time())}"
        tasks[task_id] = {"status": "processing", "symbol": symbol, "timestamp": time.time()}

    def _worker():
        chart_data = generate_metals_chart(symbol, **kwargs)
        with lock:
            tasks[task_id]["status"] = "completed" if chart_data else "failed"
            tasks[task_id]["result"] = chart_data
        if callback and callable(callback):
            try:
                callback(task_id, symbol, chart_data)
            except Exception as exc:
                logger.warning("Metals chart callback failed: %s", exc)

    executor.submit(_worker)
    return task_id
