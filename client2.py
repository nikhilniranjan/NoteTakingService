import requests
import logging
import time
import random
import json

API_GATEWAY_URL = "https://d22dme7p69.execute-api.ap-south-1.amazonaws.com/production_retrieve/notes"  # Update with your actual endpoint
RETRIEVE_NOTE_URL = "https://d22dme7p69.execute-api.ap-south-1.amazonaws.com/production_retrieve/retrieve"  # Update with your actual endpoint for retrieval

METRICS_URL = "https://d22dme7p69.execute-api.ap-south-1.amazonaws.com/production_metrics/metrics"  # Update with your actual metrics endpoint

SAMPLE_URLS = ["https://www.gutenberg.org/files/1342/1342-0.txt",
               "https://www.gutenberg.org/files/2701/2701-0.txt",
               "https://www.gutenberg.org/files/84/84-0.txt",
               "https://www.gutenberg.org/files/100/100-0.txt",
               "https://www.gutenberg.org/files/2641/2641-0.txt",
               "https://www.gutenberg.org/files/37106/37106-0.txt",
               "https://www.gutenberg.org/files/98/98-0.txt",
               "https://www.gutenberg.org/files/1400/1400-0.txt",
               "https://www.gutenberg.org/files/768/768-0.txt",
               "https://www.gutenberg.org/files/2554/2554-0.txt"]

# Set up logging for Lambda/CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO,filename="squeezenotes.log",encoding='utf-8')

filepath = "/Users/nikhilniranjan/andromeda/training-files/"
data_files_count = 10
training_set_count = 10000
min_note_size = 100
max_note_size = 10000
sample_text = []
samples = []


# Download sample text
for i in range(len(SAMPLE_URLS)):
    response = requests.get(SAMPLE_URLS[i])
    sample_text.append(response.text)
    #print(len(sample_text[i]))


results = []
note_table = {}  # (note_id, version) -> content
note_ids = []
num_notes = 100 # 100
num_versions = 10 #10
num_notes_to_read = 100 #100

# Download sample text
#response = requests.get(SAMPLE_URL)
#sample_text = response.text

# 1. Create notes of varying lengths
for i in range(num_notes):
    selected_sample = random.randint(0, data_files_count - 1)
    note_id = f"note_{int(time.time())}_{i}"
    note_length = random.randint(min_note_size, max_note_size)
    #vary start point randomly
    start_point = random.randint(0, len(sample_text[selected_sample]) - note_length)
    content = sample_text[selected_sample][start_point:start_point + note_length]
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
        selected_sample = random.randint(0, data_files_count - 1)
        note_length = random.randint(min_note_size, max_note_size)
        start_point = random.randint(0, len(sample_text[selected_sample]) - note_length)
        content = sample_text[selected_sample][start_point:start_point + note_length]
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


time.sleep(60) # Wait for a while

# 3. Retrieve random notes and compare contents with retry logic
max_retries = 3
retry_delay = 1  # seconds
for _ in range(num_notes_to_read):
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
    metrics = json.loads(metrics_response.text)
    body = metrics.get('body')
    body_struct = json.loads(body)
    list_metrics = body_struct.get("notes_metrics", [])
    #print("length of the list is ", len(list_metrics))

    '''
    metrics = metrics_response.json()
    #print(metrics_json)
    returned_metrics = metrics.get("body", {})
    print(returned_metrics)
    print("\n********\n")
    first_metric = returned_metrics[0]
    #if (list_metrics == None):
    #    print("Empty list!\n")
    #print(list_metrics[0]["note_id"])
    #print("length of the list is ", len(list_metrics))
    print('foobar')
    print(first_metric)
    '''
    # Write all metrics fields to file
    with open("metrics_notes.txt", "w") as f:
        f.write("note_id,version,uncompressed_size,compression_ratio,decompression_latency,read_latency\n")
        for entry in list_metrics:
            note_id = entry.get("note_id", "")
            version = entry.get("version", "")
            uncompressed_size = entry.get("uncompressed_size") if entry.get("uncompressed_size") is not None else ""
            compression_ratio = entry.get("compression_ratio") if entry.get("compression_ratio") is not None else ""
            decompression_latency = entry.get("decompression_latency") if entry.get("decompression_latency") is not None else ""
            read_latency = entry.get("read_latency") if entry.get("read_latency") is not None else ""
            f.write(f"{note_id},{version},{uncompressed_size},{compression_ratio},{decompression_latency},{read_latency}\n")
    logger.info(f"Wrote metrics details to metrics_notes.txt")

    # Calculate averages
    compression_ratios = [entry.get("compression_ratio") for entry in list_metrics if isinstance(entry.get("compression_ratio"), (int, float))]
    decompression_latencies = [entry.get("decompression_latency") for entry in list_metrics if isinstance(entry.get("decompression_latency"), (int, float))]
    read_latencies = [entry.get("read_latency") for entry in list_metrics if isinstance(entry.get("read_latency"), (int, float))]
    avg_compression_ratio = round(sum(compression_ratios) / len(compression_ratios), 2) if compression_ratios else None
    avg_decompression_latency = round(sum(decompression_latencies) / len(decompression_latencies), 2) if decompression_latencies else None
    avg_read_latency = round(sum(read_latencies) / len(read_latencies), 2) if read_latencies else None

    # Calculate overall storage savings
    uncompressed_sizes = [entry.get("uncompressed_size") for entry in list_metrics if isinstance(entry.get("uncompressed_size"), (int, float)) and isinstance(entry.get("compression_ratio"), (int, float))]
    compressed_sizes = [entry.get("uncompressed_size") * entry.get("compression_ratio") for entry in list_metrics if isinstance(entry.get("uncompressed_size"), (int, float)) and isinstance(entry.get("compression_ratio"), (int, float))]
    total_uncompressed = sum(uncompressed_sizes)
    total_compressed = sum(compressed_sizes)
    storage_savings = round((total_uncompressed - total_compressed) / total_uncompressed, 2) if total_uncompressed > 0 else None

    logger.info(f"Average compression ratio: {avg_compression_ratio}")
    logger.info(f"Average decompression latency: {avg_decompression_latency}")
    logger.info(f"Average read latency: {avg_read_latency}")
    logger.info(f"Overall storage savings from compression: {storage_savings}")
    print(f"Average compression ratio: {avg_compression_ratio}")
    print(f"Average decompression latency: {avg_decompression_latency}")
    print(f"Average read latency: {avg_read_latency}")
    print(f"Overall storage savings from compression: {storage_savings}")
except Exception as e:
    logger.error(f"Error requesting or processing metrics: {e}")
    results.append({"action": "get_metrics", "statusCode": 500, "body": f"Error requesting metrics: {e}"})

logger.info(f"Client execution complete. Results: {results}")
