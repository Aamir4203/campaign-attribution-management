const express = require('express');
const multer = require('multer');
const fs = require('fs').promises;
const path = require('path');

// Load configuration
const REPORT_FILES_BASE_PATH = process.env.REPORT_FILES_BASE_PATH ||
  path.join(__dirname, '..', 'REPORT_FILES');

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: async (req, file, cb) => {
    const { requestId } = req.body;
    if (!requestId) {
      return cb(new Error('Request ID is required'), '');
    }

    const uploadPath = path.join(REPORT_FILES_BASE_PATH, requestId);

    try {
      await fs.mkdir(uploadPath, { recursive: true });
      cb(null, uploadPath);
    } catch (error) {
      cb(error, '');
    }
  },
  filename: (req, file, cb) => {
    const { requestId, fileType } = req.body;
    let filename;

    switch (fileType) {
      case 'timestamp':
        filename = `TimeStampReport${requestId}.csv`;
        break;
      case 'cpm_report':
        filename = `CpmReport${requestId}.csv`;
        break;
      case 'decile_report':
        filename = `DecileReport${requestId}.csv`;
        break;
      default:
        return cb(new Error('Invalid file type'), '');
    }

    cb(null, filename);
  }
});

const upload = multer({
  storage,
  fileFilter: (req, file, cb) => {
    // Only allow CSV files
    if (file.mimetype === 'text/csv' ||
        file.originalname.toLowerCase().endsWith('.csv') ||
        file.mimetype === 'application/vnd.ms-excel') {
      cb(null, true);
    } else {
      cb(new Error('Only CSV files are allowed'), false);
    }
  },
  limits: {
    fileSize: 50 * 1024 * 1024, // 50MB limit
  }
});

// Generate next request ID
const generateRequestId = async () => {
  try {
    // For now, generate a simple incremental ID
    // In production, this should query the database for the next ID
    const timestamp = Date.now();
    const randomSuffix = Math.floor(Math.random() * 1000);
    return `${timestamp}${randomSuffix}`;
  } catch (error) {
    throw new Error('Failed to generate request ID');
  }
};

// File upload endpoint
const uploadFile = async (req, res) => {
  try {
    const uploadSingle = upload.single('file');

    uploadSingle(req, res, async (err) => {
      if (err) {
        return res.status(400).json({
          success: false,
          error: err.message
        });
      }

      if (!req.file) {
        return res.status(400).json({
          success: false,
          error: 'No file uploaded'
        });
      }

      const { requestId, fileType } = req.body;
      if (!['timestamp', 'cpm_report', 'decile_report'].includes(fileType)) {
        return res.status(400).json({
          success: false,
          error: 'Invalid file type'
        });
      }

      // Perform backend validation
      const validation = await validateUploadedFile(req.file.path, fileType);

      res.json({
        success: true,
        file: {
          originalName: req.file.originalname,
          filename: req.file.filename,
          path: req.file.path,
          size: req.file.size,
          fileType,
          requestId
        },
        validation
      });
    });
  } catch (error) {
    console.error('File upload error:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error'
    });
  }
};

// File validation function with comprehensive checks
async function validateUploadedFile(filePath, fileType) {
  try {
    const fileContent = await fs.readFile(filePath, 'utf-8');
    const lines = fileContent.split('\n').filter(line => line.trim());

    const validation = {
      isValid: true,
      errors: [],
      warnings: [],
      fileInfo: {
        lines: lines.length,
        columns: lines[0] ? lines[0].split('|').length : 0,
        hasHeader: false
      }
    };

    if (lines.length === 0) {
      validation.errors.push('File is empty');
      validation.isValid = false;
      return validation;
    }

    // File type specific validation
    let hasHeader = false;
    switch (fileType) {
      case 'timestamp':
        hasHeader = validateTimestampFile(lines, validation);
        break;
      case 'cpm_report':
        hasHeader = validateCpmReportFile(lines, validation);
        break;
      case 'decile_report':
        hasHeader = validateDecileReportFile(lines, validation);
        break;
    }

    if (hasHeader) {
      validation.warnings.push('File appears to have headers. Please ensure file has no header row and is pipe-separated.');
    }

    validation.isValid = validation.errors.length === 0;
    validation.fileInfo.hasHeader = hasHeader;
    return validation;
  } catch (error) {
    return {
      isValid: false,
      errors: ['Failed to read file content'],
      warnings: [],
      fileInfo: { lines: 0, columns: 0, hasHeader: false }
    };
  }
}

function validateTimestampFile(lines, validation) {
  let hasHeader = false;

  if (lines.length < 1) {
    validation.errors.push('Timestamp file must have at least 1 data row');
    return hasHeader;
  }

  const firstRow = lines[0].split('|');
  if (firstRow.length < 3) {
    validation.errors.push('Timestamp file must have at least 3 columns');
    return hasHeader;
  }

  // Check if first row is header
  const date1 = firstRow[0].trim();
  const date2 = firstRow[1].trim();
  const date3 = firstRow[2].trim();

  if (!isValidDate(date1) || !isValidDate(date2) || !isValidDate(date3)) {
    hasHeader = true;

    if (lines.length < 2) {
      validation.errors.push('Timestamp file must have at least 1 data row after header');
      return hasHeader;
    }
  }

  // Validate data rows
  const startRow = hasHeader ? 1 : 0;
  for (let i = startRow; i < Math.min(startRow + 5, lines.length); i++) {
    const columns = lines[i].split('|');
    if (columns.length >= 3) {
      const d1 = columns[0].trim();
      const d2 = columns[1].trim();
      const d3 = columns[2].trim();

      if (!isValidDate(d1) || !isValidDate(d2) || !isValidDate(d3)) {
        validation.errors.push(`Invalid date format in row ${i + 1}. Expected YYYY-MM-DD format`);
        break;
      }
    }
  }

  return hasHeader;
}

function validateCpmReportFile(lines, validation) {
  let hasHeader = false;

  if (lines.length < 1) {
    validation.errors.push('CPM report must have at least 1 data row');
    return hasHeader;
  }

  const firstRow = lines[0].split('|');
  if (firstRow.length !== 14) {
    validation.errors.push('CPM report must have exactly 14 columns');
    return hasHeader;
  }

  // Check if first row is header
  const numericColumns = [2, 3, 4, 5, 6, 7];
  let numericIssues = 0;

  for (const colIndex of numericColumns) {
    const value = firstRow[colIndex].trim().replace(/,/g, '');
    if (!isValidNumber(value)) {
      numericIssues++;
    }
  }

  if (numericIssues >= numericColumns.length / 2) {
    hasHeader = true;
  }

  // Validate data rows
  const startRow = hasHeader ? 1 : 0;
  for (let i = startRow; i < Math.min(startRow + 5, lines.length); i++) {
    const columns = lines[i].split('|');
    if (columns.length !== 14) {
      validation.errors.push(`Row ${i + 1} has incorrect number of columns`);
      break;
    }

    const date = columns[1].trim();
    if (!isValidDate(date)) {
      validation.errors.push(`Invalid date format in row ${i + 1}: ${date}`);
      break;
    }

    for (const colIndex of numericColumns) {
      const value = columns[colIndex].trim().replace(/,/g, '');
      if (!isValidNumber(value)) {
        validation.errors.push(`Invalid numeric value in row ${i + 1}, column ${colIndex + 1}: ${columns[colIndex]}`);
        break;
      }
    }
  }

  return hasHeader;
}

function validateDecileReportFile(lines, validation) {
  let hasHeader = false;

  if (lines.length < 1) {
    validation.errors.push('Decile report must have at least 1 data row');
    return hasHeader;
  }

  const firstRow = lines[0].split('|');
  if (firstRow.length !== 8) {
    validation.errors.push('Decile report must have exactly 8 columns');
    return hasHeader;
  }

  // Check if first row is header
  let numericIssues = 0;
  for (let colIndex = 0; colIndex <= 3; colIndex++) {
    const value = firstRow[colIndex].trim().replace(/,/g, '');
    if (!isValidNumber(value)) {
      numericIssues++;
    }
  }

  if (numericIssues >= 2) {
    hasHeader = true;
  }

  // Validate data rows
  const startRow = hasHeader ? 1 : 0;
  for (let i = startRow; i < Math.min(startRow + 5, lines.length); i++) {
    const columns = lines[i].split('|');
    if (columns.length !== 8) {
      validation.errors.push(`Row ${i + 1} has incorrect number of columns`);
      break;
    }

    for (let colIndex = 0; colIndex <= 3; colIndex++) {
      const value = columns[colIndex].trim().replace(/,/g, '');
      if (!isValidNumber(value)) {
        validation.errors.push(`Invalid numeric value in row ${i + 1}, column ${colIndex + 1}: ${columns[colIndex]}`);
        break;
      }
    }
  }

  return hasHeader;
}

function isValidDate(dateStr) {
  if (!dateStr) return false;
  const date = new Date(dateStr);
  return !isNaN(date.getTime()) && /^\d{4}-\d{2}-\d{2}$/.test(dateStr);
}

function isValidNumber(value) {
  if (!value || value === '') return false;
  return !isNaN(Number(value));
}

// Get file paths for a request
const getRequestFilePaths = (requestId) => {
  const requestPath = path.join(REPORT_FILES_BASE_PATH, requestId);
  return {
    timestamp: path.join(requestPath, `TimeStampReport${requestId}.csv`),
    cpmReport: path.join(requestPath, `CpmReport${requestId}.csv`),
    decileReport: path.join(requestPath, `DecileReport${requestId}.csv`)
  };
};

module.exports = {
  uploadFile,
  generateRequestId,
  getRequestFilePaths,
  REPORT_FILES_BASE_PATH
};
