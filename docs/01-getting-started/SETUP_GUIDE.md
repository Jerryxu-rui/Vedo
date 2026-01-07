# ViMax Setup and Running Guide

## ✅ Installation Complete

The project has been successfully set up with:
- Python 3.12.12 virtual environment (`.venv`)
- All 72 dependencies installed
- Bug fixes applied to error handling code
- **Configured for custom API router: https://api.maoai.vip**

## 🔧 Configuration Status

✅ **Already Configured!** The project is set up to use your custom API router at `https://api.maoai.vip/v1`

### API Configuration

The configuration files have been updated to use:
- **Chat Model**: OpenAI-compatible API via your custom router
- **Image Generator**: YunwuAPI implementation (supports custom base_url)
- **Video Generator**: YunwuAPI implementation (supports custom base_url)

Your API key is already configured in both config files.

### What Was Changed

1. **Image Generator**: Changed from `ImageGeneratorNanobananaGoogleAPI` to `ImageGeneratorNanobananaYunwuAPI`
   - Added `base_url: https://api.maoai.vip`
   - Added `api_version: v1`

2. **Video Generator**: Changed from `VideoGeneratorVeoGoogleAPI` to `VideoGeneratorVeoYunwuAPI`
   - Added `base_url: https://api.maoai.vip`

3. **Chat Model**: Already configured with your custom base_url
   - `base_url: https://api.maoai.vip/v1`

## 🚀 Running the Project

### Option 1: Idea to Video

Transform a simple idea into a complete video:

```bash
uv run python main_idea2video.py
```

**Customize your idea** by editing `main_idea2video.py`:

```python
idea = """
Your creative idea here...
"""

user_requirement = """
For adults, do not exceed 3 scenes. Each scene should be no more than 5 shots.
"""

style = "Realistic, warm feel"
```

### Option 2: Script to Video

Generate video from a screenplay:

```bash
uv run python main_script2video.py
```

**Customize your script** by editing `main_script2video.py`:

```python
script = """
EXT. LOCATION - TIME
Your screenplay here...
"""

user_requirement = """
Fast-paced with no more than 15 shots.
"""

style = "Anime Style"
```

## 🐛 Bug Fixes Applied

1. **Fixed `AttributeError` in error handling code:**
   - ✅ `tools/image_generator_nanobanana_google_api.py` - Fixed ClientError.status_code → ClientError.code
   - ✅ `tools/video_generator_veo_google_api.py` - Fixed ClientError.status_code → ClientError.code

2. **Enhanced Yunwu API implementations to support custom base URLs:**
   - ✅ `tools/image_generator_nanobanana_yunwu_api.py` - Added base_url and api_version parameters
   - ✅ `tools/video_generator_veo_yunwu_api.py` - Added base_url parameter

3. **Updated configuration files:**
   - ✅ `configs/idea2video.yaml` - Switched to YunwuAPI implementations with custom base_url
   - ✅ `configs/script2video.yaml` - Switched to YunwuAPI implementations with custom base_url

## 📁 Project Structure

```
ViMax/
├── agents/              # AI agents for different tasks
├── configs/             # Configuration files (API keys here!)
├── interfaces/          # Data structures
├── pipelines/           # Main processing pipelines
├── tools/               # API integrations
├── utils/               # Helper utilities
├── main_idea2video.py   # Entry point for idea→video
├── main_script2video.py # Entry point for script→video
└── .venv/               # Python virtual environment
```

## 💡 Features

### 🌟 Idea2Video
- Transform raw ideas into complete video stories
- Automated scriptwriting, storyboarding, and character design
- End-to-end video generation

### ⚙️ Script2Video
- Generate videos from any screenplay
- Complete control over narrative and visual storytelling
- Professional cinematography automation

### 🎨 Novel2Video (Available)
- Adapt complete novels into episodic video content
- Intelligent narrative compression
- Character tracking across episodes

## ⚠️ Important Notes

1. **API Costs**: Video generation can be expensive. Monitor your API usage.

2. **Rate Limits**: The config files have rate limiting settings:
   - Chat model: 500 requests/min, 2000/day
   - Image generation: 10 requests/min, 500/day
   - Video generation: 2 requests/min, 10/day

3. **Processing Time**: Video generation takes time. Be patient!

4. **Output Directory**: Generated content is saved in `.working_dir/`

## 🔍 Troubleshooting

### "API key not valid" Error
- Verify your API key is valid for https://api.maoai.vip
- Check that the base_url is correctly set in the config files
- Ensure your API key has access to the required models (Gemini, image generation, video generation)

### Connection Issues
- Verify you can access https://api.maoai.vip from your network
- Check if any firewall or proxy is blocking the connection

### Import Errors
```bash
# Reinstall dependencies
uv sync --python 3.12
```

### Rate Limit Errors
- The code now properly handles rate limits with exponential backoff
- Adjust rate limits in config files if needed

## 📚 Additional Resources

- [README](readme.md) - Project overview and demos
- [中文文档](README_ZH.md) - Chinese documentation
- [Technical Report](assets/ViMax_technical_report.pdf) - Detailed technical information

## 🎬 Example Usage

```bash
# 1. Edit your API keys in configs/idea2video.yaml
# 2. Edit your idea in main_idea2video.py
# 3. Run the pipeline
uv run python main_idea2video.py

# Output will be in: .working_dir/idea2video/
```

## 🆘 Getting Help

- Check the [Communication Guide](Communication.md) for community support
- Review error logs in the terminal output
- Ensure all API keys are correctly configured

---

**Ready to create amazing videos with AI! 🎥✨**