import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassCard } from '../shared';
import { Input } from '../ui';
import {
  TrendingUp, Clock, Brain, ChevronDown,
  Building2, Cpu, Bitcoin, Globe, Plus, X
} from 'lucide-react';
import { USMarketConfig } from '../../types/config';
import { useTranslation } from 'react-i18next';
import { parseIntSafe } from '../../utils/number';

interface Props {
  config: USMarketConfig;
  onChange: (config: USMarketConfig) => void;
}

interface TagInputProps {
  value: string[];
  onChange: (value: string[]) => void;
  placeholder?: string;
}

const TagInput: React.FC<TagInputProps> = ({ value, onChange, placeholder }) => {
  const [input, setInput] = useState('');

  const handleAdd = () => {
    const trimmed = input.trim().toUpperCase();
    if (trimmed && !value.includes(trimmed)) {
      onChange([...value, trimmed]);
      setInput('');
    }
  };

  const handleRemove = (tag: string) => {
    onChange(value.filter(t => t !== tag));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAdd();
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        <AnimatePresence>
          {value.map(tag => (
            <motion.span
              key={tag}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-md text-sm"
            >
              {tag}
              <button
                onClick={() => handleRemove(tag)}
                className="hover:text-red-500 transition-colors"
              >
                <X size={14} />
              </button>
            </motion.span>
          ))}
        </AnimatePresence>
      </div>
      <div className="flex gap-2">
        <Input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="flex-1"
        />
        <button
          onClick={handleAdd}
          className="px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
        >
          <Plus size={18} />
        </button>
      </div>
    </div>
  );
};

interface CategorySectionProps {
  title: string;
  hint: string;
  icon: React.ReactNode;
  iconColor: string;
  value: string[];
  onChange: (value: string[]) => void;
}

const CategorySection: React.FC<CategorySectionProps> = ({
  title, hint, icon, iconColor, value, onChange
}) => {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50"
      >
        <div className="flex items-center gap-2">
          <span className={iconColor}>{icon}</span>
          <span className="font-medium text-gray-900 dark:text-white">{title}</span>
          <span className="text-xs text-gray-500">({value.length})</span>
        </div>
        <motion.span
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="text-gray-500" size={18} />
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
            <div className="p-3 space-y-2">
              <p className="text-xs text-gray-500">{hint}</p>
              <TagInput value={value} onChange={onChange} placeholder="输入符号后按回车" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export const USMarketConfigComponent: React.FC<Props> = ({ config, onChange }) => {
  const { t } = useTranslation();

  const handleChange = <K extends keyof USMarketConfig>(
    field: K,
    value: USMarketConfig[K]
  ) => {
    onChange({ ...config, [field]: value });
  };

  const handleCategoryChange = (
    category: keyof USMarketConfig['categories'],
    value: string[]
  ) => {
    handleChange('categories', { ...config.categories, [category]: value });
  };

  return (
    <motion.div
      className="space-y-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* 基础设置 */}
      <GlassCard className="p-4">
        <div className="flex items-center gap-3 mb-4">
          <TrendingUp className="text-green-500" size={22} />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('usMarket.title')}
          </h3>
        </div>

        <p className="text-sm text-gray-500 mb-4">{t('usMarket.description')}</p>

        <div className="space-y-4">
          {/* 启用开关 */}
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="us_market_enabled"
              checked={config.enabled}
              onChange={(e) => handleChange('enabled', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-green-600 focus:ring-green-500"
            />
            <label htmlFor="us_market_enabled" className="text-gray-700 dark:text-gray-300 font-medium">
              {t('usMarket.fields.enabled')}
            </label>
          </div>

          {config.enabled && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-4 pl-8 border-l-2 border-green-500/30"
            >
              {/* 开盘后检查时间 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    <Clock size={16} />
                    {t('usMarket.fields.checkAfterOpen')}
                  </label>
                  <Input
                    type="number"
                    value={config.check_after_open_minutes}
                    onChange={(e) => handleChange('check_after_open_minutes', parseIntSafe(e.target.value, config.check_after_open_minutes))}
                    min={1}
                    max={60}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">{t('usMarket.fields.checkAfterOpenHint')}</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    {t('usMarket.fields.vixSymbol')}
                  </label>
                  <Input
                    type="text"
                    value={config.vix_symbol}
                    onChange={(e) => handleChange('vix_symbol', e.target.value)}
                    placeholder="^VIX"
                    className="w-full"
                  />
                </div>
              </div>

              {/* AI 分析开关 */}
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="ai_analysis_enabled"
                  checked={config.ai_analysis_enabled}
                  onChange={(e) => handleChange('ai_analysis_enabled', e.target.checked)}
                  className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <label htmlFor="ai_analysis_enabled" className="flex items-center gap-2 text-gray-700 dark:text-gray-300 font-medium">
                    <Brain size={16} className="text-blue-500" />
                    {t('usMarket.fields.aiAnalysisEnabled')}
                  </label>
                  <p className="text-xs text-gray-500">{t('usMarket.fields.aiAnalysisHint')}</p>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </GlassCard>

      {/* 监控标的分类 */}
      {config.enabled && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <GlassCard className="p-4">
            <div className="flex items-center gap-3 mb-4">
              <Globe className="text-purple-500" size={22} />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {t('usMarket.categories.title')}
              </h3>
            </div>

            <div className="space-y-3">
              <CategorySection
                title={t('usMarket.categories.indices')}
                hint={t('usMarket.categories.indicesHint')}
                icon={<Building2 size={18} />}
                iconColor="text-blue-500"
                value={config.categories.indices}
                onChange={(v) => handleCategoryChange('indices', v)}
              />

              <CategorySection
                title={t('usMarket.categories.tech')}
                hint={t('usMarket.categories.techHint')}
                icon={<Cpu size={18} />}
                iconColor="text-purple-500"
                value={config.categories.tech}
                onChange={(v) => handleCategoryChange('tech', v)}
              />

              <CategorySection
                title={t('usMarket.categories.cryptoStocks')}
                hint={t('usMarket.categories.cryptoStocksHint')}
                icon={<Bitcoin size={18} />}
                iconColor="text-orange-500"
                value={config.categories.crypto_stocks}
                onChange={(v) => handleCategoryChange('crypto_stocks', v)}
              />

              <CategorySection
                title={t('usMarket.categories.macro')}
                hint={t('usMarket.categories.macroHint')}
                icon={<Globe size={18} />}
                iconColor="text-green-500"
                value={config.categories.macro}
                onChange={(v) => handleCategoryChange('macro', v)}
              />
            </div>
          </GlassCard>
        </motion.div>
      )}
    </motion.div>
  );
};
