import { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { X, ChevronRight, ChevronLeft, CheckCircle2 } from 'lucide-react'
import { useTheme } from '@/hooks/useTheme'

interface Step {
  title: string
  description: string
  element?: string
}

const tourSteps: Step[] = [
  {
    title: '👋 欢迎使用设备检修知识系统',
    description: '这是一个基于多模态大模型的智能设备检修助手。让我带你快速了解主要功能！',
  },
  {
    title: '🔍 知识检索',
    description: '在搜索页面，你可以通过文本或图片快速查找检修知识，支持语义理解。',
  },
  {
    title: '🤖 AI问答助手',
    description: '遇到问题时，AI助手可以提供智能解答，支持多轮对话和图片输入。',
  },
  {
    title: '📋 作业指引',
    description: '系统可以自动生成标准化的检修作业指导书，提升工作效率。',
  },
  {
    title: '📚 知识管理',
    description: '上传文档和案例，通过审核后将纳入知识库，供后续使用。',
  },
  {
    title: '⌨️ 快捷键',
    description: '使用快捷键提升效率：Ctrl+K 快速搜索，Ctrl+1~9 快速导航，Ctrl+H 查看帮助。',
  },
]

interface OnboardingTourProps {
  forceOpen?: boolean
  onClose?: () => void
}

export function OnboardingTour({ forceOpen, onClose }: OnboardingTourProps = {}) {
  const [isOpen, setIsOpen] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [hasSeen, setHasSeen] = useState(false)
  const highlightRef = useRef<HTMLDivElement>(null)
  const { theme } = useTheme()
  const isLight = theme === 'light'

  useEffect(() => {
    if (forceOpen) {
      setIsOpen(true)
      return
    }

    const seen = localStorage.getItem('onboarding_seen')
    if (!seen) {
      setTimeout(() => {
        setIsOpen(true)
      }, 1500)
    } else {
      setHasSeen(true)
    }
  }, [forceOpen])

  const handleComplete = () => {
    localStorage.setItem('onboarding_seen', 'true')
    setIsOpen(false)
    setHasSeen(true)
    if (onClose) onClose()
  }

  const handleClose = () => {
    setIsOpen(false)
    if (onClose) onClose()
  }

  const nextStep = () => {
    if (currentStep < tourSteps.length - 1) {
      setCurrentStep(currentStep + 1)
    } else {
      handleComplete()
    }
  }

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  if (!forceOpen && hasSeen) return null

  return (
    <>
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="sm:max-w-[500px]"
          style={{
            background: isLight ? '#ffffff' : '#0d0d1a',
            border: isLight ? '1px solid #e2e8f0' : '1px solid rgba(59,130,246,0.3)'
          }}
        >
          <button
            onClick={handleClose}
            className="absolute right-4 top-4 transition-colors"
            style={{ color: isLight ? '#475569' : '#606080' }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = isLight ? '#1e293b' : '#e8e8f0' }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = isLight ? '#475569' : '#606080' }}
          >
            <X className="w-4 h-4" />
          </button>

          <DialogHeader>
            <DialogTitle className="flex items-center gap-2" style={{ color: isLight ? '#1e293b' : '#ffffff' }}>
              {tourSteps[currentStep].title}
            </DialogTitle>
            <DialogDescription style={{ color: isLight ? '#475569' : '#a0a0c0' }}>
              {tourSteps[currentStep].description}
            </DialogDescription>
          </DialogHeader>

          <div className="flex items-center justify-center gap-2 mt-6">
            {tourSteps.map((_, index) => (
              <div
                key={index}
                className="h-1.5 rounded-full transition-all duration-300"
                style={{
                  width: index === currentStep ? '2rem' : (index < currentStep ? '0.75rem' : '0.75rem'),
                  background: index <= currentStep
                    ? (isLight ? '#2563eb' : '#3b82f6')
                    : (isLight ? 'rgba(59,130,246,0.3)' : 'rgba(59,130,246,0.3)')
                }}
              />
            ))}
          </div>

          <DialogFooter className="flex justify-between mt-8">
            <Button
              variant="ghost"
              onClick={prevStep}
              disabled={currentStep === 0}
              className="transition-colors"
              style={{ color: isLight ? '#64748b' : '#8080a0' }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = isLight ? '#1e293b' : '#ffffff' }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = isLight ? '#64748b' : '#8080a0' }}
            >
              <ChevronLeft className="w-4 h-4 mr-2" />
              上一步
            </Button>
            <Button onClick={nextStep}
              style={{
                background: isLight ? 'linear-gradient(135deg, #2563eb 0%, #0891b2 100%)' : 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                color: '#ffffff'
              }}
            >
              {currentStep === tourSteps.length - 1 ? (
                <><CheckCircle2 className="w-4 h-4 mr-2" /> 完成</>
              ) : (
                <>下一步 <ChevronRight className="w-4 h-4 ml-2" /></>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

export function TourTrigger() {
  const [isOpen, setIsOpen] = useState(false)
  const { theme } = useTheme()
  const isLight = theme === 'light'

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsOpen(true)}
        className="transition-colors"
        style={{ color: isLight ? '#64748b' : '#8080a0' }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = isLight ? '#2563eb' : '#ffffff' }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = isLight ? '#64748b' : '#8080a0' }}
      >
        <CheckCircle2 className="w-4 h-4 mr-2" />
        功能引导
      </Button>
      <OnboardingTour forceOpen={isOpen} onClose={() => setIsOpen(false)} />
    </>
  )
}
