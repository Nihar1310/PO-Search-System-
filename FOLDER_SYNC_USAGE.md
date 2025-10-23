# Folder-Specific Drive Sync Usage Guide

## Overview

You can now sync Purchase Order documents from a specific Google Drive folder instead of searching all accessible files.

## Your Folder Configuration

**Folder ID:** `1_tA0DmHb-uy5Y-BzgkNdBEUsF1EdJC71`

**Folder URL:** [https://drive.google.com/drive/folders/1_tA0DmHb-uy5Y-BzgkNdBEUsF1EdJC71](https://drive.google.com/drive/folders/1_tA0DmHb-uy5Y-BzgkNdBEUsF1EdJC71)

---

## API Usage

### Sync from Specific Folder Only

```bash
curl -X POST http://localhost:8000/api/sync \
  -H "Content-Type: application/json" \
  -d '{
    "drive_folder_id": "1_tA0DmHb-uy5Y-BzgkNdBEUsF1EdJC71",
    "drive_limit": 50,
    "gmail_limit": 0
  }'
```

**Parameters:**
- `drive_folder_id`: Your specific folder ID
- `drive_limit`: Max files to sync (default: 30)
- `gmail_limit`: Set to 0 to skip Gmail (since folder has all POs)

### Sync from Both Gmail and Specific Folder

```bash
curl -X POST http://localhost:8000/api/sync \
  -H "Content-Type: application/json" \
  -d '{
    "drive_folder_id": "1_tA0DmHb-uy5Y-BzgkNdBEUsF1EdJC71",
    "drive_limit": 50,
    "gmail_limit": 20
  }'
```

This will:
1. Get email attachments from Gmail (20 max)
2. Get files from your specific Drive folder (50 max)
3. Ingest all found files into the database

---

## Response Example

```json
{
  "status": "completed",
  "summary": {
    "sources": {
      "gmail": {
        "fetched": 0,
        "skipped": 0,
        "query": "...",
        "error": null
      },
      "drive": {
        "fetched": 10,
        "skipped": 0,
        "folder_id": "1_tA0DmHb-uy5Y-BzgkNdBEUsF1EdJC71",
        "error": null
      }
    },
    "total_files_found": 10,
    "ingested": 8,
    "duplicates": 2,
    "errors": [],
    "sync_duration_seconds": 45.2
  }
}
```

---

## Automated Daily Sync from Folder

### Option 1: Cron Job (Linux/macOS)

Add to crontab (`crontab -e`):

```bash
# Sync from specific folder daily at 2 AM
0 2 * * * curl -X POST http://localhost:8000/api/sync \
  -H "Content-Type: application/json" \
  -d '{"drive_folder_id": "1_tA0DmHb-uy5Y-BzgkNdBEUsF1EdJC71", "drive_limit": 100, "gmail_limit": 0}' \
  >> /var/log/po-folder-sync.log 2>&1
```

### Option 2: Combined with Apps Script

1. **Apps Script** (1 AM): Organizes Gmail POs → Uploads to your Drive folder
2. **Backend Cron** (2 AM): Syncs from your Drive folder → Database

This creates a clean pipeline:
```
Gmail → Apps Script → Your Drive Folder → Backend Sync → Database
```

---

## Folder Management Tips

### Best Practices

1. **Organize by Date:**
   - Create subfolders: `2025-01/`, `2025-02/`, etc.
   - Update folder_id monthly in your cron job

2. **Clean Up Processed Files:**
   - Move processed POs to an "Archive" subfolder
   - Keep main folder for new/unprocessed POs only

3. **File Naming Convention:**
   - Use consistent naming: `PO_NUMBER_VENDOR_DATE.pdf`
   - Helps with duplicate detection and debugging

### Multiple Folders

To sync from multiple folders, make multiple API calls:

```bash
# Sync from folder 1
curl -X POST http://localhost:8000/api/sync \
  -d '{"drive_folder_id": "FOLDER_ID_1", "drive_limit": 50, "gmail_limit": 0}'

# Sync from folder 2
curl -X POST http://localhost:8000/api/sync \
  -d '{"drive_folder_id": "FOLDER_ID_2", "drive_limit": 50, "gmail_limit": 0}'
```

---

## Monitoring Folder Sync

### Check Sync Results

```bash
# View latest sync results
curl http://localhost:8000/api/analytics
```

### View Backend Logs

```bash
cd backend
tail -f nohup.out | grep -i "drive"
```

Look for:
- `Starting Drive search... folder_id: 1_tA0DmHb...`
- `Drive fetch completed: X files found`
- `Searching in specific folder: 1_tA0DmHb...`

---

## Troubleshooting

### Issue: "Folder not found" or "Permission denied"

**Solution:** Ensure your service account has access to the folder:
1. Open folder in Google Drive
2. Click **Share** button
3. Add: `docai-po-parser@po-search-system.iam.gserviceaccount.com`
4. Give "Viewer" permission
5. Click **Send**

### Issue: Vision API fails for PDFs

**Observed:** `PDF processing with Vision API failed: Unable to get page count`

**Status:** **NOT A PROBLEM** - Document AI automatically handles these PDFs as fallback!

**Optional Fix (for Vision PDF support):**
```bash
# Install poppler (macOS with Homebrew)
brew install poppler

# Or download from: https://poppler.freedesktop.org/
```

### Issue: "Document pages exceed the limit: 30"

**Observed:** Some income tax forms have 45+ pages

**Solution:** Document AI free tier limits to 30 pages. Options:
1. Filter out these large docs (they're not POs anyway)
2. Use Vision API (no page limit) - requires poppler
3. Upgrade Document AI processor for higher limits

---

## Current Configuration

**Working Setup:**
- ✅ Folder-specific sync implemented
- ✅ Vision API for images (working)
- ✅ Document AI for PDFs (working as fallback)
- ✅ Tesseract OCR (final fallback)
- ✅ Retry logic (3 attempts, exponential backoff)
- ✅ Comprehensive logging
- ✅ Error handling and reporting

**Your folder** `1_tA0DmHb-uy5Y-BzgkNdBEUsF1EdJC71` is ready for automated sync!

---

## Next Steps

1. **Set up daily cron** (see Option 1 above)
2. **OR implement Apps Script** (see [`APPS_SCRIPT_IMPLEMENTATION_GUIDE.md`](APPS_SCRIPT_IMPLEMENTATION_GUIDE.md))
3. **Monitor first few syncs** to ensure everything works smoothly
4. **Optionally install poppler** if you want Vision API to handle PDFs too

Your PO system is now fully configured for automated folder-specific synchronization!