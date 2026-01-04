// Test function to verify JavaScript is loading
console.log('Script.js is loading...');

// Simple test function
function testFilterButton() {
    console.log('Testing filter button...');
    const filterButton = document.getElementById('filterButton');
    const filterDropdown = document.getElementById('filterDropdown');
    
    console.log('filterButton found:', !!filterButton);
    console.log('filterDropdown found:', !!filterDropdown);
    
    if (filterButton) {
        console.log('Filter button element:', filterButton);
        console.log('Filter button classes:', filterButton.className);
        console.log('Filter button style:', filterButton.style.cssText);
    }
    
    if (filterDropdown) {
        console.log('Filter dropdown element:', filterDropdown);
        console.log('Filter dropdown classes:', filterDropdown.className);
        console.log('Filter dropdown style:', filterDropdown.style.cssText);
    }
}

// Country Selection Section Interactions
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded');
    console.log('Testing element access:');
    console.log('dataRows:', document.getElementById('dataRows'));
    console.log('loadingState:', document.getElementById('loadingState'));
    console.log('All elements with loadingState class:', document.getElementsByClassName('loading-state'));
    
    // Load dashboard data and setup pagination
    console.log('About to call loadDashboardData');
    loadDashboardData();
    
    // Setup all event listeners after a short delay to ensure elements are rendered
    setTimeout(() => {
        testFilterButton(); // Add test function call
        setupFilterSystem();
        setupPaginationEventListeners();
        setupModalEventListeners();
    }, 100);
});

// Filter system state
let filterState = {
    country: [],
    visaType: [],
    affectedGroups: [],
    changeType: []
};

let allEventsData = []; // Store all events for filtering

// Setup filter system
function setupFilterSystem() {
    console.log('Setting up filter system...');
    
    const filterButton = document.getElementById('filterButton');
    const filterDropdown = document.getElementById('filterDropdown');
    const applyFiltersBtn = document.getElementById('applyFiltersBtn');
    const clearFiltersBtn = document.getElementById('clearFiltersBtn');
    
    console.log('Filter elements found:');
    console.log('filterButton:', !!filterButton);
    console.log('filterDropdown:', !!filterDropdown);
    console.log('applyFiltersBtn:', !!applyFiltersBtn);
    console.log('clearFiltersBtn:', !!clearFiltersBtn);
    
    // Toggle filter dropdown
    if (filterButton && filterDropdown) {
        console.log('Adding click listener to filter button');
        filterButton.addEventListener('click', (e) => {
            console.log('Filter button clicked!');
            e.stopPropagation();
            const isActive = filterDropdown.classList.contains('active');
            if (isActive) {
                filterDropdown.classList.remove('active');
                console.log('Filter dropdown hidden');
            } else {
                filterDropdown.classList.add('active');
                console.log('Filter dropdown shown');
            }
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!filterDropdown.contains(e.target) && !filterButton.contains(e.target)) {
                filterDropdown.classList.remove('active');
                console.log('Filter dropdown closed by outside click');
            }
        });
    } else {
        console.error('Filter button or dropdown not found!');
    }
    
    // Apply filters
    if (applyFiltersBtn) {
        console.log('Adding click listener to apply filters button');
        applyFiltersBtn.addEventListener('click', applyFilters);
    } else {
        console.error('Apply filters button not found!');
    }
    
    // Clear filters
    if (clearFiltersBtn) {
        console.log('Adding click listener to clear filters button');
        clearFiltersBtn.addEventListener('click', clearFilters);
    } else {
        console.error('Clear filters button not found!');
    }
}

// Populate filter dropdowns with unique values from data
function populateFilterDropdowns(events) {
    const countries = [...new Set(events.map(e => e.country))].sort();
    const visaTypes = [...new Set(events.map(e => e.visa_type))].sort();
    const affectedGroups = [...new Set(events.map(e => e.affected_groups))].sort();
    const changeTypes = [...new Set(events.map(e => e.type_of_change))].sort();
    
    populateCheckboxList('countryFilter', countries);
    populateCheckboxList('visaTypeFilter', visaTypes);
    populateCheckboxList('affectedGroupsFilter', affectedGroups);
    populateCheckboxList('changeTypeFilter', changeTypes);
}

// Helper function to populate a checkbox list
function populateCheckboxList(containerId, options) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = '';
    
    options.forEach(option => {
        const checkboxItem = document.createElement('div');
        checkboxItem.className = 'checkbox-item';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `${containerId}_${option.replace(/\s+/g, '_')}`;
        checkbox.value = option;
        
        const label = document.createElement('label');
        label.htmlFor = checkbox.id;
        label.textContent = option;
        
        checkboxItem.appendChild(checkbox);
        checkboxItem.appendChild(label);
        container.appendChild(checkboxItem);
    });
}

// Helper function to get selected checkbox values
function getSelectedCheckboxValues(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return [];
    
    const checkboxes = container.querySelectorAll('input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

// Apply filters to the data
function applyFilters() {
    // Get current filter values from checkboxes
    filterState.country = getSelectedCheckboxValues('countryFilter');
    filterState.visaType = getSelectedCheckboxValues('visaTypeFilter');
    filterState.affectedGroups = getSelectedCheckboxValues('affectedGroupsFilter');
    filterState.changeType = getSelectedCheckboxValues('changeTypeFilter');
    
    // Filter the data
    let filteredEvents = allEventsData.filter(event => {
        return (filterState.country.length === 0 || filterState.country.includes(event.country)) &&
               (filterState.visaType.length === 0 || filterState.visaType.includes(event.visa_type)) &&
               (filterState.affectedGroups.length === 0 || filterState.affectedGroups.includes(event.affected_groups)) &&
               (filterState.changeType.length === 0 || filterState.changeType.includes(event.type_of_change));
    });
    
    // Update the display with filtered data
    displayFilteredData(filteredEvents);
    
    // Close the dropdown
    document.getElementById('filterDropdown')?.classList.remove('active');
    
    console.log(`Applied filters: ${Object.values(filterState).filter(arr => arr.length > 0).length} active filters, ${filteredEvents.length} results`);
}

// Clear all filters
function clearFilters() {
    // Reset filter state
    filterState = {
        country: [],
        visaType: [],
        affectedGroups: [],
        changeType: []
    };
    
    // Uncheck all checkboxes
    const allCheckboxes = document.querySelectorAll('.checkbox-list input[type="checkbox"]');
    allCheckboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    
    // Display all data
    displayFilteredData(allEventsData);
    
    // Close the dropdown
    document.getElementById('filterDropdown')?.classList.remove('active');
    
    console.log('Cleared all filters');
}

// Display filtered data
function displayFilteredData(events) {
    const dataRowsContainer = document.getElementById('dataRows');
    if (!dataRowsContainer) return;
    
    if (events.length === 0) {
        dataRowsContainer.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">No results match the selected filters.</div>';
        updatePaginationInfo(0);
        updateWeeklyBadge(0);
        return;
    }
    
    // Update pagination info
    const paginationInfo = updatePaginationInfo(events.length);
    
    // Calculate pagination for current page
    const startIndex = (currentPaginationState.currentPage - 1) * paginationInfo.recordsPerPage;
    const endIndex = startIndex + paginationInfo.recordsPerPage;
    const pageData = events.slice(startIndex, endIndex);
    
    // Calculate weekly updates from filtered data
    const weeklyCount = calculateUpdatesThisWeek(events);
    updateWeeklyBadge(weeklyCount);
    
    // Create data rows
    const rowsHTML = pageData.map(event => createDataRow(event)).join('');
    dataRowsContainer.innerHTML = rowsHTML;
}
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

// Get country flag and display name
function getCountryFlag(country) {
    return countryFlags[country] || '🌍'; // Default globe emoji if country not found
}

function getCountryDisplayName(country) {
    if (country === 'United States') {
        return 'US';
    }
    return country;
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

// Create data row HTML
function createDataRow(event) {
    const flag = getCountryFlag(event.country);
    const countryDisplay = getCountryDisplayName(event.country);
    const severity = event.severity ? event.severity.toLowerCase() : 'medium'; // Use API severity data
    const timestamp = formatTimestamp(event.timestamp);
    const effectiveDate = formatEffectiveDate(event.effective_date);
    
    // Create unique ID for this row's expand button
    const rowId = `row-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    return `
        <div class="data-row">
            <div class="data-cell country">${flag} ${countryDisplay}</div>
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
                <a href="${event.source}" target="_blank" class="sources-link">Link</a>
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
    if (recordedUpdatesElement && totalRecords > 0) {
        recordedUpdatesElement.textContent = `${totalRecords} recorded updates`;
        recordedUpdatesElement.style.display = 'block';
    }
    
    // Update "of X pages" text
    const pagesTextElement = document.querySelector('.pages-text');
    if (pagesTextElement && totalRecords > 0) {
        pagesTextElement.textContent = `of ${totalPages} pages`;
        pagesTextElement.style.display = 'block';
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
    console.log('Previous page clicked. Current page:', currentPaginationState.currentPage, 'Total pages:', currentPaginationState.totalPages);
    if (currentPaginationState.currentPage > 1) {
        console.log('Navigating to page:', currentPaginationState.currentPage - 1);
        navigateToPage(currentPaginationState.currentPage - 1);
    } else {
        console.log('Already on first page');
    }
}

// Navigate to next page
function navigateToNextPage() {
    console.log('Next page clicked. Current page:', currentPaginationState.currentPage, 'Total pages:', currentPaginationState.totalPages);
    if (currentPaginationState.currentPage < currentPaginationState.totalPages) {
        console.log('Navigating to page:', currentPaginationState.currentPage + 1);
        navigateToPage(currentPaginationState.currentPage + 1);
    } else {
        console.log('Already on last page');
    }
}

// Add pagination event listeners
function setupPaginationEventListeners() {
    const leftArrow = document.querySelector('.left-arrow');
    const rightArrow = document.querySelector('.right-arrow');
    
    console.log('Setting up pagination listeners. Left arrow:', leftArrow, 'Right arrow:', rightArrow);
    
    if (leftArrow) {
        leftArrow.addEventListener('click', navigateToPreviousPage);
        console.log('Added click listener to left arrow');
    }
    
    if (rightArrow) {
        rightArrow.addEventListener('click', navigateToNextPage);
        console.log('Added click listener to right arrow');
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
    console.log(`updateWeeklyBadge called with count: ${count}`); // Debug log
    
    const badgeElement = document.getElementById('updatesThisWeekCount');
    const badgeTextElement = document.querySelector('#updatesThisWeekBadge .badge-text');
    
    console.log('Badge element:', badgeElement); // Debug log
    console.log('Badge text element:', badgeTextElement); // Debug log
    
    if (badgeElement) {
        badgeElement.textContent = count;
        console.log(`Set badge number to: ${count}`); // Debug log
    }
    
    if (badgeTextElement) {
        // Use singular "Update" for 1, plural "Updates" for everything else
        const updateText = count === 1 ? 'Update this week' : 'Updates this week';
        badgeTextElement.textContent = updateText;
        console.log(`Set badge text to: "${updateText}"`); // Debug log
    } else {
        console.log('Badge text element not found!'); // Debug log
    }
}

// Load dashboard data from API
async function loadDashboardData(page = 1) {
    console.log('loadDashboardData called with page:', page);
    
    // Wait a bit to ensure DOM is ready
    await new Promise(resolve => setTimeout(resolve, 100));
    
    const dataRowsContainer = document.getElementById('dataRows');
    const loadingState = document.getElementById('loadingState');
    
    console.log('dataRowsContainer:', dataRowsContainer);
    console.log('loadingState:', loadingState);
    
    // Check if elements exist
    if (!dataRowsContainer) {
        console.error('dataRows element not found');
        return;
    }
    
    if (!loadingState) {
        console.error('loadingState element not found');
        // Try to create a simple loading indicator
        dataRowsContainer.innerHTML = '<div style="text-align: center; padding: 20px;">Loading...</div>';
    }
    
    try {
        // Show loading state if it exists
        if (loadingState) {
            loadingState.style.display = 'block';
        }
        
        // API URL - use Railway backend in production, local in development
        const API_BASE = window.location.hostname === 'localhost' 
            ? '' 
            : 'https://web-production-cc3f1.up.railway.app';
        
        const response = await fetch(`${API_BASE}/api/history`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success && result.data && result.data.length > 0) {
            // Store all events data for filtering
            allEventsData = result.data;
            
            // Populate filter dropdowns with unique values
            populateFilterDropdowns(allEventsData);
            
            // Hide loading state
            if (loadingState) {
                loadingState.style.display = 'none';
            }
            
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
            if (loadingState) {
                loadingState.innerHTML = '<p>No policy updates available at the moment.</p>';
            } else {
                dataRowsContainer.innerHTML = '<p>No policy updates available at the moment.</p>';
            }
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
    
    // Check if elements exist
    if (!dataRowsContainer) {
        console.error('dataRows element not found in loadSampleData');
        return;
    }
    
    if (!loadingState) {
        console.error('loadingState element not found in loadSampleData');
        return;
    }
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
            effective_date: null  // No specific effective date calculated
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
            effective_date: null  // No specific effective date calculated
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
            effective_date: null  // No specific effective date calculated
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
            effective_date: "2026-01-01T00:00:00+00:00"  // Fee changes typically have future effective dates
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
            effective_date: null  // Processing updates typically effective immediately (no specific date)
        }
    ];
    
    // Store sample data for filtering
    allEventsData = sampleData;
    
    // Populate filter dropdowns with sample data
    populateFilterDropdowns(allEventsData);
    
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