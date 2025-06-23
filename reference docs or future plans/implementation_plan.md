# Implementation Plan for Work Order Management Enhancements

This plan outlines the steps to address the work order display issue, implement new assignment logic (sorting and reshuffling), and track work order completion by produced quantity.

### **Phase 1: Frontend Work Order Display Debugging**

**Goal:** Ensure the fetched work orders are correctly displayed on the "Work Orders" page.

**Steps:**

1.  **Examine `frontend/work-orders.html`:**
    *   Review the HTML structure to understand how the work order list is intended to be rendered. Look for elements that are dynamically populated.
2.  **Examine `frontend/js/work-orders.js`:**
    *   Review the JavaScript code responsible for fetching data from `/api/work-orders` and inserting it into the HTML.
    *   Specifically, I will look at:
        *   The `fetch` call and how the response is handled.
        *   The parsing of the JSON data (`Work_order_list`).
        *   The DOM manipulation logic that creates and appends work order entries.
        *   Any client-side filtering or sorting that might be preventing display.

### **Phase 2: Implement Modular Assignment & Scheduling Logic**

**Goal:** Create a new module to centralize and manage all work order assignment, sorting, reordering, and completion tracking logic.

**New Module: `assignment_manager.py`**

This new module will be responsible for:

*   **Initial Work Order Sorting:** Implementing the default sorting logic (by `machine_no`, then `work_order_date`, then `work_order_no`) when fetching available work orders.
*   **Managing Custom Order:** Storing and retrieving the user-defined custom sequence of work orders for a machine.
*   **Work Order Assignment/Deassignment:** Handling the logic for assigning and de-assigning work orders to machines, including updating the custom sequence.
*   **Tracking Completion:** Calculating and updating the completion status of work orders based on produced quantity.
*   **Interacting with `db_handler.py`:** This module will call `db_handler.py` functions to perform database CRUD operations, but the business logic for *what* data to retrieve or update, and *how* to process it, will reside here.

**Backend Changes (`db_handler.py`, `api.py`, and `assignment_manager.py`):**

1.  **Modify `db_handler.save_work_orders`:**
    *   **Date Conversion:** The `date` field from NetSuite is "DD/MM/YYYY". I will add logic to convert this string to "YYYY-MM-DD" format before saving it to the `work_order_date` column in the `work_orders` table. This ensures that database-level sorting works correctly.

2.  **Database Schema Update (`machine_assignments` table and `work_orders` table):**
    *   **`machine_assignments` table:** Add a new column, e.g., `assigned_work_order_sequence` (TEXT or JSON), to store the ordered list of work order IDs for a given machine. This will be a comma-separated string of IDs or a JSON array.
    *   **`work_orders` table:** Add a column `produced_quantity` (FLOAT, DEFAULT 0.0) to track the quantity produced against a work order.

3.  **Refactor `db_handler.get_available_work_orders`:**
    *   This function will now primarily fetch raw work order data. The sorting logic will be moved to `assignment_manager.py`.

4.  **New Functions in `db_handler.py`:**
    *   `get_work_orders_by_ids(list_of_ids)`: A new function to fetch specific work orders by their IDs, which will be used by `assignment_manager.py` to retrieve work orders in a custom sequence.
    *   `update_work_order_produced_quantity(work_order_id, quantity_produced)`: To update the `produced_quantity` for a work order.

5.  **Modify `api.py` endpoints:**
    *   **`get_work_orders_endpoint`:** This endpoint will now call `assignment_manager.get_sorted_available_work_orders()` to get the initially sorted list.
    *   **`get_dashboard_data`:** This endpoint will call `assignment_manager.get_machine_assignments_with_ordered_work_orders()` to retrieve assignments with work orders ordered by the custom sequence.
    *   **`update_machine_assignment`:** This endpoint will call `assignment_manager.assign_work_order_to_machine()` which will handle updating the `assigned_work_order_sequence`.
    *   **New API Endpoint (`api.py`):**
        *   Create a new endpoint, e.g., `PUT /api/machine-assignments/{machine_id}/reorder`, that accepts a list of work order IDs in the desired sequence. This endpoint will call `assignment_manager.reorder_assigned_work_orders()`.
    *   **Update MQTT Processing:** When a coil is produced, the `mqtt_service.py` will call `assignment_manager.track_production()` which will update the `produced_quantity` in the database and check for work order completion.

**Frontend Changes (`frontend/operations.html`, `frontend/js/operations.js`, `frontend/js/work-orders.js`):**

1.  **Update Work Order Selection in Assignment Modal:**
    *   In `frontend/js/operations.js`, the dropdown will be populated with work orders received from the backend, which will be initially sorted by `assignment_manager.py`.
2.  **Implement Drag-and-Drop UI:**
    *   In `frontend/operations.html`, for each machine's assigned work orders, implement a UI component that allows drag-and-drop reordering (e.g., using a JavaScript library like SortableJS or jQuery UI Sortable).
    *   This UI will display the work orders in the order received from the backend (which will be the custom order if one exists, or the default sorted order).
3.  **Update `frontend/js/operations.js`:**
    *   **Fetch Custom Order:** When loading the operations page, fetch the `assigned_work_order_sequence` along with other assignment data.
    *   **Render with Custom Order:** Use the fetched sequence to render the work orders for each machine in the specified custom order.
    *   **Handle Reordering Events:** When a user reorders work orders via the UI, capture the new sequence of work order IDs.
    *   **Send Update to Backend:** Make an API call to the new `PUT /api/machine-assignments/{machine_id}/reorder` endpoint, sending the updated list of work order IDs.
    *   **Update UI:** Refresh the UI to reflect the saved order.
4.  **Display Completion Status:** Update the frontend to display the `produced_quantity` and a completion status (e.g., a percentage or a "Completed" flag) for each work order.

### **Mermaid Diagram for Modular Work Order Flow:**

```mermaid
graph TD
    subgraph "Backend"
        API_Endpoints["FastAPI (api.py)"]
        Assignment_Manager["AssignmentManager (assignment_manager.py)"]
        DB_Handler["DB Handler (db_handler.py)"]
        MQTT_Service["MQTT Service (mqtt_service.py)"]
    end

    subgraph "Frontend"
        WO_Page["Work Orders Page (work-orders.html)"]
        Operations_Page["Live Operations Page (operations.html)"]
        Assignment_Modal["Assign Work Order Modal"]
        Reorder_UI["Drag-and-Drop Reorder UI"]
    end

    subgraph "External"
        NetSuite["NetSuite ERP"]
        PLCs["PLCs / Autocoilers"]
        MQTT_Broker["MQTT Broker"]
    end

    NetSuite -- "Fetch Work Orders (DD/MM/YYYY date)" --> DB_Handler
    DB_Handler -- "Converts Date & Stores/Updates" --> Database["SQLite Database"]

    API_Endpoints -- "GET /work-orders" --> Assignment_Manager
    Assignment_Manager -- "Gets raw WOs" --> DB_Handler
    DB_Handler -- "Returns raw WOs" --> Assignment_Manager
    Assignment_Manager -- "Sorts WOs (Machine No, Date, WO No)" --> API_Endpoints
    API_Endpoints -- "Sends Sorted List" --> WO_Page

    Operations_Page -- "Loads Machine Assignments" --> API_Endpoints
    API_Endpoints -- "GET /dashboard-data" --> Assignment_Manager
    Assignment_Manager -- "Gets assignments & WOs by sequence" --> DB_Handler
    DB_Handler -- "Returns data" --> Assignment_Manager
    Assignment_Manager -- "Returns ordered assignments" --> API_Endpoints
    API_Endpoints -- "Sends ordered assignments" --> Operations_Page

    Operations_Page -- "Triggers 'Assign WO' Modal" --> Assignment_Modal
    Assignment_Modal -- "Populates dropdown with default sorted list" --> Operations_Page
    Assignment_Modal -- "User Selects WO & Assigns" --> API_Endpoints
    API_Endpoints -- "POST /update-assignment" --> Assignment_Manager
    Assignment_Manager -- "Updates assigned_work_order_id & sequence" --> DB_Handler
    DB_Handler -- "Updates DB" --> Database

    Operations_Page -- "Displays WOs in custom order" --> Reorder_UI
    Reorder_UI -- "User reorders WOs" --> Operations_Page
    Operations_Page -- "Sends new sequence" --> API_Endpoints
    API_Endpoints -- "PUT /api/machine-assignments/{machine_id}/reorder" --> Assignment_Manager
    Assignment_Manager -- "Updates assigned_work_order_sequence" --> DB_Handler
    DB_Handler -- "Updates DB" --> Database

    PLCs -- "Publish Production Data" --> MQTT_Broker
    MQTT_Broker -- "Sends Data" --> MQTT_Service
    MQTT_Service -- "Processes Message" --> Assignment_Manager
    Assignment_Manager -- "Updates produced_quantity & checks completion" --> DB_Handler
    DB_Handler -- "Updates DB" --> Database
    Assignment_Manager -- "Triggers Label Print" --> Label_Printer["Label Printer (label_printer.py)"]
    Label_Printer -- "Prints Label" --> Printer["Label Printer Hardware"]