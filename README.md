# Psychic Source Transcript Analysis Tool

A web application for analyzing call transcripts from ElevenLabs' Conversational Voice Agent for Psychic Source with additional outbound calling capabilities.

## Current Features

- **Conversation Browser**: View and search through psychic reading conversations with an iMessage-style transcript viewer
- **Dashboard**: Interactive overview with KPIs, charts, and metrics showing conversation data
- **Agent Selection**: Support for multiple Lilly agents (filter dashboard by agent)
- **Admin Panel**: View agent prompts, email templates, and interact directly with the agent through a widget
- **Ad-Hoc SQL Querying**: Ask questions about conversation data in natural language (LLM-translated to SQL)
- **Outbound Calling**: Make personalized outbound calls to previous callers using ElevenLabs' voice synthesis
- **Sentiment Analysis**: Analyze the emotional tone of conversations
- **Topic Extraction**: Identify key themes and topics discussed
- **Data Visualization**: Interactive charts and graphs showing trends and patterns

## Architecture

The application uses a service-oriented architecture with Supabase as the primary database:

- **Flask Backend**: Handles API requests, data processing, and rendering
- **Service Layer**: Separates business logic from API integration and presentation
- **Supabase Integration**: PostgreSQL-based cloud database for scalable data storage
- **ElevenLabs API Integration**: Retrieves conversation data and enables outbound calling
- **Analysis Engine**: Processes conversation data to extract insights
- **Responsive UI**: Bootstrap-based interface with Chart.js visualizations

## Outbound Calling System

The application includes a complete outbound calling system:

- **Client Library**: JavaScript and Python clients for initiating calls
- **FastAPI Service**: REST API for managing outbound calls
- **ElevenLabs Integration**: Uses ElevenLabs' text-to-speech for natural-sounding calls
- **Twilio Integration**: Handles actual phone call placement and status updates
- **Hospitality Feature**: Personalized follow-up calls to previous customers

## Tech Stack

- **Backend**: Python 3.12 with Flask
- **Database**: Supabase (PostgreSQL)
- **API Gateway**: FastAPI for the outbound calling service
- **Frontend**: HTML/CSS/JS with Bootstrap 5 and Chart.js
- **LLM Integration**: OpenAI for enhanced analysis and SQL query translation
- **Authentication**: Supabase auth
- **Deployment**: Supports Replit, traditional servers, and containerized environments

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Supabase account and project
- ElevenLabs API key
- OpenAI API key for enhanced analysis

### Installation

1. Clone the repository:

```bash
git clone https://github.com/your-org/psychic-source-analyzer.git
cd psychic-source-analyzer
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up environment variables:

Create a `.env` file in the project root:

```
# ElevenLabs Configuration
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_AGENT_ID_CURIOUS=your_curious_caller_agent_id
ELEVENLABS_VOICE_ID=your_voice_id

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Twilio for outbound calls
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# Flask Configuration
SECRET_KEY=your_random_secret_key
```

5. Download NLTK resources (if using NLP features):

```bash
python nltk_setup.py
```

### Starting the Application

Use the simplified startup script:

```bash
bash simplified_start.sh
```

Or start directly with Python:

```bash
python run.py
```

Access the application at http://localhost:8080 (check the console output for the actual port).

## Usage

### Dashboard

The dashboard provides an overview of conversation metrics, including:

- Total conversations
- Average duration
- Completion rate
- Month-to-date cost tracking with budget indicator
- Time-of-day distribution
- Day-of-week distribution
- Agent selection dropdown for filtering metrics by agent
- Agent administration panel for viewing prompts and email templates
- SQL query interface for ad-hoc data exploration

### Transcript Viewer

Browse and search conversations with:

- Date range filtering
- Full-text search
- iMessage-style transcript view
- Sentiment highlighting

### Themes & Sentiment

Analyze the emotional tone and topics of conversations:

- Sentiment trends over time
- Top themes and topics
- Theme-sentiment correlation
- Common questions and concerns

### Outbound Calling

The dashboard includes an outbound calling demo, allowing you to:

- Select a recipient from a dropdown menu
- Initiate a personalized outbound call with a customized greeting
- View the call status and greeting message

## Project Structure

```
/
├── app/                      # Main application directory
│   ├── __init__.py           # Application factory
│   ├── routes.py             # Route definitions
│   ├── api/                  # API integration
│   │   ├── elevenlabs_client.py  # ElevenLabs API client
│   │   └── routes.py            # API endpoints
│   ├── services/             # Service layer
│   │   ├── conversation_service.py     # Database conversation service
│   │   ├── supabase_conversation_service.py  # Supabase implementation
│   │   ├── analysis_service.py         # Analysis operations
│   │   └── export_service.py           # Export operations
│   ├── static/               # Static assets
│   │   ├── css/              # Stylesheets
│   │   ├── js/               # JavaScript files
│   │   └── images/           # Images (Tom memes, function maps)
│   ├── tasks/                # Background tasks
│   │   └── sync.py           # Data synchronization with ElevenLabs
│   ├── templates/            # HTML templates
│   └── utils/                # Utility functions
├── outbound_calls/           # Outbound calling system
│   ├── app.py                # FastAPI outbound call service
│   ├── client.py             # Python client for outbound calls
│   ├── mcp_client.py         # ElevenLabs MCP client
│   ├── outbound.py           # Core outbound functionality
│   ├── outbound_client.js    # JavaScript client for web usage
│   └── outbound_server.py    # Server endpoints
├── tools/                    # Utility tools
│   └── supabase_client.py    # Supabase client wrapper
├── tests/                    # Test directory
├── config.py                 # Configuration settings
├── run.py                    # Application entry point
└── requirements.txt          # Python dependencies
```

## Recent Updates

### 1. Dashboard Enhancements (April 2025)

- **Multi-Agent Support**: Added ability to filter dashboard by different Lilly agents
- **Agent Administration Panel**: Added viewing of agent prompts and email templates
- **Natural Language SQL Interface**: Added ability to query the database using plain English
- **Cost Tracking**: Added month-to-date cost tracking with budget visualization
- **UI Improvements**: Enhanced card design and tooltips for better information display

### 2. Supabase Integration (April 2025)

- Migrated data storage from SQLAlchemy to Supabase for improved scalability
- Implemented hybrid approach with fallback to original database if needed
- Updated sync task to write data to Supabase
- Created RPC functions for custom queries
- Updated services to use Supabase client

### 3. Outbound Calling System (April 2025)

- Added complete outbound calling functionality with ElevenLabs integration
- Created hospitality calling feature for personalized customer follow-up
- Implemented both JavaScript and Python clients
- Added FastAPI service for call management
- Created documentation with function maps

### 4. Fun Features (April 2025)

- Added expandable Tom images in the Fun section
- Added function map visualization for the outbound calling system
- Enhanced documentation and sample data

## API Documentation

See [API documentation](docs/api/API_DOCUMENTATION.md) for detailed information on the application's REST API.

## Deployment

### On Replit

The application is configured to run on Replit. Simply:

1. Import the repository
2. Set the environment variables in the Replit Secrets
3. Run `bash replit_start.sh`

### On a Traditional Server

1. Set up a production WSGI server (e.g., Gunicorn):

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8080 "app:create_app()"
```

2. Set up a reverse proxy (e.g., Nginx) to handle static files and SSL termination.

## Development Guidelines

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Write comprehensive docstrings
- Add unit tests for new functionality
- Keep files under 200-300 lines of code (refactor if necessary)
- Avoid mock data in production code
- Write thorough tests for all major functionality

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- ElevenLabs for their Conversational Voice Agent API
- Supabase for database infrastructure
- The Flask and FastAPI teams for the web frameworks
- Chart.js for data visualization capabilities

# Psychic Source Flask App - Development & Deployment Guide

## Overview
This project is a Flask-based web application for Psychic Source, designed for robust analytics, agent management, and integration with Supabase and AI services. The codebase is optimized for development on Replit, with a clear separation between development and production environments.

---

## Development Environment (Replit)

### Database Configuration
- **Development (Replit):**
  - Uses **SQLite** (`sqlite:///app.db`) for all development and testing.
  - This is enforced in `config.py` regardless of the presence of a `DATABASE_URL` environment variable.
  - Data is stored in the `app.db` file in your project directory and persists between runs.
- **Production:**
  - Uses **PostgreSQL** via the `DATABASE_URL` environment variable.
  - Only enabled when `FLASK_ENV=production`.

### Why SQLite for Dev?
- Avoids binary incompatibility issues with `psycopg2` and Replit's environment.
- No need for external database services or drivers.
- Fast, lightweight, and easy to reset.

### Switching Environments
- **Development:**
  - No action needed; SQLite is always used unless `FLASK_ENV=production`.
- **Production:**
  - Set `FLASK_ENV=production` and provide a valid `DATABASE_URL` for PostgreSQL.

---

## Environment Variables

| Variable                | Purpose                                 | Example Value                                                      |
|------------------------ |-----------------------------------------|--------------------------------------------------------------------|
| `FLASK_ENV`             | Set to `production` for prod            | `production` or `development`                                      |
| `DATABASE_URL`          | PostgreSQL URI (prod only)              | `postgresql://user:pass@host:port/dbname`                          |
| `SECRET_KEY`            | Flask secret key                        | `supersecretkey`                                                   |
| `ELEVENLABS_API_KEY`    | ElevenLabs API key                      | `sk-...`                                                           |
| `SUPABASE_URL`          | Supabase project URL                    | `https://xyz.supabase.co`                                          |
| `SUPABASE_SERVICE_KEY`  | Supabase service key                    | `eyJ...`                                                           |
| `OPENAI_API_KEY`        | OpenAI API key                          | `sk-...`                                                           |

- Add any additional environment variables as needed for your integrations.

---

## Dev Workflow Tips

- **Start the server:**
  ```sh
  python run.py
  ```
- **Database migrations:**
  - Migrations are supported with Flask-Migrate and SQLite.
  - For schema changes:
    ```sh
    flask db migrate -m "Your message"
    flask db upgrade
    ```
- **Testing:**
  - Write tests for all major functionality.
  - Use SQLite for all local/dev tests.
- **Troubleshooting:**
  - If you see segmentation faults or memory errors, ensure you are using SQLite (check logs for `sqlite:///app.db`).
  - If you need to use PostgreSQL, do so only in production or in a local environment with compatible system libraries.
- **Environment switching:**
  - The app will always use SQLite unless `FLASK_ENV=production`.
  - To force production mode, set `FLASK_ENV=production` and provide a valid `DATABASE_URL`.
- **Data persistence:**
  - The `app.db` file will persist between runs on Replit. To reset, simply delete the file.

---

## Production Deployment

- Set `FLASK_ENV=production` and provide a valid `DATABASE_URL` for PostgreSQL.
- Ensure all required environment variables are set.
- Use a production-ready WSGI server (e.g., Gunicorn) for deployment.

---

## config.py Logic (Database Selection)

```python
# config.py (excerpt)
if os.environ.get('FLASK_ENV') == 'production':
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
else:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
```
- This ensures SQLite is always used for dev, and PostgreSQL only in production.

---

## Additional Notes
- For any issues with dependencies, always remove `.pythonlibs` and reinstall:
  ```sh
  rm -rf .pythonlibs
  pip install -r requirements.txt
  ```
- If you need to reset the database, delete `app.db` and restart the server.
- For further help, see the comments in `config.py` and the project's codebase.

---

## Contact
For questions or support, contact the project maintainer or open an issue in the repository. 