
## Master Requirements Specification Document

---

## Document Authority and Version Control
- **Document Version:** 2.0 - MASTER SPECIFICATION
- **Date:** June 28, 2025
- **Author:** MES Development Team
- **Review Status:** APPROVED FOR IMPLEMENTATION
- **Authority Level:** SUPERSEDES ALL PREVIOUS MESWO DOCUMENTATION

### ⚠️ **CRITICAL NOTICE**
**This document is the DEFINITIVE and AUTHORITATIVE specification for all MESWO functionality. It supersedes and overrides any previous MESWO instructions, requirements, or documentation found in the codebase, project context, or related documents. All development, testing, and deployment must conform to THIS specification only.**

### Version History
- **v1.0:** Initial MESWO requirements (DEPRECATED)
- **v2.0:** Master specification with security, analytics, and lifecycle management (CURRENT)

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Key Definitions](#key-definitions)
4. [Work Order Hierarchy](#work-order-hierarchy)
5. [MESWO Creation Logic](#meswo-creation-logic)
6. [Production Execution Rules](#production-execution-rules)
7. [Changeover Management](#changeover-management)
8. [Security and Access Control](#security-and-access-control)
9. [MESWO Lifecycle Management](#meswo-lifecycle-management)
10. [Data Collection and Analytics](#data-collection-and-analytics)
11. [NetSuite Integration](#netsuite-integration)
12. [User Interface Requirements](#user-interface-requirements)
13. [Configuration Management](#configuration-management)
14. [System Integration and Tracking](#system-integration-and-tracking)
15. [Success Criteria](#success-criteria)
16. [Implementation Timeline](#implementation-timeline)
17. [Risk Management and Mitigation](#risk-management-and-mitigation)
18. [Appendix](#appendix)

---

## 1. Executive Summary

The MCPL Manufacturing Execution System (MES) implements a sophisticated two-tier work order management system that optimizes production efficiency while maintaining delivery commitments. The system automatically consolidates NetSuite Work Orders (NSWOs) into Manufacturing Execution System Work Orders (MESWOs) based on delivery dates and changeover optimization, then executes production with minimal manual intervention.

### 1.1 Key Principles
- **Delivery First:** Work orders grouped by delivery date to ensure customer commitments
- **Efficiency Second:** Within date groups, optimize for minimum changeover time
- **Automatic Execution:** Seamless progression through work order sequences
- **Complete Traceability:** Full production lineage from raw materials to finished products
- **Intelligent Analytics:** Data-driven continuous improvement

---

## 2. System Overview

### 2.1 Architecture Components
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   NetSuite ERP  │    │   MCPL MES      │    │  Shop Floor     │
│                 │    │                 │    │                 │
│ • Work Orders   │◄───┤ • MESWO Engine  │───►│ • 5 Autocoilers │
│ • BOM Data      │    │ • Production    │    │ • MQTT Broker   │
│ • Status Sync   │    │   Control       │    │ • Label Printer │
└─────────────────┘    │ • Analytics     │    └─────────────────┘
                       └─────────────────┘
```

### 2.2 Data Flow Overview
1. **Input:** NetSuite work orders fetched via RESTlet API
2. **Processing:** Automatic MESWO creation with optimization algorithms
3. **Execution:** Real-time production monitoring via MQTT
4. **Output:** Label printing, quality tracking, NetSuite status updates

---

## 3. Key Definitions

### 3.1 Work Order Types

**NetSuite Work Order (NSWO)**
- Individual customer orders from NetSuite ERP
- Contains: Part code, quantity, delivery date, BOM data
- Represents single customer requirement

**Manufacturing Execution System Work Order (MESWO)**
- Container for multiple related NSWOs
- Optimized for production efficiency
- Executes as atomic production unit

### 3.2 MCPL Part Code Structure
**Format:** `[Wire Spec][Insulation][Gauge][Color 1][Color 2]` (11 characters)

**Example:** `M04A0141818`
- **M04:** Wire Specification (FLRY-B T2)
- **A0:** Insulation (PVC NORMAL T2)
- **14:** Gauge (0.50 mm²)
- **18:** Primary Color (RED 3000-PVC)
- **18:** Secondary Color (RED 3000-PVC) = solid color

### 3.3 Changeover Types
**Copper Changeover** (Longest Duration)
- Determined by BOM analysis
- Requires complete material change
- Estimated time: 15-25 minutes

**PVC/Insulation Changeover** (Medium Duration)
- Based on characters 4-5 of part code
- Different insulation types or grades
- Estimated time: 5-12 minutes

**Color Changeover** (Shortest Duration)
- Based on characters 8-11 of part code
- Color masterbatch changes only
- Estimated time: 1-5 minutes

---

## 4. Work Order Hierarchy

### 4.1 Relationship Structure
```
MESWO (Manufacturing Execution System Work Order)
├── NSWO 1 (NetSuite Work Order)
├── NSWO 2 (NetSuite Work Order)
├── NSWO 3 (NetSuite Work Order)
└── NSWO N (NetSuite Work Order)
```

### 4.2 MESWO Naming Convention
**Standard Format:** `MESWO-{MACHINE_ID}-{YYYYMMDD}-{SEQUENCE}`
**Split MESWO Format:** `MESWO-{MACHINE_ID}-{YYYYMMDD}-{SEQUENCE}-{SPLIT_TYPE}`
**Cross-Machine Format:** `MESWO-POOL-{YYYYMMDD}-{SEQUENCE}` (when in pool, no specific machine)

**Examples:**
- `MESWO-1-20250617-001` (First MESWO for Machine 1 on June 17, 2025)
- `MESWO-POOL-20250617-001` (MESWO in pool, originally created for June 17)
- `MESWO-1-20250617-001-CONT` (Continuation MESWO after split)
- `MESWO-1-20250617-001-DEFER` (Deferred MESWO after split)
- `MESWO-URGENT-20250617-001` (Urgent MESWO with immediate priority)

**Naming Rules:**
- Machine-specific IDs only when actively assigned to machine
- Pool-based naming when MESWO is unassigned or paused
- Split suffixes (-CONT, -DEFER) preserve original sequence relationship
- URGENT prefix for customer-escalated priority MESWOs

---

## 5. MESWO Creation Logic

### 5.1 Primary Grouping Rules

**Rule 1: Date-First Grouping**
- All work orders grouped by `work_order_date` (delivery commitment)
- No cross-date optimization allowed
- Delivery commitments take absolute priority

**Rule 2: Efficiency Optimization Within Dates**
Within each date group, optimize by:
1. **Copper Type** (from BOM analysis) - Minimize longest changeovers
2. **PVC/Insulation Type** (part code chars 4-5) - Minimize medium changeovers
3. **Color Sequence** (part code chars 8-11) - Minimize short changeovers

### 5.2 MESWO Creation Algorithm
```
For each work_order_date:
  1. Extract all NSWOs for this date
  2. Analyze BOM data to determine copper specifications
  3. Group NSWOs by copper type
  4. Within each copper group:
     a. Sub-group by PVC/insulation type
     b. Sequence by color for optimal transitions
  5. Create MESWO for each optimized group
  6. Assign sequential MESWO numbers per machine per date
```

### 5.3 Automatic MESWO Assignment
- System automatically assigns MESWOs to appropriate machines based on `machine_no` field
- No manual intervention required for standard operations
- Emergency override capability for supervisors

---

## 6. Production Execution Rules

### 6.1 Immediate Production Start
**Requirement:** Production begins immediately upon MESWO assignment
- No manual start confirmation required
- Label printing for first NSWO starts automatically
- Real-time production tracking via MQTT activated

### 6.2 Automatic NSWO Progression

**6.2.1 Same MCPL Part Code Transition (Seamless)**
**Business Rule:** When consecutive NSWOs share identical MCPL part codes
- System automatically advances to next NSWO when quantity target reached
- No production stoppage required
- Continuous production maintained

**Example:**
```
NSWO1: M04A0141818 - 5,000 meters
NSWO2: M04A0141818 - 3,000 meters  
NSWO3: M04A0141818 - 2,000 meters

Production Flow:
- Meter 0-5,000: NSWO1 active
- Meter 5,001: Auto-switch to NSWO2
- Meter 8,001: Auto-switch to NSWO3
- Meter 10,001: MESWO complete
```

**6.2.2 Different MCPL Part Code Transition (Mandatory Downtime)**
**Business Rule:** When consecutive NSWOs have different MCPL part codes
- Machine MUST remain in OFF state for minimum downtime period
- Downtime duration determined by changeover type
- Next NSWO cannot start until minimum downtime completed

**Downtime Requirements:**
- **Color-only change:** 2 minutes minimum
- **PVC change:** 8 minutes minimum  
- **Copper change:** 20 minutes minimum
- **Combined changes:** Maximum of individual requirements

### 6.3 Continuous Production Edge Case
**Scenario:** Machine continues running without required downtime between different part codes

**System Response:**
1. All continuous production attributed to previous NSWO as over-production
2. Next NSWO cannot start until machine enters OFF state
3. Minimum downtime timer starts only after machine stops
4. Alerts generated for operators about missed changeover

### 6.4 Downtime Handling for Same Part Codes
**Scenario:** Unexpected machine downtime during same part code sequence

**System Response:**
- Current NSWO continues upon machine restart
- No automatic advancement due to downtime
- NSWO progression only occurs when quantity targets met
- Downtime logged for analytics but doesn't affect sequence

---

## 7. Changeover Management

### 7.1 Changeover Detection and Classification

**7.1.1 Automatic Detection**
System analyzes consecutive NSWOs to determine changeover requirements:

```python
# Changeover Analysis Logic
def analyze_changeover(current_nswo, next_nswo):
    current_part = current_nswo.mcpl_part_code
    next_part = next_nswo.mcpl_part_code
    
    # Extract part code components
    current_wire_spec = current_part[0:3]    # M04
    current_insulation = current_part[3:5]   # A0
    current_gauge = current_part[5:7]        # 14
    current_colors = current_part[7:11]      # 1818
    
    # Compare and classify changeover type
    changeover_types = []
    
    if different_copper_from_bom(current_nswo, next_nswo):
        changeover_types.append("COPPER")
    
    if current_insulation != next_insulation:
        changeover_types.append("PVC")
    
    if current_colors != next_colors:
        changeover_types.append("COLOR")
    
    return changeover_types
```

**7.1.2 Changeover Time Calculation**
```python
def calculate_changeover_time(changeover_types):
    base_times = {
        "COPPER": 20,  # minutes
        "PVC": 8,      # minutes
        "COLOR": 2     # minutes
    }
    
    # Return maximum time (changeovers can overlap)
    return max([base_times[ct] for ct in changeover_types])
```

### 7.2 Historical Changeover Tracking

**7.2.1 Automatic Data Collection**
System tracks changeover performance using MQTT data:

**Detection Logic:**
```
When machine_status transitions FALSE → TRUE:
1. Record changeover_start_time
2. Classify changeover type based on work order analysis
3. Record changeover_end_time when machine restarts
4. Calculate actual_changeover_duration
5. Store data for analytics
```

**7.2.2 Changeover Analytics**
System provides historical analysis:
- Average changeover time by type
- Changeover time trends by operator
- Machine-specific changeover performance  
- Efficiency impact of changeover optimization

---

## 8. Security and Access Control

### 8.1 Padlock Security System

**8.1.1 Default State (Locked)**
- Production screen loads with padlock overlay active
- All NSWO sequence modifications disabled
- Only safety-critical functions available (MESWO pause/stop)
- Clear visual indication of locked state

**8.1.2 Authentication Requirements**
**Access Levels:**
- **Supervisor:** Can unlock sequence modifications (if admin allows)
- **Admin:** Can override all restrictions and configure settings
- **Operator:** View-only access, cannot unlock sequences

**8.1.3 Unlock Process**
```
User Experience Flow:
1. Supervisor clicks padlock icon
2. Authentication modal appears
3. Enter Supervisor ID + Password
4. If valid AND admin permits → Unlock for configurable time
5. Small countdown timer appears in corner
6. Auto-lock after timeout period
```

### 8.2 Session Management

**8.2.1 Auto-Lock Behavior**
- **Default Timeout:** 1 minute (admin configurable)
- **Warning Period:** 15 seconds before auto-lock
- **Extend Session:** Available via warning notification
- **Immediate Lock:** Any security violation or manual lock

**8.2.2 In-Progress Operations**
When auto-lock occurs during user interaction:
- **Completed Actions:** Committed to system
- **In-Progress Drag:** Cancelled, item returns to original position
- **Partial Changes:** Rolled back to last committed state

### 8.3 Administrative Controls

**8.3.1 Master Security Settings**
```
Admin Configuration Options:
- ALLOW_NSWO_REORDERING: true/false (master override)
- UNLOCK_TIMEOUT_MINUTES: 1-60 minutes
- REQUIRE_SUPERVISOR_AUTH: true/false
- AUTO_LOCK_WARNING_SECONDS: 5-60 seconds
- LOG_ALL_SECURITY_EVENTS: true/false
```

**8.3.2 Sequence Modification Control**
**When ALLOW_NSWO_REORDERING = false:**
- MESWO treated as atomic block
- Supervisors can only pause/stop/resume entire MESWO
- No individual NSWO manipulation allowed
- Maintains production discipline and changeover optimization

**When ALLOW_NSWO_REORDERING = true:**
- Authenticated supervisors can modify NSWO sequence within MESWO
- Drag-and-drop reordering available during unlock period
- Changes logged for audit trail

---

## 9. MESWO Lifecycle Management

### 9.1 MESWO States

**9.1.1 State Definitions**
```
READY: Available for assignment to any machine
ASSIGNED: Allocated to specific machine, ready to start
IN_PROGRESS: Currently producing (specific NSWO active within sequence)
PAUSED: Temporarily stopped, can be reassigned to any machine
MATERIAL_HOLD: Blocked due to material unavailability
QUALITY_HOLD: Stopped for quality investigation
SPLIT_PENDING: Awaiting MESWO reorganization due to constraints
INVESTIGATION: Under quality or process investigation
COMPLETED: All NSWOs finished successfully
CLOSED: Timed out or administratively closed
```

**9.1.2 Enhanced State Transitions**
```
READY → ASSIGNED (machine assignment)
ASSIGNED → IN_PROGRESS (production start)
IN_PROGRESS → PAUSED (supervisor pause)
IN_PROGRESS → MATERIAL_HOLD (material shortage detected)
IN_PROGRESS → QUALITY_HOLD (quality issue detected)
IN_PROGRESS → COMPLETED (all NSWOs finished)
PAUSED → IN_PROGRESS (resume on any machine)
MATERIAL_HOLD → SPLIT_PENDING (partial material available)
QUALITY_HOLD → INVESTIGATION (formal investigation started)
INVESTIGATION → IN_PROGRESS (investigation resolved)
SPLIT_PENDING → READY (new MESWOs created after split)
ANY_STATE → CLOSED (timeout expiry or administrative closure)
```

**9.1.3 Priority States for Pool Management**
```
URGENT: Customer-requested priority, interruption allowed
HIGH: Important customer, minimal delays acceptable  
NORMAL: Standard priority, follows optimization rules
LOW: Filler work, can be delayed for efficiency
HOLD: Various hold states (material, quality, investigation)
```

### 9.2 Advanced MESWO Management

**9.2.1 Supervisor Pause Capability**
When supervisor pauses MESWO:
1. **Record Current State:** Which NSWO active, quantity produced
2. **Return to Pool:** MESWO moves to Pool Column (Column 1) with appropriate priority
3. **Release Machine:** Machine becomes available for other work
4. **Visual Status Update:** MESWO shows paused state with timestamp and reason
5. **Start Retention Timer:** Configurable timeout period begins

**9.2.2 MESWO Splitting for Constraints**
When material or delivery constraints are identified:
```python
# Automatic MESWO splitting logic
def handle_meswo_constraints(meswo, constraint_type, affected_nswos):
    if constraint_type == "MATERIAL_SHORTAGE":
        # Split at material boundary
        available_nswos = meswo.nswos - affected_nswos
        if available_nswos:
            continue_meswo = create_partial_meswo(available_nswos, original_priority)
            blocked_meswo = create_meswo(affected_nswos, material_available_date)
            return split_meswo(meswo, continue_meswo, blocked_meswo)
    
    elif constraint_type == "DELIVERY_DATE_CHANGE":
        # Reorganize by new delivery dates
        date_groups = group_nswos_by_delivery_date(affected_nswos)
        new_meswos = []
        for date, nswos in date_groups.items():
            new_meswo = create_meswo_for_date(nswos, date)
            new_meswos.append(new_meswo)
        return split_meswo(meswo, new_meswos)
```

**9.2.3 Urgent Order Interruption Logic**
```python
def handle_urgent_order(urgent_nswo, current_production_state):
    # Calculate interruption cost for each machine
    interruption_analysis = []
    
    for machine in active_machines:
        current_meswo = machine.active_meswo
        interruption_cost = calculate_interruption_cost(
            current_meswo.current_nswo_progress,
            urgent_nswo.changeover_requirements,
            current_meswo.remaining_time
        )
        
        interruption_analysis.append({
            'machine_id': machine.id,
            'cost_minutes': interruption_cost,
            'recommendation': 'interrupt' if interruption_cost < MAX_INTERRUPTION_COST else 'queue',
            'current_customer': current_meswo.primary_customer,
            'changeover_type': analyze_changeover_type(machine.current_state, urgent_nswo)
        })
    
    # Recommend optimal interruption strategy
    best_option = min(interruption_analysis, key=lambda x: x['cost_minutes'])
    
    if best_option['cost_minutes'] < MAX_INTERRUPTION_COST:
        return create_interruption_plan(best_option, urgent_nswo)
    else:
        return queue_for_next_available_slot(urgent_nswo)
```

**9.2.4 Pool-Based Assignment with Intelligence**
```python
def suggest_optimal_machine_assignment(meswo, available_machines):
    recommendations = []
    
    for machine in available_machines:
        # Calculate changeover requirements
        changeover_time = calculate_changeover_time(
            machine.current_material_state,
            meswo.first_nswo_requirements
        )
        
        # Consider operator skill level
        operator_compatibility = evaluate_operator_skill(
            machine.current_operator,
            meswo.complexity_level
        )
        
        # Evaluate shift timing
        shift_compatibility = evaluate_shift_timing(
            meswo.estimated_duration,
            machine.remaining_shift_time
        )
        
        # Calculate overall score
        efficiency_score = calculate_assignment_efficiency(
            changeover_time,
            operator_compatibility, 
            shift_compatibility,
            meswo.priority_level
        )
        
        recommendations.append({
            'machine_id': machine.id,
            'changeover_time': changeover_time,
            'efficiency_score': efficiency_score,
            'operator_skill_match': operator_compatibility,
            'shift_timing': shift_compatibility,
            'recommendation_reason': generate_recommendation_reason(...)
        })
    
    return sorted(recommendations, key=lambda x: x['efficiency_score'], reverse=True)
```

### 9.3 Quality Exception Handling

**9.3.1 Quality Issue Detection During Production**
When quality issues are detected during MESWO execution:

```python
def handle_quality_issue_during_meswo(meswo, problematic_nswo, quality_issue_type):
    if admin_settings.ALLOW_QUALITY_EXCEPTIONS:
        # Granular quality control override
        if quality_issue_type in ["SPARK", "DIAMETER", "SPECIFIC_DEFECT"]:
            # Isolate problematic NSWO only
            quarantine_nswo(problematic_nswo, quality_hold=True)
            
            # Continue MESWO with remaining NSWOs if safe
            if can_continue_safely(meswo, problematic_nswo):
                continue_meswo_sequence(meswo, skip_nswo=problematic_nswo)
                create_quality_investigation_workflow(problematic_nswo)
            else:
                # Pause entire MESWO if quality affects subsequent NSWOs
                pause_meswo(meswo, reason="Quality Investigation - Sequence Impact")
        
        elif quality_issue_type in ["MATERIAL_CONTAMINATION", "MACHINE_CALIBRATION"]:
            # Issues affecting entire production run
            pause_meswo(meswo, reason="Quality Investigation - System Wide")
            initiate_comprehensive_quality_review(meswo)
            
    else:
        # Conservative approach: pause entire MESWO
        pause_meswo(meswo, reason="Quality Investigation")
        create_quality_investigation_workflow(problematic_nswo)
```

**9.3.2 Quality Hold State Management**
- **NSWO-Level Holds:** Individual NSWOs can be placed on quality hold
- **MESWO-Level Holds:** Entire MESWO paused for systemic quality issues
- **Investigation Workflow:** Automatic creation of quality investigation tasks
- **Resolution Tracking:** Clear process for releasing quality holds

**9.3.3 Quality Exception Administrative Controls**
```
ALLOW_QUALITY_EXCEPTIONS: true/false
QUALITY_EXCEPTION_TYPES: ["SPARK", "DIAMETER", "MATERIAL_DEFECT"]
REQUIRE_QA_APPROVAL_FOR_CONTINUATION: true/false
AUTO_QUARANTINE_SIMILAR_PARTS: true/false
```

**9.3.1 Retention Period Management**
- **Default Period:** 7 days (admin configurable)
- **Customer-Specific:** Optional different retention by customer priority
- **Extension Capability:** Manual extension by admin for special cases

**9.3.2 Auto-Closure Process**
When retention period expires:
1. **Calculate Final Status:** Determine completion state of each NSWO
2. **NetSuite Synchronization:** Send status updates for all NSWOs
3. **Data Archival:** Move MESWO data to historical storage
4. **System Cleanup:** Remove from active production queues

**NetSuite Status Updates:**
```
For each NSWO in expired MESWO:
- COMPLETED: Fully produced NSWOs with actual quantities
- PARTIALLY_COMPLETED: NSWOs with partial production
- CLOSED: Unstarted NSWOs marked as closed
- Include: Actual quantities, production dates, machine assignments
```

---

## 10. Data Collection and Analytics

### 10.1 Real-Time Data Capture

**10.1.1 MQTT Data Sources**
From each autocoiler (10-second intervals):
- `machine_status`: Production state (running/stopped)
- `actual_quantity`: Current production quantity (0.01m units)
- `finished_coil_status`: Coil completion trigger
- `set_coil_length`: Target length setting
- `previous_work_order_length`: Last completed coil length

**10.1.2 Derived Analytics**
System calculates real-time metrics:
- **Production Rate:** Meters per minute from quantity progression
- **Efficiency:** Actual vs target production rates
- **OEE Components:** Availability, Performance, Quality
- **Changeover Performance:** Actual vs planned changeover times

### 10.2 Historical Analytics

**10.2.1 Changeover Analytics**
- Average changeover time by type (copper/PVC/color)
- Changeover time trends by operator and machine
- Efficiency impact of changeover optimization
- Cost analysis of changeover delays

**10.2.2 Production Analytics**
- MESWO completion time vs planned schedule
- Over-production analysis by machine and operator
- Quality correlation with production parameters
- Machine utilization and performance benchmarking

**10.2.3 Quality Analytics**
- Defect rates by changeover type
- Quality trends during continuous production runs
- Copper lot quality correlation
- Speed vs quality optimization curves

### 10.3 Performance Analytics

**10.3.1 Changeover Optimization**
- Recommend optimal NSWO sequencing within MESWOs based on historical data
- Track changeover time patterns by operator and machine
- Identify recurring inefficiencies in changeover processes

**10.3.2 Quality Analysis**
- Track defect patterns relative to production parameters
- Monitor quality trends during continuous production runs
- Generate alerts when quality metrics deviate from normal ranges

---

## 11. NetSuite Integration

### 11.1 Data Synchronization

**11.1.1 Inbound Data (NetSuite → MES)**
- **Work Orders:** Fetch via RESTlet API with configurable frequency
- **BOM Data:** Component specifications for changeover analysis  
- **Customer Data:** Priority levels and special requirements
- **Material Data:** Copper specifications and availability

**11.1.2 Outbound Data (MES → NetSuite)**
- **Production Status:** Real-time NSWO completion updates
- **Quantity Reporting:** Actual vs planned production quantities
- **Quality Data:** Defect reports and quality metrics
- **Resource Utilization:** Machine and operator efficiency data

### 11.2 Status Update Protocol - STANDARDIZED TERMINOLOGY

**11.2.1 Event-Driven Immediate Updates**
Critical events that trigger immediate NetSuite API calls:
- NSWO completion (when target quantity reached)
- NSWO production start (when production begins)
- Quality issues detected (critical defects)
- Material shortage constraints (blocking production)
- Urgent order interruptions (affecting planned sequence)
- Delivery date change requests (customer-initiated)

**11.2.2 Polling-Based Batch Updates (10-Minute Intervals)**
Regular updates sent in scheduled batches:
- Production progress updates (quantity progress for active NSWOs)
- Machine status changes (running/stopped transitions)
- Operator assignment variances (planned vs actual operator differences)
- Shift assignment variances (planned vs actual shift differences)
- Equipment assignment variances (planned vs actual machine differences)
- Changeover completion timings (actual vs estimated performance)
- MESWO state changes (assignments, pauses, resumes)

**11.2.3 Daily Batch Synchronization**
Comprehensive daily reports:
- Complete production summaries per MESWO
- Variance analysis reports (planned vs actual comprehensive data)
- Historical performance metrics
- System health and uptime statistics

### 11.3 Error Handling

**11.3.1 Connection Resilience**
- Automatic retry logic for failed API calls
- Local data buffering during connectivity issues
- Conflict resolution for synchronized data
- Manual override capability for critical operations

---

## 12. User Interface Requirements

### 12.1 Production Dashboard

**12.1.1 Dashboard Layout Structure**
- **6-column layout for complete MESWO management:**
  - **Column 1:** Unassigned/Paused MESWO Pool
  - **Columns 2-6:** Autocoiler machines (1-5)
- Live production progress per machine
- Current MESWO and active NSWO display
- Real-time quantity and efficiency metrics

**12.1.2 MESWO Pool Column (Column 1)**
**Purpose:** Central repository for paused and unassigned MESWOs
- **Unassigned MESWOs:** Newly created, ready for machine assignment
- **Paused MESWOs:** Temporarily stopped, available for reassignment
- **Visual Indicators:** 
  - Color coding: Unassigned (blue), Paused (orange), Expired soon (red)
  - Time indicators: Creation date, pause duration, retention countdown
- **Drag-and-Drop Source:** All MESWOs can be dragged to any available machine
- **Search and Filter:** Quick finding by customer, part code, or priority

**12.1.3 Machine Columns (Columns 2-6)**
**Individual Machine Status Display:**
- **Active MESWO:** Currently assigned MESWO with progress indicator
- **Current NSWO:** Active NSWO within MESWO sequence
- **Queue Visibility:** Next 2-3 NSWOs in sequence preview
- **Drop Zone:** Accept MESWOs from pool or other machines
- **Machine Controls:** Pause, stop, emergency controls

**12.1.4 MESWO Management Interface**
- Visual MESWO cards with production progress
- **Drag-and-drop MESWO assignment:**
  - From pool to machines
  - Between machines (for paused MESWOs)
  - From machines back to pool (pause operation)
- Pause/resume controls for active MESWOs
- Emergency stop and override capabilities

**12.1.5 Pool Management Features**
- **Retention Monitoring:** Visual countdown for MESWOs approaching auto-closure
- **Priority Indicators:** Urgent, standard, low priority visual markers
- **Batch Selection:** Multi-select MESWOs for bulk operations
- **Quick Actions:** Assign to next available machine, extend retention

### 12.2 Sequence Management

**12.2.1 NSWO Sequence Display**
- Clear visualization of NSWO order within MESWO
- Progress indicators for each NSWO
- Changeover type indicators between NSWOs
- Estimated completion times

**12.2.2 Security-Controlled Modifications**
- Padlock overlay for locked state
- Authentication modal for supervisor access
- Countdown timer during unlocked sessions
- Visual feedback for locked interactions

### 12.3 Analytics Dashboard

**12.3.1 Real-Time Metrics**
- Live OEE calculation per machine
- Current changeover in progress status
- Daily production vs plan comparison
- Quality metrics and alerts

**12.3.2 Historical Analysis**
- Changeover time trends by type
- Production efficiency comparisons
- Quality correlation analysis
- Cost impact calculations

### 12.4 Mobile Optimization

**12.4.1 Responsive Design**
- Touch-optimized controls for tablet use
- Readable text and buttons for shop floor environment
- Offline capability during network issues
- Progressive Web App functionality

---



## 13. Configuration Management

### 13.1 Consolidated Administrative Settings

### 13.1 Consolidated Administrative Settings - STANDARDIZED FORMAT

All configuration parameters use consistent lowercase YAML format throughout the system:

**13.1.1 Security and Access Control**
```yaml
security:
  allow_nswo_reordering: true/false              # Enable sequence modifications
  unlock_timeout_minutes: 1-60                   # Session timeout
  require_supervisor_auth: true/false            # Authentication requirement
  auto_lock_warning_seconds: 5-60               # Warning before auto-lock
  log_all_security_events: true/false           # Audit logging
  quality_exception_override: true              # Quality overrides atomic block rule (always true)
```

**13.1.2 MESWO Management and Workflow**
```yaml
meswo_management:
  allow_meswo_splitting: true/false              # Enable constraint-based splitting
  allow_quality_exceptions: true/false          # Individual NSWO quality holds
  allow_urgent_interruptions: true/false        # Production interruption for urgent orders
  max_interruption_cost_minutes: 30             # Threshold for interruption decisions
  enable_shift_awareness: true/false            # Shift boundary considerations
  enable_operator_skill_matching: true/false    # Skill-based assignment
  atomic_block_override_for_safety: true        # Always allow safety overrides (always true)
```

**13.1.3 Changeover and Production Timing**
```yaml
changeover_times:
  copper_minutes: 20                             # Base copper changeover time
  pvc_minutes: 8                                 # Base PVC changeover time  
  color_minutes: 2                               # Base color changeover time
  complexity_multiplier: 1.2                    # Additional time for multi-type changeovers
  track_actual_vs_estimated: true/false         # Performance learning
  learn_from_historical_data: true/false        # Algorithm improvement
```

**13.1.4 Retention and Lifecycle Management**
```yaml
retention_policies:
  base_retention_days: 7                         # Base retention for all MESWOs
  material_hold_extension: 23                   # Additional days for MATERIAL_HOLD (total 30)
  quality_hold_extension: 7                     # Additional days for QUALITY_HOLD (total 14)
  investigation_extension: 14                   # Additional days for INVESTIGATION (total 21)
  scheduled_extension: 60                       # Additional days for SCHEDULED state (total 67)
  manual_extension_max_days: 30                 # Maximum manual extension allowed
  enable_intelligent_closure: true/false        # Smart closure decisions
  completion_threshold_for_extension: 80        # % complete to offer extension
```

**13.1.5 Priority and Customer Management**  
```yaml
priority_management:
  urgent_delivery_threshold_hours: 24           # Auto-assign URGENT priority
  high_delivery_threshold_hours: 48             # Auto-assign HIGH priority
  low_priority_threshold_days: 7                # Auto-assign LOW priority
  allow_supervisor_priority_override: true/false # Manual priority elevation
  customer_escalation_auto_urgent: true/false   # Customer requests trigger URGENT
```

**13.1.6 Integration and External Systems**
```yaml
netsuite_integration:
  immediate_sync_events: ["NSWO_COMPLETED", "QUALITY_ISSUE_DETECTED", "MATERIAL_SHORTAGE"]
  polling_interval_minutes: 10                  # Regular polling frequency
  batch_sync_frequency: "daily"                 # Comprehensive sync frequency
  retry_attempts: 3                             # Failed API call retries
  timeout_seconds: 30                           # API timeout
  enable_customer_notifications: true/false     # Delivery change notifications
  enable_delivery_date_sync: true/false         # Bidirectional date sync
  enable_variance_reporting: true/false         # Planned vs actual reporting

material_integration:
  enable_real_time_inventory: true/false        # Live inventory monitoring
  low_stock_warning_days: 3                     # Advance warning threshold
  critical_stock_warning_days: 1                # Critical shortage warning
  auto_suggest_alternatives: true/false         # Alternative material recommendations
  enable_supplier_notifications: true/false     # Automatic purchase notifications
```

**13.1.7 Quality and Analytics**
```yaml
quality_management:
  exception_types: ["SPARK", "DIAMETER", "MATERIAL_DEFECT", "CALIBRATION_DRIFT"]
  require_qa_approval_for_continuation: true/false
  auto_quarantine_similar_parts: true/false
  enable_quality_trend_monitoring: true/false   # Historical quality analysis
  quality_correlation_tracking: true/false      # Quality parameter analysis

analytics_and_reporting:
  enable_changeover_time_analysis: true/false
  enable_material_usage_monitoring: true/false  
  enable_production_efficiency_tracking: true/false
  enable_quality_correlation_analysis: true/false
  enable_performance_benchmarking: true/false
  enable_variance_trend_analysis: true/false
```

**Configuration Usage Throughout System:**
All references in the codebase use the standardized format:
- `config.security.allow_nswo_reordering`
- `config.meswo_management.allow_meswo_splitting`
- `config.retention_policies.base_retention_days`
- `config.priority_management.urgent_delivery_threshold_hours`# MCPL MES Work Order Management System
### 18. System Integration and Tracking

### 18.1 Machine and Operator State Tracking

**18.1.1 Dual Tracking System (Planned vs Actual)**
The system maintains complete records of both planned (from NSWO) and actual production data:

```python
# NSWO Contains (Planned Data from NetSuite):
nswo_planned_data = {
    "operator_name": "John Smith",           # Planned operator from NetSuite
    "production_date": "2025-06-17",         # Planned production date
    "equipment_id": "Autocoiler-3",          # Planned machine assignment
    "shift": "Day Shift",                    # Planned shift
    "quantity": 5000                         # Planned quantity
}

# System Tracks (Actual Production Data):
actual_production_data = {
    "actual_operator": "Mike Johnson",        # Supervisor-assigned actual operator
    "actual_production_date": "2025-06-18",  # Actual production date
    "actual_equipment_id": "Autocoiler-1",   # Actual machine used
    "actual_shift": "Night Shift",           # Actual shift worked
    "actual_quantity": 4850                   # Actual quantity produced
}

# Complete Production Record:
production_record = {
    **nswo_planned_data,
    **actual_production_data,
    "variance_analysis": {
        "operator_changed": True,
        "date_variance_days": 1,
        "equipment_changed": True,
        "shift_changed": True,
        "quantity_variance": -150
    }
}
```

**18.1.2 Operator Assignment and Tracking**
- **Supervisor Assignment:** Supervisors assign operators to machines via dashboard interface
- **Real-time Tracking:** Current operator assignment visible on each machine column
- **Variance Detection:** System highlights when actual operator differs from NSWO planned operator
- **Historical Records:** Complete operator assignment history for each MESWO/NSWO

**18.1.3 Machine State Data Structure**
```python
machine_state = {
    "machine_id": "Autocoiler-1",
    "current_operator": {
        "operator_id": "OP001",
        "operator_name": "Mike Johnson",
        "skill_level": 3,
        "assigned_timestamp": "2025-06-17T14:30:00Z",
        "assigned_by_supervisor": "SUP001"
    },
    "current_shift": {
        "shift_name": "Day Shift",
        "shift_start": "06:00:00",
        "shift_end": "18:00:00",
        "remaining_minutes": 125
    },
    "active_meswo": "MESWO-1-20250617-001",
    "current_nswo": "38",
    "machine_status": "RUNNING"
}
```

### 18.2 Shift Management System

**18.2.1 Administrative Shift Configuration**
Admin-configurable shift schedules supporting flexible timing:

```yaml
shift_configuration:
  shift_1:
    name: "Day Shift"
    start_time: "06:00:00"
    end_time: "18:00:00"
    duration_hours: 12
  
  shift_2:
    name: "Night Shift"  
    start_time: "18:00:00"
    end_time: "06:00:00"     # Next day
    duration_hours: 12
    
  # Alternative configuration example:
  shift_1_alt:
    name: "Morning Shift"
    start_time: "06:00:00" 
    end_time: "17:00:00"
    duration_hours: 11
    
  shift_2_alt:
    name: "Evening Shift"
    start_time: "17:00:00"
    end_time: "06:00:00"     # Next day  
    duration_hours: 13
```

**18.2.2 Shift Boundary Management**
- **Automatic Detection:** System calculates current shift based on current time
- **Overlap Handling:** Handles shifts that cross midnight boundary
- **Handover Periods:** Optional buffer time between shifts for handover
- **Variance Tracking:** Records when actual shift differs from NSWO planned shift

### 18.3 NetSuite Integration Strategy

**18.3.1 Event-Driven Real-time Updates (Immediate Triggers)**
Events that trigger immediate NetSuite API calls:

```python
immediate_netsuite_events = [
    "NSWO_COMPLETED",                    # When NSWO reaches target quantity
    "NSWO_STARTED",                      # When NSWO production begins
    "QUALITY_ISSUE_DETECTED",           # Critical quality problems
    "MESWO_PAUSED_MATERIAL_SHORTAGE",   # Material constraint issues
    "MESWO_PAUSED_QUALITY_HOLD",        # Quality investigation started
    "URGENT_ORDER_INTERRUPTION",        # Urgent order affects planned sequence
    "DELIVERY_DATE_CHANGE_REQUEST",     # Customer requests delivery change
    "MESWO_SPLIT_MATERIAL_CONSTRAINT",  # MESWO split due to material issues
]

def trigger_immediate_netsuite_update(event_type, event_data):
    # Send critical events immediately
    if event_type in immediate_netsuite_events:
        api_payload = create_netsuite_payload(event_type, event_data)
        send_netsuite_api_call(api_payload, priority="IMMEDIATE")
        log_event_sync(event_type, "IMMEDIATE", api_payload)
```

**18.3.2 Polling-Based Updates (10-Minute Intervals)**
Regular updates sent every 10 minutes:

```python
polling_netsuite_events = [
    "PRODUCTION_PROGRESS_UPDATE",        # Quantity progress for active NSWOs
    "MACHINE_STATUS_UPDATE",             # Machine running/stopped status
    "OPERATOR_ASSIGNMENT_CHANGES",      # Actual vs planned operator variances
    "SHIFT_ASSIGNMENT_CHANGES",         # Actual vs planned shift variances  
    "EQUIPMENT_ASSIGNMENT_CHANGES",     # Actual vs planned machine variances
    "CHANGEOVER_COMPLETION",             # Changeover timing and efficiency
    "MESWO_ASSIGNMENT_CHANGES",         # MESWO reassignments between machines
    "RETENTION_WARNING_UPDATES",        # MESWOs approaching retention expiry
]

def process_polling_updates():
    # Collect all changes since last poll
    changes_since_last_poll = gather_system_changes(last_poll_timestamp)
    
    for change in changes_since_last_poll:
        if change.event_type in polling_netsuite_events:
            queue_for_batch_sync(change)
    
    # Send batched updates
    send_batched_netsuite_updates()
    update_last_poll_timestamp()
```

**18.3.3 Variance Reporting to NetSuite**
Complete planned vs actual tracking for NetSuite analysis:

```python
variance_report_payload = {
    "nswo_id": "38",
    "planned_data": {
        "operator": "John Smith",
        "production_date": "2025-06-17", 
        "equipment": "Autocoiler-3",
        "shift": "Day Shift",
        "quantity": 5000
    },
    "actual_data": {
        "operator": "Mike Johnson",
        "production_date": "2025-06-18",
        "equipment": "Autocoiler-1", 
        "shift": "Night Shift",
        "quantity": 4850
    },
    "variance_summary": {
        "operator_variance": True,
        "date_variance_days": 1,
        "equipment_variance": True,
        "shift_variance": True,
        "quantity_variance_percent": -3.0
    },
    "variance_reasons": [
        "Original equipment maintenance required",
        "Operator schedule conflict resolved",
        "Production delay due to material delivery"
    ]
}
```

---

## 14. Success Criteria

### 14.1 Functional Requirements

**14.1.1 Core Functionality**
- [x] Automatic MESWO creation with date-first grouping
- [x] Changeover optimization within date groups
- [x] Seamless NSWO progression for same part codes
- [x] Mandatory downtime enforcement for part code changes
- [x] Cross-machine MESWO resume capability

**14.1.2 Security and Control**
- [x] Padlock security system with supervisor authentication
- [x] Configurable auto-lock timing
- [x] Administrative override capabilities
- [x] Complete audit trail for all modifications

**14.1.3 Data and Analytics**
- [x] Real-time changeover detection and timing
- [x] Historical changeover performance analysis
- [x] Quality correlation with production parameters
- [x] NetSuite bidirectional synchronization

### 14.2 Performance Metrics

**14.2.1 Efficiency Improvements**
- 20-30% reduction in changeover frequency through optimal grouping
- 15-25% improvement in machine utilization
- 10-15% reduction in total production time

**14.2.2 Quality Improvements**
- 40-60% reduction in false positive detections
- 25-35% improvement in defect detection accuracy
- 90%+ accuracy in changeover time predictions

**14.2.3 Operational Improvements**
- 99.5%+ system uptime during production hours
- <2 second response time for real-time updates
- 100% traceability for all production activities

---

## 15. Implementation Timeline

### 15.1 Phase 1: Foundation (Weeks 1-4)

**Week 1-2: Core MESWO Logic**
- Implement date-first grouping algorithm
- Develop changeover optimization within date groups
- Create basic MESWO data structures

**Week 3-4: Production Execution**
- Implement automatic NSWO progression
- Develop changeover detection and timing
- Create basic production control interface

### 15.2 Phase 2: Security and Control (Weeks 5-8)

**Week 5-6: Padlock Security System**
- Implement authentication and session management
- Develop auto-lock and extend session functionality
- Create administrative configuration interface

**Week 7-8: MESWO Lifecycle Management**
- Implement pause/resume functionality
- Develop cross-machine assignment capability
- Create retention and auto-closure logic

### 15.3 Phase 3: Analytics and Integration (Weeks 9-12)

**Week 9-10: Data Collection**
- Implement real-time changeover tracking
- Develop historical analytics dashboard
- Create quality correlation analysis

**Week 11-12: NetSuite Integration**
- Implement bidirectional data synchronization
- Develop error handling and resilience
- Create comprehensive testing and validation

### 15.4 Phase 4: Optimization and Deployment (Weeks 13-16)

**Week 13-14: Performance Optimization**
- Optimize algorithms for production scale
- Implement advanced analytics features
- Conduct comprehensive system testing

**Week 15-16: Production Deployment**
- Deploy to production environment
- Conduct operator training
- Monitor initial performance and adjust

---

## 16. Appendix

### 16.1 Sample MESWO Structure

**Example Date Group: June 17, 2025**
```json
{
  "date": "2025-06-17",
  "meswos": [
    {
      "meswo_id": "MESWO-1-20250617-001",
      "machine_id": 1,
      "copper_type": "BNF-16/0.21",
      "nswo_sequence": [
        {
          "nswo_id": "38",
          "mcpl_part_code": "M04A0141818",
          "quantity": 5000,
          "customer": "TATA Motors"
        },
        {
          "nswo_id": "39", 
          "mcpl_part_code": "M04A0141125",
          "quantity": 3000,
          "customer": "TATA Motors"
        }
      ],
      "changeover_analysis": [
        {
          "from_nswo": "38",
          "to_nswo": "39", 
          "changeover_type": ["COLOR"],
          "estimated_time_minutes": 2
        }
      ]
    }
  ]
}
```

### 16.2 Configuration File Example

```yaml
# MES Work Order Configuration
meswo_config:
  security:
    allow_nswo_reordering: true
    unlock_timeout_minutes: 1
    auto_lock_warning_seconds: 15
    require_supervisor_auth: true
  
  changeover_times:
    copper_minutes: 20
    pvc_minutes: 8
    color_minutes: 2
  
  retention:
    default_days: 7
    premium_customer_days: 14
    auto_close_enabled: true
  
  netsuite:
    sync_frequency: "hourly"
    retry_attempts: 3
    timeout_seconds: 30
```

---

## 18. Appendix

### 18.1 Complete API Reference

**Core MESWO Management**
- `GET /api/meswos?include_analytics=true` - List MESWOs with optional analytics data
- `POST /api/meswos` - Create MESWO with automatic optimization
- `PUT /api/meswos/{id}/assign?include_recommendations=true` - Assign with optional changeover analysis
- `PUT /api/meswos/{id}/pause` - Pause with automatic pool return and state preservation
- `PUT /api/meswos/{id}/resume?target_machine=auto` - Resume with optional optimal machine selection
- `POST /api/meswos/{id}/split` - Split MESWO for material/delivery constraints
- `PUT /api/meswos/{id}/merge` - Merge compatible MESWOs

**Advanced MESWO Operations**
- `POST /api/meswos/urgent-interrupt` - Handle urgent order interruptions with cost analysis
- `PUT /api/meswos/{id}/delivery-date` - Change delivery dates with impact analysis
- `POST /api/meswos/{id}/quality-hold` - Place MESWO on quality hold
- `PUT /api/meswos/{id}/material-hold` - Handle material constraints
- `POST /api/meswos/{id}/investigate` - Start quality investigation workflow

**Pool and Assignment Management**
- `GET /api/pool/meswos?sort=priority&filter=ready` - Get pool MESWOs with sorting and filtering
- `POST /api/pool/assign-optimal` - Get changeover-based machine assignment recommendations
- `PUT /api/pool/bulk-assign` - Bulk assignment operations
- `GET /api/pool/retention-alerts` - Get MESWOs approaching retention expiry

**Operator and Shift Management**
- `POST /api/operators/assign` - Assign operator to machine with skill level validation
- `GET /api/shifts/current` - Get current shift information for all machines
- `PUT /api/shifts/config` - Update admin shift configuration
- `GET /api/operators/assignments` - Get current operator assignments across all machines

**Tracking and Variance Management**
- `GET /api/tracking/planned-vs-actual/{nswo_id}` - Get planned vs actual variance data
- `POST /api/tracking/variance-report` - Submit variance explanation and notes
- `GET /api/tracking/variance-summary` - Get variance analytics across NSWOs
- `PUT /api/tracking/update-actual` - Update actual production data (operator, date, machine, shift)

**NetSuite Integration and Sync**
- `POST /api/netsuite/immediate-sync` - Trigger immediate event-driven sync
- `GET /api/netsuite/sync-status` - Get current sync status and last update times
- `PUT /api/netsuite/sync-config` - Configure sync frequency and event triggers
- `GET /api/netsuite/variance-reports` - Get planned vs actual reports ready for NetSuite

**Analytics and Reporting**
- `GET /api/analytics/changeover-analysis` - Changeover time analysis and trends
- `GET /api/analytics/quality-correlation` - Quality issue correlation analysis
- `GET /api/analytics/variance-trends` - Planned vs actual variance trends
- `GET /api/analytics/operator-efficiency` - Operator performance across machines and shifts
- `GET /api/analytics/shift-performance` - Shift-based production analysis
- `GET /api/analytics/performance-dashboard` - Real-time performance metrics

**Security and Administration**
- `POST /api/auth/unlock-advanced` - Multi-level authentication for critical operations
- `PUT /api/config/meswo-settings` - Update advanced MESWO configuration
- `PUT /api/config/shift-schedule` - Update shift timing configuration
- `GET /api/audit/variance-changes` - Audit trail for planned vs actual changes
- `GET /api/audit/operator-assignments` - Operator assignment history

### 18.2 Enhanced Sample MESWO with Complete Lifecycle

**Example Advanced MESWO with All States:**
```json
{
  "meswo_id": "MESWO-1-20250617-001",
  "state": "IN_PROGRESS",
  "priority": "HIGH",
  "machine_id": 1,
  "delivery_date": "2025-06-17",
  "created_timestamp": "2025-06-15T08:00:00Z",
  "assigned_timestamp": "2025-06-15T09:00:00Z",
  "copper_type": "BNF-16/0.21",
  "estimated_duration_minutes": 180,
  "complexity_level": 3,
  "retention_days": 7,
  "retention_expiry": "2025-06-22T08:00:00Z",
  "nswo_sequence": [
    {
      "nswo_id": "38",
      "mcpl_part_code": "M04A0141818",
      "quantity": 5000,
      "status": "COMPLETED",
      "produced_quantity": 5000,
      "customer": "TATA Motors",
      "planned_operator": "John Smith",
      "actual_operator": "Mike Johnson",
      "planned_shift": "Day Shift",
      "actual_shift": "Day Shift",
      "planned_machine": "Autocoiler-3",
      "actual_machine": "Autocoiler-1",
      "completion_timestamp": "2025-06-15T10:30:00Z"
    },
    {
      "nswo_id": "39", 
      "mcpl_part_code": "M04A0141125",
      "quantity": 3000,
      "status": "IN_PROGRESS", 
      "produced_quantity": 1500,
      "customer": "TATA Motors",
      "planned_operator": "John Smith",
      "actual_operator": "Mike Johnson",
      "planned_shift": "Day Shift",
      "actual_shift": "Day Shift",
      "start_timestamp": "2025-06-15T10:35:00Z"
    }
  ],
  "changeover_analysis": [
    {
      "from_nswo": "38",
      "to_nswo": "39",
      "changeover_type": ["COLOR"],
      "estimated_time_minutes": 2,
      "actual_time_minutes": 1.5,
      "efficiency_percentage": 125.0
    }
  ],
  "variance_summary": {
    "operator_variance": true,
    "machine_variance": true,
    "shift_variance": false,
    "date_variance": false
  }
}
```

### 18.3 Master Configuration Template

```yaml
# MCPL MES Master Configuration - Production Ready
meswo_system_config:
  security:
    allow_nswo_reordering: true
    unlock_timeout_minutes: 1
    auto_lock_warning_seconds: 15
    require_supervisor_auth: true
    log_all_security_events: true
    quality_exception_override: true
  
  meswo_management:
    allow_meswo_splitting: true
    allow_quality_exceptions: true
    allow_urgent_interruptions: true
    max_interruption_cost_minutes: 30
    enable_shift_awareness: true
    enable_operator_skill_matching: true
    atomic_block_override_for_safety: true
  
  changeover_times:
    copper_minutes: 20
    pvc_minutes: 8
    color_minutes: 2
    complexity_multiplier: 1.2
    track_actual_vs_estimated: true
    learn_from_historical_data: true
  
  retention_policies:
    base_retention_days: 7
    material_hold_extension: 23
    quality_hold_extension: 7
    investigation_extension: 14
    scheduled_extension: 60
    manual_extension_max_days: 30
    enable_intelligent_closure: true
    completion_threshold_for_extension: 80
  
  priority_management:
    urgent_delivery_threshold_hours: 24
    high_delivery_threshold_hours: 48
    low_priority_threshold_days: 7
    allow_supervisor_priority_override: true
    customer_escalation_auto_urgent: true
  
  netsuite_integration:
    immediate_sync_events: ["NSWO_COMPLETED", "NSWO_STARTED", "QUALITY_ISSUE_DETECTED"]
    polling_interval_minutes: 10
    batch_sync_frequency: "daily"
    retry_attempts: 3
    timeout_seconds: 30
    enable_variance_reporting: true
  
  material_integration:
    enable_real_time_inventory: true
    low_stock_warning_days: 3
    critical_stock_warning_days: 1
    auto_suggest_alternatives: true
    enable_supplier_notifications: true
  
  quality_management:
    exception_types: ["SPARK", "DIAMETER", "MATERIAL_DEFECT", "CALIBRATION_DRIFT"]
    require_qa_approval_for_continuation: true
    auto_quarantine_similar_parts: true
    enable_quality_trend_monitoring: true
    quality_correlation_tracking: true
  
  analytics_and_reporting:
    enable_changeover_time_analysis: true
    enable_material_usage_monitoring: true
    enable_production_efficiency_tracking: true
    enable_quality_correlation_analysis: true
    enable_performance_benchmarking: true
    enable_variance_trend_analysis: true
```

---

**Document End**

*This enhanced specification provides complete coverage for advanced manufacturing execution system requirements with full consistency and production readiness. All implementation must adhere to these requirements for robust production floor operation.*
