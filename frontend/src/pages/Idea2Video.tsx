import { useState, useCallback, useRef, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
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
  image_url: string
  video_url?: string
}

interface Outline {
  title: string
  genre: string
  style: string
  synopsis: string
  characters_summary: Array<{name: string, role: string, description?: string}>
  plot_summary: Array<{act?: string, scene?: string, description: string}>
  highlights: string[]
}

interface ChatMessage {
  id: string
  role: 'assistant' | 'user' | 'system'
  content: string
  timestamp: Date
}

interface WorkflowState {
  step: 'input' | 'outline' | 'characters' | 'scenes' | 'storyboard' | 'video' | 'completed'
  status: 'idle' | 'generating' | 'ready' | 'error'
  episodeId: string | null
  outline: Outline | null
  characters: Character[]
  scenes: Scene[]
  storyboard: Shot[]
  videoUrl: string | null
  error: string | null
  progress: number
  progressMessage: string
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
    error: null,
    progress: 0,
    progressMessage: ''
  })

  const [selectedShot, setSelectedShot] = useState<number>(0)
  const [activeTab, setActiveTab] = useState<'video' | 'audio' | 'music'>('video')
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const episodeId = searchParams.get('episode')
    if (episodeId && !workflow.episodeId) {
      restoreDraftState(episodeId)
    }
  }, [searchParams])

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

  const determineStepFromState = (backendState: string): 'outline' | 'characters' | 'scenes' | 'storyboard' | 'video' | 'completed' => {
    if (backendState === 'video_completed') return 'completed'
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

  const pollStatus = useCallback(async (episodeId: string, expectedStep: string) => {
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
        setTimeout(() => pollStatus(episodeId, expectedStep), 3000)
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
        setTimeout(() => pollStatus(episodeId, expectedStep), 2000)
        return
      }

      if (isStepComplete(backendState, expectedStep)) {
        const newStep = determineStepFromState(backendState)
        const videoUrl = data.video_path || data.step_info?.video?.path || null
        
        console.log('[DEBUG] Poll complete - backendState:', backendState, 'expectedStep:', expectedStep)
        console.log('[DEBUG] data.outline:', data.outline)
        console.log('[DEBUG] data.characters:', data.characters)
        console.log('[DEBUG] Full response data:', data)
        
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

      setTimeout(() => pollStatus(episodeId, expectedStep), 2000)

    } catch (error) {
      console.error('Poll error:', error)
      setTimeout(() => pollStatus(episodeId, expectedStep), 3000)
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!idea.trim()) return

    addMessage('user', idea)
    addMessage('assistant', '好的，我将为您精心打造这个视频项目。让我开始生成故事大纲...')

    setWorkflow(prev => ({
      ...prev,
      status: 'generating',
      step: 'outline',
      progress: 0,
      progressMessage: 'Creating your video project...'
    }))

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

      if (!createResponse.ok) throw new Error('Failed to create workflow')
      
      const createData = await createResponse.json()
      const episodeId = createData.episode_id

      setWorkflow(prev => ({ ...prev, episodeId }))

      const outlineResponse = await fetch(`/api/v1/conversational/episode/${episodeId}/outline/generate`, {
        method: 'POST'
      })

      if (!outlineResponse.ok) throw new Error('Failed to start outline generation')

      pollStatus(episodeId, 'outline')
      setIdea('')

    } catch (error) {
      setWorkflow(prev => ({
        ...prev,
        status: 'error',
        error: error instanceof Error ? error.message : 'Failed to start generation'
      }))
      addMessage('system', '创建项目失败，请重试')
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

    addMessage('assistant', '正在生成视频，这可能需要一些时间...')
    setWorkflow(prev => ({ ...prev, status: 'generating' }))

    try {
      await fetch(`/api/v1/conversational/episode/${workflow.episodeId}/storyboard/confirm`, { method: 'POST' })
      await fetch(`/api/v1/conversational/episode/${workflow.episodeId}/video/generate`, { method: 'POST' })
      pollStatus(workflow.episodeId, 'video')
    } catch (error) {
      setWorkflow(prev => ({ ...prev, status: 'error', error: 'Failed to generate video' }))
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

    if (workflow.step === 'characters' && workflow.characters.length > 0) {
      return (
        <div className="right-panel-content">
          <div className="panel-header">
            <h3>角色设计</h3>
            <span className="badge badge-info">内容由 AI 生成</span>
          </div>
          
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

          <div className="panel-footer">
            <button className="btn-primary-action" onClick={handleConfirmCharacters}>
              确认角色设计
            </button>
          </div>
        </div>
      )
    }

    if (workflow.step === 'scenes' && workflow.scenes.length > 0) {
      return (
        <div className="right-panel-content">
          <div className="panel-header">
            <h3>第1集: {workflow.outline?.title}</h3>
            <span className="badge badge-success">已有视频</span>
            <span className="badge badge-info">内容由 AI 生成</span>
          </div>
          
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

          <div className="panel-footer">
            <button className="btn-primary-action" onClick={handleConfirmScenes}>
              确认场景设计
            </button>
          </div>
        </div>
      )
    }

    if (workflow.step === 'storyboard' && workflow.storyboard.length > 0) {
      const currentShot = workflow.storyboard[selectedShot]
      return (
        <div className="right-panel-content storyboard-view">
          <div className="storyboard-header">
            <button className="btn-icon">裁剪分镜</button>
            <button className="btn-icon">对口型</button>
          </div>
          
          <div className="main-preview">
            {currentShot?.image_url && (
              <img src={currentShot.image_url} alt={`Shot ${selectedShot + 1}`} className="preview-image" />
            )}
            <div className="shot-label">{currentShot?.description}</div>
          </div>

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

    if ((workflow.step === 'video' || workflow.step === 'completed') && workflow.videoUrl) {
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

      <div className="chat-panel">
        <div className="shot-selector">
          <span>■ 分镜{selectedShot + 1}</span>
          <button className="btn-generate-video">图片生成视频</button>
        </div>

        <div className="chat-brand">
          <span className="brand-icon">⚡</span>
          <span className="brand-name">Seko</span>
        </div>

        <div className="chat-messages">
          {messages.map((msg) => (
            <div key={msg.id} className={`chat-message ${msg.role}`}>
              {msg.role === 'assistant' && (
                <div className="message-content">
                  <p>{msg.content}</p>
                </div>
              )}
              {msg.role === 'user' && (
                <div className="user-message">
                  <p>{msg.content}</p>
                </div>
              )}
              {msg.role === 'system' && (
                <div className="system-message">
                  <p>{msg.content}</p>
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
              <span className="char-count">+10</span>
            </div>
          </form>
        </div>
      </div>

      <div className="content-panel">
        {renderRightPanel()}
      </div>
    </div>
  )
}

export default Idea2Video
