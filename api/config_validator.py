#!/usr/bin/env python3
"""
Configuration validation module for ValueScan API
Provides server-side validation for all config fields
"""

import re
from typing import Dict, List, Tuple, Any, Optional


class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class ConfigValidator:
    """Validates configuration data"""

    @staticmethod
    def validate_url(url: str, field_name: str) -> None:
        """Validate URL format"""
        if not url:
            return

        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        if not url_pattern.match(url):
            raise ValidationError(field_name, f"Invalid URL format: {url}")

    @staticmethod
    def validate_range(value: Any, min_val: float, max_val: float, field_name: str) -> None:
        """Validate numeric range"""
        try:
            num_val = float(value)
            if not (min_val <= num_val <= max_val):
                raise ValidationError(
                    field_name,
                    f"Value {num_val} must be between {min_val} and {max_val}"
                )
        except (TypeError, ValueError):
            raise ValidationError(field_name, f"Invalid numeric value: {value}")

    @staticmethod
    def validate_required(value: Any, field_name: str) -> None:
        """Validate required field"""
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError(field_name, "This field is required")

    @staticmethod
    def validate_conditional_required(
        condition: bool,
        value: Any,
        field_name: str,
        condition_desc: str
    ) -> None:
        """Validate conditionally required field"""
        if condition:
            ConfigValidator.validate_required(value, field_name)
            if not value:
                raise ValidationError(
                    field_name,
                    f"Required when {condition_desc}"
                )

    @staticmethod
    def validate_signal_monitor_config(config: Dict) -> List[str]:
        """Validate signal monitor configuration"""
        errors = []

        try:
            # Validate ValueScan API settings
            if config.get('enable_valuescan'):
                ConfigValidator.validate_conditional_required(
                    True,
                    config.get('valuescan_api_url'),
                    'valuescan_api_url',
                    'ValueScan is enabled'
                )
                ConfigValidator.validate_url(
                    config.get('valuescan_api_url', ''),
                    'valuescan_api_url'
                )

            # Validate Telegram settings
            if config.get('enable_telegram'):
                ConfigValidator.validate_conditional_required(
                    True,
                    config.get('telegram_bot_token'),
                    'telegram_bot_token',
                    'Telegram is enabled'
                )
                ConfigValidator.validate_conditional_required(
                    True,
                    config.get('telegram_chat_id'),
                    'telegram_chat_id',
                    'Telegram is enabled'
                )

            # Validate polling interval
            if 'valuescan_poll_interval' in config:
                ConfigValidator.validate_range(
                    config['valuescan_poll_interval'],
                    1, 300,
                    'valuescan_poll_interval'
                )

            # Validate age filter
            if 'age_filter_minutes' in config:
                ConfigValidator.validate_range(
                    config['age_filter_minutes'],
                    0, 1440,
                    'age_filter_minutes'
                )

            # Validate IPC settings
            if config.get('enable_ipc_forwarding'):
                if 'ipc_port' in config:
                    ConfigValidator.validate_range(
                        config['ipc_port'],
                        1024, 65535,
                        'ipc_port'
                    )

                if 'ipc_connect_timeout' in config:
                    ConfigValidator.validate_range(
                        config['ipc_connect_timeout'],
                        1, 60,
                        'ipc_connect_timeout'
                    )

                if 'ipc_max_retries' in config:
                    ConfigValidator.validate_range(
                        config['ipc_max_retries'],
                        0, 100,
                        'ipc_max_retries'
                    )

        except ValidationError as e:
            errors.append(f"{e.field}: {e.message}")

        return errors

    @staticmethod
    def validate_trader_config(config: Dict) -> List[str]:
        """Validate trader configuration"""
        errors = []

        try:
            # Validate Binance API settings
            if config.get('enable_trading'):
                ConfigValidator.validate_conditional_required(
                    True,
                    config.get('binance_api_key'),
                    'binance_api_key',
                    'trading is enabled'
                )
                ConfigValidator.validate_conditional_required(
                    True,
                    config.get('binance_api_secret'),
                    'binance_api_secret',
                    'trading is enabled'
                )

            # Validate leverage
            if 'leverage' in config:
                ConfigValidator.validate_range(
                    config['leverage'],
                    1, 125,
                    'leverage'
                )

            # Validate position size percentage
            if 'position_size_percent' in config:
                ConfigValidator.validate_range(
                    config['position_size_percent'],
                    0.1, 100,
                    'position_size_percent'
                )

            # Validate stop loss
            if 'stop_loss_percent' in config:
                ConfigValidator.validate_range(
                    config['stop_loss_percent'],
                    0.1, 50,
                    'stop_loss_percent'
                )

            # Validate take profit levels
            for i in range(1, 4):
                tp_key = f'take_profit_{i}_percent'
                if tp_key in config:
                    ConfigValidator.validate_range(
                        config[tp_key],
                        0.1, 1000,
                        tp_key
                    )

                tp_qty_key = f'take_profit_{i}_qty_percent'
                if tp_qty_key in config:
                    ConfigValidator.validate_range(
                        config[tp_qty_key],
                        1, 100,
                        tp_qty_key
                    )

            # Validate trailing stop
            if 'trailing_stop_activation_percent' in config:
                ConfigValidator.validate_range(
                    config['trailing_stop_activation_percent'],
                    0, 100,
                    'trailing_stop_activation_percent'
                )

            if 'trailing_stop_callback_percent' in config:
                ConfigValidator.validate_range(
                    config['trailing_stop_callback_percent'],
                    0.1, 50,
                    'trailing_stop_callback_percent'
                )

            # Validate pyramiding
            if 'max_pyramiding_levels' in config:
                ConfigValidator.validate_range(
                    config['max_pyramiding_levels'],
                    1, 10,
                    'max_pyramiding_levels'
                )

            if 'pyramiding_scale_factor' in config:
                ConfigValidator.validate_range(
                    config['pyramiding_scale_factor'],
                    0.1, 10,
                    'pyramiding_scale_factor'
                )

            # Validate Telegram notification settings
            if config.get('enable_telegram_notifications'):
                ConfigValidator.validate_conditional_required(
                    True,
                    config.get('telegram_bot_token'),
                    'telegram_bot_token',
                    'Telegram notifications are enabled'
                )
                ConfigValidator.validate_conditional_required(
                    True,
                    config.get('telegram_chat_id'),
                    'telegram_chat_id',
                    'Telegram notifications are enabled'
                )

        except ValidationError as e:
            errors.append(f"{e.field}: {e.message}")

        return errors

    @staticmethod
    def validate_copytrade_config(config: Dict) -> List[str]:
        """Validate copytrade configuration"""
        errors = []

        try:
            # Validate Telegram settings
            if config.get('enable_copytrade'):
                ConfigValidator.validate_conditional_required(
                    True,
                    config.get('telegram_api_id'),
                    'telegram_api_id',
                    'copytrade is enabled'
                )
                ConfigValidator.validate_conditional_required(
                    True,
                    config.get('telegram_api_hash'),
                    'telegram_api_hash',
                    'copytrade is enabled'
                )
                ConfigValidator.validate_conditional_required(
                    True,
                    config.get('telegram_phone'),
                    'telegram_phone',
                    'copytrade is enabled'
                )

            # Validate Binance API settings
            if config.get('enable_copytrade'):
                ConfigValidator.validate_conditional_required(
                    True,
                    config.get('binance_api_key'),
                    'binance_api_key',
                    'copytrade is enabled'
                )
                ConfigValidator.validate_conditional_required(
                    True,
                    config.get('binance_api_secret'),
                    'binance_api_secret',
                    'copytrade is enabled'
                )

            # Validate leverage
            if 'leverage' in config:
                ConfigValidator.validate_range(
                    config['leverage'],
                    1, 125,
                    'leverage'
                )

            # Validate position size
            if 'position_size_usdt' in config:
                ConfigValidator.validate_range(
                    config['position_size_usdt'],
                    1, 1000000,
                    'position_size_usdt'
                )

            # Validate stop loss
            if 'stop_loss_percent' in config:
                ConfigValidator.validate_range(
                    config['stop_loss_percent'],
                    0.1, 50,
                    'stop_loss_percent'
                )

            # Validate take profit
            if 'take_profit_percent' in config:
                ConfigValidator.validate_range(
                    config['take_profit_percent'],
                    0.1, 1000,
                    'take_profit_percent'
                )

        except ValidationError as e:
            errors.append(f"{e.field}: {e.message}")

        return errors

    @staticmethod
    def validate_ai_config(config: Dict, config_type: str) -> List[str]:
        """Validate AI module configuration"""
        errors = []

        try:
            # Validate API settings
            if config.get('enabled'):
                ConfigValidator.validate_conditional_required(
                    True,
                    config.get('api_key'),
                    'api_key',
                    f'{config_type} is enabled'
                )
                ConfigValidator.validate_conditional_required(
                    True,
                    config.get('api_url'),
                    'api_url',
                    f'{config_type} is enabled'
                )
                ConfigValidator.validate_url(
                    config.get('api_url', ''),
                    'api_url'
                )
                ConfigValidator.validate_conditional_required(
                    True,
                    config.get('model'),
                    'model',
                    f'{config_type} is enabled'
                )

            # Validate interval hours
            if 'interval_hours' in config:
                ConfigValidator.validate_range(
                    config['interval_hours'],
                    0.1, 168,  # 0.1 hour to 1 week
                    'interval_hours'
                )

            # Validate lookback hours
            if 'lookback_hours' in config:
                ConfigValidator.validate_range(
                    config['lookback_hours'],
                    1, 720,  # 1 hour to 30 days
                    'lookback_hours'
                )

        except ValidationError as e:
            errors.append(f"{e.field}: {e.message}")

        return errors


def validate_config(config_type: str, config: Dict) -> Tuple[bool, List[str]]:
    """
    Validate configuration data

    Args:
        config_type: Type of config ('signal', 'trader', 'copytrade', 'ai_summary', etc.)
        config: Configuration dictionary

    Returns:
        Tuple of (is_valid, error_messages)
    """
    validator = ConfigValidator()

    if config_type == 'signal':
        errors = validator.validate_signal_monitor_config(config)
    elif config_type == 'trader':
        errors = validator.validate_trader_config(config)
    elif config_type == 'copytrade':
        errors = validator.validate_copytrade_config(config)
    elif config_type in ['ai_summary', 'ai_signal', 'ai_levels', 'ai_market']:
        errors = validator.validate_ai_config(config, config_type)
    else:
        return True, []

    return len(errors) == 0, errors
