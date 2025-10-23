#!/usr/bin/env python3
"""
Test script to verify Document AI integration
"""
import os
import sys

# Set credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/niharsmac/Desktop/PO Project/backend/docai-key.json'

# Test 1: Import test
print("=" * 60)
print("TEST 1: Checking imports...")
try:
    from app.services import docai_service
    print("✓ docai_service imported successfully")
except Exception as e:
    print(f"❌ Failed to import docai_service: {e}")
    sys.exit(1)

# Test 2: Configuration test
print("\n" + "=" * 60)
print("TEST 2: Checking configuration...")
from app.config import get_settings
settings = get_settings()

print(f"  USE_DOCAI: {os.getenv('USE_DOCAI', 'false')}")
print(f"  DOCAI_PROJECT_ID: {settings.DOCAI_PROJECT_ID or '(not set)'}")
print(f"  DOCAI_LOCATION: {settings.DOCAI_LOCATION or '(not set)'}")
print(f"  DOCAI_PROCESSOR_ID: {settings.DOCAI_PROCESSOR_ID or '(not set)'}")
print(f"  GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '(not set)')}")

if not settings.DOCAI_PROJECT_ID or not settings.DOCAI_PROCESSOR_ID:
    print("❌ Document AI settings are missing")
    sys.exit(1)
print("✓ All Document AI settings configured")

# Test 3: Credentials file test
print("\n" + "=" * 60)
print("TEST 3: Checking credentials file...")
creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if os.path.exists(creds_path):
    print(f"✓ Credentials file exists: {creds_path}")
else:
    print(f"❌ Credentials file not found: {creds_path}")
    sys.exit(1)

# Test 4: Client initialization test
print("\n" + "=" * 60)
print("TEST 4: Testing Document AI client...")
try:
    from google.cloud import documentai
    print("✓ google.cloud.documentai imported")
    
    # Try to create client
    client = documentai.DocumentProcessorServiceClient()
    print("✓ Document AI client created successfully")
except Exception as e:
    print(f"❌ Failed to create Document AI client: {e}")
    sys.exit(1)

# Test 5: Processor path test
print("\n" + "=" * 60)
print("TEST 5: Verifying processor path...")
try:
    processor_path = client.processor_path(
        settings.DOCAI_PROJECT_ID,
        settings.DOCAI_LOCATION,
        settings.DOCAI_PROCESSOR_ID
    )
    print(f"✓ Processor path: {processor_path}")
except Exception as e:
    print(f"❌ Failed to construct processor path: {e}")
    sys.exit(1)

# Summary
print("\n" + "=" * 60)
print("🎉 ALL TESTS PASSED!")
print("=" * 60)
print("\nDocument AI is properly configured and ready to use.")
print("\nNext steps:")
print("  1. Upload a PDF via the frontend (http://localhost:5173)")
print("  2. Check backend logs for 'Extracted X characters via Document AI'")
print("  3. Verify extraction_method='docai' in the database")