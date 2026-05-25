import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Eye, Trash2, FileText, FileSpreadsheet, Presentation, Image, FileType, Download, Loader2 } from "lucide-react";
import type { ReactNode } from "react";

interface Document {
  document_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  file_size_display: string;
  category: string;
  page_count: number;
  chunk_count: number;
  status: string;
  uploader_name: string;
  created_at: string;
}

interface DocTableProps {
  documents: Document[];
  onDelete?: (id: string) => void;
  onPreview?: (id: string) => void;
  onDownload?: (id: string, filename: string) => void;
  downloadingIds?: Set<string>;
}

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  pending: { label: "待处理", className: "bg-yellow-100 text-yellow-800 border-yellow-200" },
  approved: { label: "已审核", className: "bg-blue-100 text-blue-800 border-blue-200" },
  completed: { label: "已完成", className: "bg-green-100 text-green-800 border-green-200" },
  rejected: { label: "已拒绝", className: "bg-red-100 text-red-800 border-red-200" },
  processing: { label: "处理中", className: "bg-orange-100 text-orange-800 border-orange-200" },
  failed: { label: "失败", className: "bg-red-100 text-red-800 border-red-200" },
  parsed: { label: "已解析", className: "bg-purple-100 text-purple-800 border-purple-200" },
};

function getFileTypeIcon(fileType: string): ReactNode {
  const ext = fileType.toLowerCase().replace(".", "");
  if (ext === "pdf") return <FileText className="h-4 w-4 text-red-500" />;
  if (["docx", "doc", "txt", "md", "log"].includes(ext)) return <FileText className="h-4 w-4 text-blue-500" />;
  if (["xlsx", "xls", "csv"].includes(ext)) return <FileSpreadsheet className="h-4 w-4 text-green-500" />;
  if (["pptx", "ppt"].includes(ext)) return <Presentation className="h-4 w-4 text-orange-500" />;
  if (["jpg", "jpeg", "png", "bmp", "gif", "tiff", "webp"].includes(ext)) return <Image className="h-4 w-4 text-purple-500" />;
  if (["json", "xml"].includes(ext)) return <FileType className="h-4 w-4 text-gray-500" />;
  return <FileText className="h-4 w-4 text-gray-400" />;
}

function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status];
  if (!config) {
    return <Badge variant="outline">{status}</Badge>;
  }
  return <Badge variant="outline" className={config.className}>{config.label}</Badge>;
}

export function DocTable({ documents, onDelete, onPreview, onDownload, downloadingIds }: DocTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>文件名</TableHead>
          <TableHead>类型</TableHead>
          <TableHead>大小</TableHead>
          <TableHead>分类</TableHead>
          <TableHead>页数</TableHead>
          <TableHead>分块数</TableHead>
          <TableHead>状态</TableHead>
          <TableHead>上传者</TableHead>
          <TableHead>上传时间</TableHead>
          <TableHead>操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {documents.length === 0 ? (
          <TableRow>
            <TableCell colSpan={10} className="h-24 text-center text-muted-foreground">
              暂无文档数据
            </TableCell>
          </TableRow>
        ) : (
          documents.map((doc) => (
            <TableRow key={doc.document_id}>
              <TableCell className="max-w-[200px]">
                <div className="flex items-center gap-2">
                  {getFileTypeIcon(doc.file_type)}
                  <span className="truncate font-medium">{doc.filename}</span>
                </div>
              </TableCell>
              <TableCell>{doc.file_type.toUpperCase()}</TableCell>
              <TableCell>{doc.file_size_display}</TableCell>
              <TableCell>{doc.category}</TableCell>
              <TableCell>{doc.page_count ?? "-"}</TableCell>
              <TableCell>{doc.chunk_count ?? "-"}</TableCell>
              <TableCell>
                <StatusBadge status={doc.status} />
              </TableCell>
              <TableCell>{doc.uploader_name}</TableCell>
              <TableCell>{new Date(doc.created_at).toLocaleString("zh-CN")}</TableCell>
              <TableCell>
                <div className="flex items-center gap-1">
                  {onDownload && (
                    <Button
                      variant="ghost"
                      size="icon"
                      disabled={downloadingIds?.has(doc.document_id)}
                      onClick={() => onDownload(doc.document_id, doc.filename)}
                      title="下载"
                    >
                      {downloadingIds?.has(doc.document_id) ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Download className="h-4 w-4" />
                      )}
                    </Button>
                  )}
                  {onPreview && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onPreview(doc.document_id)}
                      title="预览"
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  )}
                  {onDelete && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onDelete(doc.document_id)}
                      title="删除"
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  )}
                </div>
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}
