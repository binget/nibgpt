import os

import MetaTrader5 as mt5

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy import text


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

SYMBOL = "XAUUSDm"

DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:"
    f"{os.getenv('DB_PORT')}/"
    f"{os.getenv('DB_NAME')}"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="XAUUSD AI Dashboard API",
    version="11.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HEALTH
# ============================================================

@app.get("/")
def root():

    return {
        "status": "online",
        "system": "XAUUSD AI",
        "version": "V11",
        "mode": "PAPER TRADING"
    }


# ============================================================
# LIVE MARKET
# ============================================================

@app.get("/api/market")
def market():

    if not mt5.initialize():

        return {
            "status": "error",
            "message": str(
                mt5.last_error()
            )
        }

    try:

        tick = mt5.symbol_info_tick(
            SYMBOL
        )

        info = mt5.symbol_info(
            SYMBOL
        )

        if tick is None or info is None:

            return {
                "status": "error",
                "message":
                    "Unable to retrieve XAUUSD market data"
            }

        bid = float(tick.bid)
        ask = float(tick.ask)

        return {
            "status": "online",
            "symbol": SYMBOL,
            "bid": bid,
            "ask": ask,
            "spread": ask - bid,
            "digits": info.digits
        }

    finally:

        mt5.shutdown()

@app.get("/api/market/candles")
def market_candles(
    timeframe: str = "M1",
    limit: int = 200
):

    timeframe_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "H1": mt5.TIMEFRAME_H1,
    }

    timeframe = timeframe.upper()

    if timeframe not in timeframe_map:
        return {
            "status": "error",
            "message": "Invalid timeframe",
            "candles": []
        }

    if limit < 10:
        limit = 10

    if limit > 500:
        limit = 500

    if not mt5.initialize():
        return {
            "status": "error",
            "message": str(mt5.last_error()),
            "candles": []
        }

    try:

        rates = mt5.copy_rates_from_pos(
            SYMBOL,
            timeframe_map[timeframe],
            0,
            limit
        )

        if rates is None or len(rates) == 0:
            return {
                "status": "error",
                "message": "No candle data returned",
                "candles": []
            }

        candles = []

        for rate in rates:

            candles.append({
                "time":
                    int(rate["time"]),

                "open":
                    float(rate["open"]),

                "high":
                    float(rate["high"]),

                "low":
                    float(rate["low"]),

                "close":
                    float(rate["close"]),

                "volume":
                    int(rate["tick_volume"]),

                "spread":
                    int(rate["spread"]) * 0.001
            })

        return {
            "status": "online",
            "symbol": SYMBOL,
            "timeframe": timeframe,
            "candles": candles
        }

    finally:

        mt5.shutdown()

@app.get("/api/trade/open")
def open_trade():

    sql = text(
        """
        SELECT
            id,
            signal_id,
            direction,
            entry_time,
            entry_price,
            stop_loss,
            take_profit,
            exit_time,
            exit_price,
            result,
            pnl,
            duration_minutes,
            status
        FROM xauusd_paper_trades
        WHERE status = 'OPEN'
        ORDER BY entry_time DESC
        LIMIT 1
        """
    )

    with engine.connect() as connection:

        row = connection.execute(
            sql
        ).mappings().first()

    if row is None:

        return {
            "has_open_trade": False,
            "trade": None
        }

    return {
        "has_open_trade": True,
        "trade": dict(row)
    }

# ============================================================
# LATEST SIGNAL
# ============================================================

@app.get("/api/signal/latest")
def latest_signal():

    sql = text(
        """
        SELECT
            id,
            session_date,
            signal_time,
            symbol,
            model_version,
            strategy_version,
            probability,
            threshold,
            decision,
            entry_price,
            stop_loss,
            take_profit,
            spread,
            previous_day_move,
            five_day_move,
            weekend_gap,
            first30_move,
            return_5m,
            return_30m,
            rsi,
            atr,
            status
        FROM xauusd_live_signals
        ORDER BY id DESC
        LIMIT 1
        """
    )

    with engine.connect() as connection:

        row = connection.execute(
            sql
        ).mappings().first()

    if row is None:

        return {
            "signal": None
        }

    return {
        "signal": dict(row)
    }


# ============================================================
# SIGNAL HISTORY
# ============================================================

@app.get("/api/signals")
def signals():

    sql = text(
        """
        SELECT
            id,
            session_date,
            signal_time,
            probability,
            threshold,
            decision,
            entry_price,
            stop_loss,
            take_profit,
            spread,
            status
        FROM xauusd_live_signals
        ORDER BY id DESC
        LIMIT 100
        """
    )

    with engine.connect() as connection:

        rows = connection.execute(
            sql
        ).mappings().all()

    return {
        "signals": [
            dict(row)
            for row in rows
        ]
    }


# ============================================================
# PAPER TRADING ANALYTICS
# ============================================================

@app.get("/api/analytics/paper")
def paper_analytics():

    sql = text(
        """
        SELECT
            id,
            signal_id,
            direction,
            entry_time,
            entry_price,
            stop_loss,
            take_profit,
            exit_time,
            exit_price,
            result,
            pnl,
            duration_minutes,
            status
        FROM xauusd_paper_trades
        WHERE status = 'CLOSED'
        ORDER BY entry_time ASC
        """
    )

    with engine.connect() as connection:
        rows = connection.execute(sql).mappings().all()

    trades = [dict(row) for row in rows]

    # --------------------------------------------------------
    # NO CLOSED PAPER TRADES YET
    # --------------------------------------------------------

    if not trades:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "timeouts": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "average_pnl": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "max_losing_streak": 0,
            "average_duration": 0.0,
            "equity": []
        }

    # --------------------------------------------------------
    # P/L VALUES
    # --------------------------------------------------------

    pnl_values = [
        float(trade["pnl"] or 0)
        for trade in trades
    ]

    total_trades = len(pnl_values)

    # --------------------------------------------------------
    # WIN / LOSS / TIMEOUT COUNTS
    # --------------------------------------------------------

    wins = sum(
        1
        for value in pnl_values
        if value > 0
    )

    losses = sum(
        1
        for value in pnl_values
        if value < 0
    )

    timeouts = sum(
        1
        for trade in trades
        if str(trade["result"] or "").upper() == "TIMEOUT"
    )

    # --------------------------------------------------------
    # GROSS PROFIT / LOSS
    # --------------------------------------------------------

    gross_profit = sum(
        value
        for value in pnl_values
        if value > 0
    )

    gross_loss = abs(
        sum(
            value
            for value in pnl_values
            if value < 0
        )
    )

    # --------------------------------------------------------
    # PROFIT FACTOR
    # --------------------------------------------------------

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = 0.0

    # --------------------------------------------------------
    # TOTAL / AVERAGE P&L
    # --------------------------------------------------------

    total_pnl = sum(pnl_values)

    if total_trades > 0:
        average_pnl = total_pnl / total_trades
    else:
        average_pnl = 0.0

    # --------------------------------------------------------
    # WIN RATE
    # --------------------------------------------------------

    if total_trades > 0:
        win_rate = (wins / total_trades) * 100
    else:
        win_rate = 0.0

    # ========================================================
    # EQUITY CURVE
    # ========================================================

    equity_curve = []

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0

    for index, trade in enumerate(trades):

        pnl = float(
            trade["pnl"] or 0
        )

        equity += pnl

        if equity > peak:
            peak = equity

        drawdown = equity - peak

        if drawdown < max_drawdown:
            max_drawdown = drawdown

        exit_time = trade["exit_time"]

        if exit_time is not None:
            try:
                exit_time_value = exit_time.isoformat()
            except AttributeError:
                exit_time_value = str(exit_time)
        else:
            exit_time_value = None

        equity_curve.append(
            {
                "trade": index + 1,
                "time": exit_time_value,
                "pnl": round(pnl, 6),
                "equity": round(equity, 6),
                "drawdown": round(drawdown, 6)
            }
        )

    # ========================================================
    # MAXIMUM LOSING STREAK
    # ========================================================

    max_losing_streak = 0
    current_losing_streak = 0

    for pnl in pnl_values:

        if pnl < 0:

            current_losing_streak += 1

            if current_losing_streak > max_losing_streak:
                max_losing_streak = current_losing_streak

        else:

            current_losing_streak = 0

    # ========================================================
    # AVERAGE TRADE DURATION
    # ========================================================

    durations = []

    for trade in trades:

        duration = trade["duration_minutes"]

        if duration is not None:

            try:
                durations.append(
                    float(duration)
                )
            except (TypeError, ValueError):
                pass

    if durations:
        average_duration = (
            sum(durations) /
            len(durations)
        )
    else:
        average_duration = 0.0

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "trades": total_trades,
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "win_rate": round(win_rate, 4),
        "total_pnl": round(total_pnl, 6),
        "average_pnl": round(average_pnl, 6),
        "profit_factor": round(profit_factor, 6),
        "max_drawdown": round(max_drawdown, 6),
        "max_losing_streak": max_losing_streak,
        "average_duration": round(average_duration, 2),
        "equity": equity_curve
    }


# ============================================================
# AI PROBABILITY VS ACTUAL PAPER-TRADE RESULT
# ============================================================

@app.get("/api/analytics/probability")
def probability_analysis():

    sql = text(
        """
        SELECT
            s.id,
            s.session_date,
            s.signal_time,
            s.probability,
            s.decision,
            t.result,
            t.pnl,
            t.entry_time,
            t.exit_time
        FROM xauusd_live_signals s

        INNER JOIN xauusd_paper_trades t
            ON t.signal_id = s.id

        WHERE
            s.decision = 'PAPER_SELL'
            AND t.status = 'CLOSED'

        ORDER BY s.signal_time ASC
        """
    )

    with engine.connect() as connection:
        rows = connection.execute(sql).mappings().all()

    records = []

    for row in rows:

        probability = float(
            row["probability"] or 0
        )

        session_date = row["session_date"]

        if session_date is not None:
            try:
                session_date_value = session_date.isoformat()
            except AttributeError:
                session_date_value = str(session_date)
        else:
            session_date_value = None

        signal_time = row["signal_time"]

        if signal_time is not None:
            try:
                signal_time_value = signal_time.isoformat()
            except AttributeError:
                signal_time_value = str(signal_time)
        else:
            signal_time_value = None

        entry_time = row["entry_time"]

        if entry_time is not None:
            try:
                entry_time_value = entry_time.isoformat()
            except AttributeError:
                entry_time_value = str(entry_time)
        else:
            entry_time_value = None

        exit_time = row["exit_time"]

        if exit_time is not None:
            try:
                exit_time_value = exit_time.isoformat()
            except AttributeError:
                exit_time_value = str(exit_time)
        else:
            exit_time_value = None

        records.append(
            {
                "id": row["id"],
                "session_date": session_date_value,
                "signal_time": signal_time_value,
                "probability": probability,
                "probability_pct": round(
                    probability * 100,
                    2
                ),
                "decision": row["decision"],
                "result": row["result"],
                "pnl": float(
                    row["pnl"] or 0
                ),
                "entry_time": entry_time_value,
                "exit_time": exit_time_value
            }
        )

    return {
        "count": len(records),
        "records": records
    }


@app.get("/api/analytics/probability")
def probability_analysis():

    sql = text(
        """
        SELECT
            s.id,
            s.session_date,
            s.probability,
            s.decision,
            t.result,
            t.pnl
        FROM xauusd_live_signals s

        LEFT JOIN xauusd_paper_trades t
            ON t.signal_id = s.id

        WHERE
            s.decision = 'PAPER_SELL'
            AND t.status = 'CLOSED'

        ORDER BY s.signal_time ASC
        """
    )

    with engine.connect() as connection:

        rows = connection.execute(
            sql
        ).mappings().all()

    return {
        "records": [
            {
                "id": row["id"],
                "session_date": row["session_date"],
                "probability": float(
                    row["probability"] or 0
                ),
                "probability_pct": float(
                    row["probability"] or 0
                ) * 100,
                "result": row["result"],
                "pnl": float(
                    row["pnl"] or 0
                )
            }
            for row in rows
        ]
    }

@app.get("/api/analytics/probability")
def probability_analysis():

    sql = text(
        """
        SELECT
            s.id,
            s.session_date,
            s.probability,
            s.decision,
            t.result,
            t.pnl
        FROM xauusd_live_signals s

        LEFT JOIN xauusd_paper_trades t
            ON t.signal_id = s.id

        WHERE
            s.decision = 'PAPER_SELL'
            AND t.status = 'CLOSED'

        ORDER BY s.signal_time ASC
        """
    )

    with engine.connect() as connection:

        rows = connection.execute(
            sql
        ).mappings().all()

    return {
        "records": [
            {
                "id":
                    row["id"],

                "session_date":
                    row[
                        "session_date"
                    ],

                "probability":
                    float(
                        row[
                            "probability"
                        ] or 0
                    ),

                "probability_pct":
                    float(
                        row[
                            "probability"
                        ] or 0
                    ) * 100,

                "result":
                    row["result"],

                "pnl":
                    float(
                        row["pnl"] or 0
                    )
            }

            for row in rows
        ]
    }

# ============================================================
# PAPER TRADES
# ============================================================

@app.get("/api/trades")
def trades():

    sql = text(
        """
        SELECT
            id,
            signal_id,
            direction,
            entry_time,
            entry_price,
            stop_loss,
            take_profit,
            exit_time,
            exit_price,
            result,
            pnl,
            duration_minutes,
            status
        FROM xauusd_paper_trades
        ORDER BY id DESC
        LIMIT 100
        """
    )

    with engine.connect() as connection:

        rows = connection.execute(
            sql
        ).mappings().all()

    return {
        "trades": [
            dict(row)
            for row in rows
        ]
    }


# ============================================================
# PERFORMANCE
# ============================================================

@app.get("/api/performance")
def performance():

    sql = text(
        """
        SELECT
            COUNT(*) FILTER (
                WHERE status = 'CLOSED'
            ) AS trades,

            COUNT(*) FILTER (
                WHERE result = 'WIN'
            ) AS wins,

            COUNT(*) FILTER (
                WHERE result = 'LOSS'
            ) AS losses,

            COUNT(*) FILTER (
                WHERE result = 'TIMEOUT'
            ) AS timeouts,

            COALESCE(
                SUM(pnl) FILTER (
                    WHERE status = 'CLOSED'
                ),
                0
            ) AS total_pnl,

            COALESCE(
                AVG(pnl) FILTER (
                    WHERE status = 'CLOSED'
                ),
                0
            ) AS average_pnl

        FROM xauusd_paper_trades
        """
    )

    with engine.connect() as connection:

        row = connection.execute(
            sql
        ).mappings().first()

    data = dict(row)

    trades = int(
        data["trades"] or 0
    )

    wins = int(
        data["wins"] or 0
    )

    win_rate = (
        (wins / trades) * 100
        if trades > 0
        else 0
    )

    return {
        "trades": trades,
        "wins": wins,
        "losses": int(
            data["losses"] or 0
        ),
        "timeouts": int(
            data["timeouts"] or 0
        ),
        "win_rate": win_rate,
        "total_pnl": float(
            data["total_pnl"] or 0
        ),
        "average_pnl": float(
            data["average_pnl"] or 0
        )
    }

    # ============================================================
# COMPLETED PAPER TRADE HISTORY
# ============================================================

@app.get("/api/paper-trades/history")
def paper_trade_history():

    sql = text(
        """
        SELECT
            t.id,
            t.signal_id,
            t.direction,
            t.entry_time,
            t.entry_price,
            t.stop_loss,
            t.take_profit,
            t.exit_time,
            t.exit_price,
            t.result,
            t.pnl,
            t.duration_minutes,
            t.status,

            s.session_date,
            s.signal_time,
            s.probability

        FROM xauusd_paper_trades t

        LEFT JOIN xauusd_live_signals s
            ON s.id = t.signal_id

        WHERE t.status = 'CLOSED'

        ORDER BY t.entry_time DESC
        """
    )

    with engine.connect() as connection:
        rows = connection.execute(sql).mappings().all()

    records = []

    for row in rows:

        # ----------------------------------------------------
        # DATE/TIME CONVERSION
        # ----------------------------------------------------

        def serialize_datetime(value):

            if value is None:
                return None

            try:
                return value.isoformat()
            except AttributeError:
                return str(value)

        # ----------------------------------------------------
        # PROBABILITY
        # ----------------------------------------------------

        probability = float(
            row["probability"] or 0
        )

        # ----------------------------------------------------
        # EXIT REASON
        # ----------------------------------------------------

        result = str(
            row["result"] or ""
        ).upper()

        if result == "WIN":
            exit_reason = "TAKE PROFIT"

        elif result == "LOSS":
            exit_reason = "STOP LOSS"

        elif result == "TIMEOUT":
            exit_reason = "MAX HOLD"

        else:
            exit_reason = result or "UNKNOWN"

        # ----------------------------------------------------
        # RECORD
        # ----------------------------------------------------

        records.append(
            {
                "id": row["id"],

                "signal_id":
                    row["signal_id"],

                "session_date":
                    serialize_datetime(
                        row["session_date"]
                    ),

                "signal_time":
                    serialize_datetime(
                        row["signal_time"]
                    ),

                "probability":
                    probability,

                "probability_pct":
                    round(
                        probability * 100,
                        2
                    ),

                "direction":
                    row["direction"],

                "entry_time":
                    serialize_datetime(
                        row["entry_time"]
                    ),

                "entry_price":
                    float(
                        row["entry_price"] or 0
                    ),

                "stop_loss":
                    float(
                        row["stop_loss"] or 0
                    ),

                "take_profit":
                    float(
                        row["take_profit"] or 0
                    ),

                "exit_time":
                    serialize_datetime(
                        row["exit_time"]
                    ),

                "exit_price":
                    float(
                        row["exit_price"] or 0
                    ),

                "result":
                    result,

                "exit_reason":
                    exit_reason,

                "pnl":
                    float(
                        row["pnl"] or 0
                    ),

                "duration_minutes":
                    float(
                        row["duration_minutes"] or 0
                    ),

                "status":
                    row["status"]
            }
        )

    return {
        "count": len(records),
        "records": records
    }

    # ============================================================
# SYSTEM HEALTH
# ============================================================

from pathlib import Path
from datetime import datetime, timezone


@app.get("/api/system/health")
def system_health():

    health = {
        "overall_status": "HEALTHY",
        "checked_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "mt5": {
            "status": "UNKNOWN",
            "message": None,
            "last_tick_time": None
        },

        "database": {
            "status": "UNKNOWN",
            "message": None
        },

        "model": {
            "status": "UNKNOWN",
            "model_file": None,
            "metadata_file": None
        },

        "signals": {
            "latest_signal_time": None,
            "latest_decision": None,
            "latest_probability": None
        },

        "paper_trading": {
            "open_trades": 0,
            "closed_trades": 0
        },
        "engine": {
            "status": "UNKNOWN",
            "last_seen": None,
            "seconds_since_heartbeat": None,
            "message": None
        },
    }


    # ========================================================
    # DATABASE CHECK
    # ========================================================

    try:

        with engine.connect() as connection:

            connection.execute(
                text("SELECT 1")
            )

        health["database"]["status"] = (
            "HEALTHY"
        )

        health["database"]["message"] = (
            "PostgreSQL connection successful"
        )

    except Exception as e:

        health["database"]["status"] = (
            "OFFLINE"
        )

        health["database"]["message"] = str(e)

        health["overall_status"] = (
            "OFFLINE"
        )


    # ========================================================
    # MODEL FILE CHECK
    # ========================================================

    model_file = Path(
        r"D:\xauusd-ai\models\xauusd_v11_logistic.joblib"
    )

    metadata_file = Path(
        r"D:\xauusd-ai\models\xauusd_v11_model_meta.json"
    )

    health["model"]["model_file"] = str(
        model_file
    )

    health["model"]["metadata_file"] = str(
        metadata_file
    )

    if (
        model_file.exists()
        and
        metadata_file.exists()
    ):

        health["model"]["status"] = (
            "HEALTHY"
        )

    else:

        health["model"]["status"] = (
            "OFFLINE"
        )

        health["overall_status"] = (
            "OFFLINE"
        )


    # ========================================================
    # MT5 CHECK
    # ========================================================

    try:

        if not mt5.initialize():

            health["mt5"]["status"] = (
                "OFFLINE"
            )

            health["mt5"]["message"] = str(
                mt5.last_error()
            )

            if (
                health["overall_status"]
                != "OFFLINE"
            ):
                health["overall_status"] = (
                    "WARNING"
                )

        else:

            tick = mt5.symbol_info_tick(
                SYMBOL
            )

            if tick is None:

                health["mt5"]["status"] = (
                    "WARNING"
                )

                health["mt5"]["message"] = (
                    "MT5 connected but no tick data"
                )

                if (
                    health["overall_status"]
                    == "HEALTHY"
                ):
                    health["overall_status"] = (
                        "WARNING"
                    )

            else:

                tick_time = datetime.fromtimestamp(
                    int(tick.time),
                    tz=timezone.utc
                )

                health["mt5"]["status"] = (
                    "HEALTHY"
                )

                health["mt5"]["message"] = (
                    "MT5 connected"
                )

                health["mt5"][
                    "last_tick_time"
                ] = tick_time.isoformat()

    except Exception as e:

        health["mt5"]["status"] = (
            "OFFLINE"
        )

        health["mt5"]["message"] = str(e)

        if (
            health["overall_status"]
            != "OFFLINE"
        ):
            health["overall_status"] = (
                "WARNING"
            )

    finally:

        try:
            mt5.shutdown()
        except Exception:
            pass


    # ========================================================
    # SIGNAL / PAPER TRADE CHECK
    # ========================================================

    try:

        with engine.connect() as connection:

            latest_signal = connection.execute(
                text(
                    """
                    SELECT
                        signal_time,
                        decision,
                        probability
                    FROM xauusd_live_signals
                    ORDER BY id DESC
                    LIMIT 1
                    """
                )
            ).mappings().first()


            if latest_signal:

                signal_time = (
                    latest_signal[
                        "signal_time"
                    ]
                )

                health["signals"][
                    "latest_signal_time"
                ] = (
                    signal_time.isoformat()
                    if signal_time
                    else None
                )

                health["signals"][
                    "latest_decision"
                ] = latest_signal[
                    "decision"
                ]

                probability = latest_signal[
                    "probability"
                ]

                health["signals"][
                    "latest_probability"
                ] = (
                    float(probability)
                    if probability is not None
                    else None
                )


            open_count = connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM xauusd_paper_trades
                    WHERE status = 'OPEN'
                    """
                )
            ).scalar()


            closed_count = connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM xauusd_paper_trades
                    WHERE status = 'CLOSED'
                    """
                )
            ).scalar()


            health["paper_trading"][
                "open_trades"
            ] = int(
                open_count or 0
            )

            health["paper_trading"][
                "closed_trades"
            ] = int(
                closed_count or 0
            )

    except Exception as e:

        if (
            health["overall_status"]
            == "HEALTHY"
        ):
            health["overall_status"] = (
                "WARNING"
            )

        health["signals"]["error"] = str(e)


# ========================================================
# LIVE ENGINE HEARTBEAT CHECK
# ========================================================

try:

    with engine.connect() as connection:

        heartbeat = connection.execute(
            text(
                """
                SELECT
                    engine_name,
                    last_seen,
                    status,
                    message
                FROM xauusd_engine_heartbeat
                WHERE engine_name = 'XAUUSD_V11'
                LIMIT 1
                """
            )
        ).mappings().first()

if heartbeat is None:

        health["engine"]["status"] = "STOPPED"

        health["engine"]["message"] = (
            "No heartbeat has been recorded"
        )

        if health["overall_status"] == "HEALTHY":
            health["overall_status"] = "WARNING"

else:

        last_seen = heartbeat["last_seen"]

        now_utc = datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )

        seconds_since = (
            now_utc - last_seen
        ).total_seconds()

        health["engine"]["last_seen"] = (
            last_seen.isoformat()
        )

        health["engine"][
            "seconds_since_heartbeat"
        ] = round(
            seconds_since,
            1
        )

        health["engine"]["message"] = (
            heartbeat["message"]
        )

        if seconds_since <= 90:

            health["engine"]["status"] = (
                "RUNNING"
            )

        elif seconds_since <= 180:

            health["engine"]["status"] = (
                "STALE"
            )

            if (
                health["overall_status"]
                == "HEALTHY"
            ):
                health["overall_status"] = (
                    "WARNING"
                )

        else:

            health["engine"]["status"] = (
                "STOPPED"
            )

            if (
                health["overall_status"]
                == "HEALTHY"
            ):
                health["overall_status"] = (
                    "WARNING"
            )

except Exception as e:

health["engine"]["status"] = (
    "UNKNOWN"
)

health["engine"]["message"] = str(e)

if (
    health["overall_status"]
    == "HEALTHY"
):
    health["overall_status"] = (
    "WARNING"
)

return health