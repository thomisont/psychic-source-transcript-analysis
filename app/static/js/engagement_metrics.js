console.log("ENGAGEMENT_METRICS.JS LOADED - V1");

// Ensure Chart.js and utils.js are loaded before this script

document.addEventListener('DOMContentLoaded', function() {
    
    // Check if we are on the correct page
    if (!document.getElementById('volumeChart')) { // Use a chart ID as identifier
        // console.log("Not on Engagement Metrics page, skipping init.");
        return;
    }
    console.log("Initializing Engagement Metrics page scripts...");

    // Global chart instances scoped to this module
    const visualizationCharts = {
        volumeChart: null,
        durationChart: null,
        timeOfDayChart: null,
        dayOfWeekChart: null,
        completionChart: null
    };

    // --- Utility Functions (Scoped) ---
    const logDebug = (message, ...args) => {
        console.debug(`[EngagementMetrics] ${message}`, ...args);
    };

    const updateDateRangeIndicator = (timeframe, startDate, endDate) => {
        const indicator = document.getElementById('current-date-range');
        const aggregationNote = document.getElementById('aggregation-note');
        if (!indicator) return;

        let text = 'Invalid Range';
        let showAggregationNote = false;
        
        switch(timeframe) {
            case 'last_7_days': text = 'Last 7 Days'; showAggregationNote = true; break;
            case 'last_30_days': text = 'Last 30 Days'; showAggregationNote = true; break;
            case 'last_90_days': text = 'Last 90 Days'; showAggregationNote = true; break;
            case 'all_time': text = 'All Time (Since Jan 1, 2024)'; showAggregationNote = true; break;
            case 'custom': 
                if (startDate && endDate) {
                    try {
                         // Format dates nicely
                         const start = new Date(startDate + 'T00:00:00Z').toLocaleDateString();
                         const end = new Date(endDate + 'T00:00:00Z').toLocaleDateString();
                         text = `Custom: ${start} - ${end}`;
                         showAggregationNote = true;
                    } catch (e) { text = `Custom: ${startDate} - ${endDate}`; }
                } else {
                    text = 'Custom Range (Not Set)';
                }
                break;
            default: text = `Unknown Timeframe: ${timeframe}`; break;
        }
        indicator.textContent = text;
        if (aggregationNote) {
            aggregationNote.style.display = showAggregationNote ? 'inline' : 'none';
        }
    };

    // --- Data Fetching and Processing ---
    async function loadVisualizationData(timeframe = 'last_30_days', startDate = null, endDate = null) {
        logDebug(`Loading visualization data for timeframe: ${timeframe}`, {startDate, endDate});
        const loadingOverlay = document.getElementById('loading-overlay');
        const contentArea = document.getElementById('visualization-content');

        // Show loading state
        if (loadingOverlay) loadingOverlay.classList.remove('d-none');
        if (contentArea) contentArea.classList.add('opacity-50');
        
        // Determine API URL
        let apiUrl = '/api/visualizations';
        const params = new URLSearchParams();
        if (timeframe === 'custom' && startDate && endDate) {
            params.append('start_date', startDate);
            params.append('end_date', endDate);
        } else {
            params.append('timeframe', timeframe);
        }
        apiUrl += `?${params.toString()}`;
        logDebug(`Fetching URL: ${apiUrl}`);

        try {
            // Use global API utility
            const data = await API.fetch(apiUrl);
            logDebug("Visualization API response received:", data);

            if (data && data.success && data.data) {
                updateCharts(data.data);
                // Update total calls count for the selected period
                const totalCallsElement = document.getElementById('total-calls-count');
                if (totalCallsElement) {
                    totalCallsElement.textContent = data.total_conversations_period !== undefined ? data.total_conversations_period : 'N/A';
                }
                 // Update the date range indicator text
                 updateDateRangeIndicator(timeframe, startDate || data.start_date, endDate || data.end_date);

            } else {
                throw new Error(data?.message || "Invalid data format received from visualization API.");
            }
        } catch (error) {
            console.error("Error loading visualization data:", error);
            // Use global UI utility
            UI.showToast(`Error loading visualizations: ${error.message}`, 'danger');
            // Optionally clear charts or show error messages in charts
             updateCharts({ error: true }); // Pass error flag to clear charts
        } finally {
            // Hide loading state
            if (loadingOverlay) loadingOverlay.classList.add('d-none');
            if (contentArea) contentArea.classList.remove('opacity-50');
        }
    }

    async function fetchTotalConversations() {
        logDebug("Fetching total conversations count...");
        const totalCountElement = document.getElementById('total-conversations-count');
        const refreshButton = document.getElementById('refresh-total');
        if (!totalCountElement) return;

        totalCountElement.textContent = '...'; // Indicate loading
        if (refreshButton) refreshButton.disabled = true;

        try {
            // Assuming /api/status returns total_conversations
            const data = await API.fetch('/api/status'); 
            if (data && data.total_conversations !== undefined) {
                totalCountElement.textContent = data.total_conversations;
            } else {
                totalCountElement.textContent = 'N/A';
                throw new Error("Total conversation count not found in status API response.");
            }
        } catch (error) {
             console.error("Error fetching total conversations count:", error);
             totalCountElement.textContent = 'Error';
             // UI.showToast is handled by API.fetch
        } finally {
             if (refreshButton) refreshButton.disabled = false;
        }
    }

    // --- Chart Update Functions ---
    function updateCharts(data) {
        logDebug("Updating all charts with data:", data);
        
        // Clear existing charts safely
        Object.keys(visualizationCharts).forEach(key => {
            if (visualizationCharts[key]) {
                 try { visualizationCharts[key].destroy(); } catch(e) { console.warn(`Error destroying chart ${key}:`, e); }
                 visualizationCharts[key] = null;
            }
        });

        if (data.error) {
            console.warn("Error flag received, charts will remain empty.");
            // Optionally display error messages in chart containers
            return; 
        }
        
        // Call individual update functions
        if (data.volume_trend) updateVolumeChart(data.volume_trend);
        if (data.duration_trend) updateDurationChart(data.duration_trend);
        if (data.time_of_day) updateTimeOfDayChart(data.time_of_day);
        if (data.day_of_week) updateDayOfWeekChart(data.day_of_week);
        if (data.completion_rate_trend) updateCompletionChart(data.completion_rate_trend);
    }

    function updateVolumeChart(volumeData) {
        const ctx = document.getElementById('volumeChart')?.getContext('2d');
        if (!ctx || !volumeData || !volumeData.labels || !volumeData.data) {
             logDebug("Volume chart context or data missing, skipping update.");
             return;
        }
        logDebug(`Creating volume chart with ${volumeData.labels.length} labels.`);
        const dateRange = volumeData.labels.length;

        visualizationCharts.volumeChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: volumeData.labels,
                datasets: [{
                    label: 'Conversations',
                    data: volumeData.data,
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: {
                         ticks: {
                             maxRotation: 45,
                             minRotation: 45,
                             autoSkip: dateRange > 10 // Skip labels if too many
                         }
                     },
                    y: { beginAtZero: true, ticks: { precision: 0 } }
                }
            }
        });
    }

    function updateDurationChart(durationData) {
        const ctx = document.getElementById('durationChart')?.getContext('2d');
         if (!ctx || !durationData || !durationData.labels || !durationData.data) {
             logDebug("Duration chart context or data missing, skipping update.");
             return;
         }
        logDebug(`Creating duration chart with ${durationData.labels.length} labels.`);
        const dateRange = durationData.labels.length;

        visualizationCharts.durationChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: durationData.labels,
                datasets: [{
                    label: 'Avg Duration (s)',
                    data: durationData.data,
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                // Use global Formatter
                                return `Avg: ${Formatter.duration(context.raw)}`; 
                            }
                        }
                    }
                },
                scales: {
                    x: {
                         ticks: {
                             maxRotation: 45,
                             minRotation: 45,
                             autoSkip: dateRange > 10
                         }
                     },
                    y: { 
                        beginAtZero: true, 
                        ticks: { 
                            precision: 0, 
                            callback: function(value) { return Formatter.duration(value); } // Format Y axis
                        }
                    }
                }
            }
        });
    }

     function updateTimeOfDayChart(timeData) {
        const ctx = document.getElementById('timeOfDayChart')?.getContext('2d');
         if (!ctx || !timeData || !timeData.labels || !timeData.data) {
             logDebug("Time of day chart context or data missing, skipping update.");
             return;
         }
        logDebug(`Creating time of day chart with ${timeData.labels.length} labels.`);
        
        visualizationCharts.timeOfDayChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: timeData.labels.map(h => `${String(h).padStart(2, '0')}:00`), // Format hour labels
                datasets: [{
                    label: 'Conversations',
                    data: timeData.data,
                    backgroundColor: 'rgba(255, 206, 86, 0.6)',
                    borderColor: 'rgba(255, 206, 86, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'x', // Keep hours on X axis
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } }
                }
            }
        });
    }

    function updateDayOfWeekChart(dayData) {
        const ctx = document.getElementById('dayOfWeekChart')?.getContext('2d');
         if (!ctx || !dayData || !dayData.labels || !dayData.data) {
             logDebug("Day of week chart context or data missing, skipping update.");
             return;
         }
        logDebug(`Creating day of week chart with ${dayData.labels.length} labels.`);
        
        visualizationCharts.dayOfWeekChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dayData.labels, // Expect Mon, Tue, etc.
                datasets: [{
                    label: 'Conversations',
                    data: dayData.data,
                    backgroundColor: 'rgba(153, 102, 255, 0.6)',
                    borderColor: 'rgba(153, 102, 255, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'x', // Keep days on X axis
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } }
                }
            }
        });
    }

    function updateCompletionChart(completionData) {
        const ctx = document.getElementById('completionChart')?.getContext('2d');
        if (!ctx || !completionData || !completionData.labels || !completionData.data) {
            logDebug("Completion chart context or data missing, skipping update.");
            return;
        }
        logDebug(`Creating completion chart with ${completionData.labels.length} labels.`);
        
        const dataValues = completionData.data.map(d => {
             const num = Number(d);
             return isNaN(num) ? 0 : num; 
        });
        const dateRange = completionData.labels.length;

        visualizationCharts.completionChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: completionData.labels,
                datasets: [{
                    label: 'Completion Rate (%)',
                    data: dataValues,
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Rate: ${context.raw.toFixed(1)}%`;
                            },
                             title: function(tooltipItems) {
                                try {
                                    const date = new Date(tooltipItems[0].label + 'T00:00:00Z'); 
                                    return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
                                } catch (e) {
                                    return tooltipItems[0].label; 
                                }
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45,
                            autoSkip: dateRange > 10
                        }
                    },
                    y: {
                        min: 0,
                        suggestedMax: 100, 
                        ticks: {
                            callback: function(value) { return value + '%'; }
                        }
                    }
                }
            }
        });
    }

    // --- Event Listeners --- 
    
    // Timeframe buttons
    document.querySelectorAll('.timeframe-selector').forEach(button => {
        button.addEventListener('click', function() {
            document.querySelectorAll('.timeframe-selector').forEach(btn => {
                btn.classList.remove('btn-warning', 'active');
                btn.classList.add('btn-outline-light');
            });
            this.classList.remove('btn-outline-light');
            this.classList.add('btn-warning', 'active');
            
            const timeframe = this.dataset.timeframe;
            logDebug(`Timeframe button clicked: ${timeframe}`);
            loadVisualizationData(timeframe);
        });
    });

    // Custom Range Modal Apply Button
    const applyCustomRangeButton = document.getElementById('apply-custom-range');
    const customStartDateInput = document.getElementById('custom-start-date');
    const customEndDateInput = document.getElementById('custom-end-date');
    const filterModalElement = document.getElementById('filterModal');

    if (applyCustomRangeButton && customStartDateInput && customEndDateInput && filterModalElement) {
        applyCustomRangeButton.addEventListener('click', function() {
            const startDate = customStartDateInput.value;
            const endDate = customEndDateInput.value;
            logDebug(`Custom range applied: ${startDate} - ${endDate}`);
            if (startDate && endDate) {
                // Deactivate preset timeframe buttons
                document.querySelectorAll('.timeframe-selector').forEach(btn => {
                     btn.classList.remove('btn-warning', 'active');
                     btn.classList.add('btn-outline-light');
                 });
                 // Load data with custom dates
                loadVisualizationData('custom', startDate, endDate);
                // Close modal
                const modal = bootstrap.Modal.getInstance(filterModalElement);
                if (modal) modal.hide();
            } else {
                UI.showToast("Please select both a start and end date.", "warning");
            }
        });
    } else {
         console.warn("Custom date range modal elements not found.");
    }

    // Refresh Total Conversations Button
    const refreshTotalButton = document.getElementById('refresh-total');
    if (refreshTotalButton) {
        refreshTotalButton.addEventListener('click', fetchTotalConversations);
    } else {
         console.warn("Refresh total button #refresh-total not found.");
    }

    // --- Initial Load --- 
    const initialTimeframe = document.querySelector('.timeframe-selector.active')?.dataset.timeframe || 'last_30_days';
    logDebug(`Initial data load for timeframe: ${initialTimeframe}`);
    loadVisualizationData(initialTimeframe);
    fetchTotalConversations(); // Fetch total count on initial load

}); // End DOMContentLoaded 