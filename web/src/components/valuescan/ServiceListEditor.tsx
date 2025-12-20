import { useState } from 'react'
import { Plus, Trash2, Power, PowerOff, Edit2, Check, X } from 'lucide-react'
import type { KeepaliveServiceConfig } from '../../types/config'

interface ServiceListEditorProps {
  services: KeepaliveServiceConfig[]
  onChange: (services: KeepaliveServiceConfig[]) => void
  onAddService?: () => void
  onRemoveService?: (index: number) => void
}

const DEFAULT_SERVICE: KeepaliveServiceConfig = {
  name: '',
  display_name: '',
  check_interval: 60,
  restart_cooldown: 300,
  no_log_threshold: null,
  enabled: true,
}

const inputClass =
  'w-full px-3 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-white text-sm focus:outline-none focus:border-neutral-600 transition-colors'

export function ServiceListEditor({
  services,
  onChange,
  onAddService,
  onRemoveService,
}: ServiceListEditorProps) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [editForm, setEditForm] =
    useState<KeepaliveServiceConfig>(DEFAULT_SERVICE)
  const [showAddForm, setShowAddForm] = useState(false)
  const [newService, setNewService] =
    useState<KeepaliveServiceConfig>(DEFAULT_SERVICE)

  const handleToggleEnabled = (index: number) => {
    const updated = [...services]
    updated[index] = { ...updated[index], enabled: !updated[index].enabled }
    onChange(updated)
  }

  const handleRemove = (index: number) => {
    if (onRemoveService) {
      onRemoveService(index)
    } else {
      const updated = services.filter((_, i) => i !== index)
      onChange(updated)
    }
  }

  const handleStartEdit = (index: number) => {
    setEditingIndex(index)
    setEditForm({ ...services[index] })
  }

  const handleCancelEdit = () => {
    setEditingIndex(null)
    setEditForm(DEFAULT_SERVICE)
  }

  const handleSaveEdit = () => {
    if (editingIndex === null) return
    const updated = [...services]
    updated[editingIndex] = editForm
    onChange(updated)
    setEditingIndex(null)
    setEditForm(DEFAULT_SERVICE)
  }

  const handleAddService = () => {
    if (!newService.name.trim() || !newService.display_name.trim()) return
    if (onAddService) {
      onAddService()
    }
    onChange([...services, newService])
    setNewService(DEFAULT_SERVICE)
    setShowAddForm(false)
  }

  const handleCancelAdd = () => {
    setShowAddForm(false)
    setNewService(DEFAULT_SERVICE)
  }

  return (
    <div className="space-y-3">
      {/* Service List */}
      {services.map((service, index) => (
        <div
          key={index}
          className={`bg-neutral-900 border rounded-lg p-4 ${
            service.enabled
              ? 'border-neutral-800'
              : 'border-neutral-800/50 opacity-60'
          }`}
        >
          {editingIndex === index ? (
            /* Edit Mode */
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-neutral-400 mb-1">
                    服务名称
                  </label>
                  <input
                    type="text"
                    value={editForm.name}
                    onChange={(e) =>
                      setEditForm({ ...editForm, name: e.target.value })
                    }
                    className={inputClass}
                    placeholder="valuescan-signal"
                  />
                </div>
                <div>
                  <label className="block text-xs text-neutral-400 mb-1">
                    显示名称
                  </label>
                  <input
                    type="text"
                    value={editForm.display_name}
                    onChange={(e) =>
                      setEditForm({ ...editForm, display_name: e.target.value })
                    }
                    className={inputClass}
                    placeholder="信号监控"
                  />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs text-neutral-400 mb-1">
                    检查间隔 (秒)
                  </label>
                  <input
                    type="number"
                    min={10}
                    max={300}
                    value={editForm.check_interval || 60}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        check_interval: parseInt(e.target.value) || 60,
                      })
                    }
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className="block text-xs text-neutral-400 mb-1">
                    重启冷却 (秒)
                  </label>
                  <input
                    type="number"
                    min={60}
                    value={editForm.restart_cooldown || 300}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        restart_cooldown: parseInt(e.target.value) || 300,
                      })
                    }
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className="block text-xs text-neutral-400 mb-1">
                    无日志阈值 (秒)
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={editForm.no_log_threshold ?? ''}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        no_log_threshold: e.target.value
                          ? parseInt(e.target.value)
                          : null,
                      })
                    }
                    className={inputClass}
                    placeholder="留空禁用"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <button
                  onClick={handleCancelEdit}
                  className="px-3 py-1.5 text-sm text-neutral-400 hover:text-white transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
                <button
                  onClick={handleSaveEdit}
                  className="px-3 py-1.5 text-sm text-white hover:text-neutral-300 transition-colors"
                >
                  <Check className="w-4 h-4" />
                </button>
              </div>
            </div>
          ) : (
            /* View Mode */
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => handleToggleEnabled(index)}
                  className={`p-1.5 rounded transition-colors ${
                    service.enabled
                      ? 'text-green-500 hover:bg-green-500/10'
                      : 'text-neutral-500 hover:bg-neutral-500/10'
                  }`}
                  title={service.enabled ? '点击禁用' : '点击启用'}
                >
                  {service.enabled ? (
                    <Power className="w-4 h-4" />
                  ) : (
                    <PowerOff className="w-4 h-4" />
                  )}
                </button>
                <div>
                  <div className="text-sm font-medium text-white">
                    {service.display_name}
                  </div>
                  <div className="text-xs text-neutral-500">{service.name}</div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-xs text-neutral-400">
                  检查: {service.check_interval || 60}s | 冷却:{' '}
                  {service.restart_cooldown || 300}s
                  {service.no_log_threshold &&
                    ` | 无日志: ${service.no_log_threshold}s`}
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleStartEdit(index)}
                    className="p-1.5 text-neutral-400 hover:text-white hover:bg-neutral-800 rounded transition-colors"
                    title="编辑"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleRemove(index)}
                    className="p-1.5 text-neutral-400 hover:text-red-500 hover:bg-red-500/10 rounded transition-colors"
                    title="删除"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      ))}

      {/* Add Service Form */}
      {showAddForm ? (
        <div className="bg-neutral-900 border border-white/20 rounded-lg p-4 space-y-3">
          <div className="text-sm font-medium text-white mb-2">添加新服务</div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-neutral-400 mb-1">
                服务名称 (systemd unit)
              </label>
              <input
                type="text"
                value={newService.name}
                onChange={(e) =>
                  setNewService({ ...newService, name: e.target.value })
                }
                className={inputClass}
                placeholder="valuescan-signal"
              />
            </div>
            <div>
              <label className="block text-xs text-neutral-400 mb-1">
                显示名称
              </label>
              <input
                type="text"
                value={newService.display_name}
                onChange={(e) =>
                  setNewService({ ...newService, display_name: e.target.value })
                }
                className={inputClass}
                placeholder="信号监控"
              />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-neutral-400 mb-1">
                检查间隔 (秒)
              </label>
              <input
                type="number"
                min={10}
                max={300}
                value={newService.check_interval || 60}
                onChange={(e) =>
                  setNewService({
                    ...newService,
                    check_interval: parseInt(e.target.value) || 60,
                  })
                }
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-xs text-neutral-400 mb-1">
                重启冷却 (秒)
              </label>
              <input
                type="number"
                min={60}
                value={newService.restart_cooldown || 300}
                onChange={(e) =>
                  setNewService({
                    ...newService,
                    restart_cooldown: parseInt(e.target.value) || 300,
                  })
                }
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-xs text-neutral-400 mb-1">
                无日志阈值 (秒)
              </label>
              <input
                type="number"
                min={0}
                value={newService.no_log_threshold ?? ''}
                onChange={(e) =>
                  setNewService({
                    ...newService,
                    no_log_threshold: e.target.value
                      ? parseInt(e.target.value)
                      : null,
                  })
                }
                className={inputClass}
                placeholder="留空禁用"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={handleCancelAdd}
              className="px-4 py-2 text-sm text-neutral-400 hover:text-white transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleAddService}
              disabled={
                !newService.name.trim() || !newService.display_name.trim()
              }
              className="px-4 py-2 text-sm bg-white text-black rounded-lg hover:bg-neutral-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              添加
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowAddForm(true)}
          className="w-full py-3 border border-dashed border-neutral-700 rounded-lg text-neutral-400 hover:text-white hover:border-neutral-500 transition-colors flex items-center justify-center gap-2"
        >
          <Plus className="w-4 h-4" />
          <span>添加服务</span>
        </button>
      )}
    </div>
  )
}
