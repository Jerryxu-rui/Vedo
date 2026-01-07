<div align="center">
  <h1 align="center">Vedo: Conversational Video Generation Platform</h1>

  <div align="center">
  </div>

  <p align="center">
    <img src="https://img.shields.io/badge/🐍Python-3.12-00d9ff?style=for-the-badge&logo=python&logoColor=white&labelColor=1a1a2e">
	<a href="https://github.com/astral-sh/uv"><img src="https://img.shields.io/badge/⚡uv-Ready-ff6b6b?style=for-the-badge&logo=python&logoColor=white&labelColor=1a1a2e"></a>
	<img src="https://img.shields.io/badge/License-MIT-4ecdc4?style=for-the-badge&logo=opensourceinitiative&logoColor=white" alt="MIT License">
  </p>

  <p align="center">
    <a href="https://github.com/Jerryxu-rui/Vedo"><img src="https://img.shields.io/github/stars/Jerryxu-rui/Vedo?style=social" alt="GitHub stars"></a>
    <a href="https://github.com/Jerryxu-rui/Vedo/issues"><img src="https://img.shields.io/github/issues/Jerryxu-rui/Vedo" alt="GitHub issues"></a>
    <a href="https://github.com/Jerryxu-rui/Vedo/commits/main"><img src="https://img.shields.io/github/last-commit/Jerryxu-rui/Vedo" alt="GitHub last commit"></a>
  </p>

</div>

---

## 🎬 What is Vedo?

**Vedo** is an advanced conversational video generation platform that transforms ideas, scripts, and novels into complete video productions through intelligent multi-agent workflows. Built with a modern architecture featuring WebSocket-based real-time communication, A2A (Agent-to-Agent) coordination, and a responsive React/TypeScript frontend.

### ✨ Key Features

- **💬 Conversational Interface**: Natural language interaction for video creation
- **🤖 Multi-Agent Orchestration**: Specialized agents for scriptwriting, storyboarding, character design, and video generation
- **🌐 Real-time Progress Tracking**: WebSocket-based live updates on generation progress
- **🎨 Multiple Generation Modes**:
  - **Idea2Video**: Transform raw ideas into complete videos
  - **Script2Video**: Convert screenplay scripts into visual narratives
  - **Novel2Video**: Adapt complete novels into episodic content
- **🔗 API-First Design**: RESTful and WebSocket APIs for integration
- **⚡ Modern Stack**: Python backend with FastAPI, React/TypeScript frontend, uv for dependency management

---

## 🎥 Video Demonstrations

Vedo generates high-quality videos from simple ideas, scripts, and novels. Here are some examples of videos created by the platform:

<table>
<tr>
<td align="center" width="33%">
  <strong>Idea2Video Example</strong><br/>
  <em>"A cat and dog become best friends"</em><br/>
  <small>Children's cartoon style, 3 scenes</small>
</td>
<td align="center" width="33%">
  <strong>Script2Video Example</strong><br/>
  <em>School basketball scene</em><br/>
  <small>Animated style, dynamic camera angles</small>
</td>
<td align="center" width="33%">
  <strong>Novel2Video Example</strong><br/>
  <em>Fantasy adventure adaptation</em><br/>
  <small>Episodic content, character consistency</small>
</td>
</tr>
<tr>
<td align="center" width="33%">
  <!-- Video placeholder 1 -->
  <div style="background: #1a1a2e; padding: 20px; border-radius: 10px; color: white;">
    🎬 Video Example 1<br/>
    <small>Upload to video hosting service<br/>and embed URL here</small>
  </div>
</td>
<td align="center" width="33%">
  <!-- Video placeholder 2 -->
  <div style="background: #1a1a2e; padding: 20px; border-radius: 10px; color: white;">
    🎬 Video Example 2<br/>
    <small>Upload to video hosting service<br/>and embed URL here</small>
  </div>
</td>
<td align="center" width="33%">
  <!-- Video placeholder 3 -->
  <div style="background: #1a1a2e; padding: 20px; border-radius: 10px; color: white;">
    🎬 Video Example 3<br/>
    <small>Upload to video hosting service<br/>and embed URL here</small>
  </div>
</td>
</tr>
</table>

*Note: Actual video files are generated in the `.working_dir` directory during operation. To showcase videos in this README, upload them to a video hosting service (YouTube, Vimeo, etc.) and replace the placeholders with embedded video links.*

---

## 🏗️ Architecture Overview

Vedo follows a modular, service-oriented architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React/TypeScript)              │
│                    Real-time WebSocket Dashboard            │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                    API Gateway (FastAPI)                    │
│          REST Endpoints • WebSocket Connections             │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                Conversational Orchestrator                  │
│         Intent Analysis • Workflow Management               │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌───────────────┬──────────────┬──────────────┬──────────────┐
│               │              │              │              │
▼               ▼              ▼              ▼              ▼
┌──────────────┐┌─────────────┐┌─────────────┐┌─────────────┐┌─────────────┐
│   Script     ││ Storyboard  ││  Character  ││   Scene     ││   Video     │
│   Agents     ││   Agents    ││   Agents    ││   Agents    ││  Generator  │
└──────────────┘└─────────────┘└─────────────┘└─────────────┘└─────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for Python dependency management
- Node.js 18+ (for frontend development)
- API keys for LLM services (OpenAI, Google Gemini, etc.)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Jerryxu-rui/Vedo.git
   cd Vedo
   ```

2. **Set up Python environment**
   ```bash
   uv sync
   source .venv/bin/activate  # On Unix/macOS
   # or .venv\Scripts\activate on Windows
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Set up frontend** (optional, for development)
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

5. **Run the backend server**
   ```bash
   python api_server.py
   ```
   The API server will start at `http://localhost:8000`

6. **Access the frontend**
   Open `frontend/index.html` in your browser or serve it with a local server.

### Configuration

Edit `configs/idea2video.yaml` or `configs/script2video.yaml` to configure your preferred LLM providers and API keys:

```yaml
chat_model:
  init_args:
    model: google/gemini-2.5-flash-lite-preview-09-2025
    model_provider: openai
    api_key: <YOUR_API_KEY>
    base_url: https://openrouter.ai/api/v1

image_generator:
  class_path: tools.ImageGeneratorNanobananaGoogleAPI
  init_args:
    api_key: <YOUR_API_KEY>

video_generator:
  class_path: tools.VideoGeneratorVeoGoogleAPI
  init_args:
    api_key: <YOUR_API_KEY>
```

---

## 📖 Usage Examples

### 1. Idea to Video
```python
from main_idea2video import generate_video_from_idea

idea = "A cat and dog become best friends and have adventures together"
user_requirement = "Create a children's cartoon with 3 scenes"
style = "Cartoon"

result = generate_video_from_idea(idea, user_requirement, style)
```

### 2. Script to Video
```python
from main_script2video import generate_video_from_script

script = """
EXT. PARK - DAY
A cat and dog play together near a fountain.
CAT: (purring) This is fun!
DOG: (wagging tail) Best day ever!
"""

user_requirement = "Fast-paced with dynamic camera angles"
style = "Animated"

result = generate_video_from_script(script, user_requirement, style)
```

### 3. Web Interface
Access the web interface at `http://localhost:8000` (after starting the API server) to use the conversational interface for video generation.

---

## 🔧 Project Structure

```
Vedo/
├── api_server.py              # Main FastAPI server
├── api_routes_*.py           # Various API route modules
├── services/                 # Business logic services
│   ├── chat_service.py       # Conversational chat service
│   ├── a2a_agent_coordinator.py  # Agent coordination
│   └── intent_analyzer.py    # LLM-based intent analysis
├── agents/                   # Specialized agent implementations
│   ├── screenwriter.py       # Script writing agent
│   ├── storyboard_artist.py  # Storyboard generation
│   └── character_extractor.py # Character design
├── frontend/                 # React/TypeScript frontend
│   ├── src/
│   │   ├── pages/           # Page components
│   │   ├── components/      # Reusable UI components
│   │   └── hooks/           # Custom React hooks
├── configs/                  # Configuration files
├── tools/                    # External API integrations
└── utils/                    # Utility functions
```

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with cutting-edge AI models and APIs
- Inspired by the creative potential of generative AI
- Thanks to all contributors and the open-source community

---

<p align="center">
  <strong>🌟 If you find Vedo useful, please give us a star on GitHub!</strong>
</p>

<p align="center">
  <em>Transform your ideas into videos with Vedo 🎬</em>
</p>
