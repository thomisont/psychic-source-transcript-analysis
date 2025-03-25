/**
 * Main JavaScript file for Psychic Source Transcript Analysis Tool
 */

// Format date objects for display
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Format seconds as minutes:seconds
function formatDuration(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

// Map sentiment score to text description
function sentimentToText(score) {
    if (score > 0.5) return 'Very Positive';
    if (score > 0.1) return 'Positive';
    if (score > -0.1) return 'Neutral';
    if (score > -0.5) return 'Negative';
    return 'Very Negative';
}

// Get color for sentiment score
function sentimentToColor(score) {
    if (score > 0.5) return '#28a745'; // green
    if (score > 0.1) return '#5cb85c'; // light green
    if (score > -0.1) return '#ffc107'; // yellow
    if (score > -0.5) return '#ff9800'; // orange
    return '#dc3545'; // red
}

// Copy text to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text)
        .then(() => {
            // Show success message
            const toast = document.createElement('div');
            toast.classList.add('toast', 'align-items-center', 'text-white', 'bg-success', 'border-0');
            toast.setAttribute('role', 'alert');
            toast.setAttribute('aria-live', 'assertive');
            toast.setAttribute('aria-atomic', 'true');
            
            toast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas fa-check-circle me-2"></i>Copied to clipboard!
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            `;
            
            document.body.appendChild(toast);
            const bsToast = new bootstrap.Toast(toast);
            bsToast.show();
            
            // Remove toast after it's hidden
            toast.addEventListener('hidden.bs.toast', function() {
                document.body.removeChild(toast);
            });
        })
        .catch(err => {
            console.error('Failed to copy text: ', err);
        });
} 