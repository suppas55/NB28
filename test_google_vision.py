import os
import requests
import base64
import json

def test_google_vision_api(api_key, image_path=None):
    """
    Test Google Vision API with your API key
    """
    
    # Create a simple test image (1x1 pixel PNG) if no image provided
    if image_path is None:
        # Base64 encoded 1x1 transparent PNG
        test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    else:
        # Read and encode the provided image
        with open(image_path, "rb") as image_file:
            test_image_b64 = base64.b64encode(image_file.read()).decode('utf-8')
    
    # Google Vision API endpoint - try project-specific endpoint first
    # You may need to replace PROJECT_ID with your actual project ID
    # url = f"https://vision.googleapis.com/v1/projects/PROJECT_ID/images:annotate?key={api_key}"
    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
    
    # Request payload
    payload = {
        "requests": [
            {
                "image": {
                    "content": test_image_b64
                },
                "features": [
                    {
                        "type": "LABEL_DETECTION",
                        "maxResults": 5
                    }
                ]
            }
        ]
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        print("Testing Google Vision API...")
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API Key is working!")
            print(f"Response: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ API request failed with status code: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        return False

if __name__ == "__main__":
    # Get API key from environment variable or input
    api_key = os.getenv('GOOGLE_VISION_API_KEY')
    
    if not api_key:
        api_key = input("Enter your Google Vision API key: ")
    
    if api_key:
        # Test with default image (1x1 PNG)
        print("Testing with default test image...")
        test_google_vision_api(api_key)
        
        # Optionally test with your own image
        image_path = input("\nEnter path to test image (or press Enter to skip): ").strip()
        if image_path and os.path.exists(image_path):
            print(f"\nTesting with your image: {image_path}")
            test_google_vision_api(api_key, image_path)
        elif image_path:
            print(f"❌ Image file not found: {image_path}")
    else:
        print("❌ No API key provided")
