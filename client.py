import requests
import logging

API_GATEWAY_URL = "https://d22dme7p69.execute-api.ap-south-1.amazonaws.com/production_retrieve/notes"  # Update with your actual endpoint
RETRIEVE_NOTE_URL = "https://d22dme7p69.execute-api.ap-south-1.amazonaws.com/production_retrieve/retrieve"  # Update with your actual endpoint for retrieval
SAMPLE_URL = "https://www.gutenberg.org/files/1342/1342-0.txt"  # Pride and Prejudice

# Set up logging for Lambda/CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

#TBD: DONT HARDCODE VERSION NUMBER


def lambda_handler(event=None, context=None):
    results = []
    note_id = "sample-001"

    # 1. Create note (version 1)
    logger.info(f"Starting note creation for note_id={note_id}, version=1")
    try:
        response = requests.get(SAMPLE_URL)
        sample_text = response.text[:1000]
        payload = {
            "note_id": note_id,
            "version": "1",
            "content": sample_text,
            "title": "Sample Note from Web",
        }
        api_response = requests.post(API_GATEWAY_URL, json=payload)
        logger.info(f"Create response: status={api_response.status_code}, body={api_response.text}")
        results.append({
            "action": "create",
            "statusCode": api_response.status_code,
            "body": api_response.text
        })
    except Exception as e:
        logger.error(f"Error posting to API Gateway (create): {e}")
        results.append({
            "action": "create",
            "statusCode": 500,
            "body": f"Error posting to API Gateway (create): {e}"
        })

    # 2. Retrieve note (version 1) with retry logic
    import time
    logger.info(f"Retrieving note for note_id={note_id}, version=1 (with retry)")
    max_retries = 5
    retry_delay = 3  # seconds
    for attempt in range(1, max_retries + 1):
        try:
            params = {"note_id": note_id, "version": "1"}
            response = requests.get(RETRIEVE_NOTE_URL, params=params)
            logger.info(f"Retrieve v1 attempt {attempt}: status={response.status_code}, body={response.text}")
            # Check for 404 and specific error message
            if response.status_code == 404 and "Compressed note not found" in response.text:
                logger.info(f"Compressed note not found on attempt {attempt}. Retrying in {retry_delay} seconds...")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    continue
            results.append({
                "action": "retrieve_v1",
                "statusCode": response.status_code,
                "body": response.text,
                "attempt": attempt
            })
            break
        except Exception as e:
            logger.error(f"Error retrieving note v1 (attempt {attempt}): {e}")
            if attempt == max_retries:
                results.append({
                    "action": "retrieve_v1",
                    "statusCode": 500,
                    "body": f"Error retrieving note v1: {e}",
                    "attempt": attempt
                })
            else:
                time.sleep(retry_delay)

    # 3. Update note (version 2)
    logger.info(f"Updating note for note_id={note_id}, version=2")
    try:
        response = requests.get(SAMPLE_URL)
        sample_text = response.text[1000:2000]
        payload = {
            "note_id": note_id,
            "version": "2",
            "content": sample_text,
            "title": "Updated Sample Note from Web",
        }
        api_response = requests.put(API_GATEWAY_URL, json=payload)
        logger.info(f"Update response: status={api_response.status_code}, body={api_response.text}")
        results.append({
            "action": "update",
            "statusCode": api_response.status_code,
            "body": api_response.text
        })
    except Exception as e:
        logger.error(f"Error posting to API Gateway (update): {e}")
        results.append({
            "action": "update",
            "statusCode": 500,
            "body": f"Error posting to API Gateway (update): {e}"
        })

    # 4. Retrieve note (version 2)
    logger.info(f"Retrieving note for note_id={note_id}, version=2")
    try:
        params = {"note_id": note_id, "version": "2"}
        response = requests.get(RETRIEVE_NOTE_URL, params=params)
        logger.info(f"Retrieve v2 response: status={response.status_code}, body={response.text}")
        results.append({
            "action": "retrieve_v2",
            "statusCode": response.status_code,
            "body": response.text
        })
    except Exception as e:
        logger.error(f"Error retrieving note v2: {e}")
        results.append({
            "action": "retrieve_v2",
            "statusCode": 500,
            "body": f"Error retrieving note v2: {e}"
        })

    logger.info(f"Lambda execution complete. Results: {results}")
    return {"results": results}


