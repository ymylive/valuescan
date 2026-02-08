#!/usr/bin/env python3
"""
Configuration validation module for the Signal Monitor API (signal + system only).
"""

import re
from typing import Dict, List, Tuple, Any


class ValidationError(Exception):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class ConfigValidator:
    @staticmethod
    def validate_url(url: str, field_name: str) -> None:
        if not url:
            return
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$',
            re.IGNORECASE,
        )
        if not url_pattern.match(url):
            raise ValidationError(field_name, f"Invalid URL format: {url}")

    def validate_signal_config(self, config: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        enable_telegram = config.get('enable_telegram', True)
        if enable_telegram:
            if not config.get('telegram_bot_token'):
                errors.append('telegram_bot_token is required when telegram is enabled')
            if not config.get('telegram_chat_id'):
                errors.append('telegram_chat_id is required when telegram is enabled')
        return errors


def validate_config(config_type: str, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    validator = ConfigValidator()
    errors: List[str] = []

    if config_type == 'signal':
        errors = validator.validate_signal_config(config)

    return (len(errors) == 0, errors)
