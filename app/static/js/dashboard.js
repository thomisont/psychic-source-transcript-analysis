console.log("DASHBOARD.JS LOADED - V1");

// ==========================================
// Dashboard Specific Logic (Loads on DOMContentLoaded)
// ==========================================
// This script handles fetching statistics for the main dashboard,
// initializing charts, and updating the UI elements (KPIs and charts)
// based on the selected date range.
// 
// Key Data Source: /api/dashboard/stats endpoint, which calls the 
//                  Supabase RPC function 'get_message_activity_in_range'.
//                  This function uses message timestamps for filtering and aggregation.
// 
// KPIs Added (April 2025):
//  - Completion Rate (calculated in SupabaseConversationService)
// 
// Chart Style Changes (April 2025):
//  - Volume/Duration charts styled to match old Engagement Metrics page (filled, curved line)
//  - Y-axis titles added to bar charts.
// 
// Dependencies: utils.js (API, Formatter, UI, getDatesFromTimeframe), 
//               main.js (initializeGlobalDateRangeSelector)
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
    // Check if we are on the dashboard page using a reliable element ID
    // Use an ID present only on the dashboard template (e.g., a main container)
    if (!document.getElementById('dashboard-main-container')) { // Ensure this ID exists in index.html
        console.log("Not on the main dashboard page (dashboard-main-container not found), skipping dashboard script init.");
        return;
    }

    console.log("Initializing dashboard scripts...");

    // --- State Variables ---
    let currentAgentId = null; // Store the currently selected agent ID

    // --- Chart Instance Variables ---
    let hourlyChartInstance = null;
    let weekdayChartInstance = null;
    let callVolumeChartInstance = null;
    let callDurationChartInstance = null;

    // --- Element References ---
    const agentSelector = document.getElementById('agent-selector');

    // --- Debounce Utility --- 
    // Moved definition here, outside .then()
    let debounceTimeout;
    function debounce(func, delay) {
        return function(...args) {
            clearTimeout(debounceTimeout);
            debounceTimeout = setTimeout(() => {
                func.apply(this, args);
            }, delay);
        };
    }
    // --- End Debounce Utility ---

    // --- Helper Functions ---

    /**
     * Initializes all dashboard charts.
     */
    function initializeCharts() {
        console.log("Initializing dashboard charts...");
        try {
            // Common chart options with updated fonts and colors
            const commonChartOptions = {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        left: 10,
                        right: 10,
                        top: 10,
                        bottom: 10
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: themeColors.textMuted,
                            font: baseFont
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)' // Lighter grid lines
                        }
                    },
                    x: {
                       ticks: {
                            color: themeColors.textMuted,
                            font: baseFont
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false, // Usually false for dashboard charts
                        labels: {
                           font: baseFont,
                           color: themeColors.darkGray
                        }
                    },
                    tooltip: {
                        enabled: true,
                        backgroundColor: themeColors.darkGray,
                        titleFont: { ...titleFont, size: 13 }, 
                        titleColor: themeColors.white,
                        bodyFont: baseFont,
                        bodyColor: themeColors.white,
                        padding: 10,
                        cornerRadius: 4,
                        boxPadding: 4,
                        callbacks: { 
                            // Default callbacks, override per chart if needed
                        }
                    }
                }
            };

            // Create Hourly Activity chart instance if needed
            const ctxHourly = document.getElementById('hourlyActivityChart')?.getContext('2d');
            if (ctxHourly && !hourlyChartInstance) {
                hourlyChartInstance = new Chart(ctxHourly, {
                    type: 'bar',
                    data: { labels: [], datasets: [{ label: 'Messages', data: [], backgroundColor: vizPalette[3] }] }, // Use Light Blue
                    options: {
                        ...commonChartOptions,
                        scales: {
                            ...commonChartOptions.scales,
                            y: {
                                ...commonChartOptions.scales?.y,
                                title: { display: true, text: 'Messages', color: themeColors.darkGray, font: titleFont }
                            }
                        },
                        layout: {
                            padding: {
                                bottom: 20
                            }
                        }
                    }
                });
                console.log("Hourly chart initialized");
            }

            // Create Weekday Activity chart instance if needed
            const ctxWeekday = document.getElementById('weekdayActivityChart')?.getContext('2d');
            if (ctxWeekday && !weekdayChartInstance) {
                weekdayChartInstance = new Chart(ctxWeekday, {
                    type: 'bar',
                    data: { labels: [], datasets: [{ label: 'Messages', data: [], backgroundColor: vizPalette[2] }] }, // Use Purple
                    options: {
                        ...commonChartOptions,
                        scales: {
                            ...commonChartOptions.scales,
                            y: {
                                ...commonChartOptions.scales?.y,
                                title: { display: true, text: 'Messages', color: themeColors.darkGray, font: titleFont }
                            }
                        },
                        layout: {
                            padding: {
                                bottom: 20
                            }
                        }
                    }
                });
                console.log("Weekday chart initialized");
            }

            // Initialize Call Volume Trend chart if needed
            const ctxVolume = document.getElementById('callVolumeChart')?.getContext('2d');
            if (ctxVolume && !callVolumeChartInstance) {
                // Create gradient background - REVERTED to RGBA
                // const volumeGradient = ctxVolume.createLinearGradient(0, 0, 0, 300);
                // volumeGradient.addColorStop(0, colorMix(vizPalette[0], 'white', 90)); 
                // volumeGradient.addColorStop(1, colorMix(vizPalette[0], 'white', 100)); 

                callVolumeChartInstance = new Chart(ctxVolume, {
                    type: 'line',
                    data: {
                        labels: [],
                        datasets: [{
                            label: 'Conversations',
                            data: [],
                            backgroundColor: 'rgba(58, 12, 163, 0.1)', // Light Indigo fill
                            borderColor: vizPalette[0], // Primary line (Indigo)
                            borderWidth: 2,
                            tension: 0.4,
                            fill: true,
                            pointBackgroundColor: vizPalette[0],
                            pointBorderColor: themeColors.white,
                            pointHoverRadius: 6,
                            pointHoverBackgroundColor: vizPalette[0]
                        }]
                    },
                    options: {
                        ...commonChartOptions,
                        scales: {
                            y: {
                                ...commonChartOptions.scales?.y,
                                title: { display: true, text: 'Conversations', color: themeColors.darkGray, font: titleFont },
                                ticks: { precision: 0, color: themeColors.textMuted, font: baseFont },
                            },
                            x: {
                                ...commonChartOptions.scales?.x,
                                title: { display: true, text: 'Date', color: themeColors.darkGray, font: titleFont },
                                ticks: { 
                                    autoSkip: true,
                                    maxRotation: 45,
                                    minRotation: 45,
                                    color: themeColors.textMuted,
                                    font: baseFont
                                }
                            }
                        }
                    }
                });
                console.log("Call Volume chart initialized");
            }

            // Initialize Call Duration Chart if needed
            const ctxDuration = document.getElementById('callDurationChart')?.getContext('2d');
            if (ctxDuration && !callDurationChartInstance) {
                 // Create gradient background - REVERTED to RGBA
                // const durationGradient = ctxDuration.createLinearGradient(0, 0, 0, 300); 
                // durationGradient.addColorStop(0, colorMix(vizPalette[2], 'white', 90)); 
                // durationGradient.addColorStop(1, colorMix(vizPalette[2], 'white', 100)); 

                callDurationChartInstance = new Chart(ctxDuration, {
                    type: 'line',
                    data: {
                        labels: [],
                        datasets: [{
                            label: 'Avg Duration (s)',
                            data: [],
                            backgroundColor: 'rgba(76, 201, 240, 0.1)', // Light Light Blue fill
                            borderColor: vizPalette[4], // Use vizAccent Teal line (previously vizPalette[2])
                            borderWidth: 2,
                            tension: 0.4,
                            fill: true,
                            pointBackgroundColor: vizPalette[4],
                            pointBorderColor: themeColors.white,
                            pointHoverRadius: 6,
                            pointHoverBackgroundColor: vizPalette[4] // Use vizAccent Teal
                        }]
                    },
                    options: {
                        ...commonChartOptions,
                        plugins: {
                            ...commonChartOptions.plugins,
                            tooltip: {
                                ...commonChartOptions.plugins.tooltip,
                                callbacks: {
                                    label: (ctx) => `Avg: ${Formatter.duration(ctx.raw)}`
                                }
                            }
                        },
                        scales: {
                            y: {
                                ...commonChartOptions.scales?.y,
                                title: { display: true, text: 'Avg Duration (mm:ss)', color: themeColors.darkGray, font: titleFont },
                                ticks: { 
                                    precision: 0, 
                                    callback: (value) => Formatter.duration(value, true),
                                    color: themeColors.textMuted,
                                    font: baseFont 
                                },
                            },
                            x: {
                                ...commonChartOptions.scales?.x,
                                title: { display: true, text: 'Date', color: themeColors.darkGray, font: titleFont },
                                ticks: {
                                    autoSkip: true,
                                    maxRotation: 45,
                                    minRotation: 45,
                                    color: themeColors.textMuted,
                                    font: baseFont
                                }
                            }
                        }
                    }
                });
                console.log("Call Duration chart initialized");
            }
        } catch (error) {
            console.error('General error during chart initialization:', error);
        }
    }

    /**
     * Populates the agent selector dropdown with data from the API.
     */
    async function populateAgentSelector() {
        if (!agentSelector) {
            console.error('Agent selector dropdown not found');
            return;
        }

        try {
            const data = await API.fetch('/api/agents');
            if (data && data.agents && data.agents.length > 0) {
                agentSelector.innerHTML = ''; // Clear loading text
                data.agents.forEach(agent => {
                    const option = document.createElement('option');
                    option.value = agent.id;
                    option.textContent = agent.name;
                    agentSelector.appendChild(option);
                });

                // Set the default agent or load from storage
                const storedAgentId = sessionStorage.getItem('selectedAgentId');
                const defaultAgentId = data.default_agent_id;
                currentAgentId = storedAgentId || defaultAgentId;

                if (currentAgentId) {
                    agentSelector.value = currentAgentId;
                } else {
                    // Fallback if no default/stored - select the first agent
                    if (agentSelector.options.length > 0) {
                         agentSelector.selectedIndex = 0;
                         currentAgentId = agentSelector.value;
                         sessionStorage.setItem('selectedAgentId', currentAgentId);
                    }
                }
                console.log(`Agent selector populated. Selected: ${currentAgentId}`);
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
     * Fetches dashboard statistics from the API for the given timeframe and agent ID.
     * Also fetches agent administration data (prompt, emails, widget config).
     * Uses the global API utility from utils.js.
     * @param {string} timeframe - The selected timeframe identifier (e.g., 'last_7_days').
     */
    async function loadDashboardData(timeframe = 'last_30_days') {
        console.log(`Loading ALL dashboard data for timeframe: ${timeframe}, agent: ${currentAgentId}`);
        const loadingIndicator = document.getElementById('dashboard-loading-indicator');
        if (loadingIndicator) loadingIndicator.style.display = 'block';

        if (!currentAgentId) {
            console.warn("No agent selected, cannot load dashboard data.");
            // UI.showToast('Please select an agent.', 'warning'); // Suppress toast on initial load issue
            if (loadingIndicator) loadingIndicator.style.display = 'none';
            // Scroll to top even if we return early due to no agent
            window.scrollTo(0, 0); 
            console.log("Forcing scroll to top after dashboard data load attempt (no agent).");
            return; // Exit early if no agent is selected
        }

        try {
            // --- Fetch Dashboard Stats --- 
            const { startDate, endDate } = getDatesFromTimeframe(timeframe);
            console.log(`Calculated date range: ${startDate} to ${endDate}`);
            const statsApiUrl = `/api/dashboard/stats?timeframe=${timeframe}&start_date=${startDate}&end_date=${endDate}&agent_id=${encodeURIComponent(currentAgentId)}`;
            console.log(`Fetching stats from: ${statsApiUrl}`);
            const statsPromise = API.fetch(statsApiUrl);

            // Admin data is fetched when accordion opens

            // --- Wait only for stats fetch --- 
            const statsData = await statsPromise;
            
            console.log("Stats fetch resolved. Logging data before UI update:");
            console.log("Stats Data:", statsData);

            // --- Update UI --- 
            initializeCharts(); // Ensure charts exist
            updateDashboardUI(statsData); // Update KPIs and Charts
            
        } catch (error) {
            console.error("Error fetching or processing dashboard data:", error);
            UI.showToast(`Error loading dashboard data: ${error.message}`, "danger");
            updateDashboardUI({ error: true }); // Reset stats UI
            
        } finally {
            if (loadingIndicator) loadingIndicator.style.display = 'none';
            // Move scroll to top here, ensuring it runs after async ops attempt completion
            window.scrollTo(0, 0);
            console.log("Forcing scroll to top after dashboard data load attempt.");
        }
    }

    /**
     * Updates all dashboard UI elements (KPI cards and charts) with new data.
     * Handles potential errors by displaying 'Error' or default values.
     * @param {object} data - The statistics object received from the API or {error: true} on failure.
     * Expected data structure (from /api/dashboard/stats):
     * {
     *   total_conversations_period: number,
     *   avg_duration_seconds: number,
     *   avg_cost_credits: number,
     *   completion_rate: number (0.0 to 1.0),
     *   peak_time_hour: number | null,
     *   activity_by_hour: { '0': count, '1': count, ... },
     *   activity_by_day: { '0': count, '1': count, ... }, // Monday=0
     *   daily_volume: { 'YYYY-MM-DD': count, ... },
     *   daily_avg_duration: { 'YYYY-MM-DD': seconds, ... },
     *   error?: boolean // Flag indicating if the data loading failed
     * }
     */
    function updateDashboardUI(data) {
        console.log("Updating dashboard UI with data:", data);
        
        // *** ADD EXPLICIT ERROR HANDLING AT START ***
        const isError = data?.error ? true : false; // Check if the data object itself indicates an error
        if (isError) {
            console.error("updateDashboardUI received error data from API:", data.error);
            // Set all KPIs to 'Error' or '--'
            updateText('total-conversations', 'Error');
            updateText('average-duration', 'Error');
            updateText('average-cost', 'Error');
            updateText('completion-rate', 'Error');
            updateText('peak-time', 'Error');
            updateText('mtd-cost', 'Error');
            updateText('mtd-cost-budget-label', 'Budget: Error');
            // Clear charts or show error message within them
            updateChart(hourlyChartInstance, [], [], 'hourly-chart-container');
            updateChart(weekdayChartInstance, [], [], 'weekday-chart-container');
            updateChart(callVolumeChartInstance, [], [], 'volume-chart-container');
            updateChart(callDurationChartInstance, [], [], 'duration-chart-container');
            // Update progress bar to error state (optional)
            const progressBar = document.getElementById('mtd-cost-progress');
            if (progressBar) {
                 progressBar.style.width = `100%`;
                 progressBar.classList.remove('bg-success', 'bg-warning');
                 progressBar.classList.add('bg-danger');
                 progressBar.textContent = 'Error';
            }
            return; // Stop further processing
        }
        // *** END ERROR HANDLING ***

        // Helper to safely update text content of an element by ID
        const updateText = (id, value, formatter = null) => {
            const element = document.getElementById(id);
            console.log(`updateText called: ID=${id}, Raw Value=${value}, Formatter=${formatter ? formatter.name : 'None'}`);
            if (element) {
                 // *** RESTORE Original Logic ***
                 let displayValue = '--'; // Default placeholder
                 try {
                     if (!isError && value !== null && value !== undefined) {
                         displayValue = formatter ? formatter(value) : value;
                     } else if (isError) {
                          displayValue = 'Error';
                     }
                     console.log(` - Setting textContent for #${id} to: ${displayValue}`); 
                     element.textContent = displayValue;
                 } catch (formatError) {
                     console.error(`Error formatting value for ID ${id}:`, value, formatError);
                     element.textContent = 'FmtErr'; 
                 }
                 // *** END RESTORE Original Logic ***
            } else {
                 console.warn(`updateText: Element with ID '${id}' not found.`);
            }
        };

        // Helper to update Chart.js, now includes empty state handling
        const updateChart = (chartInstance, labels, dataSet, chartContainerId) => {
            console.log("updateChart called. Instance:", !!chartInstance, "Labels:", labels, "DataSet:", dataSet, "Container:", chartContainerId);
            const container = chartContainerId ? document.getElementById(chartContainerId) : null;
            const emptyMessageEl = container ? container.querySelector('.empty-chart-message') : null;

            if (chartInstance) {
                let isEmpty = data.error || !labels || labels.length === 0 || !dataSet || dataSet.length === 0;
                if (dataSet && Array.isArray(dataSet) && dataSet.every(val => val === 0)) {
                    isEmpty = true; // Also consider empty if all values are zero
                }

                if (!isEmpty) {
                    chartInstance.data.labels = labels;
                    chartInstance.data.datasets[0].data = dataSet;
                    if (emptyMessageEl) emptyMessageEl.style.display = 'none';
                    chartInstance.canvas.style.display = 'block';
                } else {
                    chartInstance.data.labels = [];
                    chartInstance.data.datasets[0].data = [];
                    if (emptyMessageEl) emptyMessageEl.style.display = 'block';
                    chartInstance.canvas.style.display = 'none';
                }
                chartInstance.update();
            } else {
                // console.warn("Attempted to update a non-existent chart instance.");
                if (emptyMessageEl) emptyMessageEl.style.display = 'block'; // Show empty message if chart never initialized
            }
        };

        // --- Update KPI Cards ---
        // Use the helper function for cleaner updates
        updateText('total-conversations', data.total_conversations_period);
        updateText('average-duration', data.avg_duration_seconds, Formatter.duration);
        updateText('average-cost', data.avg_cost_credits, Formatter.cost);
        updateText('completion-rate', data.completion_rate, Formatter.percentage);
        updateText('peak-time', data.peak_time_hour, Formatter.hour);

        // --- NEW: Update Month-to-Date Cost KPI & Progress Bar ---
        const mtdCost = data.month_to_date_cost;
        const budget = data.monthly_credit_budget;
        updateText('mtd-cost', mtdCost, Formatter.cost); // Format as cost
        updateText('mtd-cost-budget-label', `Budget: ${Formatter.number(budget)}`); // Format budget nicely
        
        const progressBar = document.getElementById('mtd-cost-progress');
        if (progressBar) {
            let percentage = 0;
            if (budget && budget > 0 && mtdCost !== null && mtdCost >= 0) {
                percentage = Math.min(100, (mtdCost / budget) * 100); // Cap at 100%
            }
            
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage.toFixed(0));
            progressBar.textContent = `${percentage.toFixed(0)}%`; // Optional: Show percentage on bar
            
            // Change progress bar color based on usage
            progressBar.classList.remove('bg-success', 'bg-warning', 'bg-danger');
            if (percentage >= 90) {
                progressBar.classList.add('bg-danger');
            } else if (percentage >= 75) {
                progressBar.classList.add('bg-warning');
            } else {
                progressBar.classList.add('bg-success');
            }
        }
        // --- END NEW MTD COST --- 

        // --- Update Charts with container IDs for empty state---
        // Hourly Activity Chart (Bar)
        const hourlyLabels = Array.from({ length: 24 }, (_, i) => Formatter.hour(i));
        const hourlyValues = hourlyLabels.map((_, hour) => data.activity_by_hour?.[hour] || 0);
        updateChart(hourlyChartInstance, hourlyLabels, hourlyValues, 'hourly-chart-container'); // Pass container ID

        // Weekday Activity Chart (Bar)
        const weekdayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        const weekdayValues = weekdayLabels.map((_, dayIndex) => data.activity_by_day?.[dayIndex] || 0);
        updateChart(weekdayChartInstance, weekdayLabels, weekdayValues, 'weekday-chart-container'); // Pass container ID

        // Daily Call Volume Trend Chart (Line)
        const sortedVolume = Object.entries(data.daily_volume || {})
            .sort(([dateA], [dateB]) => new Date(dateA) - new Date(dateB));
        const volumeLabels = sortedVolume.map(([date]) => date);
        const volumeValues = sortedVolume.map(([, count]) => count || 0);
        updateChart(callVolumeChartInstance, volumeLabels, volumeValues, 'volume-chart-container'); // Pass container ID

        // Daily Call Duration Trend Chart (Line)
        const sortedDuration = Object.entries(data.daily_avg_duration || {})
             .sort(([dateA], [dateB]) => new Date(dateA) - new Date(dateB));
        const durationLabels = sortedDuration.map(([date]) => date);
        // Ensure duration values are numbers (handle potential nulls/undefined)
        const durationValues = sortedDuration.map(([, duration]) => Number(duration || 0)); 
        updateChart(callDurationChartInstance, durationLabels, durationValues, 'duration-chart-container'); // Pass container ID
    }

    /**
     * Updates the Agent Administration Panel UI elements.
     * @param {object} promptData - Data from /api/agents/<id>/prompt
     * @param {object} widgetConfigData - Data from /api/agents/<id>/widget-config (NOW contains embed_code)
     * @param {object} teamEmailData - Data from /api/email-templates/team
     * @param {object} callerEmailData - Data from /api/email-templates/caller
     * @param {boolean} error - Flag indicating if any admin data fetch failed
     */
    function updateAdminPanelUI(promptData = {}, widgetConfigData = {}, teamEmailData = {}, callerEmailData = {}, error = false) {
        // --- Log function entry and args ---
        console.log("Entering updateAdminPanelUI function...");
        console.log("Received promptData:", promptData);
        console.log("Received widgetConfigData:", widgetConfigData);
        console.log("Received teamEmailData:", teamEmailData);
        console.log("Received callerEmailData:", callerEmailData);
        console.log("Received error flag:", error);
        // --- End logging ---

        // *** REVERT: Remove setTimeout wrapper ***
        // setTimeout(() => { 
        console.log("Updating Agent Admin Panel UI... (Directly, no setTimeout)");
        const promptDisplay = document.getElementById('agent-prompt-viewer');
        const teamEmailDisplay = document.getElementById('team-email-viewer');
        const callerEmailDisplay = document.getElementById('caller-email-viewer');
        const widgetEmbedArea = document.getElementById('agent-widget-embed-area');
        const adminErrorDisplay = document.getElementById('admin-panel-error');

        // *** ADD LOGGING FOR ELEMENT FINDING ***
        console.log("Finding elements: ", {
            promptDisplayFound: !!promptDisplay,
            teamEmailDisplayFound: !!teamEmailDisplay,
            callerEmailDisplayFound: !!callerEmailDisplay,
            widgetEmbedAreaFound: !!widgetEmbedArea,
            adminErrorDisplayFound: !!adminErrorDisplay
        });
        // *** END LOGGING ***

        if (adminErrorDisplay) adminErrorDisplay.style.display = 'none';

        if (widgetEmbedArea) {
            widgetEmbedArea.innerHTML = 'Loading widget...';
        }

        if (error) {
            console.error("Error loading agent administration data.");
            if (adminErrorDisplay) {
                adminErrorDisplay.textContent = 'Error loading agent details. Some information may be unavailable.';
                adminErrorDisplay.style.display = 'block';
            }
            if (promptDisplay) promptDisplay.textContent = 'Error loading prompt.';
            if (teamEmailDisplay) teamEmailDisplay.innerHTML = '<p>Error loading template.</p>';
            if (callerEmailDisplay) callerEmailDisplay.innerHTML = '<p>Error loading template.</p>';
            if (widgetEmbedArea) widgetEmbedArea.innerHTML = '<p class="text-danger">Error loading widget.</p>';
            return;
        }

        // Update Prompt Display
        if (promptDisplay) {
            const promptValue = promptData?.prompt || 'Prompt not available.';
            console.log(`Formatting promptDisplay content...`);
            // Format the prompt text
            const lines = promptValue.split('\n');
            const formattedLines = lines.map(line => {
                const trimmedLine = line.trim();
                // Bold lines that are all uppercase (or start with # for future use)
                if ((trimmedLine.length > 0 && trimmedLine === trimmedLine.toUpperCase()) || trimmedLine.startsWith('#')) {
                    return `<strong>${line}</strong>`;
                }
                return line;
            });
            // Set innerHTML with <br> tags
            promptDisplay.innerHTML = formattedLines.join('<br>');
        }

        // Update Widget Embed Area
        if (widgetEmbedArea) {
            if (widgetConfigData?.embed_code) {
                const embedCode = widgetConfigData.embed_code;
                console.log(`Setting widgetEmbedArea.innerHTML to: ${embedCode.substring(0, 100)}...`);
                const convaiTagMatch = embedCode.match(/<elevenlabs-convai.*?><\/elevenlabs-convai>/);
                if (convaiTagMatch && convaiTagMatch[0]) {
                    widgetEmbedArea.innerHTML = convaiTagMatch[0];
                    console.log("Injected <elevenlabs-convai> tag into embed area.");
                } else {
                    console.error('Could not extract <elevenlabs-convai> tag from embed code:', embedCode);
                    widgetEmbedArea.innerHTML = '<p class="text-danger">Error: Invalid widget embed code format.</p>';
                }
            } else {
                widgetEmbedArea.innerHTML = '<p class="text-warning">Widget not available for this agent.</p>';
                console.warn("Embed code not found in widget config data:", widgetConfigData);
            }
        }

        // Update Email Template Displays
        if (teamEmailDisplay) {
            const teamHtml = teamEmailData?.html_content || '<p>Team email template not available.</p>';
            console.log(`Setting teamEmailDisplay.innerHTML to: ${teamHtml.substring(0, 100)}...`);
            teamEmailDisplay.innerHTML = teamHtml;
            // teamEmailDisplay.offsetHeight; // REMOVE repaint force
        }
        if (callerEmailDisplay) {
            const callerHtml = callerEmailData?.html_content || '<p>Caller email template not available.</p>';
            console.log(`Setting callerEmailDisplay.innerHTML to: ${callerHtml.substring(0, 100)}...`);
            callerEmailDisplay.innerHTML = callerHtml;
            // callerEmailDisplay.offsetHeight; // REMOVE repaint force
        }
        // }, 0); // REMOVE setTimeout
    }

    /**
     * Handles the submission of the natural language SQL query.
     */
    async function handleSqlQuerySubmit() {
        const queryInput = document.getElementById('sql-query-input');
        const resultsArea = document.getElementById('sql-query-results');
        const executedSqlArea = document.getElementById('sql-query-executed'); // Get new element
        const submitButton = document.getElementById('submit-sql-query-btn');
        const loadingSpinner = document.getElementById('sql-query-loading');
        const countSpan = document.getElementById('sql-query-count'); // Get count span

        if (!queryInput || !resultsArea || !submitButton || !loadingSpinner || !executedSqlArea || !countSpan) { // Check new element
            console.error('SQL Query UI elements (incl. count span) not found!');
            return;
        }

        const nlQuery = queryInput.value.trim();
        if (!nlQuery) {
            UI.showToast('Please enter a query.', 'warning');
            return;
        }

        // --- Attempt to extract search term from NL query for highlighting --- 
        let searchTerm = null;
        const quoteMatch = nlQuery.match(/['"](.+?)['"]/); // Find text in single or double quotes
        if (quoteMatch && quoteMatch[1]) {
            searchTerm = quoteMatch[1];
            console.log(`Extracted quoted search term for highlighting: ${searchTerm}`);
        } else {
             // Fallback: Try extracting the last word as the search term
             const words = nlQuery.trim().split(/\s+/);
             if (words.length > 0) {
                 // Get last word and remove trailing punctuation (like . or ?)
                 let lastWord = words[words.length - 1].replace(/[.,?]$/, '');
                 // Basic check: avoid highlighting very short words unless it's the only word
                 if (lastWord.length > 2 || words.length === 1) { 
                     searchTerm = lastWord;
                     console.log(`Using fallback: Extracted last word '${searchTerm}' for highlighting.`);
                 } else {
                      console.log("Fallback: Last word is too short, skipping highlighting.");
                 }
             } else {
                 console.log("No quoted term found and no words found for fallback highlighting.");
             }
        }
        // --- End search term extraction ---

        console.log(`Submitting SQL NL Query: ${nlQuery}`);
        submitButton.disabled = true;
        loadingSpinner.style.display = 'inline-block';
        resultsArea.textContent = 'Processing query...'; 
        executedSqlArea.textContent = ''; 
        countSpan.textContent = ''; // Clear count

        try {
            const response = await API.fetch('/api/sql-query', {
                method: 'POST',
                body: JSON.stringify({ query: nlQuery }),
                headers: { 'Content-Type': 'application/json' }
            });

            console.log("SQL Query API response:", response);

            // Display executed query first
            if (response && response.query_executed) {
                 executedSqlArea.textContent = `Query Executed: ${response.query_executed}`;
            } else {
                 executedSqlArea.textContent = 'Query Executed: (Not available)';
            }
            
            resultsArea.textContent = ''; 
            countSpan.textContent = ''; // Clear count again before setting

            if (response && response.results && Array.isArray(response.results)) {
                const resultCount = response.results.length;
                countSpan.textContent = `(${resultCount} record${resultCount !== 1 ? 's' : ''} found)`; // Display count

                if (resultCount === 0) {
                    resultsArea.textContent = "(Query executed successfully, but returned no data)";
                } else {
                    let formattedOutput = '';
                    
                    response.results.forEach(item => {
                        let contextText = '[No Context Available]'; // Default if neither text nor summary found
                        let contextLabel = 'Context';
                        let applyHighlighting = false; // Flag to control highlighting

                        // Prioritize message text if available (usually from message-specific queries)
                        if (item.text !== null && item.text !== undefined) {
                            contextText = item.text;
                            contextLabel = 'Context (Message Text)';
                            applyHighlighting = true; // Only highlight message text
                        } 
                        // Fallback to conversation summary if text is not available
                        else if (item.summary !== null && item.summary !== undefined) {
                            contextText = item.summary;
                            contextLabel = 'Context (Summary)';
                            // Do not apply search term highlighting to summary for now
                        }

                        // Apply highlighting only if it was message text and a term exists
                        if (applyHighlighting && searchTerm) {
                            try {
                                const highlightRegex = new RegExp(searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'); 
                                contextText = contextText.replace(highlightRegex, (match) => `<strong>${match}</strong>`);
                            } catch (e) {
                                 console.error("Error creating or applying highlight regex:", e); 
                            }
                        }

                        // Escape potential HTML in other fields
                        const escapeHtml = (unsafe) => {
                             const safeString = String(unsafe); 
                             return safeString.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
                        }
                        
                        const externalId = escapeHtml(item.external_id || 'N/A');
                        // Determine which ID to show as the secondary ID based on what's available
                        const secondaryIdLabel = item.id ? `(ID: ${escapeHtml(item.id)})` : ''; // Show internal ID if present
                        const msgIdLabel = item.id && contextLabel === 'Context (Message Text)' ? `(Msg ID: ${escapeHtml(item.id)})` : secondaryIdLabel;
                        
                        // Do not escape contextText as it might contain intentional HTML (<strong>)
                        
                        formattedOutput += 
`Conversation ID: ${externalId} ${msgIdLabel}<br>${contextLabel}: ${contextText.replace(/\n/g, '<br>')}<br>--------------------<br>`; 
                    });
                    resultsArea.innerHTML = formattedOutput;
                }
            } else if (response && response.error) {
                resultsArea.textContent = `Error: ${response.error}`;
                countSpan.textContent = '(Error)'; // Indicate error in count
            } else {
                 resultsArea.textContent = 'Received an unexpected response from the server.';
                 countSpan.textContent = '(Error)';
            }
        } catch (error) {
            console.error("Error submitting SQL query:", error);
            resultsArea.textContent = `Error submitting query: ${error.message || 'Unknown error'}. Please try again later.`; 
            countSpan.textContent = '(Error)'; // Indicate error in count
            if (executedSqlArea.textContent === '') { 
                 executedSqlArea.textContent = 'Query Executed: (Error before execution)'; 
            }
        } finally {
            submitButton.disabled = false;
            loadingSpinner.style.display = 'none';
        }
    }

    // --- Initialization and Event Listeners ---

    // Initialize Bootstrap tooltips
    console.log("Initializing Bootstrap tooltips...");
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    console.log("Bootstrap tooltips initialized.");

    // Initialize agent selector first
    populateAgentSelector().then(() => {
        // This block runs AFTER agents are populated and currentAgentId is set
        console.log("Agent selector promise resolved. Initializing date selector and loading initial data...");

        // --- Date Selector Initialization (Only Attach Listeners) --- 
        if (typeof initializeGlobalDateRangeSelector === 'function') {
            const dateRangeSelector = document.querySelector('#date-range-selector');
            const debouncedLoadData = debounce(loadDashboardData, 300); // Debounce subsequent clicks

            if (dateRangeSelector) {
                console.log('DEBUG (dashboard.js): Calling initializeGlobalDateRangeSelector to attach listeners...');
                initializeGlobalDateRangeSelector(debouncedLoadData); // Pass debounced function for clicks
            } else {
                console.error('Dashboard: Date range selector element not found!');
            }
        } else {
            console.error("Dashboard: initializeGlobalDateRangeSelector function not found. Date controls inactive.");
        }
        
        // *** TRIGGER INITIAL LOAD EXPLICITLY HERE ***
        const initiallyActiveButton = document.querySelector('#date-range-selector .date-range-btn.active');
        const initialTimeframe = initiallyActiveButton?.dataset.timeframe || 'last_30_days';
        console.log(`Triggering initial dashboard data load directly with timeframe: ${initialTimeframe} and agent: ${currentAgentId}`);
        // Call loadDashboardData directly for the first load
        loadDashboardData(initialTimeframe); 
        
        // Set the initial active button state AFTER the first load is triggered
        UI.setActiveTimeframeButton(initialTimeframe);
        console.log(`Initial active timeframe button set to: ${initialTimeframe}`);

        // --- Agent Selector Listener --- 
        const agentSelectorElement = document.getElementById('agent-selector');
        if (agentSelectorElement) {
             console.log("Attaching listener to agent selector:", agentSelectorElement);
             agentSelectorElement.addEventListener('change', (event) => {
                console.log("Agent selector CHANGED!"); 
                currentAgentId = event.target.value;
                sessionStorage.setItem('selectedAgentId', currentAgentId);
                console.log(`Agent changed to: ${currentAgentId}`);
                // Reload ALL dashboard data for the new agent
                const activeTimeframeButton = document.querySelector('#date-range-selector .date-range-btn.active');
                const currentTimeframe = activeTimeframeButton ? activeTimeframeButton.dataset.timeframe : 'last_30_days';
                loadDashboardData(currentTimeframe); // Load immediately, no debounce needed on explicit change
            });
            console.log("Agent selector listener attached."); 
        } else {
             console.warn("Agent selector element not found, listener not attached.");
        }
        // --- End Agent Selector Listener ---
        
        // Add event listener for SQL query button
        const sqlSubmitBtn = document.getElementById('submit-sql-query-btn');
        if (sqlSubmitBtn) {
            console.log("Attaching listener to SQL button:", sqlSubmitBtn);
            sqlSubmitBtn.addEventListener('click', handleSqlQuerySubmit);
            console.log("SQL query button listener attached.");
        } else {
             console.error("SQL query submit button not found!");
        }

        // Add listener for Admin Accordion opening
        const adminCollapseElement = document.getElementById('collapseAdmin');
        if (adminCollapseElement) {
            console.log("Attaching 'shown.bs.collapse' listener to #collapseAdmin");
            adminCollapseElement.addEventListener('shown.bs.collapse', async () => {
                console.log("Admin accordion shown, fetching/updating admin panel UI...");
                
                const promptDisplay = document.getElementById('agent-prompt-viewer');
                const teamEmailDisplay = document.getElementById('team-email-viewer');
                const callerEmailDisplay = document.getElementById('caller-email-viewer');
                const widgetEmbedArea = document.getElementById('agent-widget-embed-area');
                if (promptDisplay) promptDisplay.textContent = 'Fetching prompt...';
                if (teamEmailDisplay) teamEmailDisplay.innerHTML = 'Fetching template...';
                if (callerEmailDisplay) callerEmailDisplay.innerHTML = 'Fetching template...'; // Use correct ID
                if (widgetEmbedArea) widgetEmbedArea.innerHTML = 'Loading widget...';
                
                if (!currentAgentId) {
                    console.warn("Cannot update admin panel on show, currentAgentId is not set.");
                    return;
                }
                try {
                    const promptPromise = API.fetch(`/api/agents/${currentAgentId}/prompt`);
                    const widgetConfigPromise = API.fetch(`/api/agents/${currentAgentId}/widget-config`);
                    const teamEmailPromise = API.fetch('/api/email-templates/team');
                    const callerEmailPromise = API.fetch('/api/email-templates/caller');

                    const [promptData, widgetConfigData, teamEmailData, callerEmailData] = await Promise.all([
                        promptPromise,
                        widgetConfigPromise,
                        teamEmailPromise,
                        callerEmailPromise
                    ]);
                    
                    updateAdminPanelUI(promptData, widgetConfigData, teamEmailData, callerEmailData);

                } catch (error) {
                     console.error("Error re-fetching admin data on accordion show:", error);
                     updateAdminPanelUI({}, {}, {}, {}, true);
                }
            });
            console.log("Admin accordion 'shown' listener attached.");
        } else {
            console.warn("#collapseAdmin element not found, cannot attach 'shown' listener.");
        }

    }).catch(err => {
         console.error("Failed to initialize agent selector, dashboard might not load correctly.", err);
         // Scroll to top even if agent selector fails
         window.scrollTo(0, 0);
         console.log("Forcing scroll to top after agent selector failure.");
    });

    // Removed redundant/old initialization calls that were here

});