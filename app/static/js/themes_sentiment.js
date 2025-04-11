console.log("THEMES_SENTIMENT.JS LOADED - V1");

document.addEventListener('DOMContentLoaded', function() {
    // Ensure utilities are loaded (from utils.js)
    if (typeof API === 'undefined' || typeof UI === 'undefined' || typeof Formatter === 'undefined') {
        console.error("Required utilities (API, UI, Formatter) not found. Aborting Themes & Sentiment init.");
        return;
    }

    console.log('Themes page loaded - initializing...');
    
    // Initialize date range controls
    initializeDateControls();
    
    // Initial data load
    // Assuming the default active button (e.g., 30 days) will trigger the first fetch via its click handler simulation
    // If not, uncomment the line below:
    // fetchThemesSentimentData(); 
    
    // Setup debug panel listeners if elements exist
    const refreshBtn = document.getElementById('refresh-btn');
    const debugBtn = document.getElementById('debug-btn');
    const reloadBtn = document.getElementById('reload-page'); // Check if this ID is consistently added

    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            refreshThemesData(); // Changed name for clarity
        });
    } else {
         console.warn("Debug refresh button #refresh-btn not found.");
    }

    if (debugBtn) {
         debugBtn.addEventListener('click', function() {
             // Check if panel is becoming visible to fetch status
             // This logic might need refinement based on how Bootstrap collapse events work
             setTimeout(fetchApiStatus, 100); // Simple delay, might need mutation observer
         });
    } else {
         console.warn("Debug panel toggle button #debug-btn not found.");
    }

    // Note: The reload button listener seems to be added dynamically *after* refresh
    // We might need a more robust way to handle that if it causes issues.

});

function initializeDateControls() {
    console.log("Initializing date controls...");
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    const applyBtn = document.getElementById('apply-date-filter');
    const timeframeBtns = document.querySelectorAll('.btn-group[aria-label="Date range selection"] button');
    
    if (!startDateInput || !endDateInput || !applyBtn || timeframeBtns.length === 0) {
        console.error("Date control elements not found. Cannot initialize.");
        return;
    }

    // Set default dates (last 30 days)
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    // Format dates as YYYY-MM-DD for input fields
    const formatDateForInput = (date) => {
        const year = date.getFullYear();
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const day = date.getDate().toString().padStart(2, '0');
        return `${year}-${month}-${day}`;
    };

    startDateInput.value = formatDateForInput(thirtyDaysAgo);
    endDateInput.value = formatDateForInput(today);
    
    // Add listeners to timeframe buttons
    timeframeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            timeframeBtns.forEach(b => {
                b.classList.remove('btn-secondary');
                b.classList.add('btn-outline-secondary');
            });
            this.classList.remove('btn-outline-secondary');
            this.classList.add('btn-secondary');
            
            const days = this.getAttribute('data-days');
            if (days) { // Only preset buttons have data-days
                 const today = new Date();
                 let startDate = new Date();
                 startDate.setDate(today.getDate() - parseInt(days));
                 startDateInput.value = formatDateForInput(startDate);
                 endDateInput.value = formatDateForInput(today);
                 fetchThemesSentimentData(); // Apply automatically
            } // Else: Custom range, wait for Apply button
        });
    });
    
    // Add listener for Apply button (for custom range or explicit apply)
    applyBtn.addEventListener('click', fetchThemesSentimentData);
    
    // Simulate click on default (e.g., 30 days) to set initial state and load data
    const defaultButton = document.querySelector('.btn-group[aria-label="Date range selection"] button[data-days="30"]');
    if (defaultButton) {
        console.log("Simulating click on 30-day button for initial load...");
        defaultButton.click();
    } else {
         console.warn("Default 30-day button not found, triggering manual fetch...");
         fetchThemesSentimentData(); // Fallback fetch
    }
}

async function fetchThemesSentimentData() {
    console.log("Fetching themes and sentiment data...");
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    
    if (!startDate || !endDate) {
        UI.showToast("Please select a valid start and end date.", "warning");
        return;
    }

    // Show loading states
    const sentimentContainer = document.getElementById('sentiment-overview');
    const themesContainer = document.getElementById('top-themes');
    if (sentimentContainer) sentimentContainer.innerHTML = '<div class="text-center p-3"><div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div> Loading Sentiment...</div>';
    if (themesContainer) themesContainer.innerHTML = '<div class="text-center p-3"><div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div> Loading Themes...</div>';
    hideWarningBanner(); // Hide previous warnings
    
    const apiUrl = `/api/themes-sentiment/full-analysis?start_date=${startDate}&end_date=${endDate}`;
    console.log(`Fetching themes and sentiment data from: ${apiUrl}`);
    
    try {
        const data = await API.fetch(apiUrl);
        console.log("Themes API Response:", data);
        
        // Update conversation count
        const countDisplay = document.getElementById('conversation-count-display');
        if (countDisplay) {
            countDisplay.textContent = `Conversations: ${data.total_conversations_in_range || 0}`;
        }
        
        if (data.error) {
            showWarningBanner(`Error: ${data.error}`);
            displayErrorMessage(sentimentContainer, data.error);
            displayErrorMessage(themesContainer, data.error);
        } else if (data.is_fallback_data) {
            showWarningBanner("Notice: Displaying sample data. Analysis may be incomplete.");
            // Display fallback data normally
            displaySentimentOverview(data.sentiment_overview);
            displayTopThemes(data.top_themes);
        } else {
            // Display actual data
            displaySentimentOverview(data.sentiment_overview);
            displayTopThemes(data.top_themes);
        }
    } catch (error) {
        console.error('Error fetching themes data:', error);
        showWarningBanner(`Error loading data: ${error.message}`);
        displayErrorMessage(sentimentContainer, error.message);
        displayErrorMessage(themesContainer, error.message);
        // UI.showToast is handled by API.fetch
    }
}

function displayErrorMessage(container, message) {
     if (container) {
         container.innerHTML = `<div class="alert alert-danger m-0">Error: ${message}</div>`;
     }
}

function displaySentimentOverview(data) {
    const overviewElement = document.getElementById('sentiment-overview');
    if (!overviewElement) {
        console.error("Element with ID 'sentiment-overview' not found.");
        return;
    }
    
    if (!data) {
        overviewElement.innerHTML = '<div class="alert alert-warning">No sentiment overview data available.</div>';
        return;
    }

    // Use NEW keys from backend
    const callerSentiment = data.avg_caller_sentiment;
    const agentSentiment = data.avg_agent_sentiment;

    // Helper to safely format sentiment number or return '--'
    const formatSentiment = (value) => {
        return (typeof value === 'number' && !isNaN(value)) ? value.toFixed(2) : '--';
    };
    
    // Helper to safely get color or default
    const getSentimentColor = (value) => {
        return (typeof value === 'number' && !isNaN(value)) ? Sentiment.toColor(value) : '#6c757d'; // Default gray
    };

    overviewElement.innerHTML = `
        <div class="col-md-6 mb-4">
            <div class="card h-100 shadow-sm">
                <div class="card-body text-center">
                    <h5 class="card-title text-muted">Avg. Caller Sentiment</h5>
                    <p class="card-text fs-4 fw-bold" style="color: ${getSentimentColor(callerSentiment)}">
                        ${formatSentiment(callerSentiment)}
                    </p>
                </div>
            </div>
        </div>
        <div class="col-md-6 mb-4">
            <div class="card h-100 shadow-sm">
                <div class="card-body text-center">
                    <h5 class="card-title text-muted">Avg. Agent Sentiment</h5>
                    <p class="card-text fs-4 fw-bold" style="color: ${getSentimentColor(agentSentiment)}">
                        ${formatSentiment(agentSentiment)}
                    </p>
                </div>
            </div>
        </div>
    `;
}

function displayTopThemes(themes) {
    const container = document.getElementById('top-themes');
     if (!container) return;

    if (!themes || !Array.isArray(themes) || themes.length === 0) {
        container.innerHTML = '<div class="alert alert-info m-0">No theme data available or data is in unexpected format.</div>';
        if (themes && !Array.isArray(themes)) {
            console.warn("Received non-array data for top themes:", themes);
        }
        return;
    }
    
    // Sort themes by count, descending
    themes.sort((a, b) => b.count - a.count);
    
    const topThemes = themes.slice(0, 10); // Limit display
    
    let html = '<ul class="list-group list-group-flush">'; // Use flush for better card integration
    topThemes.forEach(theme => {
        // Determine badge color based on sentiment score
        const sentimentColor = Sentiment.toColor(theme.sentiment); 
        // Use text-dark for light backgrounds for contrast
        const textColorClass = (theme.sentiment > -0.1 && theme.sentiment < 0.5) ? 'text-dark' : ''; 
        
        html += `
            <li class="list-group-item d-flex justify-content-between align-items-center px-0">
                <span class="theme-name">${theme.theme || 'Unknown Theme'}</span>
                <div>
                     <span class="badge rounded-pill me-2" style="background-color: ${sentimentColor}; color: ${textColorClass ? '#212529' : '#fff'}" title="Avg. Sentiment: ${theme.sentiment?.toFixed(2) || 'N/A'}">
                         ${theme.sentiment?.toFixed(1) || '--'}
                     </span>
                     <span class="badge bg-primary rounded-pill" title="Count">${theme.count}</span>
                </div>
            </li>
        `;
    });
    html += '</ul>';
    
    container.innerHTML = html;
}

// --- Warning Banner --- 
function showWarningBanner(message) {
    const banner = document.getElementById('warning-banner');
    const messageEl = document.getElementById('warning-message');
    if (banner && messageEl) {
        messageEl.textContent = message;
        banner.style.display = 'block';
    } else {
         console.warn("Warning banner elements not found.");
    }
}

function hideWarningBanner() {
    const banner = document.getElementById('warning-banner');
    if (banner) banner.style.display = 'none';
}

// --- Debug Panel Functions --- 
async function fetchApiStatus() {
    console.log("Fetching API status for debug panel...");
    const statusDiv = document.getElementById('api-status');
    if (!statusDiv) return;

    statusDiv.innerHTML = 'Loading status...';
    try {
        // Use global API utility
        const data = await API.fetch('/api/status'); // Corrected endpoint from previous sessions
        console.log("Debug API Status data:", data);

        let statusHTML = '<ul class="list-unstyled small">';
        for (const key in data) {
            if (typeof data[key] === 'object' && data[key] !== null) {
                statusHTML += `<li><strong>${key.charAt(0).toUpperCase() + key.slice(1)}:</strong> 
                               <span class="badge bg-${data[key].status === 'connected' || data[key].status === 'available' ? 'success' : 'danger'}">
                                   ${data[key].status || 'unknown'}
                               </span> - ${data[key].message || ''}</li>`;
            } else {
                 statusHTML += `<li><strong>${key}:</strong> ${data[key]}</li>`;
            }
        }
        statusHTML += '</ul>';
        statusDiv.innerHTML = statusHTML;
    } catch (error) {
        console.error("Error fetching API status for debug:", error);
        statusDiv.innerHTML = `<div class="alert alert-danger p-2 m-0">Error checking API status: ${error.message}</div>`;
    }
}
    
async function refreshThemesData() {
    console.log("Attempting to refresh themes data...");
    // Note: The endpoint /api/themes-sentiment/refresh might not exist or work as intended.
    // This function might need complete removal or replacement based on actual backend capabilities.
    
    const forceRefresh = document.getElementById('force-refresh')?.checked || false;
    const refreshBtn = document.getElementById('refresh-btn');
    const resultDiv = document.getElementById('refresh-result');
    
    if (!resultDiv || !refreshBtn) {
         console.error("Refresh elements not found.");
         return;
    }

    refreshBtn.disabled = true;
    resultDiv.innerHTML = '<div class="alert alert-info p-2 m-0">Sending refresh request...</div>';
    
    try {
        // This endpoint seems hypothetical or might need correction
        const data = await API.fetch('/api/themes-sentiment/refresh', { // Verify this endpoint exists
            method: 'POST',
            body: JSON.stringify({ force_cache_refresh: forceRefresh }), // Adjust payload as needed
        });
        console.log("Refresh Response:", data);

        resultDiv.innerHTML = `
            <div class="alert alert-success p-2 m-0">
                <strong>Status:</strong> ${data.status || 'Unknown'}<br>
                <strong>Message:</strong> ${data.message || 'No message received.'}
            </div>
        `;
        // Optionally trigger a reload or data refetch on success
        if (data.status === 'success') {
             UI.showToast("Data refresh triggered successfully. Reloading analysis...", "success");
             setTimeout(fetchThemesSentimentData, 500); // Refetch analysis data after short delay
        } else {
             UI.showToast(data.message || "Refresh request sent, but status unknown.", "warning");
        }

    } catch (error) {
        console.error("Error during data refresh request:", error);
        resultDiv.innerHTML = `<div class="alert alert-danger p-2 m-0">Error refreshing data: ${error.message}</div>`;
        // UI.showToast handled by API.fetch
    } finally {
        refreshBtn.disabled = false;
    }
} 