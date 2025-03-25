# Psychic Source Transcript Analysis Tool

A web application for retrieving, analyzing, and visualizing conversation data from the ElevenLabs Conversational Voice Agent "Lily" (ID: 3HFVw3nTZfIivPaHr3ne).

## Features

- Secure API integration with ElevenLabs
- Conversation data retrieval and filtering
- Sentiment analysis of conversations
- Topic extraction and analysis
- Interactive data visualizations
- Data export in multiple formats (JSON, CSV, Markdown)

## Technology Stack

- **Backend**: Flask, Pandas, NumPy, TextBlob, NLTK
- **Frontend**: Bootstrap 5, Chart.js, DataTables.js
- **APIs**: ElevenLabs Conversational Voice Agent API

## Installation

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/psychic-source-transcript-analysis-tool.git
   cd psychic-source-transcript-analysis-tool
   ```

2. Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on `.env.example` and add your ElevenLabs API key:
   ```
   FLASK_APP=run.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key-here
   ELEVENLABS_API_KEY=your-elevenlabs-api-key-here
   ELEVENLABS_AGENT_ID=3HFVw3nTZfIivPaHr3ne
   ```

5. Run the application:
   ```bash
   flask run
   ```

6. Access the application at http://localhost:5000

### Replit Deployment

1. Fork the repository and import to Replit
2. Set environment variables in Replit Secrets:
   - `SECRET_KEY`
   - `ELEVENLABS_API_KEY`
   - `ELEVENLABS_AGENT_ID` 
3. The application will automatically use port 8080 in Replit

## Usage

1. **Dashboard**: View recent activity and quick actions
2. **Data Selection**: Select and filter conversation data by date range
3. **Analysis**: Analyze individual conversations for sentiment and topics
4. **Visualization**: View aggregated data visualizations for multiple conversations

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [ElevenLabs](https://elevenlabs.io) for the Conversational Voice Agent API
- [Flask](https://flask.palletsprojects.com) for the web framework
- [Chart.js](https://www.chartjs.org) for visualizations
- [Bootstrap](https://getbootstrap.com) for the UI framework 