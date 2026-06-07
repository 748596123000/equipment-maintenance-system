import { useEffect, useState, useCallback, useMemo, lazy, Suspense } from "react"
import { api, downloadFile } from "@/lib/api"
import { sanitizeText } from "@/lib/sanitize"
import { DocTable } from "@/components/document/doc-table"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select"
import { Search, FileText, Layers, Trash2, AlertTriangle, Loader2 } from "lucide-react"

// Lazy load heavy PDF viewer component
const PdfViewer = lazy(() => import("@/components/document/pdf-viewer").then(m => ({ default: m.PdfViewer })))

// Loading fallback with cyberpunk animation
function ComponentLoader() {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="relative">
        <div className="w-10 h-10 border-4 border-[var(--color-border,#e2e8f0)] border-t-[#00f0ff] rounded-full animate-spin" />
        <div className="absolute inset-0 w-10 h-10 border-4 border-[rgba(0,240,255,0.3)] border-b-[#6366f1] rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }} />
      </div>
    </div>
  )
}

interface Document {
  document_id: string
  filename: string
  file_type: string
  file_size: number
  file_size_display: string
  category: string
  page_count: number
  chunk_count: number
  status: string
  uploader_name: string
  created_at: string
}

interface PreviewData {
  content: string
  filename: string
  file_type: string
}

export default function DatabasePage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [searchKeyword, setSearchKeyword] = useState("")
  const [categoryFilter, setCategoryFilter] = useState("all")
  const [previewDoc, setPreviewDoc] = useState<Document | null>(null)
  const [previewData, setPreviewData] = useState<PreviewData | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [downloadingIds, setDownloadingIds] = useState<Set<string>>(new Set())

  const fetchDocuments = useCallback(async () => {
    try {
      setLoading(true)
      const res = await api.get<{ documents: Document[] }>("/upload/list", {
        params: { status: "completed" },
      })
      setDocuments(res.data.documents || [])
    } catch {
      setDocuments([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  const categories = useMemo(() => {
    const cats = new Set(documents.map((d) => d.category))
    return Array.from(cats).sort()
  }, [documents])

  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) => {
      const matchesSearch = doc.filename
        .toLowerCase()
        .includes(searchKeyword.toLowerCase())
      const matchesCategory =
        categoryFilter === "all" || doc.category === categoryFilter
      return matchesSearch && matchesCategory
    })
  }, [documents, searchKeyword, categoryFilter])

  const totalChunks = useMemo(
    () => documents.reduce((sum, d) => sum + (d.chunk_count || 0), 0),
    [documents]
  )

  const handlePreview = useCallback(async (docId: string) => {
    const doc = documents.find((d) => d.document_id === docId)
    if (!doc) return

    setPreviewDoc(doc)
    setPreviewData(null)
    setPreviewLoading(true)

    if ((doc.file_type || '').toLowerCase().replace(".", "") === "pdf") {
      setPreviewLoading(false)
      return
    }

    try {
      const res = await api.get<PreviewData>(`/upload/${docId}/preview`)
      setPreviewData(res.data)
    } catch {
      setPreviewData(null)
    } finally {
      setPreviewLoading(false)
    }
  }, [documents])

  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return
    try {
      setDeleteLoading(true)
      await api.delete(`/upload/${deleteTarget.document_id}`)
      setDocuments((prev) =>
        prev.filter((d) => d.document_id !== deleteTarget.document_id)
      )
      setDeleteTarget(null)
    } catch {
      setErrorMsg('删除文档失败，请稍后重试')
    } finally {
      setDeleteLoading(false)
    }
  }, [deleteTarget])

  const handleDownload = useCallback(async (documentId: string, filename: string) => {
    if (downloadingIds.has(documentId)) return
    try {
      setDownloadingIds(prev => new Set(prev).add(documentId))
      await downloadFile(documentId, filename)
    } catch {
      setErrorMsg('下载文档失败，请稍后重试')
    } finally {
      setDownloadingIds(prev => {
        const next = new Set(prev)
        next.delete(documentId)
        return next
      })
    }
  }, [downloadingIds])

  const isPdfPreview = (previewDoc?.file_type || '').toLowerCase().replace(".", "") === "pdf"

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">📚 文档数据库</h1>
        <p className="text-muted-foreground mt-1">
          管理已完成的文档，支持预览与删除操作
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-2">
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
                documents.length.toLocaleString()
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
                totalChunks.toLocaleString()
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="搜索文档名称..."
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="选择分类" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">
              全部分类
              <Badge variant="secondary" className="ml-2">
                {documents.length}
              </Badge>
            </SelectItem>
            {categories.map((cat) => {
              const count = documents.filter((d) => d.category === cat).length
              return (
                <SelectItem key={cat} value={cat}>
                  {cat}
                  <Badge variant="secondary" className="ml-2">
                    {count}
                  </Badge>
                </SelectItem>
              )
            })}
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex h-40 items-center justify-center">
              <p className="text-muted-foreground">加载中...</p>
            </div>
          ) : (
            <DocTable
              documents={filteredDocuments}
              onDelete={(id) => {
                const doc = documents.find((d) => d.document_id === id)
                if (doc) setDeleteTarget(doc)
              }}
              onPreview={handlePreview}
              onDownload={handleDownload}
              downloadingIds={downloadingIds}
            />
          )}
        </CardContent>
      </Card>

      <Dialog
        open={!!previewDoc}
        onOpenChange={(open) => {
          if (!open) {
            setPreviewDoc(null)
            setPreviewData(null)
          }
        }}
      >
        <DialogContent className="max-w-4xl h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="truncate">
              {previewDoc?.filename}
            </DialogTitle>
            <DialogDescription>
              {previewDoc && (
                <span className="flex items-center gap-2">
                  <Badge variant="outline">
                    {previewDoc.file_type.toUpperCase()}
                  </Badge>
                  <Badge variant="outline">{previewDoc.category}</Badge>
                  {previewDoc.chunk_count > 0 && (
                    <Badge variant="outline">
                      {previewDoc.chunk_count} 个分块
                    </Badge>
                  )}
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 min-h-0 overflow-hidden">
            {previewLoading ? (
              <div className="flex h-full items-center justify-center">
                <p className="text-muted-foreground">加载预览中...</p>
              </div>
            ) : isPdfPreview && previewDoc ? (
              <Suspense fallback={<ComponentLoader />}>
              <PdfViewer documentId={previewDoc.document_id} />
            </Suspense>
            ) : previewData ? (
                <div className="h-full overflow-auto rounded-md border bg-muted/30 p-4">
                <pre className="whitespace-pre-wrap text-sm leading-relaxed">
                  {sanitizeText(previewData.content)}
                </pre>
              </div>
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-muted-foreground">无法预览此文件格式</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      <Dialog
        open={!!deleteTarget}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              确认删除
            </DialogTitle>
            <DialogDescription>
              确定要删除文档「{deleteTarget?.filename}」吗？此操作不可撤销，关联的知识库数据也将被移除。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteTarget(null)}
              disabled={deleteLoading}
            >
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteLoading}
            >
              {deleteLoading ? "删除中..." : "确认删除"}
              <Trash2 className="ml-2 h-4 w-4" />
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
