console.log("DASHBOARD.JS LOADED - V2 (Tabs Refactor)");

// ==========================================
// Dashboard Specific Logic (Loads on DOMContentLoaded)
// Refactored for Top-Level Tabs (Curious Caller, Member Hospitality)
// ==========================================
// Key Changes:
// - Uses top-level tabs (#dashboardTab) to switch between agent views.
// - KPIs and Charts are duplicated in HTML with prefixes (cc-, mh-).
// - JS functions are parameterized with idPrefix.
// - Chart instances are stored per prefix.
// - Global agent selector is hidden when agent tabs are active.
// ==========================================

// Define Theme Colors (from CSS variables)
const themeColors = {
    primary: getComputedStyle(document.documentElement).getPropertyValue('--primary-color').trim() || '#3A0CA3',
    secondary: getComputedStyle(document.documentElement).getPropertyValue('--secondary-color').trim() || '#C77DFF',
    darkGray: getComputedStyle(document.documentElement).getPropertyValue('--dark-gray').trim() || '#343a40',
    textMuted: getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim() || '#6c757d',
    white: '#ffffff'
};

// Define Data Viz Palette (from CSS variables)
const vizPalette = [
    getComputedStyle(document.documentElement).getPropertyValue('--viz-color-1').trim() || '#3A0CA3', // Indigo
    getComputedStyle(document.documentElement).getPropertyValue('--viz-color-2').trim() || '#C77DFF', // Magenta
    getComputedStyle(document.documentElement).getPropertyValue('--viz-color-3').trim() || '#9D4EDD', // Lighter Purple
    getComputedStyle(document.documentElement).getPropertyValue('--viz-color-4').trim() || '#5E60CE', // Medium Blue
    // Add more colors if needed, matching CSS
    getComputedStyle(document.documentElement).getPropertyValue('--teal').trim() || '#20c997',
    getComputedStyle(document.documentElement).getPropertyValue('--orange').trim() || '#fd7e14'
];

// Define Base Font Options
const baseFont = { family: 'Lato', size: 12, weight: 'normal' };
const titleFont = { family: 'Montserrat', size: 14, weight: 'bold' };

document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('dashboard-main-container')) {
        console.log("Not on the main dashboard page (dashboard-main-container not found), skipping dashboard script init.");
        return;
    }
    window.scrollTo(0, 0);
    console.log("Page scrolled to top on initial load.");
    console.log("Initializing dashboard scripts (Tab Refactor)...");

    // --- State Variables ---
    let activeTabId = 'curious-caller-tab'; // Default active tab
    let activePrefix = 'cc-'; // Default prefix
    let activeAgentId = document.getElementById(activeTabId)?.dataset.agentId || null; // Get initial agent ID
    let currentSelectedTimeframe = 'last_30_days'; // Default timeframe
    let allAgentsData = []; // Store agent list fetched once
    let defaultAgentIdFromConfig = null;

    // --- Chart Instance Variables (Per Prefix) ---
    let chartInstances = {
        'cc-': { hourly: null, weekday: null, volume: null, duration: null },
        'mh-': { hourly: null, weekday: null, volume: null, duration: null }
        // Add keys for other potential prefixes if needed
    };

    // --- Element References ---
    const globalAgentSelectorContainer = document.querySelector('.agent-control'); // The container div
    const dashboardTab = document.getElementById('dashboardTab');

    // --- Debounce Utility ---
    let debounceTimeout;
    function debounce(func, delay) {
        return function(...args) {
            clearTimeout(debounceTimeout);
            debounceTimeout = setTimeout(() => {
                func.apply(this, args);
            }, delay);
        };
    }

    // --- Helper Functions ---

    /**
     * Initializes all dashboard charts for a specific prefix.
     * Creates new chart instances if they don't exist for the prefix.
     * @param {string} prefix - The ID prefix (e.g., 'cc-', 'mh-').
     */
    function initializeCharts(prefix) {
        console.log(`Initializing dashboard charts for prefix: ${prefix}`);
        try {
            if (!prefix || !chartInstances[prefix]) {
                console.error(`Invalid prefix '${prefix}' for chart initialization.`);
                return;
            }

            // Common chart options (same as before)
            const commonChartOptions = {
                responsive: true,
                maintainAspectRatio: false,
                layout: { padding: { left: 10, right: 10, top: 10, bottom: 10 } },
                scales: {
                    y: { beginAtZero: true, ticks: { color: themeColors.textMuted, font: baseFont }, grid: { color: 'rgba(0, 0, 0, 0.05)' } },
                    x: { ticks: { color: themeColors.textMuted, font: baseFont }, grid: { color: 'rgba(0, 0, 0, 0.05)' } }
                },
                plugins: {
                    legend: { display: false, labels: { font: baseFont, color: themeColors.darkGray } },
                    tooltip: {
                        enabled: true, backgroundColor: themeColors.darkGray, titleFont: { ...titleFont, size: 13 },
                        titleColor: themeColors.white, bodyFont: baseFont, bodyColor: themeColors.white,
                        padding: 10, cornerRadius: 4, boxPadding: 4, callbacks: {}
                    }
                }
            };

            // Create Hourly Activity chart if needed for this prefix
            const ctxHourly = document.getElementById(`${prefix}hourlyActivityChart`)?.getContext('2d');
            if (ctxHourly && !chartInstances[prefix].hourly) {
                chartInstances[prefix].hourly = new Chart(ctxHourly, {
                    type: 'bar',
                    data: { labels: [], datasets: [{ label: 'Messages', data: [], backgroundColor: vizPalette[3] }] },
                    options: { ...commonChartOptions, scales: { ...commonChartOptions.scales, y: { ...commonChartOptions.scales?.y, title: { display: true, text: 'Messages', color: themeColors.darkGray, font: titleFont } } }, layout: { padding: { bottom: 20 } } }
                });
                console.log(`Hourly chart initialized for ${prefix}`);
            }

            // Create Weekday Activity chart if needed for this prefix
            const ctxWeekday = document.getElementById(`${prefix}weekdayActivityChart`)?.getContext('2d');
            if (ctxWeekday && !chartInstances[prefix].weekday) {
                chartInstances[prefix].weekday = new Chart(ctxWeekday, {
                    type: 'bar',
                    data: { labels: [], datasets: [{ label: 'Messages', data: [], backgroundColor: vizPalette[2] }] },
                    options: { ...commonChartOptions, scales: { ...commonChartOptions.scales, y: { ...commonChartOptions.scales?.y, title: { display: true, text: 'Messages', color: themeColors.darkGray, font: titleFont } } }, layout: { padding: { bottom: 20 } } }
                });
                console.log(`Weekday chart initialized for ${prefix}`);
            }

            // Initialize Call Volume Trend chart if needed for this prefix
            const ctxVolume = document.getElementById(`${prefix}callVolumeChart`)?.getContext('2d');
            if (ctxVolume && !chartInstances[prefix].volume) {
                chartInstances[prefix].volume = new Chart(ctxVolume, {
                    type: 'line',
                    data: { labels: [], datasets: [{ label: 'Conversations', data: [], backgroundColor: 'rgba(58, 12, 163, 0.1)', borderColor: vizPalette[0], borderWidth: 2, tension: 0.4, fill: true, pointBackgroundColor: vizPalette[0], pointBorderColor: themeColors.white, pointHoverRadius: 6, pointHoverBackgroundColor: vizPalette[0] }] },
                    options: { ...commonChartOptions, scales: { y: { ...commonChartOptions.scales?.y, title: { display: true, text: 'Conversations', color: themeColors.darkGray, font: titleFont }, ticks: { precision: 0, color: themeColors.textMuted, font: baseFont } }, x: { ...commonChartOptions.scales?.x, title: { display: true, text: 'Date', color: themeColors.darkGray, font: titleFont }, ticks: { autoSkip: true, maxRotation: 45, minRotation: 45, color: themeColors.textMuted, font: baseFont } } } }
                });
                console.log(`Call Volume chart initialized for ${prefix}`);
            }

            // Initialize Call Duration Chart if needed for this prefix
            const ctxDuration = document.getElementById(`${prefix}callDurationChart`)?.getContext('2d');
            if (ctxDuration && !chartInstances[prefix].duration) {
                chartInstances[prefix].duration = new Chart(ctxDuration, {
                    type: 'line',
                    data: { labels: [], datasets: [{ label: 'Avg Duration (s)', data: [], backgroundColor: 'rgba(76, 201, 240, 0.1)', borderColor: vizPalette[4], borderWidth: 2, tension: 0.4, fill: true, pointBackgroundColor: vizPalette[4], pointBorderColor: themeColors.white, pointHoverRadius: 6, pointHoverBackgroundColor: vizPalette[4] }] },
                    options: { ...commonChartOptions, plugins: { ...commonChartOptions.plugins, tooltip: { ...commonChartOptions.plugins.tooltip, callbacks: { label: (ctx) => `Avg: ${Formatter.duration(ctx.raw)}` } } }, scales: { y: { ...commonChartOptions.scales?.y, title: { display: true, text: 'Avg Duration (mm:ss)', color: themeColors.darkGray, font: titleFont }, ticks: { precision: 0, callback: (value) => Formatter.duration(value, true), color: themeColors.textMuted, font: baseFont } }, x: { ...commonChartOptions.scales?.x, title: { display: true, text: 'Date', color: themeColors.darkGray, font: titleFont }, ticks: { autoSkip: true, maxRotation: 45, minRotation: 45, color: themeColors.textMuted, font: baseFont } } } }
                });
                console.log(`Call Duration chart initialized for ${prefix}`);
            }
        } catch (error) {
            console.error(`Error during chart initialization for prefix ${prefix}:`, error);
        }
    }

    /**
     * Populates the agent selector dropdown (now likely hidden or secondary).
     * Stores the agent data globally for reference.
     */
    async function populateAgentSelector() {
        // Keep this function for potential future use or if other tabs need the agent list,
        // but the dropdown itself might be hidden.
        const agentSelector = document.getElementById('agent-selector');
        if (!agentSelector) return; // No selector, nothing to do

        try {
            const data = await API.fetch('/api/agents');
            if (data && data.agents && data.agents.length > 0) {
                allAgentsData = data.agents; // Store for later use
                defaultAgentIdFromConfig = data.default_agent_id;

                agentSelector.innerHTML = ''; // Clear loading text
                allAgentsData.forEach(agent => {
                    const option = document.createElement('option');
                    option.value = agent.id;
                    option.textContent = agent.name;
                    agentSelector.appendChild(option);
                });

                // Set initial value if needed, but don't rely on it for tab logic
                if (defaultAgentIdFromConfig) {
                    agentSelector.value = defaultAgentIdFromConfig;
                }
                console.log(`Agent selector populated (may be hidden). Default config ID: ${defaultAgentIdFromConfig}`);
            } else {
                agentSelector.innerHTML = '<option value="">No agents found</option>';
                console.error('No agents returned from API or API error.');
            }
        } catch (error) {
            console.error('Error fetching or populating agents:', error);
            agentSelector.innerHTML = '<option value="">Error loading</option>';
            UI.showToast('Failed to load agent list', 'danger');
        }
    }

    /**
     * Fetches dashboard statistics from the API for the given agent, timeframe, and prefix.
     * @param {string} agentId - The ID of the agent to fetch data for.
     * @param {string} timeframe - The selected timeframe identifier (e.g., 'last_7_days').
     * @param {string} prefix - The ID prefix for the current view (e.g., 'cc-', 'mh-').
     */
    async function loadDashboardData(agentId, timeframe, prefix) {
        console.log(`Loading dashboard data for Agent: ${agentId}, Timeframe: ${timeframe}, Prefix: ${prefix}`);
        const loadingIndicator = document.getElementById('dashboard-loading-indicator'); // Assume one global indicator for now
        if (loadingIndicator) loadingIndicator.style.display = 'block';

        // Ensure charts are initialized for this prefix
        initializeCharts(prefix);

        if (!agentId) {
            console.warn("No agent ID provided, cannot load dashboard data.");
            updateDashboardUI({ error: "No agent selected" }, prefix); // Show error state
            if (loadingIndicator) loadingIndicator.style.display = 'none';
            return;
        }

        try {
            const { startDate, endDate } = getDatesFromTimeframe(timeframe);
            const statsApiUrl = `/api/dashboard/stats?timeframe=${timeframe}&start_date=${startDate}&end_date=${endDate}&agent_id=${encodeURIComponent(agentId)}`;
            console.log(`Fetching stats from: ${statsApiUrl}`);
            const statsData = await API.fetch(statsApiUrl);

            console.log(`Stats fetch resolved for ${prefix}. Data:`, statsData);
            updateDashboardUI(statsData || {}, prefix);

        } catch (error) {
            console.error(`Error fetching dashboard data for ${prefix}:`, error);
            UI.showToast(`Error loading dashboard data for ${prefix}: ${error.message}`, "danger");
            updateDashboardUI({ error: `API fetch failed: ${error.message}` }, prefix); // Reset stats UI with error message
        } finally {
            if (loadingIndicator) loadingIndicator.style.display = 'none';
            console.log(`Finished loading data for ${prefix}`);
        }
    }

    /**
     * Updates all dashboard UI elements (KPI cards and charts) for a specific prefix.
     * Handles potential errors by displaying 'Error' or default values.
     * @param {object} data - The statistics object received from the API or {error: message} on failure.
     * @param {string} prefix - The ID prefix for the elements to update (e.g., 'cc-', 'mh-').
     */
    function updateDashboardUI(data, prefix) {
        console.log(`Updating dashboard UI for prefix: ${prefix} with data:`, data);
        
        const isError = typeof data?.error === 'string' && data.error;
        if (isError) {
            console.error(`updateDashboardUI (${prefix}) received error data:`, data.error);
            // Set all KPIs to 'Error'
            updateText(`${prefix}total-conversations`, 'Error');
            updateText(`${prefix}average-duration`, 'Error');
            updateText(`${prefix}average-cost`, 'Error');
            updateText(`${prefix}completion-rate`, 'Error');
            updateText(`${prefix}peak-time`, 'Error');
            updateText(`${prefix}mtd-cost`, 'Error');
            updateText(`${prefix}mtd-cost-budget-label`, 'Budget: Error');
            // Clear charts
            updateChart(prefix, 'hourly', [], [], 'hourly-chart-container');
            updateChart(prefix, 'weekday', [], [], 'weekday-chart-container');
            updateChart(prefix, 'volume', [], [], 'volume-chart-container');
            updateChart(prefix, 'duration', [], [], 'duration-chart-container');
            // Update progress bar
            const progressBar = document.getElementById(`${prefix}mtd-cost-progress`);
            if (progressBar) {
                 progressBar.style.width = `100%`;
                 progressBar.classList.remove('bg-success', 'bg-warning');
                 progressBar.classList.add('bg-danger');
                 progressBar.textContent = 'Error';
            }
            return;
        }

        // Helper to safely update text content of an element by prefixed ID
        const updateText = (prefixedId, value, formatter = null) => {
            const element = document.getElementById(prefixedId);
            console.log(`updateText called: ID=${prefixedId}, Raw Value=${value}`);
            if (element) {
                 let displayValue = '--'; // Default placeholder
                 try {
                     // Check for null/undefined, 0 is a valid value
                     if (value !== null && value !== undefined) {
                         displayValue = formatter ? formatter(value) : value;
                     } 
                     console.log(` - Setting textContent for #${prefixedId} to: ${displayValue}`); 
                     element.textContent = displayValue;
                 } catch (formatError) {
                     console.error(`Error formatting value for ID ${prefixedId}:`, value, formatError);
                     element.textContent = 'FmtErr'; 
                 }
            } else {
                 console.warn(`updateText: Element with ID '${prefixedId}' not found.`);
            }
        };

        // Helper to update a specific Chart.js instance for the given prefix
        // Now receives prefix and chartKey to identify the correct instance and container
        const updateChart = (prefix, chartKey, labels, dataSet, chartContainerIdSuffix) => {
            const chartInstance = chartInstances[prefix] ? chartInstances[prefix][chartKey] : null;
            const chartContainerId = `${prefix}${chartContainerIdSuffix}`;
            console.log(`updateChart called for ${prefix}${chartKey}. Instance:`, !!chartInstance, "Labels:", labels, "DataSet:", dataSet, "Container:", chartContainerId);
            const container = chartContainerId ? document.getElementById(chartContainerId) : null;
            const emptyMessageEl = container ? container.querySelector('.empty-chart-message') : null;

            if (chartInstance) {
                const hasData = dataSet && dataSet.length > 0 && labels && labels.length > 0;
                if (hasData) {
                    chartInstance.data.labels = labels;
                    chartInstance.data.datasets[0].data = dataSet;
                    chartInstance.update();
                    if (emptyMessageEl) emptyMessageEl.style.display = 'none';
                    if (container) container.style.opacity = '1';
                    console.log(` - Chart ${prefix}${chartKey} updated.`);
                } else {
                    // Clear chart and show empty message
                    chartInstance.data.labels = [];
                    chartInstance.data.datasets[0].data = [];
                    chartInstance.update();
                    if (emptyMessageEl) emptyMessageEl.style.display = 'block';
                    if (container) container.style.opacity = '0.6'; // Fade out slightly
                    console.log(` - Chart ${prefix}${chartKey} cleared (no data).`);
                }
            } else {
                console.warn(`Chart instance ${prefix}${chartKey} not found for update.`);
                 if (emptyMessageEl) emptyMessageEl.textContent = 'Chart initialization failed.';
                 if (emptyMessageEl) emptyMessageEl.style.display = 'block';
                 if (container) container.style.opacity = '0.6';
            }
        };

        // --- Update KPIs --- 
        updateText(`${prefix}total-conversations`, data?.total_conversations_period ?? 0, Formatter.number);
        updateText(`${prefix}average-duration`, data?.avg_duration_seconds ?? 0, Formatter.duration);
        updateText(`${prefix}average-cost`, data?.avg_cost_credits ?? 0, Formatter.number);
        updateText(`${prefix}completion-rate`, data?.completion_rate ?? 0, Formatter.percent);
        updateText(`${prefix}peak-time`, data?.peak_time_hour, Formatter.peakTime);
        updateText(`${prefix}mtd-cost`, data?.month_to_date_cost ?? 0, Formatter.number);
        updateText(`${prefix}mtd-cost-budget-label`, data?.monthly_budget ? `Budget: ${Formatter.number(data.monthly_budget)}` : 'Budget: --');

        // Update MTD Cost Progress Bar
        const progressBar = document.getElementById(`${prefix}mtd-cost-progress`);
        const budget = data?.monthly_budget ?? 0;
        const cost = data?.month_to_date_cost ?? 0;
        if (progressBar && budget > 0) {
            const percentage = Math.min((cost / budget) * 100, 100);
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage);
            progressBar.classList.remove('bg-success', 'bg-warning', 'bg-danger');
            if (percentage >= 90) {
                progressBar.classList.add('bg-danger');
            } else if (percentage >= 75) {
                progressBar.classList.add('bg-warning');
            } else {
                progressBar.classList.add('bg-success');
            }
            progressBar.textContent = ''; // Clear error text if any
        } else if (progressBar) {
             progressBar.style.width = `0%`;
             progressBar.setAttribute('aria-valuenow', 0);
             progressBar.classList.remove('bg-warning', 'bg-danger');
             progressBar.classList.add('bg-success');
             progressBar.textContent = '';
        }

        // --- Update Charts --- 
        
        // Hourly Activity (Bar Chart)
        const hourlyLabels = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, '0') + ':00');
        const hourlyData = hourlyLabels.map((label, index) => data?.activity_by_hour?.[index.toString()] ?? 0);
        updateChart(prefix, 'hourly', hourlyLabels, hourlyData, 'hourly-chart-container');

        // Weekday Activity (Bar Chart)
        const weekdayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        const weekdayData = weekdayLabels.map((_, index) => data?.activity_by_day?.[index.toString()] ?? 0);
        updateChart(prefix, 'weekday', weekdayLabels, weekdayData, 'weekday-chart-container');

        // Call Volume Trend (Line Chart)
        const dailyVolumeData = data?.daily_volume ?? {};
        const volumeLabels = Object.keys(dailyVolumeData).sort(); // Sort dates
        const volumeCounts = volumeLabels.map(date => dailyVolumeData[date]);
        updateChart(prefix, 'volume', volumeLabels, volumeCounts, 'volume-chart-container');

        // Call Duration Trend (Line Chart)
        const dailyDurationData = data?.daily_avg_duration ?? {};
        const durationLabels = Object.keys(dailyDurationData).sort(); // Sort dates
        const durationValues = durationLabels.map(date => dailyDurationData[date]);
        updateChart(prefix, 'duration', durationLabels, durationValues, 'duration-chart-container');

        console.log(`Finished updating UI for ${prefix}`);
    }

    // --- Event Listeners --- 

    // Listener for Top-Level Tabs
    if (dashboardTab) {
        dashboardTab.addEventListener('shown.bs.tab', (event) => {
            const newTabButton = event.target; // Button element of the newly activated tab
            activeTabId = newTabButton.id;
            console.log(`Tab shown: ${activeTabId}`);

            if (activeTabId === 'curious-caller-tab' || activeTabId === 'member-hospitality-tab') {
                activePrefix = (activeTabId === 'curious-caller-tab') ? 'cc-' : 'mh-';
                activeAgentId = newTabButton.dataset.agentId;
                console.log(` - Switched to Agent Tab. Prefix: ${activePrefix}, Agent ID: ${activeAgentId}`);
                if (globalAgentSelectorContainer) globalAgentSelectorContainer.style.display = 'none'; // Hide global selector
                // Load data for the new agent tab
                loadDashboardData(activeAgentId, currentSelectedTimeframe, activePrefix);
            } else {
                 activePrefix = null; // No prefix for non-agent tabs like Success Metrics
                 activeAgentId = null;
                 console.log(` - Switched to Non-Agent Tab: ${activeTabId}`);
                 // Decide whether to show the global selector based on the specific non-agent tab
                 if (activeTabId === 'success-metrics-tab') {
                     if (globalAgentSelectorContainer) globalAgentSelectorContainer.style.display = 'none'; // Hide for Success Metrics too? Or show?
                 } else {
                     if (globalAgentSelectorContainer) globalAgentSelectorContainer.style.display = 'flex'; // Default show for others?
                 }
                 
                 // Handle loading for other tabs if necessary 
                 if (activeTabId === 'success-metrics-tab') {
                      // This logic is now handled by initializeSuccessMetricsHandlers listening on the button
                      console.log('Success Metrics tab activated - its specific handler should trigger rendering.');
                 } else {
                      // Add logic for other future tabs
                 }
            }
        });
    }

    // Listener for Date Range Buttons
    const dateRangeSelector = document.getElementById('date-range-selector');
    if (dateRangeSelector) {
        dateRangeSelector.addEventListener('click', (event) => {
            if (event.target.classList.contains('date-range-btn')) {
                const buttons = dateRangeSelector.querySelectorAll('.date-range-btn');
                buttons.forEach(btn => btn.classList.remove('active'));
                event.target.classList.add('active');
                currentSelectedTimeframe = event.target.dataset.timeframe;
                console.log(`Date range changed to: ${currentSelectedTimeframe}`);
                
                // Reload data ONLY if an agent tab is currently active
                 if (activePrefix && activeAgentId) {
                     loadDashboardData(activeAgentId, currentSelectedTimeframe, activePrefix);
                 } else {
                     console.log("Non-agent tab active, skipping agent data reload on date change.");
                     // Add logic here if date range should affect the active non-agent tab
                     if (activeTabId === 'success-metrics-tab') {
                         // Re-render success metrics if they are date-dependent (they are not currently)
                     }
                 }
            }
        });
    }

    // --- Initialization --- 
    console.log("Starting dashboard initialization...");
    populateAgentSelector(); // Populate selector, it will be hidden/shown by tab logic

    // Initial load for the default active tab (must match HTML)
    const initialTabButton = document.querySelector('#dashboardTab .nav-link.active');
    if (initialTabButton) {
        activeTabId = initialTabButton.id;
        activeAgentId = initialTabButton.dataset.agentId;
        activePrefix = (activeTabId === 'curious-caller-tab') ? 'cc-' : (activeTabId === 'member-hospitality-tab' ? 'mh-' : null);
        currentSelectedTimeframe = document.querySelector('#date-range-selector .date-range-btn.active')?.dataset.timeframe || 'last_30_days';
        
        console.log(`Initial Load - Active Tab: ${activeTabId}, Prefix: ${activePrefix}, Agent: ${activeAgentId}, Timeframe: ${currentSelectedTimeframe}`);

        if (activePrefix && activeAgentId) {
             if (globalAgentSelectorContainer) globalAgentSelectorContainer.style.display = 'none'; // Hide selector initially if agent tab is default
             // Load initial data
             loadDashboardData(activeAgentId, currentSelectedTimeframe, activePrefix);
        } else {
             if (globalAgentSelectorContainer) globalAgentSelectorContainer.style.display = 'flex'; // Show selector if non-agent tab is default
             // Handle initial load for non-agent tabs if needed
             console.log("Initial load is for a non-agent tab.");
             if (activeTabId === 'success-metrics-tab') {
                 // Trigger initial render if needed, although the listener should handle it too
             }
        }
    } else {
        console.error("Could not find initial active tab button.");
        // Fallback or error handling needed?
    }

    // Initialize other features 
    // Ensure these are initialized regardless of the initial tab
    initializeAdminPanelHandlers();
    initializeSqlQueryHandler();
    initializeFutureFeaturesHandlers();
    initializeCompetitiveIntelHandlers(); 
    initializeGlassFrogHandlers();
    initializeSuccessMetricsHandlers(); // Make sure this is called to set up its listener
    
    console.log("Dashboard initialization complete.");

    // --- Drawer Trigger --- 
    const drawer = document.getElementById('voice-drawer');
    const trigger = document.getElementById('voice-drawer-trigger');
    const closeBtn = document.getElementById('voice-drawer-close-btn');
    if (drawer && trigger && closeBtn) {
        trigger.addEventListener('click', () => drawer.classList.add('active'));
        closeBtn.addEventListener('click', () => drawer.classList.remove('active'));
    } else {
        console.warn('Drawer elements not found, trigger inactive.')
    }

});

// ==========================================
// Agent Administration Specific Logic
// ==========================================
// (Keep existing functions initializeAdminPanelHandlers, updateAdminPanelUI)
// ... (existing code for Admin Panel) ...
function initializeAdminPanelHandlers() {
    console.log("Initializing Agent Admin Panel Handlers...");
    // ... (rest of existing function) ...
}

function updateAdminPanelUI(promptData = {}, widgetConfigData = {}, teamEmailData = {}, callerEmailData = {}, error = false) {
    console.log("Updating Admin Panel UI. Error:", error);
    // ... (rest of existing function) ...
}

// ==========================================
// Ask Lilly (SQL Query) Specific Logic
// ==========================================
// (Keep existing functions initializeSqlQueryHandler, handleSqlQuerySubmit)
// ... (existing code for SQL Query) ...
function initializeSqlQueryHandler() {
    console.log("Initializing SQL Query Handler...");
    // ... (rest of existing function) ...
}
// handleSqlQuerySubmit is defined inside initializeSqlQueryHandler

// ==========================================
// Future Features Specific Logic
// ==========================================
// (Keep existing functions initializeFutureFeaturesHandlers, handleLilyReportButton, initHospitalityCallingFeature)
// ... (existing code for Future Features) ...
function initializeFutureFeaturesHandlers() {
    console.log("Initializing Future Features Handlers...");
    // ... (rest of existing function) ...
}
async function handleLilyReportButton() {
    // ... (rest of existing function) ...
}
function initHospitalityCallingFeature() {
    // ... (rest of existing function) ...
}

// ==========================================
// Competitive Intelligence Specific Logic
// ==========================================
// (Keep existing function initializeCompetitiveIntelHandlers)
// ... (existing code for Comp Intel) ...
function initializeCompetitiveIntelHandlers() {
    console.log("Initializing Competitive Intel Handlers...");
    // ... (rest of existing function) ...
}

// ==========================================
// GlassFrog Specific Logic
// ==========================================
// (Keep existing functions initializeGlassFrogHandlers, renderGlassFrog)
// ... (existing code for GlassFrog) ...
function initializeGlassFrogHandlers() {
    console.log("Initializing GlassFrog Handlers...");
    // ... (rest of existing function) ...
}
function renderGlassFrog(data) {
    // ... (rest of existing function) ...
}

// ==========================================
// Success Metrics Specific Logic
// ==========================================
// (Keep existing functions initializeSuccessMetricsHandlers, renderSuccessMetrics)
// Note: initializeSuccessMetricsHandlers now uses the tab button listener
function initializeSuccessMetricsHandlers() {
    console.log("Initializing Success Metrics Handlers (Tab Listener Setup)...");
    const collapseElement = document.getElementById('success-metrics-pane'); 
    // Find the tab button that controls this pane to add listener
    const tabButton = document.querySelector('#dashboardTab [data-bs-target="#success-metrics-pane"]');
    let isDataLoaded = false;

    if (tabButton && collapseElement) {
         // Use the event listener added globally to #dashboardTab
         // We just need to ensure renderSuccessMetrics() gets called appropriately
         // The global listener already handles basic activation logging.
         // If renderSuccessMetrics needs to be called *only* when the tab is shown,
         // we could potentially add a specific check inside the global listener, 
         // or rely on the fact that the DOM elements are only visible when the tab is shown.
         console.log("Success Metrics tab handler setup. Rendering logic tied to tab activation.");
         // Initial render might be needed if it's the default active tab
         if (tabButton.classList.contains('active')) {
             console.log("Success Metrics is initial active tab, rendering now.");
             renderSuccessMetrics();
             isDataLoaded = true;
         } 
         // Add listener to render when tab becomes active later
         tabButton.addEventListener('shown.bs.tab', () => {
             if (!isDataLoaded) {
                 renderSuccessMetrics();
                 isDataLoaded = true;
             }
         }); 

    } else {
         console.warn("Could not find Success Metrics tab button or pane for handler setup.");
    }
}

function renderSuccessMetrics() {
    const container = document.getElementById('success-metrics-container');
    if (!container) {
        console.error("Success metrics container not found!");
        return;
    }

    console.log("Rendering Success Metrics...");
    // ... (rest of existing function to render metrics and add listeners) ...
    const metrics = [
        { id: 'convRate', title: 'Conversation Rate', baseline: '5%', target: '15%', current: localStorage.getItem('sm_convRate_current') || '' },
        { id: 'avgDuration', title: 'Average Duration', baseline: '2m30s', target: '1m45s', current: localStorage.getItem('sm_avgDuration_current') || '' },
        { id: 'custSat', title: 'Customer Satisfaction', baseline: '75%', target: '90%', current: localStorage.getItem('sm_custSat_current') || '' },
        { id: 'taskComplete', title: 'Task Completion Rate', baseline: '60%', target: '85%', current: localStorage.getItem('sm_taskComplete_current') || '' },
        { id: 'costPerConv', title: 'Cost Per Conversation', baseline: '$3.50', target: '$2.00', current: localStorage.getItem('sm_costPerConv_current') || '' },
        { id: 'agentUtil', title: 'Agent Utilization', baseline: 'N/A', target: '70%', current: localStorage.getItem('sm_agentUtil_current') || '' },
    ];

    container.innerHTML = metrics.map(metric => `
        <div class="col-lg-4 col-md-6">
            <div class="card h-100">
                <div class="card-body">
                    <h6 class="card-title">${metric.title}</h6>
                    <div class="mb-2">
                        <span class="badge bg-light text-dark">Baseline: ${metric.baseline}</span>
                        <span class="badge bg-success ms-1">Target: ${metric.target}</span>
                    </div>
                    <div class="input-group input-group-sm">
                        <span class="input-group-text">Current:</span>
                        <input type="text" class="form-control success-metric-input" 
                               id="current-${metric.id}" 
                               data-metric-id="${metric.id}" 
                               placeholder="Enter value..." 
                               value="${metric.current}">
                    </div>
                </div>
            </div>
        </div>
    `).join('');

    // Add event listeners to save input values to localStorage
    container.querySelectorAll('.success-metric-input').forEach(input => {
        input.addEventListener('change', (e) => {
            const metricId = e.target.dataset.metricId;
            const value = e.target.value;
            localStorage.setItem(`sm_${metricId}_current`, value);
            console.log(`Saved metric ${metricId}: ${value}`);
            // Optional: Add visual feedback on save
            e.target.classList.add('is-valid');
            setTimeout(() => e.target.classList.remove('is-valid'), 1500);
        });
    });
}