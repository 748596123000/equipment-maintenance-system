import React, { useEffect, useState, useCallback, useRef } from 'react'
// FORCE_REBUILD: llama_cpp support added
import { useAuthStore } from '@/stores/auth-store'
import { useTheme } from '@/hooks/useTheme'
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
  AlertTriangle,
  Loader2,
  Cpu,
  Eye,
  EyeOff,
  RefreshCw,
  Trash2,
  XCircle,
  Download,
  Package,
  Wifi,
  WifiOff,
  Zap,
  Key,
  Activity,
  Play,
  FileText,
  MessageSquare,
  Sparkles,
  BookOpen,
  Clock,
  Circle,
} from 'lucide-react'

interface SystemConfig {
  dashscope_api_key: string
  minimax_api_key: string
  deepseek_api_key: string
  zhipu_api_key: string
  baichuan_api_key: string
  moonshot_api_key: string
  siliconflow_api_key: string
  openai_compatible_api_key: string
  llm_backend: string
  llm_model: string
  llm_api_base_url: string
  llm_api_key: string
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
  // ====== 新增 per-service 独立厂商配置 ======
  // LLM
  llm_vendor: string
  llm_api_key_override: string
  llm_api_base_url_override: string
  llm_model_override: string
  // Embedding
  embedding_vendor: string
  embedding_api_key: string
  embedding_api_base_url: string
  embedding_model_name: string
  // Vision
  vision_vendor: string
  vision_api_key: string
  vision_api_base_url: string
  vision_model_name: string
}

interface SystemInfo {
  platform: string
  system: string
  machine: string
  architecture: string
  is_loongarch: boolean
  python_version: string
  compatibility?: {
    llm_backends?: Record<string, boolean>
    ocr_backends?: Record<string, boolean>
    vision_backends?: Record<string, boolean>
  }
  recommended?: {
    llm_backend?: string
    ocr_backend?: string
    vision_backend?: string
    embedding_backend?: string
  }
  hints?: {
    loongarch?: string[]
  }
  llama_cpp?: {
    available: boolean
    default_url: string
    alternate_url: string
    hint: string
  }
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
    nvidia_driver_available?: boolean
    diagnostics?: {
      nvidia_driver_version?: string
      cuda_driver_version?: string
      nvidia_gpu_names?: string[]
      torch_version?: string
      torch_cuda_version?: string | null
      torch_gpu_reason?: string
      paddle_version?: string
      paddle_gpu_reason?: string
    }
  }
  ocr: {
    backend: string
    use_gpu: boolean
    language: string
    available: boolean
    engine_loaded: boolean
    engine_type?: string
  }
  vision: {
    backend: string
    local_model: string
    local_available: boolean
    current_backend: string
  }
}

interface ServiceStatus {
  llm: { available: boolean; backend?: string; model?: string; error?: string }
  embedding: { available: boolean; backend?: string; model?: string; error?: string }
  ocr: { available: boolean; backend?: string; error?: string }
  vision: { available: boolean; backend?: string; current_backend?: string; error?: string }
  dashscope: { available: boolean; api_key_set: boolean }
}

interface TestResult {
  service: string
  success: boolean
  message: string
  latency_ms: number
}

interface FunctionTestResult {
  name: string
  success: boolean
  message: string
  latency_ms: number
  timestamp: Date
}

const LLM_MODELS = [
  { value: 'qwen-max', label: 'Qwen Max（最强）' },
  { value: 'qwen-plus', label: 'Qwen Plus（均衡）' },
  { value: 'qwen-turbo', label: 'Qwen Turbo（最快）' },
  { value: 'qwen-long', label: 'Qwen Long（长文本）' },
]

const LLM_BACKENDS = [
  { value: 'dashscope', label: '通义千问 (DashScope)', website: 'https://dashscope.console.aliyun.com' },
  { value: 'minimax', label: 'MiniMax（Token Plan）', website: 'https://platform.minimaxi.com/user-center/payment/token-plan' },
  { value: 'deepseek', label: 'DeepSeek（深度求索）', website: 'https://platform.deepseek.com' },
  { value: 'zhipu', label: '智谱AI (Zhipu)', website: 'https://open.bigmodel.cn' },
  { value: 'baichuan', label: '百川智能 (Baichuan)', website: 'https://www.baichuan-ai.com' },
  { value: 'moonshot', label: '月之暗面 (Kimi)', website: 'https://platform.moonshot.cn' },
  { value: 'siliconflow', label: '硅基流动 (SiliconFlow)', website: 'https://www.siliconflow.cn' },
  { value: 'ollama', label: 'Ollama（本地模型）', website: 'https://ollama.com' },
  { value: 'llama_cpp', label: 'llama.cpp（本地模型）', website: 'https://github.com/ggerganov/llama.cpp' },
  { value: 'openai_compatible', label: 'OpenAI 兼容 API', website: '' },
]

// Embedding 厂商列表
const EMBEDDING_VENDORS = [
  { value: 'dashscope', label: '通义千问 (DashScope)', website: 'https://dashscope.console.aliyun.com', defaultModel: 'text-embedding-v3', defaultBaseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
  { value: 'openai_compatible', label: 'OpenAI 兼容 API', website: '', defaultModel: '', defaultBaseUrl: 'http://localhost:8080/v1' },
  { value: 'llama_cpp', label: 'llama.cpp（本地）', website: 'https://github.com/ggerganov/llama.cpp', defaultModel: '', defaultBaseUrl: 'http://127.0.0.1:8080/v1' },
  { value: 'ollama', label: 'Ollama（本地）', website: 'https://ollama.com', defaultModel: 'nomic-embed-text', defaultBaseUrl: 'http://localhost:11434/v1' },
]

// Vision 厂商列表
const VISION_VENDORS = [
  { value: 'dashscope', label: '通义千问 (DashScope)', website: 'https://dashscope.console.aliyun.com', defaultModel: 'qwen-vl-max', defaultBaseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
  { value: 'openai_compatible', label: 'OpenAI 兼容 API', website: '', defaultModel: '', defaultBaseUrl: 'http://localhost:8081/v1' },
  { value: 'llama_cpp', label: 'llama.cpp（本地多模态）', website: 'https://github.com/ggerganov/llama.cpp', defaultModel: 'Qwen2-VL-2B-Instruct-Q4_K_M', defaultBaseUrl: 'http://127.0.0.1:8081/v1' },
]

const MINIMAX_MODELS = [
  { value: 'abab6.5s-chat', label: 'ABAB 6.5S Chat（推荐）' },
  { value: 'abab6.5g-chat', label: 'ABAB 6.5G Chat' },
  { value: 'abab5.5s-chat', label: 'ABAB 5.5S Chat' },
  { value: 'abab5.5g-chat', label: 'ABAB 5.5G Chat' },
]

const DEEPSEEK_MODELS = [
  { value: 'deepseek-chat', label: 'DeepSeek Chat（推荐）' },
  { value: 'deepseek-coder', label: 'DeepSeek Coder（代码）' },
  { value: 'deepseek-reasoner', label: 'DeepSeek Reasoner（推理）' },
]

const ZHIPU_MODELS = [
  { value: 'glm-4', label: 'GLM-4（最强）' },
  { value: 'glm-4-flash', label: 'GLM-4-Flash（快速）' },
  { value: 'glm-3-turbo', label: 'GLM-3-Turbo（均衡）' },
]

const BAICHUAN_MODELS = [
  { value: 'Baichuan4', label: 'Baichuan4（推荐）' },
  { value: 'Baichuan3-Turbo', label: 'Baichuan3-Turbo' },
  { value: 'Baichuan2-Open', label: 'Baichuan2-Open' },
]

const MOONSHOT_MODELS = [
  { value: 'moonshot-v1-128k', label: 'Moonshot V1 128K（长文本）' },
  { value: 'moonshot-v1-32k', label: 'Moonshot V1 32K（推荐）' },
  { value: 'moonshot-v1-8k', label: 'Moonshot V1 8K' },
]

const SILICONFLOW_MODELS = [
  { value: 'Qwen/Qwen2.5-72B-Instruct', label: 'Qwen2.5-72B（推荐）' },
  { value: 'deepseek-ai/DeepSeek-V2.5', label: 'DeepSeek V2.5' },
  { value: 'THUDM/GLM-4-9B-Chat', label: 'GLM-4-9B' },
  { value: 'Qwen/Qwen2-VL-72B-Instruct', label: 'Qwen2-VL-72B' },
]

const EMBEDDING_MODELS = [
  { value: 'text-embedding-v3', label: 'text-embedding-v3（推荐）' },
  { value: 'text-embedding-v2', label: 'text-embedding-v2' },
  { value: 'text-embedding-v1', label: 'text-embedding-v1' },
]

const OCR_BACKENDS = [
  { value: 'auto', label: '自动检测', loongarchHint: '将优先选择 RapidOCR / API' },
  { value: 'rapidocr', label: 'RapidOCR（CPU推荐）', loongarchHint: 'LoongArch 推荐（CPU 即用）' },
  { value: 'paddleocr', label: 'PaddleOCR（需GPU）', loongarchHint: 'LoongArch 无官方预编译 wheel，需自行从源码编译，难度高' },
  { value: 'api', label: 'DashScope API', loongarchHint: '云端 OCR，LoongArch 完全可用' },
  { value: 'none', label: '关闭 OCR', loongarchHint: '' },
]

const OCR_LANGUAGES = [
  { value: 'ch', label: '中文' },
  { value: 'en', label: '英文' },
  { value: 'ch_en', label: '中英混合' },
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

function ApiKeyInput({
  id,
  label,
  value,
  onChange,
  placeholder,
  hint,
}: {
  id: string
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  hint?: React.ReactNode
}) {
  const [visible, setVisible] = useState(false)
  const isMasked = value === '******'

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <div className="flex gap-1.5">
        <div className="relative flex-1">
          <Input
            id={id}
            type={visible && !isMasked ? 'text' : 'password'}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className="pr-9"
          />
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="absolute right-0 top-0 h-full px-2.5 hover:bg-transparent"
            onClick={() => setVisible(!visible)}
          >
            {visible && !isMasked ? (
              <EyeOff className="h-3.5 w-3.5 text-muted-foreground" />
            ) : (
              <Eye className="h-3.5 w-3.5 text-muted-foreground" />
            )}
          </Button>
        </div>
      </div>
      {isMasked && (
        <p className="text-xs text-amber-600">已配置密钥，输入新值将覆盖</p>
      )}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}

function TestButton({
  service,
  config,
  onResult,
  disabled,
  label,
  icon: IconComponent,
}: {
  service: 'llm' | 'embedding' | 'vision' | 'ocr'
  config: SystemConfig
  onResult: (result: TestResult) => void
  disabled?: boolean
  label?: string
  icon?: React.ComponentType<{ className?: string }>
}) {
  const [testing, setTesting] = useState(false)

  const handleTest = async () => {
    setTesting(true)
    try {
      const payload: Record<string, string> = { service }
      // 优先使用每个服务的独立 vendor 配置
      if (service === 'llm') {
        const llmBackend = (config.llm_vendor || config.llm_backend || 'dashscope').toLowerCase()
        payload.backend = llmBackend
        payload.model = config.llm_model_override || config.llm_model
        payload.base_url = config.llm_api_base_url_override || config.llm_api_base_url
        // 按 backend 类型选择正确的厂商 API Key
        if (config.llm_api_key_override) {
          payload.api_key = config.llm_api_key_override
        } else {
          const vendorKeyMap: Record<string, string | undefined> = {
            minimax: config.minimax_api_key,
            deepseek: config.deepseek_api_key,
            zhipu: config.zhipu_api_key,
            baichuan: config.baichuan_api_key,
            moonshot: config.moonshot_api_key,
            siliconflow: config.siliconflow_api_key,
            openai_compatible: config.openai_compatible_api_key,
          }
          payload.api_key = vendorKeyMap[llmBackend] || config.llm_api_key || config.dashscope_api_key
        }
      } else if (service === 'embedding') {
        payload.backend = config.embedding_vendor || 'dashscope'
        payload.model = config.embedding_model_name || config.embedding_model
        payload.base_url = config.embedding_api_base_url
        if (config.embedding_api_key) payload.api_key = config.embedding_api_key
      } else if (service === 'vision') {
        payload.backend = config.vision_vendor || config.vision_backend
        payload.model = config.vision_model_name
        payload.base_url = config.vision_api_base_url
        if (config.vision_api_key) payload.api_key = config.vision_api_key
      }
      const res = await api.post<TestResult>('/admin/test-connection', payload)
      onResult(res.data)
    } catch (err: unknown) {
      onResult({
        service,
        success: false,
        message: '测试请求失败',
        latency_ms: 0,
      })
    } finally {
      setTesting(false)
    }
  }

  return (
    <Button
      variant="outline"
      size="sm"
      className="text-xs px-2 py-1 h-7"
      disabled={disabled || testing}
      onClick={handleTest}
    >
      {testing ? (
        <Loader2 className="mr-1 h-3 w-3 animate-spin" />
      ) : IconComponent ? (
        <IconComponent className="mr-1 h-3 w-3" />
      ) : (
        <Zap className="mr-1 h-3 w-3" />
      )}
      {label || '测试连接'}
    </Button>
  )
}

function TestResultBadge({ result }: { result: TestResult | null }) {
  if (!result) return null
  return (
    <div className={`text-xs flex items-center gap-1 mt-1 ${result.success ? 'text-green-600' : 'text-red-500'}`}>
      {result.success ? (
        <CheckCircle2 className="h-3 w-3 shrink-0" />
      ) : (
        <AlertCircle className="h-3 w-3 shrink-0" />
      )}
      <span className="truncate">{result.message}</span>
    </div>
  )
}

/**
 * 单个服务（LLM / Embedding / Vision）的厂商配置卡
 * 包含：厂商下拉 + 独立 API Key + Base URL + 模型名 + 测试按钮
 */
function ServiceVendorCard({
  title,
  icon,
  vendorField,
  vendorValue,
  apiKeyField,
  apiKeyValue,
  baseUrlField,
  baseUrlValue,
  modelField,
  modelValue,
  vendors,
  updateField,
  testService,
  onTestResult,
  config,
}: {
  title: string
  icon: React.ReactNode
  vendorField: string
  vendorValue: string
  apiKeyField: string
  apiKeyValue: string
  baseUrlField: string
  baseUrlValue: string
  modelField: string
  modelValue: string
  vendors: Array<{ value: string; label: string; website?: string; defaultModel?: string; defaultBaseUrl?: string }>
  updateField: (field: string, value: any) => void
  testService: 'llm' | 'embedding' | 'vision'
  onTestResult: (r: TestResult) => void
  config: SystemConfig
}) {
  const currentVendor = vendors.find((v) => v.value === vendorValue)
  const placeholderUrl = currentVendor?.defaultBaseUrl || ''
  const placeholderModel = currentVendor?.defaultModel || ''

  return (
    <div className="rounded-md border p-3 space-y-2.5 bg-card">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          {icon}
          {title}
        </div>
        {vendorValue && (
          <Badge variant="secondary" className="text-[10px]">
            {currentVendor?.label || vendorValue}
          </Badge>
        )}
      </div>

      {/* 厂商选择 */}
      <div className="space-y-1">
        <Label className="text-xs">厂商 / 后端</Label>
        <Select
          value={vendorValue || ''}
          onValueChange={(v) => {
            updateField(vendorField, v)
            // 自动填默认 Base URL / Model
            const vcfg = vendors.find((x) => x.value === v)
            if (vcfg?.defaultBaseUrl && !baseUrlValue) {
              updateField(baseUrlField, vcfg.defaultBaseUrl)
            }
            if (vcfg?.defaultModel && !modelValue) {
              updateField(modelField, vcfg.defaultModel)
            }
          }}
        >
          <SelectTrigger className="h-8 text-xs">
            <SelectValue placeholder="选择厂商（留空使用通用配置）" />
          </SelectTrigger>
          <SelectContent>
            {vendors.map((v) => (
              <SelectItem key={v.value} value={v.value}>
                {v.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {currentVendor?.website && (
          <a
            href={currentVendor.website}
            target="_blank"
            rel="noreferrer"
            className="text-[10px] text-muted-foreground hover:underline block truncate"
          >
            {currentVendor.website}
          </a>
        )}
      </div>

      {/* 独立 API Key */}
      <div className="space-y-1">
        <Label className="text-xs">独立 API Key（留空用通用 Key）</Label>
        <Input
          type="password"
          value={apiKeyValue || ''}
          onChange={(e) => updateField(apiKeyField, e.target.value)}
          placeholder="留空 → 使用厂商通用 Key"
          className="h-8 text-xs font-mono"
        />
      </div>

      {/* Base URL + Model 并排 */}
      <div className="grid grid-cols-1 gap-2">
        <div className="space-y-1">
          <Label className="text-xs">Base URL</Label>
          <Input
            value={baseUrlValue || ''}
            onChange={(e) => updateField(baseUrlField, e.target.value)}
            placeholder={placeholderUrl || '如 https://api.example.com/v1'}
            className="h-8 text-xs font-mono"
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">模型名</Label>
          <Input
            value={modelValue || ''}
            onChange={(e) => updateField(modelField, e.target.value)}
            placeholder={placeholderModel || '如 qwen-max / text-embedding-v3'}
            className="h-8 text-xs font-mono"
          />
        </div>
      </div>

      {/* 测试按钮 */}
      <div className="flex justify-end pt-1">
        <TestButton
          service={testService}
          config={config}
          onResult={onTestResult}
          label="测试"
          icon={Zap}
        />
      </div>
    </div>
  )
}

export default function ApiSettingsPage() {
  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.role === 'admin'
  
  const { theme } = useTheme()
  const isLight = theme === 'light'

  const [config, setConfig] = useState<SystemConfig | null>(null)
  const [originalConfig, setOriginalConfig] = useState<SystemConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingConfig, setPendingConfig] = useState<SystemConfig | null>(null)

  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  const [showLoongarchHelp, setShowLoongarchHelp] = useState(true)
  const isLoongarch = systemInfo?.is_loongarch ?? false
  const llmCompat = systemInfo?.compatibility?.llm_backends ?? {}
  const ocrCompat = systemInfo?.compatibility?.ocr_backends ?? {}
  const visionCompat = systemInfo?.compatibility?.vision_backends ?? {}

  const [gpuStatus, setGpuStatus] = useState<GpuStatus | null>(null)
  const [gpuLoading, setGpuLoading] = useState(false)
  const [clearingCache, setClearingCache] = useState(false)
  const [installingCudaDeps, setInstallingCudaDeps] = useState(false)
  const [cudaInstallStatus, setCudaInstallStatus] = useState<string | null>(null)
  const gpuRefreshRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const [models, setModels] = useState<ModelItem[]>([])
  const [modelsLoading, setModelsLoading] = useState(false)
  const [downloadingIds, setDownloadingIds] = useState<Set<string>>(new Set())
  const [settingVisionModel, setSettingVisionModel] = useState<string | null>(null)

  const [llmModels, setLlmModels] = useState<{ id: string; name: string }[]>([])
  const [llmModelsLoading, setLlmModelsLoading] = useState(false)
  const [llmStatus, setLlmStatus] = useState<{ available: boolean; connection: string } | null>(null)

  const [servicesStatus, setServicesStatus] = useState<ServiceStatus | null>(null)
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({})

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

  const fetchSystemInfo = useCallback(async () => {
    try {
      const res = await api.get<SystemInfo>('/admin/system-info')
      setSystemInfo(res.data)
    } catch {
      setSystemInfo(null)
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

  const fetchServicesStatus = useCallback(async () => {
    try {
      const res = await api.get<ServiceStatus>('/admin/services/status')
      setServicesStatus(res.data)
    } catch {
      setServicesStatus(null)
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

  const handleInstallCudaDeps = async () => {
    try {
      setInstallingCudaDeps(true)
      setCudaInstallStatus('正在启动安装...')
      await api.post('/admin/install-cuda-deps')

      const pollStatus = async () => {
        try {
          const res = await api.get<{ status: string }>('/admin/install-cuda-deps/status')
          const status = res.data.status

          if (status === 'installing' || status === 'uninstalling_cpu_torch' || status === 'installing_cuda_torch') {
            const statusText: Record<string, string> = {
              'uninstalling_cpu_torch': '正在卸载 CPU 版 PyTorch...',
              'installing_cuda_torch': '正在安装 CUDA 版 PyTorch（约2.7GB，请耐心等待）...',
              'installing': '正在准备安装...',
            }
            setCudaInstallStatus(statusText[status] || '安装中...')
            setTimeout(pollStatus, 3000)
          } else if (status === 'completed') {
            setCudaInstallStatus('安装完成！正在刷新GPU状态...')
            setInstallingCudaDeps(false)
            fetchGpuStatus()
            setTimeout(() => setCudaInstallStatus(null), 5000)
          } else if (status.startsWith('failed:')) {
            setCudaInstallStatus(`安装失败: ${status.replace('failed:', '')}`)
            setInstallingCudaDeps(false)
          } else {
            setCudaInstallStatus(null)
            setInstallingCudaDeps(false)
          }
        } catch {
          setTimeout(pollStatus, 5000)
        }
      }

      setTimeout(pollStatus, 2000)
    } catch {
      setCudaInstallStatus('启动安装失败')
      setInstallingCudaDeps(false)
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

  const fetchLlmModels = useCallback(async (backend?: string, baseUrl?: string, apiKey?: string) => {
    try {
      setLlmModelsLoading(true)
      const params = new URLSearchParams()
      if (backend) params.set('backend', backend)
      if (baseUrl) params.set('base_url', baseUrl)
      if (apiKey) params.set('api_key', apiKey)
      const qs = params.toString()
      const res = await api.get<{ models: { id: string; name: string }[] }>(`/admin/llm/models${qs ? '?' + qs : ''}`)
      setLlmModels(res.data.models || [])
    } catch {
      setLlmModels([])
    } finally {
      setLlmModelsLoading(false)
    }
  }, [])

  const fetchLlmStatus = useCallback(async () => {
    try {
      const res = await api.get<{ available: boolean; connection: string }>('/admin/llm/status')
      setLlmStatus(res.data)
    } catch {
      setLlmStatus(null)
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
      setSettingVisionModel(modelId)
      await api.put('/models/vision-model', { model_id: modelId })
      updateField('local_vision_model', modelId)
      updateField('vision_backend', 'local')
      setMessage({ type: 'success', text: `视觉模型已切换为 ${modelId.split('/').pop()}，后端已设为本地模型` })
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } }
        setMessage({ type: 'error', text: axiosErr.response?.data?.detail || '切换模型失败' })
      } else {
        setMessage({ type: 'error', text: '切换模型失败' })
      }
    } finally {
      setSettingVisionModel(null)
    }
  }

  useEffect(() => {
    fetchConfig()
    fetchGpuStatus()
    fetchModels()
    fetchLlmStatus()
    fetchServicesStatus()
    fetchSystemInfo()
  }, [fetchConfig, fetchGpuStatus, fetchModels, fetchLlmStatus, fetchServicesStatus, fetchSystemInfo])

  useEffect(() => {
    gpuRefreshRef.current = setInterval(fetchGpuStatus, 30000)
    return () => {
      if (gpuRefreshRef.current) clearInterval(gpuRefreshRef.current)
    }
  }, [fetchGpuStatus])

  // LoongArch：若当前配置为不兼容后端，则提示一次并推荐切换（不强制覆盖）
  const [loongarchSuggested, setLoongarchSuggested] = useState(false)
  useEffect(() => {
    if (!systemInfo || !isLoongarch || !config || loongarchSuggested) return
    const ollamaInUse = config.llm_backend === 'ollama'
    const paddleInUse = config.ocr_backend === 'paddleocr'
    const localVisionInUse = config.vision_backend === 'local'
    if (ollamaInUse || paddleInUse || localVisionInUse) {
      setMessage({
        type: 'error',
        text: '检测到 LoongArch 环境与不兼容后端（Ollama/PaddleOCR/本地视觉），请手动切换到 DashScope API / RapidOCR / 自动视觉。功能保持可用，按需切换即可。',
      })
    }
    setLoongarchSuggested(true)
  }, [systemInfo, isLoongarch, config, loongarchSuggested])

  const updateField = <K extends keyof SystemConfig>(key: K, value: SystemConfig[K]) => {
    if (!config) return
    setConfig(prev => prev ? { ...prev, [key]: value } : prev)
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
      setMessage({ type: 'success', text: '配置保存成功，相关服务已自动重载' })
      fetchServicesStatus()
      fetchLlmStatus()
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

  const handleTestResult = (service: string, result: TestResult) => {
    setTestResults(prev => ({ ...prev, [service]: result }))
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

      {systemInfo && (
        <div className={`rounded-md border px-4 py-3 text-sm ${
          isLoongarch
            ? 'bg-amber-50 border-amber-200 text-amber-900'
            : 'bg-blue-50 border-blue-200 text-blue-900'
        }`}>
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              {isLoongarch ? (
                <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
              ) : (
                <Server className="h-4 w-4 shrink-0 text-blue-600" />
              )}
              <span className="font-medium">
                {isLoongarch
                  ? '检测到 LoongArch 架构环境，已为您适配推荐方案'
                  : '当前运行环境信息'}
              </span>
              <span className="text-xs text-muted-foreground">
                {systemInfo.system} · {systemInfo.machine} · Python {systemInfo.python_version}
              </span>
              {isLoongarch && systemInfo.llama_cpp && (
                <Badge variant={systemInfo.llama_cpp.available ? 'default' : 'secondary'} className="text-[10px] px-1.5">
                  llama.cpp {systemInfo.llama_cpp.available ? '已安装' : '未安装'}
                </Badge>
              )}
            </div>
            {isLoongarch && systemInfo.hints?.loongarch && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={() => setShowLoongarchHelp(v => !v)}
              >
                {showLoongarchHelp ? '收起' : '查看建议'}
              </Button>
            )}
          </div>
          {isLoongarch && showLoongarchHelp && systemInfo.hints?.loongarch && (
            <ul className="mt-2 space-y-1 text-xs text-amber-800 list-disc pl-5">
              {systemInfo.hints.loongarch.map((h, i) => (
                <li key={i}>{h}</li>
              ))}
            </ul>
          )}
          {isLoongarch && systemInfo.llama_cpp?.available && (
            <div className="mt-2 flex items-center gap-2 text-xs">
              <Button
                variant="outline"
                size="sm"
                className="h-6 text-xs bg-amber-100 border-amber-300 hover:bg-amber-200"
                onClick={() => {
                  updateField('llm_backend', 'llama_cpp')
                  updateField('llm_api_base_url', systemInfo.llama_cpp?.default_url || 'http://localhost:11434/v1')
                  setMessage({ type: 'success', text: '已切换到 llama.cpp 本地模型，请配置 LLM 模型名称后保存' })
                }}
              >
                一键配置 llama-server
              </Button>
              <span className="text-amber-700">
                启动：<code className="bg-amber-100 px-1 rounded">llama-server -m ~/models/*.gguf --host 0.0.0.0 --port 11434</code>
              </span>
            </div>
          )}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-blue-500" />
            服务状态总览
          </CardTitle>
          <CardDescription>
            所有 API 服务的实时连接状态
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 mb-3">
            <Button variant="outline" size="sm" onClick={fetchServicesStatus}>
              <RefreshCw className="mr-1 h-3 w-3" />
              刷新状态
            </Button>
          </div>
          {servicesStatus ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {[
                { key: 'dashscope', label: 'DashScope', icon: Key, data: servicesStatus.dashscope },
                { key: 'llm', label: 'LLM 大模型', icon: Brain, data: servicesStatus.llm },
                { key: 'embedding', label: 'Embedding', icon: Search, data: servicesStatus.embedding },
                { key: 'ocr', label: 'OCR 识别', icon: Eye, data: servicesStatus.ocr },
                { key: 'vision', label: '视觉模型', icon: Cpu, data: servicesStatus.vision },
              ].map(({ key, label, icon: Icon, data }) => (
                <div 
                  key={key} 
                  className="premium-card p-3 flex flex-col justify-between min-h-[80px]"
                  style={{ alignItems: 'stretch' }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <Icon className="h-3.5 w-3.5" style={{ color: isLight ? '#3b82f6' : '#00f0ff' }} />
                      <span className="text-xs font-medium" style={{ color: isLight ? '#1e293b' : '#e8e8e8' }}>{label}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className={`status-dot ${data.available ? 'online' : 'offline'}`} />
                      <Badge 
                        variant={data.available ? 'default' : 'secondary'} 
                        className="text-[10px] px-1.5"
                        style={{ 
                          background: data.available 
                            ? (isLight ? '#dcfce7' : 'rgba(16, 185, 129, 0.2)') 
                            : (isLight ? '#fee2e2' : 'rgba(239, 68, 68, 0.2)'),
                          color: data.available 
                            ? (isLight ? '#166534' : '#10b981') 
                            : (isLight ? '#991b1b' : '#ef4444')
                        }}
                      >
                        {data.available ? '可用' : '不可用'}
                      </Badge>
                    </div>
                  </div>
                  <div className="mt-auto">
                    {data.available && 'model' in data && data.model && (
                      <p className="text-[10px] truncate" style={{ color: isLight ? '#64748b' : '#6b7280' }}>{data.model}</p>
                    )}
                    {data.available && 'backend' in data && data.backend && (
                      <p className="text-[10px] truncate" style={{ color: isLight ? '#64748b' : '#6b7280' }}>{data.backend}</p>
                    )}
                    {'api_key_set' in data && (
                      <p className="text-[10px]" style={{ color: isLight ? '#64748b' : '#6b7280' }}>
                        {data.api_key_set ? '✓ API Key 已配置' : '✗ API Key 未配置'}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-16 text-muted-foreground text-sm">
              加载服务状态...
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5 text-amber-500" />
            API 密钥与厂商管理（多厂商 / 多服务独立配置）
          </CardTitle>
          <CardDescription>
            LLM / Embedding / Vision 三类服务可分别选择不同厂商，API Key、Base URL、模型名也独立配置。例：LLM 用本地 llama.cpp、Embedding 用 DashScope、Vision 用 OpenAI 兼容的 vLLM
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* ========== 通用 API 密钥（厂商级公共 Key） ========== */}
          <div className="rounded-md border p-3 space-y-2 bg-muted/20">
            <div className="text-sm font-medium">通用 API 密钥（厂商级，未在下方服务独立配置时自动使用）</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              <ApiKeyInput id="dashscope-api-key" label="DashScope / 通义千问 Key" value={config.dashscope_api_key} onChange={(v) => updateField('dashscope_api_key', v)} placeholder="sk-xxx" hint="Embedding/Vision 默认厂商" />
              <ApiKeyInput id="deepseek-api-key" label="DeepSeek Key" value={config.deepseek_api_key} onChange={(v) => updateField('deepseek_api_key', v)} placeholder="sk-xxx" />
              <ApiKeyInput id="zhipu-api-key" label="智谱 AI Key" value={config.zhipu_api_key} onChange={(v) => updateField('zhipu_api_key', v)} />
              <ApiKeyInput id="baichuan-api-key" label="百川 Key" value={config.baichuan_api_key} onChange={(v) => updateField('baichuan_api_key', v)} />
              <ApiKeyInput id="moonshot-api-key" label="Moonshot / Kimi Key" value={config.moonshot_api_key} onChange={(v) => updateField('moonshot_api_key', v)} />
              <ApiKeyInput id="siliconflow-api-key" label="SiliconFlow / 硅基流动 Key" value={config.siliconflow_api_key} onChange={(v) => updateField('siliconflow_api_key', v)} />
              <ApiKeyInput id="minimax-api-key" label="MiniMax Key" value={config.minimax_api_key} onChange={(v) => updateField('minimax_api_key', v)} />
              <ApiKeyInput id="openai-compatible-api-key" label="OpenAI 兼容 Key（vLLM/llama-server）" value={config.openai_compatible_api_key} onChange={(v) => updateField('openai_compatible_api_key', v)} placeholder="no-key" />
            </div>
          </div>

          {/* ========== 独立服务配置：3 张并排卡 ========== */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* --- LLM 服务卡 --- */}
            <ServiceVendorCard
              title="LLM 文本生成"
              icon={<Brain className="h-4 w-4 text-blue-500" />}
              vendorField="llm_vendor"
              vendorValue={config.llm_vendor}
              apiKeyField="llm_api_key_override"
              apiKeyValue={config.llm_api_key_override}
              baseUrlField="llm_api_base_url_override"
              baseUrlValue={config.llm_api_base_url_override}
              modelField="llm_model_override"
              modelValue={config.llm_model_override}
              vendors={LLM_BACKENDS}
              updateField={updateField}
              testService="llm"
              onTestResult={(r) => handleTestResult('llm', r)}
              config={config}
            />

            {/* --- Embedding 服务卡 --- */}
            <ServiceVendorCard
              title="Embedding 向量化"
              icon={<Search className="h-4 w-4 text-green-500" />}
              vendorField="embedding_vendor"
              vendorValue={config.embedding_vendor}
              apiKeyField="embedding_api_key"
              apiKeyValue={config.embedding_api_key}
              baseUrlField="embedding_api_base_url"
              baseUrlValue={config.embedding_api_base_url}
              modelField="embedding_model_name"
              modelValue={config.embedding_model_name}
              vendors={EMBEDDING_VENDORS}
              updateField={updateField}
              testService="embedding"
              onTestResult={(r) => handleTestResult('embedding', r)}
              config={config}
            />

            {/* --- Vision 服务卡 --- */}
            <ServiceVendorCard
              title="Vision 视觉理解"
              icon={<Eye className="h-4 w-4 text-purple-500" />}
              vendorField="vision_vendor"
              vendorValue={config.vision_vendor}
              apiKeyField="vision_api_key"
              apiKeyValue={config.vision_api_key}
              baseUrlField="vision_api_base_url"
              baseUrlValue={config.vision_api_base_url}
              modelField="vision_model_name"
              modelValue={config.vision_model_name}
              vendors={VISION_VENDORS}
              updateField={updateField}
              testService="vision"
              onTestResult={(r) => handleTestResult('vision', r)}
              config={config}
            />
          </div>

          {/* 兼容说明 */}
          <div className="rounded-md border-l-4 border-cyan-500 bg-cyan-50/50 dark:bg-cyan-950/20 p-3 text-xs space-y-1">
            <div className="font-medium text-cyan-900 dark:text-cyan-200">关于 API 格式兼容性</div>
            <ul className="text-cyan-800 dark:text-cyan-300 list-disc pl-5 space-y-0.5">
              <li><b>留空回退</b>：每个服务的"独立 Key / Base URL"留空时，会自动使用对应厂商的"通用 API 密钥"</li>
              <li><b>OpenAI 兼容格式</b>：DashScope、DeepSeek、Zhipu、Baichuan、Moonshot、SiliconFlow、MiniMax 全部支持 /v1/chat/completions、/v1/embeddings、/v1/models</li>
              <li><b>llama.cpp</b>：启动 llama-server 后即可被 LLM/Embedding/Vision 三服务共用；Embedding 需服务开启 embedding 端点、Vision 需 --mmproj</li>
              <li><b>LoongArch 推荐</b>：LLM=llama.cpp、Embedding=DashScope、Vision=llama.cpp（Qwen2-VL-2B 多模态）</li>
            </ul>
          </div>

          {/* 旧 LLM 后端兼容（保持旧字段不动，新代码不依赖） */}
          <details className="rounded-md border p-3">
            <summary className="text-sm font-medium cursor-pointer text-muted-foreground hover:text-foreground">
              兼容：旧版 LLM 后端配置（llm_backend / llm_model 等）
            </summary>
            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">旧 LLM 后端（兼容字段）</Label>
                <Select value={config.llm_backend || 'dashscope'} onValueChange={(v) => updateField('llm_backend', v)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {LLM_BACKENDS.map(b => <SelectItem key={b.value} value={b.value}>{b.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">旧 LLM 模型（兼容字段）</Label>
                <Input value={config.llm_model || ''} onChange={(e) => updateField('llm_model', e.target.value)} />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">旧 LLM Base URL（兼容字段）</Label>
                <Input value={config.llm_api_base_url || ''} onChange={(e) => updateField('llm_api_base_url', e.target.value)} />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">旧 Embedding 模型（兼容字段）</Label>
                <Input value={config.embedding_model || ''} onChange={(e) => updateField('embedding_model', e.target.value)} />
              </div>
            </div>
          </details>

          {/* 一键测试所有服务 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>连接测试结果（每张卡内已有独立测试按钮）</Label>
            </div>
            <div className="premium-card p-3 space-y-1">
              {testResults.llm && <TestResultBadge result={testResults.llm} />}
              {testResults.embedding && <TestResultBadge result={testResults.embedding} />}
              {testResults.vision && <TestResultBadge result={testResults.vision} />}
              {testResults.ocr && <TestResultBadge result={testResults.ocr} />}
              {!testResults.llm && !testResults.embedding && !testResults.vision && !testResults.ocr && (
                <p className="text-xs text-muted-foreground">在各服务卡上点击"测试"按钮验证</p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

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
            <div className="rounded-lg border border-dashed p-4 text-center max-w-md mx-auto">
              {gpuStatus.gpu.nvidia_driver_available ? (
                <>
                  <AlertTriangle className="h-6 w-6 text-yellow-500 mx-auto mb-2" />
                  <p className="text-sm font-medium text-yellow-600">检测到 NVIDIA GPU 但未启用 CUDA 加速</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {(gpuStatus.gpu.diagnostics?.nvidia_gpu_names?.length ?? 0) > 0
                      ? `GPU: ${gpuStatus.gpu.diagnostics?.nvidia_gpu_names?.join(", ")}`
                      : "NVIDIA GPU 已检测到"}
                    {gpuStatus.gpu.diagnostics?.cuda_driver_version && ` | CUDA 驱动: ${gpuStatus.gpu.diagnostics.cuda_driver_version}`}
                  </p>
                  <div className="mt-2 space-y-1 text-xs text-left max-w-sm mx-auto">
                    {gpuStatus.gpu.diagnostics?.torch_gpu_reason && (
                      <p className="text-yellow-600">⚠ PyTorch: {gpuStatus.gpu.diagnostics.torch_gpu_reason}</p>
                    )}
                    {gpuStatus.gpu.diagnostics?.paddle_gpu_reason && (
                      <p className="text-yellow-600">⚠ PaddlePaddle: {gpuStatus.gpu.diagnostics.paddle_gpu_reason}</p>
                    )}
                  </div>
                  <Button
                    size="sm"
                    className="mt-3 bg-yellow-600 hover:bg-yellow-700 text-white"
                    disabled={installingCudaDeps}
                    onClick={handleInstallCudaDeps}
                  >
                    {installingCudaDeps ? (
                      <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                    ) : (
                      <Download className="mr-1 h-3 w-3" />
                    )}
                    一键安装 CUDA 版 PyTorch
                  </Button>
                  {cudaInstallStatus && (
                    <p className="text-xs text-muted-foreground mt-1">{cudaInstallStatus}</p>
                  )}
                </>
              ) : (
                <>
                  <XCircle className="h-6 w-6 text-muted-foreground mx-auto mb-2" />
                  <p className="text-sm font-medium">未检测到 GPU 设备</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    系统将以 CPU 模式运行，OCR 和视觉模型将使用 API 或 CPU 推理
                  </p>
                </>
              )}
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
                  引擎: {gpuStatus.ocr.engine_type || (gpuStatus.ocr.engine_loaded ? '已加载' : '未加载')} | 语言: {gpuStatus.ocr.language}
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
                  {OCR_BACKENDS.map((b) => {
                    const compat = isLoongarch ? ocrCompat[b.value] : true
                    return (
                      <SelectItem key={b.value} value={b.value}>
                        <div className="flex items-center gap-2">
                          <span>{b.label}</span>
                          {isLoongarch && (
                            <Badge
                              variant={compat === false ? 'destructive' : 'secondary'}
                              className="text-[10px] px-1.5"
                            >
                              {compat === false ? '不兼容' : '可用'}
                            </Badge>
                          )}
                        </div>
                      </SelectItem>
                    )
                  })}
                </SelectContent>
              </Select>
              {isLoongarch && (() => {
                const cur = OCR_BACKENDS.find(b => b.value === config.ocr_backend)
                const curCompat = ocrCompat[config.ocr_backend]
                return (
                  <p className={`text-xs ${curCompat === false ? 'text-red-600' : 'text-amber-700'}`}>
                    {cur?.loongarchHint}
                  </p>
                )
              })()}
              {!isLoongarch && (
                <p className="text-xs text-muted-foreground">
                  auto 自动选择可用后端（RapidOCR → PaddleOCR → API）
                </p>
              )}
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
                value={
                  config.vision_backend === 'local'
                    ? config.local_vision_model
                    : config.vision_backend
                }
                onValueChange={(v) => {
                  if (v === 'auto' || v === 'dashscope') {
                    updateField('vision_backend', v)
                  } else {
                    updateField('vision_backend', 'local')
                    updateField('local_vision_model', v)
                  }
                }}
              >
                <SelectTrigger id="vision-backend">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">
                    <div className="flex items-center gap-2">
                      <span>自动检测</span>
                      {isLoongarch && (
                        <Badge variant="secondary" className="text-[10px] px-1.5">可用</Badge>
                      )}
                    </div>
                  </SelectItem>
                  <SelectItem value="dashscope">
                    <div className="flex items-center gap-2">
                      <span>DashScope API</span>
                      {isLoongarch && (
                        <Badge variant="secondary" className="text-[10px] px-1.5">LoongArch 推荐</Badge>
                      )}
                    </div>
                  </SelectItem>
                  {models
                    .filter((m) => m.type === 'vision' && m.downloaded)
                    .map((m) => {
                      const localCompat = isLoongarch ? visionCompat['local'] : true
                      return (
                        <SelectItem key={m.id} value={m.id}>
                          <div className="flex items-center gap-2">
                            <span>{m.name}（本地）</span>
                            {isLoongarch && (
                              <Badge
                                variant={localCompat === false ? 'destructive' : 'secondary'}
                                className="text-[10px] px-1.5"
                              >
                                {localCompat === false ? '需自行编译' : '可用'}
                              </Badge>
                            )}
                          </div>
                        </SelectItem>
                      )
                    })}
                </SelectContent>
              </Select>
              {isLoongarch && (
                <p className="text-xs text-amber-700">
                  LoongArch 上本地视觉模型需自行编译 llama.cpp + GGUF（无 PyTorch GPU）。推荐使用 DashScope API。
                </p>
              )}
              {!isLoongarch && (
                <p className="text-xs text-muted-foreground">
                  已下载的视觉模型会自动出现在选项中，选择后使用本地推理
                </p>
              )}
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
              {models.map((model) => {
                // 计算 LoongArch 兼容性与提示
                let loongarchBadge: { text: string; variant: 'destructive' | 'secondary' | 'outline' } | null = null
                let loongarchTip = ''
                if (isLoongarch) {
                  if (model.type === 'vision') {
                    loongarchBadge = { text: 'GGUF 可用', variant: 'secondary' }
                    loongarchTip = 'GGUF 量化版，llama.cpp 多模态推理可用。下载后启动 llama-server 加载此模型即可。'
                  } else if (model.id === 'PaddleOCR/PPOCRv4') {
                    loongarchBadge = { text: '不兼容', variant: 'destructive' }
                    loongarchTip = 'PaddleOCR 依赖 paddlepaddle-gpu，LoongArch 上无官方预编译 wheel（需从源码编译，难度高）。推荐使用 RapidOCR 或 DashScope API 完成 OCR。'
                  } else if (model.type === 'llm') {
                    loongarchBadge = { text: 'GGUF 推荐', variant: 'secondary' }
                    loongarchTip = 'GGUF 量化版文本模型，下载后用 llama-server 启动本地 LLM 服务。'
                  } else if (model.type === 'ocr') {
                    loongarchBadge = { text: '兼容', variant: 'secondary' }
                  }
                }
                return (
                <div
                  key={model.id}
                  className="rounded-lg border p-3 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium">{model.name}</span>
                      {model.recommended && (
                        <Badge variant="default" className="text-xs bg-blue-500">推荐</Badge>
                      )}
                      <Badge variant="outline" className="text-xs">
                        {model.type === 'vision' ? '视觉' : model.type === 'ocr' ? 'OCR' : model.type === 'llm' ? 'LLM' : model.type}
                      </Badge>
                      <span className="text-xs text-muted-foreground">{model.size}</span>
                      {loongarchBadge && (
                        <Badge variant={loongarchBadge.variant} className="text-[10px] px-1.5">
                          LoongArch · {loongarchBadge.text}
                        </Badge>
                      )}
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
                              disabled={settingVisionModel !== null}
                              onClick={() => handleSetVisionModel(model.id)}
                            >
                              {settingVisionModel === model.id ? (
                                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                              ) : null}
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
                      ) : model.download_status === 'downloading' || model.download_status === 'installing_deps' ? (
                        <div className="flex items-center gap-2 w-40">
                          <div className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden">
                            <div
                              className="h-full rounded-full bg-blue-500 transition-all"
                              style={{ width: `${model.download_status === 'installing_deps' ? 100 : model.download_progress}%` }}
                            />
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {model.download_status === 'installing_deps' ? '安装依赖' : `${model.download_progress}%`}
                          </span>
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
                  {isLoongarch && loongarchTip && (
                    <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                      {loongarchTip}
                    </p>
                  )}
                </div>
                )
              })}
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
            配置 AI 问答和作业指引生成使用的语言模型，支持本地模型和自定义API
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="llm-backend">LLM 后端</Label>
              <Select
                value={config.llm_backend}
                onValueChange={(v) => {
                  updateField('llm_backend', v)
                  if (v === 'dashscope') {
                    updateField('llm_model', 'qwen-max')
                    setLlmModels(LLM_MODELS.map(m => ({ id: m.value, name: m.label })))
                  } else if (v === 'llama_cpp') {
                    fetchLlmModels(v, config.llm_api_base_url || 'http://localhost:11434/v1', config.llm_api_key)
                  } else {
                    fetchLlmModels(v, config.llm_api_base_url, config.llm_api_key)
                  }
                }}
              >
                <SelectTrigger id="llm-backend">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LLM_BACKENDS.map((b) => {
                    const compat = isLoongarch ? llmCompat[b.value] : true
                    return (
                      <SelectItem key={b.value} value={b.value}>
                        <div className="flex items-center gap-2">
                          <span>{b.label}</span>
                          {isLoongarch && (
                            <Badge
                              variant={compat === false ? 'destructive' : 'secondary'}
                              className="text-[10px] px-1.5"
                            >
                              {compat === false ? '不兼容' : '可用'}
                            </Badge>
                          )}
                        </div>
                      </SelectItem>
                    )
                  })}
                </SelectContent>
              </Select>
              {isLoongarch && (() => {
                const cur = LLM_BACKENDS.find(b => b.value === config.llm_backend)
                const curCompat = llmCompat[config.llm_backend]
                return (
                  <p className={`text-xs ${curCompat === false ? 'text-red-600' : 'text-amber-700'}`}>
                    {cur?.loongarchHint}
                    {curCompat === false && ' · 当前架构不兼容，可手动配置但服务将无法启动'}
                  </p>
                )
              })()}
              <div className="flex items-center gap-2">
                {llmStatus?.available ? (
                  <Badge variant="default" className="text-xs bg-green-500">
                    <Wifi className="h-3 w-3 mr-1" />
                    已连接
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="text-xs">
                    <WifiOff className="h-3 w-3 mr-1" />
                    未连接
                  </Badge>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs h-5 px-1"
                  onClick={fetchLlmStatus}
                >
                  <RefreshCw className="h-3 w-3" />
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="llm-model">LLM 模型</Label>
              {config.llm_backend === 'dashscope' ? (
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
              ) : config.llm_backend === 'minimax' ? (
                <Select
                  value={config.llm_model}
                  onValueChange={(v) => updateField('llm_model', v)}
                >
                  <SelectTrigger id="llm-model">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MINIMAX_MODELS.map((m) => (
                      <SelectItem key={m.value} value={m.value}>
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : config.llm_backend === 'deepseek' ? (
                <Select
                  value={config.llm_model}
                  onValueChange={(v) => updateField('llm_model', v)}
                >
                  <SelectTrigger id="llm-model">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DEEPSEEK_MODELS.map((m) => (
                      <SelectItem key={m.value} value={m.value}>
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : config.llm_backend === 'zhipu' ? (
                <Select
                  value={config.llm_model}
                  onValueChange={(v) => updateField('llm_model', v)}
                >
                  <SelectTrigger id="llm-model">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ZHIPU_MODELS.map((m) => (
                      <SelectItem key={m.value} value={m.value}>
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : config.llm_backend === 'baichuan' ? (
                <Select
                  value={config.llm_model}
                  onValueChange={(v) => updateField('llm_model', v)}
                >
                  <SelectTrigger id="llm-model">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {BAICHUAN_MODELS.map((m) => (
                      <SelectItem key={m.value} value={m.value}>
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : config.llm_backend === 'moonshot' ? (
                <Select
                  value={config.llm_model}
                  onValueChange={(v) => updateField('llm_model', v)}
                >
                  <SelectTrigger id="llm-model">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MOONSHOT_MODELS.map((m) => (
                      <SelectItem key={m.value} value={m.value}>
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : config.llm_backend === 'siliconflow' ? (
                <Select
                  value={config.llm_model}
                  onValueChange={(v) => updateField('llm_model', v)}
                >
                  <SelectTrigger id="llm-model">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SILICONFLOW_MODELS.map((m) => (
                      <SelectItem key={m.value} value={m.value}>
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : llmModels.length > 0 ? (
                <Select
                  value={config.llm_model}
                  onValueChange={(v) => updateField('llm_model', v)}
                >
                  <SelectTrigger id="llm-model">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {llmModels.map((m) => (
                      <SelectItem key={m.id} value={m.id}>
                        {m.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <Input
                  id="llm-model"
                  value={config.llm_model}
                  onChange={(e) => updateField('llm_model', e.target.value)}
                  placeholder="输入模型名称"
                />
              )}
              {config.llm_backend !== 'dashscope' && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs h-5 px-1"
                  disabled={llmModelsLoading}
                  onClick={() => fetchLlmModels(config.llm_backend, config.llm_api_base_url, config.llm_api_key)}
                >
                  {llmModelsLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
                  刷新模型列表
                </Button>
              )}
            </div>

            {config.llm_backend === 'openai_compatible' && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="llm-api-base-url">API 基础 URL</Label>
                  <Input
                    id="llm-api-base-url"
                    value={config.llm_api_base_url}
                    onChange={(e) => updateField('llm_api_base_url', e.target.value)}
                    placeholder="http://localhost:8000/v1"
                  />
                  <p className="text-xs text-muted-foreground">
                    OpenAI 兼容 API 的基础地址，如 vLLM、LMStudio 等
                  </p>
                </div>
                <ApiKeyInput
                  id="llm-api-key"
                  label="API 密钥"
                  value={config.llm_api_key}
                  onChange={(v) => updateField('llm_api_key', v)}
                  placeholder="sk-..."
                  hint="部分 API 不需要密钥可留空"
                />
              </>
            )}

            {config.llm_backend === 'ollama' && (
              <div className="space-y-2">
                <Label htmlFor="ollama-url">Ollama 服务地址</Label>
                <Input
                  id="ollama-url"
                  value={config.llm_api_base_url}
                  onChange={(e) => updateField('llm_api_base_url', e.target.value)}
                  placeholder="http://localhost:11434"
                />
                <p className="text-xs text-muted-foreground">
                  Ollama 默认地址 http://localhost:11434，支持自定义
                </p>
              </div>
            )}

            {config.llm_backend === 'llama_cpp' && (
              <div className="space-y-2">
                <Label htmlFor="llama-cpp-url">llama-server 服务地址</Label>
                <Input
                  id="llama-cpp-url"
                  value={config.llm_api_base_url}
                  onChange={(e) => updateField('llm_api_base_url', e.target.value)}
                  placeholder="http://localhost:11434/v1"
                />
                <p className="text-xs text-muted-foreground">
                  llama-server 默认地址 http://localhost:11434/v1。启动命令：
                  <code className="bg-muted px-1 rounded ml-1">llama-server -m ~/models/*.gguf --host 0.0.0.0 --port 11434</code>
                </p>
                {systemInfo?.llama_cpp?.available && (
                  <p className="text-xs text-green-600">
                    ✓ 已检测到 llama.cpp 二进制，可直接启动本地推理
                  </p>
                )}
              </div>
            )}

            {config.llm_backend === 'minimax' && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="minimax-api-url">MiniMax API 地址</Label>
                  <Input
                    id="minimax-api-url"
                    value={config.llm_api_base_url || 'https://api.minimax.chat/v1'}
                    onChange={(e) => updateField('llm_api_base_url', e.target.value)}
                    placeholder="https://api.minimax.chat/v1"
                  />
                  <p className="text-xs text-muted-foreground">
                    MiniMax API 基础地址，默认使用 Token Plan 端点
                  </p>
                </div>
                <ApiKeyInput
                  id="minimax-api-key"
                  label="MiniMax API 密钥"
                  value={config.llm_api_key}
                  onChange={(v) => updateField('llm_api_key', v)}
                  placeholder="sk-xxxxxxxxxxxxxxxx"
                  hint={
                    <span>
                      从{' '}
                      <a href="https://platform.minimaxi.com/user-center/payment/token-plan" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">platform.minimaxi.com</a>{' '}购买 Token Plan 获取 API 密钥
                    </span>
                  }
                />
              </>
            )}

            {config.llm_backend === 'deepseek' && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="deepseek-api-url">DeepSeek API 地址</Label>
                  <Input
                    id="deepseek-api-url"
                    value={config.llm_api_base_url || 'https://api.deepseek.com/v1'}
                    onChange={(e) => updateField('llm_api_base_url', e.target.value)}
                    placeholder="https://api.deepseek.com/v1"
                  />
                  <p className="text-xs text-muted-foreground">DeepSeek API 基础地址</p>
                </div>
                <ApiKeyInput
                  id="deepseek-api-key"
                  label="DeepSeek API 密钥"
                  value={config.llm_api_key}
                  onChange={(v) => updateField('llm_api_key', v)}
                  placeholder="sk-xxxxxxxxxxxxxxxx"
                  hint={
                    <span>
                      从{' '}
                      <a href="https://platform.deepseek.com" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">platform.deepseek.com</a>{' '}获取 API 密钥
                    </span>
                  }
                />
              </>
            )}

            {config.llm_backend === 'zhipu' && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="zhipu-api-url">智谱AI API 地址</Label>
                  <Input
                    id="zhipu-api-url"
                    value={config.llm_api_base_url || 'https://open.bigmodel.cn/api/paas/v4'}
                    onChange={(e) => updateField('llm_api_base_url', e.target.value)}
                    placeholder="https://open.bigmodel.cn/api/paas/v4"
                  />
                  <p className="text-xs text-muted-foreground">智谱AI API 基础地址</p>
                </div>
                <ApiKeyInput
                  id="zhipu-api-key"
                  label="智谱AI API 密钥"
                  value={config.llm_api_key}
                  onChange={(v) => updateField('llm_api_key', v)}
                  placeholder="sk-xxxxxxxxxxxxxxxx"
                  hint={
                    <span>
                      从{' '}
                      <a href="https://open.bigmodel.cn" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">open.bigmodel.cn</a>{' '}获取 API 密钥
                    </span>
                  }
                />
              </>
            )}

            {config.llm_backend === 'baichuan' && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="baichuan-api-url">百川智能 API 地址</Label>
                  <Input
                    id="baichuan-api-url"
                    value={config.llm_api_base_url || 'https://api.baichuan-ai.com/v1'}
                    onChange={(e) => updateField('llm_api_base_url', e.target.value)}
                    placeholder="https://api.baichuan-ai.com/v1"
                  />
                  <p className="text-xs text-muted-foreground">百川智能 API 基础地址</p>
                </div>
                <ApiKeyInput
                  id="baichuan-api-key"
                  label="百川智能 API 密钥"
                  value={config.llm_api_key}
                  onChange={(v) => updateField('llm_api_key', v)}
                  placeholder="sk-xxxxxxxxxxxxxxxx"
                  hint={
                    <span>
                      从{' '}
                      <a href="https://www.baichuan-ai.com" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">www.baichuan-ai.com</a>{' '}获取 API 密钥
                    </span>
                  }
                />
              </>
            )}

            {config.llm_backend === 'moonshot' && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="moonshot-api-url">Kimi API 地址</Label>
                  <Input
                    id="moonshot-api-url"
                    value={config.llm_api_base_url || 'https://api.moonshot.cn/v1'}
                    onChange={(e) => updateField('llm_api_base_url', e.target.value)}
                    placeholder="https://api.moonshot.cn/v1"
                  />
                  <p className="text-xs text-muted-foreground">月之暗面 API 基础地址</p>
                </div>
                <ApiKeyInput
                  id="moonshot-api-key"
                  label="Kimi API 密钥"
                  value={config.llm_api_key}
                  onChange={(v) => updateField('llm_api_key', v)}
                  placeholder="sk-xxxxxxxxxxxxxxxx"
                  hint={
                    <span>
                      从{' '}
                      <a href="https://platform.moonshot.cn" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">platform.moonshot.cn</a>{' '}获取 API 密钥
                    </span>
                  }
                />
              </>
            )}

            {config.llm_backend === 'siliconflow' && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="siliconflow-api-url">硅基流动 API 地址</Label>
                  <Input
                    id="siliconflow-api-url"
                    value={config.llm_api_base_url || 'https://api.siliconflow.cn/v1'}
                    onChange={(e) => updateField('llm_api_base_url', e.target.value)}
                    placeholder="https://api.siliconflow.cn/v1"
                  />
                  <p className="text-xs text-muted-foreground">硅基流动 API 基础地址</p>
                </div>
                <ApiKeyInput
                  id="siliconflow-api-key"
                  label="硅基流动 API 密钥"
                  value={config.llm_api_key}
                  onChange={(v) => updateField('llm_api_key', v)}
                  placeholder="sk-xxxxxxxxxxxxxxxx"
                  hint={
                    <span>
                      从{' '}
                      <a href="https://www.siliconflow.cn" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">www.siliconflow.cn</a>{' '}获取 API 密钥
                    </span>
                  }
                />
              </>
            )}

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
