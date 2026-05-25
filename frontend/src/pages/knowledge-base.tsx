import { useEffect, useState, useCallback, useMemo } from "react"
import { useAuthStore } from "@/stores/auth-store"
import { useTheme, COLORS } from "@/hooks/useTheme"
import { sanitizeText } from "@/lib/sanitize"
import { api, downloadFile } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import {
  Database,
  Search,
  ChevronDown,
  ChevronRight,
  FileText,
  Layers,
  HardDrive,
  FileSpreadsheet,
  Presentation,
  Image,
  FileType,
  Zap,
  Loader2,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  XCircle,
  Eye,
  Sparkles,
  Download,
} from "lucide-react"

interface KnowledgeDocument {
  document_id: string
  filename: string
  file_type: string
  file_size: number
  file_size_display: string
  category: string
  chunk_count: number
  page_count: number
  status: string
  uploader_name: string
  created_at: string
}

interface KnowledgeStats {
  document_count: number
  total_chunks: number
  chroma_status: string
  db_size_mb: number
}

interface PreviewData {
  filename: string
  page_count: number
  uploader_name: string
  content: string
}

interface DocumentImage {
  id: string
  page_number: number
  image_index: number
  image_url: string
  width: number
  height: number
  image_format: string
  ai_description: string
  ai_analyzed: boolean
}

interface CategoryGroup {
  category: string
  documents: KnowledgeDocument[]
}

function getFileIcon(fileType: string) {
  const ext = fileType.toLowerCase().replace(".", "")
  if (ext === "pdf") return <FileText className="h-4 w-4 text-red-500 shrink-0" />
  if (["docx", "doc", "txt", "md", "log"].includes(ext)) return <FileText className="h-4 w-4 text-blue-500 shrink-0" />
  if (["xlsx", "xls", "csv"].includes(ext)) return <FileSpreadsheet className="h-4 w-4 text-green-500 shrink-0" />
  if (["pptx", "ppt"].includes(ext)) return <Presentation className="h-4 w-4 text-orange-500 shrink-0" />
  if (["jpg", "jpeg", "png", "bmp", "gif", "tiff", "webp"].includes(ext)) return <Image className="h-4 w-4 text-purple-500 shrink-0" />
  if (["json", "xml"].includes(ext)) return <FileType className="h-4 w-4 text-gray-500 shrink-0" />
  return <FileText className="h-4 w-4 text-gray-400 shrink-0" />
}

const STATUS_CONFIG: Record<string, { label: string; className: string; icon?: React.ReactNode }> = {
  pending: { label: "待审核", className: "bg-yellow-100 text-yellow-800 border-yellow-200" },
  approved: { label: "已审核", className: "bg-blue-100 text-blue-800 border-blue-200", icon: <AlertCircle className="h-3 w-3" /> },
  completed: { label: "已完成", className: "bg-green-100 text-green-800 border-green-200", icon: <CheckCircle2 className="h-3 w-3" /> },
  rejected: { label: "已拒绝", className: "bg-red-100 text-red-800 border-red-200", icon: <XCircle className="h-3 w-3" /> },
  processing: { label: "处理中", className: "bg-orange-100 text-orange-800 border-orange-200", icon: <Loader2 className="h-3 w-3 animate-spin" /> },
  parsed: { label: "已解析", className: "bg-purple-100 text-purple-800 border-purple-200" },
  failed: { label: "处理失败", className: "bg-red-100 text-red-800 border-red-200", icon: <XCircle className="h-3 w-3" /> },
}

function canProcessToKnowledge(status: string): boolean {
  return ["approved", "completed", "parsed", "failed"].includes(status)
}

function getProcessButtonLabel(status: string): string {
  if (status === "approved") return "处理为知识"
  if (status === "failed") return "重新处理"
  if (status === "parsed") return "重新向量化"
  if (status === "completed") return "重新处理"
  return "处理为知识"
}

export default function KnowledgeBasePage() {
  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.role === "admin"
  const { theme } = useTheme()
  const isLight = theme === 'light'
  const colors = isLight ? COLORS.light : COLORS.dark

  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [stats, setStats] = useState<KnowledgeStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchKeyword, setSearchKeyword] = useState("")
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())
  const [selectedDoc, setSelectedDoc] = useState<KnowledgeDocument | null>(null)
  const [previewData, setPreviewData] = useState<PreviewData | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [processingIds, setProcessingIds] = useState<Set<string>>(new Set())
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)
  const [docImages, setDocImages] = useState<DocumentImage[]>([])
  const [imagesLoading, setImagesLoading] = useState(false)
  const [analyzingId, setAnalyzingId] = useState<string | null>(null)
  const [previewTab, setPreviewTab] = useState<"text" | "images">("text")
  const [downloadingIds, setDownloadingIds] = useState<Set<string>>(new Set())
  const [completingIds, setCompletingIds] = useState<Set<string>>(new Set())

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const docsRes = await api.get<{ documents: KnowledgeDocument[] }>("/upload/list", {
        params: { page_size: 100 },
      })
      setDocuments(docsRes.data.documents || [])

      if (isAdmin) {
        try {
          const statsRes = await api.get<KnowledgeStats>("/admin/stats")
          setStats(statsRes.data)
        } catch {
          setStats(null)
        }
      } else {
        try {
          const myStatsRes = await api.get<{ total: number; pending: number; approved: number; completed: number }>("/upload/my/stats")
          setStats({
            document_count: myStatsRes.data.total,
            total_chunks: 0,
            chroma_status: "",
            db_size_mb: 0,
          })
        } catch {
          setStats(null)
        }
      }
    } catch {
      setDocuments([])
      setStats(null)
    } finally {
      setLoading(false)
    }
  }, [isAdmin])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleSearch = useCallback(async () => {
    if (!searchKeyword.trim()) {
      fetchData()
      return
    }
    try {
      setLoading(true)
      const res = await api.get<{ documents: KnowledgeDocument[] }>("/upload/list", {
        params: { keyword: searchKeyword, page_size: 100 },
      })
      setDocuments(res.data.documents || [])
    } catch {
      setDocuments([])
    } finally {
      setLoading(false)
    }
  }, [searchKeyword, fetchData])

  const handleProcessToKnowledge = useCallback(async (doc: KnowledgeDocument, e: React.MouseEvent) => {
    e.stopPropagation()
    if (processingIds.has(doc.document_id)) return

    setProcessingIds((prev) => new Set(prev).add(doc.document_id))
    setMessage(null)
    try {
      await api.post(`/upload/${doc.document_id}/process`)
      setMessage({ type: "success", text: `"${doc.filename}" 已开始处理为知识` })
      setDocuments((prev) =>
        prev.map((d) =>
          d.document_id === doc.document_id ? { ...d, status: "processing" } : d
        )
      )
      if (selectedDoc?.document_id === doc.document_id) {
        setSelectedDoc((prev) => prev ? { ...prev, status: "processing" } : prev)
      }
      setTimeout(() => {
        fetchData()
      }, 5000)
    } catch (err: unknown) {
      let detail = "处理失败"
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { data?: { detail?: string; _message?: string } } }
        detail = axiosErr.response?.data?.detail || axiosErr.response?.data?._message || detail
      }
      setMessage({ type: "error", text: detail })
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev)
        next.delete(doc.document_id)
        return next
      })
    }
  }, [processingIds, selectedDoc, fetchData])

  const categoryGroups = useMemo<CategoryGroup[]>(() => {
    const map = new Map<string, KnowledgeDocument[]>()
    for (const doc of documents) {
      const cat = doc.category || "未分类"
      if (!map.has(cat)) {
        map.set(cat, [])
      }
      map.get(cat)!.push(doc)
    }
    return Array.from(map.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([category, docs]) => ({ category, documents: docs }))
  }, [documents])

  const toggleCategory = useCallback((category: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev)
      if (next.has(category)) {
        next.delete(category)
      } else {
        next.add(category)
      }
      return next
    })
  }, [])

  const handleDocClick = useCallback(async (doc: KnowledgeDocument) => {
    setSelectedDoc(doc)
    setDetailOpen(true)
    setPreviewLoading(true)
    setPreviewData(null)
    setDocImages([])
    setPreviewTab("text")
    try {
      const res = await api.get<PreviewData>(`/upload/${doc.document_id}/preview`)
      setPreviewData(res.data)
    } catch {
      setPreviewData(null)
    } finally {
      setPreviewLoading(false)
    }
    setImagesLoading(true)
    try {
      const imgRes = await api.get<{ images: DocumentImage[] }>(`/upload/${doc.document_id}/images`)
      setDocImages(imgRes.data.images || [])
      if ((imgRes.data.images || []).length > 0) {
        setPreviewTab("images")
      }
    } catch {
      setDocImages([])
    } finally {
      setImagesLoading(false)
    }
  }, [])

  const handleAnalyzeImage = useCallback(async (imageId: string) => {
    if (analyzingId) return
    setAnalyzingId(imageId)
    try {
      const res = await api.post<{ ai_description: string }>(`/upload/images/${imageId}/analyze`)
      setDocImages((prev) =>
        prev.map((img) =>
          img.id === imageId
            ? { ...img, ai_description: res.data.ai_description, ai_analyzed: true }
            : img
        )
      )
    } catch {
      setMessage({ type: "error", text: "图片AI分析失败，请检查视觉AI服务" })
    } finally {
      setAnalyzingId(null)
    }
  }, [analyzingId])

  const handleDownload = useCallback(async (documentId: string, filename: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (downloadingIds.has(documentId)) return
    try {
      setDownloadingIds(prev => new Set(prev).add(documentId))
      await downloadFile(documentId, filename)
    } catch {
      setMessage({ type: "error", text: "下载文档失败，请稍后重试" })
    } finally {
      setDownloadingIds(prev => {
        const next = new Set(prev)
        next.delete(documentId)
        return next
      })
    }
  }, [downloadingIds])

  const handleComplete = useCallback(async (doc: KnowledgeDocument, e: React.MouseEvent) => {
    e.stopPropagation()
    if (completingIds.has(doc.document_id)) return

    setCompletingIds((prev) => new Set(prev).add(doc.document_id))
    setMessage(null)
    try {
      await api.post(`/upload/${doc.document_id}/complete`)
      setMessage({ type: "success", text: `"${doc.filename}" 已标记为已完成` })
      setDocuments((prev) =>
        prev.map((d) =>
          d.document_id === doc.document_id ? { ...d, status: "completed" } : d
        )
      )
      if (selectedDoc?.document_id === doc.document_id) {
        setSelectedDoc((prev) => prev ? { ...prev, status: "completed" } : prev)
      }
    } catch (err: unknown) {
      let detail = "标记完成失败"
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } }
        detail = axiosErr.response?.data?.detail || detail
      }
      setMessage({ type: "error", text: detail })
    } finally {
      setCompletingIds((prev) => {
        const next = new Set(prev)
        next.delete(doc.document_id)
        return next
      })
    }
  }, [completingIds, selectedDoc])

  const completedDocs = documents.filter((d) => d.status === "completed")
  const totalChunks = documents.reduce((sum, d) => sum + (d.chunk_count || 0), 0)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">知识库</h1>
          <p className="text-muted-foreground mt-1">
            浏览知识库中的文档与内容数据
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
          <RefreshCw className={`mr-1 h-3 w-3 ${loading ? "animate-spin" : ""}`} />
          刷新
        </Button>
      </div>

      {message && (
        <div className={`flex items-center gap-2 rounded-md px-4 py-3 text-sm ${
          message.type === "success"
            ? "bg-green-50 text-green-700"
            : "bg-destructive/10 text-destructive"
        }`}>
          {message.type === "success" ? (
            <CheckCircle2 className="h-4 w-4 shrink-0" />
          ) : (
            <AlertCircle className="h-4 w-4 shrink-0" />
          )}
          {message.text}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              文档总数
            </CardTitle>
            <FileText className="h-5 w-5 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {loading ? (
                <div className="h-8 w-20 animate-pulse rounded bg-muted" />
              ) : (
                (stats?.document_count ?? documents.length).toLocaleString()
              )}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              分块总数
            </CardTitle>
            <Layers className="h-5 w-5 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {loading ? (
                <div className="h-8 w-20 animate-pulse rounded bg-muted" />
              ) : (
                (stats?.total_chunks || totalChunks).toLocaleString()
              )}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              已完成文档
            </CardTitle>
            <Database className="h-5 w-5 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {loading ? (
                <div className="h-8 w-20 animate-pulse rounded bg-muted" />
              ) : (
                completedDocs.length.toLocaleString()
              )}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              向量库状态
            </CardTitle>
            <HardDrive className="h-5 w-5 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {loading ? (
                <div className="h-8 w-20 animate-pulse rounded bg-muted" />
              ) : stats?.chroma_status ? (
                <Badge
                  variant="outline"
                  className={
                    stats.chroma_status === "healthy"
                      ? "bg-green-100 text-green-800 border-green-200 text-lg px-3 py-1"
                      : "bg-red-100 text-red-800 border-red-200 text-lg px-3 py-1"
                  }
                >
                  {stats.chroma_status === "healthy" ? "正常" : stats.chroma_status}
                </Badge>
              ) : (
                <span className="text-lg text-muted-foreground">-</span>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="搜索知识库文档..."
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            className="pl-9"
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSearch()
            }}
          />
        </div>
        <Button onClick={handleSearch} disabled={loading}>
          <Search className="mr-2 h-4 w-4" />
          搜索
        </Button>
        {searchKeyword && (
          <Button
            variant="outline"
            onClick={() => {
              setSearchKeyword("")
              fetchData()
            }}
          >
            清除
          </Button>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            分类浏览
            <Badge variant="secondary">{categoryGroups.length} 个分类</Badge>
            <Badge variant="secondary">{documents.length} 篇文档</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex h-40 items-center justify-center">
              <p className="text-muted-foreground">加载中...</p>
            </div>
          ) : categoryGroups.length === 0 ? (
            <div className="flex h-40 flex-col items-center justify-center gap-2">
              <FileText className="h-12 w-12 text-muted-foreground/30" />
              <p className="text-muted-foreground">暂无文档数据</p>
              <p className="text-xs text-muted-foreground">请先在知识管理页面上传文档</p>
            </div>
          ) : (
            <ScrollArea className="h-[500px]">
              <div className="space-y-2 pr-4">
                {categoryGroups.map((group) => {
                  const isExpanded = expandedCategories.has(group.category)
                  return (
                    <Collapsible
                      key={group.category}
                      open={isExpanded}
                      onOpenChange={() => toggleCategory(group.category)}
                    >
                      <CollapsibleTrigger asChild>
                        <Button
                          variant="ghost"
                          className="w-full justify-start gap-2 h-auto py-3 px-4"
                        >
                          {isExpanded ? (
                            <ChevronDown className="h-4 w-4 shrink-0" />
                          ) : (
                            <ChevronRight className="h-4 w-4 shrink-0" />
                          )}
                          <FileText className="h-4 w-4 shrink-0 text-blue-500" />
                          <span className="font-medium">{group.category}</span>
                          <Badge variant="secondary" className="ml-auto">
                            {group.documents.length} 篇文档
                          </Badge>
                        </Button>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <div className="ml-6 space-y-2 pb-2">
                          {group.documents.map((doc) => {
                            const statusCfg = STATUS_CONFIG[doc.status]
                            const isProcessing = doc.status === "processing"
                            const canProcess = isAdmin && canProcessToKnowledge(doc.status)
                            return (
                              <div
                                key={doc.document_id}
                                className={`card-overlap-fix items-center rounded-md px-4 py-3 text-sm hover:bg-muted/50 cursor-pointer min-w-0 transition-all duration-200 hover:shadow-md ${
                                  isProcessing ? "bg-orange-50/50" : (isLight ? "bg-slate-50" : "bg-[rgba(21,21,40,0.3)]")
                                }`}
                                onClick={() => handleDocClick(doc)}
                              >
                                <div className="flex items-center gap-3">
                                  <div className="shrink-0">
                                    {getFileIcon(doc.file_type)}
                                  </div>
                                  <span className="truncate min-w-0 flex-1 text-overlap-fix" style={{ color: isLight ? '#1e293b' : '#e8e8e8' }}>{doc.filename}</span>
                                  <span className="text-xs text-muted-foreground shrink-0">
                                    {doc.file_size_display}
                                  </span>
                                  {doc.chunk_count > 0 && (
                                    <Badge variant="outline" className="text-xs shrink-0">
                                      {doc.chunk_count} 分块
                                    </Badge>
                                  )}
                                  {statusCfg && (
                                    <Badge variant="outline" className={`text-xs shrink-0 ${statusCfg.className}`}>
                                      {statusCfg.icon}
                                      {statusCfg.label}
                                    </Badge>
                                  )}
                                </div>
                                <div className="flex items-center gap-2 ml-8">
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    className="shrink-0 h-7 w-7 p-0"
                                    disabled={downloadingIds.has(doc.document_id)}
                                    onClick={(e) => handleDownload(doc.document_id, doc.filename, e)}
                                    title="下载"
                                  >
                                    {downloadingIds.has(doc.document_id) ? (
                                      <Loader2 className="h-3.5 w-3.5 animate-spin" style={{ color: isLight ? colors.CYBER_BLUE : '#3b82f6' }} />
                                    ) : (
                                      <Download className="h-3.5 w-3.5" style={{ color: isLight ? colors.CYBER_BLUE : '#3b82f6' }} />
                                    )}
                                  </Button>
                                  {doc.status !== "completed" && ["approved", "parsed", "processing", "failed"].includes(doc.status) && (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="text-xs h-7 shrink-0"
                                      style={{
                                        border: `1px solid ${isLight ? '#22c55e80' : 'rgba(34,197,94,0.5)'}`,
                                        color: isLight ? '#16a34a' : '#4ade80'
                                      }}
                                      onMouseEnter={(e) => { if (!isLight) e.currentTarget.style.background = 'rgba(34,197,94,0.1)' }}
                                      onMouseLeave={(e) => { if (!isLight) e.currentTarget.style.background = 'transparent' }}
                                      disabled={completingIds.has(doc.document_id)}
                                      onClick={(e) => handleComplete(doc, e)}
                                    >
                                      {completingIds.has(doc.document_id) ? (
                                        <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                                      ) : (
                                        <CheckCircle2 className="mr-1 h-3 w-3" />
                                      )}
                                      完成
                                    </Button>
                                  )}
                                  {canProcess && (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="text-xs h-7 shrink-0" style={{ 
                                        border: `1px solid ${isLight ? colors.CYBER_BLUE + '50' : 'rgba(59,130,246,0.5)'}`,
                                        color: isLight ? colors.CYBER_BLUE : '#3b82f6' 
                                      }}
                                      onMouseEnter={(e) => { if (!isLight) e.currentTarget.style.background = 'rgba(59,130,246,0.1)' }}
                                      onMouseLeave={(e) => { if (!isLight) e.currentTarget.style.background = 'transparent' }}
                                      disabled={processingIds.has(doc.document_id)}
                                      onClick={(e) => handleProcessToKnowledge(doc, e)}
                                    >
                                      {processingIds.has(doc.document_id) ? (
                                        <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                                      ) : (
                                        <Zap className="mr-1 h-3 w-3" />
                                      )}
                                      {getProcessButtonLabel(doc.status)}
                                    </Button>
                                  )}
                                  {isProcessing && !canProcess && (
                                    <div className="flex items-center gap-1 text-xs text-orange-500 shrink-0">
                                      <Loader2 className="h-3 w-3 animate-spin" />
                                      处理中...
                                    </div>
                                  )}
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      </CollapsibleContent>
                    </Collapsible>
                  )
                })}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="truncate">
              {selectedDoc?.filename}
            </DialogTitle>
            <DialogDescription>
              {selectedDoc && (
                <span className="flex items-center gap-2 flex-wrap">
                  <Badge variant="outline">{selectedDoc.category}</Badge>
                  {selectedDoc.chunk_count > 0 && (
                    <Badge variant="outline">{selectedDoc.chunk_count} 个分块</Badge>
                  )}
                  <Badge variant="outline">{selectedDoc.file_type.toUpperCase()}</Badge>
                  <Badge variant="outline">{selectedDoc.file_size_display}</Badge>
                  {selectedDoc.uploader_name && (
                    <Badge variant="outline">上传者: {selectedDoc.uploader_name}</Badge>
                  )}
                  {STATUS_CONFIG[selectedDoc.status] && (
                    <Badge variant="outline" className={STATUS_CONFIG[selectedDoc.status].className}>
                      {STATUS_CONFIG[selectedDoc.status].icon}
                      {STATUS_CONFIG[selectedDoc.status].label}
                    </Badge>
                  )}
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          {selectedDoc && (
            <div className="flex items-center gap-2 border-b pb-3">
              {selectedDoc.status !== "completed" && ["approved", "parsed", "processing", "failed"].includes(selectedDoc.status) && (
                <Button
                  size="sm"
                  className="bg-green-600 hover:bg-green-700"
                  disabled={completingIds.has(selectedDoc.document_id)}
                  onClick={(e) => handleComplete(selectedDoc, e)}
                >
                  {completingIds.has(selectedDoc.document_id) ? (
                    <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                  ) : (
                    <CheckCircle2 className="mr-1 h-3 w-3" />
                  )}
                  标记完成
                </Button>
              )}
              {isAdmin && canProcessToKnowledge(selectedDoc.status) && (
                <Button
                  size="sm"
                  className="bg-indigo-600 hover:bg-indigo-700"
                  disabled={processingIds.has(selectedDoc.document_id)}
                  onClick={(e) => handleProcessToKnowledge(selectedDoc, e)}
                >
                  {processingIds.has(selectedDoc.document_id) ? (
                    <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                  ) : (
                    <Zap className="mr-1 h-3 w-3" />
                  )}
                  {getProcessButtonLabel(selectedDoc.status)}
                </Button>
              )}
              <span className="text-xs text-muted-foreground">
                {selectedDoc.status === "completed"
                  ? "文档已标记为已完成"
                  : selectedDoc.status === "approved"
                  ? "将文档解析、分块并向量化，存入向量知识库"
                  : selectedDoc.status === "failed"
                  ? "上次处理失败，点击重新处理"
                  : "重新解析并更新向量知识库"}
              </span>
            </div>
          )}
          <div className="flex items-center gap-1 border-b pb-2">
            <button
              onClick={() => setPreviewTab("text")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors ${
                previewTab === "text"
                  ? "bg-slate-200 dark:bg-slate-700 font-medium"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <FileText className="h-3.5 w-3.5" />
              文本内容
            </button>
            <button
              onClick={() => setPreviewTab("images")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors ${
                previewTab === "images"
                  ? "bg-slate-200 dark:bg-slate-700 font-medium"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Image className="h-3.5 w-3.5" />
              图片分析
              {docImages.length > 0 && (
                <Badge variant="secondary" className="ml-1 text-xs px-1.5 py-0">
                  {docImages.length}
                </Badge>
              )}
              {imagesLoading && <Loader2 className="h-3 w-3 animate-spin" />}
            </button>
          </div>
          <div className="flex-1 min-h-0">
            {previewTab === "text" ? (
              previewLoading ? (
                <div className="flex h-40 items-center justify-center">
                  <p className="text-muted-foreground">加载文档内容...</p>
                </div>
              ) : !previewData ? (
                <div className="flex h-40 items-center justify-center">
                  <p className="text-muted-foreground">暂无预览内容</p>
                </div>
              ) : (
                <ScrollArea className="h-[55vh]">
                  <div className="space-y-3 pr-4">
                    {previewData.content.split("\n---\n").map((pageContent, idx) => (
                      <Card key={idx}>
                        <CardContent className="p-4">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant="secondary">
                              第 {idx + 1} 部分
                            </Badge>
                          </div>
                          <p className="text-sm leading-relaxed whitespace-pre-wrap">
                            {sanitizeText(pageContent)}
                          </p>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </ScrollArea>
              )
            ) : imagesLoading ? (
              <div className="flex h-40 items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                <p className="ml-2 text-muted-foreground">加载图片...</p>
              </div>
            ) : docImages.length === 0 ? (
              <div className="flex h-40 flex-col items-center justify-center gap-2">
                <Image className="h-12 w-12 text-muted-foreground/30" />
                <p className="text-muted-foreground">该文档未提取到图片</p>
                <p className="text-xs text-muted-foreground">PDF文档中的图片会在处理时自动提取和分析</p>
              </div>
            ) : (
              <ScrollArea className="h-[55vh]">
                <div className="space-y-4 pr-4">
                  {docImages.map((img) => (
                    <Card key={img.id} className="overflow-hidden">
                      <div className="grid grid-cols-1 sm:grid-cols-[200px_1fr] gap-0">
                        <div className="bg-slate-100 dark:bg-slate-800 flex items-center justify-center p-3 border-b sm:border-b-0 sm:border-r min-h-[150px] sm:min-h-0">
                          <img
                            src={img.image_url}
                            alt={`第${img.page_number}页图片${img.image_index + 1}`}
                            className="max-w-full max-h-48 object-contain rounded"
                          />
                        </div>
                        <div className="p-4 space-y-3 min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant="secondary">
                              第 {img.page_number} 页
                            </Badge>
                            <Badge variant="outline">
                              图片 {img.image_index + 1}
                            </Badge>
                            {img.ai_analyzed ? (
                              <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                                <Eye className="mr-1 h-3 w-3" />
                                AI已分析
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
                                待分析
                              </Badge>
                            )}
                          </div>
                          {img.ai_description ? (
                            <div>
                              <p className="text-xs font-medium text-muted-foreground mb-1">AI 视觉分析结果</p>
                              <p className="text-sm leading-relaxed bg-slate-50 dark:bg-slate-900 rounded-md p-3 break-words">
                                {sanitizeText(img.ai_description)}
                              </p>
                            </div>
                          ) : (
                            <p className="text-sm text-muted-foreground">暂无AI分析结果</p>
                          )}
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-xs"
                            disabled={analyzingId === img.id}
                            onClick={() => handleAnalyzeImage(img.id)}
                          >
                            {analyzingId === img.id ? (
                              <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                            ) : (
                              <Sparkles className="mr-1 h-3 w-3" />
                            )}
                            {img.ai_analyzed ? "重新分析" : "AI分析"}
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </ScrollArea>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
