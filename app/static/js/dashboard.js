console.log("DASHBOARD.JS LOADED - V1");

// ==========================================
// Dashboard Specific Logic (Loads on DOMContentLoaded)
// ==========================================
// This script handles fetching statistics for the main dashboard,
// initializing charts, and updating the UI elements (KPIs and charts)
// based on the selected date range.
// Depends on: utils.js (API, Formatter, UI), main.js (initializeGlobalDateRangeSelector)
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    // Check if we are on the dashboard page using a reliable element ID
    // Use an ID present only on the dashboard template (e.g., a main container)
    if (!document.getElementById('dashboard-main-container')) { // Ensure this ID exists in index.html
        console.log("Not on the main dashboard page (dashboard-main-container not found), skipping dashboard script init.");
        return;
    }

    console.log("Initializing dashboard scripts...");

    // --- Chart Instance Variables ---
    // Keep track of Chart.js instances to update them later.
    // conversationsChartInstance removed as it's no longer used.
    let hourlyChartInstance = null;
    let weekdayChartInstance = null;
    let callVolumeChartInstance = null;
    let callDurationChartInstance = null;

    // --- Helper Functions ---

    /**
     * Initializes a single Chart.js instance.
     * @param {string} canvasId - The ID of the canvas element.
     * @param {string} type - The chart type (e.g., 'bar', 'line').
     * @param {object} options - Chart.js options object.
     * @returns {Chart|null} The Chart instance or null if initialization failed.
     */
    function initializeChart(canvasId, type, options = {}) {
        const ctx = document.getElementById(canvasId)?.getContext('2d');
        if (!ctx) {
            console.error(`Canvas context not found for chart ID: ${canvasId}`);
            return null;
        }
        try {
            // Provide default data structure
            const defaultData = {
                labels: [],
                datasets: [{
                    label: 'Dataset', // Default label, can be customized via options
                    data: [],
                    // Add some default styling or let options override
                    backgroundColor: 'rgba(0, 123, 255, 0.5)',
                    borderColor: 'rgba(0, 123, 255, 1)',
                    borderWidth: 1
                }]
            };
            return new Chart(ctx, { type, data: defaultData, options });
        } catch (e) {
            console.error(`Error creating chart for ID ${canvasId}:`, e);
            return null;
        }
    }

    /**
     * Initializes all dashboard charts if their canvas elements exist
     * and an instance hasn't already been created.
     * Called once on DOMContentLoaded.
     */
    function initializeCharts() {
        console.log("Initializing dashboard charts IF NEEDED...");
        try {
            // Get contexts for existing charts
            const ctxHourly = document.getElementById('hourlyActivityChart')?.getContext('2d');
            const ctxWeekday = document.getElementById('weekdayActivityChart')?.getContext('2d');
            // Note: 'callVolumeChart' and 'callDurationChart' canvases are checked inside initializeChart

            // Common chart options
            const chartOptions = {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true } },
                plugins: { legend: { display: false } }
            };

            // Create Hourly Activity chart instance if needed
            if (ctxHourly && !hourlyChartInstance) {
                try {
                    hourlyChartInstance = new Chart(ctxHourly, {
                        type: 'bar',
                        data: { labels: [], datasets: [{ label: 'Messages', data: [], backgroundColor: '#17a2b8' }] }, // Changed label
                        options: chartOptions
                    });
                    console.log("Hourly chart initialized");
                } catch (e) {
                    console.error("Error creating hourly chart:", e);
                    // We don't nullify the instance on error here, as a partial init might
                    // still allow updates later, or prevent re-initialization attempts.
                }
            }

            // Create Weekday Activity chart instance if needed
            if (ctxWeekday && !weekdayChartInstance) {
                try {
                    weekdayChartInstance = new Chart(ctxWeekday, {
                        type: 'bar',
                        data: { labels: [], datasets: [{ label: 'Messages', data: [], backgroundColor: '#ffc107' }] }, // Changed label
                        options: chartOptions
                    });
                    console.log("Weekday chart initialized");
                } catch (e) {
                    console.error("Error creating weekday chart:", e);
                }
            }

            // Initialize Call Volume Trend chart if needed (uses helper)
            if (!callVolumeChartInstance && document.getElementById('callVolumeChart')) {
                callVolumeChartInstance = initializeChart('callVolumeChart', 'line', {
                    scales: {
                        y: { beginAtZero: true, ticks: { precision: 0 }, title: { display: true, text: 'Conversations'} },
                        x: { title: { display: true, text: 'Date'}, ticks: { autoSkip: true, maxTicksLimit: 15 } } // Auto-skip labels for readability
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: { callbacks: { label: (ctx) => `${ctx.raw} conversations` } }
                    },
                    elements: { line: { tension: 0.1 } } // Slight curve to the line
                });
                console.log("Call Volume chart initialized");
            }

            // Initialize Call Duration Chart
            if (!callDurationChartInstance && document.getElementById('callDurationChart')) {
                callDurationChartInstance = initializeChart('callDurationChart', 'line', {
                    scales: {
                        y: { beginAtZero: true, ticks: { precision: 0, callback: (value) => Formatter.duration(value, true) }, title: { display: true, text: 'Avg Duration (mm:ss)' } }, // Format Y-axis as duration
                        x: { title: { display: true, text: 'Date' }, ticks: { autoSkip: true, maxTicksLimit: 15 } }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: { callbacks: { label: (ctx) => `Avg: ${Formatter.duration(ctx.raw)}` } } // Format tooltip
                    },
                    elements: { line: { tension: 0.1, borderColor: '#28a745', backgroundColor: 'rgba(40, 167, 69, 0.1)' } } // Green color
                });
                console.log("Call Duration chart initialized");
            }
        } catch (error) {
            console.error('General error during chart initialization:', error);
        }
    }

    /**
     * Fetches dashboard statistics from the API for the given timeframe.
     * Uses the global API utility from utils.js.
     * @param {string} timeframe - The selected timeframe identifier (e.g., 'last_7_days').
     */
    async function loadDashboardStats(timeframe = 'last_30_days') {
        console.log(`Loading dashboard stats for timeframe: ${timeframe}`);
        const loadingIndicator = document.getElementById('dashboard-loading-indicator');
        if (loadingIndicator) loadingIndicator.style.display = 'block';

        try {
            // Use global utilities
            const { startDate, endDate } = getDatesFromTimeframe(timeframe);
            console.log(`Calculated date range: ${startDate} to ${endDate}`);

            // Construct the API endpoint URL
            const apiUrl = `/api/dashboard/stats?timeframe=${timeframe}&start_date=${startDate}&end_date=${endDate}`;
            console.log(`Fetching from: ${apiUrl}`);

            // Fetch data
            const statsData = await API.fetch(apiUrl);
            console.log("Raw dashboard data received:", statsData);

            // --- Ensure charts are initialized BEFORE updating UI --- 
            initializeCharts(); 

            // Update UI with received data
            updateDashboardUI(statsData);

        } catch (error) {
            console.error("Error fetching or processing dashboard stats:", error);
            UI.showToast(`Error loading dashboard data: ${error.message}`, "danger");
            updateDashboardUI({ error: true }); // Pass error flag to clear/reset UI
        } finally {
            if (loadingIndicator) loadingIndicator.style.display = 'none'; // Hide loading indicator
        }
    }

    /**
     * Updates all dashboard UI elements (KPI cards and charts) with new data.
     * Handles potential errors by displaying 'Error' or default values.
     * @param {object} data - The statistics object received from the API or {error: true} on failure.
     * Expected data structure:
     * {
     *   total_conversations_period: number,
     *   avg_duration_seconds: number,
     *   avg_cost_credits: number,
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
        
        // Helper to safely update text content of an element by ID
        const updateText = (id, value, formatter = null) => {
            const element = document.getElementById(id);
            if (element) {
                let displayValue = '--';
                if (!data.error && value !== null && value !== undefined) {
                    displayValue = formatter ? formatter(value) : value;
                } else if (data.error) {
                     displayValue = 'Error';
                }
                element.textContent = displayValue;
            }
        };

        // Helper to update a Chart.js instance
        const updateChart = (chartInstance, labels, dataSet) => {
            console.log("updateChart called. Instance:", !!chartInstance, "Labels:", labels, "DataSet:", dataSet);
            if (chartInstance) {
                if (!data.error && labels && dataSet) {
                    chartInstance.data.labels = labels;
                    chartInstance.data.datasets[0].data = dataSet;
                } else {
                    chartInstance.data.labels = [];
                    chartInstance.data.datasets[0].data = [];
                }
                chartInstance.update();
            } else {
                // console.warn("Attempted to update a non-existent chart instance.");
            }
        };

        // --- Update KPI Cards ---
        // Use the helper function for cleaner updates
        updateText('total-conversations', data.total_conversations_period);
        updateText('average-duration', data.avg_duration_seconds, Formatter.duration);
        updateText('average-cost', data.avg_cost_credits, Formatter.cost);
        updateText('peak-time', data.peak_time_hour, Formatter.hour);

        // --- Update Charts ---

        // Hourly Activity Chart (Bar)
        // Expects data.activity_by_hour = { '0': count, '1': count, ... '23': count }
        const hourlyLabels = Array.from({ length: 24 }, (_, i) => Formatter.hour(i)); // Labels 00:00 to 23:00
        const hourlyValues = hourlyLabels.map((_, hour) => data.activity_by_hour?.[hour] || 0);
        console.log("Hourly Chart Data:", { labels: hourlyLabels, values: hourlyValues });
        updateChart(hourlyChartInstance, hourlyLabels, hourlyValues);

        // Weekday Activity Chart (Bar)
        // Expects data.activity_by_day = { '0': count, ... '6': count } (Mon=0)
        const weekdayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        const weekdayValues = weekdayLabels.map((_, dayIndex) => data.activity_by_day?.[dayIndex] || 0);
        console.log("Weekday Chart Data:", { labels: weekdayLabels, values: weekdayValues });
        updateChart(weekdayChartInstance, weekdayLabels, weekdayValues);

        // Daily Call Volume Trend Chart (Line)
        // Expects data.daily_volume = { 'YYYY-MM-DD': count, ... }
        // Sort data by date
        const sortedVolume = Object.entries(data.daily_volume || {})
            .sort(([dateA], [dateB]) => new Date(dateA) - new Date(dateB));
        const volumeLabels = sortedVolume.map(([date]) => date);
        const volumeValues = sortedVolume.map(([, count]) => count || 0);
        console.log("Volume Trend Chart Data:", { labels: volumeLabels, values: volumeValues });
        updateChart(callVolumeChartInstance, volumeLabels, volumeValues);

        // Daily Call Duration Trend Chart (Line)
        // Expects data.daily_avg_duration = { 'YYYY-MM-DD': seconds, ... }
        const sortedDuration = Object.entries(data.daily_avg_duration || {})
             .sort(([dateA], [dateB]) => new Date(dateA) - new Date(dateB));
        const durationLabels = sortedDuration.map(([date]) => date);
        // Ensure duration values are numbers (handle potential nulls/undefined)
        const durationValues = sortedDuration.map(([, duration]) => Number(duration || 0)); 
        console.log("Duration Trend Chart Data:", { labels: durationLabels, values: durationValues });
        updateChart(callDurationChartInstance, durationLabels, durationValues);
    }

    // Initialize the global date selector from main.js
    // It handles the button clicks/date changes and calls our loadDashboardStats function.
    if (typeof initializeGlobalDateRangeSelector === 'function') {
        const dateRangeSelector = document.querySelector('#date-range-selector');

        // Simple debounce utility to prevent rapid API calls during date changes.
        let debounceTimeout;
        function debounce(func, delay) {
            return function(...args) {
                clearTimeout(debounceTimeout);
                debounceTimeout = setTimeout(() => {
                    func.apply(this, args);
                }, delay);
            };
        }

        // Create a debounced version of the data loading function.
        const debouncedLoadStats = debounce(loadDashboardStats, 300); // 300ms delay prevents excessive calls

        if (dateRangeSelector) {
            console.log('Initializing global date range selector for dashboard...');
            // Pass the debounced data loading function as the callback.
            initializeGlobalDateRangeSelector(debouncedLoadStats);

            // Trigger initial data load based on the default active button.
            console.log('Triggering initial dashboard data load...');
            const initiallyActiveButton = dateRangeSelector.querySelector('.btn-range.active');
            if (initiallyActiveButton) {
                loadDashboardStats(initiallyActiveButton.value); // Use the value of the active button
            } else {
                loadDashboardStats('last_30_days'); // Default if somehow no button is active
            }
        } else {
            console.error('Dashboard: Date range selector element not found!');
        }
    } else {
        console.error("Dashboard: initializeGlobalDateRangeSelector function not found. Date controls inactive.");
    }
}); 