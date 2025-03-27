# Core Project Requirements - NO SAMPLE DATA

1. NEVER include sample, mock, or demo data generation in the codebase
2. Always use real data from API endpoints or proper fallbacks
3. Handle missing data with appropriate empty states, not generated data
4. Show informative error messages rather than placeholder data
5. Ensure all visualizations show empty states for missing data
6. Display actual API counts - do not fabricate statistics
7. Use loading indicators instead of placeholder content
8. Implement proper error boundaries and recovery options

# Implementation Guidelines

## Development Workflow

- NEVER start the server inside Cursor until the user explicitly requests it
- Always wait for user approval before applying changes that affect the running application
- Allow the user to review and accept/reject proposed changes before restarting the server
- Make code changes in a way that allows proper review before execution

## Data Handling

- Never generate random data for charts or displays
- Show "No data available" messages when API returns empty results
- Validate all API responses before displaying
- Log errors but don't generate fake data to compensate

## User Interface

- Design proper empty states for all data visualizations
- Create informative error messages for API failures
- Use standard Bootstrap components for consistent styling
- Implement loading indicators during API requests

## JavaScript Best Practices

- Validate data before rendering charts
- Display empty state UI instead of generating random data
- Add timeout handling for all async operations
- Use feature detection rather than browser detection
- Separate concerns between JS, templates, and Flask routes 

## LLM Integration Best Practices

- Set ConversationAnalyzer's lightweight_mode to false for full LLM-powered analysis
- Implement comprehensive normalization for LLM responses to handle various output formats
- Add robust error handling for OpenAI API failures with appropriate fallbacks
- Use specific prompt templates designed for each analysis type (themes, questions, concerns)
- Implement response data structure parsing that can handle inconsistent outputs
- Apply a modular approach to LLM analysis with dedicated methods for different insights
- Handle incomplete or unexpected LLM responses gracefully
- Add detailed error logging for easier debugging of LLM integration issues
- For UI components showing LLM-generated insights:
  - Use appropriate component types for different data structures (accordions for questions, lists for concerns)
  - Ensure responsive design for complex nested components
  - Implement specialized empty states for each analysis section
  - Create timeline-style displays for conversation excerpts 