import { useEffect, useState, useCallback, useRef } from 'react'
import { useAuthStore } from '@/stores/auth-store'
import { api } from '@/lib/api'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Brain,
  Search,
  Database,
  Server,
  Save,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Cpu,
  Eye,
  RefreshCw,
  Trash2,
  XCircle,
  Download,
  Package,
} from 'lucide-react'

interface SystemConfig {
  llm_model: string
  embedding_model: string
  llm_temperature: number
  llm_max_tokens: number
  chunk_size: number
  chunk_overlap: number
  top_k_results: number
  retriever_score_threshold: number
  max_upload_size: number
  api_host: string
  api_port: number
  debug: boolean
  ocr_backend: string
  ocr_use_gpu: boolean
  ocr_language: string
  vision_backend: string
  local_vision_model: string
}

interface GpuDeviceInfo {
  index: number
  name: string
  total_vram_mb: number
  used_vram_mb: number
  free_vram_mb: number
  compute_capability: string
}

interface GpuStatus {
  gpu: {
    available: boolean
    cuda_available: boolean
    device_count: number
    devices: GpuDeviceInfo[]
    torch_gpu: boolean
    paddle_gpu: boolean
    torch_available?: boolean
    paddle_available?: boolean
  }
  ocr: {
    backend: string
    use_gpu: boolean
    language: string
    available: boolean
    engine_loaded: boolean
  }
  vision: {
    backend: string
    local_model: string
    local_available: boolean
    current_backend: string
  }
}

const LLM_MODELS = [
  { value: 'qwen-max', label: 'Qwen Max（最强）' },
  { value: 'qwen-plus', label: 'Qwen Plus（均衡）' },
  { value: 'qwen-turbo', label: 'Qwen Turbo（最快）' },
  { value: 'qwen-long', label: 'Qwen Long（长文本）' },
]

const EMBEDDING_MODELS = [
  { value: 'text-embedding-v3', label: 'text-embedding-v3（推荐）' },
  { value: 'text-embedding-v2', label: 'text-embedding-v2' },
  { value: 'text-embedding-v1', label: 'text-embedding-v1' },
]

const OCR_BACKENDS = [
  { value: 'auto', label: '自动检测' },
  { value: 'paddleocr', label: 'PaddleOCR' },
  { value: 'none', label: '关闭 OCR' },
]

const OCR_LANGUAGES = [
  { value: 'ch', label: '中文' },
  { value: 'en', label: '英文' },
  { value: 'ch_en', label: '中英混合' },
]

const VISION_BACKENDS = [
  { value: 'auto', label: '自动检测' },
  { value: 'dashscope', label: 'DashScope API' },
  { value: 'local', label: '本地模型（需GPU）' },
]

interface ModelItem {
  id: string
  name: string
  type: string
  size: string
  description: string
  recommended: boolean
  downloaded: boolean
  download_status: string | null
  download_progress: number
}

export default function ApiSettingsPage() {
  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.role === 'admin'

  const [config, setConfig] = useState<SystemConfig | null>(null)
  const [originalConfig, setOriginalConfig] = useState<SystemConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingConfig, setPendingConfig] = useState<SystemConfig | null>(null)

  const [gpuStatus, setGpuStatus] = useState<GpuStatus | null>(null)
  const [gpuLoading, setGpuLoading] = useState(false)
  const [clearingCache, setClearingCache] = useState(false)
  const gpuRefreshRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const [models, setModels] = useState<ModelItem[]>([])
  const [modelsLoading, setModelsLoading] = useState(false)
  const [downloadingIds, setDownloadingIds] = useState<Set<string>>(new Set())

  const fetchConfig = useCallback(async () => {
    try {
      setLoading(true)
      const res = await api.get<SystemConfig>('/admin/config')
      setConfig(res.data)
      setOriginalConfig(res.data)
    } catch {
      setMessage({ type: 'error', text: '加载配置失败' })
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchGpuStatus = useCallback(async () => {
    try {
      setGpuLoading(true)
      const res = await api.get<GpuStatus>('/admin/gpu-status')
      setGpuStatus(res.data)
    } catch {
      setGpuStatus(null)
    } finally {
      setGpuLoading(false)
    }
  }, [])

  const handleClearGpuCache = async () => {
    try {
      setClearingCache(true)
      await api.post('/admin/gpu-cache/clear')
      setMessage({ type: 'success', text: 'GPU缓存已清理' })
      fetchGpuStatus()
    } catch {
      setMessage({ type: 'error', text: '清理GPU缓存失败' })
    } finally {
      setClearingCache(false)
    }
  }

  const fetchModels = useCallback(async () => {
    try {
      setModelsLoading(true)
      const res = await api.get<{ models: ModelItem[] }>('/models/available')
      setModels(res.data.models || [])
    } catch {
      setModels([])
    } finally {
      setModelsLoading(false)
    }
  }, [])

  const handleDownloadModel = async (modelId: string) => {
    try {
      setDownloadingIds(prev => new Set(prev).add(modelId))
      await api.post('/models/download', { model_id: modelId })
      pollDownloadStatus(modelId)
    } catch {
      setDownloadingIds(prev => {
        const next = new Set(prev)
        next.delete(modelId)
        return next
      })
      setMessage({ type: 'error', text: '启动下载失败' })
    }
  }

  const pollDownloadStatus = useCallback((modelId: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await api.get<{ status: string; progress: number }>(`/models/download/${encodeURIComponent(modelId)}/status`)
        const { status, progress } = res.data
        setModels(prev => prev.map(m =>
          m.id === modelId ? { ...m, download_status: status, download_progress: progress } : m
        ))
        if (status === 'completed') {
          clearInterval(interval)
          setDownloadingIds(prev => {
            const next = new Set(prev)
            next.delete(modelId)
            return next
          })
          setModels(prev => prev.map(m =>
            m.id === modelId ? { ...m, downloaded: true } : m
          ))
          setMessage({ type: 'success', text: `${modelId.split('/').pop()} 下载完成` })
          fetchGpuStatus()
        } else if (status === 'failed') {
          clearInterval(interval)
          setDownloadingIds(prev => {
            const next = new Set(prev)
            next.delete(modelId)
            return next
          })
          setMessage({ type: 'error', text: `${modelId.split('/').pop()} 下载失败` })
        }
      } catch {
        clearInterval(interval)
      }
    }, 3000)
  }, [fetchGpuStatus])

  const handleDeleteModel = async (modelId: string) => {
    try {
      await api.delete(`/models/download/${encodeURIComponent(modelId)}`)
      setModels(prev => prev.map(m =>
        m.id === modelId ? { ...m, downloaded: false, download_status: null, download_progress: 0 } : m
      ))
      setMessage({ type: 'success', text: '模型已删除' })
    } catch {
      setMessage({ type: 'error', text: '删除模型失败' })
    }
  }

  const handleSetVisionModel = async (modelId: string) => {
    try {
      await api.put('/models/vision-model', { model_id: modelId })
      updateField('local_vision_model', modelId)
      setMessage({ type: 'success', text: `视觉模型已切换为 ${modelId.split('/').pop()}` })
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } }
        setMessage({ type: 'error', text: axiosErr.response?.data?.detail || '切换模型失败' })
      } else {
        setMessage({ type: 'error', text: '切换模型失败' })
      }
    }
  }

  useEffect(() => {
    fetchConfig()
    fetchGpuStatus()
    fetchModels()
  }, [fetchConfig, fetchGpuStatus, fetchModels])

  useEffect(() => {
    gpuRefreshRef.current = setInterval(fetchGpuStatus, 30000)
    return () => {
      if (gpuRefreshRef.current) clearInterval(gpuRefreshRef.current)
    }
  }, [fetchGpuStatus])

  const updateField = <K extends keyof SystemConfig>(key: K, value: SystemConfig[K]) => {
    if (!config) return
    setConfig({ ...config, [key]: value })
    setMessage(null)
  }

  const hasChanges = config && originalConfig
    ? JSON.stringify(config) !== JSON.stringify(originalConfig)
    : false

  const handleSave = async () => {
    if (!config || !hasChanges) return

    const changed: Record<string, unknown> = {}
    for (const key of Object.keys(config) as Array<keyof SystemConfig>) {
      if (config[key] !== originalConfig?.[key]) {
        changed[key] = config[key]
      }
    }

    setSaving(true)
    setMessage(null)
    try {
      await api.put('/admin/config', changed)
      setOriginalConfig({ ...config })
      setMessage({ type: 'success', text: '配置保存成功' })
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { message?: string } } }
        setMessage({ type: 'error', text: axiosErr.response?.data?.message || '保存失败' })
      } else {
        setMessage({ type: 'error', text: '保存失败' })
      }
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    if (!originalConfig) return
    setPendingConfig({ ...originalConfig })
    setConfirmOpen(true)
  }

  const confirmReset = () => {
    if (pendingConfig) {
      setConfig(pendingConfig)
      setMessage(null)
    }
    setConfirmOpen(false)
    setPendingConfig(null)
  }

  if (!isAdmin) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">API 管理</h1>
        <Card>
          <CardContent className="flex h-40 items-center justify-center">
            <p className="text-muted-foreground">需要管理员权限</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">API 管理</h1>
        <div className="space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <Card key={i}>
              <CardContent className="h-40 animate-pulse rounded-lg bg-muted" />
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (!config) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">API 管理</h1>
        <Card>
          <CardContent className="flex h-40 items-center justify-center">
            <p className="text-muted-foreground">无法加载配置信息</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">API 管理</h1>
          <p className="text-muted-foreground mt-1">管理系统 API 配置和模型参数</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleReset} disabled={!hasChanges || saving}>
            <RotateCcw className="mr-2 h-4 w-4" />
            重置
          </Button>
          <Button onClick={handleSave} disabled={!hasChanges || saving}>
            {saving ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            保存配置
          </Button>
        </div>
      </div>

      {message && (
        <div className={`flex items-center gap-2 rounded-md px-4 py-3 text-sm ${
          message.type === 'success'
            ? 'bg-green-50 text-green-700'
            : 'bg-destructive/10 text-destructive'
        }`}>
          {message.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4 shrink-0" />
          ) : (
            <AlertCircle className="h-4 w-4 shrink-0" />
          )}
          {message.text}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="h-5 w-5 text-cyan-500" />
            GPU 状态监控
          </CardTitle>
          <CardDescription>
            实时监控 GPU 设备状态和加速服务运行情况
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchGpuStatus}
              disabled={gpuLoading}
            >
              {gpuLoading ? (
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              ) : (
                <RefreshCw className="mr-1 h-3 w-3" />
              )}
              刷新
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleClearGpuCache}
              disabled={clearingCache || !gpuStatus?.gpu.available}
            >
              {clearingCache ? (
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              ) : (
                <Trash2 className="mr-1 h-3 w-3" />
              )}
              清理缓存
            </Button>
          </div>

          {!gpuStatus ? (
            <div className="flex items-center justify-center h-20 text-muted-foreground text-sm">
              {gpuLoading ? '加载GPU状态...' : '无法获取GPU状态'}
            </div>
          ) : !gpuStatus.gpu.available ? (
            <div className="rounded-lg border border-dashed p-6 text-center">
              <XCircle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
              <p className="text-sm font-medium">未检测到 GPU 设备</p>
              <p className="text-xs text-muted-foreground mt-1">
                系统将以 CPU 模式运行，OCR 和视觉模型将使用 API 或 CPU 推理
              </p>
              <div className="flex items-center justify-center gap-4 mt-3 text-xs text-muted-foreground">
                <span>CUDA: {gpuStatus.gpu.cuda_available ? '✓' : '✗'}</span>
                <span>PyTorch: {gpuStatus.gpu.torch_gpu ? '✓' : '✗'}</span>
                <span>PaddlePaddle: {gpuStatus.gpu.paddle_gpu ? '✓' : '✗'}</span>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Badge variant="default" className="bg-green-500">GPU 可用</Badge>
                <span className="text-sm text-muted-foreground">
                  检测到 {gpuStatus.gpu.device_count} 个设备
                </span>
              </div>

              {gpuStatus.gpu.devices.map((dev) => (
                <div key={dev.index} className="rounded-lg border p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{dev.name}</span>
                    <Badge variant="outline" className="text-xs">
                      CUDA {dev.compute_capability}
                    </Badge>
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>显存使用</span>
                      <span>{dev.used_vram_mb} / {dev.total_vram_mb} MB</span>
                    </div>
                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-cyan-500 transition-all"
                        style={{
                          width: `${Math.min(100, (dev.used_vram_mb / dev.total_vram_mb) * 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))}

              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                <span>PyTorch GPU: {gpuStatus.gpu.torch_gpu ? '✓' : '✗'}</span>
                <span>PaddlePaddle GPU: {gpuStatus.gpu.paddle_gpu ? '✓' : '✗'}</span>
              </div>
            </div>
          )}

          {gpuStatus && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
              <div className="rounded-lg border p-3 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">OCR 服务</span>
                  <Badge variant={gpuStatus.ocr.available ? 'default' : 'secondary'} className="text-xs">
                    {gpuStatus.ocr.available ? '可用' : '不可用'}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  后端: {gpuStatus.ocr.backend} | GPU: {gpuStatus.ocr.use_gpu ? '开启' : '关闭'}
                </p>
                <p className="text-xs text-muted-foreground">
                  引擎: {gpuStatus.ocr.engine_loaded ? '已加载' : '未加载'} | 语言: {gpuStatus.ocr.language}
                </p>
              </div>
              <div className="rounded-lg border p-3 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">视觉模型</span>
                  <Badge variant={gpuStatus.vision.local_available ? 'default' : 'secondary'} className="text-xs">
                    {gpuStatus.vision.current_backend}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  配置: {gpuStatus.vision.backend} | 本地: {gpuStatus.vision.local_available ? '可用' : '不可用'}
                </p>
                <p className="text-xs text-muted-foreground truncate">
                  模型: {gpuStatus.vision.local_model}
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Eye className="h-5 w-5 text-indigo-500" />
            OCR / 视觉模型配置
          </CardTitle>
          <CardDescription>
            配置文档图片OCR识别和视觉描述模型参数
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="ocr-backend">OCR 后端</Label>
              <Select
                value={config.ocr_backend}
                onValueChange={(v) => updateField('ocr_backend', v)}
              >
                <SelectTrigger id="ocr-backend">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {OCR_BACKENDS.map((b) => (
                    <SelectItem key={b.value} value={b.value}>
                      {b.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                auto 自动检测 PaddleOCR 是否可用
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="ocr-language">OCR 语言</Label>
              <Select
                value={config.ocr_language}
                onValueChange={(v) => updateField('ocr_language', v)}
              >
                <SelectTrigger id="ocr-language">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {OCR_LANGUAGES.map((l) => (
                    <SelectItem key={l.value} value={l.value}>
                      {l.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between rounded-lg border p-3">
              <div className="space-y-0.5">
                <Label htmlFor="ocr-use-gpu">OCR GPU 加速</Label>
                <p className="text-xs text-muted-foreground">
                  启用后 PaddleOCR 将使用 GPU 推理
                </p>
              </div>
              <Switch
                id="ocr-use-gpu"
                checked={config.ocr_use_gpu}
                onCheckedChange={(v) => updateField('ocr_use_gpu', v)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="vision-backend">视觉模型后端</Label>
              <Select
                value={config.vision_backend}
                onValueChange={(v) => updateField('vision_backend', v)}
              >
                <SelectTrigger id="vision-backend">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {VISION_BACKENDS.map((b) => (
                    <SelectItem key={b.value} value={b.value}>
                      {b.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                auto 优先本地GPU，降级到DashScope API
              </p>
            </div>

            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="local-vision-model">本地视觉模型</Label>
              <Input
                id="local-vision-model"
                value={config.local_vision_model}
                onChange={(e) => updateField('local_vision_model', e.target.value)}
                placeholder="Qwen/Qwen2-VL-2B-Instruct"
              />
              <p className="text-xs text-muted-foreground">
                HuggingFace 模型名称，需提前下载或可在线加载
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Package className="h-5 w-5 text-emerald-500" />
            模型管理
          </CardTitle>
          <CardDescription>
            下载和管理本地推理模型，下载后可离线使用
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={fetchModels} disabled={modelsLoading}>
              {modelsLoading ? (
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              ) : (
                <RefreshCw className="mr-1 h-3 w-3" />
              )}
              刷新
            </Button>
          </div>

          {models.length === 0 && !modelsLoading ? (
            <div className="flex items-center justify-center h-20 text-muted-foreground text-sm">
              暂无可用模型
            </div>
          ) : (
            <div className="space-y-2">
              {models.map((model) => (
                <div
                  key={model.id}
                  className="rounded-lg border p-3 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{model.name}</span>
                      {model.recommended && (
                        <Badge variant="default" className="text-xs bg-blue-500">推荐</Badge>
                      )}
                      <Badge variant="outline" className="text-xs">
                        {model.type === 'vision' ? '视觉' : model.type === 'ocr' ? 'OCR' : model.type}
                      </Badge>
                      <span className="text-xs text-muted-foreground">{model.size}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      {model.downloaded ? (
                        <>
                          <Badge variant="default" className="text-xs bg-green-500">已下载</Badge>
                          {model.type === 'vision' && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-xs h-6"
                              onClick={() => handleSetVisionModel(model.id)}
                            >
                              设为视觉模型
                            </Button>
                          )}
                          {model.id !== 'PaddleOCR/PPOCRv4' && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-xs h-6 text-red-600 hover:text-red-700 hover:bg-red-50"
                              onClick={() => handleDeleteModel(model.id)}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          )}
                        </>
                      ) : model.download_status === 'downloading' ? (
                        <div className="flex items-center gap-2 w-32">
                          <div className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden">
                            <div
                              className="h-full rounded-full bg-blue-500 transition-all"
                              style={{ width: `${model.download_progress}%` }}
                            />
                          </div>
                          <span className="text-xs text-muted-foreground">{model.download_progress}%</span>
                        </div>
                      ) : model.download_status === 'failed' ? (
                        <>
                          <Badge variant="destructive" className="text-xs">失败</Badge>
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs h-6"
                            onClick={() => handleDownloadModel(model.id)}
                          >
                            重试
                          </Button>
                        </>
                      ) : (
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-xs h-6"
                          disabled={downloadingIds.has(model.id)}
                          onClick={() => handleDownloadModel(model.id)}
                        >
                          {downloadingIds.has(model.id) ? (
                            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                          ) : (
                            <Download className="mr-1 h-3 w-3" />
                          )}
                          下载
                        </Button>
                      )}
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">{model.description}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-blue-500" />
            大语言模型配置
          </CardTitle>
          <CardDescription>
            配置 AI 问答和作业指引生成使用的语言模型
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="llm-model">LLM 模型</Label>
              <Select
                value={config.llm_model}
                onValueChange={(v) => updateField('llm_model', v)}
              >
                <SelectTrigger id="llm-model">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LLM_MODELS.map((m) => (
                    <SelectItem key={m.value} value={m.value}>
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                当前: <code className="bg-muted px-1 rounded">{config.llm_model}</code>
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="embedding-model">Embedding 模型</Label>
              <Select
                value={config.embedding_model}
                onValueChange={(v) => updateField('embedding_model', v)}
              >
                <SelectTrigger id="embedding-model">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {EMBEDDING_MODELS.map((m) => (
                    <SelectItem key={m.value} value={m.value}>
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                当前: <code className="bg-muted px-1 rounded">{config.embedding_model}</code>
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="temperature">
                生成温度
                <Badge variant="secondary" className="ml-2">{config.llm_temperature}</Badge>
              </Label>
              <Input
                id="temperature"
                type="number"
                min={0}
                max={2}
                step={0.1}
                value={config.llm_temperature}
                onChange={(e) => updateField('llm_temperature', parseFloat(e.target.value) || 0)}
              />
              <p className="text-xs text-muted-foreground">
                值越高输出越随机（0.0 ~ 2.0），推荐 0.7
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="max-tokens">
                最大输出 Token
                <Badge variant="secondary" className="ml-2">{config.llm_max_tokens}</Badge>
              </Label>
              <Input
                id="max-tokens"
                type="number"
                min={1}
                max={32768}
                step={256}
                value={config.llm_max_tokens}
                onChange={(e) => updateField('llm_max_tokens', parseInt(e.target.value) || 4096)}
              />
              <p className="text-xs text-muted-foreground">
                单次回答最大 token 数（1 ~ 32768）
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5 text-green-500" />
            检索配置
          </CardTitle>
          <CardDescription>
            配置知识检索和向量匹配参数
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="top-k">
                检索结果数 (Top K)
                <Badge variant="secondary" className="ml-2">{config.top_k_results}</Badge>
              </Label>
              <Input
                id="top-k"
                type="number"
                min={1}
                max={20}
                value={config.top_k_results}
                onChange={(e) => updateField('top_k_results', parseInt(e.target.value) || 5)}
              />
              <p className="text-xs text-muted-foreground">
                每次检索返回的最大结果数（1 ~ 20）
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="score-threshold">
                相似度阈值
                <Badge variant="secondary" className="ml-2">{config.retriever_score_threshold}</Badge>
              </Label>
              <Input
                id="score-threshold"
                type="number"
                min={0}
                max={1}
                step={0.05}
                value={config.retriever_score_threshold}
                onChange={(e) => updateField('retriever_score_threshold', parseFloat(e.target.value) || 0.3)}
              />
              <p className="text-xs text-muted-foreground">
                低于此阈值的结果将被过滤（0.0 ~ 1.0）
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5 text-purple-500" />
            文本分块配置
          </CardTitle>
          <CardDescription>
            配置文档解析后的文本分块策略
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="chunk-size">
                分块大小
                <Badge variant="secondary" className="ml-2">{config.chunk_size} 字符</Badge>
              </Label>
              <Input
                id="chunk-size"
                type="number"
                min={100}
                max={4096}
                step={64}
                value={config.chunk_size}
                onChange={(e) => updateField('chunk_size', parseInt(e.target.value) || 512)}
              />
              <p className="text-xs text-muted-foreground">
                每个文本块的最大字符数（100 ~ 4096）
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="chunk-overlap">
                分块重叠
                <Badge variant="secondary" className="ml-2">{config.chunk_overlap} 字符</Badge>
              </Label>
              <Input
                id="chunk-overlap"
                type="number"
                min={0}
                max={500}
                step={10}
                value={config.chunk_overlap}
                onChange={(e) => updateField('chunk_overlap', parseInt(e.target.value) || 50)}
              />
              <p className="text-xs text-muted-foreground">
                相邻块之间的重叠字符数（0 ~ 500）
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5 text-orange-500" />
            服务配置
          </CardTitle>
          <CardDescription>
            系统服务运行参数（只读）
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">监听地址</p>
              <p className="font-mono text-sm bg-muted px-2 py-1 rounded">{config.api_host}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">监听端口</p>
              <p className="font-mono text-sm bg-muted px-2 py-1 rounded">{config.api_port}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">最大上传大小</p>
              <p className="font-mono text-sm bg-muted px-2 py-1 rounded">
                {(config.max_upload_size / 1024 / 1024).toFixed(0)} MB
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {hasChanges && (
        <div className="fixed bottom-4 right-4 z-50">
          <Card className="shadow-lg border-orange-200 bg-orange-50">
            <CardContent className="flex items-center gap-3 py-3 px-4">
              <AlertCircle className="h-4 w-4 text-orange-600 shrink-0" />
              <span className="text-sm text-orange-800">有未保存的更改</span>
              <Separator orientation="vertical" className="h-4" />
              <Button size="sm" onClick={handleSave} disabled={saving}>
                {saving ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : <Save className="mr-1 h-3 w-3" />}
                保存
              </Button>
              <Button size="sm" variant="ghost" onClick={handleReset}>
                取消
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认重置</DialogTitle>
            <DialogDescription>
              将所有配置恢复为上次保存的状态，未保存的更改将丢失。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              取消
            </Button>
            <Button onClick={confirmReset}>确认重置</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
