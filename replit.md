# ViMax - Agentic Video Generation Platform

## Overview

ViMax is an AI-powered video generation platform that transforms ideas and scripts into complete videos. It functions as an all-in-one Director, Screenwriter, Producer, and Video Generator. The system uses a multi-agent architecture where specialized AI agents handle different aspects of video production - from script development to character extraction to final video generation.

The platform supports two main workflows:
- **Idea2Video**: Transform a creative idea into a complete video with automatically generated script, characters, and scenes
- **Script2Video**: Convert an existing script into video with character consistency and visual continuity

## User Preferences

Preferred communication style: Simple, everyday language.

## Running the Application

The application consists of two parts:
1. **Backend API** (Python/FastAPI) - Runs on port 3001
2. **Frontend** (React/Vite) - Runs on port 5000 (user-facing)

### Workflows
- `API Server`: `python api_server.py` - Starts the backend API on port 3001
- `Frontend`: `cd frontend && npm run dev` - Starts the React frontend on port 5000

### Required Environment Variables
- `YUNWU_API_KEY` - API key for Yunwu.ai services (image/video generation)
- `DATABASE_URL` - PostgreSQL connection string (optional, defaults to SQLite)
- `CORS_ORIGINS` - Comma-separated list of allowed origins (optional, defaults to "*")

## System Architecture

### Backend Architecture (Python/FastAPI)

The backend uses FastAPI with a modular architecture:

- **API Layer**: Multiple route modules handle different concerns:
  - `api_server.py` - Main server with character management and chat endpoints (port 3001)
  - `seko_api_routes.py` - Series/Episode/Character management for multi-episode support
  - `api_routes_conversational.py` - Conversational workflow for step-by-step video generation
  - `api_routes_direct_pipeline.py` - Direct pipeline execution endpoints
  - `api_routes_websocket.py` - Real-time progress updates via WebSocket
  - `api_routes_video.py` - Video download and preview management

- **Pipeline Layer** (`pipelines/`):
  - `Idea2VideoPipeline` - End-to-end idea to video conversion
  - `Script2VideoPipeline` - Script-based video generation with character consistency
  - Pipelines are configured via YAML files in `configs/`

- **Agent Layer** (`agents/`): Specialized AI agents for different tasks:
  - `Screenwriter` - Story development from ideas
  - `CharacterExtractor` - Extract character information from scripts
  - `CharacterPortraitsGenerator` - Generate consistent character portraits
  - `StoryboardArtist` - Design shot-by-shot storyboards
  - `CameraImageGenerator` - Generate images with camera consistency
  - `ReferenceImageSelector` - Select best reference images for consistency

- **Tools Layer** (`tools/`): External API integrations for media generation:
  - Image generators (Doubao Seedream, Nanobanana/Gemini via Yunwu or Google API)
  - Video generators (Doubao Seedance, Veo via Yunwu or Google API)
  - All tools support custom API routers (base_url configuration)

### Database Layer

- **SQLAlchemy ORM** with PostgreSQL (default) or SQLite fallback
- **Models** (`database_models.py`):
  - `Series` - Multi-episode video series
  - `Episode` - Individual episodes within a series
  - `Scene` - Scenes within episodes
  - `Shot` - Individual shots with generation status
  - `Character` - Character profiles with appearance tracking
  - `CharacterShot` - Character-to-shot assignments for consistency
  - `GenerationProgress` - Track generation status

### Frontend Architecture (React/TypeScript/Vite)

Located in `frontend/` directory:
- React 18 with TypeScript
- Vite 5 as build tool with React Router v6
- Modern dark theme UI with gradient accents
- Pages:
  - **Home** - Main landing with idea input and workflow overview
  - **Idea to Video** - Enter creative ideas, select style/duration, generate video
  - **Script to Video** - Upload or paste scripts for video generation
  - **Library** - Browse and manage generated videos
- Proxies API calls to backend on port 3001

### Key Design Patterns

1. **Agent-based Architecture**: Each AI task is handled by a specialized agent class that encapsulates prompts, LLM interactions, and output parsing

2. **Pipeline Pattern**: Complex workflows are composed of sequential agent calls with caching support

3. **Dependency Injection**: Configuration is loaded from YAML files; tools and models are instantiated dynamically via `importlib`

4. **Rate Limiting**: Built-in rate limiters for API calls with configurable requests per minute/day

5. **Retry with Tenacity**: All external API calls use tenacity for automatic retries

6. **Character Consistency Engine**: `CharacterConsistencyEngine` injects character descriptions and reference images into generation prompts

## External Dependencies

### AI/ML APIs
- **LangChain**: Chat model abstraction and prompt management
- **OpenAI-compatible APIs**: Chat models via custom routers (configurable base_url)
- **Google Gemini**: Image generation via `google-genai` package (optional)
- **Yunwu API** (yunwu.ai): Primary API router for image/video generation
  - Doubao Seedream (image generation)
  - Doubao Seedance (video generation)
  - Veo (video generation)

### Media Processing
- **MoviePy**: Video concatenation and editing
- **OpenCV (cv2)**: Image/video frame processing
- **Pillow (PIL)**: Image handling
- **scenedetect**: Scene detection in videos

### Database
- **SQLAlchemy**: ORM for database operations
- **PostgreSQL**: Default database via psycopg2-binary
- **SQLite**: Fallback database option

### Web Framework
- **FastAPI**: REST API with async support
- **WebSocket**: Real-time progress updates via `utils/websocket_manager.py`
- **Pydantic**: Request/response validation with modern `.model_dump()` syntax

### Package Management
- **uv**: Python package manager (uv sync for dependencies)
- **npm**: Frontend package management

### Configuration Files
- `configs/idea2video.yaml` - Idea2Video pipeline configuration
- `configs/script2video.yaml` - Script2Video pipeline configuration
- Required API keys: Set via `YUNWU_API_KEY` environment variable

## Recent Changes

- **Granular Editing Endpoints** (Dec 28, 2025):
  - Added individual edit/regenerate/delete endpoints for characters, scenes, and shots
  - Characters: PATCH `/episode/{id}/characters/{char_id}` (edit), POST `.../regenerate` (regenerate image), DELETE
  - Scenes: PATCH `/episode/{id}/scenes/{scene_id}` (edit), POST `.../regenerate` (regenerate image), DELETE
  - Shots: PATCH `/episode/{id}/shots/{shot_id}` (edit), DELETE
  - Updated batch generation logic to check existing count before deleting (incremental mode)
  - Added `generate_character_portrait()` and `generate_scene_image()` helper methods to PipelineAdapter
- **Draft Resume Feature** (Dec 28, 2025):
  - Added `load_or_create_from_db` method to WorkflowManager for persistent workflow state restoration
  - Workflow state now restored from database on server restart, including outline, characters, scenes, storyboard, and video path
  - Frontend Idea2Video now detects `?episode` query parameter and restores previous progress
  - Users can click "继续编辑" (Continue Editing) in Library to resume draft projects
  - API keys moved to environment variable `${YUNWU_API_KEY}` in config files for security
- Redesigned Idea2Video page to match reference UI with split-panel studio layout:
  - Episode sidebar on far left for multi-episode management
  - Navigation sidebar with icon tabs (画面/配音/音乐)
  - Chat panel with AI assistant (Seko) conversation and workflow checklist
  - Dynamic content panel on right for previewing outline, characters, scenes, storyboard, and video
- Added Chinese localization for workflow labels
- Implemented storyboard view with shot timeline and playback controls
- Added robust state polling with lowercase normalization to handle enum format variations
- Fixed video URL extraction with fallback chain (video_path or step_info.video.path)
- Fixed character portrait generator bug with None values for dynamic_features
- Added scenes step to match backend workflow requirements
- Added React frontend with modern dark theme UI
- Fixed file upload handling with aiofiles
- Updated to Pydantic v2 conventions (.model_dump())
- Added PostgreSQL support with psycopg2-binary
- Configured CORS for flexible origin handling
