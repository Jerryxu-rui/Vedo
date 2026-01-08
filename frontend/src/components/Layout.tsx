import { Link, Outlet, useLocation } from 'react-router-dom'
import './Layout.css'

function Layout() {
  const location = useLocation()

  const isActive = (path: string) => {
    return location.pathname === path ? 'nav-link active' : 'nav-link'
  }

  return (
    <div className="layout">
      <header className="header glass-navbar">
        <div className="container header-content">
          <Link to="/" className="logo">
            <span className="logo-icon">V</span>
            <span className="logo-text">ViMax</span>
          </Link>
          <nav className="nav">
            <Link to="/" className={isActive('/')}>Home</Link>
            <Link to="/idea2video" className={isActive('/idea2video')}>Idea to Video</Link>
            <Link to="/script2video" className={isActive('/script2video')}>Script to Video</Link>
            <Link to="/library" className={isActive('/library')}>Library</Link>
            <Link to="/agents" className={isActive('/agents')}>Agent Monitor</Link>
          </nav>
        </div>
      </header>
      <main className="main">
        <Outlet />
      </main>
      <footer className="footer">
        <div className="container">
          <p>ViMax - AI-Powered Video Generation Platform</p>
        </div>
      </footer>
    </div>
  )
}

export default Layout
