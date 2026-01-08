# Adaptive Student Navigator - Python Backend

AI Agent orchestration service using FastAPI and LangGraph for intelligent learning interventions.

## Architecture

This service integrates with the Node.js backend through REST APIs and Redis pub/sub to provide:

- **Cognitive Load Recognition (CLR Agent)**: Analyzes behavioral data to calculate real-time cognitive load
- **Performance Analysis (Performance Agent)**: Tracks learning velocity and improvement trends
- **Engagement Tracking (Engagement Agent)**: Monitors student engagement and dropout risk
- **Curriculum Adaptation (Curriculum Agent)**: Adjusts learning paths based on cognitive load
- **Motivation & Intervention (Motivation Agent)**: Generates timely support messages

## Technology Stack

- **FastAPI**: Modern Python web framework
- **LangGraph**: Agent orchestration with state management
- **LangChain**: LLM integration for intelligent agents
- **Redis**: Pub/sub messaging and caching
- **PostgreSQL**: Data persistence via SQLAlchemy
- **Pydantic**: Data validation and settings management

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Node.js backend running (for integration)

### Installation

1. **Create virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the service:**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

The service will be available at:

- API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Environment Variables

```env
DATABASE_URL=postgresql://user:password@localhost:5432/student_navigator
REDIS_URL=redis://localhost:6379
NODE_BACKEND_URL=http://localhost:3000
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
AGENT_EXECUTION_TIMEOUT=300
CLR_THRESHOLD_LOW=30
CLR_THRESHOLD_MEDIUM=60
CLR_THRESHOLD_HIGH=80
```

## API Endpoints

### Health Checks

- `GET /health` - Basic service health check
- `GET /health/agents` - Detailed agent statistics

### Agent Workflow

- `POST /api/agents/trigger-workflow` - Trigger complete agent workflow
- `GET /api/agents/workflow-status/{workflow_id}` - Check workflow status
- `POST /api/agents/calculate-cognitive-load` - Calculate cognitive load
- `POST /api/agents/request-intervention` - Request immediate intervention
- `POST /api/agents/curriculum-adjustment` - Adjust learning path

## Agent Workflow

```
START → Fetch Behavioral Data → CLR Agent → Route by Cognitive Load
                                                   ↓
                       [Low/Medium] → Performance Agent → Engagement Agent → Curriculum Agent
                                                   ↓
                       [High/Critical] → Motivation Agent → Curriculum Agent
                                                   ↓
                                                  END
```

## Redis Pub/Sub Channels

### Subscribed Channels (Incoming)

- `behavior:events` - Real-time behavioral events
- `sessions:ended` - Session end notifications
- `quiz:completed` - Quiz completion events
- `cognitive:threshold` - Cognitive load threshold breaches

### Published Channels (Outgoing)

- `interventions` - Intervention delivery to frontend
- `curriculum_updates` - Curriculum change notifications
- `agent:clr` - CLR Agent events
- `agent:performance` - Performance Agent events
- `agent:engagement` - Engagement Agent events
- `agent:curriculum` - Curriculum Agent events
- `agent:motivation` - Motivation Agent events

## Development

### Project Structure

```
backend-python/
├── main.py                 # FastAPI application
├── requirements.txt        # Dependencies
├── Dockerfile             # Container definition
├── .env.example           # Environment template
├── agents/
│   ├── __init__.py
│   ├── graph.py           # LangGraph orchestration
│   ├── state.py           # Shared state schema
│   └── base_agent.py      # Base agent class
├── api/
│   ├── health.py          # Health check endpoints
│   └── bridge.py          # REST API bridge
├── config/
│   ├── database.py        # PostgreSQL connection
│   ├── redis_client.py    # Redis connection
│   └── settings.py        # Environment config
├── models/
│   └── schemas.py         # Pydantic models
└── services/
    ├── event_consumer.py  # Redis event consumer
    └── pubsub_handler.py  # Redis pub/sub handler
```

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

### Logging

Set `LOG_LEVEL` in `.env`:

- `DEBUG` - Detailed logs including SQL queries
- `INFO` - Standard operation logs (default)
- `WARNING` - Warnings and errors only
- `ERROR` - Errors only

## Integration with Node.js Backend

The Python backend communicates with Node.js through:

1. **REST API calls** from Node.js to trigger workflows
2. **Redis pub/sub** for real-time event streaming
3. **Shared PostgreSQL** database for data persistence
4. **Shared Redis** for caching and buffering

Node.js sends behavioral events → Python processes with agents → Results published to Redis → Node.js delivers to frontend

## Deployment

### Docker

```bash
docker build -t student-navigator-python .
docker run -p 8000:8000 --env-file .env student-navigator-python
```

### Docker Compose

Integrate with existing `docker-compose.yml`:

```yaml
python-backend:
  build: ./backend-python
  ports:
    - "8000:8000"
  environment:
    - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/student_navigator
    - REDIS_URL=redis://redis:6379
    - NODE_BACKEND_URL=http://backend:3000
  depends_on:
    - postgres
    - redis
    - backend
```

## Monitoring

- Health checks: `curl http://localhost:8000/health`
- Agent stats: `curl http://localhost:8000/health/agents`
- API docs: `http://localhost:8000/docs`
- Logs: Check console output with configured LOG_LEVEL

## Future Enhancements

- [ ] Implement full LLM-powered agents (currently placeholders)
- [ ] Add agent memory with LangGraph checkpointing
- [ ] Integrate RAG for personalized content retrieval
- [ ] Add Prometheus metrics endpoint
- [ ] Implement circuit breakers for external services
- [ ] Add comprehensive unit and integration tests
- [ ] Implement agent A/B testing framework

## License

See root LICENSE file

## Support

For issues and questions, see main project README
