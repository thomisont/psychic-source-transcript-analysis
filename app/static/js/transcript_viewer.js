console.log("TRANSCRIPT_VIEWER.JS LOADED - V1");

// ==========================================
// Transcript Viewer Specific Logic
// ==========================================
// Handles DataTable initialization, data fetching for the table,
// modal display for conversation details, and transcript rendering.

document.addEventListener('DOMContentLoaded', () => {
    console.log("TRANSCRIPT_VIEWER: DOMContentLoaded listener entered.");
    // Check if we are on the Data Selection/Transcript Viewer page
    // Use a reliable element ID present ONLY on this page's template
    if (!document.getElementById('conversations-table')) {
        // console.log("Not on the Data Selection page, skipping transcript viewer init.");
        return;
    }
    console.log("Initializing Transcript Viewer page scripts...");

    // Module-scoped variables
    let conversationsDataTable = null;
    let currentTranscriptExportData = null; // <-- ADDED: Store data for export
    
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

    // Function to show/hide filter sections based on selected search type
    function toggleFilterSections() {
        const searchType = document.querySelector('input[name="search-type"]:checked')?.value || 'date';
        const dateFilters = document.getElementById('date-range-filters');
        const customDateStart = document.getElementById('custom-date-inputs');
        const customDateEnd = document.getElementById('custom-date-inputs-end');
        const idFilter = document.getElementById('conversation-id-filter');
        const searchButtonContainer = document.getElementById('search-button') ? document.getElementById('search-button').parentElement : null; // Get button container

        const isCustomTimeframe = document.getElementById('timeframe-custom')?.checked;

        if (dateFilters) dateFilters.style.display = (searchType === 'date') ? '' : 'none';
        if (idFilter) idFilter.style.display = (searchType === 'id') ? '' : 'none';
        
        // Show custom date inputs only if 'date' search AND 'custom' timeframe are selected
        const showCustom = (searchType === 'date' && isCustomTimeframe);
        if (customDateStart) customDateStart.style.display = showCustom ? '' : 'none';
        if (customDateEnd) customDateEnd.style.display = showCustom ? '' : 'none';
        
        // Show the main search button only when date search is active (ID search has its own button)
        if(searchButtonContainer) searchButtonContainer.style.display = (searchType === 'date') ? '' : 'none';

        console.log(`Toggled filters: SearchType=${searchType}, ShowDateFilters=${dateFilters?.style.display}, ShowIDFilter=${idFilter?.style.display}, ShowCustom=${showCustom}`);
    }

    // Initializes or returns the existing DataTables instance for the conversations table.
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

    // ==========================================
    // Download Helper Function
    // ==========================================
    function triggerDownload(content, filename, contentType) {
        const blob = new Blob([content], { type: contentType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        console.log(`Triggered download for ${filename}`);
    }

    // ==========================================
    // Transcript Export Functionality
    // ==========================================
    function formatTranscriptForExport(format) {
        // ADD LOGGING HERE to debug the erroneous toast
        console.log(`>>> formatTranscriptForExport called for format: ${format}`);
        console.log(`>>> Checking currentTranscriptExportData:`, currentTranscriptExportData);
        console.log(`>>> Checking transcript presence:`, currentTranscriptExportData ? (currentTranscriptExportData.transcript ? `${currentTranscriptExportData.transcript.length} messages` : 'transcript key missing/null') : 'currentTranscriptExportData is null/undefined');
        
        if (!currentTranscriptExportData || !currentTranscriptExportData.transcript) {
            console.error("!!! Condition for 'No transcript data' toast met."); // Log specifically when this happens
            if(window.UI) UI.showToast("No transcript data loaded to export.", "warning");
            return null;
        }

        const { conversation_id, start_time, duration, cost, summary, transcript } = currentTranscriptExportData;
        const filenameBase = `transcript_${conversation_id || 'unknown'}`;
        const readableDate = start_time ? Formatter.date(start_time, true) : 'Unknown Date'; // Use longer format

        console.log(`Formatting transcript ${conversation_id} for ${format} export.`);

        if (format === 'json') {
            const jsonData = {
                conversation_id: conversation_id,
                start_time: start_time, // Keep ISO string for JSON
                readable_date: readableDate,
                duration_seconds: duration,
                formatted_duration: Formatter.duration(duration),
                cost_credits: cost,
                summary: summary,
                transcript: transcript.map(msg => ({
                    timestamp: msg.timestamp, // Keep ISO string
                    speaker: msg.speaker,
                    role: msg.role,
                    text: msg.text
                }))
            };
            return {
                content: JSON.stringify(jsonData, null, 2),
                filename: `${filenameBase}.json`,
                contentType: 'application/json'
            };
        } else if (format === 'csv') {
            // Header row
            let csvContent = 'Timestamp,Speaker,Role,Text\\n';
            // Data rows
            transcript.forEach(msg => {
                const time = msg.timestamp ? new Date(msg.timestamp).toISOString() : 'N/A';
                const speaker = msg.speaker || 'Unknown';
                const role = msg.role || 'unknown';
                // Escape quotes within the text by doubling them, and enclose the whole text in quotes
                const text = `\"${(msg.text || '').replace(/"/g, '""')}\"`; 
                csvContent += `${time},${speaker},${role},${text}\\n`;
            });
             return {
                content: csvContent,
                filename: `${filenameBase}.csv`,
                contentType: 'text/csv;charset=utf-8;'
            };
        } else if (format === 'markdown') {
            let mdContent = `# Transcript: ${conversation_id}\\n\\n`;
            mdContent += `**Date:** ${readableDate}\\n`;
            mdContent += `**Duration:** ${Formatter.duration(duration)}\\n`;
            mdContent += `**Cost:** ${cost !== null && cost !== undefined ? cost + ' credits' : 'N/A'}\\n\\n`;
            mdContent += `**Summary:**\\n${summary || 'No summary available.'}\\n\\n`;
            mdContent += `## Messages\\n\\n`;

            transcript.forEach(msg => {
                const time = msg.timestamp ? Formatter.dateTime(msg.timestamp) : 'Unknown Time';
                const speakerLabel = msg.role === 'agent' ? 'Lily (Agent)' : (msg.speaker || 'Curious Caller');
                mdContent += `**${speakerLabel}:** ${msg.content || ''}\\n`;
                mdContent += `_${time}_\\n\\n`;
            });
            return {
                content: mdContent,
                filename: `${filenameBase}.md`,
                contentType: 'text/markdown;charset=utf-8;'
            };
        } else {
            console.error(`Unsupported export format: ${format}`);
             if(window.UI) UI.showToast(`Unsupported export format: ${format}`, "danger");
            return null;
        }
    }

    function handleExportClick(event) {
        // ADD LOGGING HERE to detect multiple calls
        console.log(`>>> handleExportClick invoked for event target:`, event.target.id);

        // *** ADD EXPLICIT CHECK AT HANDLER START ***
        if (!currentTranscriptExportData || !currentTranscriptExportData.transcript) {
            console.error(">>> handleExportClick: Data not ready at the start of handler!");
             if(window.UI) UI.showToast("Export data is not ready yet. Please wait a moment.", "warning");
             // Prevent default even on early exit if the link was clicked
             event.preventDefault();
             return; // Exit early
        }
        
        event.preventDefault();
        const format = event.target.id.split('-')[1]; // e.g., 'export-json' -> 'json'
        console.log(`Export button clicked for format: ${format}`);
        
        const exportData = formatTranscriptForExport(format);
        
        if (exportData) {
            triggerDownload(exportData.content, exportData.filename, exportData.contentType);
             if(window.UI) UI.showToast(`Transcript exported as ${format.toUpperCase()}.`, "success");
        } else {
            console.warn("Export failed, no data generated.");
            // Error toast is shown within formatTranscriptForExport if needed
        }
    }

    // Fetches conversation data based on selected filters (date range or ID) and populates the DataTable.
    async function handleDateSearch() {
        console.log("handleDateSearch initiated...");
        const startDateInput = document.getElementById('start-date');
        const endDateInput = document.getElementById('end-date');
        // CORRECTED ID for conversation search input
        const conversationIdInput = document.getElementById('conversation-id'); 
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
            // Use the corrected input element
            const conversationId = conversationIdInput ? conversationIdInput.value.trim() : null;
            if (conversationId) {
                console.log(`Searching for specific Conversation ID: ${conversationId}`);
                dataTable.clear().draw();
                if (resultsInfo) resultsInfo.textContent = `Loading details for Conversation ID: ${conversationId}...`;
                
                // Show loading indicator for ID search as well
                const loadingIndicator = document.getElementById('loading-indicator');
                if (loadingIndicator) loadingIndicator.classList.remove('d-none');
                
                try {
                    await viewConversation(conversationId); // Call the function within this scope
                } finally {
                     if (loadingIndicator) loadingIndicator.classList.add('d-none');
                }
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
        
        // Check if custom range radio is selected FIRST
        const customRadio = document.getElementById('timeframe-custom');
        const isCustom = customRadio?.checked;
        
        if (isCustom) {
            timeframe = 'custom';
            startDate = startDateInput ? startDateInput.value : null;
            endDate = endDateInput ? endDateInput.value : null;
            console.log(`Using custom date range directly: ${startDate} to ${endDate}`);
        } else {
            // Find the checked preset timeframe radio button
            const checkedTimeframeRadio = document.querySelector('input[name="timeframe"]:checked');
            if (checkedTimeframeRadio) {
                timeframe = checkedTimeframeRadio.value; 
                console.log(`Selected preset timeframe value: ${timeframe}`);
                // Use global getDatesFromTimeframe utility for presets
                if (typeof getDatesFromTimeframe === 'function') { 
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
                } else {
                    console.error("getDatesFromTimeframe function not found!");
                    if (window.UI) UI.showToast("Date calculation utility missing.", "danger");
                    return;
                }
            } else {
                 console.warn("No timeframe radio button selected, cannot determine date range.");
                 if (window.UI) UI.showToast("Please select a timeframe.", "warning");
                 return;
            }
        }

        // Final validation check for dates
        if (!startDate || !endDate) {
            console.error(`Date validation failed: StartDate=${startDate}, EndDate=${endDate}`);
            if (window.UI) UI.showToast("Please select or enter a valid start and end date.", "warning");
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
        
        // Show loading indicator (ensure it exists)
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) loadingIndicator.classList.remove('d-none');
        
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
        } finally {
            // **ALWAYS** hide loading indicator after fetch attempt
            if (loadingIndicator) loadingIndicator.classList.add('d-none');
            console.log("handleDateSearch finished attempt, hiding loading indicator.");
        }
    }

    // Renders the conversation transcript messages into the modal with iMessage styling.
    function renderTranscript(transcriptMessages, container) {
        console.log("Rendering transcript with messages:", transcriptMessages);
        if (!container) {
            console.error("Transcript container not found in modal.");
            return;
        }

        container.innerHTML = ''; // Clear previous content

        if (!transcriptMessages || transcriptMessages.length === 0) {
            container.innerHTML = '<div class="text-center text-muted p-3">No transcript messages available.</div>';
            return;
        }

        transcriptMessages.forEach(message => {
            // Determine speaker and alignment based on role
            const isAgent = message.role === 'agent';
            const rowClass = isAgent ? 'agent-message' : 'caller-message'; // Parent row class for alignment
            const speakerLabel = isAgent ? 'Lily' : 'Curious Caller'; // Corrected speaker labels
            const avatarIcon = isAgent ? 'fas fa-headset' : 'fas fa-user'; // Font Awesome icons

            const messageGroup = document.createElement('div');
            messageGroup.className = 'message-group d-flex align-items-end mb-3'; // Use flex for avatar/bubble alignment

            const avatarContainer = document.createElement('div');
            // Simplified container, remove specific sizing/bg classes from JS
            avatarContainer.className = `avatar-container ${isAgent ? 'me-2' : 'ms-2 order-1'}`; 
            // Apply color and larger size directly to the icon tag
            avatarContainer.innerHTML = `<i class="${avatarIcon} fa-2x"></i>`; // Use fa-2x for larger size

            const messageBubble = document.createElement('div');
            messageBubble.className = 'message-bubble d-flex flex-column'; // Bubble container

            const speakerNameSpan = document.createElement('span');
            speakerNameSpan.className = 'speaker-label mb-1'; // Class for speaker name
            speakerNameSpan.textContent = speakerLabel;

            const messageTextSpan = document.createElement('span');
            messageTextSpan.className = 'message-text'; // Class for message text
            // REVERTING to use .content based on previous working state
            // *** CRITICAL: This rendering logic EXPECTS the message text to be in the 'content' key ***
            // *** Do not change to '.text' or other keys without verifying the data source ***
            messageTextSpan.textContent = message.content || '(No text content)'; // Handle null/empty text

            const timestampSpan = document.createElement('span');
            timestampSpan.className = 'timestamp mt-1 align-self-end'; // Class for timestamp, aligned right
            timestampSpan.textContent = message.timestamp ? Formatter.time(message.timestamp) : 'Unknown time';


            // Assemble bubble content
            messageBubble.appendChild(speakerNameSpan);
            messageBubble.appendChild(messageTextSpan);
            messageBubble.appendChild(timestampSpan);

            // Assemble message group (avatar + bubble)
            messageGroup.appendChild(avatarContainer);
            messageGroup.appendChild(messageBubble);
             
            // Create the main row div and apply alignment class
            const messageRow = document.createElement('div');
            messageRow.className = rowClass; // This div controls left/right justification via CSS
            messageRow.appendChild(messageGroup); // Append the group to the row

            container.appendChild(messageRow); // Add the complete row to the main container
        });

         // Scroll to bottom is removed based on user feedback
        // container.scrollTop = container.scrollHeight; 
        console.log("Transcript rendering complete.");
    }

    // Fetches details for a specific conversation ID and displays them in the modal.
    async function viewConversation(conversationId) {
        console.log(`Viewing conversation ID: ${conversationId}`);
        if (typeof window !== 'undefined') window.currentConversationId = conversationId; 
        
        // Use the new container ID
        const transcriptContainer = document.getElementById('modal-transcript-content'); 
        const modalTitle = document.getElementById('transcriptModalLabel');
        // Other modal elements for overview details
        const modalConvId = document.getElementById('modal-conversation-id');
        const modalConvDate = document.getElementById('modal-conversation-date');
        const modalDuration = document.getElementById('modal-duration');
        const modalCost = document.getElementById('modal-cost');
        const modalSummary = document.getElementById('modal-summary');
        const modalHiNotesTextarea = document.getElementById('hi-notes-textarea'); 
        const resultsInfo = document.getElementById('results-info'); // Main page info
        const modalTranscriptContent = document.getElementById('modal-transcript-content');
        const exportDropdownButton = document.querySelector('#conversationModal .modal-footer .dropdown-toggle'); // Get export button

        if (!transcriptContainer || !modalTitle || !modalConvId || !modalConvDate || !modalSummary) { // Check essential elements
            console.error("Transcript modal elements not found.");
            if (window.UI) UI.showToast("Error displaying transcript: UI elements missing.", "danger");
            return;
        }

        // Show simple loading state INITIALLY in the container and modal title
        modalTitle.textContent = `Loading Conversation: ${conversationId}...`;
        transcriptContainer.innerHTML = '<div class="text-center text-muted p-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Loading transcript...</p></div>';
        // Clear overview details
        modalConvId.textContent = 'Loading...';
        modalConvDate.textContent = 'Loading...';
        modalDuration.textContent = 'Loading...';
        modalCost.textContent = '...';
        modalSummary.textContent = 'Loading...';
        if (modalHiNotesTextarea) modalHiNotesTextarea.value = '';
        
        // Show the modal
        if (!transcriptModalInstance) {
             console.error("Cannot show modal: Instance not available.");
             if (window.UI) UI.showToast("Could not display transcript viewer.", "danger");
             return;
        }
        transcriptModalInstance.show();

        currentTranscriptExportData = null; // Clear previous export data
        if (exportDropdownButton) exportDropdownButton.disabled = true; // Disable export button initially

        console.log("Showing modal...");

        try {
            // Step 1: Fetch details
            const details = await API.fetch(`/api/conversations/${conversationId}`);
            console.log("Conversation details received:", details);

            // Validate Transcript Data
            if (!details || !Array.isArray(details.transcript)) {
                 console.error("Invalid or missing transcript data format received:", details);
                 throw new Error('Invalid or missing transcript data received.');
            }

            // Step 2: Populate Overview Section in Modal
            modalTitle.textContent = `Conversation: ${details.conversation_id || conversationId}`;
            modalConvId.textContent = details.conversation_id || 'N/A';
            modalConvDate.textContent = details.start_time ? Formatter.dateTime(details.start_time) : 'N/A';
            modalDuration.textContent = details.duration ? Formatter.duration(details.duration) : 'N/A';
            modalCost.textContent = details.cost !== undefined && details.cost !== null ? `${details.cost} credits` : 'N/A';
            modalSummary.textContent = details.summary || 'No AI summary available.';
            if (modalHiNotesTextarea) {
                modalHiNotesTextarea.value = details.hi_notes || '';
            }

            // Step 3: Render Transcript using the updated function
            renderTranscript(details.transcript, transcriptContainer);

            // Optional: Update main page results info
            if (resultsInfo) resultsInfo.textContent = `Viewing transcript for ${conversationId}.`;

            // --- Store data needed for export ---
            currentTranscriptExportData = {
                conversation_id: details.conversation_id,
                start_time: details.start_time,
                duration: details.duration,
                cost: details.cost_credits,
                summary: details.summary,
                transcript: details.transcript || [] // Ensure transcript is an array
            };
            console.log("Stored data for export:", currentTranscriptExportData);
            // --- End storing export data ---

            if (exportDropdownButton) exportDropdownButton.disabled = false; // Re-enable export button on success

        } catch (error) {
            console.error("Error fetching or displaying conversation details:", error);
            if (window.UI) UI.showToast(`Error loading transcript: ${error.message}`, "danger");
            modalTitle.textContent = `Error Loading Transcript`;
            transcriptContainer.innerHTML = `<div class="alert alert-danger">Failed to load transcript for ID ${conversationId}. ${error.message}</div>`;
            // Optionally update results info on main page
            if (resultsInfo) {
                 resultsInfo.textContent = `Error loading transcript ${conversationId}: ${error.message}`;
                 resultsInfo.classList.add('text-danger');
            }
            currentTranscriptExportData = null; // Clear export data on error
            if (exportDropdownButton) exportDropdownButton.disabled = true; // Ensure export button is disabled on error
        }
    }

    // --- Main Initialization within DOMContentLoaded ---
    
    // Wrap initialization in jQuery's ready function to ensure DataTables plugin is loaded
    $(document).ready(function() {
        console.log("jQuery document ready fired. Initializing DataTable and loading data...");
        initializeDataTable(); // Initialize the table
        
        // Attach listeners AFTER table is potentially initialized
        const searchButton = document.getElementById('search-button');
        const conversationIdSearchButton = document.getElementById('search-id-button'); // Ensure this ID is correct in HTML
        const radioButtons = document.querySelectorAll('input[name="search-type"], input[name="timeframe"]');
        const tableBody = document.querySelector('#conversations-table tbody');
        const exportJsonLink = document.getElementById('export-json');
        const exportCsvLink = document.getElementById('export-csv');
        const exportMarkdownLink = document.getElementById('export-markdown');

        if (searchButton) {
            searchButton.addEventListener('click', handleDateSearch);
            console.log("Listener attached to Date Search button.");
        }
        
        if (conversationIdSearchButton) {
            conversationIdSearchButton.addEventListener('click', handleDateSearch); // handleDateSearch now handles both types
            console.log("Listener attached to ID Search button.");
        }

        radioButtons.forEach(radio => {
            radio.addEventListener('change', toggleFilterSections);
        });
        console.log("Listeners attached to radio buttons.");

        if (tableBody) {
            tableBody.addEventListener('click', function(event) {
                if (event.target.classList.contains('view-btn')) {
                    const conversationId = event.target.getAttribute('data-id');
                    console.log(`View button clicked for ID: ${conversationId}`);
                    viewConversation(conversationId);
                }
            });
            console.log("Listener attached to table body for view buttons.");
        } else {
            console.warn("Table body #conversations-table tbody not found for event listener.");
        }

        if (exportJsonLink) exportJsonLink.addEventListener('click', handleExportClick);
        if (exportCsvLink) exportCsvLink.addEventListener('click', handleExportClick);
        if (exportMarkdownLink) exportMarkdownLink.addEventListener('click', handleExportClick);
        console.log("Listeners attached to export links.");
        
        // Initial setup calls
        toggleFilterSections(); // Set initial visibility of filters
        handleDateSearch(); // Perform initial data load for the table based on default filters
        console.log("Initial filter visibility set and initial data search triggered.");

        // Add event listener for HI Notes Save button in modal
        const saveNotesBtnModal = document.getElementById('save-hi-notes-btn-modal');
        if (saveNotesBtnModal) {
            saveNotesBtnModal.addEventListener('click', async function() {
                const notesTextarea = document.getElementById('hi-notes-textarea');
                const notesStatus = document.getElementById('save-notes-status-modal');
                const notes = notesTextarea.value;
                const conversationId = document.getElementById('modal-conversation-id').textContent;
                if (!conversationId || conversationId === 'N/A') {
                    notesStatus.textContent = 'No conversation ID.';
                    return;
                }
                notesStatus.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
                try {
                    const response = await fetch(`/api/conversations/${conversationId}/notes`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ hi_notes: notes })
                    });
                    const data = await response.json();
                    if (response.ok && data.success) {
                        notesStatus.innerHTML = '<i class="fas fa-check-circle text-success"></i> Saved!';
                    } else {
                        notesStatus.innerHTML = `<i class="fas fa-times-circle text-danger"></i> Error: ${data.error || 'Unknown error'}`;
                    }
                } catch (error) {
                    notesStatus.innerHTML = `<i class="fas fa-exclamation-triangle text-danger"></i> Error: ${error.message}`;
                }
                setTimeout(() => { notesStatus.innerHTML = ''; }, 3000);
            });
        }

    }); // End of jQuery document ready

    console.log("Transcript Viewer page scripts initialization complete.");

}); // End DOMContentLoaded