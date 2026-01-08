import { useState, useCallback, useRef, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useWorkflowWebSocket } from '../hooks/useWebSocket'
import WorkflowProgress from '../components/WorkflowProgress'
import type { VideoSegment } from '../types/segment'
import './Idea2Video.css'

interface Character {
  id: string
  name: string
  role: string
  description: string
  appearance: string
  image_url: string
}

interface Scene {
  id: string
  name: string
  description: string
  atmosphere: string
  image_url: string
}

interface Shot {
  id: string
  shot_number: number
  description: string
  camera_angle: string
  camera_movement?: string
  visual_desc?: string
  image_url: string
  video_url?: string
  status?: string
}

interface Outline {
  title: string
  genre: string
  style: string
  synopsis: string
  characters_summary: Array<{ name: string, role: string, description?: string }>
  plot_summary: Array<{ act?: string, scene?: string, description: string }>
  highlights: string[]
}

interface ChatMessage {
  id: string
  role: 'assistant' | 'user' | 'system'
  content: string
  timestamp: Date
}

interface WorkflowState {
  step: 'input' | 'outline' | 'characters' | 'scenes' | 'storyboard' | 'video' | 'segments' | 'completed'
  status: 'idle' | 'generating' | 'ready' | 'error'
  episodeId: string | null
  outline: Outline | null
  characters: Character[]
  scenes: Scene[]
  storyboard: Shot[]
  videoUrl: string | null
  segments: VideoSegment[]
  error: string | null
  progress: number
  progressMessage: string
  context?: Record<string, any>
}

interface WorkflowStep {
  id: string
  label: string
  sublabel?: string
  completed: boolean
  active: boolean
}

function Idea2Video() {
  const [searchParams] = useSearchParams()
  const [idea, setIdea] = useState('')
  const [style, setStyle] = useState('cinematic')
  const [isRestoringDraft, setIsRestoringDraft] = useState(false)
  const [showModelSettings, setShowModelSettings] = useState(false)
  const [videoModel, setVideoModel] = useState('veo3-fast')
  const [imageModel, setImageModel] = useState('doubao-seedream-4-0-250828')
  const [videoModels, setVideoModels] = useState<Array<{ name: string, description: string }>>([])
  const [imageModels, setImageModels] = useState<Array<{ name: string, description: string }>>([])
  const [llmModel, setLlmModel] = useState('gemini-2.0-flash-exp')
  const [llmModels, setLlmModels] = useState<Array<{ id: string, name: string, provider: string, description: string }>>([])
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      role: 'assistant',
      content: '你好！我是Seko，很高兴能为您策划这部充满史诗感的短片。请告诉我您想要创作的视频主题或想法。',
      timestamp: new Date()
    }
  ])

  const [workflow, setWorkflow] = useState<WorkflowState>({
    step: 'input',
    status: 'idle',
    episodeId: null,
    outline: null,
    characters: [],
    scenes: [],
    storyboard: [],
    videoUrl: null,
    segments: [],
    error: null,
    progress: 0,
    progressMessage: ''
  })

  const [selectedShot, setSelectedShot] = useState<number>(0)
  const [selectedSegment, setSelectedSegment] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'video' | 'audio' | 'music'>('video')
  const [showWebSocketProgress, setShowWebSocketProgress] = useState(false)
  const [showSegmentWorkflow, setShowSegmentWorkflow] = useState(false)
  const [draggedShotIndex, setDraggedShotIndex] = useState<number | null>(null)
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  // Shot editing state (for storyboard view)
  const [editingShot, setEditingShot] = useState<number | null>(null)
  const [editedDescription, setEditedDescription] = useState('')
  const [editedCameraAngle, setEditedCameraAngle] = useState('')
  const [editedCameraMovement, setEditedCameraMovement] = useState('')

  // Shot editing functions (shared between storyboard and video steps)
  const handleEditShot = (index: number) => {
    const shot = workflow.storyboard[index]
    setEditingShot(index)
    setEditedDescription(shot.visual_desc || shot.description)
    setEditedCameraAngle(shot.camera_angle)
    setEditedCameraMovement(shot.camera_movement || '')
  }

  const handleSaveShot = async () => {
    if (editingShot === null) return
    
    const shot = workflow.storyboard[editingShot]
    const isNewShot = shot.id.startsWith('shot-')
    
    if (!workflow.episodeId) {
      addMessage('system', '无法保存：没有episode ID')
      return
    }
    
    try {
      if (isNewShot) {
        // For new shots, we need to create them in the database first
        // Get the first scene from the episode
        const stateResponse = await fetch(`/api/v1/conversational/episode/${workflow.episodeId}/state`)
        if (!stateResponse.ok) {
          throw new Error('Failed to get episode state')
        }
        
        const stateData = await stateResponse.json()
        const scenes = stateData.scenes || []
        
        if (scenes.length === 0) {
          addMessage('system', '无法保存新分镜：请先生成场景')
          return
        }
        
        // Use the first scene's ID
        const sceneId = scenes[0].id
        
        // Create the shot in database
        const createResponse = await fetch(
          `/api/v1/conversational/episode/${workflow.episodeId}/shots`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              scene_id: sceneId,
              shot_number: shot.shot_number,
              visual_desc: editedDescription,
              camera_angle: editedCameraAngle,
              camera_movement: editedCameraMovement || 'STATIC'
            })
          }
        )
        
        if (!createResponse.ok) {
          const errorText = await createResponse.text()
          console.error('Create shot error:', errorText)
          throw new Error(`Failed to create shot: ${createResponse.status} ${errorText}`)
        }
        
        const createData = await createResponse.json()
        console.log('Shot created:', createData)
        
        // Update local state with the database shot
        const updatedStoryboard = [...workflow.storyboard]
        updatedStoryboard[editingShot] = {
          ...createData.shot,
          description: createData.shot.visual_desc
        }
        
        setWorkflow(prev => ({ ...prev, storyboard: updatedStoryboard }))
        setEditingShot(null)
        addMessage('assistant', `分镜${editingShot + 1}已创建并保存到数据库`)
        
      } else {
        // Update existing shot in database
        const updateResponse = await fetch(
          `/api/v1/conversational/episode/${workflow.episodeId}/shots/${shot.id}`,
          {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              visual_desc: editedDescription,
              camera_angle: editedCameraAngle,
              camera_movement: editedCameraMovement
            })
          }
        )
        
        if (!updateResponse.ok) {
          const errorText = await updateResponse.text()
          console.error('Update shot error:', errorText)
          throw new Error(`Failed to update shot: ${updateResponse.status}`)
        }
        
        const updateData = await updateResponse.json()
        console.log('Shot updated:', updateData)
        
        // Update local state
        const updatedStoryboard = [...workflow.storyboard]
        updatedStoryboard[editingShot] = {
          ...updateData.shot,
          description: updateData.shot.visual_desc
        }
        
        setWorkflow(prev => ({ ...prev, storyboard: updatedStoryboard }))
        setEditingShot(null)
        addMessage('assistant', `分镜${editingShot + 1}已更新并保存到数据库`)
      }
      
    } catch (error) {
      console.error('Error saving shot:', error)
      setEditingShot(null)
      addMessage('system', `保存分镜失败: ${error instanceof Error ? error.message : '请重试'}`)
    }
  }

  const handleDeleteShot = async (index: number) => {
    if (!confirm(`确定要删除分镜${index + 1}吗？`)) return

    const shotToDelete = workflow.storyboard[index]

    // Check if this is a database shot (UUID format) or a client-generated shot (shot-timestamp format)
    const isDbShot = shotToDelete.id && !shotToDelete.id.startsWith('shot-')

    // If shot exists in database, delete from database
    if (isDbShot && workflow.episodeId) {
      try {
        const response = await fetch(
          `/api/v1/conversational/episode/${workflow.episodeId}/shots/${shotToDelete.id}`,
          { method: 'DELETE' }
        )

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          throw new Error(errorData.detail || 'Failed to delete shot from database')
        }

        addMessage('assistant', `分镜${index + 1}已从数据库删除`)
      } catch (error) {
        console.error('Error deleting shot:', error)
        addMessage('system', `删除分镜失败: ${error instanceof Error ? error.message : '请重试'}`)
        return
      }
    } else {
      // Client-side only shot, just remove from local state
      addMessage('assistant', `分镜${index + 1}已删除`)
    }

    // Update local state
    const updatedStoryboard = workflow.storyboard.filter((_, i) => i !== index)
    setWorkflow(prev => ({ ...prev, storyboard: updatedStoryboard }))

    if (selectedShot >= updatedStoryboard.length) {
      setSelectedShot(Math.max(0, updatedStoryboard.length - 1))
    }
  }

  const handleAddShot = () => {
    const newShot: Shot = {
      id: `shot-${Date.now()}`,
      shot_number: workflow.storyboard.length + 1,
      description: '新分镜描述',
      camera_angle: 'MEDIUM SHOT',
      camera_movement: 'STATIC',
      visual_desc: '新分镜描述',
      image_url: ''
    }

    const updatedStoryboard = [...workflow.storyboard, newShot]
    setWorkflow(prev => ({ ...prev, storyboard: updatedStoryboard }))
    setSelectedShot(updatedStoryboard.length - 1)
    addMessage('assistant', '已添加新分镜')
  }

  const handleDuplicateShot = (index: number) => {
    const shotToDuplicate = workflow.storyboard[index]
    const newShot: Shot = {
      ...shotToDuplicate,
      id: `shot-${Date.now()}`,
      shot_number: workflow.storyboard.length + 1
    }

    const updatedStoryboard = [...workflow.storyboard]
    updatedStoryboard.splice(index + 1, 0, newShot)
    setWorkflow(prev => ({ ...prev, storyboard: updatedStoryboard }))
    setSelectedShot(index + 1)
    addMessage('assistant', `已复制分镜${index + 1}`)
  }

  // Drag and drop handlers for shot reordering
  const handleDragStart = (e: React.DragEvent, index: number) => {
    setDraggedShotIndex(index)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOverIndex(index)
  }

  const handleDragLeave = () => {
    setDragOverIndex(null)
  }

  const handleDrop = (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault()

    if (draggedShotIndex === null || draggedShotIndex === targetIndex) {
      setDraggedShotIndex(null)
      setDragOverIndex(null)
      return
    }

    const updatedStoryboard = [...workflow.storyboard]
    const [draggedShot] = updatedStoryboard.splice(draggedShotIndex, 1)
    updatedStoryboard.splice(targetIndex, 0, draggedShot)

    // Update shot numbers
    updatedStoryboard.forEach((shot, idx) => {
      shot.shot_number = idx + 1
    })

    setWorkflow(prev => ({ ...prev, storyboard: updatedStoryboard }))
    setSelectedShot(targetIndex)
    setDraggedShotIndex(null)
    setDragOverIndex(null)
    addMessage('assistant', `已将分镜${draggedShotIndex + 1}移动到位置${targetIndex + 1}`)
  }

  const handleDragEnd = () => {
    setDraggedShotIndex(null)
    setDragOverIndex(null)
  }

  // WebSocket connection for real-time progress updates
  const { isConnected: wsConnected } = useWorkflowWebSocket(
    workflow.episodeId || 'pending',
    (message) => {
      if (message.type === 'progress' && message.workflow_id === workflow.episodeId) {
        // Update workflow state from WebSocket message
        setWorkflow(prev => ({
          ...prev,
          progress: message.progress || prev.progress,
          progressMessage: message.message || prev.progressMessage,
          status: message.state === 'running' ? 'generating' :
            message.state === 'completed' ? 'ready' :
              message.state === 'failed' ? 'error' : prev.status
        }))

        // Update step based on stage
        if (message.stage) {
          const stageToStep: Record<string, typeof workflow.step> = {
            'outline': 'outline',
            'characters': 'characters',
            'scenes': 'scenes',
            'storyboard': 'storyboard',
            'video': 'video'
          }
          const newStep = stageToStep[message.stage]
          if (newStep) {
            setWorkflow(prev => ({ ...prev, step: newStep }))
          }
        }

        // Add progress message to chat
        if (message.message && message.progress > 0) {
          addMessage('system', `进度更新: ${message.message} (${Math.round(message.progress * 100)}%)`)
        }
      }
    }
  )

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const episodeId = searchParams.get('episode')
    if (episodeId && !workflow.episodeId) {
      restoreDraftState(episodeId)
    }
  }, [searchParams])

  useEffect(() => {
    // Load available models
    fetch('/api/v1/models/available')
      .then(res => res.json())
      .then(data => {
        setVideoModels(data.video || [])
        setImageModels(data.image || [])
      })
      .catch(err => console.error('Failed to load models:', err))

    // Load LLM models
    fetch('/api/v1/chat/models')
      .then(res => res.json())
      .then(data => {
        if (data.models) {
          setLlmModels(data.models)
        }
      })
      .catch(err => console.error('Failed to load LLM models:', err))

    // Load user preferences
    const savedPrefs = localStorage.getItem('model_preferences')
    if (savedPrefs) {
      const prefs = JSON.parse(savedPrefs)
      setVideoModel(prefs.video_model || 'veo3-fast')
      setImageModel(prefs.image_model || 'doubao-seedream-4-0-250828')
    }

    // Load LLM model preference
    const savedLLM = localStorage.getItem('selectedLLMModel')
    if (savedLLM) {
      setLlmModel(savedLLM)
    }
  }, [])

  const restoreDraftState = async (episodeId: string) => {
    setIsRestoringDraft(true)
    try {
      const response = await fetch(`/api/v1/conversational/episode/${episodeId}/state`)
      if (!response.ok) {
        console.error('Failed to restore draft state')
        setIsRestoringDraft(false)
        return
      }

      const data = await response.json()
      const backendState = (data.state as string).toLowerCase()

      const step = determineStepFromState(backendState)
      const isGenerating = backendState.includes('generating') || backendState.includes('refining')

      setWorkflow(prev => ({
        ...prev,
        step: step,
        status: isGenerating ? 'generating' : 'ready',
        episodeId: episodeId,
        outline: data.outline || null,
        characters: data.characters || [],
        scenes: data.scenes || [],
        storyboard: data.storyboard || [],
        videoUrl: data.video_path || null,
        error: data.error || null
      }))

      setMessages([
        {
          id: '1',
          role: 'assistant',
          content: '欢迎回来！我已经恢复了您之前的项目进度。',
          timestamp: new Date()
        }
      ])

      if (data.outline) {
        setMessages(prev => [...prev, {
          id: `restored-outline-${Date.now()}`,
          role: 'assistant',
          content: `当前项目标题: "${data.outline.title}"，进度已恢复到"${getStepLabel(step)}"阶段。`,
          timestamp: new Date()
        }])
      }

      if (isGenerating) {
        pollStatus(episodeId, step)
      }

    } catch (error) {
      console.error('Error restoring draft:', error)
    } finally {
      setIsRestoringDraft(false)
    }
  }

  const getStepLabel = (step: string): string => {
    const labels: Record<string, string> = {
      'input': '输入创意',
      'outline': '故事大纲',
      'characters': '角色设计',
      'scenes': '场景设计',
      'storyboard': '分镜设计',
      'video': '视频生成',
      'completed': '已完成'
    }
    return labels[step] || step
  }

  const workflowSteps: WorkflowStep[] = [
    { id: 'outline', label: '根据本集内容，生成详细的故事大纲', completed: workflow.step !== 'input' && workflow.step !== 'outline', active: workflow.step === 'outline' },
    { id: 'style', label: '定义写实电影感的视觉风格和美术元素', completed: workflow.step !== 'input' && workflow.step !== 'outline', active: false },
    { id: 'characters', label: '细化本集出场角色的造型和特点', sublabel: '设计角色特征', completed: ['scenes', 'storyboard', 'video', 'completed'].includes(workflow.step), active: workflow.step === 'characters' },
    { id: 'character_gen', sublabel: '调用工具生成角色图', completed: ['scenes', 'storyboard', 'video', 'completed'].includes(workflow.step), active: workflow.step === 'characters', label: '' },
    { id: 'scenes', label: '设计本集所需的关键场景细节', completed: ['storyboard', 'video', 'completed'].includes(workflow.step), active: workflow.step === 'scenes' },
    { id: 'scene_gen', sublabel: '调用工具生成场景图', completed: ['storyboard', 'video', 'completed'].includes(workflow.step), active: workflow.step === 'scenes', label: '' },
    { id: 'storyboard', label: '绘制本集详细的分镜剧本', completed: ['video', 'completed'].includes(workflow.step), active: workflow.step === 'storyboard' },
  ]

  const determineStepFromState = (backendState: string): 'outline' | 'characters' | 'scenes' | 'storyboard' | 'video' | 'segments' | 'completed' => {
    if (backendState === 'video_completed') return 'completed'
    if (backendState.includes('segment')) return 'segments'
    if (backendState.includes('video')) return 'video'
    if (backendState.includes('storyboard')) return 'storyboard'
    if (backendState.includes('scene')) return 'scenes'
    if (backendState.includes('character')) return 'characters'
    return 'outline'
  }

  const isStepComplete = (backendState: string, targetStep: string): boolean => {
    const completedStates: Record<string, string[]> = {
      'outline': ['outline_generated', 'outline_confirmed', 'refining_completed', 'refined'],
      'characters': ['characters_generated', 'characters_confirmed'],
      'scenes': ['scenes_generated', 'scenes_confirmed'],
      'storyboard': ['storyboard_generated', 'storyboard_confirmed'],
      'video': ['video_completed']
    }
    return completedStates[targetStep]?.includes(backendState) || false
  }

  const addMessage = useCallback((role: 'assistant' | 'user' | 'system', content: string) => {
    setMessages(prev => [...prev, {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      role,
      content,
      timestamp: new Date()
    }])
  }, [])

  const pollStatus = useCallback(async (episodeId: string, expectedStep: string, pollCount: number = 0) => {
    const addMsg = (role: 'assistant' | 'user' | 'system', content: string) => {
      setMessages(prev => [...prev, {
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        role,
        content,
        timestamp: new Date()
      }])
    }

    try {
      const response = await fetch(`/api/v1/conversational/episode/${episodeId}/state`)
      if (!response.ok) {
        setTimeout(() => pollStatus(episodeId, expectedStep, pollCount + 1), 3000)
        return
      }

      const data = await response.json()
      const backendState = (data.state as string).toLowerCase()

      if (backendState === 'failed') {
        setWorkflow(prev => ({
          ...prev,
          status: 'error',
          error: data.error || 'Generation failed'
        }))
        addMsg('system', `生成失败: ${data.error || '未知错误'}`)
        return
      }

      if (backendState.includes('generating') || backendState.includes('refining')) {
        setTimeout(() => pollStatus(episodeId, expectedStep, 0), 2000)
        return
      }

      if (isStepComplete(backendState, expectedStep)) {
        const newStep = determineStepFromState(backendState)
        const videoUrl = data.video_path || data.step_info?.video?.path || null

        setWorkflow(prev => ({
          ...prev,
          step: newStep === 'completed' ? 'completed' : expectedStep as typeof prev.step,
          status: 'ready',
          outline: data.outline || prev.outline,
          characters: data.characters?.length > 0 ? data.characters : prev.characters,
          scenes: data.scenes?.length > 0 ? data.scenes : prev.scenes,
          storyboard: data.storyboard?.length > 0 ? data.storyboard : prev.storyboard,
          videoUrl: videoUrl || prev.videoUrl
        }))

        const stepMessages: Record<string, string> = {
          'outline': '剧本大纲已生成完成，请在右侧查看并确认',
          'characters': '角色设计已完成，请在右侧查看角色卡片',
          'scenes': '场景设计已完成，请在右侧查看场景列表',
          'storyboard': '分镜剧本已完成，请在右侧查看分镜表',
          'video': '视频生成完成！'
        }
        if (stepMessages[expectedStep]) {
          addMsg('assistant', stepMessages[expectedStep])
        }
        return
      }

      // If we've polled many times without progress and not in generating state,
      // detect as stale and allow user to retry
      if (pollCount > 15) {
        const currentStep = determineStepFromState(backendState)

        // Update to current state and stop generating status
        setWorkflow(prev => ({
          ...prev,
          step: currentStep,
          status: 'ready',
          outline: data.outline || prev.outline,
          characters: data.characters?.length > 0 ? data.characters : prev.characters,
          scenes: data.scenes?.length > 0 ? data.scenes : prev.scenes,
          storyboard: data.storyboard?.length > 0 ? data.storyboard : prev.storyboard
        }))
        addMsg('system', `生成似乎已停止。当前阶段: ${getStepLabel(currentStep)}。请点击"继续生成"重试。`)
        return
      }

      setTimeout(() => pollStatus(episodeId, expectedStep, pollCount + 1), 2000)

    } catch (error) {
      console.error('Poll error:', error)
      setTimeout(() => pollStatus(episodeId, expectedStep, pollCount + 1), 3000)
    }
  }, [])

  // 快速意图检测（第一层：规则匹配）
  const quickIntentCheck = (message: string): 'chat' | 'video_generation' | 'uncertain' => {
    const msg = message.toLowerCase().trim()

    // 明确的对话意图
    if (/^(hi|hello|你好|嗨|您好|hey)$/i.test(msg)) return 'chat'
    if (/^(help|帮助|功能|what can you do|你能做什么)$/i.test(msg)) return 'chat'
    if (/^(how|why|what|when|where|怎么|为什么|什么|如何)/.test(msg) && msg.length < 30) return 'chat'

    // 明确的视频生成意图
    if (/(创建|生成|制作|做一个|拍摄|录制).*(视频|短片|影片|电影)/.test(msg)) return 'video_generation'
    if (/(make|create|generate|produce).*(video|film|movie|short)/.test(msg)) return 'video_generation'
    if (/^(拍|录|做).*(视频|短片)/.test(msg)) return 'video_generation'

    // 不确定，需要LLM判断
    return 'uncertain'
  }

  // LLM意图分类（第二层：AI判断）
  const classifyIntentWithLLM = async (message: string): Promise<{ intent: string, confidence: number, reasoning: string }> => {
    try {
      const response = await fetch('/api/v1/chat/classify-intent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: message,
          model: llmModel
        })
      })

      if (!response.ok) {
        // Check for API key error (503)
        if (response.status === 503) {
          const errorData = await response.json().catch(() => ({}))
          if (errorData.detail && errorData.detail.error === 'api_key_required') {
            // Display API key configuration message
            addMessage('system',
              `⚠️ ${errorData.detail.message}\n\n` +
              `系统需要LLM API密钥才能智能分析您的输入。\n\n` +
              `请设置环境变量：\n` +
              `export YUNWU_API_KEY="your-api-key-here"\n\n` +
              `或在配置文件中设置：\n` +
              `configs/idea2video.yaml\n\n` +
              `配置后，系统将能够：\n` +
              `✓ 智能理解您的视频创意\n` +
              `✓ 自动判断何时开始生成\n` +
              `✓ 提供更准确的内容建议\n\n` +
              `支持的API提供商：\n` +
              `• 云雾AI (yunwu.ai) - 推荐\n` +
              `• Google Gemini\n` +
              `• OpenAI GPT\n` +
              `• Anthropic Claude`
            )
            throw new Error('API key required')
          }
        }
        throw new Error('Intent classification failed')
      }

      const data = await response.json()
      return {
        intent: data.intent,
        confidence: data.confidence,
        reasoning: data.reasoning
      }
    } catch (error) {
      console.error('LLM intent classification error:', error)
      // 如果是API key错误，不要继续处理
      if (error instanceof Error && error.message === 'API key required') {
        throw error
      }
      // 其他错误：默认为对话模式（更安全）
      return {
        intent: 'chat',
        confidence: 0.5,
        reasoning: '分类失败，默认为对话模式'
      }
    }
  }

  // 处理对话消息
  const handleChatMessage = async (message: string) => {
    try {
      // 显示"正在思考"指示器
      const thinkingMsgId = `thinking-${Date.now()}`
      setMessages(prev => [...prev, {
        id: thinkingMsgId,
        role: 'assistant',
        content: '正在思考...',
        timestamp: new Date()
      }])

      // 创建或获取对话线程
      let threadId = workflow.context?.chat_thread_id
      if (!threadId) {
        const threadResponse = await fetch('/api/v1/chat/threads', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: 'default_user',
            llm_model: llmModel.split(' (')[0], // Remove provider suffix if present
            title: '视频助手对话',
            system_prompt: `你是Seko，一个专业的视频生成助手。

**你的核心任务是帮助用户创建视频。**

当用户表达想要创建视频但没有提供具体内容时，你应该：
1. 友好地确认他们的意图
2. 通过具体问题引导他们提供细节：
   - "您想创作什么主题的视频？比如：旅行、美食、宠物、科技等"
   - "视频的主角是谁？人物、动物、还是物品？"
   - "故事发生在什么场景？室内、户外、城市、自然？"
   - "您希望什么风格？温馨、激动人心、搞笑、还是严肃？"

当用户提供了具体内容（如"一个女人和狗在海滩跑步"），你应该：
1. 确认理解了他们的想法
2. 告诉他们"我现在就开始为您生成这个视频"
3. 系统会自动开始视频生成流程

**重要原则：**
- 不要重复相同的通用回答
- 每次回复都要推进对话，帮助用户明确想法
- 如果用户已经提供了主题，不要再问相同的问题
- 用简洁、友好的中文回答，避免冗长的列表

**示例对话：**
用户："帮助我创建视频"
你："好的！我很乐意帮您。您想创作什么主题的视频呢？比如记录生活、展示才艺、讲述故事等？"

用户："一个女人和狗"
你："很好的开始！这个女人和狗在做什么呢？是在散步、玩耍、还是其他活动？在什么地方？"

用户："在海滩跑步"
你："太棒了！我现在就开始为您生成'一个女人和狗在海滩跑步'的视频。请稍等片刻..."
（然后系统会自动触发视频生成）`
          })
        })

        if (!threadResponse.ok) {
          throw new Error(`Failed to create thread: ${threadResponse.status}`)
        }

        const threadData = await threadResponse.json()
        threadId = threadData.id

        setWorkflow(prev => ({
          ...prev,
          context: { ...prev.context, chat_thread_id: threadId }
        }))
      }

      // 验证threadId存在
      if (!threadId) {
        throw new Error('No thread ID available')
      }

      // 调用聊天API
      const chatResponse = await fetch(`/api/v1/chat/threads/${threadId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: message,
          temperature: 0.7,
          stream: false
        })
      })

      if (!chatResponse.ok) {
        throw new Error(`Chat request failed: ${chatResponse.status}`)
      }

      const chatData = await chatResponse.json()

      // 移除"正在思考"消息
      setMessages(prev => prev.filter(msg => msg.id !== thinkingMsgId))

      if (chatData.response) {
        addMessage('assistant', chatData.response)

        // 🔥 SMART AUTO-TRIGGER: Check if accumulated content is now sufficient for video generation
        // Collect recent user messages to build complete video idea
        const recentUserMessages = messages
          .filter(msg => msg.role === 'user')
          .slice(-3)  // Last 3 user messages
          .map(msg => msg.content)
          .join(' ')

        const combinedIdea = `${recentUserMessages} ${message}`.trim()

        // Re-classify the accumulated content
        const recheck = await classifyIntentWithLLM(combinedIdea)

        if (recheck.intent === 'video_generation' && recheck.confidence > 0.65) {
          console.log('[Auto-trigger] Accumulated content is now sufficient for video generation')
          console.log('[Auto-trigger] Combined idea:', combinedIdea)
          console.log('[Auto-trigger] Confidence:', recheck.confidence)

          // Remove the chat response and trigger video generation
          setMessages(prev => prev.slice(0, -1))  // Remove last assistant message

          // Add transition message
          addMessage('assistant', '太好了！我已经理解了您的想法。现在开始为您生成视频...')

          // Trigger video generation with accumulated content
          await handleVideoGeneration(combinedIdea)
        }
      } else {
        addMessage('system', '收到了响应，但内容为空。')
      }

    } catch (error) {
      // 移除"正在思考"消息
      setMessages(prev => prev.filter(msg => !msg.content.includes('正在思考')))
      addMessage('system', `抱歉，我遇到了一些问题：${error instanceof Error ? error.message : '未知错误'}。请重试。`)
    }
  }

  // 处理视频生成
  const handleVideoGeneration = async (idea: string) => {
    addMessage('assistant', '好的，我将为您精心打造这个视频项目。让我开始生成故事大纲...')

    setWorkflow(prev => ({
      ...prev,
      status: 'generating',
      step: 'outline',
      progress: 0,
      progressMessage: 'Creating your video project...'
    }))

    // Enable WebSocket progress display
    setShowWebSocketProgress(true)

    try {
      const createResponse = await fetch('/api/v1/conversational/episode/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          series_id: 'default',
          episode_number: 1,
          mode: 'idea',
          initial_content: idea,
          style: style,
          title: `Video - ${new Date().toLocaleDateString()}`
        })
      })

      // Handle validation errors (400 Bad Request)
      if (!createResponse.ok) {
        const errorData = await createResponse.json().catch(() => ({ detail: 'Failed to create workflow' }))

        // Check if it's a content validation error
        if (errorData.detail && typeof errorData.detail === 'object') {
          const detail = errorData.detail

          if (detail.error === 'content_validation_failed' || detail.error === 'invalid_intent') {
            // Remove the "generating" message
            setMessages(prev => prev.filter(msg => !msg.content.includes('好的，我将为您精心打造')))

            // Reset workflow state
            setWorkflow(prev => ({
              ...prev,
              status: 'idle',
              step: 'input'
            }))
            setShowWebSocketProgress(false)

            // Display validation error with helpful guidance
            let errorMessage = detail.message || '视频创意需要更多细节'

            if (detail.validation) {
              const v = detail.validation
              errorMessage += '\n\n缺少的元素：'
              if (v.missing_elements && v.missing_elements.length > 0) {
                errorMessage += '\n• ' + v.missing_elements.map((e: string) => {
                  const labels: Record<string, string> = {
                    'subject': '主题/主角',
                    'action': '故事情节',
                    'context': '场景/风格'
                  }
                  return labels[e] || e
                }).join('\n• ')
              }

              if (v.suggestions && v.suggestions.length > 0) {
                errorMessage += '\n\n建议：'
                errorMessage += '\n• ' + v.suggestions.join('\n• ')
              }
            }

            if (detail.examples && detail.examples.length > 0) {
              errorMessage += '\n\n示例：'
              errorMessage += '\n• ' + detail.examples.join('\n• ')
            }

            addMessage('system', errorMessage)
            return
          }
        }

        throw new Error(typeof errorData.detail === 'string' ? errorData.detail : 'Failed to create workflow')
      }

      const createData = await createResponse.json()
      const episodeId = createData.episode_id

      setWorkflow(prev => ({ ...prev, episodeId }))

      const outlineResponse = await fetch(`/api/v1/conversational/episode/${episodeId}/outline/generate`, {
        method: 'POST'
      })

      if (!outlineResponse.ok) throw new Error('Failed to start outline generation')

      pollStatus(episodeId, 'outline')

    } catch (error) {
      // Remove the "generating" message
      setMessages(prev => prev.filter(msg => !msg.content.includes('好的，我将为您精心打造')))

      setWorkflow(prev => ({
        ...prev,
        status: 'error',
        error: error instanceof Error ? error.message : 'Failed to start generation'
      }))
      setShowWebSocketProgress(false)
      addMessage('system', '创建项目失败，请重试')
    }
  }

  // 主提交处理函数（混合意图检测）
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!idea.trim()) return

    const userMessage = idea.trim()
    addMessage('user', userMessage)
    setIdea('')  // 立即清空输入框

    // 第一层：快速规则检测
    const quickIntent = quickIntentCheck(userMessage)

    if (quickIntent === 'chat') {
      // 明确是对话，直接处理
      await handleChatMessage(userMessage)
    } else if (quickIntent === 'video_generation') {
      // 明确是视频生成，直接处理
      await handleVideoGeneration(userMessage)
    } else {
      // 不确定，使用LLM分类（第二层）
      addMessage('assistant', '让我理解一下您的需求...')

      const classification = await classifyIntentWithLLM(userMessage)

      // 移除"理解中"消息
      setMessages(prev => prev.filter(msg => !msg.content.includes('让我理解一下')))

      if (classification.intent === 'video_generation' && classification.confidence > 0.6) {
        await handleVideoGeneration(userMessage)
      } else {
        await handleChatMessage(userMessage)
      }
    }
  }

  const handleConfirmOutline = async () => {
    if (!workflow.episodeId) return

    addMessage('assistant', '正在生成角色设计...')
    setWorkflow(prev => ({ ...prev, status: 'generating' }))

    try {
      await fetch(`/api/v1/conversational/episode/${workflow.episodeId}/outline/confirm`, { method: 'POST' })
      await fetch(`/api/v1/conversational/episode/${workflow.episodeId}/characters/generate`, { method: 'POST' })
      pollStatus(workflow.episodeId, 'characters')
    } catch (error) {
      setWorkflow(prev => ({ ...prev, status: 'error', error: 'Failed to generate characters' }))
    }
  }

  const handleConfirmCharacters = async () => {
    if (!workflow.episodeId) return

    addMessage('assistant', '正在生成场景设计...')
    setWorkflow(prev => ({ ...prev, status: 'generating' }))

    try {
      await fetch(`/api/v1/conversational/episode/${workflow.episodeId}/characters/confirm`, { method: 'POST' })
      await fetch(`/api/v1/conversational/episode/${workflow.episodeId}/scenes/generate`, { method: 'POST' })
      pollStatus(workflow.episodeId, 'scenes')
    } catch (error) {
      setWorkflow(prev => ({ ...prev, status: 'error', error: 'Failed to generate scenes' }))
    }
  }

  const handleConfirmScenes = async () => {
    if (!workflow.episodeId) return

    addMessage('assistant', '正在生成分镜剧本...')
    setWorkflow(prev => ({ ...prev, status: 'generating' }))

    try {
      await fetch(`/api/v1/conversational/episode/${workflow.episodeId}/scenes/confirm`, { method: 'POST' })
      await fetch(`/api/v1/conversational/episode/${workflow.episodeId}/storyboard/generate`, { method: 'POST' })
      pollStatus(workflow.episodeId, 'storyboard')
    } catch (error) {
      setWorkflow(prev => ({ ...prev, status: 'error', error: 'Failed to generate storyboard' }))
    }
  }

  const handleConfirmStoryboard = async () => {
    if (!workflow.episodeId) return

    addMessage('assistant', '正在为每个分镜生成视频，这可能需要一些时间...')
    setWorkflow(prev => ({ ...prev, status: 'generating', step: 'video' }))

    try {
      // Confirm storyboard
      await fetch(`/api/v1/conversational/episode/${workflow.episodeId}/storyboard/confirm`, {
        method: 'POST'
      })

      // ✅ NEW: Generate videos directly for shots (not segments!)
      const response = await fetch(
        `/api/v1/conversational/episode/${workflow.episodeId}/shots/generate-videos`,
        { method: 'POST' }
      )

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to start video generation' }))
        throw new Error(errorData.detail || 'Failed to start video generation')
      }

      const data = await response.json()
      addMessage('assistant', `已开始为 ${data.total_shots} 个分镜生成视频...`)

      // Poll for video generation progress
      pollShotVideoGeneration(workflow.episodeId)

    } catch (error) {
      setWorkflow(prev => ({ ...prev, status: 'error', error: 'Failed to generate videos' }))
      addMessage('system', `视频生成失败: ${error instanceof Error ? error.message : '请重试'}`)
    }
  }

  const pollShotVideoGeneration = async (episodeId: string) => {
    try {
      // ✅ NEW: Poll shot video status directly
      const response = await fetch(
        `/api/v1/conversational/episode/${episodeId}/shots/video-status`
      )

      if (!response.ok) {
        setTimeout(() => pollShotVideoGeneration(episodeId), 2000)
        return
      }

      const data = await response.json()

      // Update storyboard with shot data from database
      const updatedStoryboard = workflow.storyboard.map(shot => {
        const dbShot = data.shots.find((s: any) => s.id === shot.id)
        if (dbShot) {
          return {
            ...shot,
            video_url: dbShot.video_url,
            status: dbShot.status
          }
        }
        return shot
      })

      setWorkflow(prev => ({
        ...prev,
        storyboard: updatedStoryboard
      }))

      // Check if all done
      if (data.all_done) {
        setWorkflow(prev => ({
          ...prev,
          status: 'ready',
          step: 'video'
        }))
        addMessage('assistant', `所有分镜视频已生成完成！完成: ${data.completed}, 失败: ${data.failed}`)
      } else {
        // Continue polling
        setTimeout(() => pollShotVideoGeneration(episodeId), 2000)
      }

    } catch (error) {
      console.error('Poll video generation error:', error)
      setTimeout(() => pollShotVideoGeneration(episodeId), 3000)
    }
  }

  const handleShotRegenerate = async (shotIndex: number, changes: any) => {
    try {
      const shot = workflow.storyboard[shotIndex]

      if (!shot.id || shot.id.startsWith('shot-')) {
        addMessage('system', '该分镜还没有保存到数据库，请先保存')
        return
      }

      if (!workflow.episodeId) {
        addMessage('system', '无法重新生成：没有episode ID')
        return
      }

      addMessage('assistant', `正在重新生成分镜${shotIndex + 1}的视频...`)

      const response = await fetch(
        `/api/v1/conversational/episode/${workflow.episodeId}/shots/${shot.id}/regenerate-video`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        }
      )

      if (!response.ok) {
        const errorText = await response.text()
        console.error('Regenerate shot error:', errorText)
        throw new Error(`Failed to regenerate shot video: ${response.status}`)
      }

      const data = await response.json()
      console.log('Shot regeneration started:', data)

      // Update local state to show generating status
      const updatedStoryboard = [...workflow.storyboard]
      updatedStoryboard[shotIndex] = {
        ...shot,
        status: 'generating_video'
      }
      setWorkflow(prev => ({ ...prev, storyboard: updatedStoryboard }))

      // Poll for video generation status
      pollShotVideoGeneration(workflow.episodeId)
    } catch (error) {
      console.error('Error regenerating shot:', error)
      addMessage('system', `重新生成失败: ${error instanceof Error ? error.message : '请重试'}`)
    }
  }

  const handleCompileShots = async () => {
    if (!workflow.episodeId) return

    try {
      // Get all shots with videos - check both video_url and status
      const shotsWithVideos = workflow.storyboard.filter(shot => {
        const hasVideo = shot.video_url || (shot as any).video_url
        const isCompleted = (shot as any).status === 'completed'
        return hasVideo || isCompleted
      })

      if (shotsWithVideos.length === 0) {
        addMessage('system', '没有可合成的视频。请先生成分镜视频。')
        return
      }

      addMessage('assistant', `正在合成 ${shotsWithVideos.length} 个分镜视频...`)

      console.log('[Compilation] Compiling shots:', shotsWithVideos.map(s => ({
        id: s.id,
        shot_number: s.shot_number,
        has_video: !!s.video_url,
        status: (s as any).status
      })))

      // ✅ Use shot-based compilation endpoint with ALL shot IDs
      const response = await fetch(
        `/api/v1/conversational/episode/${workflow.episodeId}/video/compile`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            shot_ids: shotsWithVideos.map(s => s.id),
            transition_style: 'fade',
            audio_config: {
              volume_normalization: true,
              target_volume: 0.8
            }
          })
        }
      )

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to start compilation')
      }

      const data = await response.json()

      console.log('[Compilation] Started with job_id:', data.job_id, 'total_shots:', data.total_shots)

      // Poll for compilation status
      pollCompilationStatus(data.job_id)

    } catch (error) {
      console.error('[Compilation] Error:', error)
      addMessage('system', `视频合成失败: ${error instanceof Error ? error.message : '请重试'}`)
    }
  }

  const pollCompilationStatus = async (jobId: string) => {
    if (!workflow.episodeId) return

    try {
      // ✅ NEW: Use shot-based compilation status endpoint
      const response = await fetch(
        `/api/v1/conversational/episode/${workflow.episodeId}/video/compilation-status/${jobId}`
      )

      if (!response.ok) {
        setTimeout(() => pollCompilationStatus(jobId), 2000)
        return
      }

      const data = await response.json()

      if (data.status === 'completed') {
        setWorkflow(prev => ({
          ...prev,
          videoUrl: data.output_path,
          step: 'completed',
          status: 'ready'
        }))
        addMessage('assistant', '最终视频已生成完成！')
      } else if (data.status === 'failed') {
        addMessage('system', `视频合成失败: ${data.error || '未知错误'}`)
      } else {
        // Continue polling
        setTimeout(() => pollCompilationStatus(jobId), 2000)
      }

    } catch (error) {
      console.error('Poll compilation error:', error)
      setTimeout(() => pollCompilationStatus(jobId), 3000)
    }
  }

  const renderRightPanel = () => {
    if (workflow.step === 'input' || workflow.status === 'generating') {
      return (
        <div className="right-panel-empty">
          {workflow.status === 'generating' ? (
            <div className="generating-state">
              <div className="spinner-large"></div>
              <p>正在生成中...</p>
            </div>
          ) : (
            <p>输入您的想法后，内容将在此处显示</p>
          )}
        </div>
      )
    }

    if (workflow.step === 'outline' && workflow.outline) {
      return (
        <div className="right-panel-content">
          <div className="panel-header">
            <h3>第1集: {workflow.outline.title}</h3>
            <span className="badge badge-success">已有视频</span>
            <span className="badge badge-info">内容由 AI 生成</span>
          </div>

          <div className="content-section">
            <h4 className="section-title">故事梗概</h4>
            <div className="synopsis-box">
              <p className="label">内容概要:</p>
              <p>{workflow.outline.synopsis}</p>
            </div>
          </div>

          <div className="content-section">
            <h4 className="section-title">剧本亮点</h4>
            {workflow.outline.plot_summary?.map((plot, index) => (
              <div key={index} className="highlight-item">
                <span className="highlight-marker">{plot.act || plot.scene || `亮点${index + 1}`}:</span>
                <p>{plot.description}</p>
              </div>
            ))}
          </div>

          <div className="panel-footer">
            <div className="footer-options">
              <span>模型</span>
              <span>智能选择</span>
              <span>画面比例</span>
              <span>9:16</span>
            </div>
            <button className="btn-primary-action" onClick={handleConfirmOutline}>
              确认分镜大纲
            </button>
          </div>
        </div>
      )
    }

    if (workflow.step === 'characters') {
      return (
        <div className="right-panel-content">
          <div className="panel-header">
            <h3>角色设计</h3>
            <span className="badge badge-info">内容由 AI 生成</span>
          </div>

          {workflow.characters.length > 0 ? (
            <div className="characters-grid-new">
              {workflow.characters.map((char) => (
                <div key={char.id} className="character-card-new">
                  {char.image_url && (
                    <img src={char.image_url} alt={char.name} className="character-image-new" />
                  )}
                  <div className="character-overlay">
                    <span className="character-name">{char.name}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state-panel">
              <p>暂时没有检测到角色，您可以直接继续下一步，系统将自动生成角色。</p>
            </div>
          )}

          <div className="panel-footer">
            <button className="btn-primary-action" onClick={handleConfirmCharacters}>
              确认角色设计
            </button>
          </div>
        </div>
      )
    }

    if (workflow.step === 'scenes') {
      return (
        <div className="right-panel-content">
          <div className="panel-header">
            <h3>第1集: {workflow.outline?.title}</h3>
            <span className="badge badge-info">内容由 AI 生成</span>
          </div>

          {workflow.scenes.length > 0 ? (
            <>
              <div className="content-section">
                <h4 className="section-title highlight">场景列表</h4>
                <div className="scene-descriptions">
                  {workflow.scenes.map((scene) => (
                    <p key={scene.id}>
                      <strong>{scene.name}</strong>: {scene.description}
                    </p>
                  ))}
                </div>
              </div>

              <div className="scenes-grid-new">
                {workflow.scenes.map((scene) => (
                  <div key={scene.id} className="scene-card-new">
                    {scene.image_url && (
                      <img src={scene.image_url} alt={scene.name} className="scene-image-new" />
                    )}
                    <div className="scene-overlay">
                      <span>{scene.name}</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="empty-state-panel">
              <p>场景正在生成中，请稍候...</p>
            </div>
          )}

          <div className="panel-footer">
            <button className="btn-primary-action" onClick={handleConfirmScenes}>
              确认场景设计
            </button>
          </div>
        </div>
      )
    }

    if (workflow.step === 'storyboard') {
      const currentShot = workflow.storyboard[selectedShot]

      if (workflow.storyboard.length === 0) {
        return (
          <div className="right-panel-content">
            <div className="panel-header">
              <h3>分镜设计</h3>
              <span className="badge badge-info">内容由 AI 生成</span>
            </div>
            <div className="empty-state-panel">
              <p>分镜正在生成中，请稍候...</p>
            </div>
            <div className="panel-footer">
              <button className="btn-primary-action" onClick={handleConfirmStoryboard}>
                确认分镜设计
              </button>
            </div>
          </div>
        )
      }

      return (
        <div className="right-panel-content storyboard-view">
          <div className="storyboard-header">
            <button className="btn-icon" onClick={() => handleEditShot(selectedShot)}>
              ✏️ 编辑分镜
            </button>
            <button className="btn-icon" onClick={() => handleDuplicateShot(selectedShot)}>
              📋 复制
            </button>
            <button className="btn-icon btn-delete" onClick={() => handleDeleteShot(selectedShot)}>
              🗑️ 删除
            </button>
            <button className="btn-icon btn-add" onClick={handleAddShot}>
              ➕ 添加分镜
            </button>
          </div>

          {editingShot === selectedShot ? (
            <div className="shot-edit-form">
              <h4>编辑分镜 {selectedShot + 1}</h4>

              <div className="edit-field">
                <label>镜头描述:</label>
                <textarea
                  value={editedDescription}
                  onChange={(e) => setEditedDescription(e.target.value)}
                  rows={4}
                  placeholder="描述这个镜头的内容..."
                />
              </div>

              <div className="edit-field">
                <label>镜头角度:</label>
                <select
                  value={editedCameraAngle}
                  onChange={(e) => setEditedCameraAngle(e.target.value)}
                >
                  <option value="CLOSE UP">特写 (CLOSE UP)</option>
                  <option value="MEDIUM SHOT">中景 (MEDIUM SHOT)</option>
                  <option value="WIDE SHOT">远景 (WIDE SHOT)</option>
                  <option value="EXTREME CLOSE UP">大特写 (EXTREME CLOSE UP)</option>
                  <option value="FULL SHOT">全景 (FULL SHOT)</option>
                  <option value="OVER THE SHOULDER">过肩镜头 (OVER THE SHOULDER)</option>
                  <option value="BIRD'S EYE VIEW">鸟瞰 (BIRD'S EYE VIEW)</option>
                  <option value="LOW ANGLE">仰拍 (LOW ANGLE)</option>
                  <option value="HIGH ANGLE">俯拍 (HIGH ANGLE)</option>
                </select>
              </div>

              <div className="edit-field">
                <label>镜头运动:</label>
                <select
                  value={editedCameraMovement}
                  onChange={(e) => setEditedCameraMovement(e.target.value)}
                >
                  <option value="STATIC">静止 (STATIC)</option>
                  <option value="PAN">摇镜 (PAN)</option>
                  <option value="TILT">俯仰 (TILT)</option>
                  <option value="ZOOM">推拉 (ZOOM)</option>
                  <option value="DOLLY">移动 (DOLLY)</option>
                  <option value="TRACKING">跟踪 (TRACKING)</option>
                  <option value="CRANE">升降 (CRANE)</option>
                  <option value="HANDHELD">手持 (HANDHELD)</option>
                </select>
              </div>

              <div className="edit-actions">
                <button className="btn-save" onClick={handleSaveShot}>
                  💾 保存
                </button>
                <button className="btn-cancel" onClick={() => setEditingShot(null)}>
                  取消
                </button>
              </div>
            </div>
          ) : (
            <div className="main-preview">
              {currentShot?.image_url ? (
                <img src={currentShot.image_url} alt={`Shot ${selectedShot + 1}`} className="preview-image" />
              ) : (
                <div className="shot-description-placeholder">
                  <div className="shot-visual-desc">
                    <span className="camera-info">{currentShot?.camera_angle} | {currentShot?.camera_movement}</span>
                    <p>{currentShot?.visual_desc || currentShot?.description}</p>
                  </div>
                </div>
              )}
              <div className="shot-label">{currentShot?.visual_desc?.substring(0, 100) || currentShot?.description}</div>
            </div>
          )}

          <div className="playback-controls">
            <label className="subtitle-toggle">
              <span>字幕</span>
              <input type="checkbox" />
            </label>
            <button className="btn-play">▶</button>
            <span className="time-display">00:00/{String(workflow.storyboard.length * 3).padStart(2, '0')}:00</span>
            <button className="btn-storyboard-view">故事版视图</button>
          </div>

          <div className="timeline">
            {workflow.storyboard.map((shot, index) => (
              <div
                key={shot.id || index}
                className={`timeline-item ${selectedShot === index ? 'active' : ''}`}
                onClick={() => setSelectedShot(index)}
              >
                {shot.image_url && (
                  <img src={shot.image_url} alt={`Shot ${index + 1}`} />
                )}
                <span className="shot-time">分镜{index + 1}</span>
                <div className="timeline-item-actions">
                  <button
                    className="timeline-btn-edit"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleEditShot(index)
                    }}
                    title="编辑"
                  >
                    ✏️
                  </button>
                  <button
                    className="timeline-btn-delete"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDeleteShot(index)
                    }}
                    title="删除"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="panel-footer">
            <button className="btn-primary-action" onClick={handleConfirmStoryboard}>
              一键转视频
            </button>
          </div>
        </div>
      )
    }


    if (workflow.step === 'video' && workflow.storyboard.length > 0) {
      const currentShot = workflow.storyboard[selectedShot]
      const hasVideos = workflow.storyboard.some(shot => (shot as any).video_url)

      return (
        <div className="right-panel-content video-shots-view">
          <div className="panel-header">
            <h3>分镜视频编辑</h3>
            <span className="badge badge-info">
              {workflow.storyboard.filter(s => (s as any).video_url).length} / {workflow.storyboard.length} 已生成
            </span>
          </div>

          {/* Current Shot Preview */}
          <div className="shot-video-preview">
            {(currentShot as any).video_url ? (
              <video
                controls
                src={(currentShot as any).video_url}
                poster={currentShot.image_url}
                className="shot-video-player"
              />
            ) : currentShot.image_url ? (
              <div className="shot-image-preview">
                <img src={currentShot.image_url} alt={`Shot ${selectedShot + 1}`} />
                <div className="generating-overlay">
                  {(currentShot as any).status === 'generating' ? (
                    <>
                      <div className="spinner"></div>
                      <p>正在生成视频...</p>
                    </>
                  ) : (
                    <p>等待生成</p>
                  )}
                </div>
              </div>
            ) : (
              <div className="shot-placeholder">
                <p>分镜 {selectedShot + 1}</p>
              </div>
            )}
          </div>

          {/* Shot Details */}
          <div className="shot-details">
            <h4>分镜 {selectedShot + 1}: {currentShot.description?.substring(0, 50)}...</h4>
            <div className="shot-metadata">
              <span className="metadata-item">
                <strong>镜头角度:</strong> {currentShot.camera_angle}
              </span>
              <span className="metadata-item">
                <strong>镜头运动:</strong> {currentShot.camera_movement || 'STATIC'}
              </span>
            </div>
            <p className="shot-description-full">{currentShot.visual_desc || currentShot.description}</p>
          </div>

          {/* Shot Edit Controls */}
          {(currentShot as any).video_url && (
            <div className="shot-edit-controls">
              <button
                className="btn-edit-shot"
                onClick={() => handleEditShot(selectedShot)}
              >
                ✏️ 编辑分镜
              </button>
              <button
                className="btn-regenerate-shot"
                onClick={() => {
                  if (confirm(`确定要重新生成分镜${selectedShot + 1}的视频吗？`)) {
                    handleShotRegenerate(selectedShot, {
                      prompt: currentShot.visual_desc || currentShot.description
                    })
                  }
                }}
              >
                🔄 重新生成视频
              </button>
              <button
                className="btn-delete-shot"
                onClick={() => handleDeleteShot(selectedShot)}
              >
                🗑️ 删除分镜
              </button>
            </div>
          )}

          {/* Shots Timeline */}
          <div className="shots-timeline">
            <h4>所有分镜 ({workflow.storyboard.length})</h4>
            <div className="timeline-grid">
              {workflow.storyboard.map((shot, index) => (
                <div
                  key={shot.id || index}
                  className={`timeline-shot-card ${selectedShot === index ? 'active' : ''} ${draggedShotIndex === index ? 'dragging' : ''
                    } ${dragOverIndex === index ? 'drag-over' : ''}`}
                  draggable={true}
                  onDragStart={(e) => handleDragStart(e, index)}
                  onDragOver={(e) => handleDragOver(e, index)}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDrop(e, index)}
                  onDragEnd={handleDragEnd}
                  onClick={() => setSelectedShot(index)}
                >
                  <div className="shot-thumbnail">
                    {(shot as any).video_url ? (
                      <video src={(shot as any).video_url} />
                    ) : shot.image_url ? (
                      <img src={shot.image_url} alt={`Shot ${index + 1}`} />
                    ) : (
                      <div className="no-thumbnail">#{index + 1}</div>
                    )}
                    {(shot as any).video_url && (
                      <div className="video-badge">▶</div>
                    )}
                    {(shot as any).status === 'generating' && (
                      <div className="generating-badge">⟳</div>
                    )}
                  </div>
                  <div className="shot-info">
                    <span className="shot-number">分镜 {index + 1}</span>
                    <span className="shot-status">
                      {(shot as any).video_url ? '✓ 已生成' :
                        (shot as any).status === 'generating' ? '⟳ 生成中' : '○ 待生成'}
                    </span>
                  </div>
                  <div className="shot-actions">
                    <button
                      className="shot-action-btn"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleEditShot(index)
                      }}
                      title="编辑"
                    >
                      ✏️
                    </button>
                    <button
                      className="shot-action-btn"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteShot(index)
                      }}
                      title="删除"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Compile Button */}
          {hasVideos && (
            <div className="panel-footer">
              <button
                className="btn-primary-action glass-button"
                onClick={() => {
                  if (workflow.episodeId) {
                    handleCompileShots()
                  }
                }}
              >
                合成最终视频
              </button>
            </div>
          )}
        </div>
      )
    }

    if ((workflow.step === 'completed') && workflow.videoUrl) {
      return (
        <div className="right-panel-content video-view">
          <div className="video-preview-large">
            <video controls src={workflow.videoUrl} className="main-video">
              Your browser does not support video playback.
            </video>
          </div>

          <div className="video-actions">
            <a href={workflow.videoUrl} download className="btn-primary-action">
              导出
            </a>
            <button
              className="btn-secondary-action"
              onClick={() => {
                setWorkflow(prev => ({ ...prev, step: 'video' }))
              }}
            >
              返回分镜编辑
            </button>
          </div>
        </div>
      )
    }

    return null
  }

  return (
    <div className="studio-layout">
      <div className="episode-sidebar">
        <div className="sidebar-header">
          <span className="back-link">← 返回策划</span>
          <span className="episode-title">第1集: 视频项目</span>
        </div>
        <div className="episode-list">
          <div className="episode-section">
            <span className="section-label">剧集</span>
            <div className="episode-item active">
              <span className="episode-number">01</span>
            </div>
            <button className="add-episode">+</button>
          </div>
        </div>
      </div>

      <div className="nav-sidebar">
        <button
          className={`nav-item ${activeTab === 'video' ? 'active' : ''}`}
          onClick={() => setActiveTab('video')}
        >
          <span className="nav-icon">🎬</span>
          <span className="nav-label">画面</span>
        </button>
        <button
          className={`nav-item ${activeTab === 'audio' ? 'active' : ''}`}
          onClick={() => setActiveTab('audio')}
        >
          <span className="nav-icon">🎙</span>
          <span className="nav-label">配音</span>
        </button>
        <button
          className={`nav-item ${activeTab === 'music' ? 'active' : ''}`}
          onClick={() => setActiveTab('music')}
        >
          <span className="nav-icon">🎵</span>
          <span className="nav-label">音乐</span>
        </button>
      </div>

      <div className="chat-panel glass-card">
        <div className="shot-selector">
          <span>■ 分镜{selectedShot + 1}</span>
          <button className="btn-generate-video">图片生成视频</button>
        </div>

        <div className="chat-brand">
          <span className="brand-icon">⚡</span>
          <span className="brand-name">Seko</span>
          <span className="llm-model-indicator" title={`当前对话AI: ${llmModel}`}>
            🤖 {llmModels.find(m => m.id === llmModel)?.name || llmModel}
          </span>
          {workflow.episodeId && (
            <span className="ws-status-indicator" title={wsConnected ? 'WebSocket已连接' : 'WebSocket未连接'}>
              {wsConnected ? '🟢' : '🔴'}
            </span>
          )}
        </div>

        {/* Real-time WebSocket Progress */}
        {showWebSocketProgress && workflow.episodeId && workflow.status === 'generating' && (
          <div className="websocket-progress-container">
            <WorkflowProgress
              workflowId={workflow.episodeId}
              state={workflow.status === 'generating' ? 'running' :
                workflow.status === 'ready' ? 'completed' :
                  workflow.status === 'error' ? 'failed' : 'pending'}
              progress={workflow.progress}
              stage={workflow.step}
              message={workflow.progressMessage}
              onCancel={() => {
                // TODO: Implement workflow cancellation
                addMessage('system', '取消功能即将推出')
              }}
            />
          </div>
        )}

        <div className="chat-messages">
          {messages.map((msg) => (
            <div key={msg.id} className={`chat-message ${msg.role}`}>
              {msg.role === 'assistant' && (
                <div className="message-content">
                  {msg.content.split('\n').map((line, i) => (
                    <p key={i}>{line}</p>
                  ))}
                </div>
              )}
              {msg.role === 'user' && (
                <div className="user-message">
                  {msg.content.split('\n').map((line, i) => (
                    <p key={i}>{line}</p>
                  ))}
                </div>
              )}
              {msg.role === 'system' && (
                <div className="system-message">
                  {msg.content.split('\n').map((line, i) => (
                    <p key={i}>{line}</p>
                  ))}
                </div>
              )}
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        <div className="workflow-steps-list">
          {workflowSteps.filter(step => step.label).map((step) => (
            <div key={step.id} className={`workflow-step-item ${step.completed ? 'completed' : ''} ${step.active ? 'active' : ''}`}>
              <span className={`step-checkbox ${step.completed ? 'checked' : ''}`}>
                {step.completed ? '✓' : '○'}
              </span>
              <div className="step-content">
                <span className="step-label">{step.label}</span>
                {step.sublabel && <span className="step-sublabel">{step.sublabel}</span>}
              </div>
            </div>
          ))}
        </div>

        {workflow.episodeId && (
          <div className="episode-link">
            <span className="link-icon">📄</span>
            <div className="link-info">
              <span className="link-title">第1集: {workflow.outline?.title || '视频项目'}</span>
              <span className="link-date">{new Date().toLocaleString()}</span>
            </div>
            <button className="btn-copy">📋</button>
          </div>
        )}

        <div className="chat-input-area">
          <form onSubmit={handleSubmit}>
            <div className="input-wrapper">
              <button type="button" className="btn-attach">📎</button>
              <input
                type="text"
                placeholder="输入你的问题，Shift+Enter换行"
                value={idea}
                onChange={(e) => setIdea(e.target.value)}
                disabled={workflow.status === 'generating'}
              />
              <button
                type="submit"
                className="btn-send"
                disabled={!idea.trim() || workflow.status === 'generating'}
              >
                ➤
              </button>
            </div>
            <div className="input-options">
              <select
                value={style}
                onChange={(e) => setStyle(e.target.value)}
                className="style-select"
              >
                <option value="cinematic">视频生成</option>
                <option value="anime">动漫风格</option>
                <option value="realistic">写实风格</option>
              </select>

              <button
                type="button"
                className="btn-model-settings"
                onClick={() => setShowModelSettings(!showModelSettings)}
                title="模型设置"
              >
                ⚙️
              </button>

              <span className="char-count">+10</span>
            </div>

            {showModelSettings && (
              <div className="model-settings-dropdown">
                <div className="dropdown-header">
                  <span className="dropdown-title">⚙️ 模型设置</span>
                  <button
                    className="btn-close-dropdown"
                    onClick={() => setShowModelSettings(false)}
                    title="关闭"
                  >
                    ✕
                  </button>
                </div>

                <div className="model-select-group">
                  <label className="model-select-label">
                    <span className="label-icon">🤖</span>
                    对话AI模型
                  </label>
                  <select
                    value={llmModel}
                    onChange={(e) => {
                      setLlmModel(e.target.value)
                      localStorage.setItem('selectedLLMModel', e.target.value)
                    }}
                    className="model-select-compact"
                  >
                    {llmModels.length > 0 ? (
                      llmModels.map(model => (
                        <option key={model.id} value={model.id}>
                          {model.name} ({model.provider})
                        </option>
                      ))
                    ) : (
                      <>
                        <option value="gemini-2.0-flash-exp">Gemini 2.0 Flash (Google)</option>
                        <option value="gemini-1.5-pro">Gemini 1.5 Pro (Google)</option>
                        <option value="gemini-1.5-flash">Gemini 1.5 Flash (Google)</option>
                        <option value="gpt-4o">GPT-4o (OpenAI)</option>
                        <option value="gpt-4o-mini">GPT-4o Mini (OpenAI)</option>
                        <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet (Anthropic)</option>
                        <option value="qwen-plus">Qwen Plus (Alibaba)</option>
                        <option value="deepseek-chat">DeepSeek Chat (DeepSeek)</option>
                      </>
                    )}
                  </select>
                  {llmModels.find(m => m.id === llmModel)?.description && (
                    <span className="model-description">
                      {llmModels.find(m => m.id === llmModel)?.description}
                    </span>
                  )}
                </div>

                <div className="model-select-group">
                  <label className="model-select-label">
                    <span className="label-icon">🎬</span>
                    视频生成模型
                  </label>
                  <select
                    value={videoModel}
                    onChange={(e) => {
                      setVideoModel(e.target.value)
                      localStorage.setItem('model_preferences', JSON.stringify({
                        video_model: e.target.value,
                        image_model: imageModel
                      }))
                    }}
                    className="model-select-compact"
                  >
                    {videoModels.map(model => (
                      <option key={model.name} value={model.name}>
                        {model.name}
                      </option>
                    ))}
                  </select>
                  {videoModels.find(m => m.name === videoModel)?.description && (
                    <span className="model-description">
                      {videoModels.find(m => m.name === videoModel)?.description}
                    </span>
                  )}
                </div>

                <div className="model-select-group">
                  <label className="model-select-label">
                    <span className="label-icon">🖼️</span>
                    图像生成模型
                  </label>
                  <select
                    value={imageModel}
                    onChange={(e) => {
                      setImageModel(e.target.value)
                      localStorage.setItem('model_preferences', JSON.stringify({
                        video_model: videoModel,
                        image_model: e.target.value
                      }))
                    }}
                    className="model-select-compact"
                  >
                    {imageModels.map(model => (
                      <option key={model.name} value={model.name}>
                        {model.name}
                      </option>
                    ))}
                  </select>
                  {imageModels.find(m => m.name === imageModel)?.description && (
                    <span className="model-description">
                      {imageModels.find(m => m.name === imageModel)?.description}
                    </span>
                  )}
                </div>
              </div>
            )}
          </form>
        </div>
      </div>

      <div className="content-panel glass-card">
        {renderRightPanel()}
      </div>
    </div>
  )
}

export default Idea2Video
