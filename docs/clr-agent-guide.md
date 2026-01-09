# Cognitive Load Radar (CLR) Agent - Comprehensive Guide

## Overview

The Cognitive Load Radar™ is an advanced AI-powered system that continuously monitors and analyzes student cognitive load during learning sessions. It combines behavioral pattern recognition, sentiment analysis, historical baselines, and LLM-powered insights to provide real-time, personalized interventions.

## Table of Contents

1. [Concept & Motivation](#concept--motivation)
2. [Technical Architecture](#technical-architecture)
3. [Multi-Layered Calculation](#multi-layered-calculation)
4. [Pattern Detection Algorithms](#pattern-detection-algorithms)
5. [Mood Analysis Methodology](#mood-analysis-methodology)
6. [API Usage Examples](#api-usage-examples)
7. [Integration Guide](#integration-guide)
8. [Performance Tuning](#performance-tuning)
9. [Troubleshooting](#troubleshooting)

## Concept & Motivation

### The Problem

Students experience cognitive overload during learning, leading to:

- Decreased comprehension and retention
- Increased frustration and anxiety
- Higher dropout rates
- Suboptimal learning outcomes

Traditional learning platforms lack real-time awareness of student mental state, missing critical intervention opportunities.

### The Solution

The CLR Agent provides:

- **Real-time monitoring**: Continuous analysis of behavioral signals
- **Proactive interventions**: Early warnings before cognitive load becomes critical
- **Personalized insights**: AI-generated recommendations based on individual patterns
- **Predictive analytics**: Forecasting cognitive load trajectory to enable preventive actions

## Technical Architecture

```
┌─────────────┐
│   Frontend  │ (Behavioral Events via WebSocket)
└──────┬──────┘
       │
       v
┌─────────────────────┐
│  WebSocket Server   │ (Node.js Backend)
│   behaviorStream    │
└──────┬──────────────┘
       │
       v
┌─────────────────────┐
│   Redis Streams     │ (behavior:{session_id})
└──────┬──────────────┘
       │
       v (Trigger: Session End / Quiz Complete)
       │
┌──────v──────────────┐
│   CLR Agent (Python)│
│  - Pattern Detection│
│  - Mood Analysis    │
│  - Baseline Compare │
│  - LLM Insights     │
└──────┬──────────────┘
       │
       v
┌──────v──────────────┐
│  Redis Time-Series  │ (clr:{student_id})
│  PostgreSQL Storage │
└──────┬──────────────┘
       │
       v (Pub/Sub)
       │
┌──────v──────────────┐
│  WebSocket Broadcast│ (Real-time CLR Updates)
└─────────────────────┘
```

### Data Flow

1. **Event Collection**: Frontend tracks user interactions (clicks, typing, navigation, idle time)
2. **Buffering**: Events buffered in Redis streams by session ID
3. **Triggering**: Session end or quiz completion triggers CLR Agent
4. **Analysis**: Multi-layered cognitive load calculation
5. **Storage**: Results stored in Redis (time-series) and PostgreSQL (persistent)
6. **Broadcasting**: Real-time updates pushed to frontend via WebSocket
7. **API Access**: Dashboard queries historical data via REST API

## Multi-Layered Calculation

The CLR Agent employs a 4-layer approach to calculate cognitive load:

### Layer 1: Basic Weighted Metrics

Classic weighted calculation from behavioral aggregates:

```python
cognitive_load = (
    task_switching * 0.25 +      # Navigation frequency
    error_rate * 0.20 +           # Quiz/interaction errors
    procrastination * 0.20 +      # Idle time proportion
    browsing_drift * 0.15 +       # Rapid back-and-forth navigation
    time_per_concept * 0.10 +     # Very short engagement times
    productivity * 0.10           # Active vs idle time ratio
)
```

**Output**: Base score 0-100

### Layer 2: Pattern Recognition

Advanced pattern detection adds adjustment based on mental strain signals:

- **Task Switching**: >5 navigation events in 2 minutes → +15 points
- **Error Clustering**: 3+ errors in 5 minutes → +20 points
- **Procrastination Loops**: Repeated idle-nav-idle cycles → +15 points
- **Night Degradation**: 2-4 AM sessions → +80 points peak

**Output**: Pattern adjustment 0-20 points

### Layer 3: Mood Analysis

Sentiment analysis from text and typing patterns:

- Text sentiment (LLM-based): -1 (very negative) to +1 (very positive)
- Typing mood indicators: frustration, confidence, overload, engagement
- Negative mood adds 0-20 points based on severity

**Adjustment**:

- Mood < -0.5 → +20 points (high frustration)
- Mood < -0.2 → +10 points (moderate frustration)
- Mood < 0 → +5 points (slight negative)

### Layer 4: Historical Baseline

Compares current load to student's 7-day baseline:

- Calculate z-score: `(current - baseline_avg) / baseline_std`
- Flag anomalies when z-score > 2.0 (2 standard deviations)

**Adjustment**:

- z-score > 2.0 → +15 points (significantly above normal)
- z-score > 1.0 → +8 points (moderately above normal)

### Final Score

```python
final_score = min(100, max(0,
    base_score + pattern_adjustment + mood_adjustment + baseline_deviation
))
```

### Fatigue Level Mapping

- **0-25**: Low fatigue (optimal learning state)
- **25-50**: Medium fatigue (monitor, suggest breaks)
- **50-75**: High fatigue (recommend break, adjust difficulty)
- **75-100**: Critical fatigue (immediate intervention required)

## Pattern Detection Algorithms

### 1. Task Switching Pattern

**Goal**: Detect rapid context switching indicating cognitive overload

**Algorithm**:

```python
def detect_task_switching(events):
    nav_events = filter(events, type='NAVIGATION')

    for window in sliding_window(nav_events, size=5):
        if time_span(window) <= 2_minutes:
            rapid_switches += 1

    detected = rapid_switches > 0
    score = min(rapid_switches * 15, 100)
```

**Threshold**: >5 navigation events within 2 minutes

### 2. Error Clustering

**Goal**: Identify error bursts suggesting mental fatigue

**Algorithm**:

```python
def detect_error_clustering(events):
    error_events = filter(events, has_error=True)

    for window in sliding_window(error_events, size=3):
        if time_span(window) <= 5_minutes:
            clusters += 1

    detected = clusters > 0
    score = min(clusters * 20, 100)
```

**Threshold**: 3+ errors within 5 minutes

### 3. Procrastination Loops

**Goal**: Recognize repeated idle-navigation-idle cycles

**Algorithm**:

```python
def detect_procrastination_loops(events):
    for i in range(len(events) - 2):
        if pattern_match(events[i:i+3], ['IDLE', 'NAVIGATION', 'IDLE']):
            loop_count += 1

    detected = loop_count >= 2
    score = min(loop_count * 15, 100)
```

**Threshold**: 2+ procrastination loop sequences

### 4. Micro-Break Analysis

**Goal**: Analyze break frequency and duration for healthy patterns

**Algorithm**:

```python
def analyze_micro_breaks(events):
    idle_events = filter(events, type='IDLE', duration >= 60_seconds)

    break_durations = [e.duration / 60 for e in idle_events]
    break_intervals = calculate_intervals(idle_events)

    avg_duration = mean(break_durations)
    avg_interval = mean(break_intervals)

    # Optimal: 5-10 min breaks every 25-50 min
    if 5 <= avg_duration <= 10 and 25 <= avg_interval <= 50:
        score = 0  # Healthy pattern
    elif avg_interval > 100:
        score = 60  # Too few breaks
    elif avg_duration < 3:
        score = 40  # Breaks too short
```

**Optimal Range**: 5-10 minute breaks every 25-50 minutes

### 5. Night Degradation

**Goal**: Compare performance during night hours vs day

**Algorithm**:

```python
def detect_night_degradation(events, features):
    hour = features['hour_of_day']

    if 2 <= hour <= 4:
        score = 80  # Peak degradation
    elif 22 <= hour or hour <= 6:
        score = 50  # Night hours
    else:
        score = 0   # Normal hours
```

**Night Hours**: 10 PM - 6 AM with peak degradation 2-4 AM

## Mood Analysis Methodology

### Text-Based Sentiment Analysis

Uses Google Generative AI (Gemini 1.5 Flash) for sentiment extraction:

**Prompt Template**:

```
Analyze the emotional tone of this student's text.
Consider frustration, confidence, confusion, and engagement.
Return mood score from -1 (very negative) to +1 (very positive)
and a brief explanation.

Text: {student_text}
```

**Output**:

```json
{
  "mood_score": -0.6,
  "dominant_emotion": "frustrated",
  "confidence": 0.75,
  "explanation": "High frustration from repeated errors and negative phrasing"
}
```

**Sources**: Quiz answers, search queries, typing content

### Typing Pattern Mood Detection

Infers mood from typing behavior without LLM:

**Indicators**:

- **High backspace rate + low WPM**: Frustration/confusion (-0.65)
- **Consistent WPM + low corrections**: Confidence (+0.65)
- **Erratic typing + long pauses**: Cognitive overload (-0.45)
- **Very fast typing**: Engagement (+0.5)
- **Very slow typing**: Confusion/fatigue (-0.3)

**Consistency Score**:

```python
consistency = max(0, 1.0 - (wpm_variance / 100))
```

### Temporal Mood Trend

**Storage**: Redis sorted set `mood:{student_id}` with timestamp as score

**Trend Calculation** (Linear Regression):

```python
def calculate_mood_trend(mood_history):
    x = range(len(mood_history))
    y = [entry['mood_score'] for entry in mood_history]

    slope = linear_regression_slope(x, y)

    if slope > 0.01:
        trend = 'improving'
    elif slope < -0.01:
        trend = 'declining'
    else:
        trend = 'stable'
```

**Drop Detection**:

- Monitor 15-minute window
- Alert if mood drops by ≥0.4 points
- Critical intervention if drop ≥0.6 points

## API Usage Examples

### 1. Get Current Cognitive Load

```bash
curl -X GET "http://localhost:8000/api/clr/current/student123"
```

**Response**:

```json
{
  "student_id": "student123",
  "cognitive_load_score": 67.5,
  "mental_fatigue_level": "high",
  "detected_patterns": ["task_switching", "error_clustering"],
  "mood_indicators": {
    "mood_score": -0.4,
    "dominant_emotion": "frustrated"
  },
  "timestamp": 1704816000000,
  "session_id": "session456"
}
```

### 2. Get Historical Data

```bash
curl -X GET "http://localhost:8000/api/clr/history/student123?time_range=day&granularity=raw"
```

**Response**:

```json
{
  "student_id": "student123",
  "time_range": "day",
  "granularity": "raw",
  "history": [
    {
      "timestamp": 1704816000000,
      "score": 67.5,
      "fatigue_level": "high",
      "patterns": ["task_switching"]
    }
  ],
  "statistics": {
    "min": 25.0,
    "max": 75.0,
    "average": 50.5,
    "median": 52.0,
    "percentile_95": 72.0
  },
  "trend": "increasing",
  "trend_slope": 0.5,
  "data_points": 48
}
```

### 3. Generate Insights

```bash
curl -X GET "http://localhost:8000/api/clr/insights/student123"
```

**Response**:

```json
{
  "student_id": "student123",
  "insights": "Your cognitive load is elevated due to rapid task switching between topics. Consider focusing on one module at a time to improve comprehension. The error clustering pattern suggests you may benefit from reviewing prerequisite concepts before proceeding.",
  "recommendations": [
    "Take a 5-10 minute break to reset cognitive load",
    "Focus on one topic at a time instead of switching",
    "Review prerequisite material for current module"
  ],
  "generated_at": 1704816000000
}
```

### 4. Analyze Text Mood

```bash
curl -X POST "http://localhost:8000/api/clr/analyze-text" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "student123",
    "text": "I dont understand this at all its too confusing",
    "context": "quiz_answer"
  }'
```

**Response**:

```json
{
  "student_id": "student123",
  "mood_score": -0.7,
  "dominant_emotion": "confused",
  "confidence": 0.85,
  "explanation": "Strong negative sentiment with confusion indicators"
}
```

### 5. Get Dashboard Data

```bash
curl -X GET "http://localhost:8000/api/clr/dashboard/student123"
```

**Response**: Combines all CLR data in single optimized call (current, history, insights, patterns, baseline, predictions)

## Integration Guide

### Frontend Integration

**1. Subscribe to real-time updates**:

```typescript
// Connect to WebSocket
const socket = io("http://localhost:3001");

// Listen for CLR updates
socket.on("clr:update", (message) => {
  const { cognitiveLoadScore, mentalFatigueLevel, recommendations } =
    message.data;

  // Update UI
  updateCLRDisplay(cognitiveLoadScore, mentalFatigueLevel);
  showRecommendations(recommendations);
});
```

**2. Fetch dashboard data**:

```typescript
async function loadCLRDashboard(studentId: string) {
  const response = await fetch(`/api/clr/dashboard/${studentId}`);
  const data = await response.json();

  renderCLRChart(data.history);
  displayInsights(data.insights);
  showPatterns(data.patterns);
}
```

### Backend Integration

**1. Trigger CLR analysis**:

```python
from agents.graph import workflow

# Trigger after session end or quiz complete
result = await workflow.ainvoke({
    "student_id": student_id,
    "session_id": session_id,
    "trigger_type": "session_end"
})
```

**2. Access CLR storage service**:

```python
from services.clr_storage import clr_storage_service

# Store cognitive load
clr_storage_service.store_cognitive_load(student_id, session_id, clr_data)

# Get history
history = clr_storage_service.get_cognitive_load_history(student_id, 'last_week')

# Calculate baseline
baseline = clr_storage_service.calculate_baseline_metrics(student_id, days=7)
```

## Performance Tuning

### Redis Optimization

- **Time-series**: Use sorted sets for O(log N) operations
- **TTL**: Set 30-day expiration on CLR data to auto-cleanup
- **Batch operations**: Use pipeline for multiple ZADD commands

```python
pipe = redis.pipeline()
for entry in clr_entries:
    pipe.zadd(f"clr:{student_id}", {json.dumps(entry): timestamp})
pipe.execute()
```

### LLM Cost Optimization

- **Caching**: Cache insights for 5 minutes (300-second TTL)
- **Batch processing**: Analyze up to 3 text samples max per execution
- **Fallback**: Use typing patterns when text unavailable

**Estimated Costs** (Gemini 1.5 Flash):

- ~$0.0001 per sentiment analysis
- ~$0.0005 per insight generation
- With caching: ~$0.50/day for 1000 students

### Database Performance

- **Batch writes**: Accumulate 10 entries before PostgreSQL insert
- **Time-based flush**: Flush every 5 minutes even if buffer not full
- **Indexing**: Index student_id and timestamp columns

```sql
CREATE INDEX idx_cognitive_metric_student_time
ON "CognitiveMetric" (student_id, timestamp);
```

### WebSocket Throttling

- Max 1 CLR update per 30 seconds per student
- Prevents frontend flooding
- Reduces bandwidth by 95%

```typescript
const CLR_UPDATE_INTERVAL = 30000; // 30 seconds
```

## Troubleshooting

### Common Issues

**1. No CLR data appearing**

- Check if behavioral events are being tracked (frontend)
- Verify Redis connection: `redis-cli PING`
- Check agent execution logs: `tail -f logs/agent.log`
- Ensure session end event is triggered

**2. Insights not generating**

- Verify GOOGLE_API_KEY is set in `.env`
- Check LLM call logs for errors
- Test API key: `curl "https://generativelanguage.googleapis.com/v1/models?key=YOUR_KEY"`

**3. WebSocket updates not received**

- Check Redis pub/sub subscription: `PUBSUB CHANNELS agent:*`
- Verify student connection tracking in behaviorStream.ts
- Check throttling hasn't blocked update

**4. High memory usage**

- Verify Redis TTLs are set correctly (30 days)
- Run cleanup task manually if needed
- Check batch buffer isn't accumulating

**5. Slow API responses**

- Enable query result caching
- Check Redis connection pooling
- Optimize database indexes

### Debug Commands

```bash
# Check Redis CLR data
redis-cli ZRANGE clr:student123 0 -1 WITHSCORES

# Check agent execution count
redis-cli GET clr_agent:execution_count

# View recent logs
tail -f logs/clr_agent.log

# Test CLR endpoint
curl -X GET "http://localhost:8000/health/clr"
```

### Monitoring

```bash
# Check CLR agent health
curl "http://localhost:8000/health/clr"

# View detailed metrics
curl "http://localhost:8000/health/agents"
```

**Key Metrics**:

- Execution count and error rate
- Average execution time
- Pattern detection frequency
- LLM cache hit rate
- Memory usage

---

## Support

For issues or questions:

- Check logs: `backend-python/logs/`
- Health endpoint: `GET /health/clr`
- Monitoring: `GET /health/agents`

## License

Part of Adaptive Student Navigator project.
