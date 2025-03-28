# Deployment Guide for How's Lily Doing

This guide provides instructions for deploying the application to production and switching between development and production environments.

## Environment Setup

### Required Environment Variables

For both development and production, you need these core environment variables:

```
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_AGENT_ID=your_agent_id
OPENAI_API_KEY=your_openai_api_key
SECRET_KEY=a_strong_random_key
```

### Development Environment (Default)

In development mode, the application runs with:
- Debug mode enabled
- CORS allowing all origins
- Default URL: http://localhost:5000

To run in development mode:
```
FLASK_ENV=development
# BASE_URL is optional in development, defaults to http://localhost:5000
```

### Production Environment

In production mode, the application:
- Disables debug mode
- Restricts CORS to the production domain
- Uses https://howislilydoing.org as the default URL

To configure for production:
```
FLASK_ENV=production
# Optional: BASE_URL defaults to https://howislilydoing.org
```

## Replit Deployment Procedure

1. Go to your Replit project dashboard
2. Navigate to the "Secrets" tab
3. Add the following secrets:
   - `FLASK_ENV` = `production`
   - `SECRET_KEY` = (generate a strong random key)
   - `ELEVENLABS_API_KEY` = (your ElevenLabs API key)
   - `ELEVENLABS_AGENT_ID` = (your agent ID)
   - `OPENAI_API_KEY` = (your OpenAI API key)
   - `BASE_URL` = (optional, defaults to https://howislilydoing.org)

4. Deploy using the Replit deployment feature
5. Set up your custom domain (howislilydoing.org) in Replit's domain settings

## Switching Between Environments

### Local Development After Deployment

After deploying to production, you can continue local development by:

1. Using a `.env` file with:
   ```
   FLASK_ENV=development
   SECRET_KEY=dev_key_for_testing
   ELEVENLABS_API_KEY=your_key
   ELEVENLABS_AGENT_ID=your_agent_id
   OPENAI_API_KEY=your_key
   ```

2. Run the application locally:
   ```
   flask run
   ```

### Updating Production

To update the production deployment:

1. Push your changes to the repository
2. In Replit, pull the latest changes
3. Click "Deploy" in the Replit interface

The application will automatically detect that it's in production mode and configure itself accordingly.

## Troubleshooting

If your deployment has issues:

1. Check the Replit logs for errors
2. Verify all required secrets are set
3. Ensure FLASK_ENV is set to "production"
4. If CORS issues occur, verify your domain is properly configured in the BASE_URL 