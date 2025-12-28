import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './Home.css'

function Home() {
  const [idea, setIdea] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!idea.trim()) return

    setIsSubmitting(true)
    
    localStorage.setItem('vimax_idea', idea)
    navigate('/idea2video')
  }

  const handleScriptUpload = () => {
    navigate('/script2video')
  }

  return (
    <div className="container">
      <section className="hero">
        <h1 className="hero-title">
          Transform Your Ideas into
          <span className="gradient-text"> Amazing Videos</span>
        </h1>
        <p className="hero-subtitle">
          ViMax is your AI-powered video production studio. Describe your creative vision 
          and our intelligent agents will generate scripts, characters, and complete videos.
        </p>
      </section>

      <section className="idea-input-section">
        <div className="card idea-card">
          <form onSubmit={handleSubmit}>
            <div className="idea-input-wrapper">
              <textarea
                className="idea-textarea"
                placeholder="Describe your video idea... For example: 'A magical forest where glowing butterflies guide a lost child home at sunset. The atmosphere should be dreamlike with soft golden light filtering through ancient trees.'"
                value={idea}
                onChange={(e) => setIdea(e.target.value)}
                rows={4}
              />
            </div>
            <div className="idea-actions">
              <button 
                type="submit" 
                className="btn btn-primary"
                disabled={!idea.trim() || isSubmitting}
              >
                Generate Video from Idea
              </button>
              <span className="or-divider">or</span>
              <button 
                type="button"
                className="btn btn-secondary"
                onClick={handleScriptUpload}
              >
                Upload Existing Script
              </button>
            </div>
          </form>
        </div>
      </section>

      <section className="workflow-section">
        <h2 className="section-title">How It Works</h2>
        <div className="workflow-steps">
          <div className="workflow-step">
            <div className="step-number">1</div>
            <div className="step-content">
              <h3>Share Your Vision</h3>
              <p>Enter your creative idea or upload an existing script</p>
            </div>
          </div>
          <div className="workflow-arrow">→</div>
          <div className="workflow-step">
            <div className="step-number">2</div>
            <div className="step-content">
              <h3>AI Script Generation</h3>
              <p>Review and confirm the generated script outline</p>
            </div>
          </div>
          <div className="workflow-arrow">→</div>
          <div className="workflow-step">
            <div className="step-number">3</div>
            <div className="step-content">
              <h3>Characters & Scenes</h3>
              <p>AI creates character portraits and scene designs</p>
            </div>
          </div>
          <div className="workflow-arrow">→</div>
          <div className="workflow-step">
            <div className="step-number">4</div>
            <div className="step-content">
              <h3>Storyboard & Video</h3>
              <p>Shot-by-shot storyboard and final video generation</p>
            </div>
          </div>
        </div>
      </section>

      <section className="features-section">
        <div className="feature-grid">
          <div className="feature-card">
            <div className="feature-icon">🎬</div>
            <h3>Idea to Video</h3>
            <p>Transform any creative concept into a polished video with AI-generated script and visuals</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📝</div>
            <h3>Script to Video</h3>
            <p>Upload your script and watch it come to life with consistent characters</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">👥</div>
            <h3>Character Consistency</h3>
            <p>AI maintains visual consistency for characters across all scenes</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🎯</div>
            <h3>Shot-by-Shot Control</h3>
            <p>Review detailed storyboards with camera movements and composition</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📺</div>
            <h3>Multi-Episode Series</h3>
            <p>Create entire video series with consistent storytelling</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">⚡</div>
            <h3>Real-time Progress</h3>
            <p>Track generation progress with live updates</p>
          </div>
        </div>
      </section>
    </div>
  )
}

export default Home
