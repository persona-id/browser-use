# Browser-Use API Server

A FastAPI-based REST API wrapper for the browser-use library, providing HTTP endpoints for browser automation tasks and case preloading.

## Features

- **Browser Automation**: Execute complex browser tasks using LLMs via the `/run_task` endpoint
- **Case Preloading**: Visit authenticated URLs and capture screenshots via the `/preload_case` endpoint
- **Development Mode**: Automatically save screenshots locally when `DEV_MODE=true`
- **Production Ready**: Headless Chrome with optimized settings for containerized environments
- **Health Checks**: Built-in health monitoring endpoint

## API Endpoints

### 1. Health Check
```http
GET /health
```

Returns server health status.

**Response:**
```json
{
  "status": "healthy",
  "service": "browser-use-api"
}
```

### 2. Run Browser Task
```http
POST /run_task
```

Execute a browser automation task using an LLM.

**Request Body:**
```json
{
  "task": "Find the number of stars of the browser-use repo",
  "model": "gpt-4.1-mini",
  "max_steps": 100
}
```

**Response:**
```json
{
  "success": true,
  "message": "Task completed successfully",
  "steps_completed": 5,
  "result": "The browser-use repo has 15,234 stars",
  "is_done": true
}
```

### 3. Preload Case (NEW)
```http
POST /preload_case
```

Visit a Persona dashboard case URL with authentication and return a screenshot of the final page.

**Request Body:**
```json
{
  "case_token": "cas_abc123def456",
  "refresh_token": "your_persona_refresh_token"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Case preloaded successfully",
  "status_code": 200,
  "screenshot": "iVBORw0KGgoAAAANSUhEUgAA...base64-encoded-png-data"
}
```

The endpoint automatically constructs the URL: `https://app.withpersona.com/dashboard/cases/{case_token}`

**Development Mode**: When `DEV_MODE=true` is set, screenshots are automatically saved to your system's temp directory (`/tmp/browser-use-screenshots/` on Unix systems) with filenames like:
- `case_VAKx8NXRKg82SuFzKETk9qeC8u6M_20250102_143052_200.png`
- Format: `case_{TOKEN}_{TIMESTAMP}_{STATUS_CODE}.png`

## Installation & Setup

### Prerequisites

- Python 3.11+
- Chrome/Chromium browser
- OpenAI API key (or other LLM provider credentials)

### Environment Variables

Create a `.env` file in your project directory:

```bash
# Required for LLM functionality
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Specify port (defaults to 8080)
PORT=8080

# Optional: Enable development mode to save screenshots locally
DEV_MODE=true
```

## Running the API Server

### Option 1: Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/browser-use/browser-use.git
   cd browser-use
   ```

2. **Install dependencies:**
   ```bash
   # Using uv (recommended)
   uv sync --all-extras

   # Or using pip
   pip install -e ".[all]"
   ```

3. **Install Chrome/Chromium (if not already installed):**
   ```bash
   # Install Chromium via Playwright
   uvx playwright install chromium --with-deps --no-shell

   # Or install Chrome manually on your system
   ```

4. **Set up environment:**
   ```bash
   # Copy example environment file
   cp .env.example .env

   # Edit .env and add your API keys
   nano .env
   ```

5. **Run the server:**
   ```bash
   # Using uv
   uv run python api_server.py

   # Or using python directly
   python api_server.py

   # Or using uvicorn directly
   uvicorn api_server:app --host 0.0.0.0 --port 8080
   
   # With development mode enabled
   DEV_MODE=true uv run python api_server.py
   ```

6. **Test the server:**
   ```bash
   curl http://localhost:8080/health
   ```

### Option 2: Docker

The API server is already configured as the default Docker entrypoint.

#### Quick Start with Docker

1. **Pull and run the pre-built image:**
   ```bash
   docker run -p 8080:8080 -e OPENAI_API_KEY=your_key_here browseruse/browseruse:latest
   ```

2. **Or build locally:**
   ```bash
   # Clone the repository
   git clone https://github.com/browser-use/browser-use.git
   cd browser-use

   # Build the Docker image
   docker build -t browser-use-api .

   # Run the container
   docker run -p 8080:8080 -e OPENAI_API_KEY=your_key_here browser-use-api
   ```

## Usage Examples

### Python Client

```python
import asyncio
import httpx


async def run_browser_task():
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8080/run_task",
            json={
                "task": "Go to GitHub and find the browser-use repository stars",
                "model": "gpt-4.1-mini",
                "max_steps": 10
            }
        )
        return response.json()


async def preload_persona_case():
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8080/preload_case",
            json={
                "case_token": "cas_abc123def456",
                "refresh_token": "your_persona_refresh_token"
            }
        )
        return response.json()  # Contains base64 screenshot data


# Run examples
result = asyncio.run(run_browser_task())
print(result)
```

### cURL Examples

```bash
# Health check
curl http://localhost:8080/health

# Run a browser task
curl -X POST http://localhost:8080/run_task \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Go to news.yocombinator.com and get the page title",
    "model": "gpt-4.1-mini",
    "max_steps": 5
  }'

# Preload a Persona case
curl -X POST http://localhost:8080/preload_case \
  -H "Content-Type: application/json" \
  -d '{
    "case_token": "case_VAKx8NXRKg82SuFzKETk9qeC8u6M",
    "refresh_token": "your_persona_refresh_token_here"
  }'
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

async function runBrowserTask() {
  try {
    const response = await axios.post('http://localhost:8080/run_task', {
      task: 'Navigate to GitHub and check browser-use stars',
      model: 'gpt-4.1-mini',
      max_steps: 10
    });

    console.log('Task result:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

async function preloadPersonaCase(caseToken, refreshToken) {
  try {
    const response = await axios.post(
      'http://localhost:8080/preload_case',
      {
        case_token: caseToken,
        refresh_token: refreshToken
      }
    );

    console.log('Case preloaded:', response.data.success);
    return response.data.screenshot; // Base64 encoded PNG screenshot
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}
```

## API Documentation

Once the server is running, you can access the interactive API documentation at:

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

## Configuration

### Browser Settings

The API server uses optimized browser settings for production:

```python
browser_profile = BrowserProfile(
    headless=True,
    chromium_sandbox=False,
    args=[
        '--single-process',
        '--headless=new',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--no-zygote',
        '--disable-extensions',
    ]
)
```

### LLM Models

Supported models (configure via environment or request):
- OpenAI: `gpt-4.1-mini`, `gpt-4`, `gpt-3.5-turbo`
- Anthropic: `claude-3-sonnet`, `claude-3-haiku`
- Google: `gemini-pro`, `gemini-1.5-pro`
- Groq: Various models with fast inference

## Troubleshooting

### Common Issues

1. **Chrome not found**: Install Chrome/Chromium or use Playwright to install:
   ```bash
   uvx playwright install chromium --with-deps
   ```

2. **Permission denied in Docker**: Add security options:
   ```bash
   docker run --cap-add=SYS_ADMIN --security-opt seccomp=unconfined ...
   ```

3. **Memory issues**: Increase Docker memory limits:
   ```bash
   docker run --memory=2g --memory-swap=4g ...
   ```

4. **Timeout errors**: Increase request timeout for complex tasks:
   ```python
   async with httpx.AsyncClient(timeout=60.0) as client:
       # ... make request
   ```

### Debugging

Enable debug logging by setting environment variable:
```bash
export PYTHONPATH=.
export LOG_LEVEL=DEBUG
python api_server.py
```

### Docker Logs

```bash
# View real-time logs
docker logs -f container_name

# View last 100 lines
docker logs --tail 100 container_name
```

## Security Considerations

- **API Keys**: Never expose API keys in code. Use environment variables.
- **CORS**: Configure CORS settings for production deployments.
- **Authentication**: Consider adding API authentication for production use.
- **Rate Limiting**: Implement rate limiting for public deployments.
- **Firewall**: Restrict access to the API port in production.

## Performance

- **Concurrent Requests**: The server can handle multiple concurrent browser tasks
- **Resource Usage**: Each browser task uses ~200-500MB RAM
- **Scaling**: Use multiple containers behind a load balancer for high throughput

## Development

### Running Tests

```bash
# Install development dependencies
uv sync --all-extras --dev

# Run type checking
uv run pyright

# Run tests
uv run pytest -xvs tests/ci

# Test the API endpoints
python test_preload_endpoint.py
```
