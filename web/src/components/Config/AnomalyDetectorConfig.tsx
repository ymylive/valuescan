import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassCard } from '../shared';
import { Input } from '../ui';
import {
  Activity, TrendingUp, BarChart3, BookOpen,
  Link2, Heart, Zap, Target, ChevronDown, ChevronUp, Radio
} from 'lucide-react';
import { AnomalyDetectorConfig } from '../../types/config';
import { useTranslation } from 'react-i18next';
import { parseFloatSafe, parseIntSafe } from '../../utils/number';

interface Props {
  config: AnomalyDetectorConfig;
  onChange: (config: AnomalyDetectorConfig) => void;
}

interface SectionProps {
  title: string;
  icon: React.ReactNode;
  iconColor: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

const Section: React.FC<SectionProps> = ({ title, icon, iconColor, children, defaultOpen = true }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <GlassCard className="p-4">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <span className={iconColor}>{icon}</span>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
        </div>
        <motion.span
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="text-gray-500" size={20} />
        </motion.span>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="pt-4 space-y-4">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </GlassCard>
  );
};

export const AnomalyDetectorConfigComponent: React.FC<Props> = ({ config, onChange }) => {
  const { t } = useTranslation();

  const handleChange = <K extends keyof AnomalyDetectorConfig>(
    field: K,
    value: AnomalyDetectorConfig[K]
  ) => {
    onChange({ ...config, [field]: value });
  };

  const handleSymbolsChange = (value: string) => {
    const symbols = value.split(',').map(s => s.trim().toUpperCase()).filter(Boolean);
    handleChange('symbols', symbols);
  };

  const handleWeightChange = (key: keyof AnomalyDetectorConfig['scoring_weights'], value: number) => {
    handleChange('scoring_weights', { ...config.scoring_weights, [key]: value });
  };

  const handleThresholdChange = (key: keyof AnomalyDetectorConfig['scoring_thresholds'], value: number) => {
    handleChange('scoring_thresholds', { ...config.scoring_thresholds, [key]: value });
  };

  return (
    <motion.div
      className="space-y-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* 异动数据源选择 */}
      <Section
        title={t('anomaly.sections.source')}
        icon={<Radio size={22} />}
        iconColor="text-indigo-500"
      >
        <div className="text-sm text-gray-600 dark:text-gray-300">
          {t('anomaly.source.local')}
        </div>
      </Section>

      {/* 基础设置 */}
      <Section
        title={t('anomaly.sections.basic')}
        icon={<Activity size={22} />}
        iconColor="text-blue-500"
      >
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {t('anomaly.fields.symbols')}
          </label>
          <Input
            type="text"
            value={config.symbols.join(', ')}
            onChange={(e) => handleSymbolsChange(e.target.value)}
            placeholder="BTC, ETH, SOL, BNB"
            className="w-full"
          />
          <p className="text-xs text-gray-500 mt-1">{t('anomaly.fields.symbolsHint')}</p>
        </div>
      </Section>

      {/* 量价检测 */}
      <Section
        title={t('anomaly.sections.volumePrice')}
        icon={<TrendingUp size={22} />}
        iconColor="text-green-500"
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('anomaly.fields.volSpikeThreshold')}
            </label>
            <Input
              type="number"
              value={config.vol_spike_threshold}
              onChange={(e) => handleChange('vol_spike_threshold', parseFloatSafe(e.target.value, config.vol_spike_threshold))}
              step={0.5}
              min={1}
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">{t('anomaly.fields.volSpikeHint')}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('anomaly.fields.volZscoreThreshold')}
            </label>
            <Input
              type="number"
              value={config.vol_zscore_threshold}
              onChange={(e) => handleChange('vol_zscore_threshold', parseFloatSafe(e.target.value, config.vol_zscore_threshold))}
              step={0.5}
              min={1}
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('anomaly.fields.priceChangeThreshold')}
            </label>
            <Input
              type="number"
              value={config.price_change_threshold}
              onChange={(e) => handleChange('price_change_threshold', parseFloatSafe(e.target.value, config.price_change_threshold))}
              step={0.5}
              min={0.5}
              className="w-full"
            />
          </div>
        </div>
      </Section>

      {/* 衍生品检测 */}
      <Section
        title={t('anomaly.sections.derivatives')}
        icon={<BarChart3 size={22} />}
        iconColor="text-purple-500"
        defaultOpen={false}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('anomaly.fields.fundingWarnNegative')}
            </label>
            <Input
              type="number"
              value={config.funding_warn_negative}
              onChange={(e) => handleChange('funding_warn_negative', parseFloatSafe(e.target.value, config.funding_warn_negative))}
              step={0.005}
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('anomaly.fields.fundingWarnPositive')}
            </label>
            <Input
              type="number"
              value={config.funding_warn_positive}
              onChange={(e) => handleChange('funding_warn_positive', parseFloatSafe(e.target.value, config.funding_warn_positive))}
              step={0.005}
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('anomaly.fields.fundingExtremeNegative')}
            </label>
            <Input
              type="number"
              value={config.funding_extreme_negative}
              onChange={(e) => handleChange('funding_extreme_negative', parseFloatSafe(e.target.value, config.funding_extreme_negative))}
              step={0.01}
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('anomaly.fields.fundingExtremePositive')}
            </label>
            <Input
              type="number"
              value={config.funding_extreme_positive}
              onChange={(e) => handleChange('funding_extreme_positive', parseFloatSafe(e.target.value, config.funding_extreme_positive))}
              step={0.01}
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('anomaly.fields.oiChangeWarn')}
            </label>
            <Input
              type="number"
              value={config.oi_change_warn}
              onChange={(e) => handleChange('oi_change_warn', parseFloatSafe(e.target.value, config.oi_change_warn))}
              step={0.5}
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('anomaly.fields.oiChangeExtreme')}
            </label>
            <Input
              type="number"
              value={config.oi_change_extreme}
              onChange={(e) => handleChange('oi_change_extreme', parseFloatSafe(e.target.value, config.oi_change_extreme))}
              step={0.5}
              className="w-full"
            />
          </div>
        </div>
      </Section>

      {/* 盘口分析 */}
      <Section
        title={t('anomaly.sections.orderbook')}
        icon={<BookOpen size={22} />}
        iconColor="text-orange-500"
        defaultOpen={false}
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('anomaly.fields.imbalanceThreshold')}
            </label>
            <Input
              type="number"
              value={config.imbalance_threshold}
              onChange={(e) => handleChange('imbalance_threshold', parseFloatSafe(e.target.value, config.imbalance_threshold))}
              step={0.5}
              min={1}
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">{t('anomaly.fields.imbalanceHint')}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('anomaly.fields.whaleWallUsd')}
            </label>
            <Input
              type="number"
              value={config.whale_wall_usd}
              onChange={(e) => handleChange('whale_wall_usd', parseIntSafe(e.target.value, config.whale_wall_usd))}
              step={100000}
              min={100000}
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('anomaly.fields.spreadWarn')}
            </label>
            <Input
              type="number"
              value={config.spread_warn}
              onChange={(e) => handleChange('spread_warn', parseFloatSafe(e.target.value, config.spread_warn))}
              step={0.0001}
              min={0}
              className="w-full"
            />
          </div>
        </div>
      </Section>

      {/* 相关性过滤 */}
      <Section
        title={t('anomaly.sections.correlation')}
        icon={<Link2 size={22} />}
        iconColor="text-cyan-500"
        defaultOpen={false}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('anomaly.fields.correlationWindow')}
            </label>
            <Input
              type="number"
              value={config.correlation_window_minutes}
              onChange={(e) => handleChange('correlation_window_minutes', parseIntSafe(e.target.value, config.correlation_window_minutes))}
              min={15}
              max={240}
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('anomaly.fields.independenceThreshold')}
            </label>
            <Input
              type="number"
              value={config.independence_threshold}
              onChange={(e) => handleChange('independence_threshold', parseFloatSafe(e.target.value, config.independence_threshold))}
              step={0.1}
              min={0}
              max={1}
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">{t('anomaly.fields.independenceHint')}</p>
          </div>
        </div>
      </Section>

      {/* 情绪检测 */}
      <Section
        title={t('anomaly.sections.sentiment')}
        icon={<Heart size={22} />}
        iconColor="text-red-500"
        defaultOpen={false}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('anomaly.fields.fearExtreme')}
            </label>
            <Input
              type="number"
              value={config.fear_extreme}
              onChange={(e) => handleChange('fear_extreme', parseIntSafe(e.target.value, config.fear_extreme))}
              min={0}
              max={50}
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('anomaly.fields.greedExtreme')}
            </label>
            <Input
              type="number"
              value={config.greed_extreme}
              onChange={(e) => handleChange('greed_extreme', parseIntSafe(e.target.value, config.greed_extreme))}
              min={50}
              max={100}
              className="w-full"
            />
          </div>
        </div>
      </Section>

      {/* 动态阈值 */}
      <Section
        title={t('anomaly.sections.dynamic')}
        icon={<Zap size={22} />}
        iconColor="text-yellow-500"
        defaultOpen={false}
      >
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="use_dynamic_threshold"
              checked={config.use_dynamic_threshold}
              onChange={(e) => handleChange('use_dynamic_threshold', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-yellow-600 focus:ring-yellow-500"
            />
            <label htmlFor="use_dynamic_threshold" className="text-gray-700 dark:text-gray-300 font-medium">
              {t('anomaly.fields.useDynamicThreshold')}
            </label>
          </div>

          {config.use_dynamic_threshold && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pl-8 border-l-2 border-yellow-500/30">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('anomaly.fields.zscoreThreshold')}
                </label>
                <Input
                  type="number"
                  value={config.zscore_threshold}
                  onChange={(e) => handleChange('zscore_threshold', parseFloatSafe(e.target.value, config.zscore_threshold))}
                  step={0.5}
                  min={1}
                  className="w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('anomaly.fields.atrMultiplier')}
                </label>
                <Input
                  type="number"
                  value={config.atr_multiplier}
                  onChange={(e) => handleChange('atr_multiplier', parseFloatSafe(e.target.value, config.atr_multiplier))}
                  step={0.5}
                  min={1}
                  className="w-full"
                />
              </div>
            </div>
          )}
        </div>
      </Section>

      {/* 评分系统 */}
      <Section
        title={t('anomaly.sections.scoring')}
        icon={<Target size={22} />}
        iconColor="text-indigo-500"
        defaultOpen={false}
      >
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="scoring_enabled"
              checked={config.scoring_enabled}
              onChange={(e) => handleChange('scoring_enabled', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="scoring_enabled" className="text-gray-700 dark:text-gray-300 font-medium">
              {t('anomaly.fields.scoringEnabled')}
            </label>
          </div>

          {config.scoring_enabled && (
            <div className="space-y-6 pl-8 border-l-2 border-indigo-500/30">
              {/* 权重配置 */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  {t('anomaly.fields.scoringWeights')}
                </h4>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">
                      {t('anomaly.fields.weightVolumePrice')}
                    </label>
                    <Input
                      type="number"
                      value={config.scoring_weights.volume_price}
                      onChange={(e) => handleWeightChange('volume_price', parseFloatSafe(e.target.value, config.scoring_weights.volume_price))}
                      step={0.05}
                      min={0}
                      max={1}
                      className="w-full text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">
                      {t('anomaly.fields.weightDerivatives')}
                    </label>
                    <Input
                      type="number"
                      value={config.scoring_weights.derivatives}
                      onChange={(e) => handleWeightChange('derivatives', parseFloatSafe(e.target.value, config.scoring_weights.derivatives))}
                      step={0.05}
                      min={0}
                      max={1}
                      className="w-full text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">
                      {t('anomaly.fields.weightFundFlow')}
                    </label>
                    <Input
                      type="number"
                      value={config.scoring_weights.fund_flow}
                      onChange={(e) => handleWeightChange('fund_flow', parseFloatSafe(e.target.value, config.scoring_weights.fund_flow))}
                      step={0.05}
                      min={0}
                      max={1}
                      className="w-full text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">
                      {t('anomaly.fields.weightOrderbook')}
                    </label>
                    <Input
                      type="number"
                      value={config.scoring_weights.orderbook}
                      onChange={(e) => handleWeightChange('orderbook', parseFloatSafe(e.target.value, config.scoring_weights.orderbook))}
                      step={0.05}
                      min={0}
                      max={1}
                      className="w-full text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">
                      {t('anomaly.fields.weightSentiment')}
                    </label>
                    <Input
                      type="number"
                      value={config.scoring_weights.sentiment}
                      onChange={(e) => handleWeightChange('sentiment', parseFloatSafe(e.target.value, config.scoring_weights.sentiment))}
                      step={0.05}
                      min={0}
                      max={1}
                      className="w-full text-sm"
                    />
                  </div>
                </div>
              </div>

              {/* 阈值配置 */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  {t('anomaly.fields.scoringThresholds')}
                </h4>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">
                      {t('anomaly.fields.thresholdInfo')}
                    </label>
                    <Input
                      type="number"
                      value={config.scoring_thresholds.info}
                      onChange={(e) => handleThresholdChange('info', parseIntSafe(e.target.value, config.scoring_thresholds.info))}
                      min={0}
                      max={100}
                      className="w-full text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">
                      {t('anomaly.fields.thresholdWarning')}
                    </label>
                    <Input
                      type="number"
                      value={config.scoring_thresholds.warning}
                      onChange={(e) => handleThresholdChange('warning', parseIntSafe(e.target.value, config.scoring_thresholds.warning))}
                      min={0}
                      max={100}
                      className="w-full text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">
                      {t('anomaly.fields.thresholdAlert')}
                    </label>
                    <Input
                      type="number"
                      value={config.scoring_thresholds.alert}
                      onChange={(e) => handleThresholdChange('alert', parseIntSafe(e.target.value, config.scoring_thresholds.alert))}
                      min={0}
                      max={100}
                      className="w-full text-sm"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </Section>
    </motion.div>
  );
};
