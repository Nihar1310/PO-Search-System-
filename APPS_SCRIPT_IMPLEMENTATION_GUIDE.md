# Google Apps Script Implementation Guide
## Automated Gmail to Drive PO Organization

This guide provides step-by-step instructions to implement Google Apps Script automation that will:
1. Monitor Gmail for Purchase Order emails
2. Extract PO attachments (PDF, DOC, DOCX)
3. Upload them to a dedicated Google Drive folder
4. Label/archive processed emails (optional)
5. Run automatically every day

---

## Architecture Overview

```
┌─────────────────┐
│   Gmail Inbox   │  New PO emails arrive
└────────┬────────┘
         │
         │ Daily at 1 AM
         ↓
┌─────────────────┐
│  Apps Script    │  Searches for PO emails
│   (Cloud-Run)   │  Extracts attachments
└────────┬────────┘
         │
         │ Uploads
         ↓
┌─────────────────┐
│  Drive Folder   │  "PO_Inbox"
│  Centralized    │  All PO files organized here
└────────┬────────┘
         │
         │ Backend sync (2 AM)
         ↓
┌─────────────────┐
│  PO Database    │  Files parsed and stored
└─────────────────┘
```

---

## Step 1: Create Google Drive Folder

### 1.1 Create the Folder
1. Go to [Google Drive](https://drive.google.com)
2. Click **+ New** → **Folder**
3. Name it: `PO_Inbox` (or your preferred name)
4. Click **Create**

### 1.2 Get the Folder ID
1. Open the newly created folder
2. Look at the URL in your browser:
   ```
   https://drive.google.com/drive/folders/1a2b3c4d5e6f7g8h9i0j
                                           ^^^^^^^^^^^^^^^^^^^
                                           This is your Folder ID
   ```
3. Copy the Folder ID (everything after `/folders/`)
4. Save it - you'll need it in Step 3

**Example:**
- URL: `https://drive.google.com/drive/folders/1XyZ9AbC_dEfGhIjKlMnOpQ`
- Folder ID: `1XyZ9AbC_dEfGhIjKlMnOpQ`

---

## Step 2: Open Apps Script Editor

### 2.1 Access Apps Script
1. Go to [script.google.com](https://script.google.com)
2. Click **+ New project** (top left)
3. You'll see a blank script editor with `function myFunction() {}`

### 2.2 Rename the Project
1. Click "Untitled project" at the top
2. Rename it to: `PO Gmail to Drive Automation`
3. Click anywhere to save

---

## Step 3: Write the Apps Script Code

### 3.1 Main Script (Code.gs)

Replace the default code with this complete script:

```javascript
/**
 * PO Gmail to Drive Automation
 * Searches Gmail for Purchase Order emails and uploads attachments to Drive
 */

// ========== CONFIGURATION ==========
const CONFIG = {
  // Replace with your Drive folder ID from Step 1
  DRIVE_FOLDER_ID: '1XyZ9AbC_dEfGhIjKlMnOpQ',  // ⚠️ CHANGE THIS!
  
  // Gmail search query (customize if needed)
  GMAIL_QUERY: 'filename:(po OR purchase order) OR subject:(purchase order) has:attachment newer_than:2d',
  
  // Maximum emails to process per run (prevents timeout)
  MAX_EMAILS_PER_RUN: 50,
  
  // Label to apply to processed emails (set to null to disable)
  PROCESSED_LABEL: 'PO/Processed',
  
  // Supported file extensions
  ALLOWED_EXTENSIONS: ['.pdf', '.doc', '.docx'],
  
  // Archive processed emails? (true/false)
  ARCHIVE_EMAILS: false
};

// ========== MAIN FUNCTION ==========
/**
 * Main function that runs on schedule
 */
function processPOEmailsFromGmail() {
  const startTime = new Date();
  Logger.log('=== PO Processing Started at ' + startTime.toISOString() + ' ===');
  
  const stats = {
    emailsProcessed: 0,
    filesUploaded: 0,
    filesSkipped: 0,
    errors: []
  };
  
  try {
    // Get the Drive folder
    const folder = getDriveFolder();
    if (!folder) {
      throw new Error('Drive folder not found. Check DRIVE_FOLDER_ID in config.');
    }
    
    // Get or create label (if configured)
    const label = CONFIG.PROCESSED_LABEL ? getOrCreateLabel(CONFIG.PROCESSED_LABEL) : null;
    
    // Search Gmail for PO emails
    const threads = GmailApp.search(CONFIG.GMAIL_QUERY, 0, CONFIG.MAX_EMAILS_PER_RUN);
    Logger.log('Found ' + threads.length + ' email threads');
    
    // Process each thread
    threads.forEach(thread => {
      try {
        processThread(thread, folder, label, stats);
      } catch (error) {
        const errorMsg = 'Error processing thread: ' + error.message;
        Logger.log(errorMsg);
        stats.errors.push(errorMsg);
      }
    });
    
  } catch (error) {
    const errorMsg = 'Critical error: ' + error.message;
    Logger.log(errorMsg);
    stats.errors.push(errorMsg);
  }
  
  // Log final statistics
  const endTime = new Date();
  const duration = (endTime - startTime) / 1000;
  
  Logger.log('=== PO Processing Completed ===');
  Logger.log('Duration: ' + duration + ' seconds');
  Logger.log('Emails processed: ' + stats.emailsProcessed);
  Logger.log('Files uploaded: ' + stats.filesUploaded);
  Logger.log('Files skipped (duplicates): ' + stats.filesSkipped);
  Logger.log('Errors: ' + stats.errors.length);
  
  if (stats.errors.length > 0) {
    Logger.log('Error details:');
    stats.errors.forEach((error, index) => {
      Logger.log('  ' + (index + 1) + '. ' + error);
    });
  }
  
  // Send summary email (optional)
  sendSummaryEmail(stats, duration);
  
  return stats;
}

// ========== HELPER FUNCTIONS ==========

/**
 * Get Drive folder by ID
 */
function getDriveFolder() {
  try {
    return DriveApp.getFolderById(CONFIG.DRIVE_FOLDER_ID);
  } catch (error) {
    Logger.log('Error accessing Drive folder: ' + error.message);
    return null;
  }
}

/**
 * Get existing label or create new one
 */
function getOrCreateLabel(labelName) {
  let label = GmailApp.getUserLabelByName(labelName);
  if (!label) {
    label = GmailApp.createLabel(labelName);
    Logger.log('Created new label: ' + labelName);
  }
  return label;
}

/**
 * Process a single email thread
 */
function processThread(thread, folder, label, stats) {
  const messages = thread.getMessages();
  
  messages.forEach(message => {
    stats.emailsProcessed++;
    const attachments = message.getAttachments();
    
    if (attachments.length === 0) {
      return;
    }
    
    attachments.forEach(attachment => {
      try {
        processAttachment(attachment, folder, stats);
      } catch (error) {
        const errorMsg = 'Error processing attachment: ' + error.message;
        Logger.log(errorMsg);
        stats.errors.push(errorMsg);
      }
    });
  });
  
  // Label the thread as processed
  if (label) {
    thread.addLabel(label);
  }
  
  // Archive the thread (if configured)
  if (CONFIG.ARCHIVE_EMAILS) {
    thread.moveToArchive();
  }
}

/**
 * Process a single attachment
 */
function processAttachment(attachment, folder, stats) {
  const fileName = attachment.getName();
  const fileExtension = getFileExtension(fileName);
  
  // Check if file type is supported
  if (!CONFIG.ALLOWED_EXTENSIONS.includes(fileExtension.toLowerCase())) {
    Logger.log('Skipping unsupported file type: ' + fileName);
    return;
  }
  
  // Check for duplicates
  if (fileExistsInFolder(folder, fileName)) {
    Logger.log('Skipping duplicate file: ' + fileName);
    stats.filesSkipped++;
    return;
  }
  
  // Upload to Drive
  try {
    const file = folder.createFile(attachment);
    Logger.log('Uploaded: ' + fileName + ' (Size: ' + formatBytes(file.getSize()) + ')');
    stats.filesUploaded++;
  } catch (error) {
    throw new Error('Failed to upload ' + fileName + ': ' + error.message);
  }
}

/**
 * Check if file already exists in folder
 */
function fileExistsInFolder(folder, fileName) {
  const files = folder.getFilesByName(fileName);
  return files.hasNext();
}

/**
 * Get file extension from filename
 */
function getFileExtension(fileName) {
  const match = fileName.match(/\.[^.]+$/);
  return match ? match[0] : '';
}

/**
 * Format bytes to human-readable string
 */
function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Send summary email (optional)
 */
function sendSummaryEmail(stats, duration) {
  const recipientEmail = Session.getActiveUser().getEmail();
  
  // Only send if there were uploads or errors
  if (stats.filesUploaded === 0 && stats.errors.length === 0) {
    return;
  }
  
  const subject = stats.errors.length > 0 
    ? '⚠️ PO Sync Completed with Errors' 
    : '✅ PO Sync Completed Successfully';
  
  const body = `
PO Gmail to Drive Sync Summary
================================

Duration: ${duration} seconds
Emails Processed: ${stats.emailsProcessed}
Files Uploaded: ${stats.filesUploaded}
Files Skipped: ${stats.filesSkipped}
Errors: ${stats.errors.length}

${stats.errors.length > 0 ? 'Errors:\n' + stats.errors.map((e, i) => `${i + 1}. ${e}`).join('\n') : ''}

Drive Folder: https://drive.google.com/drive/folders/${CONFIG.DRIVE_FOLDER_ID}
  `;
  
  try {
    MailApp.sendEmail(recipientEmail, subject, body);
  } catch (error) {
    Logger.log('Failed to send summary email: ' + error.message);
  }
}

// ========== UTILITY FUNCTIONS ==========

/**
 * Test function - run this manually to test the script
 */
function testScript() {
  Logger.log('=== Running Test ===');
  const stats = processPOEmailsFromGmail();
  Logger.log('Test completed. Check logs above for details.');
  return stats;
}

/**
 * View Drive folder in browser
 */
function openDriveFolder() {
  const url = 'https://drive.google.com/drive/folders/' + CONFIG.DRIVE_FOLDER_ID;
  Logger.log('Drive folder URL: ' + url);
  return url;
}

/**
 * Clean up old triggers (if needed)
 */
function deleteAllTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    ScriptApp.deleteTrigger(trigger);
  });
  Logger.log('Deleted ' + triggers.length + ' triggers');
}
```

### 3.2 Update Configuration

**⚠️ IMPORTANT:** Update line 9 with your actual Drive Folder ID from Step 1:

```javascript
DRIVE_FOLDER_ID: 'YOUR_ACTUAL_FOLDER_ID_HERE',
```

---

## Step 4: Test the Script

### 4.1 Manual Test Run
1. In the Apps Script editor, select `testScript` from the function dropdown (top toolbar)
2. Click the **Run** button (▶️)
3. **First time only:** You'll see an authorization prompt:
   - Click **Review permissions**
   - Choose your Google account
   - Click **Advanced** → **Go to [Project Name] (unsafe)**
   - Click **Allow**

### 4.2 Check Results
1. Click **View** → **Logs** (or press Ctrl+Enter / Cmd+Enter)
2. You should see output like:
   ```
   === Running Test ===
   === PO Processing Started at 2025-01-18T... ===
   Found 3 email threads
   Uploaded: PO_12345.pdf (Size: 245 KB)
   Skipping duplicate file: PO_12346.pdf
   === PO Processing Completed ===
   Duration: 12.5 seconds
   Emails processed: 3
   Files uploaded: 1
   Files skipped: 1
   Errors: 0
   ```

### 4.3 Verify in Drive
1. Go to your Drive folder
2. Confirm that PO files have been uploaded

---

## Step 5: Set Up Automated Schedule

### 5.1 Create Time-Based Trigger
1. In Apps Script editor, click **Triggers** icon (⏰) on the left sidebar
2. Click **+ Add Trigger** (bottom right)
3. Configure the trigger:
   - **Choose which function to run:** `processPOEmailsFromGmail`
   - **Choose which deployment should run:** `Head`
   - **Select event source:** `Time-driven`
   - **Select type of time based trigger:** `Day timer`
   - **Select time of day:** `1am to 2am` (or your preferred time)
4. Click **Save**

### 5.2 Notification Settings
1. Still in Triggers page, click **Notifications** (⚙️ icon near top right)
2. Configure:
   - **Failures:** `Notify me daily` (recommended)
   - **Other errors:** `Notify me daily` (optional)
3. Click **Save**

---

## Step 6: Update Backend Sync Configuration

Now that Gmail POs are organized in Drive, update your backend sync to focus on this folder.

### 6.1 Modify Drive Query (Optional)

If you want the backend to ONLY sync from the PO_Inbox folder:

Edit [`backend/app/services/drive_service.py`](backend/app/services/drive_service.py):

```python
def search_drive_po_folder(folder_id: str, page_size: int = 50) -> List[Dict[str, Any]]:
    """Search for files within a specific Drive folder."""
    logger.info(f"Searching Drive folder {folder_id}")
    service = _build_service()
    
    # Query for files in specific folder
    query_string = f"'{folder_id}' in parents and (mimeType='application/pdf' or mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document' or mimeType='application/msword')"
    
    # ... rest of search logic ...
```

### 6.2 Set Up Backend Cron

Add a cron job to sync daily after Apps Script runs:

```bash
# Add to crontab (crontab -e)
# Run at 2 AM (1 hour after Apps Script)
0 2 * * * curl -X POST http://localhost:8000/api/sync \
  -H "Content-Type: application/json" \
  -d '{"gmail_limit": 0, "drive_limit": 100}' \
  >> /var/log/po-sync.log 2>&1
```

**Note:** `gmail_limit: 0` tells backend to skip Gmail (since Apps Script handles it)

---

## Step 7: Monitoring & Maintenance

### 7.1 Check Execution Logs
1. Go to [script.google.com](https://script.google.com)
2. Open your project
3. Click **Executions** icon (📋) on left sidebar
4. View recent runs, duration, and any errors

### 7.2 Email Notifications
- You'll receive daily emails for any failures
- Check your inbox for summary emails after each run

### 7.3 Manual Re-run (If Needed)
1. Open Apps Script project
2. Select `processPOEmailsFromGmail` function
3. Click Run button

---

## Customization Options

### Option 1: Change Search Criteria

Modify `GMAIL_QUERY` in config (line 11):

```javascript
// Search last 7 days instead of 2
GMAIL_QUERY: 'filename:(po OR purchase order) has:attachment newer_than:7d',

// Search specific sender
GMAIL_QUERY: 'from:vendor@example.com has:attachment',

// Multiple criteria
GMAIL_QUERY: '(subject:po OR subject:purchase order) from:vendor@example.com newer_than:2d',
```

### Option 2: Add File Renaming

Add this function before `processAttachment`:

```javascript
function renameFile(fileName, message) {
  const date = Utilities.formatDate(message.getDate(), 'GMT', 'yyyy-MM-dd');
  const sender = message.getFrom().match(/<(.+)>/)?.[1] || 'unknown';
  return date + '_' + sender + '_' + fileName;
}
```

Then in `processAttachment`, before creating file:

```javascript
const newFileName = renameFile(fileName, message);
const file = folder.createFile(attachment.copyBlob().setName(newFileName));
```

### Option 3: Organize by Date Subfolders

Add this function:

```javascript
function getOrCreateSubfolder(parentFolder, subfolderName) {
  const folders = parentFolder.getFoldersByName(subfolderName);
  if (folders.hasNext()) {
    return folders.next();
  }
  return parentFolder.createFolder(subfolderName);
}
```

Then in `processThread`, before processing attachments:

```javascript
const monthFolder = getOrCreateSubfolder(folder, Utilities.formatDate(new Date(), 'GMT', 'yyyy-MM'));
// Use monthFolder instead of folder for uploads
```

---

## Troubleshooting

### Issue: "Drive folder not found"
**Solution:** Double-check your `DRIVE_FOLDER_ID` in the config matches the ID from Step 1.

### Issue: "Authorization error"
**Solution:** 
1. Delete all triggers
2. Run `testScript` manually
3. Re-authorize the script
4. Re-create the trigger

### Issue: "Execution timeout"
**Solution:** Reduce `MAX_EMAILS_PER_RUN` to 25 or lower.

### Issue: "No files being uploaded"
**Solution:**
1. Check Gmail search query is finding emails
2. Verify attachments have supported extensions (.pdf, .doc, .docx)
3. Check execution logs for errors

### Issue: "Duplicate files keep uploading"
**Solution:** The script checks for exact filename matches. If vendors use different filenames each time, duplicates can't be detected. Consider adding custom duplicate logic based on file size or content hash.

---

## Complete Workflow Timeline

```
1:00 AM - Apps Script runs
          ├─ Searches Gmail for PO emails (last 2 days)
          ├─ Extracts PDF/DOC/DOCX attachments
          ├─ Uploads new files to Drive/PO_Inbox
          ├─ Labels processed emails
          └─ Sends summary email

2:00 AM - Backend sync runs
          ├─ Searches Drive/PO_Inbox folder
          ├─ Downloads new PO files
          ├─ Parses with Document AI
          ├─ Stores in database
          └─ Logs results

Throughout day - POs are searchable in your app
```

---

## Next Steps

After successful implementation:

1. ✅ Monitor for 1 week to ensure stability
2. ✅ Adjust `GMAIL_QUERY` based on your actual email patterns
3. ✅ Consider adding file renaming for better organization
4. ✅ Set up monthly subfolder organization if volume is high
5. ✅ Add frontend "Sync Now" button for manual triggers

---

## Summary Checklist

- [ ] Created `PO_Inbox` folder in Google Drive
- [ ] Copied folder ID
- [ ] Created Apps Script project
- [ ] Pasted and configured script code
- [ ] Tested script manually
- [ ] Verified files uploaded to Drive
- [ ] Set up daily trigger (1 AM)
- [ ] Configured email notifications
- [ ] Set up backend cron (2 AM)
- [ ] Tested end-to-end flow
- [ ] Documented folder ID and schedule

**You're done!** Your PO system will now automatically sync daily. 🎉