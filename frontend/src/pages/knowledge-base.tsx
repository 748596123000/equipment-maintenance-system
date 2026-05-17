import { useEffect, useState, useCallback, useMemo } from "react"
import { useAuthStore } from "@/stores/auth-store"
import { api } from "@/lib/api"
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

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  pending: { label: "待处理", className: "bg-yellow-100 text-yellow-800 border-yellow-200" },
  approved: { label: "已审核", className: "bg-blue-100 text-blue-800 border-blue-200" },
  completed: { label: "已完成", className: "bg-green-100 text-green-800 border-green-200" },
  rejected: { label: "已拒绝", className: "bg-red-100 text-red-800 border-red-200" },
  processing: { label: "处理中", className: "bg-orange-100 text-orange-800 border-orange-200" },
  parsed: { label: "已解析", className: "bg-purple-100 text-purple-800 border-purple-200" },
}

export default function KnowledgeBasePage() {
  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.role === "admin"

  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [stats, setStats] = useState<KnowledgeStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchKeyword, setSearchKeyword] = useState("")
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())
  const [selectedDoc, setSelectedDoc] = useState<KnowledgeDocument | null>(null)
  const [previewData, setPreviewData] = useState<PreviewData | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)

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
    try {
      const res = await api.get<PreviewData>(`/upload/${doc.document_id}/preview`)
      setPreviewData(res.data)
    } catch {
      setPreviewData(null)
    } finally {
      setPreviewLoading(false)
    }
  }, [])

  const completedDocs = documents.filter((d) => d.status === "completed")
  const totalChunks = documents.reduce((sum, d) => sum + (d.chunk_count || 0), 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">知识库</h1>
        <p className="text-muted-foreground mt-1">
          浏览知识库中的文档与内容数据
        </p>
      </div>

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
                <div className="h-8-20 animate-pulse rounded bg-muted" />
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
                        <div className="ml-6 space-y-1 pb-2">
                          {group.documents.map((doc) => {
                            const statusCfg = STATUS_CONFIG[doc.status]
                            return (
                              <Button
                                key={doc.document_id}
                                variant="ghost"
                                className="w-full justify-start gap-2 h-auto py-2.5 px-4 text-sm"
                                onClick={() => handleDocClick(doc)}
                              >
                                {getFileIcon(doc.file_type)}
                                <span className="truncate max-w-[300px]">{doc.filename}</span>
                                <span className="text-xs text-muted-foreground ml-1">
                                  {doc.file_size_display}
                                </span>
                                {doc.chunk_count > 0 && (
                                  <Badge variant="outline" className="ml-auto text-xs">
                                    {doc.chunk_count} 分块
                                  </Badge>
                                )}
                                {statusCfg && (
                                  <Badge variant="outline" className={`text-xs ${statusCfg.className}`}>
                                    {statusCfg.label}
                                  </Badge>
                                )}
                              </Button>
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
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 min-h-0">
            {previewLoading ? (
              <div className="flex h-40 items-center justify-center">
                <p className="text-muted-foreground">加载文档内容...</p>
              </div>
            ) : !previewData ? (
              <div className="flex h-40 items-center justify-center">
                <p className="text-muted-foreground">暂无预览内容</p>
              </div>
            ) : (
              <ScrollArea className="h-[60vh]">
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
                          {pageContent}
                        </p>
                      </CardContent>
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
