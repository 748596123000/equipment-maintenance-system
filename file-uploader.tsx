import { useState, useRef, useCallback } from "react";
import type { ChangeEvent, DragEvent } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Upload } from "lucide-react";

const ACCEPTED_TYPES = [
  ".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md", ".csv",
  ".json", ".xml", ".log", ".jpg", ".jpeg", ".png", ".bmp",
  ".gif", ".tiff", ".webp",
];

const CATEGORIES = [
  "通用", "变压器", "开关柜", "断路器", "隔离开关",
  "互感器", "避雷器", "电容器", "电缆", "继电保护装置", "其他",
];

interface FileEntry {
  file: File;
  progress: number;
  status: "pending" | "uploading" | "success" | "error";
  error?: string;
}

interface FileUploaderProps {
  category: string;
  onUploadComplete?: () => void;
}

function getFileIcon(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  if (["pdf"].includes(ext)) return "📄";
  if (["docx", "doc"].includes(ext)) return "📝";
  if (["xlsx", "xls", "csv"].includes(ext)) return "📊";
  if (["pptx", "ppt"].includes(ext)) return "📽️";
  if (["jpg", "jpeg", "png", "bmp", "gif", "tiff", "webp"].includes(ext)) return "🖼️";
  if (["txt", "md", "log"].includes(ext)) return "📃";
  if (["json", "xml"].includes(ext)) return "🔧";
  return "📎";
}

export function FileUploader({ category, onUploadComplete }: FileUploaderProps) {
  const [selectedCategory, setSelectedCategory] = useState(category);
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const entries: FileEntry[] = Array.from(newFiles).map((file) => ({
      file,
      progress: 0,
      status: "pending" as const,
    }));
    setFiles((prev) => [...prev, ...entries]);
  }, []);

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      if (e.dataTransfer.files.length > 0) {
        addFiles(e.dataTransfer.files);
      }
    },
    [addFiles]
  );

  const handleFileSelect = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        addFiles(e.target.files);
        e.target.value = "";
      }
    },
    [addFiles]
  );

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const uploadFiles = useCallback(async () => {
    const pendingFiles = files.filter((f) => f.status === "pending");
    for (const entry of pendingFiles) {
      setFiles((prev) =>
        prev.map((f) =>
          f.file === entry.file ? { ...f, status: "uploading" as const, progress: 0 } : f
        )
      );

      const formData = new FormData();
      formData.append("file", entry.file);
      formData.append("category", selectedCategory);

      try {
        await api.post("/upload/file", formData, {
          headers: { "Content-Type": "multipart/form-data" },
          onUploadProgress: (event) => {
            if (event.total) {
              const progress = Math.round((event.loaded / event.total) * 100);
              setFiles((prev) =>
                prev.map((f) =>
                  f.file === entry.file ? { ...f, progress } : f
                )
              );
            }
          },
        });

        setFiles((prev) =>
          prev.map((f) =>
            f.file === entry.file
              ? { ...f, status: "success" as const, progress: 100 }
              : f
          )
        );
      } catch (err) {
        const message = err instanceof Error ? err.message : "上传失败";
        setFiles((prev) =>
          prev.map((f) =>
            f.file === entry.file
              ? { ...f, status: "error" as const, error: message }
              : f
          )
        );
      }
    }

    const allDone = files.every(
      (f) => f.status === "success" || f.file === pendingFiles[pendingFiles.length - 1]?.file
    );
    if (allDone || pendingFiles.length > 0) {
      onUploadComplete?.();
    }
  }, [files, selectedCategory, onUploadComplete]);

  const hasPendingFiles = files.some((f) => f.status === "pending");
  const isUploading = files.some((f) => f.status === "uploading");

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <label className="mb-1.5 block text-sm font-medium">文档分类</label>
          <Select value={selectedCategory} onValueChange={setSelectedCategory}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="选择分类" />
            </SelectTrigger>
            <SelectContent>
              {CATEGORIES.map((cat) => (
                <SelectItem key={cat} value={cat}>
                  {cat}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div
        className={`flex min-h-[160px] cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors ${
          isDragging
            ? "border-primary bg-primary/5"
            : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50"
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <Upload className="mb-2 h-8 w-8 text-muted-foreground" />
        <p className="text-sm font-medium text-muted-foreground">
          拖拽文件到此处，或点击选择文件
        </p>
        <p className="mt-1 text-xs text-muted-foreground/70">
          支持格式：{ACCEPTED_TYPES.join(", ")}
        </p>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED_TYPES.join(",")}
          className="hidden"
          onChange={handleFileSelect}
        />
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">待上传文件 ({files.length})</p>
            <Button
              size="sm"
              disabled={!hasPendingFiles || isUploading}
              onClick={uploadFiles}
            >
              <Upload className="mr-1 h-4 w-4" />
              {isUploading ? "上传中..." : "开始上传"}
            </Button>
          </div>

          <div className="space-y-2">
            {files.map((entry, index) => (
              <div
                key={`${entry.file.name}-${index}`}
                className="flex items-center gap-3 rounded-md border p-3"
              >
                <span className="text-lg">{getFileIcon(entry.file.name)}</span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">
                    {entry.file.name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {(entry.file.size / 1024).toFixed(1)} KB
                  </p>
                  {entry.status === "uploading" && (
                    <Progress value={entry.progress} className="mt-1.5 h-1.5" />
                  )}
                  {entry.status === "error" && entry.error && (
                    <p className="mt-0.5 text-xs text-destructive">{entry.error}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {entry.status === "success" && (
                    <span className="text-xs font-medium text-green-600">✓ 上传成功</span>
                  )}
                  {entry.status === "error" && (
                    <span className="text-xs font-medium text-destructive">✗ 上传失败</span>
                  )}
                  {entry.status === "uploading" && (
                    <span className="text-xs text-muted-foreground">{entry.progress}%</span>
                  )}
                  {entry.status === "pending" && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        removeFile(index);
                      }}
                    >
                      ✕
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
