# NoteTakingService

## Overview

NoteTakingService is a distributed, versioned note-taking platform built on AWS using Lambda, S3, DynamoDB, SQS, and API Gateway. It supports note creation, updating, retrieval, compression, decompression, and metrics tracking. The system is designed for scalability, observability, and efficient storage using Zstandard compression.

## Architecture
- **AWS Lambda:** Handles note CRUD, compression, decompression, and metrics.
- **S3:** Stores note content (uncompressed and compressed).
- **DynamoDB:** Stores note metadata, including version, compression ratio, decompression latency, read latency, and uncompressed size.
- **SQS:** Triggers asynchronous compression workflows.
- **API Gateway:** Exposes REST endpoints for all Lambda functions.

## Setup Instructions

### Prerequisites
- AWS account with permissions for Lambda, S3, DynamoDB, SQS, and API Gateway
- Python 3.8+
- `boto3`, `requests`, `pyzstd` (or `zstandard`)

### Deployment Steps
1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd NoteTakingService
   ```
2. **Configure AWS resources:**
   - Create S3 bucket for notes
   - Create DynamoDB table with `note_id` (partition key) and `version` (sort key)
   - Create SQS queue
   - Deploy Lambda functions (`upload_notes.py`, `compress_notes.py`, `retrieve_note.py`, `get_metrics.py`)
   - Set up API Gateway endpoints for each Lambda
3. **Set environment variables:**
   - `NOTES_BUCKET`, `NOTES_TABLE`, `NOTES_QUEUE_URL` in Lambda configuration

### Local Development
- Install dependencies:
  ```bash
  pip install boto3 requests pyzstd
  ```
- Run client scripts for automated testing:
  ```bash
  python client2.py
  ```

## API Usage

### Endpoints
- **Create/Update Note:**
  - `POST/PUT /notes`
  - Payload: `{ "note_id": "...", "version": "...", "content": "...", "title": "..." }`
- **Retrieve Note:**
  - `GET /retrieve?note_id=...&version=...`
- **Get Metrics:**
  - `GET /metrics`
  - Response: `{ "notes_metrics": [ { "note_id": "...", "version": "...", "uncompressed_size": ..., "compression_ratio": ..., "decompression_latency": ..., "read_latency": ... }, ... ] }`

## Metrics
- **Compression Ratio:** Ratio of compressed to uncompressed size
- **Decompression Latency:** Time to decompress a note
- **Read Latency:** Time taken to read and retrieve a note from storage
- **Uncompressed Size:** Original size of the note
- **Storage Savings:** Calculated in client scripts

## Client Scripts
- `client2.py`: Automated workflows for note creation, updating, retrieval, and metrics analysis
- Output files: `metrics_notes.txt`, `squeezenotes.log`

## Dictionary Training
#might not need this line
- `train.py`: Example for training Zstandard dictionaries using sample notes

## Troubleshooting
- Ensure all AWS resources are correctly configured and environment variables are set
- Check CloudWatch logs for Lambda errors
#Might not need this line below
- For compression errors, verify sample sizes and formats in dictionary training

## License
MIT

## Author
Nikhil Niranjan
