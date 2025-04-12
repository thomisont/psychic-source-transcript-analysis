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

// --- Element References (Declare at Module Scope) ---
let loadingIndicator = null;
let errorDisplay = null;
let analysisContent = null;
let conversationCountDisplay = null;
let analysisModelInfo = null;
let loadingMessageMain = null;
let loadingMessageDetail = null;

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

    // Initialize the global date range selector (from main.js).
    if (typeof initializeGlobalDateRangeSelector === 'function') {
        initializeGlobalDateRangeSelector(handleTimeframeChange);
    } else {
        console.error("initializeGlobalDateRangeSelector function not found. Date range selection will not work.");
        if (errorDisplay) {
            errorDisplay.textContent = 'Error: Date range selector component failed to load.';
            errorDisplay.style.display = 'block';
        }
    }

    // Manually trigger the initial load for the default timeframe (7 days).
    // loadAnalysisData() is responsible for showing the loading indicator.
    console.log("Manually triggering initial load for 7 days.");
    handleTimeframeChange('last_7_days');

    // Setup event listeners (including the new delegated listener)
    setupEventListeners();
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

    // Reset UI state
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

    try {
        const url = `/api/themes-sentiment/full-analysis-v2?start_date=${encodeURIComponent(startDateISO)}&end_date=${encodeURIComponent(endDateISO)}`;
        console.log(`[loadAnalysisData] Calling API.fetch for: ${url}`);
        const data = await API.fetch(url);
        console.log("%%% RAW API DATA RECEIVED: %%%", JSON.stringify(data, null, 2));

        if (data && !data.error) {
            console.log("[loadAnalysisData] Data is valid, calling renderAnalysisData...");

            const modelName = data.analysis_status?.model_name;
            if (modelName && modelName !== 'N/A' && loadingMessageMain) {
                loadingMessageMain.textContent = `Analysis Underway Using ${modelName}`;
            }
            if (loadingMessageDetail) loadingMessageDetail.textContent = "Processing results...";

            renderAnalysisData(data);

            console.log("[loadAnalysisData] renderAnalysisData finished (sync part).");

            // Update permanent info displays
            if (conversationCountDisplay) {
                conversationCountDisplay.textContent = `Conversations in period: ${data.metadata?.total_conversations_in_range ?? 'N/A'}`;
            }
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
    // *** Log at start of function ***
    console.log("[renderAnalysisData] Start. Checking errorDisplay:", errorDisplay);

    console.log("Rendering analysis data components...", data);
    try {
        const sentimentData = data.sentiment_overview;
        const categorizedData = data.categorized_quotes;
        const metadata = data.metadata;
        const analysisStatus = data.analysis_status;

        // --- Update Info Displays First ---
        // *** ADD CHECKS ***
        if (conversationCountDisplay) {
            conversationCountDisplay.textContent = `Conversations in period: ${metadata?.total_conversations_in_range || 'N/A'}`;
        } else {
            console.warn("Element 'conversation-count-display' not found in renderAnalysisData.");
        }
        // *** ADD CHECK ***
        if (analysisModelInfo) {
            analysisModelInfo.textContent = `Analysis by: ${analysisStatus?.model_name || 'Unknown'}`;
        } else {
             console.warn("Element 'analysis-model-info' not found in renderAnalysisData.");
        }
        // --- End Info Displays ---

        clearPlaceholders(); // Hides loading/error, Shows analysisContent block

        // --- Render Components ---
        renderSentimentOverview(sentimentData);
        renderTopThemes(data.top_themes);
        renderSentimentTrends(data.sentiment_trends);
        renderThemeCorrelation(data.theme_sentiment_correlation);
        renderCollapsibleCategories(categorizedData?.common_questions, 'common-questions');
        renderCollapsibleCategories(categorizedData?.concerns_skepticism, 'concerns-skepticism');

        // *** ADD SPECIFIC LOG HERE ***
        console.log("%%% DEBUG: Data for Positive Interactions: %%%", JSON.stringify(categorizedData?.positive_interactions, null, 2));

        renderPositiveInteractions(categorizedData?.positive_interactions);
        // --- End Render Components ---

        // --- Handle Smooth Transition ---
        // *** ADD CHECKS ***
        if (analysisContent) {
            analysisContent.style.display = 'block';
            requestAnimationFrame(() => {
                 if (analysisContent) analysisContent.style.opacity = '1';
            });
        }
        // *** ADD CHECK ***
        if (loadingIndicator) {
            loadingIndicator.style.opacity = '0';
            setTimeout(() => {
                 if (loadingIndicator) loadingIndicator.style.display = 'none';
            }, 300);
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
                    borderColor: vizPalette[3], // Medium Blue 
                    backgroundColor: hexToRgba(vizPalette[3], 0.1), 
                    borderWidth: 2,
                    pointBackgroundColor: vizPalette[3],
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    tension: 0.3, 
                    fill: true 
                }
                // Removed agent/caller specific datasets as data not present
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
 * Renders collapsible categories (Common Questions, Concerns/Skepticism) using Bootstrap Accordion.
 * @param {Array<object>} categories - Array of category objects, each with `category_name`, `count`, and `quotes`.
 * @param {string} type - Identifier string ('common-questions' or 'concerns-skepticism').
 */
function renderCollapsibleCategories(categories, type) {
    const accordionContainerId = `${type}-accordion`;
    const accordionContainer = document.getElementById(accordionContainerId);

    if (!accordionContainer) {
        console.error(`Accordion container not found: #${accordionContainerId}`);
        return;
    }

    accordionContainer.innerHTML = ''; // Clear previous content

    if (!categories || categories.length === 0) {
        accordionContainer.innerHTML = `<div class="text-center text-muted p-3">No ${type.replace('-', ' ')} identified for this period.</div>`;
        return;
    }

    console.log(`Rendering ${type}:`, categories);

    categories.forEach((category, index) => {
        const categoryId = `${type}-category-${index}`;
        const collapseId = `${type}-collapse-${index}`;

        const accordionItem = document.createElement('div');
        accordionItem.className = 'accordion-item';

        const header = document.createElement('h2');
        header.className = 'accordion-header';
        header.id = `${categoryId}-header`;

        const button = document.createElement('button');
        button.className = 'accordion-button collapsed'; // Start collapsed
        button.type = 'button';
        button.dataset.bsToggle = 'collapse';
        button.dataset.bsTarget = `#${collapseId}`;
        button.setAttribute('aria-expanded', 'false');
        button.setAttribute('aria-controls', collapseId);

        const categoryName = document.createElement('span');
        categoryName.textContent = category.category_name || 'Unnamed Category';
        categoryName.className = 'me-auto'; // Push badge to the right

        const badge = document.createElement('span');
        badge.className = 'badge bg-secondary rounded-pill ms-2'; // Added margin-start
        badge.textContent = category.count || 0;

        button.appendChild(categoryName);
        button.appendChild(badge);
        header.appendChild(button);

        const collapse = document.createElement('div');
        collapse.id = collapseId;
        collapse.className = 'accordion-collapse collapse';
        collapse.setAttribute('aria-labelledby', header.id);
        collapse.dataset.bsParent = `#${accordionContainerId}`;

        const body = document.createElement('div');
        body.className = 'accordion-body';

        const listGroup = document.createElement('ul');
        listGroup.className = 'list-group list-group-flush'; // Flush removes borders

        if (category.quotes && category.quotes.length > 0) {
            category.quotes.forEach(quoteData => {
                const listItem = document.createElement('li');
                // REMOVE OLD: d-flex justify-content-between align-items-start
                listItem.className = 'list-group-item py-2 px-0'; // Simpler class, adjust padding if needed

                const quoteTextContainer = document.createElement('div');
                // No extra classes needed now, text/link handles content
                // REMOVE OLD: quoteTextContainer.className = 'me-3 flex-grow-1';

                if (quoteData.conversation_id && String(quoteData.conversation_id).toLowerCase() !== 'null') {
                    // Create a link if ID exists and is not null/undefined
                    const link = document.createElement('a');
                    link.href = '#'; // Prevent page jump, handled by JS
                    link.className = 'text-decoration-none text-dark transcript-link'; // Add class, style as needed
                    link.dataset.conversationId = quoteData.conversation_id;
                    link.innerHTML = `<i class="bi bi-quote me-1"></i>${quoteData.quote_text || "Empty Quote"}`; // Add quote icon for visual cue
                    quoteTextContainer.appendChild(link);
                } else {
                    // Just display text if no ID
                    quoteTextContainer.innerHTML = `<i class="bi bi-quote me-1 text-muted"></i><span class="text-muted">${quoteData.quote_text || "Empty Quote"}</span>`;
                    // Optionally add a class to indicate it's not clickable - Already done with text-muted span
                }

                // Append the text container (which now contains either text or a link)
                listItem.appendChild(quoteTextContainer);

                // Remove the old external link icon logic
                /*
                const linkContainer = document.createElement('div');
                linkContainer.className = 'flex-shrink-0'; // Prevent link from wrapping

                if (quoteData.conversation_id) {
                    const link = document.createElement('a');
                    link.href = '#'; // Placeholder, will be handled by JS
                    link.className = 'btn btn-sm btn-outline-primary transcript-link-icon'; // Example class
                     link.dataset.conversationId = quoteData.conversation_id;
                    link.innerHTML = '<i class="bi bi-box-arrow-up-right"></i>'; // Link icon
                    link.setAttribute('title', 'View Transcript');
                    linkContainer.appendChild(link);
                } else {
                     // Optionally show a disabled state or nothing
                }
                listItem.appendChild(linkContainer); // Append link icon container
                */

                // Sentiment Badge (if applicable) - Keep this if needed
                if (quoteData.sentiment_label) {
                    const sentimentBadge = document.createElement('span');
                    sentimentBadge.className = `badge rounded-pill ms-2 ${getSentimentClassFromLabel(quoteData.sentiment_label)}`;
                    sentimentBadge.textContent = quoteData.sentiment_label;
                    // Append badge next to the text container or where appropriate
                    quoteTextContainer.appendChild(sentimentBadge); // Append inside the main text container
                }

                listGroup.appendChild(listItem);
            });
        } else {
            const noQuotesItem = document.createElement('li');
            noQuotesItem.className = 'list-group-item text-muted px-0';
            noQuotesItem.textContent = 'No specific examples found.';
            listGroup.appendChild(noQuotesItem);
        }

        body.appendChild(listGroup);
        collapse.appendChild(body);
        accordionItem.appendChild(header);
        accordionItem.appendChild(collapse);
        accordionContainer.appendChild(accordionItem);
    });
}

/**
 * Renders the list of most positive interactions.
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
    countSpan.textContent = interactionData?.count || 0;

    // *** CORRECTED KEY: Use interactionData?.quotes ***
    const interactions = interactionData?.quotes;

    if (!interactions || interactions.length === 0) {
        listContainer.innerHTML = '<li class="list-group-item text-muted text-center">No particularly positive interactions identified.</li>';
        return;
    }

    // This log should now run correctly
    console.log("Rendering Positive Interactions (using .quotes key):", interactions);

    interactions.forEach(interaction => {
        const listItem = document.createElement('li');
        // Use flexbox for layout: text on left, badge on right
        listItem.className = 'list-group-item d-flex justify-content-between align-items-center py-2';

        const textElement = document.createElement('span');
        textElement.className = 'interaction-quote me-3'; // Add margin to separate from badge

        // Use interaction.quote_text and interaction.conversation_id (already correct)
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
        sentimentBadge.className = `badge rounded-pill ${getSentimentClassFromLabel(interaction.sentiment_label)} text-nowrap`;
        sentimentBadge.textContent = interaction.sentiment_label || 'Positive'; 

        listItem.appendChild(textElement); 
        listItem.appendChild(sentimentBadge); 
        listContainer.appendChild(listItem);
    });
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
 * Placeholder function to simulate opening the transcript modal.
 * @param {string} conversationId - The ID of the conversation to view.
 */
function showTranscriptModal(conversationId) {
    console.log(`Placeholder: Would open transcript modal for conversation ID: ${conversationId}`);
    // In a real implementation, this would:
    // 1. Fetch transcript data using the conversationId.
    // 2. Populate the modal's content area.
    // 3. Show the Bootstrap modal (e.g., using new bootstrap.Modal(...).show()).
    alert(`Placeholder: Show transcript for ID ${conversationId}`); // Simple alert for now
}

/**
 * Sets up event listeners after the DOM is ready.
 * Specifically, adds a delegated listener for transcript links.
 * Also adds listeners for Bootstrap accordion events to fix scrolling.
 */
function setupEventListeners() {
    const contentArea = document.getElementById('analysis-content');
    if (contentArea) {
        // Delegated listener for transcript links
        contentArea.addEventListener('click', (event) => {
            const linkElement = event.target.closest('.transcript-link');
            if (linkElement) {
                event.preventDefault(); 
                const conversationId = linkElement.dataset.conversationId;
                if (conversationId && conversationId !== 'null') {
                    showTranscriptModal(conversationId);
                } else {
                    console.warn("Clicked transcript link but conversation ID is missing or null.");
                }
            }
        });
         console.log("Delegated event listener for transcript links added to #analysis-content.");
    } else {
        console.error("Could not find #analysis-content to attach transcript link listener.");
    }

    // Accordion Scroll Fix Listener
    const commonQuestionsAccordion = document.getElementById('common-questions-accordion');
    const concernsSkepticismAccordion = document.getElementById('concerns-skepticism-accordion');

    const applyScrollStyles = (event) => {
        // event.target is the .accordion-collapse element that was shown
        console.log('shown.bs.collapse event fired for:', event.target.id);
        const collapseElement = event.target;
        if (collapseElement && collapseElement.classList.contains('accordion-collapse')) {
            // Find the .list-group INSIDE the .accordion-body within the shown collapse element
            const listGroupElement = collapseElement.querySelector('.accordion-body .list-group');
            if (listGroupElement) {
                console.log('Applying scroll styles to .list-group within:', collapseElement.id);
                listGroupElement.style.maxHeight = '300px'; // Apply max-height to list-group
                listGroupElement.style.overflowY = 'auto'; // Apply overflow to list-group
            } else {
                console.warn('Could not find .list-group inside .accordion-body within:', collapseElement.id);
            }
        }
    };

    if (commonQuestionsAccordion) {
        commonQuestionsAccordion.addEventListener('shown.bs.collapse', applyScrollStyles);
        console.log("Added shown.bs.collapse listener to #common-questions-accordion");
    }
    if (concernsSkepticismAccordion) {
        concernsSkepticismAccordion.addEventListener('shown.bs.collapse', applyScrollStyles);
        console.log("Added shown.bs.collapse listener to #concerns-skepticism-accordion");
    }
} 