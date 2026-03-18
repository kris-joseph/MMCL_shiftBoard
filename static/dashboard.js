/**
 * MMCL Staff Dashboard - Client-side Interactions
 * Phase 1: Basic collapsible sections and UI enhancements
 * Phase 2: Interactive workflow state management
 */

(function() {
  'use strict';

  /**
   * Initialize collapsible sections
   */
  function initCollapsibles() {
    const toggles = document.querySelectorAll('.collapse-toggle');

    toggles.forEach(toggle => {
      toggle.addEventListener('click', function() {
        const targetId = this.getAttribute('data-target');
        const content = document.getElementById(targetId);
        const isExpanded = this.getAttribute('aria-expanded') === 'true';

        // Toggle state
        this.setAttribute('aria-expanded', !isExpanded);
        content.classList.toggle('open');

        // Update button text
        const textSpan = this.querySelector('span:first-child');
        if (textSpan) {
          textSpan.textContent = isExpanded ? 'Show completed bookings' : 'Hide completed bookings';
        }
      });
    });
  }

  /**
   * Update current time indicator in timeline
   */
  function updateTimelineIndicator() {
    const now = new Date();
    const currentHour = now.getHours();

    // Highlight current hour in timeline
    const timelineHours = document.querySelectorAll('.timeline-hour');
    timelineHours.forEach(hourElement => {
      const label = hourElement.querySelector('.timeline-hour-label');
      if (label) {
        const hourText = label.textContent.trim();
        const hour = parseInt(hourText.replace(/[^\d]/g, ''), 10);

        // Mark as current hour
        if (hour === currentHour || (hourText.includes('PM') && hour + 12 === currentHour)) {
          hourElement.classList.add('current-hour');
        }
      }
    });
  }

  /**
   * Add ARIA labels for accessibility
   */
  function enhanceAccessibility() {
    // Add aria-labels to booking cards for screen readers
    const bookingCards = document.querySelectorAll('.booking-card');
    bookingCards.forEach(card => {
      const title = card.querySelector('h3');
      const time = card.querySelector('.detail-value');
      if (title && time) {
        card.setAttribute('aria-label', `Booking: ${title.textContent} at ${time.textContent}`);
      }
    });
  }

  /**
   * Auto-refresh notification
   * Show a subtle notification when page is about to refresh
   */
  function initAutoRefreshNotification() {
    // Page refreshes every 5 minutes (300 seconds)
    // Show notification 10 seconds before refresh
    const refreshInterval = 300000; // 5 minutes in ms
    const notificationTime = refreshInterval - 10000; // Show 10s before

    setTimeout(() => {
      console.log('Dashboard will refresh in 10 seconds...');
      // Could add a visual notification here in Phase 2
    }, notificationTime);
  }

  /**
   * Highlight overdue items with animation
   */
  function highlightOverdueItems() {
    const overdueCards = document.querySelectorAll('.booking-card.overdue');
    overdueCards.forEach(card => {
      card.style.animation = 'pulse 2s ease-in-out infinite';
    });
  }

  /**
   * Add CSS for pulse animation dynamically
   */
  function addPulseAnimation() {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.85; }
      }
    `;
    document.head.appendChild(style);
  }

  /**
   * Format relative times (e.g., "Starting in 15 minutes")
   * Phase 1: Display only
   * Phase 2: Update dynamically
   */
  function addRelativeTimeHints() {
    const now = new Date();
    const bookingCards = document.querySelectorAll('.booking-card');

    bookingCards.forEach(card => {
      const timeValue = card.querySelector('.detail-value');
      if (timeValue && timeValue.textContent.includes('-')) {
        const [startTime] = timeValue.textContent.split('-');
        // Future enhancement: parse and calculate relative time
        // For Phase 1, we leave this for Phase 2 implementation
      }
    });
  }

  /**
   * Print-friendly view
   */
  function enhancePrintView() {
    window.addEventListener('beforeprint', () => {
      // Expand all collapsed sections before printing
      const collapsedSections = document.querySelectorAll('.collapse-content:not(.open)');
      collapsedSections.forEach(section => {
        section.classList.add('open', 'print-expanded');
      });
    });

    window.addEventListener('afterprint', () => {
      // Collapse sections that were expanded for printing
      const printExpanded = document.querySelectorAll('.collapse-content.print-expanded');
      printExpanded.forEach(section => {
        section.classList.remove('open', 'print-expanded');
      });
    });
  }

  /**
   * Keyboard navigation enhancements
   */
  function enhanceKeyboardNav() {
    // Allow Enter/Space to toggle collapsible sections
    const toggles = document.querySelectorAll('.collapse-toggle');
    toggles.forEach(toggle => {
      toggle.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.click();
        }
      });
    });
  }

  /**
   * Toggle booking card expanded/collapsed state
   * Called from onclick in template
   */
  window.toggleBookingCard = function(headerBar) {
    const card = headerBar.closest('.booking-card');
    card.classList.toggle('expanded');
  };

  /**
   * Toggle hour group expanded/collapsed state
   * Called from onclick in template
   */
  window.toggleHourGroup = function(header) {
    const group = header.closest('.hour-group');
    const content = group.querySelector('.hour-group-content');
    const isCollapsed = content.classList.contains('collapsed');
    if (isCollapsed) {
      content.classList.remove('collapsed');
      group.classList.add('expanded');
    } else {
      content.classList.add('collapsed');
      group.classList.remove('expanded');
    }
  };

  /**
   * Expand all booking cards
   */
  function expandAllBookings() {
    const cards = document.querySelectorAll('.booking-card');
    cards.forEach(card => card.classList.add('expanded'));
  }

  /**
   * Collapse all booking cards
   */
  function collapseAllBookings() {
    const cards = document.querySelectorAll('.booking-card');
    cards.forEach(card => card.classList.remove('expanded'));
  }

  /**
   * Filter bookings by type or station
   * Works for both media lab (booking-type) and makerspace (station-type)
   */
  window.filterBookings = function(filterType) {
    const allCards = document.querySelectorAll('.booking-card');
    const buttons = document.querySelectorAll('.filter-button');

    // Update button states
    buttons.forEach(btn => {
      if (btn.dataset.filter === filterType) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Filter cards
    allCards.forEach(card => {
      // Use station-type if available (makerspace), otherwise booking-type (media lab)
      const cardType = card.dataset.stationType || card.dataset.bookingType;

      if (filterType === 'all') {
        // Show all cards
        card.classList.remove('filter-hidden');
      } else if (cardType === filterType) {
        // Show matching cards
        card.classList.remove('filter-hidden');
      } else {
        // Hide non-matching cards
        card.classList.add('filter-hidden');
      }
    });

    // Hide hour groups whose cards are all filtered out
    document.querySelectorAll('.hour-group').forEach(group => {
      const content = group.querySelector('.hour-group-content');
      if (!content) return;
      const visibleCards = content.querySelectorAll('.booking-card:not(.filter-hidden)').length;
      if (visibleCards === 0 && filterType !== 'all') {
        group.classList.add('filter-hidden');
      } else {
        group.classList.remove('filter-hidden');
      }
    });

    console.log(`Filter applied: ${filterType}`);
  };

  /**
   * Initialize filter buttons
   */
  function initFilters() {
    // Set default active state
    const allButton = document.querySelector('.filter-button[data-filter="all"]');
    if (allButton) {
      allButton.classList.add('active');
    }
  }

  // ─── Workflow Checklist ────────────────────────────────────────────────────

  function workflowStorageKey(bookingId) {
    return 'mmcl_steps_' + bookingId;
  }

  function loadCheckedSteps(bookingId) {
    try {
      const saved = localStorage.getItem(workflowStorageKey(bookingId));
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      return [];
    }
  }

  function saveCheckedSteps(bookingId, checkedSteps) {
    try {
      localStorage.setItem(workflowStorageKey(bookingId), JSON.stringify(checkedSteps));
    } catch (e) { /* localStorage unavailable — silent fail */ }
  }

  function updateWorkflowProgress(card) {
    const checkboxes = card.querySelectorAll('.step-checkbox');
    if (!checkboxes.length) return;

    const total = checkboxes.length;
    const checked = Array.from(checkboxes).filter(cb => cb.checked).length;
    const pct = (checked / total) * 100;

    // Header bar progress fill (collapsible cards)
    const headerFill = card.querySelector('.workflow-header-progress-fill');
    if (headerFill) headerFill.style.width = pct + '%';

    // Inline progress fill (always-expanded in-progress job cards)
    const inlineFill = card.querySelector('.workflow-inline-progress-fill');
    if (inlineFill) inlineFill.style.width = pct + '%';

    // Step counter "X / N"
    const counter = card.querySelector('.workflow-step-counter');
    if (counter) counter.textContent = checked;
  }

  window.onStepChecked = function(checkbox) {
    const stepItem = checkbox.closest('.workflow-step');
    const card = checkbox.closest('.booking-card');
    if (!stepItem || !card) return;

    stepItem.classList.toggle('step-completed', checkbox.checked);
    updateWorkflowProgress(card);

    const bookingId = card.dataset.bookingId;
    if (bookingId) {
      const checkedSteps = Array.from(card.querySelectorAll('.step-checkbox'))
        .filter(cb => cb.checked)
        .map(cb => parseInt(cb.dataset.step, 10));
      saveCheckedSteps(bookingId, checkedSteps);
    }
  };

  function initWorkflowCheckboxes() {
    document.querySelectorAll('.booking-card[data-booking-id]').forEach(card => {
      const bookingId = card.dataset.bookingId;
      const saved = loadCheckedSteps(bookingId);
      if (!saved.length) return;

      card.querySelectorAll('.step-checkbox').forEach(checkbox => {
        if (saved.includes(parseInt(checkbox.dataset.step, 10))) {
          checkbox.checked = true;
          checkbox.closest('.workflow-step').classList.add('step-completed');
        }
      });
      updateWorkflowProgress(card);
    });
  }

  // ─────────────────────────────────────────────────────────────────────────────

  /**
   * Initialize dashboard on page load
   */
  function init() {
    console.log('MMCL Dashboard initialized');

    // Start with all cards collapsed
    collapseAllBookings();

    // Core functionality
    initCollapsibles();
    initFilters();
    initWorkflowCheckboxes();
    enhanceAccessibility();
    enhanceKeyboardNav();
    enhancePrintView();

    // Visual enhancements
    addPulseAnimation();
    updateTimelineIndicator();
    highlightOverdueItems();

    // Auto-refresh
    initAutoRefreshNotification();

    // Debug info
    const bookingCount = document.querySelectorAll('.booking-card').length;
    console.log(`Displaying ${bookingCount} bookings`);
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
