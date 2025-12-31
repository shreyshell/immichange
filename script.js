// Country Selection Section Interactions
document.addEventListener('DOMContentLoaded', function() {
    // Explore button hover effect
    const exploreButton = document.getElementById('exploreButton');
    const comingSoonDisclaimer = document.getElementById('comingSoonDisclaimer');
    
    if (exploreButton && comingSoonDisclaimer) {
        exploreButton.addEventListener('mouseenter', () => {
            comingSoonDisclaimer.classList.add('pulse');
            setTimeout(() => {
                comingSoonDisclaimer.classList.remove('pulse');
            }, 600); // Match the animation duration
        });
    }

    // Load dashboard data and setup pagination
    loadDashboardData();
    
    // Setup pagination event listeners after a short delay to ensure elements are rendered
    setTimeout(() => {
        setupPaginationEventListeners();
        setupModalEventListeners();
    }, 100);
});

// Country flag mapping
const countryFlags = {
    'United States': '🇺🇸',
    'USA': '🇺🇸',
    'Canada': '🇨🇦',
    'United Kingdom': '🇬🇧',
    'UK': '🇬🇧',
    'Australia': '🇦🇺',
    'Germany': '🇩🇪',
    'France': '🇫🇷',
    'Japan': '🇯🇵',
    'India': '🇮🇳',
    'China': '🇨🇳',
    'Mexico': '🇲🇽',
    'Brazil': '🇧🇷',
    'UAE': '🇦🇪',
    'Singapore': '🇸🇬',
    'Netherlands': '🇳🇱',
    'Sweden': '🇸🇪',
    'Norway': '🇳🇴',
    'Denmark': '🇩🇰',
    'Switzerland': '🇨🇭'
};

// Get country flag
function getCountryFlag(country) {
    return countryFlags[country] || '🌍'; // Default globe emoji if country not found
}

// Format timestamp to match Figma design (M/D/YYYY, H:MM AM/PM)
function formatTimestamp(isoString) {
    if (!isoString) return 'N/A';
    
    const date = new Date(isoString);
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const year = date.getFullYear();
    
    let hours = date.getHours();
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12; // 0 should be 12
    
    return `${month}/${day}/${year}, ${hours}:${minutes} ${ampm}`;
}

// Format effective date (Month DD, YYYY)
function formatEffectiveDate(isoString) {
    if (!isoString) return 'N/A';
    
    const date = new Date(isoString);
    const months = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December'];
    
    const month = months[date.getMonth()];
    const day = date.getDate();
    const year = date.getFullYear();
    
    return `${month} ${day}, ${year}`;
}

// Get severity level (randomize for demo since API doesn't provide this)
function getSeverityLevel() {
    const severities = ['high', 'medium', 'low'];
    return severities[Math.floor(Math.random() * severities.length)];
}

// Create data row HTML
function createDataRow(event) {
    const flag = getCountryFlag(event.country);
    const severity = getSeverityLevel();
    const timestamp = formatTimestamp(event.timestamp);
    const effectiveDate = formatEffectiveDate(event.effective_date);
    
    // Create unique ID for this row's expand button
    const rowId = `row-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    return `
        <div class="data-row">
            <div class="data-cell country">${flag} ${event.country}</div>
            <div class="data-cell visa-type">${event.visa_type}</div>
            <div class="data-cell change-type">${event.type_of_change}</div>
            <div class="data-cell affected-groups">${event.affected_groups}</div>
            <div class="data-cell severity">
                <div class="severity-tag ${severity}">${severity.charAt(0).toUpperCase() + severity.slice(1)}</div>
            </div>
            <div class="data-cell summary">
                <span class="summary-text" title="${event.summary}">${event.summary}</span>
                <button class="expand-summary-btn" onclick="openSummaryModal('${rowId}', ${JSON.stringify(event).replace(/"/g, '&quot;')})">+</button>
            </div>
            <div class="data-cell sources">
                <a href="${event.source}" target="_blank" class="sources-link">
                    <span class="link-icon">🔗</span>
                    Read more
                </a>
            </div>
            <div class="data-cell timestamp">
                <div class="timestamp-tag">${timestamp}</div>
            </div>
            <div class="data-cell effective-date">${effectiveDate}</div>
        </div>
    `;
}

// Open summary modal
function openSummaryModal(rowId, eventData) {
    const modal = document.getElementById('summaryModalOverlay');
    const content = document.getElementById('summaryModalContent');
    const meta = document.getElementById('summaryModalMeta');
    
    if (modal && content && meta) {
        // Set the summary content
        content.innerHTML = `<p>${eventData.summary}</p>`;
        
        // Set meta information
        const flag = getCountryFlag(eventData.country);
        const formattedDate = formatEffectiveDate(eventData.effective_date);
        
        meta.innerHTML = `
            <div class="summary-modal-meta-item"><strong>Country:</strong> ${flag} ${eventData.country}</div>
            <div class="summary-modal-meta-item"><strong>Visa Type:</strong> ${eventData.visa_type}</div>
            <div class="summary-modal-meta-item"><strong>Type of Change:</strong> ${eventData.type_of_change}</div>
            <div class="summary-modal-meta-item"><strong>Affected Groups:</strong> ${eventData.affected_groups}</div>
            <div class="summary-modal-meta-item"><strong>Effective Date:</strong> ${formattedDate}</div>
            <div class="summary-modal-meta-item"><strong>Source:</strong> <a href="${eventData.source}" target="_blank" class="sources-link">View Original</a></div>
        `;
        
        // Show modal
        modal.classList.add('active');
        
        // Prevent body scroll
        document.body.style.overflow = 'hidden';
    }
}

// Close summary modal
function closeSummaryModal() {
    const modal = document.getElementById('summaryModalOverlay');
    
    if (modal) {
        modal.classList.remove('active');
        
        // Restore body scroll
        document.body.style.overflow = '';
    }
}

// Setup modal event listeners
function setupModalEventListeners() {
    const modal = document.getElementById('summaryModalOverlay');
    const closeBtn = document.getElementById('closeModalBtn');
    
    // Close button click
    if (closeBtn) {
        closeBtn.addEventListener('click', closeSummaryModal);
    }
    
    // Click outside modal to close
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeSummaryModal();
            }
        });
    }
    
    // Escape key to close
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeSummaryModal();
        }
    });
}

// Pagination state
let currentPaginationState = {
    currentPage: 1,
    totalPages: 1,
    totalRecords: 0,
    recordsPerPage: 10
};

// Update pagination information
function updatePaginationInfo(totalRecords) {
    const recordsPerPage = 10;
    const totalPages = Math.ceil(totalRecords / recordsPerPage);
    
    // Update global state
    currentPaginationState = {
        currentPage: Math.min(currentPaginationState.currentPage, totalPages || 1),
        totalPages: totalPages || 1,
        totalRecords: totalRecords,
        recordsPerPage: recordsPerPage
    };
    
    // Update "X recorded updates" text
    const recordedUpdatesElement = document.querySelector('.recorded-updates-text');
    if (recordedUpdatesElement) {
        recordedUpdatesElement.textContent = `${totalRecords} recorded updates`;
    }
    
    // Update "of X pages" text
    const pagesTextElement = document.querySelector('.pages-text');
    if (pagesTextElement) {
        pagesTextElement.textContent = `of ${totalPages} pages`;
    }
    
    // Update page number in pagination controls
    const pageNumberElement = document.querySelector('.page-number span');
    if (pageNumberElement) {
        pageNumberElement.textContent = currentPaginationState.currentPage;
    }
    
    // Update arrow states
    updateArrowStates();
    
    return currentPaginationState;
}

// Update arrow button states (enabled/disabled)
function updateArrowStates() {
    const leftArrow = document.querySelector('.left-arrow');
    const rightArrow = document.querySelector('.right-arrow');
    
    if (leftArrow) {
        if (currentPaginationState.currentPage <= 1) {
            leftArrow.disabled = true;
            leftArrow.style.opacity = '0.5';
            leftArrow.style.cursor = 'not-allowed';
        } else {
            leftArrow.disabled = false;
            leftArrow.style.opacity = '1';
            leftArrow.style.cursor = 'pointer';
        }
    }
    
    if (rightArrow) {
        if (currentPaginationState.currentPage >= currentPaginationState.totalPages) {
            rightArrow.disabled = true;
            rightArrow.style.opacity = '0.5';
            rightArrow.style.cursor = 'not-allowed';
        } else {
            rightArrow.disabled = false;
            rightArrow.style.opacity = '1';
            rightArrow.style.cursor = 'pointer';
        }
    }
}

// Navigate to specific page
function navigateToPage(pageNumber) {
    if (pageNumber < 1 || pageNumber > currentPaginationState.totalPages) {
        return; // Invalid page number
    }
    
    currentPaginationState.currentPage = pageNumber;
    loadDashboardData(pageNumber);
}

// Navigate to previous page
function navigateToPreviousPage() {
    if (currentPaginationState.currentPage > 1) {
        navigateToPage(currentPaginationState.currentPage - 1);
    }
}

// Navigate to next page
function navigateToNextPage() {
    if (currentPaginationState.currentPage < currentPaginationState.totalPages) {
        navigateToPage(currentPaginationState.currentPage + 1);
    }
}

// Add pagination event listeners
function setupPaginationEventListeners() {
    const leftArrow = document.querySelector('.left-arrow');
    const rightArrow = document.querySelector('.right-arrow');
    
    if (leftArrow) {
        leftArrow.addEventListener('click', navigateToPreviousPage);
    }
    
    if (rightArrow) {
        rightArrow.addEventListener('click', navigateToNextPage);
    }
}

// Calculate updates from the past 7 days
function calculateUpdatesThisWeek(events) {
    const now = new Date();
    const sevenDaysAgo = new Date(now.getTime() - (7 * 24 * 60 * 60 * 1000));
    
    let count = 0;
    events.forEach(event => {
        if (event.timestamp) {
            const eventDate = new Date(event.timestamp);
            if (eventDate >= sevenDaysAgo && eventDate <= now) {
                count++;
            }
        }
    });
    
    return count;
}

// Update the weekly updates badge
function updateWeeklyBadge(count) {
    const badgeElement = document.getElementById('updatesThisWeekCount');
    if (badgeElement) {
        badgeElement.textContent = count;
    }
}

// Load dashboard data from API
async function loadDashboardData(page = 1) {
    const dataRowsContainer = document.getElementById('dataRows');
    const loadingState = document.getElementById('loadingState');
    
    try {
        // Show loading state
        loadingState.style.display = 'block';
        
        // Fetch data from API - use full URL with port
        const response = await fetch('http://localhost:8000/api/history');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success && result.data && result.data.length > 0) {
            // Hide loading state
            loadingState.style.display = 'none';
            
            // Update pagination info based on total records
            const paginationInfo = updatePaginationInfo(result.count || result.data.length);
            console.log(`Loaded ${paginationInfo.totalRecords} records across ${paginationInfo.totalPages} pages, showing page ${page}`);
            
            // Calculate pagination for current page
            const startIndex = (page - 1) * paginationInfo.recordsPerPage;
            const endIndex = startIndex + paginationInfo.recordsPerPage;
            const pageData = result.data.slice(startIndex, endIndex);
            
            // Calculate and update weekly updates count (use all data, not just current page)
            const weeklyCount = calculateUpdatesThisWeek(result.data);
            updateWeeklyBadge(weeklyCount);
            
            // Create data rows for current page
            const rowsHTML = pageData.map(event => createDataRow(event)).join('');
            dataRowsContainer.innerHTML = rowsHTML;
            
            // Update page number display
            const pageNumberElement = document.querySelector('.page-number span');
            if (pageNumberElement) {
                pageNumberElement.textContent = page;
            }
            
        } else {
            // Show fallback message
            loadingState.innerHTML = '<p>No policy updates available at the moment.</p>';
            updatePaginationInfo(0);
            updateWeeklyBadge(0);
        }
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        
        // Show sample data as fallback
        loadSampleData(page);
    }
}

// Load sample data as fallback
function loadSampleData(page = 1) {
    const dataRowsContainer = document.getElementById('dataRows');
    const loadingState = document.getElementById('loadingState');
    
    // Extended sample data to test pagination
    const sampleData = [
        {
            country: "United States",
            visa_type: "H-1B",
            type_of_change: "Policy Update",
            affected_groups: "Specialty Workers",
            severity: "Medium",
            summary: "DHS Changes Process for Awarding H-1B Work Visas to Better Protect American Workers",
            source: "https://www.uscis.gov/newsroom/news-releases/dhs-changes-process-for-awarding-h-1b-work-visas",
            timestamp: "2025-12-23T14:04:14+00:00",
            effective_date: "2025-12-23T14:04:14+00:00"
        },
        {
            country: "United States",
            visa_type: "Asylum",
            type_of_change: "Policy Update",
            affected_groups: "Asylum Seekers",
            severity: "High",
            summary: "DHS, DOJ Announce Rule to Bar Asylum for Aliens Who Pose Security Threats",
            source: "https://www.uscis.gov/newsroom/alerts/dhs-doj-announce-rule-to-bar-asylum",
            timestamp: "2025-12-29T15:58:15+00:00",
            effective_date: "2025-12-29T15:58:15+00:00"
        },
        {
            country: "Canada",
            visa_type: "Express Entry",
            type_of_change: "Program Launch",
            affected_groups: "Skilled Workers",
            severity: "Low",
            summary: "New Express Entry Draw Invites 3,500 Candidates",
            source: "https://www.canada.ca/en/immigration-refugees-citizenship",
            timestamp: "2025-12-20T10:30:00+00:00",
            effective_date: "2025-12-20T10:30:00+00:00"
        },
        {
            country: "United Kingdom",
            visa_type: "Skilled Worker",
            type_of_change: "Fee Change",
            affected_groups: "Skilled Workers",
            severity: "Medium",
            summary: "UK Increases Immigration Health Surcharge Fees",
            source: "https://www.gov.uk/healthcare-immigration-application",
            timestamp: "2025-12-18T09:15:00+00:00",
            effective_date: "2026-01-01T00:00:00+00:00"
        },
        {
            country: "Australia",
            visa_type: "Temporary Skill Shortage",
            type_of_change: "Processing Update",
            affected_groups: "Temporary Workers",
            severity: "Low",
            summary: "Faster Processing Times for TSS Visa Applications",
            source: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-skill-shortage-482",
            timestamp: "2025-12-15T14:45:00+00:00",
            effective_date: "2025-12-15T14:45:00+00:00"
        }
    ];
    
    // Hide loading state
    loadingState.style.display = 'none';
    
    // Update pagination info for sample data
    const paginationInfo = updatePaginationInfo(sampleData.length);
    console.log(`Loaded ${paginationInfo.totalRecords} sample records across ${paginationInfo.totalPages} pages, showing page ${page}`);
    
    // Calculate pagination for current page
    const startIndex = (page - 1) * paginationInfo.recordsPerPage;
    const endIndex = startIndex + paginationInfo.recordsPerPage;
    const pageData = sampleData.slice(startIndex, endIndex);
    
    // Calculate and update weekly updates count for sample data
    const weeklyCount = calculateUpdatesThisWeek(sampleData);
    updateWeeklyBadge(weeklyCount);
    
    // Create data rows with sample data
    const rowsHTML = pageData.map(event => createDataRow(event)).join('');
    dataRowsContainer.innerHTML = `
        <div style="text-align: center; padding: 10px; font-size: 12px; color: #666; margin-bottom: 10px;">
            Showing sample data - API connection failed
        </div>
        ${rowsHTML}
    `;
    
    // Update page number display
    const pageNumberElement = document.querySelector('.page-number span');
    if (pageNumberElement) {
        pageNumberElement.textContent = page;
    }
}