import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth-store'
import { api } from '@/lib/api'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FileText, Search, Users, MessageSquare } from 'lucide-react'

interface AdminStats {
  documents: number
  searches: number
  users: number
  today_chats: number
}

interface UserStats {
  documents: number
  searches: number
  today_chats: number
}

interface StatCard {
  title: string
  value: number
  icon: React.ReactNode
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()
  const [stats, setStats] = useState<StatCard[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchStats() {
      try {
        if (user?.role === 'admin') {
          const res = await api.get('/admin/stats')
          const d = res.data
          setStats([
            { title: '知识库文档', value: d.document_count || 0, icon: <FileText className="h-5 w-5 text-blue-500" /> },
            { title: '问答次数', value: d.chat_count || 0, icon: <Search className="h-5 w-5 text-green-500" /> },
            { title: '用户数量', value: d.user_count || 0, icon: <Users className="h-5 w-5 text-purple-500" /> },
            { title: '知识分块', value: d.total_chunks || 0, icon: <MessageSquare className="h-5 w-5 text-orange-500" /> },
          ])
        } else {
          try {
            const res = await api.get('/upload/my/stats')
            const d = res.data
            setStats([
              { title: '知识库文档', value: d.total || 0, icon: <FileText className="h-5 w-5 text-blue-500" /> },
              { title: '已完成', value: d.completed || 0, icon: <Search className="h-5 w-5 text-green-500" /> },
              { title: '待审批', value: d.pending || 0, icon: <MessageSquare className="h-5 w-5 text-orange-500" /> },
            ])
          } catch {
            setStats([
              { title: '知识库文档', value: 0, icon: <FileText className="h-5 w-5 text-blue-500" /> },
              { title: '已完成', value: 0, icon: <Search className="h-5 w-5 text-green-500" /> },
              { title: '待审批', value: 0, icon: <MessageSquare className="h-5 w-5 text-orange-500" /> },
            ])
          }
        }
      } catch {
        setStats([
          { title: '知识库文档', value: 0, icon: <FileText className="h-5 w-5 text-blue-500" /> },
          { title: '问答次数', value: 0, icon: <Search className="h-5 w-5 text-green-500" /> },
          { title: '用户数量', value: 0, icon: <Users className="h-5 w-5 text-purple-500" /> },
          { title: '知识分块', value: 0, icon: <MessageSquare className="h-5 w-5 text-orange-500" /> },
        ])
      } finally {
        setLoading(false)
      }
    }

    if (user) {
      fetchStats()
    } else {
      setLoading(false)
    }
  }, [user?.role, user])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">欢迎回来，{user?.username || '用户'}</h1>
        <p className="text-muted-foreground mt-1">以下是系统运行概况</p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
              <Card key={i}>
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">加载中...</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-8 w-20 animate-pulse rounded bg-muted" />
                </CardContent>
              </Card>
            ))
          : stats.map((stat) => (
              <Card key={stat.title}>
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">{stat.title}</CardTitle>
                  {stat.icon}
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{stat.value.toLocaleString()}</div>
                </CardContent>
              </Card>
            ))}
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-3">快捷操作</h2>
        <div className="flex flex-wrap gap-3">
          <Button variant="outline" onClick={() => navigate('/search')}>
            <Search className="mr-2 h-4 w-4" />
            知识检索
          </Button>
          <Button variant="outline" onClick={() => navigate('/knowledge')}>
            <FileText className="mr-2 h-4 w-4" />
            上传文档
          </Button>
          <Button variant="outline" onClick={() => navigate('/kb')}>
            <FileText className="mr-2 h-4 w-4" />
            查看知识库
          </Button>
        </div>
      </div>
    </div>
  )
}
