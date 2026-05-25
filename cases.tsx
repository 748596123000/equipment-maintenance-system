import { useState, useEffect, useCallback } from 'react'
import { useAuthStore } from '@/stores/auth-store'
import { api } from '@/lib/api'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
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
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Search,
  Plus,
  Check,
  X,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Eye,
} from 'lucide-react'

interface CaseItem {
  case_id: string
  title: string
  description: string
  device_model: string
  status: 'pending_review' | 'approved' | 'rejected'
  created_at: string
}

interface CaseDetail extends CaseItem {
  fault_analysis: string
  repair_process: string
  lessons_learned: string
  tags: string[]
  author_id: string
  equipment_type: string
  equipment_model: string
  fault_description: string
  repair_result: string
}

interface Pagination {
  page: number
  page_size: number
  total: number
  total_pages: number
}

const STATUS_MAP: Record<string, { label: string; className: string }> = {
  pending_review: {
    label: '待审核',
    className: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  },
  approved: {
    label: '已通过',
    className: 'bg-green-100 text-green-800 border-green-200',
  },
  rejected: {
    label: '已拒绝',
    className: 'bg-red-100 text-red-800 border-red-200',
  },
}

export default function CasesPage() {
  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.role === 'admin'

  const [activeTab, setActiveTab] = useState('list')
  const [cases, setCases] = useState<CaseItem[]>([])
  const [pagination, setPagination] = useState<Pagination>({
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 0,
  })
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [loading, setLoading] = useState(false)

  const [detailOpen, setDetailOpen] = useState(false)
  const [detailData, setDetailData] = useState<CaseDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)

  const [form, setForm] = useState({
    title: '',
    equipment_type: '',
    equipment_model: '',
    fault_description: '',
    fault_analysis: '',
    repair_process: '',
    repair_result: '',
    lessons_learned: '',
    tags: '',
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

  const fetchCases = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = {
        page: pagination.page,
        page_size: pagination.page_size,
      }
      if (statusFilter !== 'all') params.status = statusFilter
      const res = await api.get<{
        cases: CaseItem[]
        pagination: Pagination
      }>('/case/list', { params })
      setCases(res.data.cases || [])
      setPagination(res.data.pagination || pagination)
    } catch {
      setCases([])
    } finally {
      setLoading(false)
    }
  }, [pagination.page, pagination.page_size, statusFilter])

  const fetchReviewCases = useCallback(async () => {
    if (!isAdmin) return
    setReviewLoading(true)
    try {
      const res = await api.get<{
        cases: CaseItem[]
        pagination: Pagination
      }>('/case/list', { params: { page: 1, page_size: 100, status: 'pending_review' } })
      setReviewCases(res.data.cases || [])
    } catch {
      setReviewCases([])
    } finally {
      setReviewLoading(false)
    }
  }, [isAdmin])

  useEffect(() => {
    fetchCases()
  }, [fetchCases])

  useEffect(() => {
    if (activeTab === 'review' && isAdmin) {
      fetchReviewCases()
    }
  }, [activeTab, isAdmin, fetchReviewCases])

  const handleSearch = useCallback(async () => {
    if (!searchKeyword.trim()) {
      fetchCases()
      return
    }
    setLoading(true)
    try {
      const res = await api.post<{
        cases: CaseItem[]
        pagination: Pagination
      }>('/case/search', {
        query: searchKeyword.trim(),
        page: 1,
        page_size: pagination.page_size,
      })
      setCases(res.data.cases || [])
      setPagination(res.data.pagination || pagination)
    } catch {
      setCases([])
    } finally {
      setLoading(false)
    }
  }, [searchKeyword, pagination.page_size, fetchCases])

  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSearch()
  }

  const openDetail = useCallback(async (caseId: string) => {
    setDetailLoading(true)
    setDetailOpen(true)
    try {
      const res = await api.get<CaseDetail>(`/case/${caseId}`)
      setDetailData(res.data)
    } catch {
      setDetailData(null)
    } finally {
      setDetailLoading(false)
    }
  }, [])

  const openDeleteDialog = useCallback((caseId: string) => {
    setDeleteTarget(caseId)
    setDeleteDialogOpen(true)
  }, [])

  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return
    try {
      await api.delete(`/case/${deleteTarget}`)
      fetchCases()
      if (isAdmin) fetchReviewCases()
    } catch {
      setErrorMsg('删除案例失败，请稍后重试')
    } finally {
      setDeleteDialogOpen(false)
      setDeleteTarget(null)
    }
  }, [deleteTarget, fetchCases, isAdmin, fetchReviewCases])

  const handleCreate = useCallback(async () => {
    if (!form.title.trim() || !form.equipment_type.trim() || !form.fault_description.trim()) return
    setSubmitting(true)
    try {
      const tags = form.tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean)
      await api.post('/case/create', {
        title: form.title.trim(),
        equipment_type: form.equipment_type.trim(),
        equipment_model: form.equipment_model.trim(),
        fault_description: form.fault_description.trim(),
        fault_analysis: form.fault_analysis.trim(),
        repair_process: form.repair_process.trim(),
        repair_result: form.repair_result.trim(),
        lessons_learned: form.lessons_learned.trim(),
        tags,
      })
      setForm({
        title: '',
        equipment_type: '',
        equipment_model: '',
        fault_description: '',
        fault_analysis: '',
        repair_process: '',
        repair_result: '',
        lessons_learned: '',
        tags: '',
      })
      setActiveTab('list')
      fetchCases()
    } catch {
      setErrorMsg('创建案例失败，请检查填写内容')
    } finally {
      setSubmitting(false)
    }
  }, [form, fetchCases])

  const openApproveDialog = useCallback((c: CaseItem) => {
    setReviewTarget(c)
    setReviewComment('')
    setApproveDialogOpen(true)
  }, [])

  const openRejectDialog = useCallback((c: CaseItem) => {
    setReviewTarget(c)
    setReviewComment('')
    setRejectDialogOpen(true)
  }, [])

  const handleApprove = useCallback(async () => {
    if (!reviewTarget) return
    setReviewSubmitting(true)
    try {
      await api.post('/case/review', {
        case_id: reviewTarget.case_id,
        status: 'approved',
        review_comment: reviewComment,
      })
      fetchReviewCases()
      fetchCases()
    } catch {
      setErrorMsg('审核通过失败，请稍后重试')
    } finally {
      setReviewSubmitting(false)
      setApproveDialogOpen(false)
      setReviewTarget(null)
      setReviewComment('')
    }
  }, [reviewTarget, reviewComment, fetchReviewCases, fetchCases])

  const handleReject = useCallback(async () => {
    if (!reviewTarget) return
    setReviewSubmitting(true)
    try {
      await api.post('/case/review', {
        case_id: reviewTarget.case_id,
        status: 'rejected',
        review_comment: reviewComment,
      })
      fetchReviewCases()
      fetchCases()
    } catch {
      setErrorMsg('审核拒绝失败，请稍后重试')
    } finally {
      setReviewSubmitting(false)
      setRejectDialogOpen(false)
      setReviewTarget(null)
      setReviewComment('')
    }
  }, [reviewTarget, reviewComment, fetchReviewCases, fetchCases])

  const setPage = (page: number) => {
    setPagination((prev) => ({ ...prev, page }))
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">🔧 检修案例管理</h1>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList>
          <TabsTrigger value="list">案例列表</TabsTrigger>
          <TabsTrigger value="create">创建案例</TabsTrigger>
          {isAdmin && <TabsTrigger value="review">案例审核</TabsTrigger>}
        </TabsList>

        <TabsContent value="list">
          <Card>
            <CardHeader>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <CardTitle>案例列表</CardTitle>
                <div className="flex items-center gap-2">
                  <div className="w-36">
                    <Select value={statusFilter} onValueChange={setStatusFilter}>
                      <SelectTrigger>
                        <SelectValue placeholder="状态筛选" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">全部</SelectItem>
                        <SelectItem value="pending_review">待审核</SelectItem>
                        <SelectItem value="approved">已通过</SelectItem>
                        <SelectItem value="rejected">已拒绝</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex-1">
                    <Input
                      value={searchKeyword}
                      onChange={(e) => setSearchKeyword(e.target.value)}
                      onKeyDown={handleSearchKeyDown}
                      placeholder="搜索案例..."
                    />
                  </div>
                  <Button onClick={handleSearch} disabled={loading} size="sm">
                    <Search className="mr-1 h-4 w-4" />
                    搜索
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="h-10 animate-pulse rounded bg-muted" />
                  ))}
                </div>
              ) : cases.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <p className="text-lg">暂无案例</p>
                  <p className="mt-1 text-sm">请尝试更换筛选条件或关键词</p>
                </div>
              ) : (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>标题</TableHead>
                        <TableHead>设备型号</TableHead>
                        <TableHead>状态</TableHead>
                        <TableHead>创建时间</TableHead>
                        <TableHead className="text-right">操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {cases.map((c) => (
                        <TableRow key={c.case_id}>
                          <TableCell>
                            <button
                              className="text-left font-medium hover:underline"
                              onClick={() => openDetail(c.case_id)}
                            >
                              {c.title}
                            </button>
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {c.device_model || '-'}
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant="outline"
                              className={STATUS_MAP[c.status]?.className}
                            >
                              {STATUS_MAP[c.status]?.label || c.status}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {new Date(c.created_at).toLocaleString('zh-CN')}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => openDetail(c.case_id)}
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                              {isAdmin && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => openDeleteDialog(c.case_id)}
                                >
                                  <Trash2 className="h-4 w-4 text-destructive" />
                                </Button>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  {pagination.total_pages > 1 && (
                    <div className="mt-4 flex items-center justify-between">
                      <p className="text-sm text-muted-foreground">
                        共 {pagination.total} 条，第 {pagination.page}/{pagination.total_pages} 页
                      </p>
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={pagination.page <= 1}
                          onClick={() => setPage(pagination.page - 1)}
                        >
                          <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={pagination.page >= pagination.total_pages}
                          onClick={() => setPage(pagination.page + 1)}
                        >
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="create">
          <Card>
            <CardHeader>
              <CardTitle>创建检修案例</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>标题 *</Label>
                  <Input
                    value={form.title}
                    onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                    placeholder="请输入案例标题"
                  />
                </div>
                <div className="space-y-2">
                  <Label>设备类型 *</Label>
                  <Input
                    value={form.equipment_type}
                    onChange={(e) => setForm((f) => ({ ...f, equipment_type: e.target.value }))}
                    placeholder="如：变压器、开关柜"
                  />
                </div>
                <div className="space-y-2">
                  <Label>设备型号</Label>
                  <Input
                    value={form.equipment_model}
                    onChange={(e) => setForm((f) => ({ ...f, equipment_model: e.target.value }))}
                    placeholder="请输入设备型号"
                  />
                </div>
                <div className="space-y-2">
                  <Label>标签（逗号分隔）</Label>
                  <Input
                    value={form.tags}
                    onChange={(e) => setForm((f) => ({ ...f, tags: e.target.value }))}
                    placeholder="如：紧急,短路,过载"
                  />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label>故障描述 *</Label>
                  <Textarea
                    value={form.fault_description}
                    onChange={(e) => setForm((f) => ({ ...f, fault_description: e.target.value }))}
                    placeholder="请详细描述故障现象"
                    rows={3}
                  />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label>故障分析</Label>
                  <Textarea
                    value={form.fault_analysis}
                    onChange={(e) => setForm((f) => ({ ...f, fault_analysis: e.target.value }))}
                    placeholder="请描述故障原因分析"
                    rows={3}
                  />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label>检修过程</Label>
                  <Textarea
                    value={form.repair_process}
                    onChange={(e) => setForm((f) => ({ ...f, repair_process: e.target.value }))}
                    placeholder="请描述检修步骤和过程"
                    rows={3}
                  />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label>检修结果</Label>
                  <Textarea
                    value={form.repair_result}
                    onChange={(e) => setForm((f) => ({ ...f, repair_result: e.target.value }))}
                    placeholder="请描述检修结果"
                    rows={2}
                  />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label>经验教训</Label>
                  <Textarea
                    value={form.lessons_learned}
                    onChange={(e) => setForm((f) => ({ ...f, lessons_learned: e.target.value }))}
                    placeholder="请总结经验教训"
                    rows={2}
                  />
                </div>
              </div>
              <div className="mt-6 flex justify-end">
                <Button
                  onClick={handleCreate}
                  disabled={
                    submitting ||
                    !form.title.trim() ||
                    !form.equipment_type.trim() ||
                    !form.fault_description.trim()
                  }
                >
                  <Plus className="mr-1 h-4 w-4" />
                  提交案例
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {isAdmin && (
          <TabsContent value="review">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>待审核案例</CardTitle>
                <Badge
                  variant="outline"
                  className="bg-yellow-100 text-yellow-800 border-yellow-200"
                >
                  {reviewCases.length} 条待审核
                </Badge>
              </CardHeader>
              <CardContent>
                {reviewLoading ? (
                  <div className="space-y-3">
                    {Array.from({ length: 3 }).map((_, i) => (
                      <div key={i} className="h-16 animate-pulse rounded bg-muted" />
                    ))}
                  </div>
                ) : reviewCases.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <p className="text-lg">暂无待审核案例</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {reviewCases.map((c) => (
                      <div
                        key={c.case_id}
                        className="flex items-center justify-between rounded-lg border p-4"
                      >
                        <div className="min-w-0 flex-1">
                          <button
                            className="truncate font-medium hover:underline"
                            onClick={() => openDetail(c.case_id)}
                          >
                            {c.title}
                          </button>
                          <div className="mt-1 flex items-center gap-3 text-sm text-muted-foreground">
                            <span>{c.device_model || '-'}</span>
                            <span>{new Date(c.created_at).toLocaleString('zh-CN')}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button size="sm" onClick={() => openApproveDialog(c)}>
                            <Check className="mr-1 h-4 w-4" />
                            通过
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => openRejectDialog(c)}
                          >
                            <X className="mr-1 h-4 w-4" />
                            拒绝
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        )}
      </Tabs>

      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>案例详情</DialogTitle>
            <DialogDescription>{detailData?.title}</DialogDescription>
          </DialogHeader>
          {detailLoading ? (
            <div className="space-y-3 py-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-6 animate-pulse rounded bg-muted" />
              ))}
            </div>
          ) : detailData ? (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Badge
                  variant="outline"
                  className={STATUS_MAP[detailData.status]?.className}
                >
                  {STATUS_MAP[detailData.status]?.label || detailData.status}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  {new Date(detailData.created_at).toLocaleString('zh-CN')}
                </span>
              </div>
              {detailData.equipment_type && (
                <div>
                  <p className="text-sm font-medium">设备类型</p>
                  <p className="mt-0.5 text-sm text-muted-foreground">{detailData.equipment_type}</p>
                </div>
              )}
              {detailData.equipment_model && (
                <div>
                  <p className="text-sm font-medium">设备型号</p>
                  <p className="mt-0.5 text-sm text-muted-foreground">{detailData.equipment_model}</p>
                </div>
              )}
              {detailData.fault_description && (
                <div>
                  <p className="text-sm font-medium">故障描述</p>
                  <p className="mt-0.5 text-sm text-muted-foreground whitespace-pre-wrap">{detailData.fault_description}</p>
                </div>
              )}
              {detailData.fault_analysis && (
                <div>
                  <p className="text-sm font-medium">故障分析</p>
                  <p className="mt-0.5 text-sm text-muted-foreground whitespace-pre-wrap">{detailData.fault_analysis}</p>
                </div>
              )}
              {detailData.repair_process && (
                <div>
                  <p className="text-sm font-medium">检修过程</p>
                  <p className="mt-0.5 text-sm text-muted-foreground whitespace-pre-wrap">{detailData.repair_process}</p>
                </div>
              )}
              {detailData.repair_result && (
                <div>
                  <p className="text-sm font-medium">检修结果</p>
                  <p className="mt-0.5 text-sm text-muted-foreground whitespace-pre-wrap">{detailData.repair_result}</p>
                </div>
              )}
              {detailData.lessons_learned && (
                <div>
                  <p className="text-sm font-medium">经验教训</p>
                  <p className="mt-0.5 text-sm text-muted-foreground whitespace-pre-wrap">{detailData.lessons_learned}</p>
                </div>
              )}
              {detailData.tags && detailData.tags.length > 0 && (
                <div>
                  <p className="text-sm font-medium">标签</p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {detailData.tags.map((tag) => (
                      <Badge key={tag} variant="secondary">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="py-4 text-center text-muted-foreground">加载案例详情失败</p>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>确定要删除该案例吗？此操作不可撤销。</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              <Trash2 className="mr-1 h-4 w-4" />
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={approveDialogOpen} onOpenChange={setApproveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>审核通过</DialogTitle>
            <DialogDescription>
              确认通过案例「{reviewTarget?.title}」的审核？
            </DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <Label className="mb-1.5 block">审核意见（可选）</Label>
            <Input
              placeholder="请输入审核意见"
              value={reviewComment}
              onChange={(e) => setReviewComment(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setApproveDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleApprove} disabled={reviewSubmitting}>
              <Check className="mr-1 h-4 w-4" />
              确认通过
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>拒绝审核</DialogTitle>
            <DialogDescription>
              拒绝案例「{reviewTarget?.title}」的审核，请填写拒绝原因。
            </DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <Label className="mb-1.5 block">拒绝原因</Label>
            <Input
              placeholder="请输入拒绝原因"
              value={reviewComment}
              onChange={(e) => setReviewComment(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectDialogOpen(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleReject} disabled={reviewSubmitting}>
              <X className="mr-1 h-4 w-4" />
              确认拒绝
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
