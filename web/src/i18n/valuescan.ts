/**
 * ValueScan 多语言翻译模块
 */
export type Language = 'zh' | 'en'

export const translations = {
  zh: {
    // 导航
    dashboard: '仪表盘',
    systemConfig: '系统配置',
    logs: '运行日志',
    language: '语言',
    
    // 仪表盘
    systemOverview: '系统概览',
    allServicesRunning: '所有服务正常运行',
    someServicesDown: '部分服务异常',
    refreshStatus: '刷新状态',
    quickActions: '快捷操作',
    editConfig: '编辑配置',
    modifyParams: '修改系统参数',
    viewLogs: '查看日志',
    monitorStatus: '监控运行状态',
    exportConfig: '导出配置',
    backupSettings: '备份当前设置',
    importConfig: '导入配置',
    restoreSettings: '恢复系统设置',
    
    // 服务
    services: '服务',
    signalMonitor: '信号监控',
    signalMonitorDesc: 'ValueScan 信号捕获',
    autoTrader: '自动交易',
    autoTraderDesc: 'Binance 合约交易',
    copyTrade: '跟单系统',
    copyTradeDesc: 'Telegram 信号跟单',
    serviceMonitor: '服务监控',
    serviceMonitorDesc: '自动重启守护',
    running: '运行中',
    stopped: '已停止',
    error: '错误',
    start: '启动',
    stop: '停止',
    restart: '重启',
    
    // 配置
    manageParams: '管理核心模块参数',
    unsaved: '未保存',
    saveConfig: '保存配置',
    configSaved: '配置保存成功',
    serviceRestarting: '服务正在重启以应用新配置',
    saveFailed: '保存失败',
    loadFailed: '加载失败',
    loadConfigFailed: '获取配置失败',
    
    // 配置分区
    signal: '信号监控',
    trader: '自动交易',
    copytrade: '跟单系统',
    keepalive: '服务监控',
    
    // 信号监控配置
    telegramConfig: 'Telegram 配置',
    telegramConfigDesc: '配置 Telegram Bot 和通知',
    enableTelegram: '启用 Telegram 通知',
    botToken: 'Bot Token',
    chatId: 'Chat ID',
    minInterval: '最小间隔 (秒)',
    
    browserConfig: '浏览器配置',
    browserConfigDesc: 'Chrome 自动化设置',
    chromeHost: 'Chrome 调试地址',
    chromePort: 'Chrome 调试端口',
    headlessMode: '无头模式',
    
    apiConfig: 'API 配置',
    apiConfigDesc: '后端服务端点',
    apiHost: 'API 主机',
    apiPort: 'API 端口',
    
    pollingConfig: '轮询与监控',
    pollingConfigDesc: '信号采集间隔设置',
    pollingInterval: '轮询间隔 (秒)',
    signalTimeout: '信号超时 (秒)',
    maxRetries: '最大重试次数',
    
    signalFilter: '信号过滤',
    signalFilterDesc: '过滤规则配置',
    minScore: '最小分数',
    symbolWhitelist: '币种白名单',
    symbolBlacklist: '币种黑名单',
    
    tokenRefresher: 'Token 刷新器',
    tokenRefresherDesc: '自动刷新认证Token',
    enableRefresher: '启用刷新器',
    refreshInterval: '刷新间隔 (秒)',
    
    ipcForwarding: 'IPC 转发',
    ipcForwardingDesc: '进程间通信配置',
    enableIpc: '启用 IPC 转发',
    ipcHost: 'IPC 主机',
    ipcPort: 'IPC 端口',
    
    proxyConfig: '代理配置',
    proxyConfigDesc: 'SOCKS5 和 HTTP 代理',
    socks5Proxy: 'SOCKS5 代理',
    httpProxy: 'HTTP 代理',
    
    externalApiKeys: '外部数据 API',
    externalApiKeysDesc: '第三方数据源密钥',
    
    chartConfig: '图表配置',
    chartConfigDesc: 'K线图和技术指标',
    enableCharts: '启用图表',
    chartInterval: '图表周期',
    
    loggingConfig: '日志配置',
    loggingConfigDesc: '日志级别和输出',
    logLevel: '日志级别',
    logFile: '日志文件',
    
    // AI 配置
    aiSignalAnalysis: 'AI 信号简评',
    aiSignalAnalysisDesc: '每个信号的AI分析',
    aiKeyLevels: 'AI 主力位',
    aiKeyLevelsDesc: 'AI 关键价位分析',
    aiOverlays: 'AI 辅助线',
    aiOverlaysDesc: 'AI 图表辅助标注',
    aiMarketAnalysis: 'AI 市场总结',
    aiMarketAnalysisDesc: '定时市场宏观分析报告',
    
    enableModule: '启用模块',
    apiUrl: 'API 地址',
    apiKey: 'API 密钥',
    model: '模型',
    intervalHours: '间隔 (小时)',
    lookbackHours: '回溯 (小时)',
    testConnection: '测试连接',
    connectionSuccess: '连接成功',
    connectionFailed: '连接失败',
    testing: '测试中...',
    
    // 交易配置
    binanceApi: 'Binance API',
    binanceApiDesc: 'API 密钥配置',
    binanceApiKey: 'API Key',
    binanceApiSecret: 'API Secret',
    useTestnet: '使用测试网',
    
    tradingBasics: '交易基础',
    tradingBasicsDesc: '杠杆和保证金设置',
    leverage: '杠杆倍数',
    marginType: '保证金类型',
    isolated: '逐仓',
    crossed: '全仓',
    positionSide: '持仓模式',
    both: '双向',
    longOnly: '仅多',
    shortOnly: '仅空',
    
    longStrategy: '多头策略',
    longStrategyDesc: '多头交易参数',
    enableLong: '启用多头',
    
    shortStrategy: '空头策略',
    shortStrategyDesc: '空头交易参数',
    enableShort: '启用空头',
    stopLossPercent: '止损 (%)',
    takeProfitPercent: '止盈 (%)',
    
    trailingStop: '追踪止损',
    trailingStopDesc: '动态止损设置',
    enableTrailingStop: '启用追踪止损',
    activationPercent: '激活百分比',
    callbackPercent: '回调百分比',
    
    signalAggregation: '信号聚合',
    signalAggregationDesc: '信号处理规则',
    timeWindow: '时间窗口 (秒)',
    minSignalScore: '最小信号分数',
    
    riskManagement: '风险管理',
    riskManagementDesc: '仓位和风险控制',
    maxPositionPercent: '单币最大仓位 (%)',
    maxTotalPositionPercent: '总仓位上限 (%)',
    maxDailyTrades: '每日最大交易',
    maxDailyLossPercent: '每日最大亏损 (%)',
    
    notifications: '通知配置',
    notificationsDesc: 'Telegram 交易通知',
    enableNotifications: '启用通知',
    notifyOpenPosition: '开仓通知',
    notifyClosePosition: '平仓通知',
    notifyStopLoss: '止损通知',
    notifyTakeProfit: '止盈通知',
    notifyErrors: '错误通知',
    
    // 跟单配置
    telegramApi: 'Telegram API',
    telegramApiDesc: 'Telegram 客户端配置',
    apiId: 'API ID',
    apiHash: 'API Hash',
    monitorGroups: '监控群组',
    signalUsers: '信号用户',
    
    copyTradeSettings: '跟单设置',
    copyTradeSettingsDesc: '跟单模式和仓位',
    enableCopyTrade: '启用跟单',
    followClose: '跟随平仓',
    positionMode: '仓位模式',
    fixedPosition: '固定仓位',
    ratioPosition: '比例仓位',
    positionRatio: '跟单比例',
    fixedSize: '固定金额',
    
    riskControl: '风险控制',
    riskControlDesc: '跟单风险管理',
    maxSingleTradeValue: '单笔最大金额',
    
    signalFilterSettings: '信号过滤',
    signalFilterSettingsDesc: '信号筛选规则',
    minLeverage: '最小杠杆',
    maxLeverage: '最大杠杆',
    directionFilter: '方向过滤',
    bothDirections: '双向',
    longOnlyFilter: '仅多',
    shortOnlyFilter: '仅空',
    maxSignalDelay: '最大延迟 (秒)',
    
    // 服务监控配置
    globalSettings: '全局设置',
    globalSettingsDesc: '监控全局参数',
    checkInterval: '检查间隔 (秒)',
    restartCooldown: '重启冷却 (秒)',
    
    telegramNotify: 'Telegram 通知',
    telegramNotifyDesc: '服务状态通知',
    
    monitoredServices: '监控的服务',
    monitoredServicesDesc: '服务列表配置',
    displayName: '显示名称',
    noLogThreshold: '无日志阈值',
    enableService: '启用服务',
    addService: '添加服务',
    removeService: '移除服务',
    
    // 日志
    systemLogs: '运行日志',
    realtimeOutput: '系统实时输出监控',
    selectService: '选择服务',
    refreshLogs: '刷新日志',
    noLogs: '暂无日志',
    loadLogsFailed: '获取日志失败',
    
    // 登录
    valueScan: 'ValueScan',
    loggedIn: '已登录',
    notLoggedIn: '未登录',
    loginToValueScan: '登录 ValueScan',
    email: '邮箱',
    password: '密码',
    login: '登录',
    loggingIn: '登录中...',
    loginSuccess: '登录成功',
    loginFailed: '登录失败',
    cookies: 'Cookies',
    
    // 导出导入
    exportConfigTitle: '导出配置',
    exportConfigDesc: '将当前配置导出为 JSON 文件',
    export: '导出',
    importConfigTitle: '导入配置',
    importConfigDesc: '从 JSON 文件恢复配置',
    import: '导入',
    importSuccess: '配置导入成功',
    importFailed: '配置导入失败',
    
    // 轮询配置二级
    requestTimeout: '请求超时 (秒)',
    maxConsecutiveFailures: '最大连续失败次数',
    failureCooldown: '失败冷却 (秒)',
    autoRelogin: '自动重登录',
    reloginCooldown: '重登录冷却 (秒)',
    
    // 信号过滤二级
    startupSignalMaxAge: '启动时信号最大延迟 (秒)',
    runtimeSignalMaxAge: '运行时信号最大延迟 (秒)',
    
    // Token刷新器二级
    tokenRefreshInterval: '刷新间隔 (小时)',
    tokenSafetyMargin: '安全边际 (秒)',
    loginMethod: '登录方式',
    refreshWindowStart: '刷新窗口开始',
    refreshWindowEnd: '刷新窗口结束',
    
    // IPC二级
    connectTimeout: '连接超时',
    retryDelay: '重试延迟',
    ipcMaxRetries: 'IPC最大重试次数',
    
    // 图表二级
    enableProCharts: '启用专业图表',
    enableAiKeyLevels: '启用AI关键位',
    enableAiOverlays: '启用AI辅助线',
    autoDeleteCharts: '自动删除图表',
    layoutId: '布局ID',
    timeout: '超时 (秒)',
    width: '宽度',
    height: '高度',
    
    // 日志二级
    logToFile: '写入文件',
    logFilePath: '日志文件路径',
    logMaxSize: '日志最大大小 (MB)',
    logBackupCount: '日志备份数量',
    logFormat: '日志格式',
    logDateFormat: '日期格式',
    
    // AI Market Summary 二级
    enableAiMarketSummary: '启用AI市场总结',
    aiApiProxy: 'AI API 代理',
    
    // 通用
    enabled: '启用',
    disabled: '禁用',
    save: '保存',
    cancel: '取消',
    confirm: '确认',
    delete: '删除',
    edit: '编辑',
    add: '添加',
    remove: '移除',
    loading: '加载中...',
    noData: '暂无数据',
    success: '成功',
    failed: '失败',
    warning: '警告',
    info: '信息',
  },
  
  en: {
    // Navigation
    dashboard: 'Dashboard',
    systemConfig: 'Settings',
    logs: 'Logs',
    language: 'Language',
    
    // Dashboard
    systemOverview: 'System Overview',
    allServicesRunning: 'All services running normally',
    someServicesDown: 'Some services are down',
    refreshStatus: 'Refresh Status',
    quickActions: 'Quick Actions',
    editConfig: 'Edit Config',
    modifyParams: 'Modify system parameters',
    viewLogs: 'View Logs',
    monitorStatus: 'Monitor runtime status',
    exportConfig: 'Export Config',
    backupSettings: 'Backup current settings',
    importConfig: 'Import Config',
    restoreSettings: 'Restore system settings',
    
    // Services
    services: 'Services',
    signalMonitor: 'Signal Monitor',
    signalMonitorDesc: 'ValueScan signal capture',
    autoTrader: 'Auto Trader',
    autoTraderDesc: 'Binance futures trading',
    copyTrade: 'Copy Trade',
    copyTradeDesc: 'Telegram signal copy',
    serviceMonitor: 'Service Monitor',
    serviceMonitorDesc: 'Auto restart daemon',
    running: 'Running',
    stopped: 'Stopped',
    error: 'Error',
    start: 'Start',
    stop: 'Stop',
    restart: 'Restart',
    
    // Config
    manageParams: 'Manage core module parameters',
    unsaved: 'Unsaved',
    saveConfig: 'Save Config',
    configSaved: 'Configuration saved',
    serviceRestarting: 'Service restarting to apply new config',
    saveFailed: 'Save failed',
    loadFailed: 'Load failed',
    loadConfigFailed: 'Failed to load config',
    
    // Config sections
    signal: 'Signal Monitor',
    trader: 'Auto Trader',
    copytrade: 'Copy Trade',
    keepalive: 'Service Monitor',
    
    // Signal Monitor Config
    telegramConfig: 'Telegram Config',
    telegramConfigDesc: 'Configure Telegram Bot and notifications',
    enableTelegram: 'Enable Telegram notifications',
    botToken: 'Bot Token',
    chatId: 'Chat ID',
    minInterval: 'Min Interval (sec)',
    
    browserConfig: 'Browser Config',
    browserConfigDesc: 'Chrome automation settings',
    chromeHost: 'Chrome Debug Host',
    chromePort: 'Chrome Debug Port',
    headlessMode: 'Headless Mode',
    
    apiConfig: 'API Config',
    apiConfigDesc: 'Backend service endpoints',
    apiHost: 'API Host',
    apiPort: 'API Port',
    
    pollingConfig: 'Polling & Monitoring',
    pollingConfigDesc: 'Signal collection interval settings',
    pollingInterval: 'Polling Interval (sec)',
    signalTimeout: 'Signal Timeout (sec)',
    maxRetries: 'Max Retries',
    
    signalFilter: 'Signal Filter',
    signalFilterDesc: 'Filter rule configuration',
    minScore: 'Min Score',
    symbolWhitelist: 'Symbol Whitelist',
    symbolBlacklist: 'Symbol Blacklist',
    
    tokenRefresher: 'Token Refresher',
    tokenRefresherDesc: 'Auto refresh auth tokens',
    enableRefresher: 'Enable Refresher',
    refreshInterval: 'Refresh Interval (sec)',
    
    ipcForwarding: 'IPC Forwarding',
    ipcForwardingDesc: 'Inter-process communication config',
    enableIpc: 'Enable IPC Forwarding',
    ipcHost: 'IPC Host',
    ipcPort: 'IPC Port',
    
    proxyConfig: 'Proxy Config',
    proxyConfigDesc: 'SOCKS5 and HTTP proxies',
    socks5Proxy: 'SOCKS5 Proxy',
    httpProxy: 'HTTP Proxy',
    
    externalApiKeys: 'External Data API',
    externalApiKeysDesc: 'Third-party data source keys',
    
    chartConfig: 'Chart Config',
    chartConfigDesc: 'Candlestick and indicators',
    enableCharts: 'Enable Charts',
    chartInterval: 'Chart Interval',
    
    loggingConfig: 'Logging Config',
    loggingConfigDesc: 'Log level and output',
    logLevel: 'Log Level',
    logFile: 'Log File',
    
    // AI Config
    aiSignalAnalysis: 'AI Signal Analysis',
    aiSignalAnalysisDesc: 'AI analysis for each signal',
    aiKeyLevels: 'AI Key Levels',
    aiKeyLevelsDesc: 'AI key price level analysis',
    aiOverlays: 'AI Overlays',
    aiOverlaysDesc: 'AI chart overlay annotations',
    aiMarketAnalysis: 'AI Market Summary',
    aiMarketAnalysisDesc: 'Scheduled macro market reports',
    
    enableModule: 'Enable Module',
    apiUrl: 'API URL',
    apiKey: 'API Key',
    model: 'Model',
    intervalHours: 'Interval (hours)',
    lookbackHours: 'Lookback (hours)',
    testConnection: 'Test Connection',
    connectionSuccess: 'Connection successful',
    connectionFailed: 'Connection failed',
    testing: 'Testing...',
    
    // Trading Config
    binanceApi: 'Binance API',
    binanceApiDesc: 'API key configuration',
    binanceApiKey: 'API Key',
    binanceApiSecret: 'API Secret',
    useTestnet: 'Use Testnet',
    
    tradingBasics: 'Trading Basics',
    tradingBasicsDesc: 'Leverage and margin settings',
    leverage: 'Leverage',
    marginType: 'Margin Type',
    isolated: 'Isolated',
    crossed: 'Cross',
    positionSide: 'Position Side',
    both: 'Both',
    longOnly: 'Long Only',
    shortOnly: 'Short Only',
    
    longStrategy: 'Long Strategy',
    longStrategyDesc: 'Long trading parameters',
    enableLong: 'Enable Long',
    
    shortStrategy: 'Short Strategy',
    shortStrategyDesc: 'Short trading parameters',
    enableShort: 'Enable Short',
    stopLossPercent: 'Stop Loss (%)',
    takeProfitPercent: 'Take Profit (%)',
    
    trailingStop: 'Trailing Stop',
    trailingStopDesc: 'Dynamic stop loss settings',
    enableTrailingStop: 'Enable Trailing Stop',
    activationPercent: 'Activation %',
    callbackPercent: 'Callback %',
    
    signalAggregation: 'Signal Aggregation',
    signalAggregationDesc: 'Signal processing rules',
    timeWindow: 'Time Window (sec)',
    minSignalScore: 'Min Signal Score',
    
    riskManagement: 'Risk Management',
    riskManagementDesc: 'Position and risk control',
    maxPositionPercent: 'Max Position (%)',
    maxTotalPositionPercent: 'Max Total Position (%)',
    maxDailyTrades: 'Max Daily Trades',
    maxDailyLossPercent: 'Max Daily Loss (%)',
    
    notifications: 'Notifications',
    notificationsDesc: 'Telegram trade notifications',
    enableNotifications: 'Enable Notifications',
    notifyOpenPosition: 'Open Position',
    notifyClosePosition: 'Close Position',
    notifyStopLoss: 'Stop Loss',
    notifyTakeProfit: 'Take Profit',
    notifyErrors: 'Errors',
    
    // Copy Trade Config
    telegramApi: 'Telegram API',
    telegramApiDesc: 'Telegram client configuration',
    apiId: 'API ID',
    apiHash: 'API Hash',
    monitorGroups: 'Monitor Groups',
    signalUsers: 'Signal Users',
    
    copyTradeSettings: 'Copy Trade Settings',
    copyTradeSettingsDesc: 'Copy mode and position',
    enableCopyTrade: 'Enable Copy Trade',
    followClose: 'Follow Close',
    positionMode: 'Position Mode',
    fixedPosition: 'Fixed',
    ratioPosition: 'Ratio',
    positionRatio: 'Position Ratio',
    fixedSize: 'Fixed Size',
    
    riskControl: 'Risk Control',
    riskControlDesc: 'Copy trade risk management',
    maxSingleTradeValue: 'Max Single Trade',
    
    signalFilterSettings: 'Signal Filter',
    signalFilterSettingsDesc: 'Signal filtering rules',
    minLeverage: 'Min Leverage',
    maxLeverage: 'Max Leverage',
    directionFilter: 'Direction Filter',
    bothDirections: 'Both',
    longOnlyFilter: 'Long Only',
    shortOnlyFilter: 'Short Only',
    maxSignalDelay: 'Max Delay (sec)',
    
    // Keepalive Config
    globalSettings: 'Global Settings',
    globalSettingsDesc: 'Monitor global parameters',
    checkInterval: 'Check Interval (sec)',
    restartCooldown: 'Restart Cooldown (sec)',
    
    telegramNotify: 'Telegram Notify',
    telegramNotifyDesc: 'Service status notifications',
    
    monitoredServices: 'Monitored Services',
    monitoredServicesDesc: 'Service list configuration',
    displayName: 'Display Name',
    noLogThreshold: 'No Log Threshold',
    enableService: 'Enable Service',
    addService: 'Add Service',
    removeService: 'Remove Service',
    
    // Logs
    systemLogs: 'System Logs',
    realtimeOutput: 'Real-time system output monitoring',
    selectService: 'Select Service',
    refreshLogs: 'Refresh Logs',
    noLogs: 'No logs',
    loadLogsFailed: 'Failed to load logs',
    
    // Login
    valueScan: 'ValueScan',
    loggedIn: 'Logged In',
    notLoggedIn: 'Not Logged In',
    loginToValueScan: 'Login to ValueScan',
    email: 'Email',
    password: 'Password',
    login: 'Login',
    loggingIn: 'Logging in...',
    loginSuccess: 'Login successful',
    loginFailed: 'Login failed',
    cookies: 'Cookies',
    
    // Export/Import
    exportConfigTitle: 'Export Config',
    exportConfigDesc: 'Export current config as JSON file',
    export: 'Export',
    importConfigTitle: 'Import Config',
    importConfigDesc: 'Restore config from JSON file',
    import: 'Import',
    importSuccess: 'Config imported successfully',
    importFailed: 'Config import failed',
    
    // Polling secondary
    requestTimeout: 'Request Timeout (sec)',
    maxConsecutiveFailures: 'Max Consecutive Failures',
    failureCooldown: 'Failure Cooldown (sec)',
    autoRelogin: 'Auto Relogin',
    reloginCooldown: 'Relogin Cooldown (sec)',
    
    // Signal Filter secondary
    startupSignalMaxAge: 'Startup Signal Max Age (sec)',
    runtimeSignalMaxAge: 'Runtime Signal Max Age (sec)',
    
    // Token Refresher secondary
    tokenRefreshInterval: 'Refresh Interval (hours)',
    tokenSafetyMargin: 'Safety Margin (sec)',
    loginMethod: 'Login Method',
    refreshWindowStart: 'Refresh Window Start',
    refreshWindowEnd: 'Refresh Window End',
    
    // IPC secondary
    connectTimeout: 'Connect Timeout',
    retryDelay: 'Retry Delay',
    ipcMaxRetries: 'IPC Max Retries',
    
    // Charts secondary
    enableProCharts: 'Enable Pro Charts',
    enableAiKeyLevels: 'Enable AI Key Levels',
    enableAiOverlays: 'Enable AI Overlays',
    autoDeleteCharts: 'Auto Delete Charts',
    layoutId: 'Layout ID',
    timeout: 'Timeout (sec)',
    width: 'Width',
    height: 'Height',
    
    // Logging secondary
    logToFile: 'Log to File',
    logFilePath: 'Log File Path',
    logMaxSize: 'Log Max Size (MB)',
    logBackupCount: 'Log Backup Count',
    logFormat: 'Log Format',
    logDateFormat: 'Date Format',
    
    // AI Market Summary secondary
    enableAiMarketSummary: 'Enable AI Market Summary',
    aiApiProxy: 'AI API Proxy',
    
    // Common
    enabled: 'Enabled',
    disabled: 'Disabled',
    save: 'Save',
    cancel: 'Cancel',
    confirm: 'Confirm',
    delete: 'Delete',
    edit: 'Edit',
    add: 'Add',
    remove: 'Remove',
    loading: 'Loading...',
    noData: 'No data',
    success: 'Success',
    failed: 'Failed',
    warning: 'Warning',
    info: 'Info',
  },
}

export type TranslationKey = keyof typeof translations.zh

export function t(language: Language, key: TranslationKey): string {
  return translations[language][key] || translations.zh[key] || key
}
