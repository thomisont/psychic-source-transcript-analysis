console.log("TRANSCRIPT_VIEWER.JS LOADED - V1");

// ==========================================
// Transcript Viewer / Data Selection Specific Functions
// ==========================================

// Ensure utilities are loaded first (from utils.js)

document.addEventListener('DOMContentLoaded', () => {
    console.log("TRANSCRIPT_VIEWER: DOMContentLoaded listener entered.");
    // Check if we are on the Data Selection/Transcript Viewer page
    // Use a reliable element ID present ONLY on this page's template
    if (!document.getElementById('conversations-table')) {
        // console.log("Not on the Data Selection page, skipping transcript viewer init.");
        return;
    }
    console.log("Initializing Transcript Viewer page scripts...");

    // DataTable instance variable (scoped to this module/listener)
    let conversationsDataTable = null;
    // Global variable reference needed for viewConversation
    // We might need to rethink how currentConversationId is managed if export stays global
    // For now, assume window.currentConversationId exists and is set by viewConversation
    
    // ---- Initialize Modal Instance Once ----
    let transcriptModalInstance = null;
    const transcriptModalElement = document.getElementById('conversationModal'); // Use the modal's main ID
    if (transcriptModalElement) {
        try {
            transcriptModalInstance = new bootstrap.Modal(transcriptModalElement);
            console.log("Transcript modal instance created.");

        } catch(modalError) {
            console.error("Failed to create Bootstrap Modal instance on load:", modalError);
            if(window.UI) UI.showToast("Error preparing transcript viewer.", "danger");
        }
    } else {
        console.error("Transcript modal element #conversationModal not found.");
    }
    // ---- End Modal Initialization ----

    // Function to initialize the DataTable
    function initializeDataTable() {
        console.log("Initializing DataTable for Transcript Viewer...");
        const tableSelector = '#conversations-table';

        console.log(`Checking if DataTable is already initialized for ${tableSelector}...`);
        if ($.fn.DataTable.isDataTable(tableSelector)) {
            console.log("DataTable already initialized.");
            conversationsDataTable = $(tableSelector).DataTable();
            return conversationsDataTable;
        }

        console.log(`Attempting to initialize DataTable for ${tableSelector}...`);
        try {
            conversationsDataTable = $(tableSelector).DataTable({
                responsive: true,
                order: [[0, 'desc']], // Default sort by date descending
                language: {
                    search: "_INPUT_",
                    searchPlaceholder: "Search transcripts..."
                },
                columns: [
                    { title: "Start Time", type: "date" },
                    { title: "Duration" },
                    { title: "Turns" },
                    { title: "Status" },
                    { title: "Conversation ID" },
                    { title: "Actions", orderable: false, searchable: false }
                ]
            });
            console.log("DataTable initialized successfully.");
        } catch (error) {
            console.error("Failed to initialize DataTable:", error);
            if (window.UI) UI.showToast("Error initializing transcript table.", "danger"); 
            conversationsDataTable = null;
        }
        console.log("Finished initializeDataTable function.");
        return conversationsDataTable;
    }

    // Function to handle search based on date range or conversation ID
    async function handleDateSearch() {
        console.log("handleDateSearch initiated...");
        const startDateInput = document.getElementById('start-date');
        const endDateInput = document.getElementById('end-date');
        const conversationIdInput = document.getElementById('conversation_id_search');
        const resultsInfo = document.getElementById('results-info');
        const dataTable = conversationsDataTable; // Use the scoped instance

        if (!dataTable) {
            console.error("DataTable not initialized. Cannot perform search.");
            if (window.UI) UI.showToast("Transcript table not ready.", "warning");
            return;
        }
        
        // Determine selected search type (date or ID)
        const searchTypeRadio = document.querySelector('input[name="search-type"]:checked');
        const searchType = searchTypeRadio ? searchTypeRadio.value : 'date'; // Default to date

        // --- Handle ID Search --- 
        if (searchType === 'id') {
            const conversationId = conversationIdInput ? conversationIdInput.value.trim() : null;
            if (conversationId) {
                console.log(`Searching for specific Conversation ID: ${conversationId}`);
                dataTable.clear().draw();
                if (resultsInfo) resultsInfo.textContent = `Loading details for Conversation ID: ${conversationId}...`;
                await viewConversation(conversationId); // Call the function within this scope
                return; // ID search complete
            } else {
                 if (window.UI) UI.showToast("Please enter a Conversation ID.", "warning");
                 return; // Exit if ID search selected but no ID entered
            }
        }

        // --- Handle Date Search --- 
        let timeframe = 'custom';
        let startDate = null;
        let endDate = null;
        
        // CORRECTLY find the checked timeframe radio button
        const checkedTimeframeRadio = document.querySelector('input[name="timeframe"]:checked');
        if (checkedTimeframeRadio) {
            timeframe = checkedTimeframeRadio.value; // e.g., '7d', '30d', 'all', 'custom'
            console.log(`Selected timeframe value: ${timeframe}`);
        } else {
            console.warn("No timeframe radio button selected, defaulting to custom.");
            timeframe = 'custom';
        }

        // Use global getDatesFromTimeframe utility for presets
        if (timeframe !== 'custom' && typeof getDatesFromTimeframe === 'function') { 
            try {
                const dates = getDatesFromTimeframe(timeframe); 
                startDate = dates.startDate;
                endDate = dates.endDate;
                // Update input fields if they exist (for visual consistency)
                if (startDateInput) startDateInput.value = startDate;
                if (endDateInput) endDateInput.value = endDate;
                console.log(`Calculated dates for timeframe '${timeframe}': ${startDate} to ${endDate}`);
            } catch (e) {
                console.error(`Error getting dates for timeframe ${timeframe}:`, e);
                if (window.UI) UI.showToast(`Invalid timeframe value: ${timeframe}`, "danger");
                return;
            }
        } else { // Handle custom timeframe
            startDate = startDateInput ? startDateInput.value : null;
            endDate = endDateInput ? endDateInput.value : null;
            console.log(`Using custom date range: ${startDate} to ${endDate}`);
            // Ensure the 'custom' radio is actually checked if we fall here
            const customRadio = document.getElementById('timeframe-custom');
            if (customRadio) customRadio.checked = true;
        }

        // Final validation check
        if (!startDate || !endDate) {
            console.error(`Validation failed: StartDate=${startDate}, EndDate=${endDate}`);
            if (window.UI) UI.showToast("Please select a valid start and end date or a timeframe.", "warning");
            return;
        }

        console.log(`Searching conversations from ${startDate} to ${endDate}`);
        dataTable.clear().draw();
        if (resultsInfo) {
            resultsInfo.textContent = `Loading conversations from ${startDate} to ${endDate}...`;
            resultsInfo.classList.remove('text-danger');
        }

        // Fetch data using global API utility
        const fetchUrl = `/api/conversations?start_date=${startDate}&end_date=${endDate}&limit=10000`;
        console.log(`>>> Calling API.fetch for URL: ${fetchUrl}`);
        try {
             // Use global API utility
            const apiData = await API.fetch(fetchUrl);
            console.log("<<< API.fetch returned. Response:", apiData);

            if (apiData && Array.isArray(apiData.conversations)) {
                const conversations = apiData.conversations;
                const totalCount = apiData.total_count || conversations.length;
                console.log(`Processing ${conversations.length} conversations, total matching: ${totalCount}`);

                if (conversations.length > 0) {
                    // Populate DataTable using rows.add()
                    // Use global Formatter utility
                    dataTable.rows.add(conversations.map(conv => [
                        Formatter.date(conv.start_time),
                        Formatter.duration(conv.duration),
                        conv.message_count || 'N/A',
                        conv.status || 'N/A',
                        conv.conversation_id || 'N/A',
                        `<button class="btn btn-sm btn-outline-primary view-btn" data-id="${conv.conversation_id}">View</button>`
                    ])).draw();
                    if (resultsInfo) resultsInfo.textContent = `Showing ${conversations.length} of ${totalCount} conversations found for ${startDate} to ${endDate}.`;
                } else {
                    if (resultsInfo) resultsInfo.textContent = `No conversations found for ${startDate} to ${endDate}.`;
                    dataTable.clear().draw();
                }
            } else {
                throw new Error("Invalid data format received from API.");
            }
        } catch (error) {
            console.error("Error fetching conversations:", error);
            if (resultsInfo) {
                resultsInfo.textContent = `Error loading conversations: ${error.message}`;
                resultsInfo.classList.add('text-danger');
            }
            // UI.showToast is handled by API.fetch
            dataTable.clear().draw();
        }
    }

    // Function to display a single conversation's transcript
    async function viewConversation(conversationId) {
        console.log(`Viewing conversation ID: ${conversationId}`);
        if (typeof window !== 'undefined') window.currentConversationId = conversationId; 
        
        const transcriptContainer = document.getElementById('transcript-content');
        const transcriptTitle = document.getElementById('transcriptModalLabel');
        const resultsInfo = document.getElementById('results-info');

        if (!transcriptContainer || !transcriptTitle) {
            console.error("Transcript modal elements not found.");
            if (window.UI) UI.showToast("Error displaying transcript: UI elements missing.", "danger");
            return;
        }

        // Show simple loading state INITIALLY in the container
        transcriptTitle.textContent = `Loading Transcript: ${conversationId}...`;
        transcriptContainer.innerHTML = '<div class="text-center p-5"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
        
        // Ensure modal is ready but DON'T show it yet
        if (!transcriptModalInstance) {
             console.error("Cannot prepare modal: Instance not available.");
             if (window.UI) UI.showToast("Could not display transcript viewer.", "danger");
             return;
        }

        try {
            // Step 1: Fetch details
            const details = await API.fetch(`/api/conversations/${conversationId}`);
            console.log("Conversation details received (simplified modal):", details);

            // Validate Transcript Data
            if (!details || !details.transcript || !Array.isArray(details.transcript)) {
                 throw new Error('Invalid or missing transcript data format received.');
            }

            // Step 2a: Populate Overview Section
            const overviewLoading = document.getElementById('overview-loading');
            const overviewDetails = document.getElementById('overview-details');
            if (overviewLoading && overviewDetails) {
                document.getElementById('overview-id').textContent = details.conversation_id || 'N/A';
                document.getElementById('overview-start').textContent = details.start_time ? Formatter.date(details.start_time) : 'N/A';
                document.getElementById('overview-duration').textContent = details.duration !== null ? Formatter.duration(details.duration) : 'N/A';
                document.getElementById('overview-status').textContent = details.status || 'N/A';
                // Populate cost_credits
                document.getElementById('overview-cost-credits').textContent = details.cost !== null ? details.cost : 'N/A';
                // Populate summary
                document.getElementById('overview-summary').textContent = details.summary || 'Not available';

                overviewLoading.style.display = 'none';
                overviewDetails.style.display = 'block';
            } else {
                 console.warn("Overview elements not found in modal.");
            }

            // Step 2b: Render transcript content
            transcriptTitle.textContent = `Transcript: ${conversationId}`;
            renderTranscript(details.transcript, transcriptContainer);

            // Step 3: NOW show the modal
            transcriptModalInstance.show();

            // Update status message
            if (resultsInfo) resultsInfo.textContent = `Displaying transcript for Conversation ID: ${conversationId}.`;

        } catch (error) {
            console.error('Error fetching or rendering transcript:', error);
            // Update title and show error in transcript area
            transcriptTitle.textContent = `Error Loading Transcript: ${conversationId}`;
            transcriptContainer.innerHTML = `<div class="alert alert-danger">Failed to load transcript: ${error.message}</div>`;
            // Also hide overview loading/details and show error there if possible
            const overviewLoading = document.getElementById('overview-loading');
            const overviewDetails = document.getElementById('overview-details');
            if(overviewLoading) overviewLoading.textContent = 'Error loading details.';
            if(overviewDetails) overviewDetails.style.display = 'none';
            // Show modal even on error to display the message
            if (transcriptModalInstance) transcriptModalInstance.show(); 

            // Optionally update results info on main page
            if (resultsInfo) {
                 resultsInfo.textContent = `Error loading transcript ${conversationId}: ${error.message}`;
                 resultsInfo.classList.add('text-danger');
            }
        }
    }

    // Function to render the transcript messages in iMessage style
    function renderTranscript(transcriptMessages, container) {
        if (!container) return;
        container.innerHTML = ''; // Clear previous content

        if (!transcriptMessages || transcriptMessages.length === 0) {
            container.innerHTML = '<div class="alert alert-info">No transcript messages available.</div>';
            return;
        }

        // Iterate over transcriptMessages
        transcriptMessages.forEach((turn, index) => {
            // Determine role based on the 'role' field provided by the backend
            const isUser = turn.role === 'user';
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message-bubble-row', isUser ? 'user-row' : 'agent-row');

            const bubble = document.createElement('div');
            bubble.classList.add('message-bubble', isUser ? 'user-bubble' : 'agent-bubble');

            const speakerSpan = document.createElement('span');
            speakerSpan.classList.add('speaker-label');
            speakerSpan.textContent = isUser ? 'Curious Caller' : 'Lily'; // Assuming 'Lily' is the agent

            const messageContent = document.createElement('p');
            // Use the 'content' field provided by the backend
            messageContent.textContent = turn.content || '[Empty message]';

            const timestampSpan = document.createElement('span');
            timestampSpan.classList.add('timestamp');
            // Use global Formatter utility
            let formattedTimestamp = 'No timestamp';
            try {
                formattedTimestamp = turn.timestamp ? Formatter.date(turn.timestamp) : 'No timestamp';
            } catch (formatError) {
                console.error(`Error formatting timestamp for message ${index}:`, turn.timestamp, formatError);
                formattedTimestamp = turn.timestamp || 'Invalid timestamp'; // Fallback if Formatter fails
            }
            timestampSpan.textContent = formattedTimestamp;

            bubble.appendChild(speakerSpan);
            bubble.appendChild(messageContent);
            bubble.appendChild(timestampSpan);
            messageDiv.appendChild(bubble);
            container.appendChild(messageDiv);
        });
    }

    // ------------------------------------------
    // Event Listener Setup
    // ------------------------------------------

    // Initialize the DataTable
    conversationsDataTable = initializeDataTable();

    // Add event listeners for timeframe buttons (Labels)
    const timeframeLabels = document.querySelectorAll('.btn-group[aria-label="Timeframe selection"] label.btn');
    timeframeLabels.forEach(label => {
        label.addEventListener('click', (event) => {
            // The radio button state is handled automatically by the browser
            // We just need to trigger the search
            // Small delay to allow radio state to update before reading it?
            setTimeout(handleDateSearch, 0); 
        });
    });

    // Add event listener for the main search button (for custom range)
    const customSearchBtn = document.getElementById('search-button'); // CORRECT ID from HTML
    if (customSearchBtn) {
        // Add logic here to ensure the 'custom' radio is selected when this is clicked?
        customSearchBtn.addEventListener('click', () => {
            const customRadio = document.getElementById('timeframe-custom');
            if (customRadio) customRadio.checked = true;
            handleDateSearch();
        });
    } else {
        console.warn("Custom date search button #search-button not found.");
    }

    // Add event listener for the conversation ID search button (Refined logic)
    const convIdSearchInput = document.getElementById('conversation-id');
    const convIdSearchBtn = document.getElementById('id-search-button');
    if (convIdSearchBtn && convIdSearchInput) {
        const searchById = () => {
            const id = convIdSearchInput.value.trim();
            if (id) {
                // Switch radio button visually
                const radioById = document.getElementById('search-by-id');
                if (radioById) radioById.checked = true;
                // Trigger the search logic (handleDateSearch checks the ID input)
                handleDateSearch(); 
            } else {
                if (window.UI) UI.showToast("Please enter a Conversation ID.", "warning");
            }
        };
        convIdSearchBtn.addEventListener('click', searchById);
        // Optional: Allow Enter key press in ID input field
        convIdSearchInput.addEventListener('keypress', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault(); // Prevent form submission
                searchById();
            }
        });
    } else {
        console.warn("Conversation ID search elements (#id-search-button or #conversation-id) not found.");
    }

    // Add event listener for view buttons (using event delegation on the table body)
    const tableBody = document.querySelector('#conversations-table tbody');
    if (tableBody) {
        tableBody.addEventListener('click', function(event) {
            if (event.target.classList.contains('view-btn')) {
                const conversationId = event.target.getAttribute('data-id');
                if (conversationId) {
                    viewConversation(conversationId);
                }
            }
        });
    } else {
        console.warn("Table body #conversations-table tbody not found for delegation.");
    }

    // Initial data load (fetch for default timeframe)
    // Find the LABEL associated with the default radio button (e.g., 30d)
    /*
    const defaultTimeframeLabel = document.querySelector('label[for="timeframe-30d"]'); 
    if (defaultTimeframeLabel) {
        console.log("Simulating click on default timeframe label...");
        defaultTimeframeLabel.click(); // Simulate click on the label
    } else {
        console.warn("Default timeframe label not found, initial load might not occur.");
    }
    */
    // ---- Direct call for initial load --- 
    console.log("Directly calling handleDateSearch for initial load...");
    // Ensure default radio (e.g., 30d) is checked visually if needed
    const defaultRadio = document.getElementById('timeframe-30d');
    if(defaultRadio) defaultRadio.checked = true;
    handleDateSearch(); 
    // ---- End Direct call ---- 

}); // End DOMContentLoaded listener 
