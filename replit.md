# ViMax - Agentic Video Generation Platform

## Overview

ViMax is an AI-powered video generation platform that transforms ideas and scripts into complete videos. It functions as an all-in-one Director, Screenwriter, Producer, and Video Generator. The system uses a multi-agent architecture where specialized AI agents handle different aspects of video production - from script development to character extraction to final video generation.

The platform supports two main workflows:
- **Idea2Video**: Transform a creative idea into a complete video with automatically generated script, characters, and scenes
- **Script2Video**: Convert an existing script into video with character consistency and visual continuity

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture (Python/FastAPI)

The backend uses FastAPI with a modular architecture:

- **API Layer**: Multiple route modules handle different concerns:
  - `api_server.py` - Main server with character management and chat endpoints
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

- **SQLAlchemy ORM** with SQLite as default database
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
- React with TypeScript
- Vite as build tool
- Features: Explore, Create, Chat, Characters, Library navigation
- WebSocket integration for real-time progress updates

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
- **SQLite**: Default database (configurable via DATABASE_URL environment variable)

### Web Framework
- **FastAPI**: REST API with async support
- **WebSocket**: Real-time progress updates via `utils/websocket_manager.py`
- **Pydantic**: Request/response validation

### Package Management
- **uv**: Python package manager (uv sync for dependencies)
- **npm**: Frontend package management

### Configuration Files
- `configs/idea2video.yaml` - Idea2Video pipeline configuration
- `configs/script2video.yaml` - Script2Video pipeline configuration
- Required API keys: Chat model, Image generator, Video generator