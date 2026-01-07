import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Idea2Video from './pages/Idea2Video'
import Script2Video from './pages/Script2Video'
import Library from './pages/Library'
import AgentMonitor from './pages/AgentMonitor'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="idea2video" element={<Idea2Video />} />
        <Route path="script2video" element={<Script2Video />} />
        <Route path="library" element={<Library />} />
        <Route path="agents" element={<AgentMonitor />} />
      </Route>
    </Routes>
  )
}

export default App
