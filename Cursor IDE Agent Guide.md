       function createTopicHeatMap() {
           // Destroy existing chart if it exists
           if (charts.topicHeatMap) {
               charts.topicHeatMap.destroy();
           }
           
           // Sample data - would be replaced with actual data
           const ctx = document.getElementById('topicHeatMap').getContext('2d');
           
           charts.topicHeatMap = new Chart(ctx, {
               type: 'bar',
               data: {
                   labels: ['readings', 'future', 'love', 'career', 'family', 'money', 'health', 'relationships', 'travel', 'spirituality'],
                   datasets: [{
                       label: 'Topic Frequency',
                       data: [85, 72, 65, 58, 45, 42, 38, 35, 30, 28],
                       backgroundColor: 'rgba(54, 162, 235, 0.5)',
                       borderColor: 'rgba(54, 162, 235, 1)',
                       borderWidth: 1
                   }]
               },
               options: {
                   indexAxis: 'y',
                   responsive: true,
                   maintainAspectRatio: false
               }
           });
       }
   </script>
   {% endblock %}
   ```

### 7. Static Files

1. Create app/static/css/style.css:
   ```css
   /* Custom Styles for Psychic Source Transcript Analysis Tool */

   /* Main layout styles */
   body {
       background-color: #f8f9fa;
       font-family: 'Inter', sans-serif;
   }

   /* Navbar customization */
   .navbar-brand {
       font-weight: 600;
   }

   /* Card styling */
   .card {
       border-radius: 0.5rem;
       box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
       margin-bottom: 1.5rem;
       border: none;
   }

   .card-header {
       border-radius: 0.5rem 0.5rem 0 0 !important;
       border-bottom: none;
   }

   /* Theme colors */
   :root {
       --primary-color: #6a4c93;
       --secondary-color: #f8961e;
       --accent-color: #f9c74f;
       --light-color: #f9f7fd;
       --dark-color: #433770;
   }

   /* Custom primary color */
   .bg-primary {
       background-color: var(--primary-color) !important;
   }

   .btn-primary {
       background-color: var(--primary-color);
       border-color: var(--primary-color);
   }

   .btn-primary:hover {
       background-color: var(--dark-color);
       border-color: var(--dark-color);
   }

   /* Dashboard widgets */
   .dashboard-widget {
       transition: transform 0.2s;
   }

   .dashboard-widget:hover {
       transform: translateY(-5px);
   }

   /* Conversation transcript styling */
   .conversation-transcript {
       max-height: 400px;
       overflow-y: auto;
       padding: 1rem;
       background-color: #f9f9f9;
       border-radius: 0.5rem;
   }

   .message {
       margin-bottom: 1rem;
   }

   /* Footer styling */
   .footer {
       margin-top: 3rem;
       padding: 1.5rem 0;
       background-color: #f9f9f9;
   }
   ```

2. Create app/static/js/main.js:
   ```javascript
   /**
    * Main JavaScript file for Psychic Source Transcript Analysis Tool
    */

   // Format date objects for display
   function formatDate(dateString) {
       const date = new Date(dateString);
       return date.toLocaleString();
   }

   // Format seconds as minutes:seconds
   function formatDuration(seconds) {
       const minutes = Math.floor(seconds / 60);
       const remainingSeconds = seconds % 60;
       return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
   }

   // Map sentiment score to text description
   function sentimentToText(score) {
       if (score > 0.5) return 'Very Positive';
       if (score > 0.1) return 'Positive';
       if (score > -0.1) return 'Neutral';
       if (score > -0.5) return 'Negative';
       return 'Very Negative';
   }

   // Get color for sentiment score
   function sentimentToColor(score) {
       if (score > 0.5) return '#28a745'; // green
       if (score > 0.1) return '#5cb85c'; // light green
       if (score > -0.1) return '#ffc107'; // yellow
       if (score > -0.5) return '#ff9800'; // orange
       return '#dc3545'; // red
   }

   // Copy text to clipboard
   function copyToClipboard(text) {
       navigator.clipboard.writeText(text)
           .then(() => {
               // Show success message
               const toast = document.createElement('div');
               toast.classList.add('toast', 'align-items-center', 'text-white', 'bg-success', 'border-0');
               toast.setAttribute('role', 'alert');
               toast.setAttribute('aria-live', 'assertive');
               toast.setAttribute('aria-atomic', 'true');
               
               toast.innerHTML = `
                   <div class="d-flex">
                       <div class="toast-body">
                           <i class="fas fa-check-circle me-2"></i>Copied to clipboard!
                       </div>
                       <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                   </div>
               `;
               
               document.body.appendChild(toast);
               const bsToast = new bootstrap.Toast(toast);
               bsToast.show();
               
               // Remove toast after it's hidden
               toast.addEventListener('hidden.bs.toast', function() {
                   document.body.removeChild(toast);
               });
           })
           .catch(err => {
               console.error('Failed to copy text: ', err);
           });
   }
   ```

---

## Deployment Guide

### 1. Local Development Deployment

1. Clone the repository (after creating it on GitHub):
   ```bash
   git clone https://github.com/yourusername/psychic-source-tool.git
   cd psychic-source-tool
   ```

2. Set up virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a .env file with your API keys:
   ```
   FLASK_APP=run.py
   FLASK_ENV=development
   ELEVENLABS_API_KEY=your_api_key_here
   ELEVENLABS_AGENT_ID=3HFVw3nTZfIivPaHr3ne
   ```

5. Run the application:
   ```bash
   flask run
   ```

6. Access the application at http://localhost:5000

### 2. Replit Deployment

1. Create a new Repl on Replit:
   - Choose "Python" as the template
   - Connect to your GitHub repository

2. Set environment variables in Replit Secrets:
   - Go to "Secrets" (padlock icon)
   - Add the following secrets:
     - `ELEVENLABS_API_KEY`: Your ElevenLabs API key
     - `ELEVENLABS_AGENT_ID`: The Agent ID (3HFVw3nTZfIivPaHr3ne)

3. Create a `.replit` file in the root directory:
   ```
   language = "python3"
   run = "python run.py"
   ```

4. Create a `pyproject.toml` file for dependency management:
   ```toml
   [tool.poetry]
   name = "psychic-source-tool"
   version = "0.1.0"
   description = "Psychic Source Transcript Analysis Tool"
   authors = ["Your Name <your.email@example.com>"]

   [tool.poetry.dependencies]
   python = "^3.8"
   flask = "^2.0.1"
   pandas = "^1.3.3"
   numpy = "^1.21.2"
   requests = "^2.26.0"
   python-dotenv = "^0.19.0"
   textblob = "^0.15.3"
   nltk = "^3.6.5"
   scikit-learn = "^1.0.0"
   matplotlib = "^3.4.3"
   flask-cors = "^3.0.10"
   flask-wtf = "^1.0.0"

   [build-system]
   requires = ["poetry-core>=1.0.0"]
   build-backend = "poetry.core.masonry.api"
   ```

5. Update the run.py file to work with Replit:
   ```python
   from app import create_app

   app = create_app()

   if __name__ == '__main__':
       # Replit specific configuration
       app.run(host='0.0.0.0', port=8080)
   ```

6. Click "Run" in Replit to start the application

---

## Recommended Additional Features

### 1. Advanced Analytics

1. **Conversation Flow Analysis**:
   - Track conversation paths and identify common patterns
   - Detect where users commonly drop off or request clarification

2. **Agent Performance Metrics**:
   - Response quality assessment
   - Effectiveness at resolving user queries
   - First-call resolution rates

3. **User Intent Classification**:
   - Train ML models to categorize user requests
   - Identify emerging topics or concerns

### 2. Integration Possibilities

1. **Dashboard Exports**:
   - Allow scheduled reports to be sent via email
   - Export visualizations as images or PDF reports

2. **User Authentication**:
   - Add user accounts for team members
   - Role-based access control

3. **Automated Alerts**:
   - Set up threshold-based alerts for negative sentiment
   - Monitor conversation volume spikes

---

## Maintenance and Future Development

### 1. Code Structure Improvements

- Implement proper error handling and logging
- Add comprehensive unit tests
- Set up CI/CD pipeline for automated testing and deployment

### 2. Performance Optimization

- Implement caching for API responses
- Optimize database queries when handling large datasets
- Consider pagination and lazy loading for large result sets

### 3. Security Considerations

- Implement rate limiting
- Add CSRF protection
- Secure sensitive endpoints with authentication
- Sanitize all user inputs

---

## Conclusion

This design document provides a comprehensive guide for developing the Psychic Source Transcript Analysis Tool. The web-based application will enable users to retrieve, analyze, and visualize conversation data from the ElevenLabs Conversational Voice Agent "Lily." The tool is designed to be deployed both locally and on Replit, with a focus on ease of use, security, and analytical capabilities.

The implementation includes:
- Flask-based web application with Bootstrap 5 UI
- Secure API integration with ElevenLabs
- Multiple data export formats (JSON, CSV, Markdown)
- Advanced data analysis capabilities (sentiment, topics)
- Interactive data visualizations with Chart.js

By following this guide, developers can build a powerful tool for understanding and improving voice agent interactions, leading to better customer experiences and more effective agent performance.
                               callback: function(value) {
                                   if (value === 1) return 'Very Positive';
                                   if (value === 0.5) return 'Positive';
                                   if (value === 0) return 'Neutral';
                                   if (value === -0.5) return 'Negative';
                                   if (value === -1) return 'Very Negative';
                                   return '';
                               }
                           }
                       }
                   }
               }
           });
       }
       
       function createTopicsChart(topicsData) {
           // Destroy existing chart if it exists
           if (topicsChart) {
               topicsChart.destroy();
           }
           
           // Extract data for chart
           const labels = topicsData.slice(0, 7).map(item => item[0]);
           const counts = topicsData.slice(0, 7).map(item => item[1]);
           
           const ctx = document.getElementById('topics-chart').getContext('2d');
           
           topicsChart = new Chart(ctx, {
               type: 'bar',
               data: {
                   labels: labels,
                   datasets: [{
                       label: 'Occurrence Count',
                       data: counts,
                       backgroundColor: 'rgba(54, 162, 235, 0.5)',
                       borderColor: 'rgba(54, 162, 235, 1)',
                       borderWidth: 1
                   }]
               },
               options: {
                   responsive: true,
                   scales: {
                       y: {
                           beginAtZero: true,
                           ticks: {
                               precision: 0
                           }
                       }
                   }
               }
           });
       }
       
       function displayTopTopics(topicsData) {
           const topicsContainer = document.getElementById('top-topics');
           topicsContainer.innerHTML = '';
           
           // Create badge for each topic
           topicsData.forEach(topic => {
               const [word, count] = topic;
               const badge = document.createElement('span');
               badge.className = 'badge bg-primary fs-6 p-2';
               badge.textContent = `${word} (${count})`;
               topicsContainer.appendChild(badge);
           });
       }
   </script>
   {% endblock %}
   ```

6. Create app/templates/visualization.html:
   ```html
   {% extends "base.html" %}

   {% block title %}Visualization - Psychic Source Analyzer{% endblock %}

   {% block content %}
   <div class="row">
       <div class="col-12">
           <div class="card shadow-sm">
               <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                   <h5 class="card-title mb-0">
                       <i class="fas fa-chart-pie me-2"></i>Data Visualization
                   </h5>
                   <div>
                       <button type="button" class="btn btn-light btn-sm" data-bs-toggle="modal" data-bs-target="#filterModal">
                           <i class="fas fa-filter me-1"></i>Filter Data
                       </button>
                   </div>
               </div>
               <div class="card-body">
                   <div class="row">
                       <div class="col-md-6 mb-4">
                           <div class="card h-100">
                               <div class="card-header">
                                   <h5 class="card-title mb-0">Conversation Volume</h5>
                               </div>
                               <div class="card-body">
                                   <canvas id="volumeChart" height="250"></canvas>
                               </div>
                           </div>
                       </div>
                       
                       <div class="col-md-6 mb-4">
                           <div class="card h-100">
                               <div class="card-header">
                                   <h5 class="card-title mb-0">Average Duration</h5>
                               </div>
                               <div class="card-body">
                                   <canvas id="durationChart" height="250"></canvas>
                               </div>
                           </div>
                       </div>
                   </div>
                   
                   <div class="row">
                       <div class="col-md-4 mb-4">
                           <div class="card h-100">
                               <div class="card-header">
                                   <h5 class="card-title mb-0">Time of Day Distribution</h5>
                               </div>
                               <div class="card-body">
                                   <canvas id="timeOfDayChart" height="250"></canvas>
                               </div>
                           </div>
                       </div>
                       
                       <div class="col-md-4 mb-4">
                           <div class="card h-100">
                               <div class="card-header">
                                   <h5 class="card-title mb-0">Day of Week Distribution</h5>
                               </div>
                               <div class="card-body">
                                   <canvas id="dayOfWeekChart" height="250"></canvas>
                               </div>
                           </div>
                       </div>
                       
                       <div class="col-md-4 mb-4">
                           <div class="card h-100">
                               <div class="card-header">
                                   <h5 class="card-title mb-0">Overall Sentiment</h5>
                               </div>
                               <div class="card-body">
                                   <canvas id="sentimentChart" height="250"></canvas>
                               </div>
                           </div>
                       </div>
                   </div>
                   
                   <div class="row">
                       <div class="col-12 mb-4">
                           <div class="card">
                               <div class="card-header">
                                   <h5 class="card-title mb-0">Topic Heat Map</h5>
                               </div>
                               <div class="card-body">
                                   <canvas id="topicHeatMap" height="300"></canvas>
                               </div>
                           </div>
                       </div>
                   </div>
               </div>
           </div>
       </div>
   </div>

   <!-- Filter Modal -->
   <div class="modal fade" id="filterModal" tabindex="-1" aria-hidden="true">
       <div class="modal-dialog">
           <div class="modal-content">
               <div class="modal-header bg-primary text-white">
                   <h5 class="modal-title">Filter Visualization Data</h5>
                   <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
               </div>
               <div class="modal-body">
                   <form id="visualization-filter-form">
                       <div class="mb-3">
                           <label for="viz-start-date" class="form-label">Start Date</label>
                           <input type="date" class="form-control" id="viz-start-date" name="start_date">
                       </div>
                       <div class="mb-3">
                           <label for="viz-end-date" class="form-label">End Date</label>
                           <input type="date" class="form-control" id="viz-end-date" name="end_date">
                       </div>
                   </form>
               </div>
               <div class="modal-footer">
                   <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                   <button type="button" class="btn btn-primary" id="apply-filter-button">Apply Filters</button>
               </div>
           </div>
       </div>
   </div>
   {% endblock %}

   {% block scripts %}
   <script>
       let charts = {};
       
       document.addEventListener('DOMContentLoaded', function() {
           // Set default date range (last 30 days)
           const endDate = new Date();
           const startDate = new Date();
           startDate.setDate(startDate.getDate() - 30);
           
           document.getElementById('viz-start-date').value = startDate.toISOString().split('T')[0];
           document.getElementById('viz-end-date').value = endDate.toISOString().split('T')[0];
           
           // Load initial visualization data
           loadVisualizationData();
           
           // Set up event listener for filter button
           document.getElementById('apply-filter-button').addEventListener('click', function() {
               $('#filterModal').modal('hide');
               loadVisualizationData();
           });
       });
       
       function loadVisualizationData() {
           const startDate = document.getElementById('viz-start-date').value;
           const endDate = document.getElementById('viz-end-date').value;
           
           // Make API request to get conversation data
           fetch(`/api/conversations?start_date=${startDate}&end_date=${endDate}&limit=1000`)
               .then(response => response.json())
               .then(data => {
                   // Process and visualize data
                   createVisualizations(data.data);
               })
               .catch(error => {
                   console.error('Error fetching visualization data:', error);
                   alert('Failed to load visualization data. Please try again.');
               });
       }
       
       function createVisualizations(data) {
           // Sample data for visualizations
           // In a real application, this would process the actual API data
           
           // Create volume chart
           createVolumeChart();
           
           // Create duration chart
           createDurationChart();
           
           // Create time of day distribution chart
           createTimeOfDayChart();
           
           // Create day of week distribution chart
           createDayOfWeekChart();
           
           // Create sentiment chart
           createSentimentChart();
           
           // Create topic heat map
           createTopicHeatMap();
       }
       
       function createVolumeChart() {
           // Destroy existing chart if it exists
           if (charts.volumeChart) {
               charts.volumeChart.destroy();
           }
           
           // Sample data - would be replaced with actual data
           const ctx = document.getElementById('volumeChart').getContext('2d');
           
           charts.volumeChart = new Chart(ctx, {
               type: 'line',
               data: {
                   labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                   datasets: [{
                       label: 'Number of Conversations',
                       data: [65, 78, 52, 84],
                       backgroundColor: 'rgba(75, 192, 192, 0.2)',
                       borderColor: 'rgba(75, 192, 192, 1)',
                       tension: 0.3,
                       fill: true
                   }]
               },
               options: {
                   responsive: true,
                   maintainAspectRatio: false
               }
           });
       }
       
       function createDurationChart() {
           // Destroy existing chart if it exists
           if (charts.durationChart) {
               charts.durationChart.destroy();
           }
           
           // Sample data - would be replaced with actual data
           const ctx = document.getElementById('durationChart').getContext('2d');
           
           charts.durationChart = new Chart(ctx, {
               type: 'bar',
               data: {
                   labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                   datasets: [{
                       label: 'Average Duration (seconds)',
                       data: [240, 325, 280, 310],
                       backgroundColor: 'rgba(54, 162, 235, 0.5)',
                       borderColor: 'rgba(54, 162, 235, 1)',
                       borderWidth: 1
                   }]
               },
               options: {
                   responsive: true,
                   maintainAspectRatio: false
               }
           });
       }
       
       function createTimeOfDayChart() {
           // Destroy existing chart if it exists
           if (charts.timeOfDayChart) {
               charts.timeOfDayChart.destroy();
           }
           
           // Sample data - would be replaced with actual data
           const ctx = document.getElementById('timeOfDayChart').getContext('2d');
           
           charts.timeOfDayChart = new Chart(ctx, {
               type: 'doughnut',
               data: {
                   labels: ['Morning', 'Afternoon', 'Evening', 'Night'],
                   datasets: [{
                       data: [25, 40, 30, 5],
                       backgroundColor: [
                           'rgba(255, 206, 86, 0.5)',
                           'rgba(75, 192, 192, 0.5)',
                           'rgba(153, 102, 255, 0.5)',
                           'rgba(54, 162, 235, 0.5)'
                       ],
                       borderWidth: 1
                   }]
               },
               options: {
                   responsive: true,
                   maintainAspectRatio: false
               }
           });
       }
       
       function createDayOfWeekChart() {
           // Destroy existing chart if it exists
           if (charts.dayOfWeekChart) {
               charts.dayOfWeekChart.destroy();
           }
           
           // Sample data - would be replaced with actual data
           const ctx = document.getElementById('dayOfWeekChart').getContext('2d');
           
           charts.dayOfWeekChart = new Chart(ctx, {
               type: 'polarArea',
               data: {
                   labels: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
                   datasets: [{
                       data: [10, 15, 20, 25, 20, 18, 12],
                       backgroundColor: [
                           'rgba(255, 99, 132, 0.5)',
                           'rgba(255, 159, 64, 0.5)',
                           'rgba(255, 205, 86, 0.5)',
                           'rgba(75, 192, 192, 0.5)',
                           'rgba(54, 162, 235, 0.5)',
                           'rgba(153, 102, 255, 0.5)',
                           'rgba(201, 203, 207, 0.5)'
                       ]
                   }]
               },
               options: {
                   responsive: true,
                   maintainAspectRatio: false
               }
           });
       }
       
       function createSentimentChart() {
           // Destroy existing chart if it exists
           if (charts.sentimentChart) {
               charts.sentimentChart.destroy();
           }
           
           // Sample data - would be replaced with actual data
           const ctx = document.getElementById('sentimentChart').getContext('2d');
           
           charts.sentimentChart = new Chart(ctx, {
               type: 'pie',
               data: {
                   labels: ['Positive', 'Neutral', 'Negative'],
                   datasets: [{
                       data: [60, 30, 10],
                       backgroundColor: [
                           'rgba(75, 192, 192, 0.5)',
                           'rgba(255, 205, 86, 0.5)',
                           'rgba(255, 99, 132, 0.5)'
                       ]
                   }]
               },
               options: {
                   responsive: true,
                   maintainAspectRatio: false
               }
           });
       }
       
       function createTopicHeat           // Handle conversation analyze button
           $('#conversations-table').on('click', '.analyze-conversation', function() {
               const conversationId = $(this).data('id');
               window.location.href = `/analysis?conversation_id=${conversationId}`;
           });
           
           // Handle export conversation
           $('.export-conversation').on('click', function(e) {
               e.preventDefault();
               const format = $(this).data('format');
               if (currentConversationId) {
                   window.location.href = `/api/export/${format}?type=conversation&conversation_id=${currentConversationId}`;
               }
           });
           
           // Handle bulk export
           document.getElementById('export-button').addEventListener('click', function() {
               const format = document.querySelector('input[name="export-format"]:checked').value;
               const startDate = document.getElementById('start-date').value;
               const endDate = document.getElementById('end-date').value;
               
               window.location.href = `/api/export/${format}?type=conversations&start_date=${startDate}&end_date=${endDate}`;
               
               // Close the modal
               $('#exportModal').modal('hide');
           });
       });
       
       function loadConversations() {
           const startDate = document.getElementById('start-date').value;
           const endDate = document.getElementById('end-date').value;
           
           // Clear existing data
           dataTable.clear();
           
           // Show loading indicator
           dataTable.draw();
           
           // Make API request
           fetch(`/api/conversations?start_date=${startDate}&end_date=${endDate}`)
               .then(response => response.json())
               .then(data => {
                   // Format dates
                   data.data.forEach(item => {
                       item.start_time = new Date(item.start_time).toLocaleString();
                       item.end_time = new Date(item.end_time).toLocaleString();
                   });
                   
                   // Add data to table
                   dataTable.rows.add(data.data).draw();
               })
               .catch(error => {
                   console.error('Error fetching conversations:', error);
                   alert('Failed to load conversation data. Please try again.');
               });
       }
       
       function viewConversation(conversationId) {
           // Store the current conversation ID
           currentConversationId = conversationId;
           
           // Clear the modal content
           document.getElementById('conversation-details-content').innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
           
           // Show the modal
           $('#conversationModal').modal('show');
           
           // Fetch conversation details
           fetch(`/api/conversations/${conversationId}`)
               .then(response => response.json())
               .then(data => {
                   // Format the transcript
                   let html = `
                       <div class="mb-3">
                           <h5>Conversation ID: ${data.conversation_id}</h5>
                           <p>
                               <strong>Start Time:</strong> ${new Date(data.start_time).toLocaleString()}<br>
                               <strong>End Time:</strong> ${new Date(data.end_time).toLocaleString()}<br>
                               <strong>Duration:</strong> ${data.duration} seconds<br>
                               <strong>Status:</strong> ${data.status}
                           </p>
                       </div>
                       <h5>Transcript</h5>
                       <div class="conversation-transcript">
                   `;
                   
                   // Add transcript messages
                   data.transcript.forEach(turn => {
                       const isAgent = turn.speaker === 'Agent';
                       const bgColor = isAgent ? 'bg-light' : 'bg-primary bg-opacity-10';
                       const textAlign = isAgent ? 'text-start' : 'text-end';
                       
                       html += `
                           <div class="message ${textAlign} mb-3">
                               <div class="d-inline-block ${bgColor} p-3 rounded">
                                   <div class="small text-muted mb-1">${turn.speaker} - ${new Date(turn.timestamp).toLocaleString()}</div>
                                   <div>${turn.text}</div>
                               </div>
                           </div>
                       `;
                   });
                   
                   html += `</div>`;
                   
                   // Update the modal content
                   document.getElementById('conversation-details-content').innerHTML = html;
               })
               .catch(error => {
                   console.error('Error fetching conversation details:', error);
                   document.getElementById('conversation-details-content').innerHTML = '<div class="alert alert-danger">Failed to load conversation details. Please try again.</div>';
               });
       }
   </script>
   {% endblock %}
   ```

5. Create app/templates/analysis.html:
   ```html
   {% extends "base.html" %}

   {% block title %}Analysis - Psychic Source Analyzer{% endblock %}

   {% block content %}
   <div class="row">
       <div class="col-12">
           <div class="card shadow-sm">
               <div class="card-header bg-primary text-white">
                   <h5 class="card-title mb-0">
                       <i class="fas fa-chart-bar me-2"></i>Conversation Analysis
                   </h5>
               </div>
               <div class="card-body">
                   <div id="analysis-container">
                       <div class="text-center py-5" id="analysis-placeholder">
                           <i class="fas fa-chart-line fa-3x mb-3 text-muted"></i>
                           <h4 class="text-muted">Select a conversation to analyze</h4>
                           <p class="text-muted">You can select a conversation from the <a href="{{ url_for('main.data_selection') }}">Data Selection</a> page.</p>
                       </div>
                       
                       <div id="analysis-content" class="d-none">
                           <div class="row">
                               <div class="col-md-12 mb-4">
                                   <h3 id="conversation-title">Conversation Analysis</h3>
                                   <div id="conversation-info" class="small text-muted"></div>
                               </div>
                           </div>
                           
                           <div class="row">
                               <div class="col-md-6 mb-4">
                                   <div class="card h-100">
                                       <div class="card-header">
                                           <h5 class="card-title mb-0">Sentiment Analysis</h5>
                                       </div>
                                       <div class="card-body">
                                           <div class="mb-3">
                                               <div class="d-flex justify-content-between align-items-center mb-1">
                                                   <span>Overall Sentiment:</span>
                                                   <span id="overall-sentiment-value" class="badge bg-primary">0</span>
                                               </div>
                                               <div class="progress" style="height: 20px;">
                                                   <div id="overall-sentiment-bar" class="progress-bar" role="progressbar" style="width: 50%"></div>
                                               </div>
                                           </div>
                                           
                                           <div class="mb-3">
                                               <div class="d-flex justify-content-between align-items-center mb-1">
                                                   <span>User Sentiment:</span>
                                                   <span id="user-sentiment-value" class="badge bg-primary">0</span>
                                               </div>
                                               <div class="progress" style="height: 20px;">
                                                   <div id="user-sentiment-bar" class="progress-bar bg-info" role="progressbar" style="width: 50%"></div>
                                               </div>
                                           </div>
                                           
                                           <div class="mb-3">
                                               <div class="d-flex justify-content-between align-items-center mb-1">
                                                   <span>Agent Sentiment:</span>
                                                   <span id="agent-sentiment-value" class="badge bg-primary">0</span>
                                               </div>
                                               <div class="progress" style="height: 20px;">
                                                   <div id="agent-sentiment-bar" class="progress-bar bg-success" role="progressbar" style="width: 50%"></div>
                                               </div>
                                           </div>
                                           
                                           <div class="mt-4">
                                               <h6>Sentiment Progression</h6>
                                               <canvas id="sentiment-chart" height="200"></canvas>
                                           </div>
                                       </div>
                                   </div>
                               </div>
                               
                               <div class="col-md-6 mb-4">
                                   <div class="card h-100">
                                       <div class="card-header">
                                           <h5 class="card-title mb-0">Topic Analysis</h5>
                                       </div>
                                       <div class="card-body">
                                           <div class="mb-3">
                                               <canvas id="topics-chart" height="200"></canvas>
                                           </div>
                                           
                                           <div class="mt-4">
                                               <h6>Top Topics</h6>
                                               <div id="top-topics" class="d-flex flex-wrap gap-2 mt-2">
                                                   <!-- Topics will be added here -->
                                               </div>
                                           </div>
                                       </div>
                                   </div>
                               </div>
                           </div>
                       </div>
                   </div>
               </div>
           </div>
       </div>
   </div>
   {% endblock %}

   {% block scripts %}
   <script>
       let sentimentChart = null;
       let topicsChart = null;
       
       document.addEventListener('DOMContentLoaded', function() {
           // Check if we have a conversation ID in the URL
           const urlParams = new URLSearchParams(window.location.search);
           const conversationId = urlParams.get('conversation_id');
           
           if (conversationId) {
               loadConversationAnalysis(conversationId);
           }
       });
       
       function loadConversationAnalysis(conversationId) {
           // Show loading state
           document.getElementById('analysis-placeholder').innerHTML = '<div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-3">Loading analysis...</p>';
           
           // Fetch conversation details
           fetch(`/api/conversations/${conversationId}`)
               .then(response => response.json())
               .then(convData => {
                   // Fetch analysis data
                   return fetch(`/api/conversations/${conversationId}/analysis`)
                       .then(response => response.json())
                       .then(analysisData => {
                           // We have both conversation details and analysis data
                           displayAnalysis(convData, analysisData);
                       });
               })
               .catch(error => {
                   console.error('Error loading analysis:', error);
                   document.getElementById('analysis-placeholder').innerHTML = '<div class="alert alert-danger">Failed to load analysis. Please try again.</div>';
               });
       }
       
       function displayAnalysis(conversationData, analysisData) {
           // Hide placeholder, show content
           document.getElementById('analysis-placeholder').classList.add('d-none');
           document.getElementById('analysis-content').classList.remove('d-none');
           
           // Set conversation info
           document.getElementById('conversation-title').textContent = `Analysis for Conversation #${conversationData.conversation_id.substring(0, 8)}...`;
           document.getElementById('conversation-info').textContent = `${new Date(conversationData.start_time).toLocaleString()} · ${conversationData.duration} seconds · ${conversationData.transcript.length} turns`;
           
           // Update sentiment values
           const overallSentiment = analysisData.sentiment.overall;
           const userSentiment = analysisData.sentiment.user_sentiment;
           const agentSentiment = analysisData.sentiment.agent_sentiment;
           
           // Display sentiment values
           document.getElementById('overall-sentiment-value').textContent = overallSentiment.toFixed(2);
           document.getElementById('user-sentiment-value').textContent = userSentiment.toFixed(2);
           document.getElementById('agent-sentiment-value').textContent = agentSentiment.toFixed(2);
           
           // Update sentiment bars
           const normalizedOverall = ((overallSentiment + 1) / 2) * 100;
           const normalizedUser = ((userSentiment + 1) / 2) * 100;
           const normalizedAgent = ((agentSentiment + 1) / 2) * 100;
           
           document.getElementById('overall-sentiment-bar').style.width = `${normalizedOverall}%`;
           document.getElementById('user-sentiment-bar').style.width = `${normalizedUser}%`;
           document.getElementById('agent-sentiment-bar').style.width = `${normalizedAgent}%`;
           
           // Set sentiment bar colors
           setSentimentColor('overall-sentiment-bar', overallSentiment);
           setSentimentColor('user-sentiment-bar', userSentiment);
           setSentimentColor('agent-sentiment-bar', agentSentiment);
           
           // Create sentiment progression chart
           const sentimentData = analysisData.sentiment.progression;
           createSentimentChart(sentimentData);
           
           // Create topics chart
           const topicsData = analysisData.topics;
           createTopicsChart(topicsData);
           
           // Display top topics
           displayTopTopics(topicsData);
       }
       
       function setSentimentColor(elementId, sentiment) {
           const element = document.getElementById(elementId);
           
           if (sentiment > 0.33) {
               element.classList.remove('bg-warning', 'bg-danger', 'bg-info');
               element.classList.add('bg-success');
           } else if (sentiment > 0) {
               element.classList.remove('bg-danger', 'bg-success', 'bg-info');
               element.classList.add('bg-warning');
           } else if (sentiment > -0.33) {
               element.classList.remove('bg-success', 'bg-danger', 'bg-warning');
               element.classList.add('bg-info');
           } else {
               element.classList.remove('bg-success', 'bg-warning', 'bg-info');
               element.classList.add('bg-danger');
           }
       }
       
       function createSentimentChart(sentimentData) {
           // Destroy existing chart if it exists
           if (sentimentChart) {
               sentimentChart.destroy();
           }
           
           const ctx = document.getElementById('sentiment-chart').getContext('2d');
           
           sentimentChart = new Chart(ctx, {
               type: 'line',
               data: {
                   labels: Array.from({length: sentimentData.length}, (_, i) => `Turn ${i+1}`),
                   datasets: [{
                       label: 'Sentiment',
                       data: sentimentData,
                       borderColor: 'rgb(75, 192, 192)',
                       tension: 0.1,
                       fill: false
                   }]
               },
               options: {
                   responsive: true,
                   scales: {
                       y: {
                           min: -1,
                           max: 1,
                           ticks: {
                               callback: function(value) {
                                   if (value === 1) return # Psychic Source Transcript Analysis Tool
## Design Document & Development Guide

## Project Overview

The Psychic Source Transcript Analysis Tool is a web application designed to retrieve, analyze, and visualize conversation data from the ElevenLabs Conversational Voice Agent API. This tool will provide an intuitive web interface for selecting, downloading, and analyzing transcript data from the Psychic Source "Lily" agent (ID: 3HFVw3nTZfIivPaHr3ne).

---

## Objectives

1. Create a user-friendly web interface for accessing ElevenLabs conversation data
2. Implement secure API authentication and data retrieval
3. Provide data export in multiple formats (JSON, MD, CSV)
4. Enable advanced data analysis and visualization capabilities
5. Ensure seamless deployment from local development to Replit

---

## Technology Stack

### Backend
- **Language**: Python 3.9+
- **Web Framework**: Flask
- **Data Processing**: Pandas, NumPy
- **API Integration**: Requests, Python-dotenv
- **Analysis Libraries**: TextBlob (sentiment), NLTK (text processing), Scikit-learn (ML capabilities)

### Frontend
- **Framework**: Flask templates with Bootstrap 5
- **JavaScript Libraries**: Chart.js, D3.js (for visualizations)
- **CSS Framework**: Bootstrap 5 with custom theming
- **Data Tables**: DataTables.js

### Development & Deployment
- **Local Development**: Cursor IDE, Python venv
- **Version Control**: Git/GitHub
- **Deployment**: Replit
- **Environment Variables**: Local .env file (development), Replit Secrets (production)

---

## System Architecture

```
┌───────────────────┐      ┌───────────────────┐      ┌───────────────────┐
│                   │      │                   │      │                   │
│  Web Interface    │◄────►│  Flask Backend    │◄────►│  ElevenLabs API   │
│  (HTML/JS/CSS)    │      │  (Python)         │      │                   │
│                   │      │                   │      │                   │
└───────────────────┘      └─────────┬─────────┘      └───────────────────┘
                                     │
                                     ▼
                           ┌───────────────────┐
                           │                   │
                           │  Data Processing  │
                           │  (Pandas/NumPy)   │
                           │                   │
                           └─────────┬─────────┘
                                     │
                                     ▼
                           ┌───────────────────┐
                           │                   │
                           │  Data Export      │
                           │  (JSON/MD/CSV)    │
                           │                   │
                           └───────────────────┘
```

---

## Directory Structure

```
psychic_source_tool/
├── app/
│   ├── __init__.py
│   ├── routes.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── elevenlabs_client.py
│   │   └── data_processor.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── conversation.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── export.py
│   │   └── analysis.py
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── templates/
│       ├── base.html
│       ├── index.html
│       ├── data_selection.html
│       ├── analysis.html
│       └── visualization.html
├── config.py
├── .env
├── .gitignore
├── requirements.txt
└── run.py
```

---

## Detailed Development Guide

### 1. Environment Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install required packages:
   ```bash
   pip install flask pandas numpy requests python-dotenv textblob nltk scikit-learn matplotlib seaborn plotly flask-wtf
   pip install -U flask-cors
   ```

3. Create a requirements.txt file:
   ```bash
   pip freeze > requirements.txt
   ```

4. Create a .env file for local development:
   ```
   FLASK_APP=run.py
   FLASK_ENV=development
   ELEVENLABS_API_KEY=your_api_key_here
   ELEVENLABS_AGENT_ID=3HFVw3nTZfIivPaHr3ne
   ```

5. Create a .gitignore file:
   ```
   venv/
   __pycache__/
   *.pyc
   .env
   .DS_Store
   .vscode/
   ```

### 2. Flask Application Setup

1. Create config.py:
   ```python
   import os
   from dotenv import load_dotenv

   load_dotenv()

   class Config:
       SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-development'
       ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
       ELEVENLABS_AGENT_ID = os.environ.get('ELEVENLABS_AGENT_ID')
       ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"
   ```

2. Create app/__init__.py:
   ```python
   from flask import Flask
   from flask_cors import CORS
   from config import Config

   def create_app(config_class=Config):
       app = Flask(__name__)
       app.config.from_object(config_class)
       CORS(app)

       from app.routes import main_bp
       app.register_blueprint(main_bp)

       return app
   ```

3. Create run.py:
   ```python
   from app import create_app

   app = create_app()

   if __name__ == '__main__':
       app.run(debug=True)
   ```

### 3. API Integration

1. Create app/api/elevenlabs_client.py:
   ```python
   import requests
   from flask import current_app
   import json
   from datetime import datetime

   class ElevenLabsClient:
       def __init__(self, api_key=None, agent_id=None):
           self.api_key = api_key or current_app.config['ELEVENLABS_API_KEY']
           self.agent_id = agent_id or current_app.config['ELEVENLABS_AGENT_ID']
           self.base_url = current_app.config['ELEVENLABS_API_URL']
           self.headers = {
               "xi-api-key": self.api_key,
               "Content-Type": "application/json"
           }

       def get_conversations(self, start_date=None, end_date=None, limit=100, offset=0):
           """
           Retrieve conversation data from ElevenLabs API
           
           Args:
               start_date (str): Start date in YYYY-MM-DD format
               end_date (str): End date in YYYY-MM-DD format
               limit (int): Maximum number of results to return
               offset (int): Offset for pagination
               
           Returns:
               dict: API response containing conversation data
           """
           url = f"{self.base_url}/agents/{self.agent_id}/conversations"
           
           params = {
               "limit": limit,
               "offset": offset
           }
           
           if start_date:
               params["start_date"] = start_date
           if end_date:
               params["end_date"] = end_date
               
           response = requests.get(url, headers=self.headers, params=params)
           
           if response.status_code == 200:
               return response.json()
           else:
               response.raise_for_status()
               
       def get_conversation_details(self, conversation_id):
           """
           Retrieve detailed data for a specific conversation
           
           Args:
               conversation_id (str): The ID of the conversation to retrieve
               
           Returns:
               dict: API response containing conversation details
           """
           url = f"{self.base_url}/agents/{self.agent_id}/conversations/{conversation_id}"
           
           response = requests.get(url, headers=self.headers)
           
           if response.status_code == 200:
               return response.json()
           else:
               response.raise_for_status()
   ```

2. Create app/api/data_processor.py:
   ```python
   import pandas as pd
   from datetime import datetime

   class DataProcessor:
       @staticmethod
       def process_conversations(conversations_data):
           """
           Process the raw conversation data from the API into a pandas DataFrame
           
           Args:
               conversations_data (dict): Raw conversation data from the API
               
           Returns:
               DataFrame: Processed conversation data
           """
           if not conversations_data or 'conversations' not in conversations_data:
               return pd.DataFrame()
               
           conversations = conversations_data['conversations']
           
           # Extract relevant fields
           processed_data = []
           for conv in conversations:
               processed_conv = {
                   'conversation_id': conv.get('id'),
                   'start_time': DataProcessor._parse_timestamp(conv.get('start_time')),
                   'end_time': DataProcessor._parse_timestamp(conv.get('end_time')),
                   'duration': conv.get('duration'),
                   'turn_count': len(conv.get('turns', [])),
                   'status': conv.get('status'),
               }
               processed_data.append(processed_conv)
               
           return pd.DataFrame(processed_data)
           
       @staticmethod
       def process_conversation_details(conversation_details):
           """
           Process the detailed conversation data from the API into a structured format
           
           Args:
               conversation_details (dict): Raw conversation details from the API
               
           Returns:
               dict: Processed conversation details with transcript
           """
           if not conversation_details:
               return {}
               
           turns = conversation_details.get('turns', [])
           
           # Extract transcript
           transcript = []
           for turn in turns:
               speaker = "Agent" if turn.get('is_agent') else "User"
               transcript.append({
                   'speaker': speaker,
                   'text': turn.get('text', ''),
                   'timestamp': DataProcessor._parse_timestamp(turn.get('timestamp'))
               })
               
           # Create structured response
           processed_details = {
               'conversation_id': conversation_details.get('id'),
               'start_time': DataProcessor._parse_timestamp(conversation_details.get('start_time')),
               'end_time': DataProcessor._parse_timestamp(conversation_details.get('end_time')),
               'duration': conversation_details.get('duration'),
               'status': conversation_details.get('status'),
               'transcript': transcript
           }
           
           return processed_details
       
       @staticmethod
       def _parse_timestamp(timestamp_str):
           """Helper method to parse API timestamps"""
           if not timestamp_str:
               return None
           try:
               return datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
           except ValueError:
               try:
                   return datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
               except ValueError:
                   return None
   ```

### 4. Data Export Utilities

1. Create app/utils/export.py:
   ```python
   import json
   import pandas as pd
   import csv
   from io import StringIO

   class DataExporter:
       @staticmethod
       def to_json(data):
           """
           Export data to JSON format
           
           Args:
               data: Data to export (dict or DataFrame)
               
           Returns:
               str: JSON string
           """
           if isinstance(data, pd.DataFrame):
               return data.to_json(orient='records', date_format='iso')
           return json.dumps(data, default=str, indent=2)
           
       @staticmethod
       def to_csv(data):
           """
           Export data to CSV format
           
           Args:
               data: Data to export (dict or DataFrame)
               
           Returns:
               str: CSV string
           """
           if isinstance(data, pd.DataFrame):
               return data.to_csv(index=False)
               
           # Handle dict data
           output = StringIO()
           if isinstance(data, dict):
               writer = csv.DictWriter(output, fieldnames=data.keys())
               writer.writeheader()
               writer.writerow(data)
           elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
               if data:
                   writer = csv.DictWriter(output, fieldnames=data[0].keys())
                   writer.writeheader()
                   writer.writerows(data)
                   
           return output.getvalue()
           
       @staticmethod
       def to_markdown(data):
           """
           Export data to Markdown format
           
           Args:
               data: Data to export (dict, DataFrame, or conversation details)
               
           Returns:
               str: Markdown string
           """
           if isinstance(data, pd.DataFrame):
               return data.to_markdown(index=False)
               
           # Handle conversation details with transcript
           if isinstance(data, dict) and 'transcript' in data:
               md_output = f"# Conversation {data.get('conversation_id')}\n\n"
               md_output += f"**Start Time:** {data.get('start_time')}\n"
               md_output += f"**End Time:** {data.get('end_time')}\n"
               md_output += f"**Duration:** {data.get('duration')} seconds\n"
               md_output += f"**Status:** {data.get('status')}\n\n"
               
               md_output += "## Transcript\n\n"
               for turn in data.get('transcript', []):
                   speaker = turn.get('speaker')
                   text = turn.get('text')
                   timestamp = turn.get('timestamp')
                   md_output += f"**{speaker}** ({timestamp}):\n{text}\n\n"
                   
               return md_output
               
           # Default to JSON representation for other types
           return f"```json\n{DataExporter.to_json(data)}\n```"
   ```

### 5. Data Analysis Utilities

1. Create app/utils/analysis.py:
   ```python
   import pandas as pd
   import numpy as np
   from textblob import TextBlob
   import re
   from collections import Counter

   class ConversationAnalyzer:
       @staticmethod
       def analyze_sentiment(transcript):
           """
           Analyze sentiment of conversation transcript
           
           Args:
               transcript (list): List of conversation turns
               
           Returns:
               dict: Sentiment analysis results
           """
           if not transcript:
               return {'overall': 0, 'progression': [], 'user_sentiment': 0, 'agent_sentiment': 0}
               
           sentiments = []
           user_texts = []
           agent_texts = []
           
           for turn in transcript:
               text = turn.get('text', '')
               sentiment = TextBlob(text).sentiment.polarity
               sentiments.append(sentiment)
               
               if turn.get('speaker') == 'User':
                   user_texts.append(text)
               else:
                   agent_texts.append(text)
                   
           # Calculate overall sentiment
           overall_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
           
           # Calculate user and agent sentiment separately
           user_sentiment = sum([TextBlob(text).sentiment.polarity for text in user_texts]) / len(user_texts) if user_texts else 0
           agent_sentiment = sum([TextBlob(text).sentiment.polarity for text in agent_texts]) / len(agent_texts) if agent_texts else 0
           
           return {
               'overall': overall_sentiment,
               'progression': sentiments,
               'user_sentiment': user_sentiment,
               'agent_sentiment': agent_sentiment
           }
           
       @staticmethod
       def extract_topics(transcript, top_n=10):
           """
           Extract the most common topics/keywords from conversation
           
           Args:
               transcript (list): List of conversation turns
               top_n (int): Number of top topics to return
               
           Returns:
               list: Top topics with counts
           """
           if not transcript:
               return []
               
           # Combine all text
           all_text = " ".join([turn.get('text', '') for turn in transcript])
           
           # Remove common stop words and punctuation
           stop_words = {"i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", 
                        "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", 
                        "her", "hers", "herself", "it", "its", "itself", "they", "them", "their", 
                        "theirs", "themselves", "what", "which", "who", "whom", "this", "that", 
                        "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", 
                        "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", 
                        "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", 
                        "at", "by", "for", "with", "about", "against", "between", "into", "through", 
                        "during", "before", "after", "above", "below", "to", "from", "up", "down", 
                        "in", "out", "on", "off", "over", "under", "again", "further", "then", 
                        "once", "here", "there", "when", "where", "why", "how", "all", "any", 
                        "both", "each", "few", "more", "most", "other", "some", "such", "no", 
                        "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", 
                        "t", "can", "will", "just", "don't", "should", "now"}
                        
           words = re.findall(r'\b[a-zA-Z]{3,}\b', all_text.lower())
           words = [word for word in words if word not in stop_words]
           
           # Count word frequencies
           word_counts = Counter(words)
           
           # Return top N topics
           return word_counts.most_common(top_n)
           
       @staticmethod
       def analyze_conversation_metrics(conversations_df):
           """
           Calculate metrics across multiple conversations
           
           Args:
               conversations_df (DataFrame): DataFrame of conversations
               
           Returns:
               dict: Various conversation metrics
           """
           if conversations_df.empty:
               return {}
               
           # Basic statistics
           metrics = {
               'total_conversations': len(conversations_df),
               'avg_duration': conversations_df['duration'].mean() if 'duration' in conversations_df else None,
               'max_duration': conversations_df['duration'].max() if 'duration' in conversations_df else None,
               'min_duration': conversations_df['duration'].min() if 'duration' in conversations_df else None,
               'avg_turns': conversations_df['turn_count'].mean() if 'turn_count' in conversations_df else None,
           }
           
           # Add time-based analytics if timestamps are available
           if 'start_time' in conversations_df:
               conversations_df['hour'] = conversations_df['start_time'].dt.hour
               conversations_df['day_of_week'] = conversations_df['start_time'].dt.dayofweek
               
               # Count by hour
               hour_counts = conversations_df.groupby('hour').size()
               metrics['hourly_distribution'] = hour_counts.to_dict()
               
               # Count by day of week
               day_counts = conversations_df.groupby('day_of_week').size()
               metrics['day_of_week_distribution'] = day_counts.to_dict()
               
           return metrics
   ```

### 6. Web Routes and Templates

1. Create app/routes.py:
   ```python
   from flask import Blueprint, render_template, request, jsonify, send_file, current_app, url_for, redirect, flash
   from datetime import datetime, timedelta
   import io
   import json
   from app.api.elevenlabs_client import ElevenLabsClient
   from app.api.data_processor import DataProcessor
   from app.utils.export import DataExporter
   from app.utils.analysis import ConversationAnalyzer

   main_bp = Blueprint('main', __name__)

   @main_bp.route('/')
   def index():
       """Home page with dashboard overview"""
       return render_template('index.html')

   @main_bp.route('/data-selection')
   def data_selection():
       """Page for selecting conversation data"""
       # Default date range (last 7 days)
       end_date = datetime.now().strftime('%Y-%m-%d')
       start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
       
       return render_template('data_selection.html', 
                             start_date=start_date,
                             end_date=end_date)

   @main_bp.route('/api/conversations')
   def get_conversations():
       """API endpoint to get conversation data"""
       start_date = request.args.get('start_date')
       end_date = request.args.get('end_date')
       limit = int(request.args.get('limit', 100))
       offset = int(request.args.get('offset', 0))
       
       try:
           client = ElevenLabsClient()
           conversations_data = client.get_conversations(
               start_date=start_date,
               end_date=end_date,
               limit=limit,
               offset=offset
           )
           
           # Process the data
           df = DataProcessor.process_conversations(conversations_data)
           
           # Return as JSON
           return jsonify({
               'total': conversations_data.get('total', 0),
               'data': json.loads(df.to_json(orient='records', date_format='iso'))
           })
           
       except Exception as e:
           return jsonify({'error': str(e)}), 500

   @main_bp.route('/api/conversations/<conversation_id>')
   def get_conversation_details(conversation_id):
       """API endpoint to get details for a specific conversation"""
       try:
           client = ElevenLabsClient()
           conversation_data = client.get_conversation_details(conversation_id)
           
           # Process the data
           processed_data = DataProcessor.process_conversation_details(conversation_data)
           
           return jsonify(processed_data)
           
       except Exception as e:
           return jsonify({'error': str(e)}), 500

   @main_bp.route('/api/conversations/<conversation_id>/analysis')
   def analyze_conversation(conversation_id):
       """API endpoint to get analysis for a specific conversation"""
       try:
           client = ElevenLabsClient()
           conversation_data = client.get_conversation_details(conversation_id)
           
           # Process the data
           processed_data = DataProcessor.process_conversation_details(conversation_data)
           
           # Analyze sentiment
           sentiment = ConversationAnalyzer.analyze_sentiment(processed_data.get('transcript', []))
           
           # Extract topics
           topics = ConversationAnalyzer.extract_topics(processed_data.get('transcript', []))
           
           return jsonify({
               'sentiment': sentiment,
               'topics': topics
           })
           
       except Exception as e:
           return jsonify({'error': str(e)}), 500

   @main_bp.route('/api/export/<format>')
   def export_data(format):
       """API endpoint to export data in different formats"""
       data_type = request.args.get('type', 'conversations')
       conversation_id = request.args.get('conversation_id')
       start_date = request.args.get('start_date')
       end_date = request.args.get('end_date')
       
       try:
           client = ElevenLabsClient()
           
           if data_type == 'conversation' and conversation_id:
               # Export a single conversation
               conversation_data = client.get_conversation_details(conversation_id)
               processed_data = DataProcessor.process_conversation_details(conversation_data)
               data = processed_data
               filename = f"conversation_{conversation_id}"
           else:
               # Export multiple conversations
               conversations_data = client.get_conversations(
                   start_date=start_date,
                   end_date=end_date,
                   limit=1000  # Increased limit for exports
               )
               df = DataProcessor.process_conversations(conversations_data)
               data = df
               filename = f"conversations_{start_date}_to_{end_date}"
               
           # Export in the requested format
           if format == 'json':
               output = DataExporter.to_json(data)
               mimetype = 'application/json'
               filename = f"{filename}.json"
           elif format == 'csv':
               output = DataExporter.to_csv(data)
               mimetype = 'text/csv'
               filename = f"{filename}.csv"
           elif format == 'md':
               output = DataExporter.to_markdown(data)
               mimetype = 'text/markdown'
               filename = f"{filename}.md"
           else:
               return jsonify({'error': 'Unsupported format'}), 400
               
           # Create in-memory file
           buffer = io.BytesIO(output.encode('utf-8'))
           buffer.seek(0)
           
           return send_file(
               buffer,
               mimetype=mimetype,
               as_attachment=True,
               download_name=filename
           )
           
       except Exception as e:
           return jsonify({'error': str(e)}), 500

   @main_bp.route('/analysis')
   def analysis_page():
       """Page for analyzing conversation data"""
       return render_template('analysis.html')

   @main_bp.route('/visualization')
   def visualization_page():
       """Page for visualizing conversation data"""
       return render_template('visualization.html')
   ```

2. Create app/templates/base.html:
   ```html
   <!DOCTYPE html>
   <html lang="en">
   <head>
       <meta charset="UTF-8">
       <meta name="viewport" content="width=device-width, initial-scale=1.0">
       <title>{% block title %}Psychic Source Transcript Analysis Tool{% endblock %}</title>
       
       <!-- Bootstrap 5 CSS -->
       <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
       
       <!-- DataTables CSS -->
       <link href="https://cdn.datatables.net/1.11.5/css/dataTables.bootstrap5.min.css" rel="stylesheet">
       
       <!-- Font Awesome -->
       <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
       
       <!-- Custom CSS -->
       <link href="{{ url_for('static', filename='css/style.css') }}" rel="stylesheet">
       
       {% block head_extra %}{% endblock %}
   </head>
   <body>
       <!-- Navigation Bar -->
       <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
           <div class="container-fluid">
               <a class="navbar-brand" href="{{ url_for('main.index') }}">
                   <i class="fas fa-brain me-2"></i>Psychic Source Analyzer
               </a>
               <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                   <span class="navbar-toggler-icon"></span>
               </button>
               <div class="collapse navbar-collapse" id="navbarNav">
                   <ul class="navbar-nav">
                       <li class="nav-item">
                           <a class="nav-link {% if request.endpoint == 'main.index' %}active{% endif %}" 
                              href="{{ url_for('main.index') }}">Dashboard</a>
                       </li>
                       <li class="nav-item">
                           <a class="nav-link {% if request.endpoint == 'main.data_selection' %}active{% endif %}" 
                              href="{{ url_for('main.data_selection') }}">Data Selection</a>
                       </li>
                       <li class="nav-item">
                           <a class="nav-link {% if request.endpoint == 'main.analysis_page' %}active{% endif %}" 
                              href="{{ url_for('main.analysis_page') }}">Analysis</a>
                       </li>
                       <li class="nav-item">
                           <a class="nav-link {% if request.endpoint == 'main.visualization_page' %}active{% endif %}" 
                              href="{{ url_for('main.visualization_page') }}">Visualization</a>
                       </li>
                   </ul>
               </div>
           </div>
       </nav>
       
       <!-- Flash Messages -->
       <div class="container mt-3">
           {% for category, message in get_flashed_messages(with_categories=true) %}
               <div class="alert alert-{{ category }} alert-dismissible fade show">
                   {{ message }}
                   <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
               </div>
           {% endfor %}
       </div>
       
       <!-- Main Content -->
       <main class="container mt-4">
           {% block content %}{% endblock %}
       </main>
       
       <!-- Footer -->
       <footer class="footer mt-5 py-3 bg-light">
           <div class="container text-center">
               <span class="text-muted">Psychic Source Transcript Analysis Tool &copy; {{ now.year }}</span>
           </div>
       </footer>
       
       <!-- Bootstrap 5 JS Bundle -->
       <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
       
       <!-- jQuery -->
       <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
       
       <!-- DataTables JS -->
       <script src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.min.js"></script>
       <script src="https://cdn.datatables.net/1.11.5/js/dataTables.bootstrap5.min.js"></script>
       
       <!-- Chart.js -->
       <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
       
       <!-- Custom JS -->
       <script src="{{ url_for('static', filename='js/main.js') }}"></script>
       
       {% block scripts %}{% endblock %}
   </body>
   </html>
   ```

3. Create app/templates/index.html:
   ```html
   {% extends "base.html" %}

   {% block title %}Dashboard - Psychic Source Analyzer{% endblock %}

   {% block content %}
   <div class="row">
       <div class="col-12">
           <div class="card shadow-sm">
               <div class="card-body">
                   <h1 class="card-title">Welcome to Psychic Source Transcript Analysis Tool</h1>
                   <p class="card-text">
                       This tool helps you extract, analyze, and visualize conversation data from the ElevenLabs 
                       Conversational Voice Agent "Lily". Use the navigation menu to explore different features.
                   </p>
               </div>
           </div>
       </div>
   </div>

   <div class="row mt-4">
       <div class="col-md-6">
           <div class="card shadow-sm">
               <div class="card-header bg-primary text-white">
                   <h5 class="card-title mb-0">
                       <i class="fas fa-chart-line me-2"></i>Recent Activity
                   </h5>
               </div>
               <div class="card-body">
                   <div id="recent-activity-chart" style="height: 250px;">
                       <canvas id="conversationsChart"></canvas>
                   </div>
               </div>
           </div>
       </div>
       
       <div class="col-md-6">
           <div class="card shadow-sm">
               <div class="card-header bg-primary text-white">
                   <h5 class="card-title mb-0">
                       <i class="fas fa-tasks me-2"></i>Quick Actions
                   </h5>
               </div>
               <div class="card-body">
                   <div class="list-group">
                       <a href="{{ url_for('main.data_selection') }}" class="list-group-item list-group-item-action">
                           <i class="fas fa-database me-2"></i>Browse Conversation Data
                       </a>
                       <a href="{{ url_for('main.analysis_page') }}" class="list-group-item list-group-item-action">
                           <i class="fas fa-search me-2"></i>Analyze Conversations
                       </a>
                       <a href="{{ url_for('main.visualization_page') }}" class="list-group-item list-group-item-action">
                           <i class="fas fa-chart-pie me-2"></i>Visualize Insights
                       </a>
                       <a href="#" class="list-group-item list-group-item-action" id="quick-export">
                           <i class="fas fa-file-export me-2"></i>Export Recent Data
                       </a>
                   </div>
               </div>
           </div>
       </div>
   </div>

   <div class="row mt-4">
       <div class="col-12">
           <div class="card shadow-sm">
               <div class="card-header bg-primary text-white">
                   <h5 class="card-title mb-0">
                       <i class="fas fa-info-circle me-2"></i>Getting Started
                   </h5>
               </div>
               <div class="card-body">
                   <div class="row">
                       <div class="col-md-4">
                           <div class="card mb-3">
                               <div class="card-body text-center">
                                   <i class="fas fa-search fa-3x mb-3 text-primary"></i>
                                   <h5>Select Data</h5>
                                   <p class="card-text">Choose date ranges and filter conversation data.</p>
                               </div>
                           </div>
                       </div>
                       <div class="col-md-4">
                           <div class="card mb-3">
                               <div class="card-body text-center">
                                   <i class="fas fa-chart-bar fa-3x mb-3 text-primary"></i>
                                   <h5>Analyze</h5>
                                   <p class="card-text">Perform sentiment analysis and extract key topics.</p>
                               </div>
                           </div>
                       </div>
                       <div class="col-md-4">
                           <div class="card mb-3">
                               <div class="card-body text-center">
                                   <i class="fas fa-file-download fa-3x mb-3 text-primary"></i>
                                   <h5>Export</h5>
                                   <p class="card-text">Download your data in JSON, CSV, or Markdown format.</p>
                               </div>
                           </div>
                       </div>
                   </div>
               </div>
           </div>
       </div>
   </div>
   {% endblock %}

   {% block scripts %}
   <script>
       document.addEventListener('DOMContentLoaded', function() {
           // Initialize dashboard charts
           initDashboardCharts();
           
           // Handle quick export
           document.getElementById('quick-export').addEventListener('click', function(e) {
               e.preventDefault();
               // Get dates for last 7 days
               const endDate = new Date().toISOString().split('T')[0];
               const startDate = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
               
               // Redirect to export endpoint
               window.location.href = `/api/export/json?type=conversations&start_date=${startDate}&end_date=${endDate}`;
           });
       });
       
       function initDashboardCharts() {
           // Sample data for demo purposes
           const ctx = document.getElementById('conversationsChart').getContext('2d');
           const chart = new Chart(ctx, {
               type: 'line',
               data: {
                   labels: ['7 days ago', '6 days ago', '5 days ago', '4 days ago', '3 days ago', '2 days ago', 'Yesterday'],
                   datasets: [{
                       label: 'Conversations',
                       data: [5, 8, 12, 7, 10, 15, 9],
                       backgroundColor: 'rgba(54, 162, 235, 0.2)',
                       borderColor: 'rgba(54, 162, 235, 1)',
                       borderWidth: 2,
                       tension: 0.3
                   }]
               },
               options: {
                   responsive: true,
                   maintainAspectRatio: false,
                   scales: {
                       y: {
                           beginAtZero: true,
                           ticks: {
                               precision: 0
                           }
                       }
                   }
               }
           });
       }
   </script>
   {% endblock %}
   ```

4. Create app/templates/data_selection.html:
   ```html
   {% extends "base.html" %}

   {% block title %}Data Selection - Psychic Source Analyzer{% endblock %}

   {% block content %}
   <div class="row">
       <div class="col-12">
           <div class="card shadow-sm">
               <div class="card-header bg-primary text-white">
                   <h5 class="card-title mb-0">
                       <i class="fas fa-database me-2"></i>Conversation Data Selection
                   </h5>
               </div>
               <div class="card-body">
                   <form id="data-filter-form" class="mb-4">
                       <div class="row g-3">
                           <div class="col-md-4">
                               <label for="start-date" class="form-label">Start Date</label>
                               <input type="date" class="form-control" id="start-date" name="start_date" value="{{ start_date }}">
                           </div>
                           <div class="col-md-4">
                               <label for="end-date" class="form-label">End Date</label>
                               <input type="date" class="form-control" id="end-date" name="end_date" value="{{ end_date }}">
                           </div>
                           <div class="col-md-4 d-flex align-items-end">
                               <button type="submit" class="btn btn-primary w-100">
                                   <i class="fas fa-search me-2"></i>Search
                               </button>
                           </div>
                       </div>
                   </form>
                   
                   <div class="table-responsive">
                       <table id="conversations-table" class="table table-striped table-hover">
                           <thead>
                               <tr>
                                   <th>ID</th>
                                   <th>Start Time</th>
                                   <th>End Time</th>
                                   <th>Duration (s)</th>
                                   <th>Turns</th>
                                   <th>Status</th>
                                   <th>Actions</th>
                               </tr>
                           </thead>
                           <tbody>
                               <!-- Data will be loaded via JavaScript -->
                           </tbody>
                       </table>
                   </div>
               </div>
           </div>
       </div>
   </div>

   <!-- Conversation Details Modal -->
   <div class="modal fade" id="conversationModal" tabindex="-1" aria-hidden="true">
       <div class="modal-dialog modal-xl">
           <div class="modal-content">
               <div class="modal-header bg-primary text-white">
                   <h5 class="modal-title">Conversation Details</h5>
                   <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
               </div>
               <div class="modal-body">
                   <div id="conversation-details-content">
                       <!-- Conversation details will be loaded here -->
                   </div>
               </div>
               <div class="modal-footer">
                   <div class="btn-group dropdown">
                       <button type="button" class="btn btn-primary dropdown-toggle" data-bs-toggle="dropdown">
                           <i class="fas fa-file-export me-2"></i>Export
                       </button>
                       <ul class="dropdown-menu">
                           <li><a class="dropdown-item export-conversation" data-format="json" href="#">JSON</a></li>
                           <li><a class="dropdown-item export-conversation" data-format="csv" href="#">CSV</a></li>
                           <li><a class="dropdown-item export-conversation" data-format="md" href="#">Markdown</a></li>
                       </ul>
                   </div>
                   <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
               </div>
           </div>
       </div>
   </div>

   <!-- Export Modal -->
   <div class="modal fade" id="exportModal" tabindex="-1" aria-hidden="true">
       <div class="modal-dialog">
           <div class="modal-content">
               <div class="modal-header bg-primary text-white">
                   <h5 class="modal-title">Export Data</h5>
                   <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
               </div>
               <div class="modal-body">
                   <form id="export-form">
                       <div class="mb-3">
                           <label class="form-label">Export Format</label>
                           <div class="form-check">
                               <input class="form-check-input" type="radio" name="export-format" id="format-json" value="json" checked>
                               <label class="form-check-label" for="format-json">JSON</label>
                           </div>
                           <div class="form-check">
                               <input class="form-check-input" type="radio" name="export-format" id="format-csv" value="csv">
                               <label class="form-check-label" for="format-csv">CSV</label>
                           </div>
                           <div class="form-check">
                               <input class="form-check-input" type="radio" name="export-format" id="format-md" value="md">
                               <label class="form-check-label" for="format-md">Markdown</label>
                           </div>
                       </div>
                   </form>
               </div>
               <div class="modal-footer">
                   <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                   <button type="button" class="btn btn-primary" id="export-button">Export</button>
               </div>
           </div>
       </div>
   </div>
   {% endblock %}

   {% block scripts %}
   <script>
       let currentConversationId = null;
       let dataTable = null;
       
       document.addEventListener('DOMContentLoaded', function() {
           // Initialize DataTable
           dataTable = $('#conversations-table').DataTable({
               columns: [
                   { data: 'conversation_id' },
                   { data: 'start_time' },
                   { data: 'end_time' },
                   { data: 'duration' },
                   { data: 'turn_count' },
                   { data: 'status' },
                   {
                       data: null,
                       orderable: false,
                       render: function(data) {
                           return `
                               <div class="btn-group btn-group-sm" role="group">
                                   <button type="button" class="btn btn-primary view-conversation" data-id="${data.conversation_id}">
                                       <i class="fas fa-eye"></i>
                                   </button>
                                   <button type="button" class="btn btn-info analyze-conversation" data-id="${data.conversation_id}">
                                       <i class="fas fa-chart-bar"></i>
                                   </button>
                               </div>`;
                       }
                   }
               ],
               order: [[1, 'desc']]
           });
           
           // Load initial data
           loadConversations();
           
           // Set up event listeners
           document.getElementById('data-filter-form').addEventListener('submit', function(e) {
               e.preventDefault();
               loadConversations();
           });
           
           // Handle conversation view button
           $('#conversations-table').on('click', '.view-conversation', function() {
               const conversationId = $(this).data('id');
               viewConversation(conversationId);
           });
           
           // Handle conversation analyze button
           $('#conversations-