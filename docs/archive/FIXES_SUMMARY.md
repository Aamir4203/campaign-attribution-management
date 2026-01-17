# File Upload Issues Fixed - December 24, 2025

## ✅ **All Issues Resolved**

### **Issue 1: Database Table Name** 
- ✅ **Fixed**: Changed `requests` table back to `"APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND_TEST"`
- **Location**: `shared/config/app.yaml` line 13
- **Reason**: You're using test table to avoid production interference

### **Issue 2: Default Mode**
- ✅ **Fixed**: Changed default mode from `'text'` to `'upload'`  
- **Location**: `HybridFileInput.tsx` line 34
- **Result**: File upload mode is now the default when page loads

### **Issue 3: UI Design Improvements**
- ✅ **Fixed**: Removed expected filename display from upload components
- ✅ **Fixed**: Removed "upload a file and it will be saved to server automatically" text
- **Locations**:
  - `FileUploadWithValidation.tsx` - Removed expected filename
  - `ValidationIndicator.tsx` - Removed expected filename from validation result
  - `HybridFileInput.tsx` - Removed description text

### **Issue 4: Decile Report Validation**
- ✅ **Fixed**: Decile validation now requires **exactly 8 columns** (not 17)
- ✅ **Added**: Proper column validation based on `requestValidation.py`:
  - Required columns: `["Delivered", "Opens", "clicks", "unsubs", "segment", "sub_seg", "decile", "old_delivered_per"]`
  - Numeric validation for: `["Delivered", "Opens", "clicks", "unsubs", "old_delivered_per"]`
  - `old_delivered_per` must be > 0 and not null
  - Required columns `["segment", "sub_seg", "decile"]` cannot be empty

### **Issue 4.1: Timestamp Validation Improved**
- ✅ **Enhanced**: Timestamp validation based on `requestValidation.py`:
  - Must have at least 3 columns for date validation
  - First 3 columns must contain valid dates
  - Date consistency check: `col1_date == col2_date == col3_date`
  - Headers expected (not header-less CSV)

### **Issue 4.2: CPM Validation Already Correct**
- ✅ **Confirmed**: CPM validation already requires exactly 14 columns
- ✅ **Confirmed**: All validation rules from `requestValidation.py` implemented

## **Validation Rules Now Match Original Script**

### **CPM Report (14 columns)**
```
["Campaign", "Date", "Delivered", "Unique Opens", "Clicks", 
 "Unsubs", "sb", "hb", "Subject Line", "Creative", 
 "Creative ID", "Offer ID", "segment", "sub_seg"]
```

### **Decile Report (8 columns)**  
```
["Delivered", "Opens", "clicks", "unsubs", 
 "segment", "sub_seg", "decile", "old_delivered_per"]
```

### **Timestamp Report (3+ columns)**
```
First 3 columns must be dates that match each other
Headers required
```

## **Testing Results Expected**

Now when you upload files:

1. **Decile report with 17 columns** → ❌ **WILL FAIL** (correctly)
2. **Decile report with 8 columns** → ✅ **WILL PASS** (if data valid)
3. **Default mode** → **File Upload mode** (not text)
4. **Clean UI** → No expected filename or server description text
5. **Test database** → Uses `*_TEST` table as requested

## **Files Modified**

1. `shared/config/app.yaml` - Fixed table name
2. `HybridFileInput.tsx` - Default mode + removed description 
3. `FileUploadWithValidation.tsx` - Removed expected filename
4. `ValidationIndicator.tsx` - Removed expected filename
5. `file_validation_service.py` - Fixed decile (8 cols) + timestamp validation
6. `uploadService.ts` - Fixed CPM prefix typo

**All issues are now resolved! The validation will properly reject your 17-column decile file and require exactly 8 columns as per the original script.** 🎉
