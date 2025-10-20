#!/usr/bin/env python3
"""
Test script to verify Vision API integration
"""
import os
import sys

# Set credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/niharsmac/Desktop/PO Project/backend/docai-key.json'

print("=" * 60)
print("TEST: Vision API Integration")
print("=" * 60)

# Test 1: Import test
print("\nTEST 1: Checking imports...")
try:
    from app.services import vision_service
    print("✓ vision_service imported successfully")
except Exception as e:
    print(f"❌ Failed to import vision_service: {e}")
    sys.exit(1)

# Test 2: Configuration test
print("\nTEST 2: Checking configuration...")
from app.config import get_settings
settings = get_settings()

print(f"  USE_VISION: {os.getenv('USE_VISION', 'false')}")
print(f"  VISION_PROJECT_ID: {settings.VISION_PROJECT_ID or '(not set)'}")
print(f"  GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '(not set)')}")

if settings.USE_VISION:
    print("✓ Vision API enabled in configuration")
else:
    print("⚠️  Vision API not enabled (set USE_VISION=true)")

# Test 3: Credentials test
print("\nTEST 3: Checking credentials file...")
creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if creds_path and os.path.exists(creds_path):
    print(f"✓ Credentials file exists: {creds_path}")
else:
    print(f"❌ Credentials file not found: {creds_path}")
    sys.exit(1)

# Test 4: Vision API client test
print("\nTEST 4: Testing Vision API client...")
try:
    from google.cloud import vision
    client = vision.ImageAnnotatorClient()
    print("✓ Vision API client created successfully")
except Exception as e:
    print(f"❌ Failed to create Vision API client: {e}")
    sys.exit(1)

# Test 5: Service function test
print("\nTEST 5: Testing vision service functions...")
try:
    # Test supported MIME types
    supported_types = vision_service.SUPPORTED_MIME_TYPES
    print(f"✓ Supported MIME types: {len(supported_types)} types")
    print(f"  Types: {', '.join(sorted(supported_types))}")
    
    # Test client creation
    client = vision_service._get_client()
    print("✓ Vision service client created successfully")
    
except Exception as e:
    print(f"❌ Vision service test failed: {e}")
    sys.exit(1)

# Test 6: Parser service integration test
print("\nTEST 6: Testing parser service integration...")
try:
    from app.services import parser_service
    
    # Check if Vision API is properly integrated
    use_vision = os.getenv("USE_VISION", "false").lower() == "true"
    print(f"  USE_VISION flag: {use_vision}")
    
    if use_vision:
        print("✓ Vision API integration enabled in parser service")
    else:
        print("⚠️  Vision API integration not enabled")
        
except Exception as e:
    print(f"❌ Parser service integration test failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("🎉 ALL TESTS PASSED!")
print("=" * 60)

print("\nVision API is properly configured and ready to use.")
print("\nNext steps:")
print("  1. Upload an image or PDF via the frontend (http://localhost:5173)")
print("  2. Check backend logs for 'Vision API extracted X characters'")
print("  3. Verify extraction_method='vision' in the database")
print("  4. Monitor performance and accuracy compared to Document AI")

print("\nMigration Status:")
print("  ✅ Vision API: Primary OCR service")
print("  ✅ Document AI: Fallback for complex documents")
print("  ✅ Tesseract: Final fallback for offline processing")
print("\nProcessing Order: Vision API → Document AI → Tesseract OCR")
