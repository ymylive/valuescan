"""
AI Trading Performance Tracker
追踪 AI 交易性能，为自我进化提供数据基础
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging


class AIPerformanceTracker:
    """
    AI 交易性能追踪器

    记录每笔 AI 交易的详细信息，包括：
    - 入场/出场价格和时间
    - AI 分析和信心度
    - 实际盈亏
    - 市场条件
    - 决策过程
    """

    def __init__(self, db_path: str = "data/ai_performance.db"):
        """
        初始化性能追踪器

        Args:
            db_path: SQLite 数据库路径
        """
        self.logger = logging.getLogger(__name__)
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # AI 交易记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,

                    -- 入场信息
                    entry_time INTEGER NOT NULL,
                    entry_price REAL NOT NULL,
                    entry_quantity REAL NOT NULL,

                    -- AI 分析
                    ai_analysis TEXT,
                    ai_confidence REAL,
                    ai_stop_loss REAL,
                    ai_take_profit REAL,
                    ai_risk_level TEXT,

                    -- 出场信息
                    exit_time INTEGER,
                    exit_price REAL,
                    exit_quantity REAL,
                    exit_reason TEXT,

                    -- 盈亏
                    realized_pnl REAL,
                    realized_pnl_percent REAL,

                    -- 市场条件
                    market_conditions TEXT,

                    -- 状态
                    status TEXT DEFAULT 'open',

                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)

            # AI 仓位调整记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_position_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT NOT NULL,
                    action_time INTEGER NOT NULL,
                    action_type TEXT NOT NULL,

                    -- AI 决策
                    ai_reason TEXT,
                    ai_confidence REAL,

                    -- 执行结果
                    quantity_before REAL,
                    quantity_after REAL,
                    price REAL,

                    -- 市场条件
                    market_conditions TEXT,

                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    FOREIGN KEY (trade_id) REFERENCES ai_trades(trade_id)
                )
            """)

            # AI 学习记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_learning_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    start_time INTEGER NOT NULL,
                    end_time INTEGER,

                    -- 学习数据
                    trades_analyzed INTEGER,
                    patterns_discovered TEXT,
                    insights TEXT,

                    -- 优化结果
                    old_parameters TEXT,
                    new_parameters TEXT,
                    expected_improvement REAL,

                    -- 验证结果
                    actual_improvement REAL,
                    validation_period_days INTEGER,

                    status TEXT DEFAULT 'pending',
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)

            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_symbol
                ON ai_trades(symbol)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_status
                ON ai_trades(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_entry_time
                ON ai_trades(entry_time)
            """)

            conn.commit()
            self.logger.info("AI Performance database initialized: %s", self.db_path)

    def record_trade_entry(
        self,
        trade_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        quantity: float,
        ai_analysis: str,
        ai_confidence: float,
        ai_stop_loss: float,
        ai_take_profit: float,
        ai_risk_level: str,
        market_conditions: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        记录 AI 交易入场

        Args:
            trade_id: 交易 ID
            symbol: 币种符号
            direction: 交易方向 (LONG/SHORT)
            entry_price: 入场价格
            quantity: 数量
            ai_analysis: AI 分析文本
            ai_confidence: AI 信心度
            ai_stop_loss: AI 止损价格
            ai_take_profit: AI 止盈价格
            ai_risk_level: AI 风险等级
            market_conditions: 市场条件

        Returns:
            bool: 是否成功记录
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ai_trades (
                        trade_id, symbol, direction,
                        entry_time, entry_price, entry_quantity,
                        ai_analysis, ai_confidence, ai_stop_loss, ai_take_profit, ai_risk_level,
                        market_conditions, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
                """, (
                    trade_id,
                    symbol,
                    direction,
                    int(time.time()),
                    entry_price,
                    quantity,
                    ai_analysis,
                    ai_confidence,
                    ai_stop_loss,
                    ai_take_profit,
                    ai_risk_level,
                    json.dumps(market_conditions) if market_conditions else None,
                ))
                conn.commit()

            self.logger.info(
                "Recorded AI trade entry: %s %s @ %.4f (confidence=%.2f)",
                direction,
                symbol,
                entry_price,
                ai_confidence,
            )
            return True

        except Exception as e:
            self.logger.error("Failed to record trade entry: %s", e)
            return False

    def record_trade_exit(
        self,
        trade_id: str,
        exit_price: float,
        quantity: float,
        exit_reason: str,
        market_conditions: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        记录 AI 交易出场

        Args:
            trade_id: 交易 ID
            exit_price: 出场价格
            quantity: 数量
            exit_reason: 出场原因
            market_conditions: 市场条件

        Returns:
            bool: 是否成功记录
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 获取入场信息
                cursor.execute("""
                    SELECT entry_price, entry_quantity, direction
                    FROM ai_trades
                    WHERE trade_id = ?
                """, (trade_id,))
                row = cursor.fetchone()

                if not row:
                    self.logger.warning("Trade not found: %s", trade_id)
                    return False

                entry_price, entry_quantity, direction = row

                # 计算盈亏
                if direction == "LONG":
                    pnl = (exit_price - entry_price) * quantity
                    pnl_percent = ((exit_price - entry_price) / entry_price) * 100
                else:  # SHORT
                    pnl = (entry_price - exit_price) * quantity
                    pnl_percent = ((entry_price - exit_price) / entry_price) * 100

                # 更新交易记录
                cursor.execute("""
                    UPDATE ai_trades
                    SET exit_time = ?,
                        exit_price = ?,
                        exit_quantity = ?,
                        exit_reason = ?,
                        realized_pnl = ?,
                        realized_pnl_percent = ?,
                        status = 'closed'
                    WHERE trade_id = ?
                """, (
                    int(time.time()),
                    exit_price,
                    quantity,
                    exit_reason,
                    pnl,
                    pnl_percent,
                    trade_id,
                ))
                conn.commit()

            self.logger.info(
                "Recorded AI trade exit: %s PnL=%.2f (%.2f%%)",
                trade_id,
                pnl,
                pnl_percent,
            )
            return True

        except Exception as e:
            self.logger.error("Failed to record trade exit: %s", e)
            return False

    def record_position_action(
        self,
        trade_id: str,
        action_type: str,
        ai_reason: str,
        ai_confidence: float,
        quantity_before: float,
        quantity_after: float,
        price: float,
        market_conditions: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        记录 AI 仓位调整动作

        Args:
            trade_id: 交易 ID
            action_type: 动作类型 (hold/add/reduce/close)
            ai_reason: AI 原因
            ai_confidence: AI 信心度
            quantity_before: 调整前数量
            quantity_after: 调整后数量
            price: 执行价格
            market_conditions: 市场条件

        Returns:
            bool: 是否成功记录
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ai_position_actions (
                        trade_id, action_time, action_type,
                        ai_reason, ai_confidence,
                        quantity_before, quantity_after, price,
                        market_conditions
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_id,
                    int(time.time()),
                    action_type,
                    ai_reason,
                    ai_confidence,
                    quantity_before,
                    quantity_after,
                    price,
                    json.dumps(market_conditions) if market_conditions else None,
                ))
                conn.commit()

            self.logger.info(
                "Recorded AI position action: %s %s (%.4f → %.4f)",
                trade_id,
                action_type,
                quantity_before,
                quantity_after,
            )
            return True

        except Exception as e:
            self.logger.error("Failed to record position action: %s", e)
            return False

    def get_performance_stats(
        self,
        days: int = 30,
        symbol: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取性能统计

        Args:
            days: 统计天数
            symbol: 币种符号（可选）

        Returns:
            Dict: 性能统计数据
        """
        try:
            cutoff_time = int((datetime.now() - timedelta(days=days)).timestamp())

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 基础查询条件
                where_clause = "WHERE entry_time >= ?"
                params = [cutoff_time]

                if symbol:
                    where_clause += " AND symbol = ?"
                    params.append(symbol)

                # 总体统计
                cursor.execute(f"""
                    SELECT
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_trades,
                        SUM(CASE WHEN status = 'closed' AND realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(CASE WHEN status = 'closed' AND realized_pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                        SUM(CASE WHEN status = 'closed' THEN realized_pnl ELSE 0 END) as total_pnl,
                        AVG(CASE WHEN status = 'closed' THEN realized_pnl_percent ELSE NULL END) as avg_pnl_percent,
                        AVG(ai_confidence) as avg_confidence
                    FROM ai_trades
                    {where_clause}
                """, params)

                row = cursor.fetchone()
                if not row:
                    return {}

                total_trades, closed_trades, winning_trades, losing_trades, total_pnl, avg_pnl_percent, avg_confidence = row

                win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0

                # 按方向统计
                cursor.execute(f"""
                    SELECT
                        direction,
                        COUNT(*) as count,
                        SUM(CASE WHEN status = 'closed' THEN realized_pnl ELSE 0 END) as pnl
                    FROM ai_trades
                    {where_clause}
                    GROUP BY direction
                """, params)

                direction_stats = {row[0]: {"count": row[1], "pnl": row[2]} for row in cursor.fetchall()}

                # 按币种统计（Top 10）
                cursor.execute(f"""
                    SELECT
                        symbol,
                        COUNT(*) as count,
                        SUM(CASE WHEN status = 'closed' THEN realized_pnl ELSE 0 END) as pnl,
                        AVG(CASE WHEN status = 'closed' THEN realized_pnl_percent ELSE NULL END) as avg_pnl_percent
                    FROM ai_trades
                    {where_clause}
                    GROUP BY symbol
                    ORDER BY pnl DESC
                    LIMIT 10
                """, params)

                symbol_stats = [
                    {
                        "symbol": row[0],
                        "count": row[1],
                        "pnl": row[2],
                        "avg_pnl_percent": row[3],
                    }
                    for row in cursor.fetchall()
                ]

                return {
                    "period_days": days,
                    "total_trades": total_trades,
                    "closed_trades": closed_trades,
                    "open_trades": total_trades - closed_trades,
                    "winning_trades": winning_trades,
                    "losing_trades": losing_trades,
                    "win_rate": win_rate,
                    "total_pnl": total_pnl,
                    "avg_pnl_percent": avg_pnl_percent,
                    "avg_confidence": avg_confidence,
                    "direction_stats": direction_stats,
                    "top_symbols": symbol_stats,
                }

        except Exception as e:
            self.logger.error("Failed to get performance stats: %s", e)
            return {}

    def get_trades_for_learning(
        self,
        min_trades: int = 50,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        获取用于学习的交易数据

        Args:
            min_trades: 最少交易数量
            days: 统计天数

        Returns:
            List[Dict]: 交易数据列表
        """
        try:
            cutoff_time = int((datetime.now() - timedelta(days=days)).timestamp())

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT
                        trade_id, symbol, direction,
                        entry_time, entry_price, entry_quantity,
                        ai_analysis, ai_confidence, ai_stop_loss, ai_take_profit, ai_risk_level,
                        exit_time, exit_price, exit_quantity, exit_reason,
                        realized_pnl, realized_pnl_percent,
                        market_conditions, status
                    FROM ai_trades
                    WHERE entry_time >= ? AND status = 'closed'
                    ORDER BY entry_time DESC
                """, (cutoff_time,))

                trades = []
                for row in cursor.fetchall():
                    trades.append({
                        "trade_id": row[0],
                        "symbol": row[1],
                        "direction": row[2],
                        "entry_time": row[3],
                        "entry_price": row[4],
                        "entry_quantity": row[5],
                        "ai_analysis": row[6],
                        "ai_confidence": row[7],
                        "ai_stop_loss": row[8],
                        "ai_take_profit": row[9],
                        "ai_risk_level": row[10],
                        "exit_time": row[11],
                        "exit_price": row[12],
                        "exit_quantity": row[13],
                        "exit_reason": row[14],
                        "realized_pnl": row[15],
                        "realized_pnl_percent": row[16],
                        "market_conditions": json.loads(row[17]) if row[17] else None,
                        "status": row[18],
                    })

                if len(trades) < min_trades:
                    self.logger.warning(
                        "Insufficient trades for learning: %d < %d",
                        len(trades),
                        min_trades,
                    )
                    return []

                return trades

        except Exception as e:
            self.logger.error("Failed to get trades for learning: %s", e)
            return []


if __name__ == "__main__":
    # 测试
    import logging

    logging.basicConfig(level=logging.INFO)

    print("AI Performance Tracker 测试")
    print("=" * 60)

    tracker = AIPerformanceTracker("data/test_ai_performance.db")

    # 测试记录交易
    trade_id = f"test_{int(time.time())}"
    tracker.record_trade_entry(
        trade_id=trade_id,
        symbol="BTC",
        direction="LONG",
        entry_price=48000,
        quantity=0.1,
        ai_analysis="强烈看涨信号",
        ai_confidence=0.85,
        ai_stop_loss=47000,
        ai_take_profit=50000,
        ai_risk_level="low",
        market_conditions={"volume_24h": 1000000, "trend": "bullish"},
    )

    # 测试记录仓位调整
    tracker.record_position_action(
        trade_id=trade_id,
        action_type="add",
        ai_reason="趋势延续，加仓",
        ai_confidence=0.8,
        quantity_before=0.1,
        quantity_after=0.15,
        price=48500,
    )

    # 测试记录出场
    tracker.record_trade_exit(
        trade_id=trade_id,
        exit_price=49500,
        quantity=0.15,
        exit_reason="止盈",
    )

    # 测试获取统计
    stats = tracker.get_performance_stats(days=30)
    print("\n性能统计:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
