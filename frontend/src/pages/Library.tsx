import { useState, useEffect } from 'react'
import './Library.css'

interface VideoItem {
  id: string
  title: string
  created_at: string
  status: string
  duration?: number
  thumbnail?: string
}

function Library() {
  const [videos, setVideos] = useState<VideoItem[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    fetchVideos()
  }, [])

  const fetchVideos = async () => {
    try {
      const seriesResponse = await fetch('/api/v1/seko/series')
      if (seriesResponse.ok) {
        const seriesList = await seriesResponse.json()
        const videoList: VideoItem[] = []
        
        for (const series of seriesList || []) {
          const episodesResponse = await fetch(`/api/v1/seko/series/${series.id}/episodes`)
          if (episodesResponse.ok) {
            const episodes = await episodesResponse.json()
            for (const episode of episodes || []) {
              videoList.push({
                id: episode.id,
                title: episode.title || `${series.title} - 第${episode.episode_number}集`,
                created_at: episode.created_at,
                status: episode.status,
                duration: episode.duration
              })
            }
          }
        }
        
        videoList.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        setVideos(videoList)
      }
    } catch (error) {
      console.error('Failed to fetch videos:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredVideos = videos.filter(video => {
    if (filter === 'all') return true
    return video.status === filter
  })

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  return (
    <div className="container">
      <div className="page-header">
        <h1>Video Library</h1>
        <p>Browse and manage your generated videos</p>
      </div>

      <div className="library-controls">
        <div className="filter-tabs">
          <button 
            className={`filter-tab ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All Videos
          </button>
          <button 
            className={`filter-tab ${filter === 'completed' ? 'active' : ''}`}
            onClick={() => setFilter('completed')}
          >
            Completed
          </button>
          <button 
            className={`filter-tab ${filter === 'processing' ? 'active' : ''}`}
            onClick={() => setFilter('processing')}
          >
            Processing
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading your videos...</p>
        </div>
      ) : filteredVideos.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🎬</div>
          <h3>No videos yet</h3>
          <p>Create your first video using Idea to Video or Script to Video</p>
        </div>
      ) : (
        <div className="video-grid">
          {filteredVideos.map(video => (
            <div key={video.id} className="video-card">
              <div className="video-thumbnail">
                {video.thumbnail ? (
                  <img src={video.thumbnail} alt={video.title} />
                ) : (
                  <div className="thumbnail-placeholder">
                    <span>🎥</span>
                  </div>
                )}
                <div className={`video-status-badge ${video.status}`}>
                  {video.status}
                </div>
              </div>
              <div className="video-info">
                <h4>{video.title}</h4>
                <p className="video-date">{formatDate(video.created_at)}</p>
                {video.duration && (
                  <p className="video-duration">{Math.round(video.duration)}s</p>
                )}
              </div>
              <div className="video-actions">
                {video.status === 'completed' && (
                  <>
                    <a 
                      href={`/api/v1/videos/episode/${video.id}/stream`}
                      className="btn btn-secondary btn-sm"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Preview
                    </a>
                    <a 
                      href={`/api/v1/videos/episode/${video.id}/download`}
                      className="btn btn-primary btn-sm"
                    >
                      Download
                    </a>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default Library
