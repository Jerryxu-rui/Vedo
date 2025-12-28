import { Link } from 'react-router-dom'
import './Home.css'

function Home() {
  return (
    <div className="container">
      <section className="hero">
        <h1 className="hero-title">
          Transform Your Ideas into
          <span className="gradient-text"> Amazing Videos</span>
        </h1>
        <p className="hero-subtitle">
          ViMax is your AI-powered video production studio. From creative concepts to polished videos, 
          our intelligent agents handle everything - scripting, character design, and video generation.
        </p>
        <div className="hero-actions">
          <Link to="/idea2video" className="btn btn-primary">
            Start with an Idea
          </Link>
          <Link to="/script2video" className="btn btn-secondary">
            Upload a Script
          </Link>
        </div>
      </section>

      <section className="features">
        <h2 className="section-title">How It Works</h2>
        <div className="feature-grid">
          <div className="feature-card">
            <div className="feature-icon">1</div>
            <h3>Share Your Vision</h3>
            <p>Describe your video idea or upload an existing script. Our AI understands your creative intent.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">2</div>
            <h3>AI Takes Over</h3>
            <p>Our specialized agents develop scripts, design characters, and create storyboards automatically.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">3</div>
            <h3>Generate Video</h3>
            <p>Watch as your video comes to life with consistent characters and professional-quality output.</p>
          </div>
        </div>
      </section>

      <section className="capabilities">
        <h2 className="section-title">Platform Capabilities</h2>
        <div className="capability-grid">
          <div className="capability-item">
            <span className="capability-check">✓</span>
            <span>Idea to Video Generation</span>
          </div>
          <div className="capability-item">
            <span className="capability-check">✓</span>
            <span>Script to Video Conversion</span>
          </div>
          <div className="capability-item">
            <span className="capability-check">✓</span>
            <span>Character Consistency</span>
          </div>
          <div className="capability-item">
            <span className="capability-check">✓</span>
            <span>Multi-Episode Series</span>
          </div>
          <div className="capability-item">
            <span className="capability-check">✓</span>
            <span>Real-time Progress Tracking</span>
          </div>
          <div className="capability-item">
            <span className="capability-check">✓</span>
            <span>Shot-by-Shot Control</span>
          </div>
        </div>
      </section>
    </div>
  )
}

export default Home
