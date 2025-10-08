#Create a lot of notes of varying lengths - create note id as a concatenation of timestamp and sequence number



#Update all of them a few times



#All the notes and versions and data should be in a hash table (note_id,version,content)



#In a loop, retrieve a random note from the table and check its contents and compare with original



#Retrieve metrics


import requests
import logging
import time
import random

API_GATEWAY_URL = "https://d22dme7p69.execute-api.ap-south-1.amazonaws.com/production_retrieve/notes"  # Update with your actual endpoint
RETRIEVE_NOTE_URL = "https://d22dme7p69.execute-api.ap-south-1.amazonaws.com/production_retrieve/retrieve"  # Update with your actual endpoint for retrieval

SAMPLE_URL = "https://www.gutenberg.org/files/1342/1342-0.txt"  # Pride and Prejudice
METRICS_URL = "https://d22dme7p69.execute-api.ap-south-1.amazonaws.com/production_metrics/metrics"  # Update with your actual metrics endpoint

# Set up logging for Lambda/CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO,filename="squeezenotes.log",encoding='utf-8')

#TBD: DONT HARDCODE VERSION NUMBER

results = []
note_table = {}  # (note_id, version) -> content
note_ids = []
num_notes = 2
num_versions = 2

# Download sample text
response = requests.get(SAMPLE_URL)
sample_text = response.text

# 1. Create notes of varying lengths
for i in range(num_notes):
    note_id = f"note_{int(time.time())}_{i}"
    note_length = random.randint(100, 1000)
    #vary start point randomly
    start_point = random.randint(0, len(sample_text) - note_length)
    content = sample_text[start_point:start_point + note_length]
    payload = {
        "note_id": note_id,
        "version": "1",
        "content": content,
        "title": f"Note {i}"
    }
    try:
        api_response = requests.post(API_GATEWAY_URL, json=payload)
        logger.info(f"Create note {note_id} response: status={api_response.status_code}")
        results.append({"action": "create", "note_id": note_id, "statusCode": api_response.status_code})
        note_table[(note_id, "1")] = content #version number is 1 on creation
        note_ids.append(note_id)
    except Exception as e:
        logger.error(f"Error creating note {note_id}: {e}")

# 2. Update all notes a few times
for version in range(2, num_versions + 1):
    for note_id in note_ids:
        note_length = random.randint(100, 1000)
        start_point = random.randint(0, len(sample_text) - note_length)
        content = sample_text[start_point:start_point + note_length]
        payload = {
            "note_id": note_id,
            "version": str(version),
            "content": content,
            "title": f"Note {note_id} v{version}"
        }
        try:
            api_response = requests.put(API_GATEWAY_URL, json=payload)
            logger.info(f"Update note {note_id} v{version} response: status={api_response.status_code}")
            results.append({"action": "update", "note_id": note_id, "version": version, "statusCode": api_response.status_code})
            note_table[(note_id, str(version))] = content
        except Exception as e:
            logger.error(f"Error updating note {note_id} v{version}: {e}")

print("Sleeping")
time.sleep(10) # Wait for a while to ensure all updates are processed

# 3. Retrieve random notes and compare contents with retry logic
max_retries = 3
retry_delay = 1  # seconds
for _ in range(num_notes * num_versions):
    note_id = random.choice(note_ids)
    version = str(random.randint(1, num_versions))
    params = {"note_id": note_id, "version": version}
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(RETRIEVE_NOTE_URL, params=params)
            logger.info(f"Retrieve note {note_id} v{version} attempt {attempt}: status={response.status_code}")
            if response.status_code == 200:
                body = response.json()
                retrieved_content = body.get("content", "")
                original_content = note_table.get((note_id, version), None)
                match = (retrieved_content == original_content)
                results.append({"action": "retrieve_compare", "note_id": note_id, "version": version, "match": match, "attempt": attempt})
                break
            else:
                logger.info(f"Note {note_id} v{version} not found on attempt {attempt}. Retrying in {retry_delay} seconds...")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    continue
                results.append({"action": "retrieve_compare", "note_id": note_id, "version": version, "statusCode": response.status_code, "attempt": attempt})
                break
        except Exception as e:
            logger.error(f"Error retrieving note {note_id} v{version} (attempt {attempt}): {e}")
            if attempt == max_retries:
                results.append({"action": "retrieve_compare", "note_id": note_id, "version": version, "error": str(e), "attempt": attempt})
            else:
                time.sleep(retry_delay)


# 4. Get metrics from metrics endpoint and process results
logger.info(f"Requesting metrics from API Gateway: {METRICS_URL}")
try:
    metrics_response = requests.get(METRICS_URL)
    logger.info(f"Metrics response: status={metrics_response.status_code}, body={metrics_response.text}")
    results.append({"action": "get_metrics", "statusCode": metrics_response.status_code, "body": metrics_response.text})

    # Parse metrics JSON
    metrics_json = metrics_response.json()
    compression_ratios = metrics_json.get("compression_ratios", [])
    latencies = metrics_json.get("decompression_latencies", [])

    # Convert compression ratios to microseconds (assuming ratio is a float, multiply by 1_000_000)
    compression_ratios_micro = [cr * 1_000_000 for cr in compression_ratios]

    # Write pairs to file
    with open("metrics_pairs.txt", "w") as f:
        f.write("compression_ratio_microseconds,decompression_latency\n")
        for cr_micro, lat in zip(compression_ratios_micro, latencies):
            f.write(f"{cr_micro},{lat}\n")
    logger.info(f"Wrote metrics pairs to metrics_pairs.txt")
except Exception as e:
    logger.error(f"Error requesting or processing metrics: {e}")
    results.append({"action": "get_metrics", "statusCode": 500, "body": f"Error requesting metrics: {e}"})

logger.info(f"Client execution complete. Results: {results}")
