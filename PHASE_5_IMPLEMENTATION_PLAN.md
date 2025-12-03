# Phase 5: Hybrid Accordion Form & File Upload System

## 🎯 **Implementation Plan**

### **Current Date:** December 4, 2025

---

## 📋 **Overview**

**Goal:** Transform Add Request form into a modern hybrid accordion layout with automated file upload and validation system for report files.

---

## 🎨 **Part 1: Hybrid Accordion Layout**

### **Design Specifications:**

#### **Layout Structure:**
```
┌────────┬──────────────────────────────────────────────────────┐
│        │  📋 Add New Request          [Progress: 2/7 ✓]      │
│        ├──────────────────────────────────────────────────────┤
│  Nav   │                                                       │
│  Bar   │  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│        │  ┃ ▼  1. 👤 Client Information    [Complete ✓] ┃  │
│  •─────│  ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫  │
│  ├ 1   │  ┃  [Expanded content...]                       ┃  │
│  • 2   │  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│  ○ 3   │                                                       │
│  ○ 4   │  ┌─────────────────────────────────────────────┐  │
│  ○ 5   │  │ ▶  2. 📅 Campaign Dates         [Empty]    │  │
│  ○ 6   │  └─────────────────────────────────────────────┘  │
│  ○ 7   │                                                       │
│        │  [More sections...]                                  │
│ [Save] │                                                       │
└────────┴──────────────────────────────────────────────────────┘
```

#### **Sidebar Features:**
- ✅ Section navigation with icons
- ✅ Active indicator (filled circle)
- ✅ Completion status checkmarks
- ✅ Click to expand/jump to section
- ✅ Progress overview
- ✅ Quick actions (Save Draft, Skip)

#### **Accordion Features:**
- ✅ Collapsible sections with smooth animations
- ✅ Color-coded left borders per section
- ✅ Status indicators (Empty, In Progress, Complete, Error)
- ✅ Icon + Number + Title headers
- ✅ Expand/Collapse all buttons

---

## 📁 **Part 2: File Upload System**

### **Current Workflow (Manual):**
```
User places file manually → User enters path → Path saved to DB
```

### **New Workflow (Automated):**
```
User uploads Excel → Backend validates → Convert to CSV (pipe-delimited) 
→ Save to server path → Return path → Auto-populate in form → Submit
```

---

## 🔍 **Backend Validation Requirements**

### **Report Type 1: CPM Report (Campaign Performance Metrics)**

#### **File Requirements:**
- **Format:** Excel (.xlsx, .xls)
- **Columns:** 14 columns exactly
- **Column Names:** `Campaign|Date|Delivered|Unique Opens|Clicks|Unsubs|sb|hb|Subject Line|Creative|Creative ID|Offer ID|segment|sub_seg`
- **Delimiter:** Pipe-separated (`|`) in output CSV

#### **Validations:**
1. **Column Count:** Must be exactly 14 columns
2. **Date Format:** Column 'Date' must be YYYY-MM-DD format
3. **Numeric Columns:** Must be int/float
   - Delivered
   - Unique Opens
   - Clicks
   - Unsubs
   - sb (soft bounce)
   - hb (hard bounce)
4. **Duplicate Rows:** Check for duplicates based on:
   - Date + segment + sub_seg + Subject Line + Creative + Offer ID
5. **Special Characters:** Escape apostrophes in Subject Line (replace `'` with `''`)

#### **Error Messages:**
- ❌ "CPM Report: File must have exactly 14 columns"
- ❌ "CPM Report: Invalid date format in row X (expected YYYY-MM-DD)"
- ❌ "CPM Report: Non-numeric value found in 'Delivered' column at row X"
- ❌ "CPM Report: Duplicate rows detected (Date: X, segment: Y, sub_seg: Z)"

---

### **Report Type 2: Decile Report (Segmentation & Performance)**

#### **File Requirements:**
- **Format:** Excel (.xlsx, .xls)
- **Columns:** 8 columns exactly
- **Column Names:** `Delivered|Opens|clicks|unsubs|segment|sub_seg|decile|old_delivered_per`
- **Delimiter:** Pipe-separated (`|`) in output CSV

#### **Validations:**
1. **Column Count:** Must be exactly 8 columns
2. **Numeric Columns:** Must be int/float
   - Delivered
   - Opens
   - clicks
   - unsubs
3. **old_delivered_per:** Must be > 0 and not null
4. **Segment Matching:** Segments and sub_segments must match CPM report
5. **Delivered Count Comparison:** Sum of Delivered by segment/sub_seg must match CPM report
6. **Residual Date:** Must be >= max date in CPM report

#### **Error Messages:**
- ❌ "Decile Report: File must have exactly 8 columns"
- ❌ "Decile Report: Invalid numeric value in 'Delivered' column at row X"
- ❌ "Decile Report: old_delivered_per cannot be null or zero"
- ❌ "Decile Report: Segment mismatch with CPM report (segment: X, sub_seg: Y not found)"
- ❌ "Decile Report: Delivered count mismatch for segment X/sub_seg Y (CPM: A, Decile: B, Diff: C)"

---

### **Report Type 3: Unique Decile Report (Type 2 Only)**

#### **File Requirements:**
- Same as Decile Report
- **Only required when Request Type = Type 2**

#### **Validations:**
- Same validations as Decile Report

---

### **Report Type 4: Suppression File**

#### **File Requirements:**
- **Format:** Text file or CSV
- **Content:** Email addresses or MD5 hashes (one per line)

#### **Validations:**
1. **File Exists:** Path must be valid
2. **Format:** Valid email format or MD5 hash format

---

### **Report Type 5: Timestamp Report (Optional)**

#### **File Requirements:**
- **Format:** Excel or CSV
- **Columns:** 3 date columns
- **Validation:** All 3 date columns must have matching dates per row

#### **Validations:**
1. **Date Matching:** timestamp_col1 == timestamp_col2 == timestamp_col3 (date only)

---

## 🔧 **Backend API Specifications**

### **Endpoint 1: Upload CPM Report**
```python
POST /api/upload-cpm-report
Content-Type: multipart/form-data

Request:
{
  "file": <Excel file>,
  "client_id": 47,
  "week": "Q4_W8"
}

Response (Success):
{
  "success": true,
  "path": "/u1/reports/Ikea/Q4_W8/cpm_report_20251204_143022.csv",
  "validation": {
    "rows": 1250,
    "segments": ["Y", "N"],
    "date_range": "2025-11-18 to 2025-11-24",
    "total_delivered": 150000
  }
}

Response (Error):
{
  "success": false,
  "errors": [
    "Column count mismatch: expected 14, found 13",
    "Invalid date format in row 5: '2025-13-45'",
    "Duplicate rows detected: 3 duplicates found"
  ]
}
```

### **Endpoint 2: Upload Decile Report**
```python
POST /api/upload-decile-report
Content-Type: multipart/form-data

Request:
{
  "file": <Excel file>,
  "client_id": 47,
  "week": "Q4_W8",
  "cpm_report_path": "/u1/reports/Ikea/Q4_W8/cpm_report_20251204_143022.csv"
}

Response (Success):
{
  "success": true,
  "path": "/u1/reports/Ikea/Q4_W8/decile_report_20251204_143025.csv",
  "validation": {
    "rows": 20,
    "segments_matched": true,
    "delivered_count_matched": true,
    "comparison": [
      {"segment": "Y", "sub_seg": "Y", "cpm_count": 75000, "decile_count": 75000, "diff": 0},
      {"segment": "N", "sub_seg": "N", "cpm_count": 75000, "decile_count": 75000, "diff": 0}
    ]
  }
}

Response (Error):
{
  "success": false,
  "errors": [
    "Segment mismatch: segment 'X' found in decile but not in CPM",
    "Delivered count mismatch for segment Y/sub_seg Y: CPM=75000, Decile=76000, Diff=1000"
  ]
}
```

---

## 💻 **Frontend Implementation**

### **Component Structure:**
```
AddRequestForm/
├── AddRequestFormHybrid.tsx          # Main form with hybrid layout
├── SectionNavigator.tsx              # Left sidebar navigation
├── CollapsibleSection.tsx            # Reusable accordion section
├── FileUploadField.tsx               # File upload with validation UI
└── sections/
    ├── ClientInformationSection.tsx
    ├── CampaignDatesSection.tsx
    ├── FileOptionsSection.tsx
    ├── ReportPathsSection.tsx        # ← Modified with file uploads
    ├── SuppressionListSection.tsx
    ├── DataPrioritySection.tsx
    └── SqlQuerySection.tsx
```

### **File Upload Component:**
```tsx
<FileUploadField
  label="CPM Report"
  accept=".xlsx,.xls"
  uploadEndpoint="/api/upload-cpm-report"
  onUploadSuccess={(path) => setValue('reportpath', path)}
  onValidationError={(errors) => showErrors(errors)}
  validation={{
    columns: 14,
    requiredColumns: ['Date', 'Delivered', 'segment', 'sub_seg'],
    maxFileSize: 50 * 1024 * 1024  // 50MB
  }}
/>
```

---

## 📦 **Backend Requirements**

### **Python Dependencies:**
```python
pandas>=2.0.0          # Excel reading & CSV conversion
openpyxl>=3.1.0        # Excel file handling
xlrd>=2.0.0            # Legacy Excel support
werkzeug>=3.0.0        # Secure filename handling
```

### **Server Path Structure:**
```
/u1/reports/
├── {client_name}/
│   ├── {week}/
│   │   ├── cpm_report_{timestamp}.csv
│   │   ├── decile_report_{timestamp}.csv
│   │   ├── unique_decile_report_{timestamp}.csv
│   │   ├── suppression_{timestamp}.txt
│   │   └── timestamp_report_{timestamp}.csv
```

---

## 🎯 **Implementation Phases**

### **Phase 5.1: Hybrid Accordion Form Layout** ⏳
- [ ] Create SectionNavigator component
- [ ] Create CollapsibleSection component
- [ ] Migrate existing form sections to new layout
- [ ] Add progress tracking
- [ ] Add expand/collapse all functionality
- [ ] Style with Tailwind CSS

### **Phase 5.2: File Upload UI Components** ⏳
- [ ] Create FileUploadField component
- [ ] Add upload progress indicators
- [ ] Add validation error display
- [ ] Add file preview functionality
- [ ] Integrate with React Hook Form

### **Phase 5.3: Backend Upload & Validation API** ⏳
- [ ] Create upload endpoints
- [ ] Implement CPM report validation
- [ ] Implement Decile report validation
- [ ] Implement cross-report validation (segment matching, count comparison)
- [ ] Add file storage logic
- [ ] Add error handling & logging

### **Phase 5.4: Testing & Integration** ⏳
- [ ] Test file uploads with sample data
- [ ] Test validation scenarios
- [ ] Test error handling
- [ ] Integration testing with form submission
- [ ] Performance testing with large files

---

## 📊 **Success Criteria**

✅ **User Experience:**
- Users can navigate sections via sidebar
- Sections expand/collapse smoothly
- Progress is visible and accurate
- File upload is intuitive with clear feedback

✅ **Validation:**
- All backend validations match requestValidation.py logic
- Clear error messages for each validation failure
- Validation happens before form submission

✅ **Performance:**
- File uploads complete within 30 seconds for typical files (<10MB)
- Validation completes within 5 seconds
- No UI blocking during upload/validation

✅ **Production Ready:**
- Error handling for all edge cases
- Logging for debugging
- Security: file type validation, size limits, path traversal prevention
- Database path updates work correctly

---

## 🚀 **Next Steps**

**Ready to start implementation!**

Please confirm:
1. ✅ Proceed with Hybrid Accordion layout?
2. ✅ Start with CPM Report upload implementation?
3. ✅ Any specific client/week naming conventions for server paths?
4. ✅ Maximum file size limits?

**Let's build Phase 5!** 🎨🚀

