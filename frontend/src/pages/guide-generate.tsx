import { useState, useEffect, useCallback } from 'react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/css-tabs'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { api } from '@/lib/api'
import {
  Sparkles,
  History,
  Download,
  Eye,
  AlertTriangle,
  Clock,
  Wrench,
  Lightbulb,
  CheckCircle2,
  Shield,
  Loader2,
  FileText,
} from 'lucide-react'

type SafetyLevel = 'low' | 'standard' | 'high' | 'critical'
type DetailLevel = 'brief' | 'medium' | 'detailed'

interface GuideStep {
  step_number: number
  title: string
  description: string
  warnings: string[]
  tools_required: string[]
  estimated_time: string
  tips: string[]
}

interface GuideResult {
  title: string
  task_summary: string
  preparation: string[]
  safety_notes: string[]
  steps: GuideStep[]
  completion_criteria: string[]
  compliance_checks?: ComplianceCheck[]
  personalized_tips?: string[]
}

interface ComplianceCheck {
  category: string
  rule: string
  description: string
  severity: string
  passed: boolean
  status: string
}

interface GuideHistoryItem {
  guide_id: string
  title: string
  task_description: string
  equipment_type: string
  equipment_model: string
  safety_level: SafetyLevel
  created_at: string
}

const SAFETY_LEVEL_MAP: Record<SafetyLevel, { label: string; color: string; bg: string }> = {
  low: { label: '低', color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/30' },
  standard: { label: '标准', color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/30' },
  high: { label: '高', color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/30' },
  critical: { label: '关键', color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/30' },
}

const DETAIL_LEVEL_MAP: Record<DetailLevel, string> = {
  brief: '简要',
  medium: '中等',
  detailed: '详细',
}

export default function GuideGeneratePage() {
  const [taskDescription, setTaskDescription] = useState('')
  const [equipmentType, setEquipmentType] = useState('')
  const [equipmentModel, setEquipmentModel] = useState('')
  const [workEnvironment, setWorkEnvironment] = useState('')
  const [safetyLevel, setSafetyLevel] = useState<SafetyLevel>('standard')
  const [detailLevel, setDetailLevel] = useState<DetailLevel>('medium')

  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<GuideResult | null>(null)

  const [historyList, setHistoryList] = useState<GuideHistoryItem[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  const [detailOpen, setDetailOpen] = useState(false)
  const [detailData, setDetailData] = useState<GuideResult | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true)
    try {
      const res = await api.get<{ guides: GuideHistoryItem[] }>('/guide/list')
      setHistoryList(res.data.guides || [])
    } catch {
      setHistoryList([])
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  const handleGenerate = async () => {
    if (!taskDescription.trim()) return
    setGenerating(true)
    setResult(null)
    try {
      const res = await api.post<GuideResult>('/guide/generate', {
        task_description: taskDescription.trim(),
        equipment_model: equipmentModel.trim() || undefined,
        equipment_type: equipmentType.trim() || undefined,
        work_environment: workEnvironment.trim() || undefined,
        safety_level: safetyLevel,
        detail_level: detailLevel,
      })
      setResult(res.data)
      fetchHistory()
    } catch {
      setResult(null)
    } finally {
      setGenerating(false)
    }
  }

  const handleViewDetail = async (guideId: string) => {
    setDetailOpen(true)
    setDetailData(null)
    setDetailLoading(true)
    try {
      const res = await api.get(`/guide/${guideId}`)
      const raw = res.data
      const guideContent = raw.guide_content || raw
      setDetailData(guideContent as GuideResult)
    } catch {
      setDetailData(null)
    } finally {
      setDetailLoading(false)
    }
  }

  const handleExport = async (guideId: string) => {
    try {
      const res = await api.get(`/guide/export/${guideId}`, { responseType: 'blob' })
      const blob = new Blob([res.data], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `guide_${guideId}.txt`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      setErrorMsg('导出指引失败，请稍后重试')
    }
  }

  const renderGuideContent = (data: GuideResult) => (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold">{data.title}</h2>
        <p className="mt-2 text-muted-foreground">{data.task_summary}</p>
      </div>

      <Separator />

      {data.preparation.length > 0 && (
        <div>
          <h3 className="mb-2 flex items-center gap-2 font-semibold">
            <CheckCircle2 className="h-4 w-4 text-green-400" />
            准备工作
          </h3>
          <ul className="ml-6 list-disc space-y-1 text-sm text-muted-foreground">
            {data.preparation.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {data.safety_notes.length > 0 && (
        <div>
          <h3 className="mb-2 flex items-center gap-2 font-semibold">
            <Shield className="h-4 w-4 text-red-400" />
            安全注意事项
          </h3>
          <div className="space-y-2">
            {data.safety_notes.map((note, i) => (
              <div
                key={i}
                className="flex items-start gap-2 rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm"
              >
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
                <span>{note}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.steps.length > 0 && (
        <div>
          <h3 className="mb-3 flex items-center gap-2 font-semibold">
            <FileText className="h-4 w-4 text-blue-400" />
            作业步骤
          </h3>
          <div className="space-y-4">
            {data.steps.map((step) => (
              <Card key={step.step_number}>
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-3">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                      {step.step_number}
                    </span>
                    <CardTitle className="text-base">{step.title}</CardTitle>
                    {step.estimated_time && (
                      <Badge variant="outline" className="ml-auto gap-1">
                        <Clock className="h-3 w-3" />
                        {step.estimated_time}
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm text-muted-foreground">{step.description}</p>

                  {step.warnings.length > 0 && (
                    <div className="space-y-1.5">
                      {step.warnings.map((w, i) => (
                        <div
                          key={i}
                          className="flex items-start gap-2 rounded border border-red-500/30 bg-red-500/10 p-2 text-xs text-red-300"
                        >
                          <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                          <span>{w}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {step.tools_required.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Wrench className="h-3.5 w-3.5 text-muted-foreground" />
                      {step.tools_required.map((tool, i) => (
                        <Badge key={i} variant="secondary" className="text-xs">
                          {tool}
                        </Badge>
                      ))}
                    </div>
                  )}

                  {step.tips.length > 0 && (
                    <div className="space-y-1.5">
                      {step.tips.map((tip, i) => (
                        <div
                          key={i}
                          className="flex items-start gap-2 rounded border border-yellow-500/30 bg-yellow-500/10 p-2 text-xs text-yellow-300"
                        >
                          <Lightbulb className="mt-0.5 h-3 w-3 shrink-0" />
                          <span>{tip}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {data.completion_criteria.length > 0 && (
        <div>
          <h3 className="mb-2 flex items-center gap-2 font-semibold">
            <CheckCircle2 className="h-4 w-4 text-green-400" />
            完成标准
          </h3>
          <ul className="ml-6 list-disc space-y-1 text-sm text-muted-foreground">
            {data.completion_criteria.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}

      {data.compliance_checks && data.compliance_checks.length > 0 && (
        <div>
          <h3 className="mb-2 flex items-center gap-2 font-semibold">
            <Shield className="h-4 w-4 text-blue-400" />
            合规校验
            <Badge variant="secondary" className="ml-1 text-xs">
              {data.compliance_checks.filter(c => c.passed).length}/{data.compliance_checks.length} 通过
            </Badge>
          </h3>
          <div className="space-y-2">
            {data.compliance_checks.map((check, i) => (
              <div
                key={i}
                className={`flex items-start gap-2 rounded-md border p-2 text-sm ${
                  check.passed
                    ? 'border-green-800 bg-green-950/30'
                    : check.severity === 'critical'
                    ? 'border-red-800 bg-red-950/30'
                    : 'border-yellow-800 bg-yellow-950/30'
                }`}
              >
                {check.passed ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-400" />
                ) : (
                  <AlertTriangle className={`mt-0.5 h-4 w-4 shrink-0 ${check.severity === 'critical' ? 'text-red-400' : 'text-yellow-400'}`} />
                )}
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{check.rule}</span>
                    <Badge variant="outline" className="text-xs">{check.category}</Badge>
                    {check.severity === 'critical' && (
                      <Badge variant="destructive" className="text-xs">关键</Badge>
                    )}
                  </div>
                  <p className="text-muted-foreground">{check.description}</p>
                </div>
                <Badge className={check.passed ? 'bg-green-600' : check.severity === 'critical' ? 'bg-red-600' : 'bg-yellow-600'}>
                  {check.passed ? '通过' : '待确认'}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.personalized_tips && data.personalized_tips.length > 0 && (
        <div>
          <h3 className="mb-2 flex items-center gap-2 font-semibold">
            <Lightbulb className="h-4 w-4 text-yellow-400" />
            个性化提示
          </h3>
          <div className="space-y-1">
            {data.personalized_tips.map((tip, i) => (
              <div key={i} className="flex items-start gap-2 rounded-md bg-blue-950/30 border border-blue-800 p-2 text-sm">
                <Lightbulb className="mt-0.5 h-3 w-3 shrink-0 text-blue-400" />
                <span>{tip}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )

  const safetyInfo = SAFETY_LEVEL_MAP[safetyLevel]

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">📝 作业指引生成</h1>

      <Tabs defaultValue="generate" className="w-full">
        <TabsList>
          <TabsTrigger value="generate" className="gap-1.5">
            <Sparkles className="h-4 w-4" />
            生成指引
          </TabsTrigger>
          <TabsTrigger value="history" className="gap-1.5">
            <History className="h-4 w-4" />
            历史指引
          </TabsTrigger>
        </TabsList>

        <TabsContent value="generate">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>填写指引参数</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>
                    任务描述 <span className="text-red-400">*</span>
                  </Label>
                  <Textarea
                    value={taskDescription}
                    onChange={(e) => setTaskDescription(e.target.value)}
                    placeholder="请详细描述作业任务内容，包括操作对象、目的、要求等（1-5000字）"
                    rows={5}
                    maxLength={5000}
                  />
                  <p className="text-xs text-muted-foreground">
                    {taskDescription.length}/5000
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>设备类型</Label>
                    <Input
                      value={equipmentType}
                      onChange={(e) => setEquipmentType(e.target.value)}
                      placeholder="如：变压器、开关柜"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>设备型号</Label>
                    <Input
                      value={equipmentModel}
                      onChange={(e) => setEquipmentModel(e.target.value)}
                      placeholder="如：SZ11-63000/110"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>作业环境</Label>
                  <Textarea
                    value={workEnvironment}
                    onChange={(e) => setWorkEnvironment(e.target.value)}
                    placeholder="描述作业环境条件，如：户外、高温、受限空间等"
                    rows={3}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>安全等级</Label>
                    <Select value={safetyLevel} onValueChange={(v) => setSafetyLevel(v as SafetyLevel)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="low">低</SelectItem>
                        <SelectItem value="standard">标准</SelectItem>
                        <SelectItem value="high">高</SelectItem>
                        <SelectItem value="critical">关键</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>详细程度</Label>
                    <Select value={detailLevel} onValueChange={(v) => setDetailLevel(v as DetailLevel)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="brief">简要</SelectItem>
                        <SelectItem value="medium">中等</SelectItem>
                        <SelectItem value="detailed">详细</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="flex items-center gap-2 rounded-md border p-3">
                  <Shield className={`h-4 w-4 ${safetyInfo.color}`} />
                  <span className="text-sm">当前安全等级：</span>
                  <Badge variant="outline" className={`${safetyInfo.bg} ${safetyInfo.color}`}>
                    {safetyInfo.label}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    / 详细程度：{DETAIL_LEVEL_MAP[detailLevel]}
                  </span>
                </div>

                <Button
                  className="w-full"
                  onClick={handleGenerate}
                  disabled={generating || !taskDescription.trim()}
                >
                  {generating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      正在生成...
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-4 w-4" />
                      生成指引
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>生成结果</CardTitle>
              </CardHeader>
              <CardContent>
                {generating ? (
                  <div className="flex flex-col items-center justify-center py-20">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    <p className="mt-4 text-muted-foreground">AI 正在生成作业指引，请稍候...</p>
                  </div>
                ) : result ? (
                  <ScrollArea className="h-[calc(100vh-340px)]">
                    {renderGuideContent(result)}
                  </ScrollArea>
                ) : (
                  <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
                    <FileText className="h-12 w-12 mb-4 opacity-30" />
                    <p>填写左侧表单后点击"生成指引"</p>
                    <p className="mt-1 text-sm">生成结果将在此处展示</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="history">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>历史指引列表</CardTitle>
              <Button variant="outline" size="sm" onClick={fetchHistory} disabled={historyLoading}>
                {historyLoading ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <History className="mr-1 h-4 w-4" />}
                刷新
              </Button>
            </CardHeader>
            <CardContent>
              {historyLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="h-12 animate-pulse rounded bg-muted" />
                  ))}
                </div>
              ) : historyList.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <History className="h-12 w-12 mb-4 opacity-30" />
                  <p>暂无历史指引</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>标题</TableHead>
                      <TableHead>设备类型</TableHead>
                      <TableHead>设备型号</TableHead>
                      <TableHead>安全等级</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead className="text-right">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {historyList.map((item) => {
                      const sl = SAFETY_LEVEL_MAP[item.safety_level]
                      return (
                        <TableRow key={item.guide_id}>
                          <TableCell className="font-medium max-w-[200px] truncate">
                            {item.title}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {item.equipment_type || '-'}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {item.equipment_model || '-'}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className={`${sl.bg} ${sl.color}`}>
                              {sl.label}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {new Date(item.created_at).toLocaleString('zh-CN')}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleViewDetail(item.guide_id)}
                              >
                                <Eye className="mr-1 h-4 w-4" />
                                查看
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleExport(item.guide_id)}
                              >
                                <Download className="mr-1 h-4 w-4" />
                                导出
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>指引详情</DialogTitle>
          </DialogHeader>
          {detailLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : detailData ? (
            <ScrollArea className="max-h-[65vh] pr-4">
              {renderGuideContent(detailData)}
            </ScrollArea>
          ) : (
            <div className="py-12 text-center text-muted-foreground">加载失败</div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
