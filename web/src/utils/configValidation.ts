import {
  AIServiceConfig,
  SignalMonitorConfig,
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

  validateAIService(config: AIServiceConfig): ValidationError[] {
    this.errors = [];

    if (config.ai_summary_proxy && !this.isValidUrl(config.ai_summary_proxy)) {
      this.addError('ai_summary_proxy', 'AI 代理地址格式不正确', 'warning');
    }

    if (config.enable_ai_signal_analysis_service) {
      if (!config.ai_signal_analysis_api_url) {
        this.addError('ai_signal_analysis_api_url', 'AI 简评 API URL 不能为空', 'error');
      } else if (!this.isValidUrl(config.ai_signal_analysis_api_url)) {
        this.addError('ai_signal_analysis_api_url', 'AI 简评 API URL 格式不正确', 'error');
      }

      if (!config.ai_signal_analysis_api_key) {
        this.addError('ai_signal_analysis_api_key', 'AI 简评 API Key 不能为空', 'error');
      }

      if (!config.ai_signal_analysis_model) {
        this.addError('ai_signal_analysis_model', 'AI 简评模型不能为空', 'error');
      }

      const hasSecondary = Boolean(
        config.ai_signal_analysis_secondary_api_url ||
          config.ai_signal_analysis_secondary_api_key ||
          config.ai_signal_analysis_secondary_model,
      );
      if (hasSecondary) {
        if (!config.ai_signal_analysis_secondary_api_url) {
          this.addError('ai_signal_analysis_secondary_api_url', '第二优先级 API URL 不能为空', 'error');
        } else if (!this.isValidUrl(config.ai_signal_analysis_secondary_api_url)) {
          this.addError('ai_signal_analysis_secondary_api_url', '第二优先级 API URL 格式不正确', 'error');
        }
        if (!config.ai_signal_analysis_secondary_api_key) {
          this.addError('ai_signal_analysis_secondary_api_key', '第二优先级 API Key 不能为空', 'error');
        }
        if (!config.ai_signal_analysis_secondary_model) {
          this.addError('ai_signal_analysis_secondary_model', '第二优先级模型不能为空', 'error');
        }
      }

      const hasTertiary = Boolean(
        config.ai_signal_analysis_tertiary_api_url ||
          config.ai_signal_analysis_tertiary_api_key ||
          config.ai_signal_analysis_tertiary_model,
      );
      if (hasTertiary) {
        if (!config.ai_signal_analysis_tertiary_api_url) {
          this.addError('ai_signal_analysis_tertiary_api_url', '第三优先级 API URL 不能为空', 'error');
        } else if (!this.isValidUrl(config.ai_signal_analysis_tertiary_api_url)) {
          this.addError('ai_signal_analysis_tertiary_api_url', '第三优先级 API URL 格式不正确', 'error');
        }
        if (!config.ai_signal_analysis_tertiary_api_key) {
          this.addError('ai_signal_analysis_tertiary_api_key', '第三优先级 API Key 不能为空', 'error');
        }
        if (!config.ai_signal_analysis_tertiary_model) {
          this.addError('ai_signal_analysis_tertiary_model', '第三优先级模型不能为空', 'error');
        }
      }

      if (config.ai_signal_analysis_mcp_enabled) {
        if (!config.ai_signal_analysis_mcp_source_primary_command) {
          this.addError('ai_signal_analysis_mcp_source_primary_command', 'MCP 主搜索源 command 不能为空', 'error');
        }
        if (!config.ai_signal_analysis_mcp_source_primary_args) {
          this.addError('ai_signal_analysis_mcp_source_primary_args', 'MCP 主搜索源 args 不能为空', 'error');
        }
        if (config.ai_signal_analysis_mcp_timeout_sec < 5 || config.ai_signal_analysis_mcp_timeout_sec > 120) {
          this.addError('ai_signal_analysis_mcp_timeout_sec', 'MCP 超时应在 5-120 秒', 'warning');
        }
        if (config.ai_signal_analysis_mcp_max_results < 1 || config.ai_signal_analysis_mcp_max_results > 20) {
          this.addError('ai_signal_analysis_mcp_max_results', 'MCP 单源结果数应在 1-20', 'warning');
        }
      }

      if (config.ai_signal_analysis_interval_hours < 0.1 || config.ai_signal_analysis_interval_hours > 168) {
        this.addError('ai_signal_analysis_interval_hours', 'AI 简评频率应在 0.1-168 小时', 'warning');
      }

      if (config.ai_signal_analysis_lookback_hours < 1 || config.ai_signal_analysis_lookback_hours > 720) {
        this.addError('ai_signal_analysis_lookback_hours', 'AI 简评回溯应在 1-720 小时', 'warning');
      }
    }

    if (config.enable_ai_key_levels_service) {
      if (!config.ai_key_levels_api_url) {
        this.addError('ai_key_levels_api_url', 'AI 主力位 API URL 不能为空', 'error');
      } else if (!this.isValidUrl(config.ai_key_levels_api_url)) {
        this.addError('ai_key_levels_api_url', 'AI 主力位 API URL 格式不正确', 'error');
      }

      if (!config.ai_key_levels_api_key) {
        this.addError('ai_key_levels_api_key', 'AI 主力位 API Key 不能为空', 'error');
      }

      if (!config.ai_key_levels_model) {
        this.addError('ai_key_levels_model', 'AI 主力位模型不能为空', 'error');
      }
    }

    if (config.enable_ai_overlays_service) {
      if (!config.ai_overlays_api_url) {
        this.addError('ai_overlays_api_url', 'AI 形态叠加 API URL 不能为空', 'error');
      } else if (!this.isValidUrl(config.ai_overlays_api_url)) {
        this.addError('ai_overlays_api_url', 'AI 形态叠加 API URL 格式不正确', 'error');
      }

      if (!config.ai_overlays_api_key) {
        this.addError('ai_overlays_api_key', 'AI 形态叠加 API Key 不能为空', 'error');
      }

      if (!config.ai_overlays_model) {
        this.addError('ai_overlays_model', 'AI 形态叠加模型不能为空', 'error');
      }
    }

    if (config.enable_ai_market_analysis) {
      if (!config.ai_market_analysis_api_url) {
        this.addError('ai_market_analysis_api_url', 'AI 市场分析 API URL 不能为空', 'error');
      } else if (!this.isValidUrl(config.ai_market_analysis_api_url)) {
        this.addError('ai_market_analysis_api_url', 'AI 市场分析 API URL 格式不正确', 'error');
      }

      if (!config.ai_market_analysis_api_key) {
        this.addError('ai_market_analysis_api_key', 'AI 市场分析 API Key 不能为空', 'error');
      }

      if (!config.ai_market_analysis_model) {
        this.addError('ai_market_analysis_model', 'AI 市场分析模型不能为空', 'error');
      }

      if (config.ai_market_analysis_interval_hours < 0.1 || config.ai_market_analysis_interval_hours > 168) {
        this.addError('ai_market_analysis_interval_hours', 'AI 市场分析频率应在 0.1-168 小时', 'warning');
      }

      if (config.ai_market_analysis_lookback_hours < 1 || config.ai_market_analysis_lookback_hours > 720) {
        this.addError('ai_market_analysis_lookback_hours', 'AI 市场分析回溯应在 1-720 小时', 'warning');
      }
    }

    return this.errors;
  }

  validateSignalMonitor(config: SignalMonitorConfig): ValidationError[] {
    this.errors = [];

    if (config.enable_telegram) {
      if (!config.telegram_bot_token) {
        this.addError('telegram_bot_token', '已启用 Telegram 时必须填写 Bot Token', 'warning');
      }

      if (!config.telegram_chat_id) {
        this.addError('telegram_chat_id', '已启用 Telegram 时必须填写 Chat ID', 'warning');
      }
    }

    if (config.chrome_debug_port < 1024 || config.chrome_debug_port > 65535) {
      this.addError('chrome_debug_port', 'Chrome 调试端口应在 1024-65535 之间', 'error');
    }

    if (config.poll_interval < 1) {
      this.addError('poll_interval', '轮询间隔必须大于 0', 'error');
    }

    if (config.ai_signal_interval_minutes < 1 || config.ai_signal_interval_minutes > 1440) {
      this.addError('ai_signal_interval_minutes', '信号发送间隔应在 1-1440 分钟', 'warning');
    }

    if (config.request_timeout < 5) {
      this.addError('request_timeout', '请求超时建议不低于 5 秒', 'warning');
    }

    if (config.enable_ipc_forwarding) {
      if (config.ipc_port < 1024 || config.ipc_port > 65535) {
        this.addError('ipc_port', 'IPC 端口应在 1024-65535 之间', 'error');
      }
    }

    if (config.enable_tradingview_chart) {
      if (!config.chart_img_api_key) {
        this.addError('chart_img_api_key', '启用 TradingView 时需要 API Key', 'warning');
      }

      if (config.chart_img_width < 400 || config.chart_img_width > 2000) {
        this.addError('chart_img_width', '图表宽度应在 400-2000 像素', 'warning');
      }

      if (config.chart_img_height < 300 || config.chart_img_height > 1500) {
        this.addError('chart_img_height', '图表高度应在 300-1500 像素', 'warning');
      }
    }

    return this.errors;
  }

  validateSystem(config: SystemConfig): ValidationError[] {
    this.errors = [];

    if (config.nofx_backend_port < 1024 || config.nofx_backend_port > 65535) {
      this.addError('nofx_backend_port', '后端端口应在 1024-65535 之间', 'error');
    }

    if (config.nofx_frontend_port < 1024 || config.nofx_frontend_port > 65535) {
      this.addError('nofx_frontend_port', '前端端口应在 1024-65535 之间', 'error');
    }

    if (config.nofx_backend_port === config.nofx_frontend_port) {
      this.addError('nofx_frontend_port', '前后端端口不能相同', 'error');
    }

    if (!config.jwt_secret) {
      this.addError('jwt_secret', 'JWT Secret 不能为空', 'warning');
    } else if (config.jwt_secret.length < 32) {
      this.addError('jwt_secret', 'JWT Secret 至少 32 位', 'warning');
    }

    if (!config.data_encryption_key) {
      this.addError('data_encryption_key', '数据加密密钥不能为空', 'warning');
    }

    if (!config.rsa_private_key) {
      this.addError('rsa_private_key', 'RSA 私钥不能为空', 'warning');
    }

    if (config.transport_encryption) {
      this.addError('transport_encryption', '启用传输加密需配置 HTTPS', 'warning');
    }

    return this.errors;
  }

  validateLogging(config: LoggingConfig): ValidationError[] {
    this.errors = [];

    if (config.log_to_file) {
      if (!config.log_file) {
        this.addError('log_file', '日志文件不能为空', 'error');
      }

      if (config.log_max_size < 1048576) {
        this.addError('log_max_size', '日志最大大小不应小于 1MB', 'warning');
      }

      if (config.log_backup_count < 1) {
        this.addError('log_backup_count', '日志备份数量必须大于 0', 'error');
      }
    }

    return this.errors;
  }

  validateAll(
    aiConfig: AIServiceConfig,
    signalConfig: SignalMonitorConfig,
    systemConfig: SystemConfig,
    loggingConfig: LoggingConfig,
  ): ValidationError[] {
    return [
      ...this.validateAIService(aiConfig),
      ...this.validateSignalMonitor(signalConfig),
      ...this.validateSystem(systemConfig),
      ...this.validateLogging(loggingConfig),
    ];
  }

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

export const configValidator = new ConfigValidator();
