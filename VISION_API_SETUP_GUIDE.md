# Google Cloud Vision API Setup Guide
## Enable Vision API with Existing Service Account

This guide walks you through enabling Cloud Vision API in your existing Google Cloud project and configuring permissions for your service account.

---

## Prerequisites

✅ You already have:
- Google Cloud project: `po-search-system`
- Service account key file: [`docai-key.json`](backend/docai-key.json)
- Document AI already working

---

## Step 1: Enable Cloud Vision API

### 1.1 Open Google Cloud Console
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project: **po-search-system** (top dropdown)

### 1.2 Enable the API
1. In the left sidebar, click **APIs & Services** → **Library**
2. Search for: `Cloud Vision API`
3. Click on **Cloud Vision API** in results
4. Click the **Enable** button
5. Wait 1-2 minutes for API to be enabled

**Confirmation:** You'll see "API enabled" message and the page will show usage graphs.

---

## Step 2: Grant Vision API Permissions to Service Account

### 2.1 Find Your Service Account Email
1. Open [`docai-key.json`](backend/docai-key.json) in a text editor
2. Look for the `client_email` field:
   ```json
   {
     "client_email": "something@po-search-system.iam.gserviceaccount.com",
     ...
   }
   ```
3. Copy this email address

### 2.2 Grant Vision API Role
1. In Google Cloud Console, go to **IAM & Admin** → **IAM**
2. Find your service account in the list (use the email from step 2.1)
3. Click the **Edit** (pencil) icon next to it
4. Click **+ Add Another Role**
5. Search for and select: **Cloud Vision AI Service Agent** 
   - Or alternatively: **Cloud Vision API User** (more restrictive, recommended)
6. Click **Save**

### Alternative: Using gcloud CLI
```bash
# Get your service account email from docai-key.json
SERVICE_ACCOUNT="your-sa@po-search-system.iam.gserviceaccount.com"

# Grant Vision API permissions
gcloud projects add-iam-policy-binding po-search-system \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/cloudvision.imageAnnotator"
```

---

## Step 3: Install Vision API Python Package

### 3.1 Install the Package
```bash
cd backend
source ../.venv/bin/activate  # Activate virtual environment
pip install google-cloud-vision
```

### 3.2 Verify Installation
```bash
python -c "from google.cloud import vision; print('Vision API installed successfully')"
```

### 3.3 Update requirements.txt
Add to [`backend/requirements.txt`](backend/requirements.txt):
```
google-cloud-vision>=3.4.0
```

---

## Step 4: Verify Credentials Work

### 4.1 Check Service Account Permissions
Create a test script: `backend/test_vision.py`

```python
#!/usr/bin/env python3
"""Test script to verify Vision API access"""

import os
from google.cloud import vision

# Set credentials (should match your .env)
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/niharsmac/Desktop/PO Project/backend/docai-key.json'

def test_vision_api():
    """Test Vision API with a simple detection"""
    try:
        client = vision.ImageAnnotatorClient()
        print("✅ Vision API client created successfully")
        
        # Test with a simple text image
        # Create a minimal test
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        # Create test image with text
        img = Image.new('RGB', (300, 100), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Purchase Order #12345", fill='black')
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
        
        # Test Vision API
        image = vision.Image(content=img_bytes)
        response = client.text_detection(image=image)
        
        if response.text_annotations:
            detected_text = response.text_annotations[0].description
            print(f"✅ Vision API working! Detected text: '{detected_text}'")
            return True
        else:
            print("⚠️  Vision API responded but detected no text")
            return False
            
    except Exception as exc:
        print(f"❌ Vision API test failed: {exc}")
        print(f"\nPossible issues:")
        print("  1. Vision API not enabled in Google Cloud Console")
        print("  2. Service account lacks Vision API permissions")
        print("  3. Credentials file path incorrect")
        return False

if __name__ == "__main__":
    test_vision_api()
```

### 4.2 Run the Test
```bash
cd backend
python test_vision.py
```

**Expected Output:**
```
✅ Vision API client created successfully
✅ Vision API working! Detected text: 'Purchase Order #12345'
```

**If you see an error**, it means one of these needs fixing:
1. Vision API not enabled (go back to Step 1)
2. Service account lacks permissions (go back to Step 2)
3. Wrong credentials path (check GOOGLE_APPLICATION_CREDENTIALS)

---

## Step 5: Verify Integration in Your App

### 5.1 Check Environment Variables

Verify [`backend/.env`](backend/.env) has:
```bash
USE_VISION=true
USE_DOCAI=true
VISION_PROJECT_ID=po-search-system
GOOGLE_APPLICATION_CREDENTIALS=/Users/niharsmac/Desktop/PO Project/backend/docai-key.json
```

### 5.2 Test End-to-End
```bash
# Start backend (if not running)
cd backend
source ../.venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, test sync with Vision API
curl -X POST http://localhost:8000/api/sync \
  -H "Content-Type: application/json" \
  -d '{"gmail_limit": 3, "drive_limit": 3}'
```

### 5.3 Check Logs
The backend logs should show which extraction method was used:
```
INFO: Vision API extracted 1234 characters from sample.pdf
```
OR if Vision fails:
```
ERROR: Vision API extraction failed for sample.pdf: ...
INFO: Extracted 1234 characters via Document AI
```

---

## Understanding Your Credentials

### What is docai-key.json?

Your [`docai-key.json`](backend/docai-key.json) is a **Service Account Key** that contains:
```json
{
  "type": "service_account",
  "project_id": "po-search-system",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "your-sa@po-search-system.iam.gserviceaccount.com",
  "client_id": "...",
  ...
}
```

### How It Works:

```
┌────────────────────────┐
│   docai-key.json       │  Single credential file
│   (Service Account)    │  Used by all Google Cloud APIs
└───────────┬────────────┘
            │
            │ Authenticates to:
            │
     ┌──────┴──────┬──────────────┬───────────────┐
     │             │              │               │
     ↓             ↓              ↓               ↓
┌─────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐
│Document │  │ Vision   │  │  Drive   │  │   Gmail    │
│   AI    │  │   API    │  │   API    │  │    API     │
└─────────┘  └──────────┘  └──────────┘  └────────────┘
     ✅           ❓            ✅             ✅
   Working    Need to      Working        Working
              Enable +
              Grant Role
```

### Key Point: 
**You only need ONE service account key file.** It can access multiple APIs if:
1. Each API is enabled in the project
2. The service account has the right IAM roles

---

## Step 6: Troubleshooting Common Issues

### Issue 1: "Permission Denied" Error
```
google.api_core.exceptions.PermissionDenied: 403 Cloud Vision API has not been used in project...
```

**Solution:** Vision API not enabled. Go to Step 1.

### Issue 2: "Service account lacks permission"
```
Permission 'cloudvision.images.annotate' denied on resource
```

**Solution:** Service account needs Vision API role. Go to Step 2.2.

### Issue 3: "Module not found: google.cloud.vision"
```
ModuleNotFoundError: No module named 'google.cloud.vision'
```

**Solution:** Install the package. Go to Step 3.

### Issue 4: Vision API Returns No Text
```
Vision API returned no text for filename.pdf
```

**Possible causes:**
- PDF has no text (blank pages)
- Image quality too low
- Wrong mime type

**Solution:** The system will automatically fall back to Document AI.

---

## Cost Optimization Strategy

### Vision vs Document AI Pricing

| API | Cost | Best For |
|-----|------|----------|
| **Vision API** | $1.50 / 1,000 images | Simple scans, clear text, images |
| **Document AI** | $1.50 / page + processor fees | Complex forms, tables, handwriting |

### Recommended Strategy (Already Implemented ✅)

```python
# From parser_service.py (lines 36-49)
if USE_VISION:
    # Try Vision first (cheaper, faster)
    text = extract_with_vision()
    
if not text and USE_DOCAI:
    # Fall back to Document AI (more accurate, expensive)
    text = extract_with_docai()

if not text:
    # Final fallback to free Tesseract OCR
    text = extract_with_tesseract()
```

### Expected Savings:
- **Vision handles 60-70%** of documents → Save ~50% on OCR costs
- **Document AI handles 20-30%** of complex documents → Maintain accuracy
- **Tesseract handles 5-10%** as final backup → Free safety net

---

## Quick Start Checklist

Follow this checklist in order:

### Google Cloud Setup (10-15 minutes)
- [ ] Go to [Google Cloud Console](https://console.cloud.google.com)
- [ ] Select project `po-search-system`
- [ ] Navigate to **APIs & Services** → **Library**
- [ ] Enable **Cloud Vision API**
- [ ] Go to **IAM & Admin** → **IAM**
- [ ] Find your service account (email from docai-key.json)
- [ ] Add role: **Cloud Vision API User**
- [ ] Save changes

### Backend Setup (5 minutes)
- [ ] `cd backend && source ../.venv/bin/activate`
- [ ] `pip install google-cloud-vision`
- [ ] `python test_vision.py` (from Step 4)
- [ ] Verify test passes with ✅ messages

### Integration Test (2 minutes)
- [ ] Start backend server
- [ ] Run sync: `curl -X POST http://localhost:8000/api/sync`
- [ ] Check logs for "Vision API extracted" messages
- [ ] Verify documents are being parsed

### Done! ✅
If all checks pass, Vision API is now your primary OCR with Document AI as fallback.

---

## Summary

**You don't need new credentials!** Just:
1. Enable Vision API in Google Cloud Console (2 minutes)
2. Grant Vision API role to existing service account (1 minute)  
3. Install python package (1 minute)
4. Test and verify (5 minutes)

**Total setup time: ~10 minutes**

The code is already written and ready - you just need to enable the API and grant permissions!