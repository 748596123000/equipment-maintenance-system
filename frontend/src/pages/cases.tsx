import { useState, useEffect, useCallback } from 'react'
import { useAuthStore } from '@/stores/auth-store'
import { api } from '@/lib/api'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/css-tabs'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from '@/components/ui/table'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '@/components/ui/dialog'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Search, Plus, Check, X, Trash2, ChevronLeft, ChevronRight, Eye, Wrench,
  FileText, Clock, CheckCircle2, XCircle, AlertTriangle, Sparkles,
} from 'lucide-react'
import { useTheme, COLORS } from '@/hooks/useTheme'
import { GradientText } from '@/components/ui/gradient-text'

const LOCAL_COLORS = COLORS

interface CaseItem {
  case_id: string; title: string; description: string; device_model: string
  status: 'pending_review' | 'approved' | 'rejected'; created_at: string
}
interface CaseDetail extends CaseItem {
  fault_analysis: string; repair_process: string; lessons_learned: string
  tags: string[]; author_id: string; equipment_type: string; equipment_model: string
  fault_description: string; repair_result: string
}
interface Pagination { page: number; page_size: number; total: number; total_pages: number }

export default function CasesPage() {
  const user = useAuthStore((s) => s.user)
  const { theme } = useTheme()
  const isLight = theme === 'light'
  const colors = isLight ? COLORS.light : COLORS.dark
  const isAdmin = user?.role === 'admin'
  const [mounted, setMounted] = useState(false)
  const [activeTab, setActiveTab] = useState('list')
  
  // Dynamic STATUS_MAP based on theme
  const STATUS_MAP: Record<string, { label: string; color: string; icon: typeof CheckCircle2 }> = {
    pending_review: { label: '待审核', color: colors.CYBER_YELLOW, icon: Clock },
    approved: { label: '已通过', color: colors.CYBER_GREEN, icon: CheckCircle2 },
    rejected: { label: '已拒绝', color: colors.CYBER_RED, icon: XCircle },
  }
  const [cases, setCases] = useState<CaseItem[]>([])
  const [pagination, setPagination] = useState<Pagination>({ page: 1, page_size: 20, total: 0, total_pages: 0 })
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [loading, setLoading] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailData, setDetailData] = useState<CaseDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [form, setForm] = useState({
    title: '', equipment_type: '', equipment_model: '', fault_description: '',
    fault_analysis: '', repair_process: '', repair_result: '', lessons_learned: '', tags: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [reviewCases, setReviewCases] = useState<CaseItem[]>([])
  const [reviewLoading, setReviewLoading] = useState(false)
  const [approveDialogOpen, setApproveDialogOpen] = useState(false)
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false)
  const [reviewTarget, setReviewTarget] = useState<CaseItem | null>(null)
  const [reviewComment, setReviewComment] = useState('')
  const [reviewSubmitting, setReviewSubmitting] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => { setMounted(true) }, [])

  const fetchCases = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { page: pagination.page, page_size: pagination.page_size }
      if (statusFilter !== 'all') params.status = statusFilter
      const res = await api.get<{ cases: CaseItem[]; pagination: Pagination }>('/case/list', { params })
      setCases(res.data.cases || [])
      setPagination(res.data.pagination || pagination)
    } catch { setCases([]) } finally { setLoading(false) }
  }, [pagination.page, pagination.page_size, statusFilter])

  const fetchReviewCases = useCallback(async () => {
    if (!isAdmin) return
    setReviewLoading(true)
    try {
      const res = await api.get<{ cases: CaseItem[] }>('/case/list', { params: { page: 1, page_size: 100, status: 'pending_review' } })
      setReviewCases(res.data.cases || [])
    } catch { setReviewCases([]) } finally { setReviewLoading(false) }
  }, [isAdmin])

  useEffect(() => { fetchCases() }, [fetchCases])
  useEffect(() => { if (activeTab === 'review' && isAdmin) fetchReviewCases() }, [activeTab, isAdmin, fetchReviewCases])

  const handleSearch = useCallback(async () => {
    if (!searchKeyword.trim()) { fetchCases(); return }
    setLoading(true)
    try {
      const res = await api.post<{ cases: CaseItem[]; pagination: Pagination }>('/case/search', { query: searchKeyword.trim(), page: 1, page_size: pagination.page_size })
      setCases(res.data.cases || [])
      setPagination(res.data.pagination || pagination)
    } catch { setCases([]) } finally { setLoading(false) }
  }, [searchKeyword, pagination.page_size, fetchCases])

  const openDetail = useCallback(async (caseId: string) => {
    setDetailLoading(true); setDetailOpen(true)
    try {
      const res = await api.get<CaseDetail>(`/case/${caseId}`)
      setDetailData(res.data)
    } catch { setDetailData(null) } finally { setDetailLoading(false) }
  }, [])

  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return
    try {
      await api.delete(`/case/${deleteTarget}`)
      fetchCases()
      if (isAdmin) fetchReviewCases()
    } catch { setErrorMsg('删除案例失败，请稍后重试') }
    finally { setDeleteDialogOpen(false); setDeleteTarget(null) }
  }, [deleteTarget, fetchCases, isAdmin, fetchReviewCases])

  const handleCreate = useCallback(async () => {
    if (!form.title.trim() || !form.equipment_type.trim() || !form.fault_description.trim()) return
    setSubmitting(true)
    try {
      const tags = form.tags.split(',').map(t => t.trim()).filter(Boolean)
      await api.post('/case/create', { title: form.title.trim(), equipment_type: form.equipment_type.trim(), equipment_model: form.equipment_model.trim(), fault_description: form.fault_description.trim(), fault_analysis: form.fault_analysis.trim(), repair_process: form.repair_process.trim(), repair_result: form.repair_result.trim(), lessons_learned: form.lessons_learned.trim(), tags })
      setForm({ title: '', equipment_type: '', equipment_model: '', fault_description: '', fault_analysis: '', repair_process: '', repair_result: '', lessons_learned: '', tags: '' })
      setActiveTab('list'); fetchCases()
    } catch { setErrorMsg('创建案例失败，请检查填写内容') } finally { setSubmitting(false) }
  }, [form, fetchCases])

  const handleApprove = useCallback(async () => {
    if (!reviewTarget) return
    setReviewSubmitting(true)
    try {
      await api.post('/case/review', { case_id: reviewTarget.case_id, status: 'approved', review_comment: reviewComment })
      fetchReviewCases(); fetchCases()
    } catch { setErrorMsg('审核通过失败，请稍后重试') }
    finally { setReviewSubmitting(false); setApproveDialogOpen(false); setReviewTarget(null); setReviewComment('') }
  }, [reviewTarget, reviewComment, fetchReviewCases, fetchCases])

  const handleReject = useCallback(async () => {
    if (!reviewTarget) return
    setReviewSubmitting(true)
    try {
      await api.post('/case/review', { case_id: reviewTarget.case_id, status: 'rejected', review_comment: reviewComment })
      fetchReviewCases(); fetchCases()
    } catch { setErrorMsg('审核拒绝失败，请稍后重试') }
    finally { setReviewSubmitting(false); setRejectDialogOpen(false); setReviewTarget(null); setReviewComment('') }
  }, [reviewTarget, reviewComment, fetchReviewCases, fetchCases])

  return (
    <div className={`space-y-6 transition-all duration-700 ${mounted ? 'opacity-100' : 'opacity-0'}`}>
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ 
            background: isLight 
              ? `linear-gradient(135deg, ${colors.CYBER_BLUE} 0%, ${colors.CYBER_GREEN} 100%)` 
              : `linear-gradient(135deg, ${colors.CYBER_GREEN} 0%, ${colors.CYBER_CYAN} 100%)`, 
            boxShadow: `0 10px 40px ${isLight ? colors.CYBER_BLUE : colors.CYBER_GREEN}40` 
          }}>
          <Wrench size={28} style={{ color: '#ffffff' }} />
        </div>
        <div>
          <GradientText as="h1" className="text-2xl font-bold" style={{ 
            background: isLight 
              ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_BLUE} 100%)` 
              : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_GREEN} 100%)`, 
            WebkitBackgroundClip: 'text', 
            WebkitTextFillColor: 'transparent' 
          }}>检修案例管理</GradientText>
          <p className="text-sm" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>Equipment Maintenance Case Management</p>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: '总案例数', value: pagination.total, color: colors.CYBER_PURPLE, icon: FileText },
          { label: '待审核', value: reviewCases.length, color: colors.CYBER_YELLOW, icon: Clock },
          { label: '已通过', value: cases.filter(c => c.status === 'approved').length, color: colors.CYBER_GREEN, icon: CheckCircle2 },
        ].map((stat) => (
          <div key={stat.label} className="p-4 rounded-xl transition-all hover:scale-[1.02]" style={{ background: `linear-gradient(135deg, ${stat.color}15 0%, ${stat.color}05 100%)`, border: `1px solid ${stat.color}30`, boxShadow: `0 4px 20px ${stat.color}10` }}>
            <div className="flex items-center justify-between">
              <stat.icon size={20} style={{ color: stat.color }} />
              <span className="text-2xl font-bold" style={{ color: stat.color }}>{stat.value}</span>
            </div>
            <p className="text-xs mt-2" style={{ color: 'rgba(148,163,184,0.7)' }}>{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Main Tabs */}
      <div className="rounded-xl" style={{ 
            background: isLight ? '#ffffff' : 'rgba(15,15,30,0.95)', 
            border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_GREEN + '20'}`,
            boxShadow: isLight ? '0 4px 20px rgba(0, 0, 0, 0.06)' : undefined
          }}>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <div className="px-6 py-4 flex items-center gap-1" style={{ borderBottom: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_GREEN + '15'}` }}>
            <TabsTrigger value="list" className="data-[state=active]:!bg-transparent data-[state=active]:!text-blue-600 data-[state=active]:!border-b-2 data-[state=active]:!border-blue-600 px-4 py-2 rounded-t-lg transition-all duration-200">
              <FileText size={16} className="mr-2" /> 案例列表
            </TabsTrigger>
            <TabsTrigger value="create" className="data-[state=active]:!bg-transparent data-[state=active]:!text-blue-600 data-[state=active]:!border-b-2 data-[state=active]:!border-blue-600 px-4 py-2 rounded-t-lg transition-all duration-200">
              <Plus size={16} className="mr-2" /> 创建案例
            </TabsTrigger>
            {isAdmin && (
              <TabsTrigger value="review" className="data-[state=active]:!bg-transparent data-[state=active]:!text-blue-600 data-[state=active]:!border-b-2 data-[state=active]:!border-blue-600 px-4 py-2 rounded-t-lg transition-all duration-200">
                <Check size={16} className="mr-2" /> 案例审核
                {reviewCases.length > 0 && <Badge className="ml-2 h-5 min-w-[20px] px-1.5 text-xs" style={{ background: `${colors.CYBER_YELLOW}30`, color: colors.CYBER_YELLOW }}>{reviewCases.length}</Badge>}
              </TabsTrigger>
            )}
          </div>

          <div className="p-6">
            <TabsContent value="list">
              <div className="space-y-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3 flex-1">
                    <div className="w-40">
                      <Select value={statusFilter} onValueChange={setStatusFilter}>
                        <SelectTrigger className="h-10 rounded-lg" style={{ 
                          background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                          border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                          color: isLight ? '#1e293b' : '#f1f5f9' 
                        }}>
                          <SelectValue placeholder="状态筛选" />
                        </SelectTrigger>
                        <SelectContent style={{ 
                          background: isLight ? '#ffffff' : 'rgba(20,20,40,0.98)', 
                          border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}` 
                        }}>
                          <SelectItem value="all">全部</SelectItem>
                          <SelectItem value="pending_review">待审核</SelectItem>
                          <SelectItem value="approved">已通过</SelectItem>
                          <SelectItem value="rejected">已拒绝</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex-1 relative">
                      <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 transition-colors" style={{ color: isLight ? '#94a3b8' : '#505080' }} />
                      <Input value={searchKeyword} onChange={(e) => setSearchKeyword(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSearch()} placeholder="搜索案例标题..." className="pl-12 pr-4 py-2 rounded-lg text-sm" style={{ 
                        background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                        border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                        color: isLight ? '#1e293b' : '#f1f5f9' 
                      }} />
                    </div>
                    <Button onClick={handleSearch} disabled={loading} size="sm" className="h-10 rounded-lg font-medium" style={{ background: `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)`, color: '#000' }}>
                      <Search className="mr-2 h-4 w-4" /> 搜索
                    </Button>
                  </div>
                </div>

                {loading ? (
                  <div className="space-y-3">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <div key={i} className="h-12 animate-pulse rounded-lg" style={{ background: isLight ? '#f1f5f9' : 'rgba(30,30,50,0.5)' }} />
                    ))}
                  </div>
                ) : cases.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <FileText className="h-16 w-16 mb-4" style={{ color: isLight ? '#cbd5e1' : '#505080' }} />
                    <p className="text-lg" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>暂无案例</p>
                    <p className="text-sm mt-2" style={{ color: isLight ? '#94a3b8' : 'rgba(148,163,184,0.5)' }}>请尝试更换筛选条件或关键词</p>
                  </div>
                ) : (
                  <>
                    <div className="rounded-xl overflow-hidden" style={{ 
                      background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                      border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}` 
                    }}>
                      <Table>
                        <TableHeader>
                          <TableRow style={{ background: `${isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN}10` }}>
                            <TableHead style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }}>标题</TableHead>
                            <TableHead style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }}>设备型号</TableHead>
                            <TableHead style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }}>状态</TableHead>
                            <TableHead style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }}>创建时间</TableHead>
                            <TableHead style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }} className="text-right">操作</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {cases.map((c) => {
                            const status = STATUS_MAP[c.status]
                            const StatusIcon = status.icon
                            return (
                              <TableRow className="hover:bg-[rgba(0,240,255,0.05)] transition-colors">
                                <TableCell>
                                  <button className="text-left font-medium flex items-center gap-2 transition-colors" style={{ color: isLight ? '#1e293b' : '#f0f0f0' }} onClick={() => openDetail(c.case_id)}>
                                    <Wrench size={16} style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }} /> {c.title}
                                  </button>
                                </TableCell>
                                <TableCell style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>{c.device_model || '-'}</TableCell>
                                <TableCell>
                                  <Badge variant="outline" className="px-2 py-0.5" style={{ background: `${status.color}20`, color: status.color, borderColor: `${status.color}40` }}>
                                    <StatusIcon size={12} className="mr-1" /> {status.label}
                                  </Badge>
                                </TableCell>
                                <TableCell style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)', fontSize: '0.875rem' }}>{new Date(c.created_at).toLocaleString('zh-CN')}</TableCell>
                                <TableCell className="text-right">
                                  <div className="flex items-center justify-end gap-1">
                                    <Button size="sm" variant="ghost" onClick={() => openDetail(c.case_id)} className="hover:bg-[rgba(0,240,255,0.1)]">
                                      <Eye size={16} style={{ color: colors.CYBER_PURPLE }} />
                                    </Button>
                                    {isAdmin && (
                                      <Button size="sm" variant="ghost" onClick={() => { setDeleteTarget(c.case_id); setDeleteDialogOpen(true) }} className="hover:bg-[rgba(239,68,68,0.1)]">
                                        <Trash2 size={16} style={{ color: colors.CYBER_RED }} />
                                      </Button>
                                    )}
                                  </div>
                                </TableCell>
                              </TableRow>
                            )
                          })}
                        </TableBody>
                      </Table>
                    </div>
                    {pagination.total_pages > 1 && (
                      <div className="flex items-center justify-between px-2">
                        <p className="text-sm" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>共 {pagination.total} 条，第 {pagination.page}/{pagination.total_pages} 页</p>
                        <div className="flex items-center gap-2">
                          <Button size="sm" variant="outline" disabled={pagination.page <= 1} onClick={() => setPagination(p => ({ ...p, page: p.page - 1 }))} className="rounded-lg" style={{ borderColor: isLight ? '#e2e8f0' : `${colors.CYBER_CYAN}40` }}>
                            <ChevronLeft size={16} />
                          </Button>
                          <Button size="sm" variant="outline" disabled={pagination.page >= pagination.total_pages} onClick={() => setPagination(p => ({ ...p, page: p.page + 1 }))} className="rounded-lg" style={{ borderColor: isLight ? '#e2e8f0' : `${colors.CYBER_CYAN}40` }}>
                            <ChevronRight size={16} />
                          </Button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </TabsContent>

            <TabsContent value="create">
              <Card className="rounded-xl" style={{ 
                  background: isLight ? '#ffffff' : 'rgba(15,15,30,0.8)', 
                  border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_GREEN + '30'}`,
                  boxShadow: isLight ? '0 4px 20px rgba(0, 0, 0, 0.06)' : undefined
                }}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Sparkles size={18} style={{ color: colors.CYBER_GREEN }} /> 创建检修案例
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label style={{ color: isLight ? '#475569' : '#c0c0d0' }}>标题 *</Label>
                      <Input value={form.title} onChange={(e) => setForm(f => ({ ...f, title: e.target.value }))} placeholder="请输入案例标题" style={{ 
                        background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                        border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                        color: isLight ? '#1e293b' : '#f1f5f9' 
                      }} />
                    </div>
                    <div className="space-y-2">
                      <Label style={{ color: isLight ? '#475569' : '#c0c0d0' }}>设备类型 *</Label>
                      <Input value={form.equipment_type} onChange={(e) => setForm(f => ({ ...f, equipment_type: e.target.value }))} placeholder="如：变压器、开关柜" style={{ 
                        background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                        border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                        color: isLight ? '#1e293b' : '#f1f5f9' 
                      }} />
                    </div>
                    <div className="space-y-2">
                      <Label style={{ color: isLight ? '#475569' : '#c0c0d0' }}>设备型号</Label>
                      <Input value={form.equipment_model} onChange={(e) => setForm(f => ({ ...f, equipment_model: e.target.value }))} placeholder="请输入设备型号" style={{ 
                        background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                        border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                        color: isLight ? '#1e293b' : '#f1f5f9' 
                      }} />
                    </div>
                    <div className="space-y-2">
                      <Label style={{ color: isLight ? '#475569' : '#c0c0d0' }}>标签（逗号分隔）</Label>
                      <Input value={form.tags} onChange={(e) => setForm(f => ({ ...f, tags: e.target.value }))} placeholder="如：紧急,短路,过载" style={{ 
                        background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                        border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                        color: isLight ? '#1e293b' : '#f1f5f9' 
                      }} />
                    </div>
                    <div className="space-y-2 sm:col-span-2">
                      <Label style={{ color: isLight ? '#475569' : '#c0c0d0' }}>故障描述 *</Label>
                      <Textarea value={form.fault_description} onChange={(e) => setForm(f => ({ ...f, fault_description: e.target.value }))} placeholder="请详细描述故障现象" rows={3} style={{ 
                        background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                        border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                        color: isLight ? '#1e293b' : '#f1f5f9' 
                      }} />
                    </div>
                    <div className="space-y-2 sm:col-span-2">
                      <Label style={{ color: isLight ? '#475569' : '#c0c0d0' }}>故障分析</Label>
                      <Textarea value={form.fault_analysis} onChange={(e) => setForm(f => ({ ...f, fault_analysis: e.target.value }))} placeholder="请描述故障原因分析" rows={3} style={{ 
                        background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                        border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                        color: isLight ? '#1e293b' : '#f1f5f9' 
                      }} />
                    </div>
                    <div className="space-y-2 sm:col-span-2">
                      <Label style={{ color: isLight ? '#475569' : '#c0c0d0' }}>检修过程</Label>
                      <Textarea value={form.repair_process} onChange={(e) => setForm(f => ({ ...f, repair_process: e.target.value }))} placeholder="请描述检修步骤和过程" rows={3} style={{ 
                        background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                        border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                        color: isLight ? '#1e293b' : '#f1f5f9' 
                      }} />
                    </div>
                    <div className="space-y-2 sm:col-span-2">
                      <Label style={{ color: isLight ? '#475569' : '#c0c0d0' }}>检修结果</Label>
                      <Textarea value={form.repair_result} onChange={(e) => setForm(f => ({ ...f, repair_result: e.target.value }))} placeholder="请描述检修结果" rows={2} style={{ 
                        background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                        border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                        color: isLight ? '#1e293b' : '#f1f5f9' 
                      }} />
                    </div>
                    <div className="space-y-2 sm:col-span-2">
                      <Label style={{ color: isLight ? '#475569' : '#c0c0d0' }}>经验教训</Label>
                      <Textarea value={form.lessons_learned} onChange={(e) => setForm(f => ({ ...f, lessons_learned: e.target.value }))} placeholder="请总结经验教训" rows={2} style={{ 
                        background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                        border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                        color: isLight ? '#1e293b' : '#f1f5f9' 
                      }} />
                    </div>
                  </div>
                  <div className="mt-6 flex justify-end">
                    <Button onClick={handleCreate} disabled={submitting || !form.title.trim() || !form.equipment_type.trim() || !form.fault_description.trim()} className="h-11 rounded-xl font-medium" style={{ background: `linear-gradient(135deg, ${colors.CYBER_GREEN} 0%, ${colors.CYBER_CYAN} 100%)`, color: '#000', boxShadow: `0 4px 20px ${colors.CYBER_GREEN}30` }}>
                      <Plus className="mr-2 h-4 w-4" /> 提交案例
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {isAdmin && (
              <TabsContent value="review">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                      <AlertTriangle size={18} style={{ color: colors.CYBER_YELLOW }} /> 待审核案例
                    </h3>
                    <Badge variant="outline" className="px-3 py-1.5 text-sm font-semibold" style={{ background: `${colors.CYBER_YELLOW}20`, color: colors.CYBER_YELLOW, borderColor: `${colors.CYBER_YELLOW}40` }}>
                      {reviewCases.length} 条待审核
                    </Badge>
                  </div>
                  {reviewLoading ? (
                    <div className="space-y-3">
                      {Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-16 animate-pulse rounded-xl" style={{ background: isLight ? '#f1f5f9' : 'rgba(30,30,50,0.5)' }} />)}
                    </div>
                  ) : reviewCases.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                      <CheckCircle2 className="h-16 w-16 mb-4" style={{ color: colors.CYBER_GREEN }} />
                      <p className="text-lg" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>暂无待审核案例</p>
                      <p className="text-sm mt-2" style={{ color: isLight ? '#94a3b8' : 'rgba(148,163,184,0.5)' }}>所有案例均已审核完成</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {reviewCases.map((c) => (
                        <div key={c.case_id} className="p-5 rounded-xl flex items-center justify-between transition-all" style={{ 
                          background: isLight ? '#f8fafc' : 'rgba(15,15,35,0.6)', 
                          border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}`,
                          boxShadow: isLight ? '0 2px 8px rgba(0, 0, 0, 0.04)' : undefined
                        }}>
                          <div className="min-w-0 flex-1">
                            <button className="truncate font-medium text-lg block w-full text-left transition-colors" style={{ color: isLight ? '#1e293b' : '#f0f0f0' }} onClick={() => openDetail(c.case_id)}>{c.title}</button>
                            <div className="mt-2 flex items-center gap-4 text-sm" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>
                              <span className="flex items-center gap-1"><Wrench size={14} /> {c.device_model || '-'}</span>
                              <span className="flex items-center gap-1"><Clock size={14} /> {new Date(c.created_at).toLocaleString('zh-CN')}</span>
                            </div>
                          </div>
                          <div className="flex items-center gap-2 ml-4">
                            <Button size="sm" onClick={() => { setReviewTarget(c); setApproveDialogOpen(true) }} className="h-9 rounded-lg font-medium" style={{ background: isLight ? colors.CYBER_GREEN : `linear-gradient(135deg, ${colors.CYBER_GREEN} 0%, ${colors.CYBER_CYAN} 100%)`, color: '#ffffff' }}>
                              <Check className="mr-1 h-4 w-4" /> 通过
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => { setReviewTarget(c); setRejectDialogOpen(true) }} className="h-9 rounded-lg" style={{ 
                              borderColor: isLight ? '#e2e8f0' : `${colors.CYBER_RED}50`, 
                              color: isLight ? colors.CYBER_RED : colors.CYBER_RED,
                              background: isLight ? '#ffffff' : 'transparent'
                            }}>
                              <X className="mr-1 h-4 w-4" /> 拒绝
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </TabsContent>
            )}
          </div>
        </Tabs>
      </div>

      {/* Case Detail Dialog */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto rounded-2xl" style={{ 
            background: isLight ? '#ffffff' : 'rgba(15,15,30,0.95)', 
            border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_GREEN + '30'}` 
          }}>
          <DialogHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ 
                background: isLight 
                  ? `linear-gradient(135deg, ${colors.CYBER_BLUE} 0%, ${colors.CYBER_CYAN} 100%)` 
                  : `linear-gradient(135deg, ${colors.CYBER_GREEN} 0%, ${colors.CYBER_CYAN} 100%)` 
              }}>
                <Wrench size={20} style={{ color: isLight ? '#ffffff' : '#000' }} />
              </div>
              <DialogTitle className="text-xl" style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}>案例详情</DialogTitle>
            </div>
            <DialogDescription style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>{detailData?.title}</DialogDescription>
          </DialogHeader>
          {detailLoading ? (
            <div className="space-y-3 py-4">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-6 animate-pulse rounded" style={{ background: isLight ? '#f1f5f9' : `${colors.CYBER_CYAN}20` }} />)}</div>
          ) : detailData ? (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                {(() => { const status = STATUS_MAP[detailData.status]; const StatusIcon = status.icon; return <Badge variant="outline" className="px-2 py-0.5" style={{ background: `${status.color}20`, color: status.color, borderColor: `${status.color}40` }}><StatusIcon size={12} className="mr-1" /> {status.label}</Badge> })()}
                <span className="text-sm" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>{new Date(detailData.created_at).toLocaleString('zh-CN')}</span>
              </div>
              {detailData.equipment_type && <div className="p-4 rounded-xl" style={{ background: `${colors.CYBER_GREEN}10`, border: `1px solid ${colors.CYBER_GREEN}20` }}><p className="text-sm font-medium mb-1" style={{ color: colors.CYBER_GREEN }}>设备类型</p><p className="text-sm" style={{ color: isLight ? '#475569' : 'rgba(148,163,184,0.7)' }}>{detailData.equipment_type}</p></div>}
              {detailData.equipment_model && <div className="p-4 rounded-xl" style={{ background: `${colors.CYBER_PURPLE}10`, border: `1px solid ${colors.CYBER_PURPLE}20` }}><p className="text-sm font-medium mb-1" style={{ color: colors.CYBER_PURPLE }}>设备型号</p><p className="text-sm" style={{ color: isLight ? '#475569' : 'rgba(148,163,184,0.7)' }}>{detailData.equipment_model}</p></div>}
              {detailData.fault_description && <div className="p-4 rounded-xl" style={{ background: `${colors.CYBER_RED}10`, border: `1px solid ${colors.CYBER_RED}20` }}><p className="text-sm font-medium mb-1" style={{ color: colors.CYBER_RED }}>故障描述</p><p className="text-sm whitespace-pre-wrap" style={{ color: isLight ? '#475569' : 'rgba(148,163,184,0.7)' }}>{detailData.fault_description}</p></div>}
              {detailData.fault_analysis && <div className="p-4 rounded-xl" style={{ background: `${colors.CYBER_YELLOW}10`, border: `1px solid ${colors.CYBER_YELLOW}20` }}><p className="text-sm font-medium mb-1" style={{ color: colors.CYBER_YELLOW }}>故障分析</p><p className="text-sm whitespace-pre-wrap" style={{ color: isLight ? '#475569' : 'rgba(148,163,184,0.7)' }}>{detailData.fault_analysis}</p></div>}
              {detailData.repair_process && <div className="p-4 rounded-xl" style={{ background: `${colors.CYBER_GREEN}10`, border: `1px solid ${colors.CYBER_GREEN}20` }}><p className="text-sm font-medium mb-1" style={{ color: colors.CYBER_GREEN }}>检修过程</p><p className="text-sm whitespace-pre-wrap" style={{ color: isLight ? '#475569' : 'rgba(148,163,184,0.7)' }}>{detailData.repair_process}</p></div>}
              {detailData.repair_result && <div className="p-4 rounded-xl" style={{ background: `${colors.CYBER_GREEN}10`, border: `1px solid ${colors.CYBER_GREEN}20` }}><p className="text-sm font-medium mb-1" style={{ color: colors.CYBER_GREEN }}>检修结果</p><p className="text-sm whitespace-pre-wrap" style={{ color: isLight ? '#475569' : 'rgba(148,163,184,0.7)' }}>{detailData.repair_result}</p></div>}
              {detailData.lessons_learned && <div className="p-4 rounded-xl" style={{ background: `${colors.CYBER_CYAN}10`, border: `1px solid ${colors.CYBER_CYAN}20` }}><p className="text-sm font-medium mb-1" style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }}>经验教训</p><p className="text-sm whitespace-pre-wrap" style={{ color: isLight ? '#475569' : 'rgba(148,163,184,0.7)' }}>{detailData.lessons_learned}</p></div>}
              {detailData.tags && detailData.tags.length > 0 && (
                <div><p className="text-sm font-medium mb-2" style={{ color: isLight ? '#475569' : '#c0c0d0' }}>标签</p><div className="flex flex-wrap gap-2">{detailData.tags.map(tag => <Badge key={tag} variant="secondary" style={{ background: `${colors.CYBER_PURPLE}20`, color: colors.CYBER_PURPLE }}>{tag}</Badge>)}</div></div>
              )}
            </div>
          ) : <p className="py-4 text-center" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>加载案例详情失败</p>}
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="rounded-2xl" style={{ 
            background: isLight ? '#ffffff' : 'rgba(15,15,30,0.95)', 
            border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_RED + '30'}` 
          }}>
          <DialogHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${colors.CYBER_RED}20` }}>
                <Trash2 size={20} style={{ color: colors.CYBER_RED }} />
              </div>
              <DialogTitle className="text-xl" style={{ color: colors.CYBER_RED }}>确认删除</DialogTitle>
            </div>
            <DialogDescription style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>确定要删除该案例吗？此操作不可撤销。</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)} className="rounded-xl" style={{ 
              borderColor: isLight ? '#e2e8f0' : `${colors.CYBER_PURPLE}50`, 
              color: isLight ? '#475569' : '#e8e8e8',
              background: isLight ? '#ffffff' : 'transparent'
            }}>取消</Button>
            <Button variant="destructive" onClick={handleDelete} className="rounded-xl" style={{ background: colors.CYBER_RED }}><Trash2 className="mr-1 h-4 w-4" /> 删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Approve Dialog */}
      <Dialog open={approveDialogOpen} onOpenChange={setApproveDialogOpen}>
        <DialogContent className="rounded-2xl" style={{ 
          background: isLight ? '#ffffff' : 'rgba(15,15,30,0.95)', 
          border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_GREEN + '30'}` 
        }}>
          <DialogHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${colors.CYBER_GREEN}20` }}>
                <CheckCircle2 size={20} style={{ color: colors.CYBER_GREEN }} />
              </div>
              <DialogTitle className="text-xl" style={{ color: colors.CYBER_GREEN }}>审核通过</DialogTitle>
            </div>
            <DialogDescription style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>确认通过案例「{reviewTarget?.title}」的审核？</DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <Label className="mb-1.5 block" style={{ color: isLight ? '#475569' : '#c0c0d0' }}>审核意见（可选）</Label>
            <Input placeholder="请输入审核意见" value={reviewComment} onChange={(e) => setReviewComment(e.target.value)} style={{ 
              background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
              border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
              color: isLight ? '#1e293b' : '#f1f5f9' 
            }} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setApproveDialogOpen(false)} className="rounded-xl" style={{ 
              borderColor: isLight ? '#e2e8f0' : `${colors.CYBER_PURPLE}50`, 
              color: isLight ? '#475569' : '#e8e8e8',
              background: isLight ? '#ffffff' : 'transparent'
            }}>取消</Button>
            <Button onClick={handleApprove} disabled={reviewSubmitting} className="rounded-xl" style={{ 
              background: isLight ? colors.CYBER_GREEN : `linear-gradient(135deg, ${colors.CYBER_GREEN} 0%, ${colors.CYBER_CYAN} 100%)`, 
              color: '#ffffff' 
            }}><Check className="mr-1 h-4 w-4" /> 确认通过</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <DialogContent className="rounded-2xl" style={{ 
          background: isLight ? '#ffffff' : 'rgba(15,15,30,0.95)', 
          border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_RED + '30'}` 
        }}>
          <DialogHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${colors.CYBER_RED}20` }}>
                <XCircle size={20} style={{ color: colors.CYBER_RED }} />
              </div>
              <DialogTitle className="text-xl" style={{ color: colors.CYBER_RED }}>拒绝审核</DialogTitle>
            </div>
            <DialogDescription style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>拒绝案例「{reviewTarget?.title}」的审核，请填写拒绝原因。</DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <Label className="mb-1.5 block" style={{ color: isLight ? '#475569' : '#c0c0d0' }}>拒绝原因</Label>
            <Input placeholder="请输入拒绝原因" value={reviewComment} onChange={(e) => setReviewComment(e.target.value)} style={{ 
              background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
              border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
              color: isLight ? '#1e293b' : '#f1f5f9' 
            }} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectDialogOpen(false)} className="rounded-xl" style={{ 
              borderColor: isLight ? '#e2e8f0' : `${colors.CYBER_PURPLE}50`, 
              color: isLight ? '#475569' : '#e8e8e8',
              background: isLight ? '#ffffff' : 'transparent'
            }}>取消</Button>
            <Button variant="destructive" onClick={handleReject} disabled={reviewSubmitting} className="rounded-xl" style={{ background: colors.CYBER_RED }}><X className="mr-1 h-4 w-4" /> 确认拒绝</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}