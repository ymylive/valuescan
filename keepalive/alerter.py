"""
Alert notification component for the Process Keepalive Service.

Responsible for sending alerts via Telegram and logging.
"""

import logging
import requests
from typing import Optional

from .config import ServiceConfig, ServiceState, TelegramConfig

logger = logging.getLogger(__name__)

# Emoji constants for visual distinction
EMOJI_RESTART = "🔄"
EMOJI_ERROR = "❌"
EMOJI_SERVICE = "⚙️"


class Alerter:
    """Handles alert notifications."""
    
    def __init__(self, telegram_config: Optional[TelegramConfig] = None):
        """
        Initialize the alerter.
        
        Args:
            telegram_config: Telegram configuration, None to disable
        """
        self.telegram_config = telegram_config
    
    def format_restart_alert(self, config: ServiceConfig, state: ServiceState, reason: str) -> str:
        """
        Format a restart alert message.
        
        Args:
            config: Service configuration
            state: Current service state
            reason: Reason for restart
            
        Returns:
            Formatted alert message containing service name, reason, and restart count
        """
        return (
            f"{EMOJI_RESTART} 服务重启通知\n"
            f"{EMOJI_SERVICE} 服务: {config.display_name} ({config.name})\n"
            f"原因: {reason}\n"
            f"重启次数: {state.restart_count}"
        )
    
    def format_error_alert(self, config: ServiceConfig, error: str) -> str:
        """
        Format an error alert message.
        
        Args:
            config: Service configuration
            error: Error description
            
        Returns:
            Formatted alert message containing service name and error details
        """
        return (
            f"{EMOJI_ERROR} 服务错误通知\n"
            f"{EMOJI_SERVICE} 服务: {config.display_name} ({config.name})\n"
            f"错误: {error}"
        )
    
    def send_telegram(self, message: str) -> bool:
        """
        Send a message via Telegram bot API.
        
        Args:
            message: Message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if self.telegram_config is None or not self.telegram_config.enabled:
            logger.debug("Telegram notifications disabled, skipping")
            return False
        
        if not self.telegram_config.bot_token or not self.telegram_config.chat_id:
            logger.warning("Telegram bot_token or chat_id not configured")
            return False
        
        url = f"https://api.telegram.org/bot{self.telegram_config.bot_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_config.chat_id,
            "text": message,
            "parse_mode": "HTML",
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.debug("Telegram message sent successfully")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False
        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    def send_alert(self, message: str) -> None:
        """
        Send an alert via Telegram and log.
        
        Always logs the alert regardless of Telegram status.
        
        Args:
            message: Alert message to send
        """
        # Always log the alert (Requirement 4.4)
        logger.warning(f"ALERT: {message}")
        
        # Attempt to send via Telegram if configured
        self.send_telegram(message)
