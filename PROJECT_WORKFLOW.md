# Campaign Attribution Management - Complete Project Workflow

## System Overview
End-to-end campaign attribution processing system handling 300M-500M records with parallel multi-threaded data processing from Snowflake, through validation and transformation pipelines, to final report generation.

---

## 🔄 Complete Workflow: UI to Backend Data Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                      PHASE 1: USER INPUT                         │
└─────────────────────────────────────────────────────────────────┘

User Login → Add Request Form → Submit

                            ↓

┌─────────────────────────────────────────────────────────────────┐
│                 PHASE 2: DATABASE INSERTION                      │
└─────────────────────────────────────────────────────────────────┘

    Request Details → PostgreSQL Database
    Generated Request ID: 6989

                            ↓

┌─────────────────────────────────────────────────────────────────┐
│             PHASE 3: PARALLEL REQUEST PROCESSING                 │
└─────────────────────────────────────────────────────────────────┘

    Request Picker (Daemon - Continuous Monitoring)
            ↓
    Polls Database → Finds Waiting Requests
            ↓
    Max 10 Concurrent Requests Running Simultaneously
            ↓

    Request 6989 | Request 6990 | Request 6991 | ... (10 parallel)
         ↓              ↓              ↓

                            ↓

┌─────────────────────────────────────────────────────────────────┐
│                   PHASE 4: VALIDATION                            │
└─────────────────────────────────────────────────────────────────┘

    Request Validation
            ↓
    ✅ Valid → Continue    |    ❌ Invalid → Stop + Email Alert

                            ↓

┌─────────────────────────────────────────────────────────────────┐
│            PHASE 5: BACKEND DATA PIPELINE (7 MODULES)            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  MODULE 1: TRT PREPARATION (Treatment Data)                      │
└─────────────────────────────────────────────────────────────────┘

    DATA SOURCE: Snowflake (Cloud Data Warehouse)
            ↓
    ┌──────────────────────────────────────────────────────────┐
    │  PARALLEL IN-MEMORY DATA PULLING                          │
    │  • 5 Threads Running Simultaneously                       │
    │  • Each Thread Pulls Data Chunk from Snowflake           │
    │  • In-Memory Processing (High-Speed RAM Operations)      │
    │  • Data Size: 300 Million - 500 Million Records         │
    │  • Thread Distribution: 60M-100M records per thread      │
    └──────────────────────────────────────────────────────────┘
            ↓
        Thread 1    Thread 2    Thread 3    Thread 4    Thread 5
        (60M-100M)  (60M-100M)  (60M-100M)  (60M-100M)  (60M-100M)
            ↓           ↓           ↓           ↓           ↓
        ─────────────────────────────────────────────────────
                            ↓
    Data Aggregation → PostgreSQL Treatment Table


    ┌────────────────────────────────────────────────┐
    │  PARALLEL BRANCH: MODULE 2 (Responders)        │
    │  Runs Simultaneously with Module 1             │
    └────────────────────────────────────────────────┘
            ↓
    Pulls Campaign Performance Data
            ↓
    [Merges with TRT results after completion]

                            ↓

┌─────────────────────────────────────────────────────────────────┐
│  MODULE 3: SUPPRESSION LIST                                      │
└─────────────────────────────────────────────────────────────────┘

    Reads Suppression Files/Lists
            ↓
    Removes Suppressed Records from TRT Data
            ↓
    Updates Suppression Statistics

                            ↓

┌─────────────────────────────────────────────────────────────────┐
│  MODULE 4: SOURCE PREPARATION                                    │
└─────────────────────────────────────────────────────────────────┘

    Creates Source Table for Campaign Delivery
            ↓
    Applies Segmentation & Priority Logic
            ↓
    Ready for Campaign Execution

                            ↓

┌─────────────────────────────────────────────────────────────────┐
│  MODULE 5: DELIVERED REPORT (POSTBACK)                           │
└─────────────────────────────────────────────────────────────────┘

    Creates Postback Table with Campaign Tracking
            ↓
    Processes Report Data
            ↓
    Merges Delivered Records with Responders
            ↓
    Final Attribution Report Ready

                            ↓

┌─────────────────────────────────────────────────────────────────┐
│  MODULE 6: TIMESTAMP APPENDING (Optional)                        │
└─────────────────────────────────────────────────────────────────┘

    Applies Realistic Timestamp Distribution
            ↓
    Updates Postback Table with Timestamps

                            ↓

┌─────────────────────────────────────────────────────────────────┐
│  MODULE 7: IP APPENDING (Optional)                               │
└─────────────────────────────────────────────────────────────────┘

    Assigns IP Addresses to Records
            ↓
    Maintains IP Uniqueness Patterns

                            ↓

┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 6: COMPLETION & NOTIFICATION              │
└─────────────────────────────────────────────────────────────────┘

    Update Database
            ↓
    Generate QA Statistics
            ↓
    Send Email Notification
            ↓
    Optional Cleanup & Archive

                            ↓

┌─────────────────────────────────────────────────────────────────┐
│             PHASE 7: USER MONITORING & ACTIONS (UI)              │
└─────────────────────────────────────────────────────────────────┘

    Request Monitor Page (Auto-refresh every 30s)
            ↓
    ┌────────────────────────────────────────────────────────┐
    │  Request ID | Client  | TRT Count | Actions           │
    │  6989       | Verizon | 450M      | Kill / View       │
    │  6990       | Nike    | 320M      | ReRun / Download  │
    └────────────────────────────────────────────────────────┘
            ↓
    Available Actions:
    • Kill: Terminates running processes
    • ReRun: Restart from specific module
    • View: Display request statistics
    • Download: Export statistics to Excel

                            ↓

    Dashboard Analytics (Auto-refresh every 5 min)
            ↓
    Real-time Metrics & User Activity Tracking
```

---

## 🔧 Technical Architecture

### **Frontend Stack**
- React + TypeScript
- Tailwind CSS

### **Backend Stack**
- Flask REST API
- PostgreSQL (Request management)
- Snowflake (TRT source data - 300M-500M records)
- Shell Scripts (Processing pipeline)

### **Data Sources**
- **PostgreSQL**: Request metadata, client info, statistics
- **Snowflake**: Treatment data (300M-500M records)
- **Presto**: Big data queries and analytics
- **Impala**: Performance analysis
- **MySQL**: Legacy client data

---

## 🎯 Key Features

### **Multi-Request Processing**
- Daemon continuously monitors database
- Up to 10 concurrent requests
- Independent processing pipelines
- No interference between requests

### **Snowflake Data Integration**
- Cloud-based data warehouse connection
- Parallel 5-thread data extraction
- In-memory processing for speed
- Handles 300M-500M record datasets

### **Modular Pipeline Architecture**
- 7 independent modules
- Restart from any module on error
- Hierarchical process tracking
- Comprehensive logging per module

### **Real-Time Monitoring**
- Live status updates in UI
- Auto-refresh capabilities
- Action controls (Kill/ReRun/View)
- Excel export functionality

---

## 📊 Data Flow Summary

```
User Form Submission
    ↓
PostgreSQL Database (Request Queue)
    ↓
Validation Layer
    ↓
Snowflake (TRT Data Source - 300M-500M records)
    ↓
5 Parallel Threads (In-Memory Processing)
    ↓
PostgreSQL TRT Table (Aggregated Data)
    ↓
7-Module Processing Pipeline
    ↓
Final Postback Table (Attribution Report)
    ↓
Email Notification + UI Update
```

---

## 🚀 System Capacity

- **Concurrent Requests**: 10 maximum
- **Data Volume per Request**: 300M - 500M records
- **Thread Count per Request**: 5 parallel threads
- **In-Memory Processing**: 60M-100M records per thread
- **System Throughput**: 5 billion records daily capacity
- **Response Time**: Sub-90 minute average per request

---

**Document Version**: 1.0
**Last Updated**: February 9, 2026
**System**: Campaign Attribution Management (CAM)
