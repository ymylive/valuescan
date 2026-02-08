import api from './api';

// ValuScan API Service - 主力位、主力成本、排行榜等数据

export type SymbolMap = Record<string, number>;

export interface CoinDetail {
  symbol: string;
  keyword: number;
  data: {
    info?: any;
    denseAreas?: DenseAreaPoint[];
    currentDensePrice?: number;
    holdCost?: HoldCostData;
    currentHoldCost?: number;
    tradeInflow?: any;
    exchangeFlowDetail?: any;
    fundFlowHistory?: any;
    fundVolumeHistory?: any;
    holders?: any;
    chains?: any;
  };
}

export interface DenseAreaPoint {
  time: number;
  type: number;
  price: string;
}

export interface HoldCostData {
  holdingPrice: Array<{ key: string; val: string }>;
  price: Array<{ key: string; val: string }>;
  balance: Array<{ key: string; val: string }>;
}

export interface CoinRankItem {
  keyword: number;
  symbol: string;
  icon: string;
  price: string;
  percentChange24h: string;
  marketCap: string;
  cost?: string;
  deviation?: string;
}

export interface SignalItem {
  symbol: string;
  keyword: number;
  score?: number;
  grade?: number;
  icon?: string;
}

export interface WhaleFlowItem {
  symbol: string;
  keyword: number;
  tradeInflow: number;
  icon?: string;
}

export interface TokenFlowItem {
  symbol: string;
  keyword: number;
  inFlowValue: string;
  icon?: string;
}

class ValuScanApiService {
  /**
   * 获取主力位数据（图表上的绿色水平线）
   */
  async getDenseAreas(vsTokenId: string | number, days: number = 14): Promise<DenseAreaPoint[]> {
    const endTime = Date.now();
    const beginTime = endTime - days * 24 * 60 * 60 * 1000;
    
    const response = await api.post('/valuescan/token/dense-areas', {
      vsTokenId: String(vsTokenId),
      beginTime,
      endTime,
    });
    
    if (response && (response as any).code === 200) {
      return (response as any).data || [];
    }
    return [];
  }

  /**
   * 获取主力成本数据（持仓成本曲线）
   */
  async getHoldCost(keyword: number, days: number = 14): Promise<HoldCostData | null> {
    const endTime = Date.now();
    const beginTime = endTime - days * 24 * 60 * 60 * 1000;
    
    const response = await api.post('/valuescan/token/hold-cost', {
      keyword,
      begin: beginTime,
      end: endTime,
    });
    
    if (response && (response as any).code === 200) {
      return (response as any).data || null;
    }
    return null;
  }

  /**
   * 获取当前主力位价格
   */
  async getCurrentDenseAreaPrice(vsTokenId: string | number, days: number = 14): Promise<number | null> {
    const data = await this.getDenseAreas(vsTokenId, days);
    if (data && data.length > 0) {
      const lastPoint = data[data.length - 1];
      return parseFloat(lastPoint.price);
    }
    return null;
  }

  /**
   * 获取当前主力成本价格
   */
  async getCurrentHoldCost(keyword: number, days: number = 14): Promise<number | null> {
    const data = await this.getHoldCost(keyword, days);
    if (data && data.holdingPrice && data.holdingPrice.length > 0) {
      const lastPoint = data.holdingPrice[data.holdingPrice.length - 1];
      return parseFloat(lastPoint.val);
    }
    return null;
  }

  /**
   * 获取涨幅榜
   */
  async getGainers(page: number = 1, pageSize: number = 20): Promise<CoinRankItem[]> {
    const response = await api.post('/valuescan/rankings/gainers', { page, pageSize });
    if (response && (response as any).code === 200) {
      return (response as any).data?.list || [];
    }
    return [];
  }

  /**
   * 获取跌幅榜
   */
  async getLosers(page: number = 1, pageSize: number = 20): Promise<CoinRankItem[]> {
    const response = await api.post('/valuescan/rankings/losers', { page, pageSize });
    if (response && (response as any).code === 200) {
      return (response as any).data?.list || [];
    }
    return [];
  }

  /**
   * 获取主力成本排行榜
   */
  async getMainCostRank(page: number = 1, pageSize: number = 20): Promise<CoinRankItem[]> {
    const response = await api.post('/valuescan/rankings/main-cost', { page, pageSize });
    if (response && (response as any).code === 200) {
      return (response as any).data?.list || [];
    }
    return [];
  }

  /**
   * 获取机会看涨信号
   */
  async getOpportunitySignals(pageNum: number = 1, pageSize: number = 20): Promise<SignalItem[]> {
    const response = await api.post('/valuescan/signals/opportunity', { pageNum, pageSize });
    if (response && (response as any).code === 200) {
      return (response as any).data?.list || [];
    }
    return [];
  }

  /**
   * 获取风险看跌信号
   */
  async getRiskSignals(pageNum: number = 1, pageSize: number = 20): Promise<SignalItem[]> {
    const response = await api.post('/valuescan/signals/risk', { pageNum, pageSize });
    if (response && (response as any).code === 200) {
      return (response as any).data?.list || [];
    }
    return [];
  }

  /**
   * 获取主力资金流
   */
  async getWhaleFlow(
    tradeType: 1 | 2 = 1,
    timePeriod: string = 'm5',
    pageNum: number = 1,
    pageSize: number = 20
  ): Promise<WhaleFlowItem[]> {
    const response = await api.post('/valuescan/whale-flow', {
      tradeType,
      timePeriod,
      pageNum,
      pageSize,
    });
    if (response && (response as any).code === 200) {
      return (response as any).data?.list || [];
    }
    return [];
  }

  /**
   * 获取代币流向
   */
  async getTokenFlow(
    timeParticleEnum: string = 'H12',
    page: number = 1,
    pageSize: number = 20
  ): Promise<TokenFlowItem[]> {
    const response = await api.post('/valuescan/token-flow', {
      timeParticleEnum,
      page,
      pageSize,
    });
    if (response && (response as any).code === 200) {
      return (response as any).data?.list || [];
    }
    return [];
  }

  /**
   * 获取币种信息
   */
  async getTokenInfo(keyword: string | number): Promise<any> {
    const response = await api.get(`/valuescan/token/info?keyword=${keyword}`);
    if (response && (response as any).code === 200) {
      return (response as any).data || null;
    }
    return null;
  }

  /**
   * 获取币种资金流入
   */
  async getTokenFlows(keyword: string | number): Promise<any> {
    const response = await api.get(`/valuescan/token/flows?keyword=${keyword}`);
    if (response && (response as any).code === 200) {
      return (response as any).data || null;
    }
    return null;
  }

  /**
   * 获取交易所资金流明细
   */
  async getExchangeFlowDetail(keyword: string | number): Promise<any> {
    const response = await api.post('/valuescan/token/exchange-flow-detail', { keyword });
    if (response && (response as any).code === 200) {
      return (response as any).data || null;
    }
    return null;
  }

  /**
   * 获取资金流/成交额历史
   */
  async getFundHistory(payload: {
    keyword: number;
    timeParticle?: string;
    limitSize?: number;
    flow?: boolean;
    type?: number;
  }): Promise<any> {
    const response = await api.post('/valuescan/token/fund-history', payload);
    if (response && (response as any).code === 200) {
      return (response as any).data || null;
    }
    return null;
  }

  /**
   * 获取持仓地址列表
   */
  async getHolders(payload: {
    keyword: number;
    coinKey: string;
    page?: number;
    pageSize?: number;
    address?: string;
  }): Promise<any> {
    const response = await api.post('/valuescan/token/holders', payload);
    if (response && (response as any).code === 200) {
      return (response as any).data || null;
    }
    return null;
  }

  /**
   * 获取链上信息列表
   */
  async getChains(symbol: string, page: number = 1, pageSize: number = 20): Promise<any> {
    const response = await api.post('/valuescan/token/chains', { symbol, page, pageSize });
    if (response && (response as any).code === 200) {
      return (response as any).data || null;
    }
    return null;
  }

  // ===== 币种映射相关 =====

  private symbolMapCache: SymbolMap | null = null;

  /**
   * 获取币种符号到ID的映射表
   */
  async getSymbolMap(): Promise<SymbolMap> {
    if (this.symbolMapCache) {
      return this.symbolMapCache;
    }
    
    const response = await api.get('/valuescan/symbol-map');
    if (response && (response as any).code === 200) {
      this.symbolMapCache = (response as any).data || {};
      return this.symbolMapCache!;
    }
    return {};
  }

  /**
   * 通过币种符号获取keyword (ID)
   */
  async getKeywordBySymbol(symbol: string): Promise<number | null> {
    const map = await this.getSymbolMap();
    return map[symbol.toUpperCase()] || null;
  }

  /**
   * 通过币种符号获取完整详情数据
   */
  async getCoinDetailBySymbol(symbol: string, days: number = 90): Promise<CoinDetail | null> {
    const response = await api.get(`/valuescan/coin-detail?symbol=${symbol.toUpperCase()}&days=${days}`);
    if (response && (response as any).code === 200) {
      return response as unknown as CoinDetail;
    }
    return null;
  }

  /**
   * 通过keyword获取完整详情数据
   */
  async getCoinDetailByKeyword(keyword: number, days: number = 90): Promise<CoinDetail | null> {
    const response = await api.get(`/valuescan/coin-detail?keyword=${keyword}&days=${days}`);
    if (response && (response as any).code === 200) {
      return response as unknown as CoinDetail;
    }
    return null;
  }

  /**
   * 清除本地缓存
   */
  clearCache(): void {
    this.symbolMapCache = null;
  }
}

export const valuescanApi = new ValuScanApiService();
export default valuescanApi;
