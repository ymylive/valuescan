import type {
  SystemStatus,
  AccountInfo,
  Position,
  DecisionRecord,
  Statistics,
  TraderInfo,
  TraderConfigData,
  AIModel,
  Exchange,
  CreateTraderRequest,
  CreateExchangeRequest,
  UpdateModelConfigRequest,
  UpdateExchangeConfigRequest,
  CompetitionData,
  BacktestRunsResponse,
  BacktestStartConfig,
  BacktestStatusPayload,
  BacktestEquityPoint,
  BacktestTradeEvent,
  BacktestMetrics,
  BacktestRunMetadata,
  Strategy,
  StrategyConfig,
  DebateSession,
  DebateSessionWithDetails,
  CreateDebateRequest,
  DebateMessage,
  DebateVote,
  DebatePersonalityInfo,
} from '../types'
import { CryptoService } from './crypto'
import { httpClient } from './httpClient'
import { withBasePath } from './appBase'

const API_BASE = withBasePath('/api')

// Helper function to get auth headers
function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('auth_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  return headers
}

async function handleJSONResponse<T>(res: Response): Promise<T> {
  const text = await res.text()
  if (!res.ok) {
    let message = text || res.statusText
    try {
      const data = text ? JSON.parse(text) : null
      if (data && typeof data === 'object') {
        message = data.error || data.message || message
      }
    } catch {
      /* ignore JSON parse errors */
    }
    throw new Error(message || '请求失败')
  }
  if (!text) {
    return {} as T
  }
  return JSON.parse(text) as T
}

export const api = {
  // AI交易员管理接口
  async getTraders(): Promise<TraderInfo[]> {
    const result = await httpClient.get<TraderInfo[]>(`${API_BASE}/my-traders`)
    if (!result.success) throw new Error('获取trader列表失败')
    return Array.isArray(result.data) ? result.data : []
  },

  // 获取公开的交易员列表（无需认证）
  async getPublicTraders(): Promise<any[]> {
    const result = await httpClient.get<any[]>(`${API_BASE}/traders`)
    if (!result.success) throw new Error('获取公开trader列表失败')
    return result.data!
  },

  async createTrader(request: CreateTraderRequest): Promise<TraderInfo> {
    const result = await httpClient.post<TraderInfo>(
      `${API_BASE}/traders`,
      request
    )
    if (!result.success) throw new Error('创建交易员失败')
    return result.data!
  },

  async deleteTrader(traderId: string): Promise<void> {
    const result = await httpClient.delete(`${API_BASE}/traders/${traderId}`)
    if (!result.success) throw new Error('删除交易员失败')
  },

  async startTrader(traderId: string): Promise<void> {
    const result = await httpClient.post(
      `${API_BASE}/traders/${traderId}/start`
    )
    if (!result.success) throw new Error('启动交易员失败')
  },

  async stopTrader(traderId: string): Promise<void> {
    const result = await httpClient.post(`${API_BASE}/traders/${traderId}/stop`)
    if (!result.success) throw new Error('停止交易员失败')
  },

  async toggleCompetition(
    traderId: string,
    showInCompetition: boolean
  ): Promise<void> {
    const result = await httpClient.put(
      `${API_BASE}/traders/${traderId}/competition`,
      { show_in_competition: showInCompetition }
    )
    if (!result.success) throw new Error('更新竞技场显示设置失败')
  },

  async closePosition(
    traderId: string,
    symbol: string,
    side: string
  ): Promise<{ message: string }> {
    const result = await httpClient.post<{ message: string }>(
      `${API_BASE}/traders/${traderId}/close-position`,
      { symbol, side }
    )
    if (!result.success) throw new Error('平仓失败')
    return result.data!
  },

  async updateTraderPrompt(
    traderId: string,
    customPrompt: string
  ): Promise<void> {
    const result = await httpClient.put(
      `${API_BASE}/traders/${traderId}/prompt`,
      { custom_prompt: customPrompt }
    )
    if (!result.success) throw new Error('更新自定义策略失败')
  },

  async getTraderConfig(traderId: string): Promise<TraderConfigData> {
    const result = await httpClient.get<TraderConfigData>(
      `${API_BASE}/traders/${traderId}/config`
    )
    if (!result.success) throw new Error('获取交易员配置失败')
    return result.data!
  },

  async updateTrader(
    traderId: string,
    request: CreateTraderRequest
  ): Promise<TraderInfo> {
    const result = await httpClient.put<TraderInfo>(
      `${API_BASE}/traders/${traderId}`,
      request
    )
    if (!result.success) throw new Error('更新交易员失败')
    return result.data!
  },

  // AI模型配置接口
  async getModelConfigs(): Promise<AIModel[]> {
    const result = await httpClient.get<AIModel[]>(`${API_BASE}/models`)
    if (!result.success) throw new Error('获取模型配置失败')
    return Array.isArray(result.data) ? result.data : []
  },

  // 获取系统支持的AI模型列表（无需认证）
  async getSupportedModels(): Promise<AIModel[]> {
    const result = await httpClient.get<AIModel[]>(
      `${API_BASE}/supported-models`
    )
    if (!result.success) throw new Error('获取支持的模型失败')
    return result.data!
  },

  async getPromptTemplates(): Promise<string[]> {
    const res = await fetch(`${API_BASE}/prompt-templates`)
    if (!res.ok) throw new Error('获取提示词模板失败')
    const data = await res.json()
    if (Array.isArray(data.templates)) {
      return data.templates.map((item: { name: string }) => item.name)
    }
    return []
  },

  async updateModelConfigs(request: UpdateModelConfigRequest): Promise<void> {
    // 检查是否启用了传输加密
    const config = await CryptoService.fetchCryptoConfig()

    if (!config.transport_encryption) {
      // 传输加密禁用时，直接发送明文
      const result = await httpClient.put(`${API_BASE}/models`, request)
      if (!result.success) throw new Error('更新模型配置失败')
      return
    }

    // 获取RSA公钥
    const publicKey = await CryptoService.fetchPublicKey()

    // 初始化加密服务
    await CryptoService.initialize(publicKey)

    // 获取用户信息（从localStorage或其他地方）
    const userId = localStorage.getItem('user_id') || ''
    const sessionId = sessionStorage.getItem('session_id') || ''

    // 加密敏感数据
    const encryptedPayload = await CryptoService.encryptSensitiveData(
      JSON.stringify(request),
      userId,
      sessionId
    )

    // 发送加密数据
    const result = await httpClient.put(`${API_BASE}/models`, encryptedPayload)
    if (!result.success) throw new Error('更新模型配置失败')
  },

  // 交易所配置接口
  async getExchangeConfigs(): Promise<Exchange[]> {
    const result = await httpClient.get<Exchange[]>(`${API_BASE}/exchanges`)
    if (!result.success) throw new Error('获取交易所配置失败')
    return result.data!
  },

  // 获取系统支持的交易所列表（无需认证）
  async getSupportedExchanges(): Promise<Exchange[]> {
    const result = await httpClient.get<Exchange[]>(
      `${API_BASE}/supported-exchanges`
    )
    if (!result.success) throw new Error('获取支持的交易所失败')
    return result.data!
  },

  async updateExchangeConfigs(
    request: UpdateExchangeConfigRequest
  ): Promise<void> {
    const result = await httpClient.put(`${API_BASE}/exchanges`, request)
    if (!result.success) throw new Error('更新交易所配置失败')
  },

  // 创建新的交易所账户
  async createExchange(
    request: CreateExchangeRequest
  ): Promise<{ id: string }> {
    const result = await httpClient.post<{ id: string }>(
      `${API_BASE}/exchanges`,
      request
    )
    if (!result.success) throw new Error('创建交易所账户失败')
    return result.data!
  },

  // 创建新的交易所账户（加密传输）
  async createExchangeEncrypted(
    request: CreateExchangeRequest
  ): Promise<{ id: string }> {
    // 检查是否启用了传输加密
    const config = await CryptoService.fetchCryptoConfig()

    if (!config.transport_encryption) {
      // 传输加密禁用时，直接发送明文
      const result = await httpClient.post<{ id: string }>(
        `${API_BASE}/exchanges`,
        request
      )
      if (!result.success) throw new Error('创建交易所账户失败')
      return result.data!
    }

    // 获取RSA公钥
    const publicKey = await CryptoService.fetchPublicKey()

    // 初始化加密服务
    await CryptoService.initialize(publicKey)

    // 获取用户信息
    const userId = localStorage.getItem('user_id') || ''
    const sessionId = sessionStorage.getItem('session_id') || ''

    // 加密敏感数据
    const encryptedPayload = await CryptoService.encryptSensitiveData(
      JSON.stringify(request),
      userId,
      sessionId
    )

    // 发送加密数据
    const result = await httpClient.post<{ id: string }>(
      `${API_BASE}/exchanges`,
      encryptedPayload
    )
    if (!result.success) throw new Error('创建交易所账户失败')
    return result.data!
  },

  // 删除交易所账户
  async deleteExchange(exchangeId: string): Promise<void> {
    const result = await httpClient.delete(
      `${API_BASE}/exchanges/${exchangeId}`
    )
    if (!result.success) throw new Error('删除交易所账户失败')
  },

  // 使用加密传输更新交易所配置（自动检测是否启用加密）
  async updateExchangeConfigsEncrypted(
    request: UpdateExchangeConfigRequest
  ): Promise<void> {
    // 检查是否启用了传输加密
    const config = await CryptoService.fetchCryptoConfig()

    if (!config.transport_encryption) {
      // 传输加密禁用时，直接发送明文
      const result = await httpClient.put(`${API_BASE}/exchanges`, request)
      if (!result.success) throw new Error('更新交易所配置失败')
      return
    }

    // 获取RSA公钥
    const publicKey = await CryptoService.fetchPublicKey()

    // 初始化加密服务
    await CryptoService.initialize(publicKey)

    // 获取用户信息（从localStorage或其他地方）
    const userId = localStorage.getItem('user_id') || ''
    const sessionId = sessionStorage.getItem('session_id') || ''

    // 加密敏感数据
    const encryptedPayload = await CryptoService.encryptSensitiveData(
      JSON.stringify(request),
      userId,
      sessionId
    )

    // 发送加密数据
    const result = await httpClient.put(
      `${API_BASE}/exchanges`,
      encryptedPayload
    )
    if (!result.success) throw new Error('更新交易所配置失败')
  },

  // 获取系统状态（支持trader_id）
  async getStatus(traderId?: string): Promise<SystemStatus> {
    const url = traderId
      ? `${API_BASE}/status?trader_id=${traderId}`
      : `${API_BASE}/status`
    const result = await httpClient.get<SystemStatus>(url)
    if (!result.success) throw new Error('获取系统状态失败')
    return result.data!
  },

  // 获取账户信息（支持trader_id）
  async getAccount(traderId?: string): Promise<AccountInfo> {
    const url = traderId
      ? `${API_BASE}/account?trader_id=${traderId}`
      : `${API_BASE}/account`
    const result = await httpClient.get<AccountInfo>(url)
    if (!result.success) throw new Error('获取账户信息失败')
    console.log('Account data fetched:', result.data)
    return result.data!
  },

  // 获取持仓列表（支持trader_id）
  async getPositions(traderId?: string): Promise<Position[]> {
    const url = traderId
      ? `${API_BASE}/positions?trader_id=${traderId}`
      : `${API_BASE}/positions`
    const result = await httpClient.get<Position[]>(url)
    if (!result.success) throw new Error('获取持仓列表失败')
    return result.data!
  },

  // 获取决策日志（支持trader_id）
  async getDecisions(traderId?: string): Promise<DecisionRecord[]> {
    const url = traderId
      ? `${API_BASE}/decisions?trader_id=${traderId}`
      : `${API_BASE}/decisions`
    const result = await httpClient.get<DecisionRecord[]>(url)
    if (!result.success) throw new Error('获取决策日志失败')
    return result.data!
  },

  // 获取最新决策（支持trader_id和limit参数）
  async getLatestDecisions(
    traderId?: string,
    limit: number = 5
  ): Promise<DecisionRecord[]> {
    const params = new URLSearchParams()
    if (traderId) {
      params.append('trader_id', traderId)
    }
    params.append('limit', limit.toString())

    const result = await httpClient.get<DecisionRecord[]>(
      `${API_BASE}/decisions/latest?${params}`
    )
    if (!result.success) throw new Error('获取最新决策失败')
    return result.data!
  },

  // 获取统计信息（支持trader_id）
  async getStatistics(traderId?: string): Promise<Statistics> {
    const url = traderId
      ? `${API_BASE}/statistics?trader_id=${traderId}`
      : `${API_BASE}/statistics`
    const result = await httpClient.get<Statistics>(url)
    if (!result.success) throw new Error('获取统计信息失败')
    return result.data!
  },

  // 获取收益率历史数据（支持trader_id）
  async getEquityHistory(traderId?: string): Promise<any[]> {
    const url = traderId
      ? `${API_BASE}/equity-history?trader_id=${traderId}`
      : `${API_BASE}/equity-history`
    const result = await httpClient.get<any[]>(url)
    if (!result.success) throw new Error('获取历史数据失败')
    return result.data!
  },

  // 批量获取多个交易员的历史数据（无需认证）
  async getEquityHistoryBatch(traderIds: string[]): Promise<any> {
    const result = await httpClient.post<any>(
      `${API_BASE}/equity-history-batch`,
      { trader_ids: traderIds }
    )
    if (!result.success) throw new Error('获取批量历史数据失败')
    return result.data!
  },

  // 获取前5名交易员数据（无需认证）
  async getTopTraders(): Promise<any[]> {
    const result = await httpClient.get<any[]>(`${API_BASE}/top-traders`)
    if (!result.success) throw new Error('获取前5名交易员失败')
    return result.data!
  },

  // 获取公开交易员配置（无需认证）
  async getPublicTraderConfig(traderId: string): Promise<any> {
    const result = await httpClient.get<any>(
      `${API_BASE}/trader/${traderId}/config`
    )
    if (!result.success) throw new Error('获取公开交易员配置失败')
    return result.data!
  },

  // 获取竞赛数据（无需认证）
  async getCompetition(): Promise<CompetitionData> {
    const result = await httpClient.get<CompetitionData>(
      `${API_BASE}/competition`
    )
    if (!result.success) throw new Error('获取竞赛数据失败')
    return result.data!
  },

  // 获取服务器IP（需要认证，用于白名单配置）
  async getServerIP(): Promise<{
    public_ip: string
    message: string
  }> {
    const result = await httpClient.get<{
      public_ip: string
      message: string
    }>(`${API_BASE}/server-ip`)
    if (!result.success) throw new Error('获取服务器IP失败')
    return result.data!
  },

  // Backtest APIs
  async getBacktestRuns(params?: {
    state?: string
    search?: string
    limit?: number
    offset?: number
  }): Promise<BacktestRunsResponse> {
    const query = new URLSearchParams()
    if (params?.state) query.set('state', params.state)
    if (params?.search) query.set('search', params.search)
    if (params?.limit) query.set('limit', String(params.limit))
    if (params?.offset) query.set('offset', String(params.offset))
    const res = await fetch(
      `${API_BASE}/backtest/runs${query.toString() ? `?${query}` : ''}`,
      {
        headers: getAuthHeaders(),
      }
    )
    return handleJSONResponse<BacktestRunsResponse>(res)
  },

  async startBacktest(
    config: BacktestStartConfig
  ): Promise<BacktestRunMetadata> {
    const res = await fetch(`${API_BASE}/backtest/start`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ config }),
    })
    return handleJSONResponse<BacktestRunMetadata>(res)
  },

  async pauseBacktest(runId: string): Promise<BacktestRunMetadata> {
    const res = await fetch(`${API_BASE}/backtest/pause`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ run_id: runId }),
    })
    return handleJSONResponse<BacktestRunMetadata>(res)
  },

  async resumeBacktest(runId: string): Promise<BacktestRunMetadata> {
    const res = await fetch(`${API_BASE}/backtest/resume`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ run_id: runId }),
    })
    return handleJSONResponse<BacktestRunMetadata>(res)
  },

  async stopBacktest(runId: string): Promise<BacktestRunMetadata> {
    const res = await fetch(`${API_BASE}/backtest/stop`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ run_id: runId }),
    })
    return handleJSONResponse<BacktestRunMetadata>(res)
  },

  async updateBacktestLabel(
    runId: string,
    label: string
  ): Promise<BacktestRunMetadata> {
    const res = await fetch(`${API_BASE}/backtest/label`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ run_id: runId, label }),
    })
    return handleJSONResponse<BacktestRunMetadata>(res)
  },

  async deleteBacktestRun(runId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/backtest/delete`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ run_id: runId }),
    })
    if (!res.ok) {
      throw new Error(await res.text())
    }
  },

  async getBacktestStatus(runId: string): Promise<BacktestStatusPayload> {
    const res = await fetch(`${API_BASE}/backtest/status?run_id=${runId}`, {
      headers: getAuthHeaders(),
    })
    return handleJSONResponse<BacktestStatusPayload>(res)
  },

  async getBacktestEquity(
    runId: string,
    timeframe?: string,
    limit?: number
  ): Promise<BacktestEquityPoint[]> {
    const query = new URLSearchParams({ run_id: runId })
    if (timeframe) query.set('tf', timeframe)
    if (limit) query.set('limit', String(limit))
    const res = await fetch(`${API_BASE}/backtest/equity?${query}`, {
      headers: getAuthHeaders(),
    })
    return handleJSONResponse<BacktestEquityPoint[]>(res)
  },

  async getBacktestTrades(
    runId: string,
    limit = 200
  ): Promise<BacktestTradeEvent[]> {
    const query = new URLSearchParams({
      run_id: runId,
      limit: String(limit),
    })
    const res = await fetch(`${API_BASE}/backtest/trades?${query}`, {
      headers: getAuthHeaders(),
    })
    return handleJSONResponse<BacktestTradeEvent[]>(res)
  },

  async getBacktestMetrics(runId: string): Promise<BacktestMetrics> {
    const res = await fetch(`${API_BASE}/backtest/metrics?run_id=${runId}`, {
      headers: getAuthHeaders(),
    })
    return handleJSONResponse<BacktestMetrics>(res)
  },

  async getBacktestTrace(
    runId: string,
    cycle?: number
  ): Promise<DecisionRecord> {
    const query = new URLSearchParams({ run_id: runId })
    if (cycle) query.set('cycle', String(cycle))
    const res = await fetch(`${API_BASE}/backtest/trace?${query}`, {
      headers: getAuthHeaders(),
    })
    return handleJSONResponse<DecisionRecord>(res)
  },

  async getBacktestDecisions(
    runId: string,
    limit = 20,
    offset = 0
  ): Promise<DecisionRecord[]> {
    const query = new URLSearchParams({
      run_id: runId,
      limit: String(limit),
      offset: String(offset),
    })
    const res = await fetch(`${API_BASE}/backtest/decisions?${query}`, {
      headers: getAuthHeaders(),
    })
    return handleJSONResponse<DecisionRecord[]>(res)
  },

  async exportBacktest(runId: string): Promise<Blob> {
    const res = await fetch(`${API_BASE}/backtest/export?run_id=${runId}`, {
      headers: getAuthHeaders(),
    })
    if (!res.ok) {
      const text = await res.text()
      try {
        const data = text ? JSON.parse(text) : null
        throw new Error(
          data?.error || data?.message || text || '导出失败，请稍后再试'
        )
      } catch (err) {
        if (err instanceof Error && err.message) {
          throw err
        }
        throw new Error(text || '导出失败，请稍后再试')
      }
    }
    return res.blob()
  },

  // Strategy APIs
  async getStrategies(): Promise<Strategy[]> {
    const result = await httpClient.get<{ strategies: Strategy[] }>(
      `${API_BASE}/strategies`
    )
    if (!result.success) throw new Error('获取策略列表失败')
    const strategies = result.data?.strategies
    return Array.isArray(strategies) ? strategies : []
  },

  async getStrategy(strategyId: string): Promise<Strategy> {
    const result = await httpClient.get<Strategy>(
      `${API_BASE}/strategies/${strategyId}`
    )
    if (!result.success) throw new Error('获取策略失败')
    return result.data!
  },

  async getActiveStrategy(): Promise<Strategy> {
    const result = await httpClient.get<Strategy>(
      `${API_BASE}/strategies/active`
    )
    if (!result.success) throw new Error('获取激活策略失败')
    return result.data!
  },

  async getDefaultStrategyConfig(): Promise<StrategyConfig> {
    const result = await httpClient.get<StrategyConfig>(
      `${API_BASE}/strategies/default-config`
    )
    if (!result.success) throw new Error('获取默认策略配置失败')
    return result.data!
  },

  async createStrategy(data: {
    name: string
    description: string
    config: StrategyConfig
  }): Promise<Strategy> {
    const result = await httpClient.post<Strategy>(
      `${API_BASE}/strategies`,
      data
    )
    if (!result.success) throw new Error('创建策略失败')
    return result.data!
  },

  async updateStrategy(
    strategyId: string,
    data: {
      name?: string
      description?: string
      config?: StrategyConfig
    }
  ): Promise<Strategy> {
    const result = await httpClient.put<Strategy>(
      `${API_BASE}/strategies/${strategyId}`,
      data
    )
    if (!result.success) throw new Error('更新策略失败')
    return result.data!
  },

  async deleteStrategy(strategyId: string): Promise<void> {
    const result = await httpClient.delete(
      `${API_BASE}/strategies/${strategyId}`
    )
    if (!result.success) throw new Error('删除策略失败')
  },

  async activateStrategy(strategyId: string): Promise<Strategy> {
    const result = await httpClient.post<Strategy>(
      `${API_BASE}/strategies/${strategyId}/activate`
    )
    if (!result.success) throw new Error('激活策略失败')
    return result.data!
  },

  async duplicateStrategy(strategyId: string): Promise<Strategy> {
    const result = await httpClient.post<Strategy>(
      `${API_BASE}/strategies/${strategyId}/duplicate`
    )
    if (!result.success) throw new Error('复制策略失败')
    return result.data!
  },

  // Debate Arena APIs
  async getDebates(): Promise<DebateSession[]> {
    const result = await httpClient.get<DebateSession[]>(`${API_BASE}/debates`)
    if (!result.success) throw new Error('获取辩论列表失败')
    return Array.isArray(result.data) ? result.data : []
  },

  async getDebate(debateId: string): Promise<DebateSessionWithDetails> {
    const result = await httpClient.get<DebateSessionWithDetails>(
      `${API_BASE}/debates/${debateId}`
    )
    if (!result.success) throw new Error('获取辩论详情失败')
    return result.data!
  },

  async createDebate(
    request: CreateDebateRequest
  ): Promise<DebateSessionWithDetails> {
    const result = await httpClient.post<DebateSessionWithDetails>(
      `${API_BASE}/debates`,
      request
    )
    if (!result.success) throw new Error('创建辩论失败')
    return result.data!
  },

  async startDebate(debateId: string): Promise<void> {
    const result = await httpClient.post(
      `${API_BASE}/debates/${debateId}/start`
    )
    if (!result.success) throw new Error('启动辩论失败')
  },

  async cancelDebate(debateId: string): Promise<void> {
    const result = await httpClient.post(
      `${API_BASE}/debates/${debateId}/cancel`
    )
    if (!result.success) throw new Error('取消辩论失败')
  },

  async executeDebate(
    debateId: string,
    traderId: string
  ): Promise<DebateSessionWithDetails> {
    const result = await httpClient.post<{
      message: string
      session: DebateSessionWithDetails
    }>(`${API_BASE}/debates/${debateId}/execute`, { trader_id: traderId })
    if (!result.success) throw new Error('执行交易失败')
    return result.data!.session
  },

  async deleteDebate(debateId: string): Promise<void> {
    const result = await httpClient.delete(`${API_BASE}/debates/${debateId}`)
    if (!result.success) throw new Error('删除辩论失败')
  },

  async getDebateMessages(debateId: string): Promise<DebateMessage[]> {
    const result = await httpClient.get<DebateMessage[]>(
      `${API_BASE}/debates/${debateId}/messages`
    )
    if (!result.success) throw new Error('获取辩论消息失败')
    return result.data!
  },

  async getDebateVotes(debateId: string): Promise<DebateVote[]> {
    const result = await httpClient.get<DebateVote[]>(
      `${API_BASE}/debates/${debateId}/votes`
    )
    if (!result.success) throw new Error('获取辩论投票失败')
    return result.data!
  },

  async getDebatePersonalities(): Promise<DebatePersonalityInfo[]> {
    const result = await httpClient.get<DebatePersonalityInfo[]>(
      `${API_BASE}/debates/personalities`
    )
    if (!result.success) throw new Error('获取AI性格列表失败')
    return result.data!
  },

  // SSE stream for live debate updates
  createDebateStream(debateId: string): EventSource {
    const token = localStorage.getItem('auth_token')
    return new EventSource(
      `${API_BASE}/debates/${debateId}/stream?token=${token}`
    )
  },

  // ==================== ValueScan 特有 API ====================
  // === ValueScan Configuration API ===
  async getConfig(): Promise<any> {
    const result = await httpClient.get<any>(`${API_BASE}/config`)
    if (!result.success) throw new Error('获取配置失败')
    return result.data
  },

  async saveConfig(config: any): Promise<any> {
    const result = await httpClient.post<any>(`${API_BASE}/config`, config)
    if (!result.success) throw new Error('保存配置失败')
    return result.data
  },

  // AI Market Summary Config
  async getAISummaryConfig(): Promise<any> {
    const result = await httpClient.get<any>(`${API_BASE}/valuescan/ai-summary/config`)
    if (!result.success) throw new Error('获取 AI 总结配置失败')
    return result.data?.config || {}
  },

  async saveAISummaryConfig(config: any): Promise<any> {
    const result = await httpClient.post<any>(`${API_BASE}/valuescan/ai-summary/config`, { config })
    if (!result.success) throw new Error('保存 AI 总结配置失败')
    return result.data
  },

  async triggerAISummary(): Promise<any> {
    const result = await httpClient.post<any>(`${API_BASE}/valuescan/ai-summary/trigger`, {})
    if (!result.success) throw new Error('触发 AI 总结失败')
    return result.data
  },

  async getValueScanSignals(
    limit: number = 10
  ): Promise<{ signals: any[]; error?: string }> {
    try {
      const result = await httpClient.get<{ signals: any[]; error?: string }>(
        `${API_BASE}/signals?limit=${limit}`
      )
      return result.success
        ? { signals: result.data?.signals || [], error: result.data?.error }
        : { signals: [], error: result.message || '获取信号失败' }
    } catch {
      return { signals: [], error: '获取信号失败' }
    }
  },

  async getValueScanAlerts(
    limit: number = 10
  ): Promise<{ alerts: any[]; error?: string }> {
    try {
      const result = await httpClient.get<{ alerts: any[]; error?: string }>(
        `${API_BASE}/alerts?limit=${limit}`
      )
      return result.success
        ? { alerts: result.data?.alerts || [], error: result.data?.error }
        : { alerts: [], error: result.message || '获取警报失败' }
    } catch {
      return { alerts: [], error: '获取警报失败' }
    }
  },

  async getValueScanStatus(): Promise<{
    signal_monitor: 'running' | 'stopped' | 'error'
    trader: 'running' | 'stopped' | 'error'
    copytrade: 'running' | 'stopped' | 'error'
  }> {
    const result = await httpClient.get<{
      signal_monitor: 'running' | 'stopped' | 'error'
      trader: 'running' | 'stopped' | 'error'
      copytrade: 'running' | 'stopped' | 'error'
    }>(`${API_BASE}/valuescan/status`)
    if (!result.success || !result.data) throw new Error('获取状态失败')
    return result.data
  },

  async getValueScanLoginStatus(): Promise<{
    logged_in: boolean
    cookies_count: number
  }> {
    try {
      const result = await httpClient.get<{
        logged_in: boolean
        cookies_count: number
      }>(`${API_BASE}/valuescan/login/status`)
      return result.success
        ? result.data!
        : { logged_in: false, cookies_count: 0 }
    } catch {
      return { logged_in: false, cookies_count: 0 }
    }
  },

  async getSimulationTraders(): Promise<any[]> {
    const result = await httpClient.get<{
      success: boolean
      data?: any[]
      error?: string
    }>(`${API_BASE}/simulation/traders`)
    if (!result.success) throw new Error(result.message || '获取模拟交易者失败')

    const payload = result.data
    if (!payload?.success)
      throw new Error(payload?.error || '获取模拟交易者失败')
    return Array.isArray(payload.data) ? payload.data : []
  },

  async getSimulationPositions(traderId: string): Promise<any[]> {
    const result = await httpClient.get<{
      success: boolean
      data?: any[]
      error?: string
    }>(`${API_BASE}/simulation/traders/${traderId}/positions`)
    if (!result.success) throw new Error(result.message || '获取模拟持仓失败')

    const payload = result.data
    if (!payload?.success) throw new Error(payload?.error || '获取模拟持仓失败')
    return Array.isArray(payload.data) ? payload.data : []
  },

  async getSimulationTrades(
    traderId: string,
    limit: number = 50
  ): Promise<any[]> {
    const result = await httpClient.get<{
      success: boolean
      data?: any[]
      error?: string
    }>(`${API_BASE}/simulation/traders/${traderId}/trades`)
    if (!result.success) throw new Error(result.message || '获取模拟交易失败')

    const payload = result.data
    if (!payload?.success) throw new Error(payload?.error || '获取模拟交易失败')
    const trades = Array.isArray(payload.data) ? payload.data : []
    return trades.slice(0, Math.max(0, limit))
  },

  async getSimulationMetrics(traderId: string): Promise<any> {
    const result = await httpClient.get<{
      success: boolean
      data?: any
      error?: string
    }>(`${API_BASE}/simulation/traders/${traderId}/metrics`)
    if (!result.success) throw new Error(result.message || '获取模拟指标失败')

    const payload = result.data
    if (!payload?.success) throw new Error(payload?.error || '获取模拟指标失败')
    return payload.data
  },

  async getServiceStatus(): Promise<{
    signal_monitor: 'running' | 'stopped' | 'error'
    trader: 'running' | 'stopped' | 'error'
    copytrade: 'running' | 'stopped' | 'error'
    keepalive: 'running' | 'stopped' | 'error'
  }> {
    try {
      const result = await httpClient.get<{
        signal_monitor: 'running' | 'stopped' | 'error'
        trader: 'running' | 'stopped' | 'error'
        copytrade: 'running' | 'stopped' | 'error'
        keepalive: 'running' | 'stopped' | 'error'
      }>(`${API_BASE}/valuescan/status`)
      return result.success
        ? result.data || {
            signal_monitor: 'stopped',
            trader: 'stopped',
            copytrade: 'stopped',
            keepalive: 'stopped',
          }
        : {
            signal_monitor: 'stopped',
            trader: 'stopped',
            copytrade: 'stopped',
            keepalive: 'stopped',
          }
    } catch {
      return {
        signal_monitor: 'stopped',
        trader: 'stopped',
        copytrade: 'stopped',
        keepalive: 'stopped',
      }
    }
  },

  async controlService(
    service: 'signal' | 'trader' | 'copytrade',
    action: 'start' | 'stop' | 'restart'
  ): Promise<{ success: boolean; message?: string }> {
    const result = await httpClient.post<{
      success: boolean
      message?: string
    }>(`${API_BASE}/service/${service}/${action}`)
    return result.success
      ? result.data!
      : { success: false, message: '操作失败' }
  },

  async getValuescanLoginStatus(): Promise<{
    logged_in: boolean
    cookies_count: number
  }> {
    try {
      const result = await httpClient.get<{
        logged_in: boolean
        cookies_count: number
      }>(`${API_BASE}/valuescan/login/status`)
      return result.success
        ? result.data!
        : { logged_in: false, cookies_count: 0 }
    } catch {
      return { logged_in: false, cookies_count: 0 }
    }
  },

  async valuescanLogin(
    email: string,
    password: string
  ): Promise<{ success: boolean; message?: string; error?: string }> {
    const result = await httpClient.post<{
      success: boolean
      message?: string
      error?: string
    }>(`${API_BASE}/valuescan/login`, { email, password }, undefined, 240_000)
    return result.success
      ? result.data!
      : { success: false, error: result.message || '登录失败' }
  },

  async prepareValuescanBrowserLogin(): Promise<{
    nonce: string
    expires_in_s: number
    valuescan_login_url: string
    bookmarklet: string
    console_snippet: string
    redirect_url: string
  }> {
    const result = await httpClient.post<any>(
      `${API_BASE}/valuescan/login/browser/prepare`,
      {},
      undefined,
      30_000
    )
    if (!result.success)
      throw new Error(result.message || '无法创建 ValueScan 登录会话')
    return result.data!
  },

  async importValuescanBrowserLogin(payload: {
    nonce: string
    localstorage: Record<string, any>
    cookies?: string
    url?: string
  }): Promise<{
    success: boolean
    status?: any
    error?: string
    seen_url?: string
    available_keys?: string[]
  }> {
    try {
      const result = await httpClient.post<any>(
        `${API_BASE}/valuescan/login/browser/import`,
        payload,
        undefined,
        60_000
      )
      if (result.success) return { success: true, ...(result.data || {}) }
      return { success: false, error: result.message || '导入失败' }
    } catch (e: any) {
      const data = e?.response?.data || {}
      return {
        success: false,
        error: data.error || data.message || e?.message || '导入失败',
        seen_url: data.seen_url,
        available_keys: data.available_keys,
      }
    }
  },

  async getValuescanArtifacts(): Promise<{
    paths: {
      cookies_file: string
      localstorage_file: string
      sessionstorage_file: string
    }
    cookies: any
    localstorage: any
    sessionstorage: any
    cookies_count: number
    has_account_token: boolean
    has_refresh_token: boolean
  }> {
    const result = await httpClient.get<any>(`${API_BASE}/valuescan/artifacts`)
    if (!result.success) throw new Error('获取 ValueScan 登录数据失败')
    return result.data!
  },

  async saveValuescanArtifacts(payload: {
    cookies?: any
    localstorage?: any
    sessionstorage?: any
  }): Promise<{ success: boolean; saved?: any; errors?: string[] }> {
    const result = await httpClient.post<any>(
      `${API_BASE}/valuescan/artifacts`,
      payload
    )
    if (!result.success)
      throw new Error(result.message || '保存 ValueScan 登录数据失败')
    return result.data!
  },

  async getValuescanCoinPoolConfig(): Promise<{ config: any; path: string }> {
    const result = await httpClient.get<any>(
      `${API_BASE}/valuescan/coinpool/config`
    )
    if (!result.success) throw new Error('获取 AI 选币数据源配置失败')
    return result.data!
  },

  async saveValuescanCoinPoolConfig(config: any): Promise<{
    success: boolean
    config?: any
    errors?: string[]
    error?: string
  }> {
    const result = await httpClient.post<any>(
      `${API_BASE}/valuescan/coinpool/config`,
      { config }
    )
    if (!result.success)
      throw new Error(result.message || '保存 AI 选币数据源配置失败')
    return result.data!
  },

  async getServiceLogs(
    service: 'signal' | 'trader' | 'proxy' | 'xray',
    lines: number = 100
  ): Promise<{ logs: string }> {
    const result = await httpClient.get<{ logs: string }>(
      `${API_BASE}/logs/${service}?lines=${lines}`
    )
    if (!result.success) throw new Error('获取日志失败')
    return result.data!
  },

  // ==================== Keepalive Configuration API ====================
  async getKeepaliveConfig(): Promise<{
    success: boolean
    config?: any
    path?: string
    error?: string
  }> {
    const result = await httpClient.get<any>(`${API_BASE}/keepalive/config`)
    if (!result.success) throw new Error('获取 Keepalive 配置失败')
    return result.data!
  },

  async saveKeepaliveConfig(config: any): Promise<{
    success: boolean
    config?: any
    errors?: string[]
    error?: string
    needs_restart?: string[]
  }> {
    const result = await httpClient.post<any>(
      `${API_BASE}/keepalive/config`,
      config
    )
    if (!result.success)
      throw new Error(result.message || '保存 Keepalive 配置失败')
    return result.data!
  },

  // ==================== Config Export/Import API ====================
  async exportConfig(
    sections: string[],
    includeSensitive: boolean = false
  ): Promise<any> {
    const result = await httpClient.post<any>(`${API_BASE}/config/export`, {
      sections,
      include_sensitive: includeSensitive,
    })
    if (!result.success) throw new Error('导出配置失败')
    return result.data!
  },

  async importConfig(
    config: any
  ): Promise<{ success: boolean; errors?: string[]; merged?: any }> {
    const result = await httpClient.post<any>(
      `${API_BASE}/config/import`,
      config
    )
    if (!result.success) throw new Error(result.message || '导入配置失败')
    return result.data!
  },
}
