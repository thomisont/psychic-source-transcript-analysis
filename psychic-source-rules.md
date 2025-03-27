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