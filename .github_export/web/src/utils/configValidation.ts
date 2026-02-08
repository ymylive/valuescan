import {
  AIServiceConfig,
  SignalMonitorConfig,
  TradingBotConfig,
  SystemConfig,
  LoggingConfig,
} from '../types/config';

export interface ValidationError {
  field: string;
  message: string;
  severity: 'error' | 'warning';
}

export class ConfigValidator {
  private errors: ValidationError[] = [];

  // Validate AI Service Configuration
  validateAIService(config: AIServiceConfig): ValidationError[] {
    this.errors = [];

    if (config.enable_ai_position_agent) {
      if (!config.ai_position_api_url) {
        this.addError('ai_position_api_url', 'AI 仓位管理 API URL 不能为空', 'error');
      } else if (!this.isValidUrl(config.ai_position_api_url)) {
        this.addError('ai_position_api_url', 'AI 仓位管理 API URL 格式不正确', 'error');
      }

      if (!config.ai_position_api_key) {
        this.addError('ai_position_api_key', 'AI 仓位管理 API 密钥不能为空', 'error');
      }

      if (!config.ai_position_model) {
        this.addError('ai_position_model', 'AI 仓位管理模型不能为空', 'error');
      }

      if (config.ai_position_check_interval < 60) {
        this.addError('ai_position_check_interval', 'AI 仓位检查间隔不应小于 60 秒', 'warning');
      }
    }

    if (config.enable_ai_evolution) {
      if (!config.ai_evolution_api_url) {
        this.addError('ai_evolution_api_url', 'AI 进化 API URL 不能为空', 'error');
      } else if (!this.isValidUrl(config.ai_evolution_api_url)) {
        this.addError('ai_evolution_api_url', 'AI 进化 API URL 格式不正确', 'error');
      }

      if (!config.ai_evolution_api_key) {
        this.addError('ai_evolution_api_key', 'AI 进化 API 密钥不能为空', 'error');
      }

      if (!config.ai_evolution_model) {
        this.addError('ai_evolution_model', 'AI 进化模型不能为空', 'error');
      }

      if (config.ai_evolution_min_trades < 10) {
        this.addError('ai_evolution_min_trades', 'AI 进化最少交易数不应小于 10', 'warning');
      }

      if (config.enable_ai_ab_testing && (config.ai_ab_test_ratio < 0 || config.ai_ab_test_ratio > 1)) {
        this.addError('ai_ab_test_ratio', 'A/B 测试比例必须在 0-1 之间', 'error');
      }
    }

    if (config.ai_summary_proxy && !this.isValidUrl(config.ai_summary_proxy)) {
      this.addError('ai_summary_proxy', 'AI 市场总结代理地址格式不正确', 'warning');
    }

    return this.errors;
  }

  // Validate Signal Monitor Configuration
  validateSignalMonitor(config: SignalMonitorConfig): ValidationError[] {
    this.errors = [];

    if (config.enable_telegram) {
      if (!config.telegram_bot_token) {
        this.addError('telegram_bot_token', '启用 Telegram 通知需要配置 Bot Token', 'error');
      }

      if (!config.telegram_chat_id) {
        this.addError('telegram_chat_id', '启用 Telegram 通知需要配置 Chat ID', 'error');
      }
    }

    if (config.chrome_debug_port < 1024 || config.chrome_debug_port > 65535) {
      this.addError('chrome_debug_port', 'Chrome 调试端口必须在 1024-65535 之间', 'error');
    }

    if (config.poll_interval < 1) {
      this.addError('poll_interval', '轮询间隔必须大于 0', 'error');
    }

    if (config.request_timeout < 5) {
      this.addError('request_timeout', '请求超时时间不应小于 5 秒', 'warning');
    }

    if (config.enable_ipc_forwarding) {
      if (config.ipc_port < 1024 || config.ipc_port > 65535) {
        this.addError('ipc_port', 'IPC 端口必须在 1024-65535 之间', 'error');
      }
    }

    if (config.enable_tradingview_chart) {
      if (!config.chart_img_api_key) {
        this.addError('chart_img_api_key', '启用 TradingView 图表需要配置 API Key', 'warning');
      }

      if (config.chart_img_width < 400 || config.chart_img_width > 2000) {
        this.addError('chart_img_width', '图表宽度应在 400-2000 像素之间', 'warning');
      }

      if (config.chart_img_height < 300 || config.chart_img_height > 1500) {
        this.addError('chart_img_height', '图表高度应在 300-1500 像素之间', 'warning');
      }
    }

    if (config.ai_brief_wait_timeout_seconds < 10 || config.ai_brief_wait_timeout_seconds > 300) {
      this.addError('ai_brief_wait_timeout_seconds', 'AI 简评等待超时建议在 10-300 秒之间', 'warning');
    }

    if (config.bull_bear_signal_ttl_seconds < 3600) {
      this.addError('bull_bear_signal_ttl_seconds', '看涨/看跌信号有效期建议不少于 3600 秒', 'warning');
    }

    return this.errors;
  }

  // Validate Trading Bot Configuration
  validateTradingBot(config: TradingBotConfig): ValidationError[] {
    this.errors = [];

    if (config.auto_trading_enabled && !config.use_testnet) {
      if (!config.binance_api_key) {
        this.addError('binance_api_key', '启用实盘自动交易需要配置币安 API Key', 'error');
      }

      if (!config.binance_api_secret) {
        this.addError('binance_api_secret', '启用实盘自动交易需要配置币安 API Secret', 'error');
      }
    } else if (!config.binance_api_key || !config.binance_api_secret) {
      this.addError('binance_api_key', '未配置币安 API，部分功能将不可用', 'warning');
    }

    if (config.leverage < 1 || config.leverage > 125) {
      this.addError('leverage', '杠杆倍数必须在 1-125 之间', 'error');
    }

    if (config.max_position_percent <= 0 || config.max_position_percent > 100) {
      this.addError('max_position_percent', '单个标的最大仓位比例必须在 0-100 之间', 'error');
    }

    if (config.max_total_position_percent <= 0 || config.max_total_position_percent > 100) {
      this.addError('max_total_position_percent', '总仓位比例上限必须在 0-100 之间', 'error');
    }

    if (config.max_daily_trades < 1) {
      this.addError('max_daily_trades', '每日最大交易次数必须大于 0', 'error');
    }

    if (config.max_daily_loss_percent <= 0 || config.max_daily_loss_percent > 50) {
      this.addError('max_daily_loss_percent', '每日最大亏损比例应在 0-50 之间', 'warning');
    }

    if (config.stop_loss_percent <= 0 || config.stop_loss_percent > 10) {
      this.addError('stop_loss_percent', '止损百分比应在 0-10 之间', 'warning');
    }

    if (config.enable_trailing_stop) {
      if (config.trailing_stop_activation <= 0) {
        this.addError('trailing_stop_activation', '移动止损激活阈值必须大于 0', 'error');
      }

      if (config.trailing_stop_callback <= 0) {
        this.addError('trailing_stop_callback', '移动止损回调比例必须大于 0', 'error');
      }

      if (config.trailing_stop_callback >= config.trailing_stop_activation) {
        this.addError('trailing_stop_callback', '移动止损回调比例应小于激活阈值', 'warning');
      }
    }

    if (config.min_signal_score < 0 || config.min_signal_score > 1) {
      this.addError('min_signal_score', '最低信号评分阈值必须在 0-1 之间', 'error');
    }

    if (config.auto_trading_enabled && !config.use_testnet) {
      this.addError('auto_trading_enabled', '启用自动交易前请确认已充分测试', 'warning');
    }

    if (config.slippage_tolerance < 0.1 || config.slippage_tolerance > 5) {
      this.addError('slippage_tolerance', '价格滑点容忍度应在 0.1-5 之间', 'warning');
    }

    return this.errors;
  }

  // Validate System Configuration
  validateSystem(config: SystemConfig): ValidationError[] {
    this.errors = [];

    if (config.nofx_backend_port < 1024 || config.nofx_backend_port > 65535) {
      this.addError('nofx_backend_port', '后端端口必须在 1024-65535 之间', 'error');
    }

    if (config.nofx_frontend_port < 1024 || config.nofx_frontend_port > 65535) {
      this.addError('nofx_frontend_port', '前端端口必须在 1024-65535 之间', 'error');
    }

    if (config.nofx_backend_port === config.nofx_frontend_port) {
      this.addError('nofx_frontend_port', '前端和后端端口不能相同', 'error');
    }

    if (!config.jwt_secret) {
      this.addError('jwt_secret', 'JWT Secret 未配置，建议使用"生成密钥"按钮自动生成', 'warning');
    } else if (config.jwt_secret.length < 32) {
      this.addError('jwt_secret', 'JWT Secret 长度应至少为 32 字符', 'warning');
    }

    if (!config.data_encryption_key) {
      this.addError('data_encryption_key', '数据加密密钥未配置，建议使用"生成密钥"按钮自动生成', 'warning');
    }

    if (!config.rsa_private_key) {
      this.addError('rsa_private_key', 'RSA 私钥未配置，建议使用"生成密钥"按钮自动生成', 'warning');
    } else if (!config.rsa_private_key.includes('BEGIN RSA PRIVATE KEY')) {
      this.addError('rsa_private_key', 'RSA 私钥格式不正确', 'error');
    }

    if (config.transport_encryption) {
      this.addError('transport_encryption', '启用传输加密需要配置 HTTPS', 'warning');
    }

    return this.errors;
  }

  // Validate Logging Configuration
  validateLogging(config: LoggingConfig): ValidationError[] {
    this.errors = [];

    if (config.log_to_file) {
      if (!config.log_file) {
        this.addError('log_file', '日志文件路径不能为空', 'error');
      }

      if (config.log_max_size < 1048576) {
        this.addError('log_max_size', '日志文件最大大小不应小于 1MB', 'warning');
      }

      if (config.log_backup_count < 1) {
        this.addError('log_backup_count', '保留的日志文件数量必须大于 0', 'error');
      }
    }

    return this.errors;
  }

  // Validate all configurations
  validateAll(
    aiConfig: AIServiceConfig,
    signalConfig: SignalMonitorConfig,
    tradingConfig: TradingBotConfig,
    systemConfig: SystemConfig,
    loggingConfig: LoggingConfig
  ): ValidationError[] {
    const allErrors: ValidationError[] = [
      ...this.validateAIService(aiConfig),
      ...this.validateSignalMonitor(signalConfig),
      ...this.validateTradingBot(tradingConfig),
      ...this.validateSystem(systemConfig),
      ...this.validateLogging(loggingConfig),
    ];

    return allErrors;
  }

  // Helper methods
  private addError(field: string, message: string, severity: 'error' | 'warning') {
    this.errors.push({ field, message, severity });
  }

  private isValidUrl(url: string): boolean {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  }
}

// Export singleton instance
export const configValidator = new ConfigValidator();
