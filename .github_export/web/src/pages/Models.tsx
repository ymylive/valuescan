import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { GlassCard } from '../components/Common/GlassCard';
import { Button } from '../components/Common/Button';
import { Input } from '../components/Common/Input';
import api from '../services/api';
import { BrainCircuit, X, Save } from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';

interface ModelConfig {
  id: string;
  name: string;
  provider: string;
  enabled: boolean;
  customApiUrl: string;
  customModelName: string;
  useFileUpload: boolean;
  apiKey?: string; // Only for update
}

const Models: React.FC = () => {
  const { t } = useTranslation();
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Partial<ModelConfig>>({});

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    try {
      const data = await api.get<ModelConfig[]>('/models');
      // @ts-ignore
      setModels(data || []);
    } catch (error) {
      console.error('Failed to fetch models', error);
      toast.error(t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (model: ModelConfig) => {
    setEditingId(model.id);
    setEditForm({ ...model, apiKey: '' }); // Don't show existing API key
  };

  const handleSave = async (id: string) => {
    try {
      // In a real app, we would send the update to the backend
      // The backend expects a map of models, or specific update structure
      // For now, we'll just mock the success locally or try to send if we knew the exact payload structure
      // Based on API: PUT /models with UpdateModelConfigRequest
      
      const payload = {
        models: {
          [id]: {
            enabled: editForm.enabled,
            api_key: editForm.apiKey,
            custom_api_url: editForm.customApiUrl,
            custom_model_name: editForm.customModelName,
            use_file_upload: editForm.useFileUpload,
          }
        }
      };

      await api.put('/models', payload);
      
      toast.success(t('common.success'));
      setEditingId(null);
      fetchModels();
    } catch (error) {
      console.error('Failed to update model', error);
      toast.error(t('common.error'));
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-gray-500">{t('common.loading')}</div>;
  }

  return (
    <div className="space-y-6">
      <Toaster position="top-right" />
      
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <BrainCircuit className="text-green-500" />
          {t('common.models')}
        </h2>
        <Button variant="secondary" onClick={fetchModels}>Refresh</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {models.map((model) => (
          <GlassCard 
            key={model.id} 
            animate 
            className={`p-6 border-l-4 ${model.enabled ? 'border-l-green-500' : 'border-l-gray-300 dark:border-l-gray-700'}`}
          >
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg font-bold text-gray-900 dark:text-white">{model.name}</h3>
                <span className="text-xs text-gray-500 uppercase tracking-wider">{model.provider}</span>
              </div>
              <div className={`px-2 py-1 rounded text-xs font-medium ${
                model.enabled 
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
                  : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
              }`}>
                {model.enabled ? t('common.enabled') : t('common.disabled')}
              </div>
            </div>

            {editingId === model.id ? (
              <div className="space-y-4 mt-4">
                <Input 
                  label="API Key" 
                  type="password" 
                  value={editForm.apiKey || ''} 
                  onChange={(e) => setEditForm({...editForm, apiKey: e.target.value})}
                  placeholder="Enter new API Key"
                />
                <Input 
                  label="Custom API URL" 
                  value={editForm.customApiUrl || ''} 
                  onChange={(e) => setEditForm({...editForm, customApiUrl: e.target.value})}
                />
                <Input 
                  label="Custom Model Name" 
                  value={editForm.customModelName || ''} 
                  onChange={(e) => setEditForm({...editForm, customModelName: e.target.value})}
                />
                <div className="flex items-center gap-2">
                  <input 
                    type="checkbox" 
                    id={`upload-${model.id}`}
                    checked={editForm.useFileUpload || false}
                    onChange={(e) => setEditForm({...editForm, useFileUpload: e.target.checked})}
                    className="rounded text-green-500 focus:ring-green-500"
                  />
                  <label htmlFor={`upload-${model.id}`} className="text-sm text-gray-700 dark:text-gray-300">
                    Use File Upload
                  </label>
                </div>
                <div className="flex items-center gap-2">
                  <input 
                    type="checkbox" 
                    id={`enabled-${model.id}`}
                    checked={editForm.enabled || false}
                    onChange={(e) => setEditForm({...editForm, enabled: e.target.checked})}
                    className="rounded text-green-500 focus:ring-green-500"
                  />
                  <label htmlFor={`enabled-${model.id}`} className="text-sm text-gray-700 dark:text-gray-300">
                    Enable Model
                  </label>
                </div>

                <div className="flex gap-2 pt-2">
                  <Button size="sm" onClick={() => handleSave(model.id)}>
                    <Save size={16} /> {t('common.save')}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>
                    <X size={16} /> {t('common.cancel')}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="mt-4 pt-4 border-t border-gray-100 dark:border-white/5 flex justify-end">
                <Button size="sm" variant="secondary" onClick={() => handleEdit(model)}>
                  {t('common.edit')}
                </Button>
              </div>
            )}
          </GlassCard>
        ))}
      </div>
    </div>
  );
};

export default Models;