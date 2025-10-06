

import requests

def lambda_handler(event, context):
	# 1. Fetch a sample text from the web (e.g., Project Gutenberg)
	SAMPLE_URL = "https://www.gutenberg.org/files/1342/1342-0.txt"  # Pride and Prejudice
	try:
		response = requests.get(SAMPLE_URL)
		sample_text = response.text[:1000]  # Use first 1000 chars for brevity
	except Exception as e:
		return {
			"statusCode": 500,
			"body": f"Failed to fetch sample text: {e}"
		}

	# 2. Define the API Gateway endpoint for upload_notes
	# Replace this with your actual API Gateway endpoint URL
	API_GATEWAY_URL = "https://l6wq49qc0k.execute-api.ap-south-1.amazonaws.com/production"

	# 3. Prepare the payload
	payload = {
		"note_id": "sample-001",
		"content": sample_text,
		"title": "Sample Note from Web",
		#"author": "Jane Austen"
	}

	# 4. Make the POST request
	try:
		api_response = requests.post(API_GATEWAY_URL, json=payload)
		result = {
			"statusCode": api_response.status_code,
			"body": api_response.text
		}
	except Exception as e:
		result = {
			"statusCode": 500,
			"body": f"Error posting to API Gateway: {e}"
		}
	return result
 

