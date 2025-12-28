import { useState, useCallback } from 'react'
import './Idea2Video.css'

interface Character {
  id: string
  name: string
  role: string
  description: string
  appearance: string
  image_url: string
}

interface Shot {
  id: string
  shot_number: number
  description: string
  camera_angle: string
  image_url: string
}

interface Outline {
  title: string
  genre: string
  style: string
  synopsis: string
  characters_summary: Array<{name: string, role: string}>
  plot_summary: Array<{scene: string, description: string}>
  highlights: string[]
}

interface WorkflowState {
  step: 'input' | 'outline' | 'characters' | 'storyboard' | 'video' | 'completed'
  status: 'idle' | 'generating' | 'ready' | 'error'
  episodeId: string | null
  outline: Outline | null
  characters: Character[]
  storyboard: Shot[]
  videoUrl: string | null
  error: string | null
  progress: number
  progressMessage: string
}

function Idea2Video() {
  const [idea, setIdea] = useState('')
  const [style, setStyle] = useState('cinematic')
  const [duration, setDuration] = useState('30')
  
  const [workflow, setWorkflow] = useState<WorkflowState>({
    step: 'input',
    status: 'idle',
    episodeId: null,
    outline: null,
    characters: [],
    storyboard: [],
    videoUrl: null,
    error: null,
    progress: 0,
    progressMessage: ''
  })

  const pollStatus = useCallback(async (episodeId: string, currentStep: string) => {
    try {
      const response = await fetch(`/api/v1/conversational/episode/${episodeId}/state`)
      if (!response.ok) return
      
      const data = await response.json()
      const state = data.state
      
      if (state.includes('generating')) {
        setWorkflow(prev => ({
          ...prev,
          status: 'generating',
          progressMessage: `Generating ${currentStep}...`
        }))
        setTimeout(() => pollStatus(episodeId, currentStep), 2000)
      } else if (state.includes('generated') || state.includes('confirmed')) {
        await fetchWorkflowData(episodeId)
      } else if (state === 'failed') {
        setWorkflow(prev => ({
          ...prev,
          status: 'error',
          error: data.error || 'Generation failed'
        }))
      }
    } catch (error) {
      console.error('Poll error:', error)
      setTimeout(() => pollStatus(episodeId, currentStep), 3000)
    }
  }, [])

  const fetchWorkflowData = async (episodeId: string) => {
    try {
      const response = await fetch(`/api/v1/conversational/episode/${episodeId}/state`)
      if (!response.ok) return
      
      const data = await response.json()
      
      setWorkflow(prev => {
        const newState = { ...prev }
        
        if (data.outline) {
          newState.outline = data.outline
          newState.step = 'outline'
          newState.status = 'ready'
        }
        
        if (data.characters && data.characters.length > 0) {
          newState.characters = data.characters
          newState.step = 'characters'
          newState.status = 'ready'
        }
        
        if (data.storyboard && data.storyboard.length > 0) {
          newState.storyboard = data.storyboard
          newState.step = 'storyboard'
          newState.status = 'ready'
        }
        
        if (data.state === 'video_completed') {
          newState.step = 'completed'
          newState.status = 'ready'
          newState.videoUrl = `/api/v1/conversational/episode/${episodeId}/video`
        }
        
        return newState
      })
    } catch (error) {
      console.error('Fetch error:', error)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!idea.trim()) return

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

      setWorkflow(prev => ({
        ...prev,
        episodeId,
        progressMessage: 'Generating story outline...'
      }))

      const outlineResponse = await fetch(`/api/v1/conversational/episode/${episodeId}/outline/generate`, {
        method: 'POST'
      })

      if (!outlineResponse.ok) throw new Error('Failed to start outline generation')

      pollStatus(episodeId, 'outline')

    } catch (error) {
      setWorkflow(prev => ({
        ...prev,
        status: 'error',
        error: error instanceof Error ? error.message : 'Failed to start generation'
      }))
    }
  }

  const handleConfirmOutline = async () => {
    if (!workflow.episodeId) return

    setWorkflow(prev => ({
      ...prev,
      status: 'generating',
      step: 'characters',
      progressMessage: 'Generating characters...'
    }))

    try {
      await fetch(`/api/v1/conversational/episode/${workflow.episodeId}/outline/confirm`, {
        method: 'POST'
      })

      await fetch(`/api/v1/conversational/episode/${workflow.episodeId}/characters/generate`, {
        method: 'POST'
      })

      pollStatus(workflow.episodeId, 'characters')

    } catch (error) {
      setWorkflow(prev => ({
        ...prev,
        status: 'error',
        error: 'Failed to generate characters'
      }))
    }
  }

  const handleConfirmCharacters = async () => {
    if (!workflow.episodeId) return

    setWorkflow(prev => ({
      ...prev,
      status: 'generating',
      step: 'storyboard',
      progressMessage: 'Generating storyboard...'
    }))

    try {
      await fetch(`/api/v1/conversational/episode/${workflow.episodeId}/characters/confirm`, {
        method: 'POST'
      })

      await fetch(`/api/v1/conversational/episode/${workflow.episodeId}/storyboard/generate`, {
        method: 'POST'
      })

      pollStatus(workflow.episodeId, 'storyboard')

    } catch (error) {
      setWorkflow(prev => ({
        ...prev,
        status: 'error',
        error: 'Failed to generate storyboard'
      }))
    }
  }

  const handleConfirmStoryboard = async () => {
    if (!workflow.episodeId) return

    setWorkflow(prev => ({
      ...prev,
      status: 'generating',
      step: 'video',
      progressMessage: 'Generating video (this may take a while)...'
    }))

    try {
      await fetch(`/api/v1/conversational/episode/${workflow.episodeId}/storyboard/confirm`, {
        method: 'POST'
      })

      await fetch(`/api/v1/conversational/episode/${workflow.episodeId}/video/generate`, {
        method: 'POST'
      })

      pollStatus(workflow.episodeId, 'video')

    } catch (error) {
      setWorkflow(prev => ({
        ...prev,
        status: 'error',
        error: 'Failed to generate video'
      }))
    }
  }

  const handleReset = () => {
    setWorkflow({
      step: 'input',
      status: 'idle',
      episodeId: null,
      outline: null,
      characters: [],
      storyboard: [],
      videoUrl: null,
      error: null,
      progress: 0,
      progressMessage: ''
    })
    setIdea('')
  }

  const stepLabels = ['Input', 'Outline', 'Characters', 'Storyboard', 'Video']
  const stepKeys = ['input', 'outline', 'characters', 'storyboard', 'video']
  const currentStepIndex = stepKeys.indexOf(workflow.step === 'completed' ? 'video' : workflow.step)

  return (
    <div className="container">
      <div className="page-header">
        <h1>Idea to Video</h1>
        <p>Transform your idea into a video step by step</p>
      </div>

      <div className="workflow-steps">
        {stepLabels.map((label, index) => (
          <div 
            key={label}
            className={`workflow-step ${index <= currentStepIndex ? 'active' : ''} ${index === currentStepIndex ? 'current' : ''}`}
          >
            <div className="step-number">{index + 1}</div>
            <span className="step-label">{label}</span>
          </div>
        ))}
      </div>

      {workflow.status === 'generating' && (
        <div className="card generating-overlay">
          <div className="spinner"></div>
          <p>{workflow.progressMessage}</p>
        </div>
      )}

      {workflow.status === 'error' && (
        <div className="card error-card">
          <h3>Error</h3>
          <p>{workflow.error}</p>
          <button className="btn btn-secondary" onClick={handleReset}>Start Over</button>
        </div>
      )}

      {workflow.step === 'input' && workflow.status !== 'generating' && (
        <div className="card">
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="label">Your Video Idea</label>
              <textarea
                className="textarea"
                placeholder="Describe your video idea in detail..."
                value={idea}
                onChange={(e) => setIdea(e.target.value)}
                rows={6}
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="label">Visual Style</label>
                <select 
                  className="input"
                  value={style}
                  onChange={(e) => setStyle(e.target.value)}
                >
                  <option value="cinematic">Cinematic</option>
                  <option value="anime">Anime</option>
                  <option value="realistic">Realistic</option>
                  <option value="cartoon">Cartoon</option>
                </select>
              </div>

              <div className="form-group">
                <label className="label">Target Duration</label>
                <select 
                  className="input"
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                >
                  <option value="15">15 seconds</option>
                  <option value="30">30 seconds</option>
                  <option value="60">1 minute</option>
                </select>
              </div>
            </div>

            <button 
              type="submit" 
              className="btn btn-primary btn-full"
              disabled={!idea.trim()}
            >
              Generate Outline
            </button>
          </form>
        </div>
      )}

      {workflow.step === 'outline' && workflow.status === 'ready' && workflow.outline && (
        <div className="card step-content">
          <h2>Story Outline</h2>
          <div className="outline-content">
            <div className="outline-header">
              <h3>{workflow.outline.title}</h3>
              <span className="genre-badge">{workflow.outline.genre}</span>
            </div>
            
            <div className="outline-section">
              <h4>Synopsis</h4>
              <p>{workflow.outline.synopsis}</p>
            </div>

            <div className="outline-section">
              <h4>Characters</h4>
              <div className="character-list-simple">
                {workflow.outline.characters_summary?.map((char, index) => (
                  <div key={index} className="character-item-simple">
                    <strong>{char.name}</strong> - {char.role}
                  </div>
                ))}
              </div>
            </div>

            <div className="outline-section">
              <h4>Plot Points</h4>
              <div className="plot-list">
                {workflow.outline.plot_summary?.map((plot, index) => (
                  <div key={index} className="plot-item">
                    <span className="plot-number">{index + 1}</span>
                    <div>
                      <strong>{plot.scene}</strong>
                      <p>{plot.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="step-actions">
            <button className="btn btn-secondary" onClick={handleReset}>Start Over</button>
            <button className="btn btn-primary" onClick={handleConfirmOutline}>
              Confirm & Generate Characters
            </button>
          </div>
        </div>
      )}

      {workflow.step === 'characters' && workflow.status === 'ready' && (
        <div className="card step-content">
          <h2>Characters</h2>
          <div className="characters-grid">
            {workflow.characters.map((char) => (
              <div key={char.id} className="character-card">
                {char.image_url && (
                  <img 
                    src={char.image_url} 
                    alt={char.name}
                    className="character-image"
                  />
                )}
                <div className="character-info">
                  <h3>{char.name}</h3>
                  <span className="role-badge">{char.role}</span>
                  <p>{char.description}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="step-actions">
            <button className="btn btn-secondary" onClick={handleReset}>Start Over</button>
            <button className="btn btn-primary" onClick={handleConfirmCharacters}>
              Confirm & Generate Storyboard
            </button>
          </div>
        </div>
      )}

      {workflow.step === 'storyboard' && workflow.status === 'ready' && (
        <div className="card step-content">
          <h2>Storyboard</h2>
          <div className="storyboard-grid">
            {workflow.storyboard.map((shot) => (
              <div key={shot.id} className="shot-card">
                {shot.image_url && (
                  <img 
                    src={shot.image_url} 
                    alt={`Shot ${shot.shot_number}`}
                    className="shot-image"
                  />
                )}
                <div className="shot-info">
                  <span className="shot-number">Shot {shot.shot_number}</span>
                  <p>{shot.description}</p>
                  <span className="camera-angle">{shot.camera_angle}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="step-actions">
            <button className="btn btn-secondary" onClick={handleReset}>Start Over</button>
            <button className="btn btn-primary" onClick={handleConfirmStoryboard}>
              Confirm & Generate Video
            </button>
          </div>
        </div>
      )}

      {(workflow.step === 'video' || workflow.step === 'completed') && workflow.status === 'ready' && (
        <div className="card step-content">
          <h2>Your Video is Ready!</h2>
          <div className="video-preview">
            {workflow.videoUrl && (
              <video 
                controls 
                src={workflow.videoUrl}
                className="video-player"
              >
                Your browser does not support video playback.
              </video>
            )}
          </div>
          <div className="step-actions">
            <button className="btn btn-secondary" onClick={handleReset}>Create Another</button>
            {workflow.videoUrl && (
              <a href={workflow.videoUrl} download className="btn btn-primary">
                Download Video
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default Idea2Video
