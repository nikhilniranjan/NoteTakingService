import requests

API_GATEWAY_URL = "https://d22dme7p69.execute-api.ap-south-1.amazonaws.com/production/notes"  # Update with your actual endpoint
SAMPLE_URL = "https://www.gutenberg.org/files/1342/1342-0.txt"  # Pride and Prejudice

def lambda_handler(event=None, context=None):
	results = []
	# Create note
	try:
		response = requests.get(SAMPLE_URL)
		sample_text = response.text[:1000]
		payload = {
			"note_id": "sample-001",
			"version": "1",
			"content": sample_text,
			"title": "Sample Note from Web",
			#"author": "Jane Austen"
		}
		api_response = requests.post(API_GATEWAY_URL, json=payload)
		results.append({
			"action": "create",
			"statusCode": api_response.status_code,
			"body": api_response.text
		})
	except Exception as e:
		results.append({
			"action": "create",
			"statusCode": 500,
			"body": f"Error posting to API Gateway (create): {e}"
		})

	# Update note
	try:
		response = requests.get(SAMPLE_URL)
		sample_text = response.text[1000:2000]
		payload = {
			"note_id": "sample-001",
			"version": "2",
			"content": sample_text,
			"title": "Updated Sample Note from Web",
			#"author": "Jane Austen"
		}
		api_response = requests.put(API_GATEWAY_URL, json=payload)
		results.append({
			"action": "update",
			"statusCode": api_response.status_code,
			"body": api_response.text
		})
	except Exception as e:
		results.append({
			"action": "update",
			"statusCode": 500,
			"body": f"Error posting to API Gateway (update): {e}"
		})

	return {"results": results}


