# Psychic Source Transcript Analysis Tool

A web application for analyzing call transcripts from ElevenLabs' Conversational Voice Agent for Psychic Source.

## Features

- **Conversation Browser**: View and search through psychic reading conversations
- **Sentiment Analysis**: Analyze the emotional tone of conversations
- **Topic Extraction**: Identify key themes and topics discussed
- **Data Visualization**: Interactive charts and graphs showing trends and patterns
- **Export Capabilities**: Export data in JSON, CSV, and Markdown formats

## Architecture

The application uses a service-oriented architecture:

- **Flask Backend**: Handles API requests, data processing, and rendering
- **Service Layer**: Separates business logic from API integration and presentation
- **ElevenLabs API Integration**: Communicates with the ElevenLabs API to retrieve conversation data
- **Analysis Engine**: Processes conversation data to extract insights
- **Responsive UI**: Bootstrap-based interface with Chart.js visualizations

## Getting Started

### Prerequisites

- Python 3.10 or higher
- ElevenLabs API key
- (Optional) OpenAI API key for enhanced analysis

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
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_AGENT_ID=your_agent_id
OPENAI_API_KEY=your_openai_api_key  # Optional
SECRET_KEY=a_random_secret_key
```

5. Download NLTK resources (if using NLP features):

```bash
python nltk_setup.py
```

### Running the Application

Start the development server:

```bash
python run.py
```

Access the application at http://localhost:3000 or http://localhost:8080 (check the console output for the actual port).

### Running Tests

Run the test suite:

```bash
python run_tests.py
```

Test API integration specifically:

```bash
python test_api_integration.py
```

## Usage

### Dashboard

The dashboard provides an overview of conversation metrics, including:

- Total conversations
- Average duration
- Completion rate
- Time-of-day distribution
- Day-of-week distribution

### Transcript Viewer

Browse and search conversations with:

- Date range filtering
- Full-text search
- Detailed transcript view
- Sentiment highlighting

### Themes & Sentiment

Analyze the emotional tone and topics of conversations:

- Sentiment trends over time
- Top themes and topics
- Theme-sentiment correlation
- Common questions and concerns

### Engagement Metrics

Visualize engagement metrics with interactive charts:

- Conversation volume over time
- Average call duration
- Time-of-day patterns
- Completion rates

## API Documentation

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for detailed information on the application's REST API.

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
gunicorn -w 4 -b 0.0.0.0:3000 "app:create_app()"
```

2. Set up a reverse proxy (e.g., Nginx) to handle static files and SSL termination.

## Development

### Project Structure

```
/
├── app/                      # Main application directory
│   ├── __init__.py           # Application factory
│   ├── routes.py             # Route definitions
│   ├── api/                  # API integration
│   │   ├── elevenlabs_client.py  # ElevenLabs API client
│   │   └── data_processor.py     # Data processing logic
│   ├── services/             # Service layer
│   │   ├── conversation_service.py  # Conversation operations
│   │   ├── analysis_service.py      # Analysis operations
│   │   └── export_service.py        # Export operations
│   ├── utils/                # Utility functions
│   │   ├── cache.py          # Caching utilities
│   │   ├── export.py         # Data export functionality
│   │   └── analysis.py       # Data analysis functionality
│   ├── static/               # Static assets
│   │   ├── css/
│   │   └── js/
│   └── templates/            # HTML templates
├── tests/                    # Test directory
│   ├── unit/                 # Unit tests
│   │   └── services/         # Service tests
│   └── integration/          # Integration tests
├── config.py                 # Configuration settings
├── run.py                    # Application entry point
└── requirements.txt          # Python dependencies
```

### Adding New Features

1. Identify the service layer component to modify
2. Add appropriate test cases
3. Implement the feature
4. Update the documentation

### Coding Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Write comprehensive docstrings
- Add unit tests for new functionality

## Troubleshooting

### Common Issues

- **API Connection Issues**: Verify your API key and network connectivity
- **Missing NLTK Resources**: Run `python nltk_setup.py` to download required resources
- **Port Conflicts**: Change the port in `run.py` if the default port is in use

### Getting Help

- Check the logs in the console output
- Review the API documentation for specific endpoints
- Run the `test_api_integration.py` script to verify API connectivity

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- ElevenLabs for their Conversational Voice Agent API
- The Flask team for the web framework
- Chart.js for data visualization capabilities 