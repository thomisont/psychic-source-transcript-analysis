// app/static/js/themes_sentiment_refactored.js

// Ensure utils.js objects are available (assuming API, UI, Formatter are defined there)
if (typeof API === 'undefined' || typeof UI === 'undefined' || typeof Formatter === 'undefined') {
    console.error("Error: Required objects (API, UI, Formatter) from utils.js are not available.");
    // Optionally, display an error to the user or halt execution
}

// Define Theme Colors & Palette (Read from CSS)
const themeColors = {
    primary: getComputedStyle(document.documentElement).getPropertyValue('--primary-color').trim() || '#3A0CA3',
    secondary: getComputedStyle(document.documentElement).getPropertyValue('--secondary-color').trim() || '#48BFE3', // Use Teal as Secondary for UI
    accent: getComputedStyle(document.documentElement).getPropertyValue('--accent-color', '#F72585').trim(), // Define an accent (Magenta/Pink)
    darkGray: getComputedStyle(document.documentElement).getPropertyValue('--dark-gray').trim() || '#343a40',
    textMuted: getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim() || '#6c757d',
    borderGray: getComputedStyle(document.documentElement).getPropertyValue('--border-gray').trim() || '#E9ECEF',
    white: '#ffffff',
    success: getComputedStyle(document.documentElement).getPropertyValue('--success-color').trim() || '#28a745',
    warning: getComputedStyle(document.documentElement).getPropertyValue('--warning-color').trim() || '#ffc107',
    danger: getComputedStyle(document.documentElement).getPropertyValue('--danger-color').trim() || '#dc3545'
};

// Define Data Visualization Palette using CSS variables
const vizPalette = [
    themeColors.primary,       // Deep Indigo
    themeColors.secondary,     // Muted Teal
    '#7209B7',                // Purple (keep from previous palette)
    themeColors.accent,        // Magenta/Pink Accent
    '#4CC9F0',                // Light Blue (keep from previous)
    themeColors.warning,       // Yellow/Orange for Neutral Sentiment
    themeColors.success,       // Green for Positive Sentiment
    themeColors.danger         // Red for Negative Sentiment
    // Add more if needed, ensure distinct
];

// Define Base Font Options
const baseFont = { family: 'Lato, sans-serif', size: 12, weight: 'normal' }; // Add fallback
const titleFont = { family: 'Montserrat, sans-serif', size: 13, weight: 'bold' }; // Add fallback

// Define Common Chart Options with updated fonts and colors
const commonChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
        y: {
            beginAtZero: true,
            ticks: { 
                color: themeColors.textMuted, 
                font: baseFont
            },
            grid: { 
                color: themeColors.borderGray, // Use border gray for grid
                drawBorder: false // Hide the axis border itself
            },
            title: { // Add placeholder for Y-axis title
                display: false, // Set to true in specific charts
                text: '',
                color: themeColors.darkGray,
                font: { ...titleFont, size: 12 } // Slightly smaller title
            }
        },
        x: {
           ticks: { 
               color: themeColors.textMuted, 
               font: baseFont 
           },
           grid: { 
               color: themeColors.borderGray, // Use border gray for grid
               drawBorder: false // Hide the axis border itself
            },
           title: { // Add placeholder for X-axis title
                display: false,
                text: '',
                color: themeColors.darkGray,
                font: { ...titleFont, size: 12 }
            }
        }
    },
    plugins: {
        legend: {
            display: true, 
            position: 'bottom',
            labels: {
               font: baseFont,
               color: themeColors.darkGray,
               boxWidth: 12,
               padding: 15
            }
        },
        tooltip: {
            enabled: true,
            backgroundColor: themeColors.darkGray,
            titleFont: titleFont,
            titleColor: themeColors.white,
            bodyFont: baseFont,
            bodyColor: themeColors.white,
            padding: 10,
            cornerRadius: 4,
            boxPadding: 4,
            // Add custom label callback for formatting
            callbacks: {
                label: function(context) {
                    let label = context.dataset.label || '';
                    if (label) {
                        label += ': ';
                    }
                    if (context.parsed.y !== null) {
                        // Basic number formatting, customize as needed
                        label += context.parsed.y;
                    }
                    return label;
                }
            }
        }
    },
    // Add interaction settings for hover effects
    interaction: {
        mode: 'index', // Show tooltips for all datasets at that index
        intersect: false, // Tooltip appears even if not directly hovering over point
    },
    hover: {
        mode: 'nearest',
        intersect: true
    }
};

let topThemesChart = null;
let sentimentTrendsChart = null;

// --- Global variable for the modal instance ---
let categoryModal = null;

// --- Element References (Declare at Module Scope) ---
let loadingIndicator = null;
let errorDisplay = null;
let analysisContent = null;
let conversationCountDisplay = null;
let analysisModelInfo = null;
let loadingMessageMain = null;
let loadingMessageDetail = null;
let categoryModalElement = null;
let categoryModalTitle = null;
let categoryModalBody = null;
// NEW: RAG Query Elements
let ragQueryInput = null;
let ragSubmitBtn = null;
let ragResponseArea = null;
let ragResponseContent = null;
let ragErrorDisplay = null;
let ragSubmitSpinner = null;

// NEW: Transcript Modal elements
let transcriptModal = null; // Instance of the modal
let transcriptModalElement = null;
let transcriptModalLabel = null;
let transcriptModalBody = null;
let transcriptLoading = null;
let transcriptError = null;
let transcriptContent = null;

document.addEventListener('DOMContentLoaded', () => {
    console.log("Themes & Sentiment Refactored JS Loaded - Page-specific init");

    // *** Assign Elements AFTER DOM is ready ***
    loadingIndicator = document.getElementById('loading-indicator');
    errorDisplay = document.getElementById('error-display');
    analysisContent = document.getElementById('analysis-content');
    conversationCountDisplay = document.getElementById('conversation-count-display');
    analysisModelInfo = document.getElementById('analysis-model-info');
    loadingMessageMain = document.getElementById('loading-message-main');
    loadingMessageDetail = document.getElementById('loading-message-detail');

    // *** Log after assignment ***
    console.log("[DOMContentLoaded] Checking elements:", { 
        loadingIndicator: !!loadingIndicator, 
        errorDisplay: !!errorDisplay, 
        analysisContent: !!analysisContent 
    });

    // Check if essential elements were found
    if (!loadingIndicator || !errorDisplay || !analysisContent) {
        console.error("CRITICAL: Could not find essential layout elements (loading, error, content). Page may not function.");
        // Optionally display a severe error message to the user
    }

    // Removed block that forced loading indicator visibility here.
    // loadAnalysisData will handle showing it when it starts.

    // --- Date Range Selector REMOVED ---
    // The analysis will now always load ALL data (no date filter).
    // Compute a fixed early start date (project inception) and today's date.
    const allStartDate = '2024-01-01';
    const today = new Date();
    const endDate = today.toISOString().slice(0, 10); // YYYY-MM-DD

    console.log(`Loading full analysis for full date range ${allStartDate} -> ${endDate}`);
    loadAnalysisData(allStartDate, endDate);

    // *** Assign Modal Elements ***
    categoryModalElement = document.getElementById('categoryDetailModal');
    categoryModalTitle = document.getElementById('categoryDetailModalLabel');
    categoryModalBody = document.getElementById('categoryDetailModalBody');

    // *** Initialize Modal Instance ***
    if (categoryModalElement) {
        categoryModal = new bootstrap.Modal(categoryModalElement);
        console.log("Category detail modal instance created.");
    } else {
        console.error("Could not find category detail modal element (#categoryDetailModal).");
    }

    // *** Assign RAG Query Elements ***
    ragQueryInput = document.getElementById('rag-query-input');
    ragSubmitBtn = document.getElementById('submit-rag-query-btn');
    ragResponseArea = document.getElementById('rag-response-area');
    ragResponseContent = document.getElementById('rag-response-content');
    ragErrorDisplay = document.getElementById('rag-error-display');
    if (ragSubmitBtn) {
        ragSubmitSpinner = ragSubmitBtn.querySelector('.spinner-border');
    }

    // *** Log RAG element assignments ***
    console.log("[DOMContentLoaded] Checking RAG elements:", {
        ragQueryInput: !!ragQueryInput,
        ragSubmitBtn: !!ragSubmitBtn,
        ragResponseArea: !!ragResponseArea,
        ragResponseContent: !!ragResponseContent,
        ragErrorDisplay: !!ragErrorDisplay,
        ragSubmitSpinner: !!ragSubmitSpinner
    });

    // *** Assign Transcript Modal Elements ***
    transcriptModalElement = document.getElementById('transcriptModal');
    transcriptModalLabel = document.getElementById('transcriptModalLabel');
    transcriptModalBody = document.getElementById('transcriptModalBody');
    transcriptLoading = document.getElementById('transcript-loading');
    transcriptError = document.getElementById('transcript-error');
    transcriptContent = document.getElementById('transcript-content');

    // *** Initialize Transcript Modal Instance ***
    if (transcriptModalElement) {
        transcriptModal = new bootstrap.Modal(transcriptModalElement);
        console.log("Transcript modal instance created.");
    } else {
        console.error("Could not find transcript modal element (#transcriptModal).");
    }

    // Setup event listeners (including the new RAG button listener)
    setupEventListeners();

    // *** Initialize Bootstrap Tooltips for Info Icons ***
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    console.log(`Initialized ${tooltipList.length} Bootstrap tooltips.`);
    // *** End Tooltip Initialization ***
});

// Chart instances - declare globally to allow updates/destruction
let sentimentDistributionChart = null;

/**
 * Handles timeframe changes triggered by the global selector.
 * Calculates dates and calls loadAnalysisData.
 * @param {string} timeframe - The timeframe key (e.g., '7d', '30d', etc.) received from the selector.
 */
function handleTimeframeChange(timeframe) {
    console.log(`[handleTimeframeChange] Received timeframe key: ${timeframe}`);
    if (!timeframe) {
        console.error("handleTimeframeChange received invalid timeframe key.");
        timeframe = '7d'; // Fallback to default
    }
    // Get dates using the utility function
    const { startDate, endDate } = getDatesFromTimeframe(timeframe);
    console.log(`[handleTimeframeChange] Calculated dates: ${startDate} to ${endDate}`);
    if(startDate && endDate) {
        loadAnalysisData(startDate, endDate);
    } else {
        console.error("Failed to calculate dates from timeframe key.");
        if (errorDisplay) {
            errorDisplay.textContent = 'Could not determine date range.';
            errorDisplay.style.display = 'block';
        }
    }
}

/**
 * Main function to fetch and render analysis data based on selected dates.
 * @param {string} startDateISO - Start date in YYYY-MM-DD format
 * @param {string} endDateISO - End date in YYYY-MM-DD format
 */
async function loadAnalysisData(startDateISO, endDateISO) {
    console.log(`[loadAnalysisData] START - Dates: ${startDateISO} to ${endDateISO}`);

    if (!startDateISO || !endDateISO) {
        console.error("loadAnalysisData called with invalid dates:", startDateISO, endDateISO);
        if (errorDisplay) {
            errorDisplay.textContent = 'Invalid date range selected.';
            errorDisplay.style.display = 'block';
        }
        return;
    }

    // Reset UI state & SHOW loading indicator
    // Use requestAnimationFrame to ensure UI updates before potentially blocking API call
    requestAnimationFrame(() => {
        if (loadingIndicator) {
            loadingIndicator.style.display = 'block';
            loadingIndicator.style.opacity = '1';
            loadingIndicator.style.pointerEvents = 'auto';
        }
        if (loadingMessageMain) loadingMessageMain.textContent = "Sentiment Analysis Underway";
        if (loadingMessageDetail) loadingMessageDetail.textContent = "This process takes time to complete.";
        if (errorDisplay) errorDisplay.style.display = 'none';
        if (analysisContent) {
            analysisContent.style.display = 'none';
            analysisContent.style.opacity = '0';
        }
        if (conversationCountDisplay) conversationCountDisplay.textContent = '';
        if (analysisModelInfo) analysisModelInfo.textContent = '';

        // Destroy previous charts
        if (sentimentDistributionChart) sentimentDistributionChart.destroy();
        if (topThemesChart) topThemesChart.destroy();
        if (sentimentTrendsChart) sentimentTrendsChart.destroy();
        sentimentDistributionChart = null;
        topThemesChart = null;
        sentimentTrendsChart = null;

        // NOW trigger the API fetch *after* the UI update frame
        triggerApiFetch(startDateISO, endDateISO);
    });
}

// Helper function to contain the async API call and subsequent rendering
async function triggerApiFetch(startDateISO, endDateISO) {
     try {
        const url = `/api/themes-sentiment/full-analysis-v2?start_date=${encodeURIComponent(startDateISO)}&end_date=${encodeURIComponent(endDateISO)}`;
        console.log(`[loadAnalysisData] Calling API.fetch for: ${url}`);
        const data = await API.fetch(url);
        console.log("%%% RAW API DATA RECEIVED: %%%", JSON.stringify(data, null, 2));

        if (data && !data.error) {
            console.log("[loadAnalysisData] Data received successfully (no 'error' key). PRE-RENDER CALL.");

            const modelName = data.analysis_status?.model_name;
            if (modelName && modelName !== 'N/A' && loadingMessageMain) {
                loadingMessageMain.textContent = `Analysis Underway Using ${modelName}`;
            }
            if (loadingMessageDetail) loadingMessageDetail.textContent = "Processing results...";

            renderAnalysisData(data);

            console.log("[loadAnalysisData] renderAnalysisData finished (sync part).");

            // Update permanent info displays
            if (conversationCountDisplay) {
                const totalConvCount = data?.metadata?.total_conversations_in_range;
                if(totalConvCount !== undefined && totalConvCount !== null) {
                    conversationCountDisplay.innerHTML = `<span class="text-muted me-2">Total Conversations:</span><span class="fw-bold">${Formatter.number(totalConvCount)}</span>`;
                } else {
                    conversationCountDisplay.textContent = 'N/A';
                }
            }

            // Ensure any legacy date‑range selector element (if cached HTML) is hidden
            const legacySelector = document.getElementById('date-range-selector');
            if (legacySelector) legacySelector.style.display = 'none';

            if (analysisModelInfo) {
                 analysisModelInfo.textContent = modelName && modelName !== 'N/A' ? `Analysis by: ${modelName}` : '';
            }

        } else {
            let errorMsg = data?.error || 'Received empty or invalid data from server.';
            let errorDetails = data?.details || "";
            if (data?.timeout) errorMsg = `Analysis timed out. ${errorMsg}`;
            console.error(`[loadAnalysisData] Error received in data object: ${errorMsg}`, errorDetails);
            throw new Error(errorMsg, { cause: errorDetails });
        }

    } catch (error) {
        console.error("[loadAnalysisData] Catch block entered.");
        console.error("Error loading analysis data:", error);
        const errorMessage = error.message || "An unknown error occurred.";
        const errorDetails = error.cause || "";

        if (errorDisplay) {
            errorDisplay.innerHTML = ''; // Clear previous details first
            errorDisplay.textContent = `Failed to load analysis data: ${errorMessage}`;
            if(errorDetails) {
                const detailsSpan = document.createElement('span');
                detailsSpan.className = 'small d-block mt-1';
                detailsSpan.textContent = `Details: ${errorDetails}`;
                errorDisplay.appendChild(detailsSpan);
            }
             errorDisplay.style.display = 'block';
        }
        if (loadingIndicator) {
            loadingIndicator.style.opacity = '0';
             setTimeout(() => {
                 if (loadingIndicator) loadingIndicator.style.display = 'none';
             }, 300);
        }
        if (analysisContent) {
             analysisContent.style.display = 'none';
        }
    }
    console.log("[loadAnalysisData] END");
}

/**
 * Main function to populate the UI with the fetched analysis data.
 * Fades out spinner and fades in content upon successful completion.
 * @param {object} data - The analysis data object received from the API.
 * @param {HTMLElement} loadingIndicator - The loading indicator element.
 * @param {HTMLElement} analysisContent - The main content container element.
 */
function renderAnalysisData(data) {
    console.log("[renderAnalysisData] FUNCTION START.");

    // *** Log at start of function ***
    console.log("[renderAnalysisData] Start. Checking errorDisplay:", errorDisplay);

    console.log("Rendering analysis data components...", data);
    try {
        const sentimentData = data.sentiment_overview;
        const categorizedData = data.categorized_quotes;
        const metadata = data.metadata;
        const analysisStatus = data.analysis_status;

        // Update the main content area with the analysis results
        console.log('[renderAnalysisData] Rendering analysis data components...', data); // Log the whole data object

        // --- Update Metadata Display --- 
        const conversationsCountEl = document.getElementById('conversation-count-display');
        const analysisModelInfoEl = document.getElementById('analysis-model-info');
        
        // Update both the inline badge and (legacy) count display
        const totalConvCount = data?.metadata?.total_conversations_in_range;

        if (conversationsCountEl) {
            conversationsCountEl.textContent = totalConvCount ?? 'N/A';
        }

        const allBadgeCountEl = document.getElementById('total-conversations-display');
        if (allBadgeCountEl) {
            if (totalConvCount !== undefined && totalConvCount !== null) {
                // Add label and thousands‑separator formatting for improved aesthetics
                allBadgeCountEl.innerHTML = `<span class="fw-bold">${Formatter.number(totalConvCount)}</span><span class="text-muted small ms-1">conversations</span>`;
            } else {
                allBadgeCountEl.textContent = 'N/A';
            }
        }

        // Safely access analysis status and update model info
        if (analysisModelInfoEl) {
             // Use optional chaining ?. for safer access
            const modelName = data?.analysis_status?.model_name;
            if (modelName) {
                analysisModelInfoEl.textContent = `Analysis by: ${modelName}`;
                analysisModelInfoEl.style.display = 'block';
            } else {
                analysisModelInfoEl.style.display = 'none';
                console.warn('Analysis status or model name missing or invalid in API data', data?.analysis_status);
            }
        }
        // --- End Metadata Display --- 

        // clearPlaceholders(); // Hides loading/error, Shows analysisContent block // MOVED TO END OF TRY BLOCK

        // --- Render Components ---
        renderSentimentOverview(sentimentData);
        renderTopThemes(data.top_themes);
        renderSentimentTrends(data.sentiment_trends);
        renderThemeCorrelation(data.theme_sentiment_correlation);
        
        // *** NEW: Call renderCategoryLists ***
        renderCategoryLists(categorizedData?.common_questions, 'common-questions');
        renderCategoryLists(categorizedData?.concerns_skepticism, 'concerns-skepticism');
        
        renderPositiveInteractions(categorizedData?.positive_interactions);
        // --- End Render Components ---

        console.log("[renderAnalysisData] All rendering components called. PRE-TRANSITION.");

        // --- Handle Smooth Transition & Hide Loader (AFTER rendering) ---
        clearPlaceholders(); // Call here instead to ensure content is ready
        
        if (analysisContent) {
            analysisContent.style.display = 'block';
            requestAnimationFrame(() => {
                 if (analysisContent) analysisContent.style.opacity = '1';
            });
        }
        if (loadingIndicator) {
            loadingIndicator.style.opacity = '0';
            // Use a slightly longer timeout to ensure content is visible before hiding loader fully
            setTimeout(() => {
                 if (loadingIndicator) loadingIndicator.style.display = 'none';
            }, 500); 
        }
        // --- End Smooth Transition ---

    } catch (error) {
        console.error("Error during renderAnalysisData:", error);
        // *** ADD CHECKS in CATCH block ***
        if (errorDisplay) {
            errorDisplay.textContent = `Error rendering analysis results: ${error.message}`;
            errorDisplay.style.display = 'block';
        }
        // *** ADD CHECKS in CATCH block ***
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
            loadingIndicator.style.opacity = '0';
        }
        // *** ADD CHECKS in CATCH block ***
        if (analysisContent) {
             analysisContent.style.display = 'none';
        }
    }
}

// Function to safely destroy and nullify a chart instance
function destroyChart(chartInstance) {
    if (chartInstance) {
        chartInstance.destroy();
        chartInstance = null; // Ensure it's nullified
    }
    return null; // Return null for reassignment
}

// --- Rendering Functions using new styles ---

/**
 * Helper to update charts and handle empty states
 */
function updateChartAndHandleEmpty(chartInstance, config, containerId) {
    const container = document.getElementById(containerId);
    const canvas = container?.querySelector('canvas');
    const emptyMessage = container?.querySelector('.empty-chart-message');

    if (!container || !canvas || !emptyMessage) {
        console.error(`Chart container, canvas, or empty message not found for ${containerId}`);
        return null; // Return null if elements missing
    }

    // Check if there's meaningful data to display
    const hasData = config.data && config.data.datasets && 
                    config.data.datasets.some(dataset => dataset.data && dataset.data.length > 0 && dataset.data.some(d => d !== null && d !== undefined && d !== 0));

    if (hasData) {
        canvas.style.display = 'block';
        emptyMessage.style.display = 'none';
        // If chart exists, update it; otherwise, create it
        if (chartInstance) {
            chartInstance.data = config.data;
            chartInstance.options = config.options;
            chartInstance.update();
            console.log(`Chart updated: ${canvas.id}`);
            return chartInstance;
        } else {
            try {
                 const newChart = new Chart(canvas, config);
                 console.log(`Chart created: ${canvas.id}`);
                 return newChart; // Return the new instance
            } catch (e) {
                 console.error(`Failed to create chart ${canvas.id}:`, e);
                 canvas.style.display = 'none';
                 emptyMessage.textContent = 'Error rendering chart.';
                 emptyMessage.style.display = 'block';
                 return null;
            }
        }
    } else {
        // No data: Hide canvas, show empty message, destroy existing chart
        canvas.style.display = 'none';
        emptyMessage.textContent = 'No data available for this period.'; // Standard empty message
        emptyMessage.style.display = 'block';
        if (chartInstance) {
             chartInstance = destroyChart(chartInstance);
        }
        console.log(`Chart empty: ${canvas.id}`);
        return null; // Return null as chart is destroyed or not created
    }
}

/**
 * Renders the Sentiment Overview section (Pie chart and labels).
 */
function renderSentimentOverview(sentimentData) {
    // Wrap the entire function logic in try...catch
    try {
        console.log("Rendering Sentiment Overview:", sentimentData); // Debugging

        const overallSentimentEl = document.getElementById('overall-sentiment-label');
        const callerSentimentEl = document.getElementById('caller-average-sentiment');
        const agentSentimentEl = document.getElementById('agent-average-sentiment');
        const distributionChartEl = document.getElementById('sentiment-distribution-chart');
        const distributionContainer = document.getElementById('sentiment-distribution-chart-container');
        const overviewContentEl = document.getElementById('sentiment-overview-content');

        if (!sentimentData || !overviewContentEl || !overallSentimentEl || !callerSentimentEl || !agentSentimentEl || !distributionChartEl || !distributionContainer) {
            console.error('Sentiment Overview: Missing data or required elements.',
                { sentimentData: !!sentimentData, overviewContentEl: !!overviewContentEl, overallSentimentEl: !!overallSentimentEl,
                  callerSentimentEl: !!callerSentimentEl, agentSentimentEl: !!agentSentimentEl,
                  distributionChartEl: !!distributionChartEl, distributionContainer: !!distributionContainer });

            if (overviewContentEl) {
                 overviewContentEl.innerHTML = '<p class="text-danger text-center">Could not render sentiment overview data.</p>';
            } else {
                console.error("Cannot display error message because #sentiment-overview-content element is missing.")
            }
            return;
        }

        // Reset the content area
        overviewContentEl.innerHTML = `
            <p class="text-muted mb-2"><strong>Overall Sentiment:</strong> <span id="overall-sentiment-label">N/A</span></p>
            <div class="mb-3 chart-container" id="sentiment-distribution-chart-container">
                <canvas id="sentiment-distribution-chart" height="150"></canvas>
                <div class="empty-chart-message" style="display: none;">No sentiment data available.</div>
            </div>
            <div class="row text-center">
                <div class="col">
                    <h6>Caller Sentiment</h6>
                    <p class="fs-4" id="caller-average-sentiment">N/A</p>
                </div>
                <div class="col">
                    <h6>Lily's Sentiment</h6>
                    <p class="fs-4" id="agent-average-sentiment">N/A</p>
                </div>
            </div>
        `;
        // Re-get elements after reset
        const newOverallSentimentEl = document.getElementById('overall-sentiment-label');
        const newCallerSentimentEl = document.getElementById('caller-average-sentiment');
        const newAgentSentimentEl = document.getElementById('agent-average-sentiment');
        const newDistributionChartEl = document.getElementById('sentiment-distribution-chart');
        const newDistributionContainer = document.getElementById('sentiment-distribution-chart-container');

        if (newOverallSentimentEl) newOverallSentimentEl.textContent = sentimentData.overall_sentiment_label || 'N/A';

        const formatScore = (score) => {
            if (score === null || score === undefined) return 'N/A';
            return Formatter && Formatter.sentimentLabel ? Formatter.sentimentLabel(score) : parseFloat(score).toFixed(2);
        };
        if (newCallerSentimentEl) newCallerSentimentEl.textContent = formatScore(sentimentData.caller_average_sentiment);
        if (newAgentSentimentEl) newAgentSentimentEl.textContent = formatScore(sentimentData.agent_average_sentiment);

        // --- Sentiment Distribution Chart ---
        if (sentimentDistributionChart) {
            sentimentDistributionChart.destroy();
            sentimentDistributionChart = null;
            console.log("Destroyed existing sentiment distribution chart");
        }

        const distributionData = sentimentData.sentiment_distribution;
        if (distributionData && Object.keys(distributionData).length > 0 && newDistributionChartEl && newDistributionContainer) {
             if (newDistributionChartEl) newDistributionChartEl.style.display = '';
             if (newDistributionContainer) newDistributionContainer.style.display = '';
             const emptyMsg = newDistributionContainer?.querySelector('.empty-chart-message');
             if(emptyMsg) emptyMsg.style.display = 'none';

             const labels = Object.keys(distributionData);
             const values = Object.values(distributionData);

             const backgroundColors = labels.map(label => {
                 switch (label.toLowerCase()) {
                     case 'very_positive': return '#198754';
                     case 'positive': return '#20c997';
                     case 'neutral': return '#ffc107';
                     case 'negative': return '#fd7e14';
                     case 'very_negative': return '#dc3545';
                     default: return '#6c757d';
                 }
             });

             const ctx = newDistributionChartEl.getContext('2d');
             sentimentDistributionChart = initializeChart(ctx, {
                 type: 'doughnut',
                 data: {
                     labels: labels.map(label => label.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())), 
                     datasets: [{
                         label: 'Sentiment Distribution',
                         data: values,
                         backgroundColor: backgroundColors,
                         borderWidth: 1
                     }]
                 },
                 options: {
                     responsive: true,
                     maintainAspectRatio: false,
                     plugins: {
                         legend: {
                             position: 'top',
                         },
                         tooltip: {
                             callbacks: {
                                 label: function(context) {
                                     let label = context.label || '';
                                     if (label) label += ': ';
                                     if (context.parsed !== null) label += context.parsed;
                                     return label;
                                 }
                             }
                         }
                     }
                 }
             });
             console.log("Created sentiment distribution chart");

        } else {
             console.log("Sentiment Distribution: No distribution data available or chart element missing.");
             if (newDistributionContainer) {
                if (newDistributionChartEl) newDistributionChartEl.style.display = 'none';
                const noDataMsg = newDistributionContainer.querySelector('.empty-chart-message');
                if (noDataMsg) {
                    noDataMsg.style.display = 'block';
                    noDataMsg.textContent = 'No sentiment distribution data available for this period.';
                } else {
                     newDistributionContainer.innerHTML = '<p class="text-muted text-center no-data-message">No sentiment distribution data available for this period.</p>';
                }
             } else {
                console.error("Cannot display 'no distribution data' message because container element is missing.");
             }
        }
    // *** This closing brace matches the try block at the top ***
    } catch (error) {
        console.error("CRITICAL Error rendering sentiment overview:", error);
        const contentEl = document.getElementById('sentiment-overview-content');
        if (contentEl) {
            contentEl.innerHTML = `<p class="text-danger text-center">Error displaying Sentiment Overview: ${error.message}</p>`;
        } else {
             console.error("Could not display Sentiment Overview error in UI, main container missing.");
        }
    }
}

/**
 * Renders the Top Themes section (Bar chart and list).
 */
function renderTopThemes(themeData) {
    // *** Corrected: Access data.top_themes.themes (it's an array) ***
    const themesArray = themeData?.themes || []; 
    const themeList = document.getElementById('top-themes-list');

    if (themeList) themeList.innerHTML = '';

    // *** Corrected: Process the array ***
    const labels = themesArray.map(item => item.theme);
    const dataValues = themesArray.map(item => item.count);

    if (labels.length === 0) {
        if (themeList) themeList.innerHTML = '<li class="list-group-item text-muted">No themes identified.</li>';
    } else {
        // Populate list from the array
        themesArray.forEach(item => {
            if (themeList) {
                const li = document.createElement('li');
                li.className = 'list-group-item d-flex justify-content-between align-items-center';
                li.textContent = item.theme;
                const span = document.createElement('span');
                span.className = 'badge bg-secondary rounded-pill';
                span.textContent = item.count;
                li.appendChild(span);
                themeList.appendChild(li);
            }
        });
    }

    const config = {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Theme Mentions',
                data: dataValues,
                backgroundColor: vizPalette.slice(0, labels.length), 
                borderColor: themeColors.white,
                borderWidth: 1
            }]
        },
        options: {
            ...commonChartOptions,
            indexAxis: 'y', // Horizontal bar chart
            scales: {
                 ...commonChartOptions.scales,
                x: { // Mentions count on X axis
                     ...commonChartOptions.scales.x,
                     title: {
                        display: true,
                        text: 'Number of Mentions',
                        color: themeColors.darkGray,
                        font: { ...titleFont, size: 12 }
                    }
                },
                y: { // Themes on Y axis
                    ...commonChartOptions.scales.y,
                    ticks: { 
                        color: themeColors.textMuted, 
                        font: baseFont, 
                        autoSkip: false // Ensure all themes are shown
                    },
                    grid: { display: false } // Cleaner look without Y grid lines
                }
            },
            plugins: {
                ...commonChartOptions.plugins,
                legend: { display: false }, // Hide legend for single dataset bar
                title: { // Add title
                    display: true,
                    text: 'Top Themes by Frequency',
                    font: titleFont,
                    color: themeColors.darkGray,
                    padding: { bottom: 10 }
                },
                 tooltip: { // Customize tooltip for bar chart
                     ...commonChartOptions.plugins.tooltip,
                     callbacks: {
                        label: function(context) {
                            return ` Mentions: ${context.parsed.x || 0}`;
                        }
                    }
                }
            }
        }
    };

    topThemesChart = updateChartAndHandleEmpty(topThemesChart, config, 'top-themes-chart-container');
}

/**
 * Renders the Sentiment Trends Over Time section (Line chart).
 */
function renderSentimentTrends(trendData) {
    // *** Corrected: Access data.sentiment_trends.labels and .average_sentiment_scores ***
    const labels = trendData?.labels || []; // Access labels array
    const avgScores = trendData?.average_sentiment_scores || []; // Access scores array

    // *** Simplified: Only one dataset (average) is provided ***
    const config = {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Average Sentiment', // Updated label
                    data: avgScores,           // Use avgScores
                    borderColor: vizPalette[3] || themeColors.accent, // Use accent color or fallback
                    borderWidth: 2,
                    pointBackgroundColor: vizPalette[3] || themeColors.accent,
                    pointRadius: 3,
                    tension: 0.4,
                    fill: true,
                    // Safely call hexToRgba
                    backgroundColor: (vizPalette[3] && vizPalette[3].startsWith('#')) 
                                     ? hexToRgba(vizPalette[3], 0.1) 
                                     : 'rgba(247, 37, 133, 0.1)' // Fallback transparent accent
                }
                // Add datasets for caller/agent trends if data structure provides them
            ]
        },
        options: {
            ...commonChartOptions,
            scales: {
                y: {
                    ...commonChartOptions.scales.y,
                    min: -1, 
                    max: 1,
                    title: { 
                        display: true,
                        text: 'Average Sentiment Score',
                        color: themeColors.darkGray,
                        font: { ...titleFont, size: 12 }
                    }
                },
                x: {
                    ...commonChartOptions.scales.x,
                    type: 'time', // Use time scale for dates
                    time: {
                        unit: 'day',
                        tooltipFormat: 'MMM d, yyyy', // Format for tooltips
                        displayFormats: { // Display formats on axis
                            day: 'MMM d'
                        }
                    },
                     title: { // X axis title
                        display: true,
                        text: 'Date',
                        color: themeColors.darkGray,
                        font: { ...titleFont, size: 12 }
                    }
                }
            },
            plugins: {
                ...commonChartOptions.plugins,
                title: { // Add title
                    display: true,
                    text: 'Sentiment Score Over Time',
                    font: titleFont,
                    color: themeColors.darkGray,
                    padding: { bottom: 10 }
                },
                 tooltip: { // Customize tooltip for line chart
                     ...commonChartOptions.plugins.tooltip,
                     callbacks: {
                        label: function(context) {
                             let label = context.dataset.label || '';
                             if (label) {
                                 label += ': ';
                             }
                             if (context.parsed.y !== null && typeof context.parsed.y !== 'undefined') {
                                 label += context.parsed.y.toFixed(2); // Format sentiment score
                             } else {
                                 label += 'N/A'; // Fallback
                             }
                             return label;
                        }
                    }
                }
            }
        }
    };

    sentimentTrendsChart = updateChartAndHandleEmpty(sentimentTrendsChart, config, 'sentiment-trends-chart-container');
}

// Helper function to convert hex color to rgba
function hexToRgba(hex, alpha = 1) {
    let c;
    if (/^#([A-Fa-f0-9]{3}){1,2}$/.test(hex)) {
        c = hex.substring(1).split('');
        if (c.length == 3) {
            c = [c[0], c[0], c[1], c[1], c[2], c[2]];
        }
        c = '0x' + c.join('');
        return `rgba(${[(c >> 16) & 255, (c >> 8) & 255, c & 255].join(',')},${alpha})`;
    }
    console.warn('Bad Hex received by hexToRgba:', hex); 
    return `rgba(0,0,0,${alpha})`; // Fallback
}

/**
 * Renders the Theme & Sentiment Correlation table.
 */
function renderThemeCorrelation(correlationData) {
    // *** Corrected: Access data.theme_sentiment_correlation (it's an array) ***
    const correlationArray = correlationData || []; 
    const tbody = document.getElementById('theme-correlation-table');
    if (!tbody) return;

    tbody.innerHTML = ''; // Clear previous data

    // *** Corrected: Check array length ***
    if (!correlationArray || correlationArray.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">No correlation data available.</td></tr>';
        return;
    }

    // *** Corrected: Iterate over the array, sort by mentions ***
    correlationArray.sort((a, b) => (b.mentions || 0) - (a.mentions || 0));

    correlationArray.forEach(item => {
        const tr = document.createElement('tr');
        // *** Use Formatter helpers (assuming they exist) ***
        // Convert label string to a pseudo-score for coloring if needed, or use label directly
        const sentimentLabel = item.sentiment_label || 'N/A'; 
        const sentimentClass = `badge bg-${getSentimentClassFromLabel(sentimentLabel)}`; // Use a helper based on label string
        
        tr.innerHTML = `
            <td>${item.theme || 'N/A'}</td>
            <td>${item.mentions || 0}</td>
            <td><span class="${sentimentClass}">${sentimentLabel}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

// *** ADD Helper function to map label string to class ***
function getSentimentClassFromLabel(label) {
    const lowerLabel = (label || '').toLowerCase();
    if (lowerLabel.includes('positive')) return 'success';
    if (lowerLabel.includes('negative')) return 'danger';
    if (lowerLabel.includes('neutral')) return 'warning';
    return 'secondary'; // Default
}

/**
 * Renders lists of clickable category names (Top 5).
 * @param {Array<object>} categories - Array of category objects, each with `category_name`, `count`, and `quotes`.
 * @param {string} type - Identifier string ('common-questions' or 'concerns-skepticism').
 */
function renderCategoryLists(categories, type) {
    const listContainerId = `${type}-list`; // e.g., common-questions-list
    const listContainer = document.getElementById(listContainerId);

    if (!listContainer) {
        console.error(`Category list container not found: #${listContainerId}`);
        return;
    }

    listContainer.innerHTML = ''; // Clear placeholder

    if (!categories || categories.length === 0) {
        listContainer.innerHTML = `<div class="text-center text-muted p-3">No ${type.replace('-', ' ')} identified.</div>`;
        return;
    }

    // Sort categories by count (descending) 
    const sortedCategories = [...categories].sort((a, b) => (b.count || 0) - (a.count || 0)); // Use spread to avoid modifying original array
    
    // *** Correctly slice the sorted array ***
    const topCategories = sortedCategories.slice(0, 5);

    console.log(`Rendering Top 5 ${type} (from ${sortedCategories.length} total):`, topCategories);

    const listGroup = document.createElement('ul');
    listGroup.className = 'list-group list-group-flush';

    topCategories.forEach((category, index) => {
        // *** Add logging and try...catch for each item ***
        console.log(`[${type}] Processing category item ${index}:`, category);
        try {
            const categoryName = category.category_name || 'Unnamed Category';
            const count = category.count || 0;
            const quotes = category.quotes || [];

            const listItem = document.createElement('li');
            // listItem.className = 'list-group-item'; // Removed class

            const link = document.createElement('a');
            link.href = '#';
            link.className = 'd-flex justify-content-between align-items-center text-decoration-none category-list-item text-primary py-2 px-3 border-bottom';
            link.dataset.categoryName = categoryName;
            try {
                link.dataset.quotes = JSON.stringify(quotes);
            } catch (e) {
                console.error(`Error stringifying quotes for category ${categoryName}:`, e);
                link.dataset.quotes = '[]'; 
            }
            
            const nameSpan = document.createElement('span');
            nameSpan.textContent = categoryName;
            nameSpan.className = 'me-2';

            const badge = document.createElement('span');
            badge.className = 'badge bg-secondary rounded-pill';
            badge.textContent = count;

            link.appendChild(nameSpan);
            link.appendChild(badge);
            listItem.appendChild(link);
            listGroup.appendChild(listItem);
            console.log(`[${type}] Successfully appended item ${index}: ${categoryName}`);
        } catch (error) {
            console.error(`[${type}] Error processing category item ${index}:`, category, error);
            // Optionally append an error message placeholder to the list
        }
    });

    listContainer.appendChild(listGroup);

    // Optionally add a note if more categories were available
    if (sortedCategories.length > 5) {
        const moreNote = document.createElement('p');
        moreNote.className = 'small text-muted mt-2';
        moreNote.textContent = `Top 5 shown. ${sortedCategories.length - 5} more categories identified.`;
        listContainer.appendChild(moreNote);
    }
}

/**
 * Renders the list of most positive interactions (Top 10).
 * @param {object} interactionData - Object containing `count` and `quotes` array.
 */
function renderPositiveInteractions(interactionData) {
    const listContainer = document.getElementById('positive-interactions-list');
    const countSpan = document.getElementById('positive-interactions-count');

    if (!listContainer || !countSpan) {
        console.error('Positive Interactions: Missing list container or count span element.');
        return;
    }

    listContainer.innerHTML = ''; // Clear previous content
    const totalCount = interactionData?.count || 0;
    countSpan.textContent = totalCount; // Show total count

    const quotes = interactionData?.quotes;

    if (!quotes || quotes.length === 0) {
        listContainer.innerHTML = '<li class="list-group-item text-muted text-center">No particularly positive interactions identified.</li>';
        return;
    }

    // Sort by sentiment_score (desc) and take top 10
    // Ensure sentiment_score exists and is a number for sorting
    const sortedQuotes = [...quotes] // Use spread to avoid modifying original array
        .filter(q => q.sentiment_score !== null && q.sentiment_score !== undefined)
        .sort((a, b) => b.sentiment_score - a.sentiment_score);
        
    // *** Correctly slice the sorted array ***
    const topQuotes = sortedQuotes.slice(0, 10);

    console.log(`Rendering Top 10 Positive Interactions (from ${sortedQuotes.length} available with scores):`, topQuotes);

    const listGroup = document.createElement('ul');
    listGroup.className = 'list-group list-group-flush';

    topQuotes.forEach((interaction, index) => {
         // *** Add logging and try...catch for each item ***
        console.log(`[PositiveInteractions] Processing item ${index}:`, interaction);
        try {
            const listItem = document.createElement('li');
            listItem.className = 'list-group-item d-flex justify-content-between align-items-center py-2';

            const textElement = document.createElement('span');
            textElement.className = 'interaction-quote me-3'; 

            if (interaction.conversation_id && String(interaction.conversation_id).toLowerCase() !== 'null') {
                const link = document.createElement('a');
                link.href = '#'; 
                link.className = 'text-decoration-none text-dark transcript-link'; 
                link.dataset.conversationId = interaction.conversation_id;
                link.innerHTML = `<i class="bi bi-quote me-1"></i>${interaction.quote_text || "Empty Quote"}`; 
                textElement.appendChild(link);
            } else {
                textElement.innerHTML = `<i class="bi bi-quote me-1 text-muted"></i><span class="text-muted">${interaction.quote_text || "Empty Quote"}</span>`;
            }

            const sentimentBadge = document.createElement('span');
            let sentimentLabel = interaction.sentiment_label || 'Positive'; 
            if (!interaction.sentiment_label && interaction.sentiment_score !== null && interaction.sentiment_score !== undefined) {
                sentimentLabel = Formatter && Formatter.sentimentLabel ? Formatter.sentimentLabel(interaction.sentiment_score) : 'Positive';
            }
            sentimentBadge.className = `badge rounded-pill ${getSentimentClassFromLabel(sentimentLabel)} text-nowrap`;
            sentimentBadge.textContent = sentimentLabel;

            listItem.appendChild(textElement); 
            listItem.appendChild(sentimentBadge); 
            listGroup.appendChild(listItem);
             console.log(`[PositiveInteractions] Successfully appended item ${index}`);
        } catch (error) {
             console.error(`[PositiveInteractions] Error processing item ${index}:`, interaction, error);
        }
    });
    
    listContainer.appendChild(listGroup);

    // Optionally add a note if more interactions were available
    const totalPositiveAvailable = sortedQuotes.length;
    if (totalPositiveAvailable > 10) {
        const moreNote = document.createElement('p');
        moreNote.className = 'small text-muted mt-2';
        // Adjust message slightly
        moreNote.textContent = `Top 10 shown. ${totalPositiveAvailable - 10} more positive interactions identified with sentiment scores.`;
        listContainer.appendChild(moreNote);
    } else if (totalCount > totalPositiveAvailable) {
        // Handle case where total count is high but few have scores
        const moreNote = document.createElement('p');
        moreNote.className = 'small text-muted mt-2';
        moreNote.textContent = `${topQuotes.length} shown. Some interactions may lack sentiment scores for ranking. Total positive: ${totalCount}.`;
        listContainer.appendChild(moreNote);
    } else if (totalCount > 10 && totalPositiveAvailable <= 10) {
         const moreNote = document.createElement('p');
        moreNote.className = 'small text-muted mt-2';
        moreNote.textContent = `${topQuotes.length} shown. Total positive interactions: ${totalCount}.`;
        listContainer.appendChild(moreNote);
    }
}

// Add helper functions to Formatter in utils.js or here if local
// Assuming these are added to utils.js based on previous context
/* 
Formatter.sentimentLabel = function(score) { ... };
Formatter.sentimentColorClass = function(score) { ... }; 
*/

console.log("Themes & Sentiment Refactored JS Parsed"); 

// Helper to initialize or update charts
function initializeChart(ctx, config) {
     try {
         // Ensure ctx is valid
         if (!ctx) {
             console.error("Chart context is invalid.");
             return null;
         }
         const chart = new Chart(ctx, config);
         console.log("Chart created:", config?.data?.datasets?.[0]?.label || ctx.canvas.id); // Log which chart was created
         return chart;
     } catch (error) {
         console.error("Error initializing chart:", error, "on canvas:", ctx?.canvas?.id, "with config:", config);
         const canvas = ctx?.canvas;
         if (canvas && canvas.parentElement) {
             const errorMsg = document.createElement('p');
             errorMsg.className = 'text-danger small text-center';
             errorMsg.textContent = 'Error loading chart.';
             if (!canvas.parentElement.querySelector('.text-danger')) {
                  canvas.style.display = 'none';
                 canvas.parentElement.appendChild(errorMsg);
             }
         }
         return null; // Return null to indicate failure
     }
}

/**
 * Hides loading/error placeholders and makes the main content area visible.
 */
function clearPlaceholders() {
    if (loadingIndicator) loadingIndicator.style.display = 'none';
    if (errorDisplay) errorDisplay.style.display = 'none';
    if (analysisContent) analysisContent.style.display = 'block'; // Show the main content area
}

/**
 * Placeholder/Implementation for showing the transcript modal.
 * Fetches conversation details and renders transcript.
 * @param {string} externalId - The external ID of the conversation to show.
 */
async function showTranscriptModal(externalId) {
    console.log(`[showTranscriptModal] Attempting to show transcript for ID: ${externalId}`);

    if (!transcriptModal || !transcriptModalBody || !transcriptLoading || !transcriptError || !transcriptContent) {
        console.error("Transcript modal elements not initialized. Cannot show transcript.");
        alert("Transcript viewer component is not ready. Please try again later.");
        return;
    }

    // Reset modal state
    transcriptLoading.style.display = 'block';
    transcriptError.style.display = 'none';
    transcriptContent.style.display = 'none';
    transcriptContent.innerHTML = ''; // Clear previous transcript
    if(transcriptModalLabel) transcriptModalLabel.textContent = `Conversation: ${externalId}`;

    // Show the modal (with loading indicator visible)
    transcriptModal.show();

    try {
        // Fetch conversation details from the API
        const apiUrl = `/api/conversations/${encodeURIComponent(externalId)}`;
        console.log(`[showTranscriptModal] Fetching data from: ${apiUrl}`);
        const response = await fetch(apiUrl);
        
        if (!response.ok) {
            let errorMsg = `HTTP error ${response.status}`; 
            try {
                const errorData = await response.json();
                errorMsg = errorData.error || errorMsg;
            } catch (e) { /* Ignore if response not JSON */ }
            throw new Error(errorMsg);
        }

        const data = await response.json();
        console.log(`[showTranscriptModal] Received data for ${externalId}:`, data);

        if (data && data.transcript && Array.isArray(data.transcript)) {
            // Render the transcript using iMessage style
            renderTranscriptInModal(data);
            transcriptContent.style.display = 'block';
        } else {
            throw new Error("Invalid or missing transcript data received from server.");
        }

    } catch (error) {
        console.error(`Error fetching or rendering transcript for ${externalId}:`, error);
        transcriptError.textContent = `Failed to load transcript: ${error.message}`;
        transcriptError.style.display = 'block';
    } finally {
        // Hide loading indicator
        transcriptLoading.style.display = 'none';
    }
}

/**
 * Renders the transcript messages into the modal body using iMessage styling.
 * @param {Array} transcript - The array of transcript messages.
 */
function renderTranscriptInModal(data) {
    console.log("[renderTranscriptInModal - V_Compare] START. Received data:", data);

    if (!transcriptContent || !transcriptError) {
        console.error("[renderTranscriptInModal] Transcript content or error display element not found.");
        return;
    }

    // Clear previous content and error messages
    transcriptContent.innerHTML = '';
    transcriptError.style.display = 'none';
    transcriptContent.style.display = 'none'; // Hide until populated

    // Use the 'transcript' array and expect 'role'/'content'/'timestamp' keys
    const transcriptMessages = data.transcript;

    // Check if transcript data is valid
    if (!transcriptMessages || !Array.isArray(transcriptMessages) || transcriptMessages.length === 0) {
        console.warn("[renderTranscriptInModal] No valid transcript messages found in data.transcript:", transcriptMessages);
        transcriptError.textContent = 'No transcript messages available for this conversation.';
        transcriptError.style.display = 'block';
        return;
    }

    const listContainer = document.createElement('div'); 
    listContainer.className = 'transcript-list'; // Use a container div

    try {
        transcriptMessages.forEach((message, index) => {
            console.log(`[renderTranscriptInModal] Processing message ${index}:`, message);
            
            // Basic validation for role and content
            if (!message || typeof message.role !== 'string' || typeof message.content !== 'string') {
                console.warn(`[renderTranscriptInModal] Skipping invalid message ${index}:`, message);
                return; 
            }
            
            // Determine speaker and alignment based on role
            const isAgent = message.role.toLowerCase() === 'agent';
            const rowClass = isAgent ? 'agent-message' : 'caller-message'; // Parent row class for alignment/styling
            const speakerLabel = isAgent ? 'Lily (Psychic)' : 'Curious Caller'; // *** Use "Curious Caller" ***
            const avatarIcon = isAgent ? 'fas fa-headset' : 'fas fa-user'; // Font Awesome icons

            // Main row container (controls left/right via CSS)
            const messageRow = document.createElement('div');
            messageRow.className = `${rowClass} mb-3`; // Add margin bottom to the row

            // Group container (aligns avatar and bubble)
            const messageGroup = document.createElement('div');
            messageGroup.className = 'message-group d-flex align-items-end'; // Use flex for avatar/bubble alignment

            // Avatar Element
            const avatarContainer = document.createElement('div');
            avatarContainer.className = `avatar-container ${isAgent ? 'me-2' : 'ms-2 order-1'}`; 
            avatarContainer.innerHTML = `<i class="${avatarIcon} fa-lg"></i>`; // Slightly larger icon?

            // Bubble Element (plain div)
            const messageBubble = document.createElement('div');
            messageBubble.className = 'message-bubble d-flex flex-column'; // Bubble container

            // Speaker Name inside Bubble
            const speakerNameSpan = document.createElement('span');
            speakerNameSpan.className = 'speaker-label mb-1'; // Class for speaker name
            speakerNameSpan.textContent = speakerLabel;

            // Message Text inside Bubble
            const messageTextSpan = document.createElement('span');
            messageTextSpan.className = 'message-text'; // Class for message text
            messageTextSpan.textContent = message.content || '(No text content)'; // Use .content

            // Timestamp inside Bubble
            const timestampSpan = document.createElement('span');
            timestampSpan.className = 'timestamp mt-1 align-self-end'; // Class for timestamp, aligned right
            // Use message.timestamp and Formatter.time (like working version)
            timestampSpan.textContent = message.timestamp ? Formatter.time(message.timestamp) : 'Unknown time';

            // Assemble bubble content
            messageBubble.appendChild(speakerNameSpan);
            messageBubble.appendChild(messageTextSpan);
            messageBubble.appendChild(timestampSpan);

            // Assemble message group (avatar + bubble)
            // Order depends on speaker
            if (isAgent) {
                messageGroup.appendChild(avatarContainer);
                messageGroup.appendChild(messageBubble);
            } else {
                 messageGroup.appendChild(messageBubble); // Bubble first for caller
                 messageGroup.appendChild(avatarContainer); // Avatar second for caller
            }
                         
            // Append the group to the row
            messageRow.appendChild(messageGroup);

            // Add the complete row to the main container
            listContainer.appendChild(messageRow); 
        }); // End forEach message

        // Append the populated list group to the main content area
        transcriptContent.appendChild(listContainer);
        transcriptContent.style.display = 'block'; // Show the populated content

    } catch (error) {
        console.error("[renderTranscriptInModal] Error processing messages:", error);
        transcriptError.textContent = 'An error occurred while rendering the transcript.';
        transcriptError.style.display = 'block';
        transcriptContent.style.display = 'none';
    }

    console.log("[renderTranscriptInModal] END.");
}

/**
 * Sets up event listeners after the DOM is ready.
 * Includes listeners for RAG submit button and category list items.
 */
function setupEventListeners() {
    // Listener for RAG Submit Button
    if (ragSubmitBtn) {
        ragSubmitBtn.addEventListener('click', submitRagQuery);
        console.log("Event listener attached to RAG submit button.");
    } else {
        console.error("Could not find RAG submit button to attach listener.");
    }

    // Delegated listener for category items (if using the category list modal)
    const analysisContentArea = document.getElementById('analysis-content');
    if (analysisContentArea && categoryModal) { // Check if category modal exists
        analysisContentArea.addEventListener('click', (event) => {
            const categoryItem = event.target.closest('.category-list-item');
            if (categoryItem) {
                event.preventDefault();
                const categoryName = categoryItem.dataset.categoryName;
                const quotesJson = categoryItem.dataset.quotes;
                console.log(`Category item clicked: ${categoryName}`);
                if (categoryName && quotesJson) {
                    try {
                        const quotes = JSON.parse(quotesJson);
                        if (categoryModalTitle) categoryModalTitle.textContent = categoryName || 'Category Details';
                        if (categoryModalBody) populateModalBody(quotes);
                        categoryModal.show();
                    } catch (e) {
                        console.error("Error parsing quotes JSON or showing category modal:", e);
                        if (categoryModalBody) categoryModalBody.innerHTML = '<p class="text-danger">Error loading quotes.</p>';
                        if (categoryModalTitle) categoryModalTitle.textContent = 'Error';
                        categoryModal.show();
                    }
                } else {
                     console.warn("Missing category data for clicked item.");
                }
            }
        });
        console.log("Delegated event listener attached for category list items.");
    } else if (!analysisContentArea){
         console.error("Could not find #analysis-content to attach delegated listeners.");
    } else if (!categoryModal) {
         console.warn("#analysis-content found, but categoryModal instance is missing. No category item listener attached.");
    }
    
    // Note: Listeners for transcript links are now handled inline in the link creation within submitRagQuery
    // and potentially within renderPositiveInteractions if those links are also meant to open the transcript modal.
    // If positive interaction links should also open the modal, update that rendering function.
}

/**
 * Populates the category detail modal body with a list of quotes.
 * @param {Array<object>} quotes - Array of quote objects for the category.
 */
function populateModalBody(quotes) {
    if (!categoryModalBody) return;

    categoryModalBody.innerHTML = ''; // Clear previous content

    const totalQuotes = quotes?.length || 0;

    if (totalQuotes === 0) {
        categoryModalBody.innerHTML = '<p class="text-muted">No quotes found for this category.</p>';
        return;
    }

    // *** Slice to get Top 5 quotes for display ***
    const topQuotes = quotes.slice(0, 5);
    console.log(`Displaying Top 5 quotes in modal (from ${totalQuotes} total):`, topQuotes);

    const listGroup = document.createElement('ul');
    listGroup.className = 'list-group list-group-flush';

    // *** Loop through topQuotes only ***
    topQuotes.forEach(quoteData => {
        const listItem = document.createElement('li');
        listItem.className = 'list-group-item d-flex justify-content-between align-items-start py-2 px-0';

        const quoteTextContainer = document.createElement('div');
        quoteTextContainer.className = 'me-3 flex-grow-1';

        if (quoteData.conversation_id && String(quoteData.conversation_id).toLowerCase() !== 'null') {
            const link = document.createElement('a');
            link.href = '#';
            link.className = 'text-decoration-none text-dark transcript-link';
            link.dataset.conversationId = quoteData.conversation_id;
             // Store quote text in data attribute for potential highlighting later
            link.dataset.quoteText = quoteData.quote_text || ''; 
            // Make the quote link call showTranscriptModal
            link.onclick = (e) => { e.preventDefault(); showTranscriptModal(quoteData.conversation_id); };
            link.innerHTML = `<i class="bi bi-quote me-1"></i>${quoteData.quote_text || "Empty Quote"}`;
            quoteTextContainer.appendChild(link);
        } else {
            quoteTextContainer.innerHTML = `<i class="bi bi-quote me-1 text-muted"></i><span class="text-muted">${quoteData.quote_text || "Empty Quote"}</span>`;
        }

        // Optionally add sentiment badge if needed (adapting from positive interactions logic)
        // if (quoteData.sentiment_label || quoteData.sentiment_score !== undefined) { ... }

        listItem.appendChild(quoteTextContainer);
        listGroup.appendChild(listItem);
    });

    categoryModalBody.appendChild(listGroup);

    // *** Add note if more than 5 quotes existed ***
    if (totalQuotes > 5) {
        const moreNote = document.createElement('p');
        moreNote.className = 'small text-muted mt-3 mb-0'; // Add margin top
        moreNote.textContent = `Showing Top 5 quotes. ${totalQuotes} total quotes in this category.`;
        categoryModalBody.appendChild(moreNote);
    }
}

/**
 * Submit the RAG query to the backend.
 */
async function submitRagQuery() {
    console.log("[submitRagQuery] Submitting RAG query...");
    if (!ragQueryInput || !ragSubmitBtn || !ragResponseArea || !ragResponseContent || !ragErrorDisplay || !ragSubmitSpinner) {
        console.error("RAG Query UI elements not found. Cannot submit.");
        return;
    }

    const query = ragQueryInput.value.trim();
    if (!query) {
        ragErrorDisplay.textContent = 'Please enter a query.';
        ragErrorDisplay.style.display = 'block';
        return;
    }

    // Date‑range selector has been removed for this page. Always query the full dataset.
    const startDate = '2024-01-01';
    const endDate = new Date().toISOString().slice(0, 10);

    console.log(`[submitRagQuery] Using full date range: ${startDate} to ${endDate}`);

    // Show loading state
    ragSubmitBtn.disabled = true;
    ragSubmitSpinner.style.display = 'inline-block';
    ragResponseArea.style.display = 'none';
    ragResponseContent.innerHTML = ''; // Clear previous response
    ragErrorDisplay.style.display = 'none';

    try {
        const response = await fetch('/api/themes-sentiment/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ 
                query: query,
                start_date: startDate,
                end_date: endDate
            })
        });

        const data = await response.json();

        if (!response.ok || data.error) {
            const errorMsg = data.error || `HTTP error ${response.status}`;
            console.error("Error fetching RAG response:", errorMsg);
            throw new Error(errorMsg);
        }

        // Display the result
        ragResponseArea.style.display = 'block';
        
        // --- NEW: Parse and linkify IDs --- 
        let answerHtml = data.answer;
        if (answerHtml) {
            const idRegex = /\(ID:\s*([^)]+)\)/g;
            answerHtml = answerHtml.replace(idRegex, (match, externalId) => {
                // Basic check to ensure externalId looks reasonable (e.g., not empty)
                if (externalId && externalId.trim()) {
                    // Create a link that calls a JS function (to be implemented in 7b)
                    return `<a href="#" class="text-primary fw-bold text-decoration-none rag-conversation-link" data-conversation-id="${externalId.trim()}" onclick="showTranscriptModal(\'${externalId.trim()}\'); return false;">${match}</a>`;
                } else {
                    // Return the original match if ID is invalid
                    return match; 
                }
            });
            // Convert newlines to <br> for HTML display
            answerHtml = answerHtml.replace(/\n/g, '<br>');
        } else {
            answerHtml = '<p class="text-muted">No answer received.</p>';
        }
        
        ragResponseContent.innerHTML = answerHtml; 
        // --- END NEW --- 

    } catch (error) {
        console.error("Error in submitRagQuery:", error);
        ragErrorDisplay.textContent = `Error: ${error.message || 'Could not process query.'}`;
        ragErrorDisplay.style.display = 'block';
    } finally {
        // Hide loading state
        ragSubmitBtn.disabled = false;
        ragSubmitSpinner.style.display = 'none';
    }
} 