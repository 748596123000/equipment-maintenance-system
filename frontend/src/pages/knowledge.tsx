import { useEffect, useState, useCallback } from "react";
import { useAuthStore } from "@/stores/auth-store";
import { api, downloadFile } from "@/lib/api";
import { FileUploader } from "@/components/document/file-uploader";
import { DocTable } from "@/components/document/doc-table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import { Check, X, Trash2, BookOpen, FileText, Upload, Sparkles, Clock, CheckCircle2, Eye, Download, Loader2 } from "lucide-react";
import { useTheme, COLORS } from '@/hooks/useTheme'
import { GradientText } from '@/components/ui/gradient-text'

const LOCAL_COLORS = COLORS

interface Document {
  document_id: string; filename: string; file_type: string; file_size: number
  file_size_display: string; category: string; page_count: number; chunk_count: number
  status: string; uploader_name: string; created_at: string
}

export default function KnowledgePage() {
  const user = useAuthStore((s) => s.user);
  const { theme } = useTheme()
  const isLight = theme === 'light'
  const colors = isLight ? COLORS.light : COLORS.dark
  
  const isAdmin = user?.role === "admin";
  const [mounted, setMounted] = useState(false);
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
  const [downloadingIds, setDownloadingIds] = useState<Set<string>>(new Set());

  useEffect(() => { setMounted(true) }, [])

  const fetchMyDocs = useCallback(async () => {
    try { const res = await api.get<{ documents: Document[] }>("/upload/my"); setMyDocs(res.data.documents || []); }
    catch { setMyDocs([]); }
  }, []);

  const fetchAllDocs = useCallback(async () => {
    try { const res = await api.get<{ documents: Document[] }>("/upload/list"); setAllDocs(res.data.documents || []); }
    catch { setAllDocs([]); }
  }, []);

  const fetchPendingDocs = useCallback(async () => {
    try { const res = await api.get<{ documents: Document[] }>("/upload/pending"); setPendingDocs(res.data.documents || []); }
    catch { setPendingDocs([]); }
  }, []);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      if (isAdmin) { await Promise.all([fetchAllDocs(), fetchPendingDocs()]); }
      else { await fetchMyDocs(); }
      setLoading(false);
    }
    fetchData();
  }, [isAdmin, fetchAllDocs, fetchPendingDocs, fetchMyDocs]);

  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/upload/${deleteTarget}`);
      if (isAdmin) { fetchAllDocs(); fetchPendingDocs(); }
      else { fetchMyDocs(); }
    } catch { setErrorMsg("删除文档失败，请稍后重试"); }
    finally { setDeleteDialogOpen(false); setDeleteTarget(null); }
  }, [deleteTarget, isAdmin, fetchAllDocs, fetchPendingDocs, fetchMyDocs]);

  const handleApprove = useCallback(async () => {
    if (!approveTarget) return;
    try {
      await api.post(`/upload/${approveTarget.document_id}/approve`, { comment: approveComment });
      fetchPendingDocs(); fetchAllDocs();
    } catch { setErrorMsg("审批通过失败，请稍后重试"); }
    finally { setApproveDialogOpen(false); setApproveTarget(null); setApproveComment(""); }
  }, [approveTarget, approveComment, fetchPendingDocs, fetchAllDocs]);

  const handleReject = useCallback(async () => {
    if (!rejectTarget) return;
    try {
      await api.post(`/upload/${rejectTarget.document_id}/reject`, { comment: rejectComment });
      fetchPendingDocs(); fetchAllDocs();
    } catch { setErrorMsg("审批拒绝失败，请稍后重试"); }
    finally { setRejectDialogOpen(false); setRejectTarget(null); setRejectComment(""); }
  }, [rejectTarget, rejectComment, fetchPendingDocs, fetchAllDocs]);

  const handleDownload = useCallback(async (documentId: string, filename: string) => {
    if (downloadingIds.has(documentId)) return;
    try {
      setDownloadingIds(prev => new Set(prev).add(documentId));
      await downloadFile(documentId, filename);
    } catch { setErrorMsg("下载文档失败，请稍后重试"); }
    finally { setDownloadingIds(prev => { const next = new Set(prev); next.delete(documentId); return next; }); }
  }, [downloadingIds]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4 mb-2">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center" style={{ 
            background: isLight 
              ? `linear-gradient(135deg, ${colors.CYBER_BLUE} 0%, #1d4ed8 100%)` 
              : `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)`, 
            boxShadow: isLight ? `0 4px 20px ${colors.CYBER_BLUE}40` : `0 4px 20px ${colors.CYBER_CYAN}40` 
          }}>
            <BookOpen size={24} style={{ color: isLight ? '#ffffff' : '#000' }} />
          </div>
          <div>
            <GradientText as="h1" className="text-3xl font-bold" style={{ 
              background: isLight 
                ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_BLUE} 100%)` 
                : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_CYAN} 100%)`, 
              WebkitBackgroundClip: 'text', 
              WebkitTextFillColor: 'transparent' 
            }}>知识管理</GradientText>
            <p className="text-sm" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>上传和管理设备检修知识文档</p>
          </div>
        </div>
        <div className="h-64 animate-pulse rounded-xl" style={{ background: isLight ? '#f1f5f9' : 'rgba(15,15,30,0.8)' }} />
      </div>
    );
  }

  return (
    <div className={`space-y-6 transition-all duration-700 ${mounted ? 'opacity-100' : 'opacity-0'}`}>
      {/* Header */}
      <div className="flex items-center gap-4 mb-2">
        <div className="w-12 h-12 rounded-2xl flex items-center justify-center" style={{ 
          background: isLight 
            ? `linear-gradient(135deg, ${colors.CYBER_BLUE} 0%, #1d4ed8 100%)` 
            : `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)`, 
          boxShadow: isLight ? `0 4px 20px ${colors.CYBER_BLUE}40` : `0 4px 20px ${colors.CYBER_CYAN}40` 
        }}>
          <BookOpen size={24} style={{ color: isLight ? '#ffffff' : '#000' }} />
        </div>
        <div>
          <GradientText as="h1" className="text-3xl font-bold" style={{ 
            background: isLight 
              ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_BLUE} 100%)` 
              : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_CYAN} 100%)`, 
            WebkitBackgroundClip: 'text', 
            WebkitTextFillColor: 'transparent' 
          }}>知识管理</GradientText>
          <p className="text-sm" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>上传和管理设备检修知识文档</p>
        </div>
      </div>

      {/* Accent line */}
      <div className="w-full h-px" style={{ background: `linear-gradient(90deg, transparent 0%, ${isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN}50 50%, transparent 100%)` }} />

      {!isAdmin && (
        <>
          {/* Upload Section */}
          <div className="rounded-xl p-8" style={{ 
            background: isLight ? '#ffffff' : 'rgba(10,10,25,0.9)', 
            border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}`,
            boxShadow: isLight ? '0 4px 20px rgba(0, 0, 0, 0.06)' : undefined
          }}>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ 
                background: isLight 
                  ? `linear-gradient(135deg, ${colors.CYBER_BLUE} 0%, #1d4ed8 100%)` 
                  : `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)`, 
                boxShadow: isLight ? `0 4px 20px ${colors.CYBER_BLUE}30` : `0 4px 20px ${colors.CYBER_CYAN}30` 
              }}>
                <Upload size={22} style={{ color: '#ffffff' }} />
              </div>
              <div>
                <GradientText as="h2" className="text-xl font-bold flex items-center gap-2" style={{ 
                  background: isLight 
                    ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_BLUE} 100%)` 
                    : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_CYAN} 100%)`, 
                  WebkitBackgroundClip: 'text', 
                  WebkitTextFillColor: 'transparent' 
                }}>
                  <FileText size={20} style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }} /> 上传文档
                </GradientText>
                <p className="text-sm mt-0.5" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>将设备检修手册转换为可检索知识</p>
              </div>
            </div>
            <FileUploader category="通用" onUploadComplete={fetchMyDocs} />
          </div>

          {/* My Documents */}
          <div className="rounded-xl p-8" style={{ 
            background: isLight ? '#ffffff' : 'rgba(10,10,25,0.9)', 
            border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}`,
            boxShadow: isLight ? '0 4px 20px rgba(0, 0, 0, 0.06)' : undefined
          }}>
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ 
                  background: isLight ? `${colors.CYBER_BLUE}15` : `${colors.CYBER_CYAN}15` 
                }}>
                  <FileText size={20} style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }} />
                </div>
                <div>
                  <h3 className="text-lg font-bold" style={{ color: isLight ? '#1e293b' : '#e8e8f0' }}>我的文档列表</h3>
                  <p className="text-xs" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>共 {myDocs.length} 篇文档</p>
                </div>
              </div>
            </div>
            <DocTable documents={myDocs} onDelete={(id) => { setDeleteTarget(id); setDeleteDialogOpen(true); }} onDownload={handleDownload} downloadingIds={downloadingIds} />
          </div>
        </>
      )}

      {isAdmin && (
        <>
          {/* Pending Approval */}
          <div className="rounded-xl p-8" style={{ 
            background: isLight ? '#ffffff' : 'rgba(10,10,25,0.9)', 
            border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_YELLOW + '20'}` 
          }}>
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ 
                  background: isLight ? `${colors.CYBER_YELLOW}15` : `${colors.CYBER_YELLOW}15`, 
                  boxShadow: isLight ? `0 4px 20px ${colors.CYBER_YELLOW}20` : `0 4px 20px ${colors.CYBER_YELLOW}20` 
                }}>
                  <Clock size={22} style={{ color: colors.CYBER_YELLOW }} />
                </div>
                <div>
                  <GradientText as="h2" className="text-xl font-bold flex items-center gap-2" style={{ 
                    background: isLight 
                      ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_YELLOW} 100%)` 
                      : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_YELLOW} 100%)`,
                    WebkitBackgroundClip: 'text', 
                    WebkitTextFillColor: 'transparent'
                  }}>
                    待审批文档
                  </GradientText>
                  <p className="text-sm mt-0.5" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>需要审核后才能加入知识库</p>
                </div>
              </div>
              <Badge variant="outline" className="px-3 py-1.5 text-sm font-semibold" style={{ 
                background: isLight ? `${colors.CYBER_YELLOW}15` : `${colors.CYBER_YELLOW}15`, 
                color: colors.CYBER_YELLOW, 
                borderColor: `${colors.CYBER_YELLOW}30` 
              }}>
                {pendingDocs.length} 条待审批
              </Badge>
            </div>
            {pendingDocs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4" style={{ 
                  background: isLight ? `${colors.CYBER_BLUE}15` : `${colors.CYBER_CYAN}15` 
                }}>
                  <CheckCircle2 size={32} style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }} />
                </div>
                <p className="text-lg font-medium" style={{ color: isLight ? '#1e293b' : '#e8e8e8' }}>暂无待审批文档</p>
                <p className="text-sm mt-1" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>所有文档都已审核完成</p>
              </div>
            ) : (
              <div className="space-y-3">
                {pendingDocs.map((doc) => (
                  <div key={doc.document_id} className="flex items-center justify-between p-4 rounded-xl transition-all" style={{ 
                    background: isLight ? '#f8fafc' : 'rgba(21,21,40,0.6)', 
                    border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}` 
                  }}>
                    <div className="min-w-0 flex-1 flex items-center gap-4">
                      <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0" style={{ 
                        background: isLight ? `${colors.CYBER_BLUE}15` : `${colors.CYBER_CYAN}15` 
                      }}>
                        <FileText size={24} style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-semibold mb-1" style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}>{doc.filename}</p>
                        <div className="flex items-center gap-3 text-xs" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>
                          <span className="px-2 py-0.5 rounded-full" style={{ background: `${colors.CYBER_PURPLE}15`, color: colors.CYBER_PURPLE }}>{doc.file_type.toUpperCase()}</span>
                          <span>{doc.file_size_display}</span>
                          <span className="px-2 py-0.5 rounded-full" style={{ background: `${colors.CYBER_GREEN}15`, color: colors.CYBER_GREEN }}>{doc.category}</span>
                          <span>上传者: {doc.uploader_name}</span>
                          <span>{new Date(doc.created_at).toLocaleString("zh-CN")}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-4">
                      <Button size="sm" variant="outline" onClick={() => { window.open(`/api/v1/upload/${doc.document_id}/view`, '_blank'); }} className="h-9 px-3 rounded-lg font-medium" style={{ 
                        borderColor: isLight ? '#e2e8f0' : `${colors.CYBER_CYAN}30`,
                        color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN,
                        background: isLight ? '#ffffff' : 'transparent'
                      }}>
                        <Eye className="mr-1 h-4 w-4" /> 查看
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => handleDownload(doc.document_id, doc.filename)} disabled={downloadingIds.has(doc.document_id)} className="h-9 px-3 rounded-lg font-medium" style={{ 
                        borderColor: isLight ? '#e2e8f0' : `${colors.CYBER_CYAN}30`,
                        color: isLight ? '#475569' : '#a0a0c0',
                        background: isLight ? '#ffffff' : 'transparent'
                      }}>
                        {downloadingIds.has(doc.document_id) ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Download className="mr-1 h-4 w-4" />} 下载
                      </Button>
                      <Button size="sm" onClick={() => { setApproveTarget(doc); setApproveDialogOpen(true); }} className="h-9 px-4 rounded-lg font-medium" style={{ 
                        background: isLight ? `linear-gradient(135deg, ${colors.CYBER_GREEN} 0%, #059669 100%)` : `linear-gradient(135deg, ${colors.CYBER_GREEN} 0%, ${colors.CYBER_CYAN} 100%)`, 
                        color: '#ffffff' 
                      }}>
                        <Check className="mr-1 h-4 w-4" /> 通过
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => { setRejectTarget(doc); setRejectDialogOpen(true); }} className="h-9 px-4 rounded-lg" style={{ 
                        background: isLight ? '#ef4444' : colors.CYBER_RED 
                      }}>
                        <X className="mr-1 h-4 w-4" /> 拒绝
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* All Documents */}
          <div className="rounded-xl p-8" style={{ 
            background: isLight ? '#ffffff' : 'rgba(10,10,25,0.9)', 
            border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}`,
            boxShadow: isLight ? '0 4px 20px rgba(0, 0, 0, 0.06)' : undefined
          }}>
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ 
                  background: isLight ? `${colors.CYBER_BLUE}15` : `${colors.CYBER_CYAN}15` 
                }}>
                  <Sparkles size={20} style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }} />
                </div>
                <div>
                  <h3 className="text-lg font-bold" style={{ color: isLight ? '#1e293b' : '#e8e8f0' }}>所有文档</h3>
                  <p className="text-xs" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>系统中的全部知识文档</p>
                </div>
              </div>
            </div>
            <DocTable documents={allDocs} onDelete={(id) => { setDeleteTarget(id); setDeleteDialogOpen(true); }} onDownload={handleDownload} downloadingIds={downloadingIds} />
          </div>
        </>
      )}

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="rounded-2xl" style={{ 
              background: isLight ? '#ffffff' : 'rgba(15,15,30,0.95)', 
              border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_RED + '30'}` 
            }}>
          <div className="p-6">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-14 h-14 rounded-xl flex items-center justify-center" style={{ background: `${colors.CYBER_RED}15` }}>
                <Trash2 size={28} style={{ color: colors.CYBER_RED }} />
              </div>
              <div>
                <DialogTitle className="text-xl font-bold" style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}>确认删除</DialogTitle>
                <DialogDescription className="text-sm mt-1" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>此操作不可撤销</DialogDescription>
              </div>
            </div>
          </div>
          <div className="p-6 pt-0">
            <DialogFooter className="flex gap-3">
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)} className="flex-1 h-11 rounded-xl" style={{ borderColor: `${colors.CYBER_CYAN}30`, color: '#e8e8e8' }}>取消</Button>
              <Button variant="destructive" onClick={handleDelete} className="flex-1 h-11 rounded-xl" style={{ background: colors.CYBER_RED }}><Trash2 className="mr-2 h-4 w-4" /> 删除</Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>

      {/* Approve Dialog */}
      <Dialog open={approveDialogOpen} onOpenChange={setApproveDialogOpen}>
        <DialogContent className="rounded-2xl" style={{ 
              background: isLight ? '#ffffff' : 'rgba(15,15,30,0.95)', 
              border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_GREEN + '30'}` 
            }}>
          <div className="p-6">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-14 h-14 rounded-xl flex items-center justify-center" style={{ background: `${colors.CYBER_GREEN}15` }}>
                <Check size={28} style={{ color: colors.CYBER_GREEN }} />
              </div>
              <div>
                <DialogTitle className="text-xl font-bold" style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}>审批通过</DialogTitle>
                <DialogDescription className="text-sm mt-1" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>确认通过文档「{approveTarget?.filename}」的审批？</DialogDescription>
              </div>
            </div>
          </div>
          <div className="p-6 pt-0 space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium" style={{ color: isLight ? '#475569' : '#c0c0d0' }}>审批意见（可选）</label>
              <Input placeholder="请输入审批意见" value={approveComment} onChange={(e) => setApproveComment(e.target.value)} className="h-11 rounded-xl" style={{ 
                background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                color: isLight ? '#1e293b' : '#f0f0f0' 
              }} />
            </div>
            <DialogFooter className="flex gap-3">
              <Button variant="outline" onClick={() => setApproveDialogOpen(false)} className="flex-1 h-11 rounded-xl" style={{ 
                borderColor: isLight ? '#e2e8f0' : `${colors.CYBER_CYAN}30`, 
                color: isLight ? '#475569' : '#e8e8e8',
                background: isLight ? '#ffffff' : 'transparent'
              }}>取消</Button>
              <Button onClick={handleApprove} className="flex-1 h-11 rounded-xl font-medium" style={{ 
                background: isLight ? colors.CYBER_GREEN : `linear-gradient(135deg, ${colors.CYBER_GREEN} 0%, ${colors.CYBER_CYAN} 100%)`, 
                color: isLight ? '#ffffff' : '#000' 
              }}><Check className="mr-2 h-4 w-4" /> 确认通过</Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <DialogContent className="rounded-2xl" style={{ 
              background: isLight ? '#ffffff' : 'rgba(15,15,30,0.95)', 
              border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_YELLOW + '30'}` 
            }}>
          <div className="p-6">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-14 h-14 rounded-xl flex items-center justify-center" style={{ background: `${colors.CYBER_YELLOW}15` }}>
                <X size={28} style={{ color: colors.CYBER_YELLOW }} />
              </div>
              <div>
                <DialogTitle className="text-xl font-bold" style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}>拒绝审批</DialogTitle>
                <DialogDescription className="text-sm mt-1" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>拒绝文档「{rejectTarget?.filename}」的审批</DialogDescription>
              </div>
            </div>
          </div>
          <div className="p-6 pt-0 space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium" style={{ color: isLight ? '#475569' : '#c0c0d0' }}>拒绝原因</label>
              <Input placeholder="请输入拒绝原因" value={rejectComment} onChange={(e) => setRejectComment(e.target.value)} className="h-11 rounded-xl" style={{ 
                background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                color: isLight ? '#1e293b' : '#f0f0f0' 
              }} />
            </div>
            <DialogFooter className="flex gap-3">
              <Button variant="outline" onClick={() => setRejectDialogOpen(false)} className="flex-1 h-11 rounded-xl" style={{ 
                borderColor: isLight ? '#e2e8f0' : `${colors.CYBER_CYAN}30`, 
                color: isLight ? '#475569' : '#e8e8e8',
                background: isLight ? '#ffffff' : 'transparent'
              }}>取消</Button>
              <Button variant="destructive" onClick={handleReject} className="flex-1 h-11 rounded-xl" style={{ background: colors.CYBER_RED }}><X className="mr-2 h-4 w-4" /> 确认拒绝</Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}