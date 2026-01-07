# ViMax Quick Start Guide

## Starting the Application

### 1. Start the Backend API Server

The backend API server provides character management and video generation endpoints.

```bash
# Start the test API server (lightweight, no video pipeline dependencies)
python3 test_api_server.py
```

The server will start on `http://localhost:3001`

**Note**: The full `api_server.py` requires additional dependencies (scenedetect, etc.). Use `test_api_server.py` for character management features.

### 2. Start the Frontend Development Server

In a new terminal:

```bash
cd frontend
npm run dev
```

The frontend will start on `http://localhost:5173`

### 3. Access the Application

Open your browser and navigate to: `http://localhost:5173`

## Available Features

### Navigation Menu
- **Explore** - Browse video gallery
- **Create** - Generate videos from ideas or scripts
- **Chat** - Natural language video creation assistant
- **Characters** - Manage characters with consistency tracking
- **Library** - View all your generated videos

### Character Management
1. Click "Characters" in the navigation
2. Click "Create Character" to add a new character
3. Fill in character details:
   - Basic info (name, description, role, age, gender)
   - Personality traits
   - Appearance (hair, eyes, skin, height, build)
   - Distinctive features
4. Save and manage your characters

### Video Generation
1. Click "Create" in the navigation
2. Choose mode:
   - **Idea to Video**: Describe your concept
   - **Script to Video**: Provide a detailed script
3. Fill in the form and click "Generate Video"
4. Monitor progress in real-time
5. View results in the Library

### Chat Interface
1. Click "Chat" in the navigation
2. Type natural language commands:
   - "Create a video about..."
   - "Make shot 1 brighter"
   - "Change the background to blue"
3. Get AI-powered assistance

## Running Tests

### Character System Tests

```bash
# Run automated character management tests
./run_character_tests.sh
```

This will:
1. Start the test API server
2. Run 7 automated tests
3. Display results
4. Stop the server

## Troubleshooting

### Port Already in Use

If port 3001 is already in use:

```bash
# Kill existing server
pkill -f "python.*api_server"

# Start fresh
python3 test_api_server.py
```

### Frontend Connection Issues

If the frontend can't connect to the backend:

1. Check if the API server is running:
   ```bash
   curl http://localhost:3001/health
   ```

2. Verify the API URL in frontend:
   - Check `frontend/.env` or `frontend/src/services/api.ts`
   - Should be `http://localhost:3001`

### Missing Dependencies

If you see import errors:

```bash
# Install Python dependencies
pip install fastapi uvicorn pydantic requests

# Install frontend dependencies
cd frontend
npm install
```

## Development Workflow

### Making Changes

1. **Backend Changes**:
   - Edit files in `services/`, `models/`, or `test_api_server.py`
   - Restart the API server
   - Test with `./run_character_tests.sh`

2. **Frontend Changes**:
   - Edit files in `frontend/src/`
   - Vite will hot-reload automatically
   - Check browser console for errors

### Testing

```bash
# Backend tests
./run_character_tests.sh

# Frontend (if tests exist)
cd frontend
npm test
```

## API Endpoints

### Character Management
- `GET /health` - Health check
- `POST /api/v1/characters` - Create character
- `GET /api/v1/characters` - List characters
- `GET /api/v1/characters/{id}` - Get character
- `PUT /api/v1/characters/{id}` - Update character
- `DELETE /api/v1/characters/{id}` - Delete character
- `GET /api/v1/characters/{id}/consistency` - Consistency report
- `POST /api/v1/characters/extract` - Extract from script

### Video Generation (Full API Server)
- `POST /api/v1/generate/idea2video` - Generate from idea
- `POST /api/v1/generate/script2video` - Generate from script
- `GET /api/v1/jobs/{id}` - Get job status
- `GET /api/v1/jobs` - List all jobs

## Project Structure

```
ViMax/
├── test_api_server.py          # Lightweight API server
├── api_server.py                # Full API server (requires deps)
├── run_character_tests.sh       # Test runner
├── test_character_system.py     # Automated tests
├── services/                    # Business logic
│   ├── character_service.py
│   └── nlp_service.py
├── models/                      # Data models
│   └── character.py
└── frontend/                    # React frontend
    ├── src/
    │   ├── pages/              # Page components
    │   ├── components/         # Reusable components
    │   └── services/           # API integration
    └── package.json
```

## Next Steps

1. **Explore the Characters page** - Create and manage characters
2. **Try the Chat interface** - Use natural language commands
3. **Generate a video** - Test the video creation workflow
4. **Run the tests** - Verify everything works

## Support

For issues or questions:
1. Check the documentation in `PHASE2_CHARACTER_SYSTEM_COMPLETE.md`
2. Review test results in `CHARACTER_SYSTEM_TEST_RESULTS.md`
3. Check server logs: `tail -f /tmp/test_api_server.log`

---

**Current Status**: Phase 2 Complete - Character Management System Fully Functional ✅