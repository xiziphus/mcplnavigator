# Frontend Refactor Implementation Plan

## 1. Overview

This document outlines the plan to refactor the frontend of the MCPL Production Dashboard. The goal is to move from an unreliable script loading mechanism to a stable, modular architecture. This will resolve `ReferenceError` issues and improve code organization and maintainability.

## 2. New Frontend Architecture

The new architecture will be based on a centralized application shell (`index.html`) that dynamically loads view-specific HTML and JavaScript.

### 2.1. New File Structure

The `frontend` directory will be reorganized as follows. This structure separates HTML templates from their corresponding JavaScript logic and introduces a shared JavaScript file.

```
frontend/
├── js/
│   ├── common.js         # Shared functions (e.g., fetchData)
│   ├── dashboard.js      # Logic for dashboard.html
│   ├── operations.js     # Logic for operations.html
│   ├── work-orders.js    # Logic for work-orders.html
│   ├── production-log.js # Logic for production-log.html
│   ├── analytics.js      # Logic for analytics.html
│   └── admin.js          # Logic for admin.html
├── index.html            # Main application shell
├── dashboard.html        # Dashboard view (HTML only)
├── operations.html       # Operations view (HTML only)
├── work-orders.html      # Work Orders view (HTML only)
├── production-log.html   # Production Log view (HTML only)
├── analytics.html        # Analytics view (HTML only)
└── admin.html            # Admin view (HTML only)
```

### 2.2. `index.html` Modifications

The core of the refactor lies in modifying `frontend/index.html` to handle dynamic page loading correctly.

#### 2.2.1. New `loadPage` Function

The existing `loadPage` function will be replaced with a new version that reliably loads and executes scripts.

```javascript
async function loadPage(pageId) {
    // Remove any previously loaded view-specific script
    const oldScript = document.getElementById('view-script');
    if (oldScript) {
        oldScript.remove();
    }

    try {
        // 1. Fetch the HTML content for the view
        const response = await fetch(`${pageId}.html`);
        if (!response.ok) {
            contentDivs[pageId].innerHTML = `<h2>Error: Could not load page.</h2>`;
            return;
        }
        const content = await response.text();

        // 2. Inject the fetched HTML into the main content area
        contentDivs[pageId].innerHTML = content;

        // 3. Dynamically create and append the corresponding script tag
        const script = document.createElement('script');
        script.id = 'view-script'; // Assign an ID for easy removal later
        script.src = `js/${pageId}.js`;
        script.defer = true; // Ensure script executes after the DOM is parsed
        script.onload = () => {
            // After the script is loaded, execute the specific page's initialization function
            if (window.pageLoadFunctions && window.pageLoadFunctions[pageId]) {
                window.pageLoadFunctions[pageId]();
            }
        };
        document.body.appendChild(script);

    } catch (error) {
        console.error('Error loading page:', error);
        contentDivs[pageId].innerHTML = `<h2>Error: Could not load page.</h2>`;
    }
}
```

#### 2.2.2. Shared Code (`common.js`)

A new file, `frontend/js/common.js`, will be created to house shared functions. The primary candidate for this is the `fetchData` function. `index.html` will load this script directly.

**`frontend/js/common.js` content:**
```javascript
const API_BASE_URL = 'http://127.0.0.1:3003/api';

async function fetchData(endpoint, options = {}) {
    const token = localStorage.getItem('access_token');
    if (!token) {
        console.error('No access token found. Please log in.');
        // Assuming showLogin is globally available from index.html
        if (window.showLogin) {
            window.showLogin();
        }
        return null;
    }

    options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${token}`
    };

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        if (!response.ok) {
            if (response.status === 401) {
                alert('Session expired or unauthorized. Please log in again.');
                if (window.showLogin) {
                    window.showLogin();
                }
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Error fetching data from ${endpoint}:`, error);
        return null;
    }
}
```

**`index.html` script loading:**
`index.html` should include `common.js` in its `<head>` or `<body>` so `fetchData` is available globally.

```html
<!-- In index.html, before the main script block -->
<script src="js/common.js"></script>
```

## 3. Implementation Steps for `code` Mode

The following is a step-by-step guide for the `code` mode to execute this refactor.

### Step 1: Create `frontend/js/common.js`

1.  Create a new file at `frontend/js/common.js`.
2.  Add the `fetchData` function (as defined in section 2.2.2) to this file.

### Step 2: Update `frontend/index.html`

1.  Add a `<script>` tag to load `frontend/js/common.js`.
2.  Replace the existing `loadPage` function with the new implementation from section 2.2.1.
3.  Remove the `fetchData` function from the main script block in `index.html` as it's now in `common.js`.
4.  Move the page-specific load functions (e.g., `loadDashboardData`, `loadOperationsData`) into a global `window.pageLoadFunctions` object so they can be called from the `onload` event of the dynamically loaded scripts.

### Step 3: Create View-Specific JavaScript Files

For each of the following HTML files, create a corresponding JavaScript file in the `frontend/js/` directory:
- `dashboard.html` -> `dashboard.js`
- `operations.html` -> `operations.js`
- `work-orders.html` -> `work-orders.js`
- `production-log.html` -> `production-log.js`
- `analytics.html` -> `analytics.js`
- `admin.html` -> `admin.js`

### Step 4: Migrate and Refactor Scripts

For each view:

1.  **Identify** the JavaScript code within the `<script>` tags of the HTML file (e.g., `frontend/dashboard.html`).
2.  **Move** this logic into the corresponding new JavaScript file (e.g., `frontend/js/dashboard.js`).
3.  **Refactor** the moved code. The code should be wrapped in an initialization function that will be added to the `window.pageLoadFunctions` object. For example, in `dashboard.js`:

    ```javascript
    // In frontend/js/dashboard.js
    if (!window.pageLoadFunctions) {
        window.pageLoadFunctions = {};
    }

    window.pageLoadFunctions.dashboard = function() {
        // All the original script content from dashboard.html goes here.
        // For example:
        async function loadDashboardData() {
            const data = await fetchData('/dashboard-data');
            if (data) {
                updateKPIs(data.assignments);
                updateAssignmentsTable(data.assignments);
            }
        }

        function updateKPIs(assignments) {
            // ... implementation
        }

        function updateAssignmentsTable(assignments) {
            // ... implementation
        }

        // Initial call
        loadDashboardData();
    };
    ```
4.  **Remove** the entire `<script>` block from the original HTML file (e.g., `frontend/dashboard.html`). The file should now only contain HTML structure.
5.  **Repeat** this process for all views listed in Step 3.

## 4. Conclusion

Following this plan will result in a more robust, maintainable, and performant frontend. It establishes a clear separation of concerns and a scalable pattern for adding new features.