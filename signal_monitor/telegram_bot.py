"""
Telegram 机器人命令处理器
处理用户私聊命令，支持交易员评测功能
"""

import re
import asyncio
import threading
import time
import json
import os
from typing import Optional, Dict, Any, Callable, Tuple
from dataclasses import dataclass, field

import requests

try:
    from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
except ImportError:
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


@dataclass
class BotConfig:
    """机器人配置"""
    enabled: bool = True
    allowed_users: list = None  # None = 允许所有用户
    admin_users: list = field(default_factory=list)  # 管理员用户ID列表（不受限时限制）
    rate_limit_seconds: int = 300  # 查询间隔限制（秒），默认5分钟
    cache_ttl: int = 300  # 缓存时间（秒）


class TelegramBotHandler:
    """Telegram 机器人命令处理器"""

    def __init__(self, token: str = None, config: BotConfig = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.config = config or BotConfig()
        self._load_bot_config()  # 加载配置文件
        self.running = False
        self._offset = 0
        self._session = requests.Session()
        self._rate_limiter: Dict[int, float] = {}  # user_id -> last_query_timestamp
        self._commands: Dict[str, Callable] = {}
        self._processed_messages: set = set()  # 已处理的消息ID，防止重复
        self._max_processed_cache = 1000  # 最多缓存1000条
        self._register_commands()

    def _load_bot_config(self):
        """从配置文件加载管理员列表和限时设置"""
        config_path = os.path.join(os.path.dirname(__file__), "bot_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.config.admin_users = cfg.get("admin_users", [])
                    self.config.rate_limit_seconds = cfg.get("rate_limit_seconds", 300)
            except Exception as e:
                print(f"[TelegramBot] Load config error: {e}")

    def _register_commands(self):
        """注册命令处理器"""
        self._commands = {
            "/start": self._cmd_start,
            "/help": self._cmd_help,
            "/trader": self._cmd_trader,
            "/t": self._cmd_trader,  # 简写
            "/analyze": self._cmd_trader,  # 别名
            "/a": self._cmd_trader,  # 简写
        }

    def _is_admin(self, user_id: int) -> bool:
        """检查用户是否为管理员"""
        return self.config.admin_users and user_id in self.config.admin_users

    def _check_rate_limit(self, user_id: int) -> Tuple[bool, int]:
        """检查速率限制
        返回: (是否允许, 剩余等待秒数)
        管理员用户不受限制
        """
        # 管理员用户不受限制
        if self._is_admin(user_id):
            return True, 0

        now = time.time()
        last_query = self._rate_limiter.get(user_id, 0)
        elapsed = now - last_query

        if elapsed < self.config.rate_limit_seconds:
            remaining = int(self.config.rate_limit_seconds - elapsed)
            return False, remaining

        # 更新最后查询时间
        self._rate_limiter[user_id] = now
        return True, 0

    def _check_user_allowed(self, user_id: int) -> bool:
        """检查用户是否被允许"""
        if self.config.allowed_users is None:
            return True
        return user_id in self.config.allowed_users

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json_payload: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
    ) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/{endpoint}"
        try:
            resp = self._session.request(
                method,
                url,
                json=json_payload,
                data=data,
                files=files,
                params=params,
                timeout=timeout,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"[TelegramBot] Request error: {e}")
        return None

    def send_message(self, chat_id: int, text: str, parse_mode: str = "HTML",
                     reply_to: int = None) -> Optional[Dict]:
        """发送消息"""
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_to:
            data["reply_to_message_id"] = reply_to

        result = self._request("POST", "sendMessage", json_payload=data, timeout=30)
        return result.get("result") if result else None

    def send_photo(self, chat_id: int, photo: bytes, caption: str = "",
                   parse_mode: str = "HTML") -> Optional[Dict]:
        """发送图片"""
        data = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": parse_mode,
        }
        files = {"photo": ("chart.png", photo, "image/png")}

        result = self._request("POST", "sendPhoto", data=data, files=files, timeout=60)
        return result.get("result") if result else None

    def edit_message(self, chat_id: int, message_id: int, text: str,
                     parse_mode: str = "HTML") -> Optional[Dict]:
        """编辑消息"""
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        result = self._request("POST", "editMessageText", json_payload=data, timeout=30)
        return result.get("result") if result else None

    def delete_message(self, chat_id: int, message_id: int) -> bool:
        """删除消息"""
        data = {"chat_id": chat_id, "message_id": message_id}

        result = self._request("POST", "deleteMessage", json_payload=data, timeout=30)
        return result is not None

    def get_updates(self, timeout: int = 30) -> list:
        """获取更新"""
        params = {
            "offset": self._offset,
            "timeout": timeout,
            "allowed_updates": ["message"],
        }

        data = self._request("GET", "getUpdates", params=params, timeout=timeout + 10)
        if data and data.get("ok"):
            return data.get("result", [])
        return []

    def handle_update(self, update: Dict):
        """处理单个更新"""
        message = update.get("message")
        if not message:
            return

        # 更新 offset
        update_id = update.get("update_id", 0)
        self._offset = max(self._offset, update_id + 1)

        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        text = message.get("text", "").strip()
        message_id = message.get("message_id")

        if not chat_id or not text:
            return

        # 消息去重：防止重复处理同一消息
        msg_key = f"{chat_id}_{message_id}"
        if msg_key in self._processed_messages:
            return
        self._processed_messages.add(msg_key)
        # 清理过多的缓存
        if len(self._processed_messages) > self._max_processed_cache:
            self._processed_messages = set(list(self._processed_messages)[-500:])

        # 检查权限
        if not self._check_user_allowed(user_id):
            self.send_message(chat_id, "⛔ 您没有使用此机器人的权限。")
            return

        # 处理命令（/start 和 /help 不受限时限制）
        if text.startswith("/"):
            parts = text.split(maxsplit=1)
            cmd = parts[0].lower().split("@")[0]  # 移除 @botname
            args = parts[1] if len(parts) > 1 else ""

            # /start 和 /help 不受限时限制
            if cmd in ["/start", "/help"]:
                if cmd in self._commands:
                    self._commands[cmd](chat_id, message_id, args, message)
                return

            # 其他命令检查速率限制
            if cmd in self._commands:
                allowed, remaining = self._check_rate_limit(user_id)
                if not allowed:
                    self.send_message(
                        chat_id,
                        f"⏳ 请等待 {remaining} 秒后再次查询\n"
                        f"💡 提示：管理员用户无此限制"
                    )
                    return
                self._commands[cmd](chat_id, message_id, args, message)
                return

        # 检查是否是交易员 ID（纯数字或特定格式）- 也需要检查限时
        if self._is_portfolio_id(text):
            allowed, remaining = self._check_rate_limit(user_id)
            if not allowed:
                self.send_message(
                    chat_id,
                    f"⏳ 请等待 {remaining} 秒后再次查询\n"
                    f"💡 提示：管理员用户无此限制"
                )
                return
            self._cmd_trader(chat_id, message_id, text, message)

    def _is_portfolio_id(self, text: str) -> bool:
        """检查是否是有效的交易员 ID"""
        # 币安跟单 ID 通常是数字
        if text.isdigit() and len(text) >= 6:
            return True
        # 也可能是带前缀的格式
        if re.match(r'^[A-Za-z0-9]{10,}$', text):
            return True
        return False

    # ========== 命令处理器 ==========

    def _cmd_start(self, chat_id: int, message_id: int, args: str, message: Dict):
        """处理 /start 命令"""
        text = """
<b>👋 欢迎使用交易员评测机器人</b>

我可以帮你评测币安跟单交易员，分析其交易风格、风险等级和跟随建议。

<b>📋 快捷指令：</b>
/analyze &lt;ID&gt; - 评测交易员
/trader &lt;ID&gt; - 评测交易员
/t &lt;ID&gt; - 快捷评测
/a &lt;ID&gt; - 快捷评测
/help - 查看帮助

<b>💡 使用示例：</b>
<code>/analyze 123456789</code>
<code>/trader 123456789</code>
或直接发送 ID：<code>123456789</code>

<b>📊 评测内容：</b>
• 交易风格分析（激进/稳健/均衡）
• 持仓风格分析（超短线/日内/波段/中长线）
• 风险评估（低/中/高/极高）
• 保证金行为检测（重点！）
• 跟随建议与建议比例

发送 /help 查看详细帮助。
"""
        self.send_message(chat_id, text)

    def _cmd_help(self, chat_id: int, message_id: int, args: str, message: Dict):
        """处理 /help 命令"""
        text = """
<b>📖 使用帮助</b>

<b>📋 快捷指令：</b>
/analyze &lt;ID&gt; - 评测交易员（推荐）
/trader &lt;ID&gt; - 评测交易员
/t &lt;ID&gt; - 快捷评测
/a &lt;ID&gt; - 快捷评测
/start - 开始使用
/help - 显示帮助

<b>💡 使用示例：</b>
<code>/analyze 3958630547737153281</code>
<code>/trader 3958630547737153281</code>
或直接发送 ID：<code>3958630547737153281</code>

<b>🔍 如何获取交易员 ID：</b>
1. 打开币安 App 或网页
2. 进入「跟单交易」
3. 点击交易员主页
4. 从 URL 复制 portfolioId 参数
   例如: ...?portfolioId=<b>3958630547737153281</b>

<b>📊 评测维度：</b>
• 交易风格：激进 / 稳健 / 均衡
• 持仓风格：超短线 / 日内 / 波段 / 中长线
• 风险等级：低 / 中 / 高 / 极高
• 保证金行为：是否频繁添加保证金（重点！）
• 跟随建议：强烈推荐 / 推荐 / 中性 / 警告 / 回避

<b>⚠️ 注意事项：</b>
• 评测结果仅供参考
• 历史表现不代表未来收益
• 请根据自身风险承受能力决策
• 重点关注「保证金行为」指标
"""
        self.send_message(chat_id, text)

    def _cmd_trader(self, chat_id: int, message_id: int, args: str, message: Dict):
        """处理 /trader 命令 - 评测交易员"""
        portfolio_id = args.strip()

        if not portfolio_id:
            self.send_message(chat_id, "❌ 请提供交易员 ID\n用法: /trader <ID>")
            return

        if not self._is_portfolio_id(portfolio_id):
            self.send_message(chat_id, "❌ 无效的交易员 ID 格式")
            return

        # 发送处理中消息
        status_msg = self.send_message(chat_id, f"⏳ 正在分析交易员 {portfolio_id}...")
        status_msg_id = status_msg.get("message_id") if status_msg else None

        try:
            # 执行评测
            result = self._evaluate_trader(portfolio_id)

            if result is None:
                if status_msg_id:
                    self.edit_message(chat_id, status_msg_id,
                                      f"❌ 无法获取交易员 {portfolio_id} 的数据\n请检查 ID 是否正确")
                return

            chart_bytes, caption = result

            # 删除状态消息
            if status_msg_id:
                self.delete_message(chat_id, status_msg_id)

            # 发送结果
            if chart_bytes:
                self.send_photo(chat_id, chart_bytes, caption)
            else:
                self.send_message(chat_id, caption)

        except Exception as e:
            print(f"[TelegramBot] Trader evaluation error: {e}")
            if status_msg_id:
                self.edit_message(chat_id, status_msg_id, f"❌ 评测失败: {str(e)[:100]}")

    def _evaluate_trader(self, portfolio_id: str) -> Optional[tuple]:
        """执行交易员评测"""
        try:
            # 导入评测模块
            from .binance_copytrade_api import fetch_trader_data
            from .trader_analyzer import analyze_trader
            from .trader_evaluation_prompt import (
                build_evaluation_prompt, parse_evaluation_response,
                get_default_evaluation, format_evaluation_message
            )
            from .trader_chart_generator import generate_trader_charts

            # 1. 获取交易员数据
            trader_data = fetch_trader_data(portfolio_id)
            if not trader_data:
                return None

            # 2. 分析数据
            analysis = analyze_trader(trader_data)
            metrics = analysis.metrics

            # 3. AI 评测
            evaluation = self._get_ai_evaluation(metrics, analysis)

            # 4. 生成图表
            chart_bytes = generate_trader_charts(trader_data, metrics, evaluation)

            # 5. 格式化消息
            caption = format_evaluation_message(evaluation, metrics)

            # 截断过长的 caption（Telegram 限制 1024 字符）
            if len(caption) > 1024:
                caption = caption[:1020] + "..."

            return chart_bytes, caption

        except Exception as e:
            print(f"[TelegramBot] Evaluate trader error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_ai_evaluation(self, metrics, analysis=None) -> Dict[str, Any]:
        """获取 AI 评测结果"""
        baseline = None
        try:
            from .trader_evaluation_prompt import (
                build_evaluation_prompt, parse_evaluation_response,
                get_default_evaluation, SYSTEM_PROMPT,
                build_baseline_evaluation, merge_evaluation
            )
            from .ai_api_utils import (
                build_payload, resolve_protocol_and_url,
                parse_compatible_content, parse_responses_body,
                AI_PROTOCOL_RESPONSES
            )

            # 读取 AI 配置
            import json
            import os

            config_path = os.path.join(os.path.dirname(__file__), "ai_signal_config.json")
            baseline = build_baseline_evaluation(metrics, analysis)

            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    ai_config = json.load(f)
            else:
                return baseline

            api_key = ai_config.get("api_key", "")
            api_url = ai_config.get("api_url", "")
            model = ai_config.get("model", "")

            if not api_key or not api_url:
                return baseline

            derived = None
            if analysis is not None:
                derived = {
                    "summary_hint": getattr(analysis, "summary", ""),
                    "strengths_hint": getattr(analysis, "strengths", []),
                    "weaknesses_hint": getattr(analysis, "weaknesses", []),
                    "risk_factors_hint": getattr(analysis, "risk_factors", []),
                }

            # 构建提示词
            metrics_dict = {
                "portfolio_id": metrics.portfolio_id,
                "nickname": metrics.nickname,
                "follower_count": metrics.follower_count,
                "aum": metrics.aum,
                "roi_7d": metrics.roi_7d,
                "roi_30d": metrics.roi_30d,
                "roi_90d": metrics.roi_90d,
                "total_roi": metrics.total_roi,
                "win_rate": metrics.win_rate,
                "max_drawdown": metrics.max_drawdown,
                "sharpe_ratio": metrics.sharpe_ratio,
                "profit_factor": metrics.profit_factor,
                "trade_count": metrics.trade_count,
                "avg_holding_hours": metrics.avg_holding_hours,
                "trade_frequency": metrics.trade_frequency,
                "avg_leverage": metrics.avg_leverage,
                "max_leverage": metrics.max_leverage,
                "preferred_pairs": metrics.preferred_pairs,
                "coin_distribution": metrics.coin_distribution,
                "long_ratio": metrics.long_ratio,
                "margin_addition_count": metrics.margin_addition_count,
                "margin_addition_ratio": metrics.margin_addition_ratio,
                "stop_loss_usage_rate": metrics.stop_loss_usage_rate,
                "avg_position_size": metrics.avg_position_size,
                "max_position_size": metrics.max_position_size,
                "trading_style": metrics.trading_style,
                "holding_style": metrics.holding_style,
                "risk_level": metrics.risk_level,
                "risk_score": metrics.risk_score,
                "margin_behavior": metrics.margin_behavior,
                "margin_concern_level": metrics.margin_concern_level,
            }
            if derived:
                metrics_dict["derived_signals"] = derived

            prompt = build_evaluation_prompt(metrics_dict)

            # 调用 AI API
            protocol, resolved_url = resolve_protocol_and_url(
                api_url, ai_config.get("api_protocol", "auto")
            )

            payload = build_payload(
                protocol, resolved_url, model,
                SYSTEM_PROMPT, prompt,
                max_tokens=2000, temperature=0.3, stream=False
            )

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            resp = requests.post(resolved_url, headers=headers, json=payload, timeout=60)

            print(f"[TelegramBot] AI API response status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"[TelegramBot] AI API error: {resp.text[:500]}")

            if resp.status_code == 200:
                if protocol == AI_PROTOCOL_RESPONSES:
                    content = parse_responses_body(resp.text)
                else:
                    content = parse_compatible_content(resp.json())

                if not content:
                    print(f"[TelegramBot] AI response empty, raw: {resp.text[:500]}")

                result = parse_evaluation_response(content)
                if result:
                    return merge_evaluation(result, baseline)

            return baseline

        except Exception as e:
            print(f"[TelegramBot] AI evaluation error: {e}")
            if baseline is not None:
                return baseline
            return get_default_evaluation()

    # ========== 运行控制 ==========

    def start_polling(self):
        """开始轮询"""
        self.running = True
        print("[TelegramBot] Started polling...")

        while self.running:
            try:
                updates = self.get_updates(timeout=30)
                for update in updates:
                    self.handle_update(update)
            except Exception as e:
                print(f"[TelegramBot] Polling error: {e}")
                time.sleep(5)

    def stop_polling(self):
        """停止轮询"""
        self.running = False
        print("[TelegramBot] Stopped polling.")

    def start_background(self):
        """在后台线程启动"""
        thread = threading.Thread(target=self.start_polling, daemon=True)
        thread.start()
        return thread


# 单例实例
_bot_instance: Optional[TelegramBotHandler] = None


def get_bot() -> TelegramBotHandler:
    """获取机器人单例"""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = TelegramBotHandler()
    return _bot_instance


def start_bot_polling():
    """启动机器人轮询"""
    bot = get_bot()
    bot.start_polling()


def start_bot_background():
    """在后台启动机器人"""
    bot = get_bot()
    return bot.start_background()


if __name__ == "__main__":
    # 直接运行时启动轮询
    start_bot_polling()
