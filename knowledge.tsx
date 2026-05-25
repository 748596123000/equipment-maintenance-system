import { useEffect, useState, useCallback } from "react";
import { useAuthStore } from "@/stores/auth-store";
import { api } from "@/lib/api";
import { FileUploader } from "@/components/document/file-uploader";
import { DocTable } from "@/components/document/doc-table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Check, X, Trash2 } from "lucide-react";

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

export default function KnowledgePage() {
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.role === "admin";

  const [myDocs, setMyDocs] = useState<Document[]>([]);
  const [allDocs, setAllDocs] = useState<Document[]>([]);
  const [pendingDocs, setPendingDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [rejectTarget, setRejectTarget] = useState<Document | null>(null);
  const [rejectComment, setRejectComment] = useState("");

  const [approveDialogOpen, setApproveDialogOpen] = useState(false);
  const [approveTarget, setApproveTarget] = useState<Document | null>(null);
  const [approveComment, setApproveComment] = useState("");

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const fetchMyDocs = useCallback(async () => {
    try {
      const res = await api.get<{ documents: Document[] }>("/upload/my");
      setMyDocs(res.data.documents || []);
    } catch {
      setMyDocs([]);
    }
  }, []);

  const fetchAllDocs = useCallback(async () => {
    try {
      const res = await api.get<{ documents: Document[] }>("/upload/list");
      setAllDocs(res.data.documents || []);
    } catch {
      setAllDocs([]);
    }
  }, []);

  const fetchPendingDocs = useCallback(async () => {
    try {
      const res = await api.get<{ documents: Document[] }>("/upload/pending");
      setPendingDocs(res.data.documents || []);
    } catch {
      setPendingDocs([]);
    }
  }, []);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      if (isAdmin) {
        await Promise.all([fetchAllDocs(), fetchPendingDocs()]);
      } else {
        await fetchMyDocs();
      }
      setLoading(false);
    }
    fetchData();
  }, [isAdmin, fetchAllDocs, fetchPendingDocs, fetchMyDocs]);

  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/upload/${deleteTarget}`);
      if (isAdmin) {
        fetchAllDocs();
        fetchPendingDocs();
      } else {
        fetchMyDocs();
      }
    } catch {
      setErrorMsg("删除文档失败，请稍后重试");
    } finally {
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    }
  }, [deleteTarget, isAdmin, fetchAllDocs, fetchPendingDocs, fetchMyDocs]);

  const handleApprove = useCallback(async () => {
    if (!approveTarget) return;
    try {
      await api.post(`/upload/${approveTarget.document_id}/approve`, {
        comment: approveComment,
      });
      fetchPendingDocs();
      fetchAllDocs();
    } catch {
      setErrorMsg("审批通过失败，请稍后重试");
    } finally {
      setApproveDialogOpen(false);
      setApproveTarget(null);
      setApproveComment("");
    }
  }, [approveTarget, approveComment, fetchPendingDocs, fetchAllDocs]);

  const handleReject = useCallback(async () => {
    if (!rejectTarget) return;
    try {
      await api.post(`/upload/${rejectTarget.document_id}/reject`, {
        comment: rejectComment,
      });
      fetchPendingDocs();
      fetchAllDocs();
    } catch {
      setErrorMsg("审批拒绝失败，请稍后重试");
    } finally {
      setRejectDialogOpen(false);
      setRejectTarget(null);
      setRejectComment("");
    }
  }, [rejectTarget, rejectComment, fetchPendingDocs, fetchAllDocs]);

  const openRejectDialog = useCallback((doc: Document) => {
    setRejectTarget(doc);
    setRejectComment("");
    setRejectDialogOpen(true);
  }, []);

  const openApproveDialog = useCallback((doc: Document) => {
    setApproveTarget(doc);
    setApproveComment("");
    setApproveDialogOpen(true);
  }, []);

  const openDeleteDialog = useCallback((id: string) => {
    setDeleteTarget(id);
    setDeleteDialogOpen(true);
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">📚 知识管理</h1>
        <div className="h-64 animate-pulse rounded-lg bg-muted" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">📚 知识管理</h1>

      {!isAdmin && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>上传文档</CardTitle>
            </CardHeader>
            <CardContent>
              <FileUploader category="通用" onUploadComplete={fetchMyDocs} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>我的文档列表</CardTitle>
            </CardHeader>
            <CardContent>
              <DocTable documents={myDocs} onDelete={openDeleteDialog} />
            </CardContent>
          </Card>
        </>
      )}

      {isAdmin && (
        <>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>待审批文档</CardTitle>
              <Badge variant="outline" className="bg-yellow-100 text-yellow-800 border-yellow-200">
                {pendingDocs.length} 条待审批
              </Badge>
            </CardHeader>
            <CardContent>
              {pendingDocs.length === 0 ? (
                <p className="py-8 text-center text-muted-foreground">暂无待审批文档</p>
              ) : (
                <div className="space-y-3">
                  {pendingDocs.map((doc) => (
                    <div
                      key={doc.document_id}
                      className="flex items-center justify-between rounded-lg border p-4"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium">{doc.filename}</p>
                        <div className="mt-1 flex items-center gap-3 text-sm text-muted-foreground">
                          <span>{doc.file_type.toUpperCase()}</span>
                          <span>{doc.file_size_display}</span>
                          <span>{doc.category}</span>
                          <span>上传者: {doc.uploader_name}</span>
                          <span>{new Date(doc.created_at).toLocaleString("zh-CN")}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          onClick={() => openApproveDialog(doc)}
                        >
                          <Check className="mr-1 h-4 w-4" />
                          通过
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => openRejectDialog(doc)}
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

          <Card>
            <CardHeader>
              <CardTitle>所有文档</CardTitle>
            </CardHeader>
            <CardContent>
              <DocTable documents={allDocs} onDelete={openDeleteDialog} />
            </CardContent>
          </Card>
        </>
      )}

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>确定要删除该文档吗？此操作不可撤销。</DialogDescription>
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
            <DialogTitle>审批通过</DialogTitle>
            <DialogDescription>
              确认通过文档「{approveTarget?.filename}」的审批？
            </DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <label className="mb-1.5 block text-sm font-medium">审批意见（可选）</label>
            <Input
              placeholder="请输入审批意见"
              value={approveComment}
              onChange={(e) => setApproveComment(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setApproveDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleApprove}>
              <Check className="mr-1 h-4 w-4" />
              确认通过
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>拒绝审批</DialogTitle>
            <DialogDescription>
              拒绝文档「{rejectTarget?.filename}」的审批，请填写拒绝原因。
            </DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <label className="mb-1.5 block text-sm font-medium">拒绝原因</label>
            <Input
              placeholder="请输入拒绝原因"
              value={rejectComment}
              onChange={(e) => setRejectComment(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectDialogOpen(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleReject}>
              <X className="mr-1 h-4 w-4" />
              确认拒绝
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
