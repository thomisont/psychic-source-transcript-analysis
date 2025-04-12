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

    // --- Chart Instance Variables ---
    let hourlyChartInstance = null;
    let weekdayChartInstance = null;
    let callVolumeChartInstance = null;
    let callDurationChartInstance = null;

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