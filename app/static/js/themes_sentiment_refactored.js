// app/static/js/themes_sentiment_refactored.js

// Ensure utils.js objects are available (assuming API, UI, Formatter are defined there)
if (typeof API === 'undefined' || typeof UI === 'undefined' || typeof Formatter === 'undefined') {
    console.error("Error: Required objects (API, UI, Formatter) from utils.js are not available.");
    // Optionally, display an error to the user or halt execution
}

// Define Theme Colors & Palette (Read from CSS)
const themeColors = {
    primary: getComputedStyle(document.documentElement).getPropertyValue('--primary-color').trim() || '#3A0CA3',
    secondary: getComputedStyle(document.documentElement).getPropertyValue('--secondary-color').trim() || '#C77DFF',
    darkGray: getComputedStyle(document.documentElement).getPropertyValue('--dark-gray').trim() || '#343a40',
    textMuted: getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim() || '#6c757d',
    white: '#ffffff'
};
const vizPalette = [
    getComputedStyle(document.documentElement).getPropertyValue('--viz-color-1').trim() || '#3A0CA3', // Indigo
    getComputedStyle(document.documentElement).getPropertyValue('--viz-color-2').trim() || '#C77DFF', // Magenta
    getComputedStyle(document.documentElement).getPropertyValue('--viz-color-3').trim() || '#9D4EDD', // Lighter Purple
    getComputedStyle(document.documentElement).getPropertyValue('--viz-color-4').trim() || '#5E60CE', // Medium Blue
    '#28a745', // Keep sentiment green
    '#ffc107', // Keep sentiment yellow/orange
    '#dc3545'  // Keep sentiment red
];

// Define Base Font Options
const baseFont = { family: 'Lato', size: 12, weight: 'normal' };
const titleFont = { family: 'Montserrat', size: 13, weight: 'bold' }; // Slightly smaller title for these charts

// Define Common Chart Options
const commonChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
        y: {
            beginAtZero: true,
            ticks: { color: themeColors.textMuted, font: baseFont },
            grid: { color: 'rgba(0, 0, 0, 0.05)' }
        },
        x: {
           ticks: { color: themeColors.textMuted, font: baseFont },
           grid: { color: 'rgba(0, 0, 0, 0.05)' }
        }
    },
    plugins: {
        legend: {
            display: true, // Often needed for these charts
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
            callbacks: { /* Default callbacks */ }
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    console.log("Themes & Sentiment Refactored JS Loaded - Page-specific init");

    // Removed block that forced loading indicator visibility here.
    // loadAnalysisData will handle showing it when it starts.

    // Initialize the global date range selector (from main.js).
    // This handles button clicks after the initial load.
    // It calls our local handleTimeframeChange function when a button is clicked.
    if (typeof initializeGlobalDateRangeSelector === 'function') {
        initializeGlobalDateRangeSelector(handleTimeframeChange);
    } else {
        console.error("initializeGlobalDateRangeSelector function not found. Date range selection will not work.");
        const errorDisplay = document.getElementById('error-display');
        if (errorDisplay) {
            errorDisplay.textContent = 'Error: Date range selector component failed to load.';
            errorDisplay.style.display = 'block';
        }
    }

    // Manually trigger the initial load for the default timeframe (7 days).
    // loadAnalysisData() is responsible for showing the loading indicator.
    console.log("Manually triggering initial load for 7 days.");
    handleTimeframeChange('last_7_days');
});

// Chart instances - declare globally to allow updates/destruction
let sentimentDistributionChart = null;
let topThemesChart = null;
let sentimentTrendsChart = null;

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
        // Display error to user?
        const errorDisplay = document.getElementById('error-display');
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
    // <<< LOGGING: Entry point >>>
    console.log(`[loadAnalysisData] START - Dates: ${startDateISO} to ${endDateISO}`);

    // Ensure dates are valid before proceeding
    if (!startDateISO || !endDateISO) {
        console.error("loadAnalysisData called with invalid dates:", startDateISO, endDateISO);
        // Display an error or prevent API call
        const errorDisplay = document.getElementById('error-display');
        errorDisplay.textContent = 'Invalid date range selected.';
        errorDisplay.style.display = 'block';
        return;
    }

    // Get references to elements
    const loadingIndicator = document.getElementById('loading-indicator');
    const loadingMessageMain = document.getElementById('loading-message-main');
    const loadingMessageDetail = document.getElementById('loading-message-detail');
    const errorDisplay = document.getElementById('error-display');
    const analysisContent = document.getElementById('analysis-content');
    const conversationCountDisplay = document.getElementById('conversation-count-display');
    const analysisModelInfo = document.getElementById('analysis-model-info'); // Get new element

    // Reset UI state: Show loading indicator, hide content & error, set default loading text.
    // The loading indicator includes a spinner, text, and progress bar.
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

    // Destroy previous charts to prevent rendering issues on data refresh
    if (sentimentDistributionChart) sentimentDistributionChart.destroy();
    if (topThemesChart) topThemesChart.destroy();
    if (sentimentTrendsChart) sentimentTrendsChart.destroy();
    sentimentDistributionChart = null;
    topThemesChart = null;
    sentimentTrendsChart = null;

    try {
        const url = `/api/themes-sentiment/full-analysis-v2?start_date=${encodeURIComponent(startDateISO)}&end_date=${encodeURIComponent(endDateISO)}`;
        console.log(`[loadAnalysisData] Calling API.fetch for: ${url}`);
        const data = await API.fetch(url);
        console.log(`[loadAnalysisData] API.fetch returned. Data received:`, data);

        if (data && !data.error) {
            console.log("[loadAnalysisData] Data is valid, calling renderAnalysisData...");
            
            // --- Update loading message with model name FIRST --- 
            // This happens quickly, especially on cache hits, so the user might not see it,
            // but ensures the text is set before rendering potentially hides the indicator.
            const modelName = data.analysis_status?.model_name;
            if (modelName && modelName !== 'N/A' && loadingMessageMain) {
                loadingMessageMain.textContent = `Analysis Underway Using ${modelName}`; 
            }
            if (loadingMessageDetail) loadingMessageDetail.textContent = "Processing results..."; 
            // ----------------------------------------------------

            // Pass elements to the rendering function (which handles hiding the indicator)
            renderAnalysisData(data, loadingIndicator, analysisContent);
            
            console.log("[loadAnalysisData] renderAnalysisData finished (sync part). Spinner/content handled inside.");
            
            // Update conversation count and permanent model info display
            if (conversationCountDisplay) conversationCountDisplay.textContent = `Conversations in period: ${data.metadata?.total_conversations_in_range ?? 'N/A'}`;
            console.log("[loadAnalysisData] Attempting to update model info.", { element: analysisModelInfo, name: modelName }); 
            if (analysisModelInfo) {
                 analysisModelInfo.textContent = modelName && modelName !== 'N/A' ? `Analysis by: ${modelName}` : '';
            }
        } else {
            // Handle errors returned in the data object itself (e.g., {error: ...})
            let errorMsg = data?.error || 'Received empty or invalid data from server.';
            let errorDetails = data?.details || "";
            if (data?.timeout) { // Check for specific timeout flag
                errorMsg = `Analysis timed out. ${errorMsg}`;
            }
            // <<< LOGGING: Error in data object >>>
            console.error(`[loadAnalysisData] Error received in data object: ${errorMsg}`, errorDetails);
            throw new Error(errorMsg, { cause: errorDetails });
        }

    } catch (error) {
        // <<< LOGGING: Catch block entered >>>
        console.error("[loadAnalysisData] Catch block entered.");
        console.error("Error loading analysis data:", error);
        // Use API.fetch's built-in error handling if it includes UI updates,
        // otherwise, update UI manually here.
        const errorMessage = error.message || "An unknown error occurred.";
        const errorDetails = error.cause || ""; // Get details if passed via cause

        // Manual UI update for error display
        if (errorDisplay) {
            errorDisplay.textContent = `Failed to load analysis data: ${errorMessage}`;
            if(errorDetails) {
                const detailsSpan = document.createElement('span');
                detailsSpan.className = 'small d-block mt-1';
                detailsSpan.textContent = `Details: ${errorDetails}`;
                errorDisplay.appendChild(detailsSpan);
            }
             errorDisplay.style.display = 'block';
        }
        // Ensure spinner fades out on error
        if (loadingIndicator) {
            loadingIndicator.style.opacity = '0';
            loadingIndicator.style.pointerEvents = 'none';
        }
        if (analysisContent) analysisContent.style.display = 'none'; // Ensure content stays hidden on error
    }
    // <<< LOGGING: End of function >>>
    console.log("[loadAnalysisData] END");
}

/**
 * Main function to populate the UI with the fetched analysis data.
 * Fades out spinner and fades in content upon successful completion.
 * @param {object} data - The analysis data object received from the API.
 * @param {HTMLElement} loadingIndicator - The loading indicator element.
 * @param {HTMLElement} analysisContent - The main content container element.
 */
function renderAnalysisData(data, loadingIndicator, analysisContent) {
    console.log("[renderAnalysisData] START - Received data:", JSON.stringify(data, null, 2));
    const errorDisplay = document.getElementById('error-display');
    if (!data) {
        console.error("[renderAnalysisData] Cannot render: Data object is null or undefined.");
        if (loadingIndicator) {
            loadingIndicator.style.opacity = '0';
            loadingIndicator.style.pointerEvents = 'none';
        }
        return;
    }
    if (errorDisplay) errorDisplay.style.display = 'none';

    try {
        console.log("[renderAnalysisData] Calling renderSentimentOverview...");
        renderSentimentOverview(data.sentiment_overview);
        console.log("[renderAnalysisData] Calling renderTopThemes...");
        renderTopThemes(data.top_themes);
        console.log("[renderAnalysisData] Calling renderSentimentTrends...");
        renderSentimentTrends(data.sentiment_trends);
        console.log("[renderAnalysisData] Calling renderThemeCorrelation...");
        renderThemeCorrelation(data.theme_sentiment_correlation);
        console.log("[renderAnalysisData] Calling renderCategorizedQuotes...");
        renderCategorizedQuotes(data.categorized_quotes);
        console.log("[renderAnalysisData] Calling renderAnalysisStatus...");
        renderAnalysisStatus(data.analysis_status);
        console.log("[renderAnalysisData] All render functions called successfully.");

        // --- Display content and start fade transition ---
        // Set content to display:block first to make it part of the layout.
        // Then use requestAnimationFrame to trigger the opacity change on the next paint cycle,
        // ensuring the CSS transition for fade-in works reliably.
        console.log("[renderAnalysisData] Starting simultaneous fade transition.");
        if (analysisContent) {
            analysisContent.style.display = 'block'; 
            requestAnimationFrame(() => { 
                 analysisContent.style.opacity = '1'; 
            });
        }
        // Start fading out the loading indicator simultaneously.
        if (loadingIndicator) {
            loadingIndicator.style.opacity = '0'; 
            // Disable pointer events after the fade-out completes (duration matches CSS).
            setTimeout(() => { 
                if (loadingIndicator) loadingIndicator.style.pointerEvents = 'none';
            }, 500); 
        }

    } catch (renderError) {
        console.error("[renderAnalysisData] Error during rendering:", renderError);
        if (errorDisplay) {
            errorDisplay.textContent = `An error occurred while displaying the analysis results: ${renderError.message}`;
            errorDisplay.style.display = 'block';
        }
        // Ensure spinner fades out on error
        if (loadingIndicator) {
            loadingIndicator.style.opacity = '0';
            loadingIndicator.style.pointerEvents = 'none';
        }
        if (analysisContent) analysisContent.style.display = 'none'; // Ensure hidden on error
    }
}

// --- Rendering Functions using new styles ---

/**
 * Helper to update charts and handle empty states
 */
function updateChartAndHandleEmpty(chartInstance, config, containerId) {
    console.log(`Updating chart ${containerId}. Has instance: ${!!chartInstance}`);
    const container = document.getElementById(containerId);
    const canvas = container?.querySelector('canvas');
    const emptyMessageEl = container?.querySelector('.empty-chart-message');

    if (!canvas) {
        console.error(`Canvas not found within container ${containerId}`);
        if(emptyMessageEl) emptyMessageEl.style.display = 'block';
        return null;
    }

    // Check if data is essentially empty
    let isEmpty = !config || !config.data || !config.data.labels || config.data.labels.length === 0 ||
                  !config.data.datasets || config.data.datasets.length === 0 ||
                  config.data.datasets.every(ds => !ds.data || ds.data.length === 0 || ds.data.every(val => val === 0));

    if (chartInstance) {
        // Destroy existing chart before creating new one if config type changed or empty
        console.log(`Destroying existing chart for ${containerId}`);
        chartInstance.destroy();
        chartInstance = null;
    }

    if (!isEmpty) {
        console.log(`Rendering chart for ${containerId}`);
        if (emptyMessageEl) emptyMessageEl.style.display = 'none';
        canvas.style.display = 'block';
        try {
            chartInstance = new Chart(canvas.getContext('2d'), config);
        } catch(e) {
             console.error(`Error creating chart for ${containerId}:`, e);
             if (emptyMessageEl) {
                 emptyMessageEl.textContent = "Error rendering chart.";
                 emptyMessageEl.style.display = 'block';
             }
             canvas.style.display = 'none';
        }
    } else {
        console.log(`Showing empty state for ${containerId}`);
        if (emptyMessageEl) emptyMessageEl.style.display = 'block';
        canvas.style.display = 'none';
    }
    return chartInstance; // Return the new or null instance
}

function renderSentimentOverview(sentimentData) {
    console.log("  [renderSentimentOverview] START - Data:", sentimentData);
    const containerId = 'sentiment-distribution-chart-container'; // Assuming a container div exists
    const hasData = sentimentData && sentimentData.sentiment_distribution;

    document.getElementById('overall-sentiment-label').textContent = sentimentData?.overall_sentiment_label || 'N/A';
    document.getElementById('caller-average-sentiment').textContent = Formatter.sentimentScore(sentimentData?.caller_average_sentiment);
    document.getElementById('agent-average-sentiment').textContent = Formatter.sentimentScore(sentimentData?.agent_average_sentiment);

    const distribution = sentimentData?.sentiment_distribution || {};
    const chartConfig = {
        type: 'doughnut',
        data: {
            labels: ['Very Positive', 'Positive', 'Neutral', 'Negative', 'Very Negative'],
            datasets: [{
                label: 'Sentiment Distribution',
                data: [
                    distribution.very_positive || 0,
                    distribution.positive || 0,
                    distribution.neutral || 0,
                    distribution.negative || 0,
                    distribution.very_negative || 0
                ],
                // Use sentiment colors from vizPalette
                backgroundColor: [
                    vizPalette[4], // Green
                    '#a0d911', // Lighter Green (adjust if needed)
                    '#d9d9d9', // Neutral Grey
                    vizPalette[5], // Yellow/Orange
                    vizPalette[6]  // Red
                ],
                borderColor: themeColors.white, // Add white border for separation
                borderWidth: 2,
                hoverOffset: 4
            }]
        },
        options: {
            ...commonChartOptions,
            plugins: {
                ...commonChartOptions.plugins,
                legend: { ...commonChartOptions.plugins.legend, position: 'right' }, // Override position
                tooltip: {
                    ...commonChartOptions.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            let label = context.label || '';
                            if (label) label += ': ';
                            label += context.parsed ?? 'N/A';
                            return label;
                        }
                    }
                }
            }
        }
    };

    sentimentDistributionChart = updateChartAndHandleEmpty(sentimentDistributionChart, chartConfig, containerId);
    console.log("  [renderSentimentOverview] END");
}

function renderTopThemes(themeData) {
    console.log("  [renderTopThemes] START - Data:", themeData);
    const containerId = 'top-themes-chart-container'; // Assuming a container div exists
    const listElement = document.getElementById('top-themes-list');
    listElement.innerHTML = ''; // Clear previous list
    const hasData = themeData && themeData.themes && themeData.themes.length > 0;

    if (!hasData) {
        console.warn("No theme data to render.");
        listElement.innerHTML = '<li class="list-group-item text-muted">No themes identified.</li>';
    } else {
        // Populate List
        themeData.themes.forEach(item => {
            const li = document.createElement('li');
            li.className = 'list-group-item d-flex justify-content-between align-items-center py-1';
            li.textContent = item.theme;
            const badge = document.createElement('span');
            // Use primary color badge for theme count
            badge.className = 'badge text-bg-light border border-primary text-primary rounded-pill'; 
            badge.textContent = item.count;
            li.appendChild(badge);
            listElement.appendChild(li);
        });
    }

    // Prepare Chart Data
    const chartLabels = hasData ? themeData.themes.map(item => item.theme) : [];
    const chartCounts = hasData ? themeData.themes.map(item => item.count) : [];

    const chartConfig = {
        type: 'bar',
        data: {
            labels: chartLabels,
            datasets: [{
                label: 'Mentions',
                data: chartCounts,
                backgroundColor: vizPalette[2], // Use Lighter Purple from palette
                borderColor: colorMix(vizPalette[2], 'black', 0.1), // Slightly darker border
                borderWidth: 1
            }]
        },
        options: {
            ...commonChartOptions,
            indexAxis: 'y', // Horizontal bar chart
            scales: {
                x: { ...commonChartOptions.scales.x, beginAtZero: true, grid: { display: false }, title: { display: false } },
                y: { ...commonChartOptions.scales.y, grid: { display: false }, ticks: { font: { size: 10 } } } // Smaller font if needed
            },
            plugins: {
                 ...commonChartOptions.plugins,
                 legend: { display: false }, // No legend needed for single dataset
                 tooltip: { ...commonChartOptions.plugins.tooltip }
             }
        }
    };

    topThemesChart = updateChartAndHandleEmpty(topThemesChart, chartConfig, containerId);
    console.log("  [renderTopThemes] END");
}


function renderSentimentTrends(trendData) {
    console.log("  [renderSentimentTrends] START - Data:", trendData);
    const containerId = 'sentiment-trends-chart-container';
    const hasData = trendData && trendData.labels && trendData.labels.length > 0;

     const chartConfig = {
         type: 'line',
         data: {
             labels: hasData ? trendData.labels : [],
             datasets: [{
                 label: 'Average Sentiment',
                 data: hasData ? trendData.average_sentiment_scores : [],
                 borderColor: vizPalette[3], // Medium Blue line
                 backgroundColor: colorMix(vizPalette[3], 'white', 80), // Very light blue fill
                 fill: true,
                 tension: 0.3, // Smoother curve
                 pointRadius: 3,
                 pointBackgroundColor: vizPalette[3]
             }]
         },
         options: {
            ...commonChartOptions,
             scales: {
                 x: {
                    ...commonChartOptions.scales.x,
                     type: 'time',
                     time: {
                         unit: 'day',
                          tooltipFormat: 'DD MMM YYYY', 
                          displayFormats: { day: 'MMM DD' }
                     },
                     title: { display: false } 
                 },
                 y: {
                    ...commonChartOptions.scales.y,
                     beginAtZero: false,
                     title: { display: false },
                     suggestedMin: -1,
                     suggestedMax: 1,
                     ticks: { precision: 1 } // Show one decimal place for sentiment score
                 }
             },
             plugins: {
                 ...commonChartOptions.plugins,
                 legend: { display: false },
                 tooltip: {
                    ...commonChartOptions.plugins.tooltip,
                     mode: 'index',
                     intersect: false,
                     callbacks: {
                         label: function(context) {
                             return `Avg Sentiment: ${context.parsed.y.toFixed(2)}`;
                         }
                     }
                 }
             }
         }
     };

    sentimentTrendsChart = updateChartAndHandleEmpty(sentimentTrendsChart, chartConfig, containerId);
    console.log("  [renderSentimentTrends] END");
}

function renderThemeCorrelation(correlationData) {
    console.log("  [renderThemeCorrelation] START - Data:", correlationData);
    const tableBody = document.getElementById('theme-correlation-table');
    tableBody.innerHTML = ''; // Clear previous data

    if (!correlationData || correlationData.length === 0) {
        console.warn("No theme correlation data to render.");
        tableBody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">No correlation data available.</td></tr>';
        return;
    }

    correlationData.forEach(item => {
        const row = tableBody.insertRow();
        row.innerHTML = `
            <td>${item.theme || 'N/A'}</td>
            <td>${item.mentions || 0}</td>
            <td><span class="badge ${getSentimentBadgeClass(item.sentiment_label)}">${item.sentiment_label || 'N/A'}</span></td>
        `;
    });
    console.log("  [renderThemeCorrelation] END");
}

function renderCategorizedQuotes(quoteData) {
    console.log("  [renderCategorizedQuotes] START - Data:", quoteData);
    if (!quoteData) {
        console.warn("No categorized quote data to render.");
        // Clear accordions and list
        document.getElementById('common-questions-accordion').innerHTML = '<div class="text-center p-3 text-muted">No questions found.</div>';
        document.getElementById('concerns-skepticism-accordion').innerHTML = '<div class="text-center p-3 text-muted">No concerns found.</div>';
        document.getElementById('positive-interactions-list').innerHTML = '<li class="list-group-item text-center text-muted">No positive interactions found.</li>';
        document.getElementById('positive-interactions-count').textContent = '0';
        return;
    }

    // Render Common Questions Accordion
    renderAccordion('common-questions-accordion', quoteData.common_questions || [], 'questions');

    // Render Concerns & Skepticism Accordion
    renderAccordion('concerns-skepticism-accordion', quoteData.concerns_skepticism || [], 'concerns');

    // Render Positive Interactions List
    renderPositiveInteractions(quoteData.positive_interactions || { count: 0, quotes: [] });
    console.log("  [renderCategorizedQuotes] END");
}

function renderAnalysisStatus(statusData) {
    console.log("  [renderAnalysisStatus] START - Data:", statusData);
    // Optional: Display the analysis mode/status somewhere if needed
    if (statusData) {
        console.info(`Analysis Status: Mode=${statusData.mode}, Message=${statusData.message}`);
        // Example: Update a small text element
        // const statusEl = document.getElementById('analysis-status-text');
        // if (statusEl) statusEl.textContent = `(${statusData.mode}: ${statusData.message})`;
    }
    console.log("  [renderAnalysisStatus] END");
}


// --- Helper Functions ---

/**
 * Dynamically renders a Bootstrap accordion section.
 * @param {string} accordionId ID of the accordion container element.
 * @param {Array} categories Array of category objects.
 * @param {string} typePrefix Prefix for generating unique IDs (e.g., 'questions', 'concerns').
 */
function renderAccordion(accordionId, categories, typePrefix) {
    const accordionElement = document.getElementById(accordionId);
    accordionElement.innerHTML = ''; // Clear previous content

    if (!categories || categories.length === 0) {
        accordionElement.innerHTML = `<div class="text-center p-3 text-muted">No ${typePrefix} found in this period.</div>`;
        return;
    }

    categories.forEach((category, index) => {
        const categoryId = `${typePrefix}-category-${index}`;
        const collapseId = `${typePrefix}-collapse-${index}`;

        const accordionItem = document.createElement('div');
        accordionItem.className = 'accordion-item';
        accordionItem.innerHTML = `
            <h2 class="accordion-header" id="${categoryId}-heading">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#${collapseId}" aria-expanded="false" aria-controls="${collapseId}">
                    ${category.category_name || 'Unnamed Category'}
                    <span class="badge bg-secondary rounded-pill ms-2">${category.count || 0}</span>
                </button>
            </h2>
            <div id="${collapseId}" class="accordion-collapse collapse" aria-labelledby="${categoryId}-heading" data-bs-parent="#${accordionId}">
                <div class="accordion-body">
                    <ul class="list-group list-group-flush">
                        ${renderQuoteListItems(category.quotes || [])}
                    </ul>
                </div>
            </div>
        `;
        accordionElement.appendChild(accordionItem);
    });
}

/**
 * Renders list items for quotes within an accordion body.
 * @param {Array} quotes Array of quote objects ({quote_text, conversation_id}).
 * @returns {string} HTML string for the list items.
 */
function renderQuoteListItems(quotes) {
    if (!quotes || quotes.length === 0) {
        return '<li class="list-group-item text-muted small">No specific examples found.</li>';
    }
    return quotes.map(quote => `
        <li class="list-group-item small">
             &ldquo;${Formatter.truncateText(quote.quote_text, 150)}&rdquo;
             <a href="/transcript/${quote.conversation_id || '#'}" target="_blank" class="text-muted small d-block" title="View full transcript">
                 (ID: ${quote.conversation_id || 'N/A'})
             </a>
        </li>
    `).join('');
     // TODO: Ensure /transcript/{id} route exists and works, or adjust link
}

/**
 * Renders the list of positive interactions.
 * @param {object} interactionData Object containing count and quotes array.
 */
function renderPositiveInteractions(interactionData) {
    const listElement = document.getElementById('positive-interactions-list');
    const countElement = document.getElementById('positive-interactions-count');
    listElement.innerHTML = ''; // Clear previous

    const count = interactionData.count || 0;
    const quotes = interactionData.quotes || [];

    countElement.textContent = count;

    if (quotes.length === 0) {
        listElement.innerHTML = '<li class="list-group-item text-center text-muted">No specific positive interactions found.</li>';
        return;
    }

    quotes.forEach(quote => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-start';
        li.innerHTML = `
            <div class="ms-2 me-auto">
                <div class="fw-bold">Caller said:</div>
                &ldquo;${Formatter.truncateText(quote.quote_text, 200)}&rdquo;
                <a href="/transcript/${quote.conversation_id || '#'}" target="_blank" class="text-muted small d-block" title="View full transcript">
                     (ID: ${quote.conversation_id || 'N/A'})
                 </a>
            </div>
            <span class="badge bg-success rounded-pill">${Formatter.sentimentScore(quote.sentiment_score)}</span>
        `;
         // TODO: Ensure /transcript/{id} route exists and works, or adjust link
        listElement.appendChild(li);
    });
}


/**
 * Helper function to get the appropriate Bootstrap badge class based on sentiment label.
 * @param {string} sentimentLabel - The sentiment label (e.g., "Positive", "Slightly Negative").
 * @returns {string} Bootstrap background class (e.g., "bg-success", "bg-warning").
 */
function getSentimentBadgeClass(sentimentLabel) {
    const labelLower = (sentimentLabel || '').toLowerCase();
    if (labelLower.includes('very positive') || labelLower.includes('positive')) return 'bg-success';
    if (labelLower.includes('slightly positive')) return 'bg-info';
    if (labelLower.includes('neutral')) return 'bg-secondary';
    if (labelLower.includes('slightly negative')) return 'bg-warning';
    if (labelLower.includes('very negative') || labelLower.includes('negative')) return 'bg-danger';
    return 'bg-light text-dark'; // Default/Unknown
}

// Add sentimentScore and truncateText to Formatter if they don't exist
if (typeof Formatter !== 'undefined') {
    if (typeof Formatter.sentimentScore !== 'function') {
        Formatter.sentimentScore = (score) => {
            if (score === null || score === undefined || isNaN(score)) return 'N/A';
            return score.toFixed(2);
        };
         console.log("Added Formatter.sentimentScore helper.");
    }
    if (typeof Formatter.truncateText !== 'function') {
         Formatter.truncateText = (text, maxLength = 100) => {
             if (!text) return '';
             if (text.length <= maxLength) return text;
             return text.substring(0, maxLength) + '...';
         };
         console.log("Added Formatter.truncateText helper.");
     }
}

// Utility function to mix colors (basic version) - REMOVED DUE TO ERRORS
/*
function colorMix(color1, color2, weight) {
    // Basic implementation for hex colors - more robust library might be needed
    // This is a placeholder and might not parse all CSS colors accurately
    try {
        const d2h = (d) => d.toString(16);
        const h2d = (h) => parseInt(h, 16);
        weight = typeof(weight) !== 'undefined' ? weight : 50;
        var color = "#";
        for (var i = 0; i <= 5; i += 2) {
            var v1 = h2d(color1.substr(i + 1, 2));
            var v2 = h2d(color2.substr(i + 1, 2));
            var val = d2h(Math.floor(v2 + (v1 - v2) * (weight / 100.0)));
            while(val.length < 2) { val = '0' + val; } 
            color += val;
        }
        return color;
    } catch (e) {
        console.warn("colorMix failed, returning color1:", e);
        return color1; // Fallback
    }
}
*/ 