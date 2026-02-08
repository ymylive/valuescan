import api from './api';

// AI Configuration API Service
export const aiConfigApi = {
  // ==================== AI Signal Analysis (单币简评) ====================

  // Get AI Signal Analysis configuration
  getSignalConfig: async () => {
    return api.get('/valuescan/ai-signal/config');
  },

  // Save AI Signal Analysis configuration
  saveSignalConfig: async (config: {
    api_url: string;
    api_key: string;
    model: string;
    enabled: boolean;
    interval: number;
    lookback_hours: number;
  }) => {
    return api.post('/valuescan/ai-signal/config', config);
  },

  // Test AI Signal Analysis connection
  testSignalConnection: async () => {
    return api.post('/valuescan/ai-signal/test');
  },

  // ==================== AI Key Levels (主力位分析) ====================

  // Get AI Key Levels configuration
  getLevelsConfig: async () => {
    return api.get('/valuescan/ai-levels/config');
  },

  // Save AI Key Levels configuration
  saveLevelsConfig: async (config: {
    api_url: string;
    api_key: string;
    model: string;
    enabled: boolean;
  }) => {
    return api.post('/valuescan/ai-levels/config', config);
  },

  // Test AI Key Levels connection
  testLevelsConnection: async () => {
    return api.post('/valuescan/ai-levels/test');
  },

  // ==================== AI Overlays (图表叠加层) ====================

  // Get AI Overlays configuration
  getOverlaysConfig: async () => {
    return api.get('/valuescan/ai-overlays/config');
  },

  // Save AI Overlays configuration
  saveOverlaysConfig: async (config: {
    api_url: string;
    api_key: string;
    model: string;
    enabled: boolean;
  }) => {
    return api.post('/valuescan/ai-overlays/config', config);
  },

  // Test AI Overlays connection
  testOverlaysConnection: async () => {
    return api.post('/valuescan/ai-overlays/test');
  },

  // ==================== AI Market Analysis (市场宏观分析) ====================

  // Get AI Market Analysis configuration
  getMarketConfig: async () => {
    return api.get('/valuescan/ai-market/config');
  },

  // Save AI Market Analysis configuration
  saveMarketConfig: async (config: {
    api_url: string;
    api_key: string;
    model: string;
    enabled: boolean;
    interval: number;
    lookback_hours: number;
  }) => {
    return api.post('/valuescan/ai-market/config', config);
  },

  // Test AI Market Analysis connection
  testMarketConnection: async () => {
    return api.post('/valuescan/ai-market/test');
  },
};
