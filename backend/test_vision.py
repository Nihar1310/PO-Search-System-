#!/usr/bin/env python3
"""Test script to verify Vision API access and functionality"""

import os
import sys

# Set credentials path
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/niharsmac/Desktop/PO Project/backend/docai-key.json'

def test_vision_api_auth():
    """Test Vision API authentication and basic functionality"""
    print("=" * 60)
    print("Testing Google Cloud Vision API")
    print("=" * 60)
    
    try:
        from google.cloud import vision
        print("✅ google-cloud-vision package imported successfully")
        
        # Create client
        client = vision.ImageAnnotatorClient()
        print("✅ Vision API client created successfully")
        print(f"   Using credentials: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")
        
        # Create a simple test image with text
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        # Create test image
        img = Image.new('RGB', (400, 150), color='white')
        draw = ImageDraw.Draw(img)
        
        # Add test text (simulating a PO document)
        test_text = "Purchase Order #PO-12345\nDate: 2025-01-15\nClient: Test Company"
        draw.text((20, 20), test_text, fill='black')
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes_value = img_bytes.getvalue()
        
        print(f"✅ Created test image ({len(img_bytes_value)} bytes)")
        
        # Test Vision API text detection
        image = vision.Image(content=img_bytes_value)
        response = client.text_detection(image=image)
        
        if response.error.message:
            print(f"❌ Vision API error: {response.error.message}")
            return False
        
        if response.text_annotations:
            detected_text = response.text_annotations[0].description
            print(f"✅ Vision API text detection successful!")
            print(f"   Detected text: '{detected_text.strip()}'")
            print(f"   Number of text blocks: {len(response.text_annotations)}")
            return True
        else:
            print("⚠️  Vision API responded but detected no text")
            return False
            
    except ImportError as exc:
        print(f"❌ Import error: {exc}")
        print("   Run: pip install google-cloud-vision Pillow")
        return False
    except Exception as exc:
        print(f"❌ Vision API test failed: {exc}")
        print(f"\nPossible issues:")
        print("  1. Vision API not enabled in Google Cloud Console")
        print("     → Go to: https://console.cloud.google.com/apis/library/vision.googleapis.com")
        print("  2. Service account lacks Vision API permissions")
        print("     → Grant role: Cloud Vision API User or imageAnnotator")
        print("  3. Credentials file path incorrect or invalid")
        print(f"     → Check: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")
        return False


def test_vision_with_real_file():
    """Test Vision API with an actual file from the filesystem"""
    print("\n" + "=" * 60)
    print("Testing Vision API with Real File")
    print("=" * 60)
    
    try:
        from google.cloud import vision
        import glob
        
        # Look for a sample PDF or image
        test_files = glob.glob("*.pdf") + glob.glob("*.png") + glob.glob("*.jpg")
        
        if not test_files:
            print("⚠️  No test files found in backend directory")
            print("   Skipping real file test")
            return None
        
        test_file = test_files[0]
        print(f"Using test file: {test_file}")
        
        client = vision.ImageAnnotatorClient()
        
        with open(test_file, 'rb') as f:
            content = f.read()
        
        if test_file.endswith('.pdf'):
            print("   Note: PDF files need conversion to images for Vision API")
            print("   (This is handled automatically in the parser service)")
            return None
        
        image = vision.Image(content=content)
        response = client.text_detection(image=image)
        
        if response.text_annotations:
            detected_text = response.text_annotations[0].description
            text_preview = detected_text[:200] + "..." if len(detected_text) > 200 else detected_text
            print(f"✅ Successfully extracted text from {test_file}")
            print(f"   Text length: {len(detected_text)} characters")
            print(f"   Preview: {text_preview}")
            return True
        else:
            print(f"⚠️  No text detected in {test_file}")
            return False
            
    except Exception as exc:
        print(f"❌ Real file test failed: {exc}")
        return False


def check_requirements():
    """Check if all required packages are installed"""
    print("\n" + "=" * 60)
    print("Checking Requirements")
    print("=" * 60)
    
    requirements = {
        'google.cloud.vision': 'google-cloud-vision',
        'PIL': 'Pillow',
        'pdf2image': 'pdf2image (optional, for PDF support)',
    }
    
    all_ok = True
    for module_name, package_name in requirements.items():
        try:
            __import__(module_name)
            print(f"✅ {package_name} installed")
        except ImportError:
            print(f"❌ {package_name} NOT installed")
            if 'optional' not in package_name.lower():
                all_ok = False
    
    return all_ok


if __name__ == "__main__":
    print("\nGoogle Cloud Vision API Test Suite\n")
    
    # Check requirements
    if not check_requirements():
        print("\n❌ Missing required packages. Install them first.")
        sys.exit(1)
    
    # Test authentication and basic functionality
    auth_ok = test_vision_api_auth()
    
    # Test with real file if available
    file_ok = test_vision_with_real_file()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Authentication & Basic OCR: {'✅ PASS' if auth_ok else '❌ FAIL'}")
    if file_ok is not None:
        print(f"Real File OCR: {'✅ PASS' if file_ok else '❌ FAIL'}")
    else:
        print(f"Real File OCR: ⊘ SKIPPED (no test files or PDF)")
    
    if auth_ok:
        print("\n🎉 Vision API is working correctly!")
        print("   Your system can now use Vision API for OCR")
        print("   Fallback to Document AI will work automatically if needed")
    else:
        print("\n⚠️  Vision API setup incomplete")
        print("   Follow the steps in VISION_API_SETUP_GUIDE.md")
    
    sys.exit(0 if auth_ok else 1)
