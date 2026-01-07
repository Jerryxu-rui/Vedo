# ViMax Minimal Base System

This is a minimal package containing only the essential code to run ViMax.

## Package Contents

- Core pipeline files (idea2video, script2video)
- API server and routes
- Essential agents and tools
- Configuration files
- Database models and services

## Quick Start

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Configure your API keys in `configs/idea2video.yaml` and `configs/script2video.yaml`

3. Run the API server:
   ```bash
   chmod +x start_api_server.sh
   ./start_api_server.sh
   ```

4. Or run directly:
   ```bash
   # For idea to video
   uv run python main_idea2video.py --idea "Your idea here"
   
   # For script to video
   uv run python main_script2video.py
   ```

## Configuration

Edit the following files to configure your API keys:
- `configs/idea2video.yaml` - Configuration for idea2video pipeline
- `configs/script2video.yaml` - Configuration for script2video pipeline

Required API keys:
- Chat model API key (e.g., OpenAI, Google Gemini)
- Image generator API key
- Video generator API key

## Documentation

For full documentation, visit: https://github.com/HKUDS/ViMax

## Package Size

This minimal package excludes:
- Test files
- Documentation files (except essential guides)
- Frontend assets
- Backup files
- Cache and temporary files
- Large binary files

Total package size: < 100MB (optimized for quick deployment)

## License

MIT License - See LICENSE file for details
