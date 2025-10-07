import os
import json
import boto3
import pyzstd as zstd
from botocore.exceptions import ClientError
import logging
import time

# Environment variables (set in Lambda console or SAM/CloudFormation)
S3_BUCKET = os.environ.get('NOTES_BUCKET', 'your-notes-bucket')
DDB_TABLE = os.environ.get('NOTES_TABLE', 'your-notes-table')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DDB_TABLE)
s3 = boto3.client('s3')

# Set up logging for Lambda/CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context=None):
    # Parse query params for note_id and version
    params = event.get('queryStringParameters', {})
    note_id = params.get('note_id')
    version = params.get('version')
    logger.info(f"Received retrieval request: note_id={note_id}, version={version}")
    if not note_id or not version:
        logger.error("Missing note_id or version in query params")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing note_id or version in query params'})
        }

    # 1. Get metadata from DynamoDB
    try:
        logger.info(f"Fetching metadata from DynamoDB: table={DDB_TABLE}, note_id={note_id}, version={version}")
        response = table.get_item(Key={'note_id': note_id, 'version': version})
        item = response.get('Item')
        if not item:
            logger.warning(f"Note not found in DynamoDB: note_id={note_id}, version={version}")
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Note not found'})
            }
        compressed_key = item.get('compressed_key')
        if not compressed_key:
            logger.warning(f"Compressed note not found for note_id={note_id}, version={version}")
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Compressed note not found'})
            }
        logger.info(f"Found compressed_key in DynamoDB: {compressed_key}")
    except ClientError as e:
        logger.error(f"Failed to fetch metadata from DynamoDB: {e.response['Error']['Message']}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to fetch metadata: {e.response["Error"]["Message"]}'})
        }

    # 2. Get compressed note from S3
    try:
        logger.info(f"Fetching compressed note from S3: bucket={S3_BUCKET}, key={compressed_key}")
        s3_obj = s3.get_object(Bucket=S3_BUCKET, Key=compressed_key)
        compressed_data = s3_obj['Body'].read()
        logger.info(f"Successfully fetched compressed note from S3: {compressed_key}")
    except ClientError as e:
        logger.error(f"Failed to fetch note from S3: {e.response['Error']['Message']}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to fetch note from S3: {e.response["Error"]["Message"]}'})
        }

    # 3. Decompress note and measure latency
    try:
        logger.info(f"Decompressing note for note_id={note_id}, version={version}")
        start_time = time.time()
        note_data = zstd.decompress(compressed_data).decode('utf-8')
        decompression_latency = time.time() - start_time
        logger.info(f"Successfully decompressed note for note_id={note_id}, version={version}. Latency: {decompression_latency:.6f} seconds")
    except Exception as e:
        logger.error(f"Failed to decompress note: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to decompress note: {e}'})
        }

    # 4. Update DynamoDB with decompression latency
    try:
        logger.info(f"Updating DynamoDB with decompression latency for note_id={note_id}, version={version}")
        table.update_item(
            Key={'note_id': note_id, 'version': version},
            UpdateExpression="SET decompression_latency = :lat",
            ExpressionAttributeValues={':lat': decompression_latency}
        )
        logger.info(f"Successfully updated decompression latency in DynamoDB for note_id={note_id}, version={version}")
    except ClientError as e:
        logger.error(f"Failed to update decompression latency in DynamoDB: {e.response['Error']['Message']}")
        # Do not fail the request if latency update fails

    # 5. Return note content
    logger.info(f"Returning note content for note_id={note_id}, version={version}")
    return {
        'statusCode': 200,
        'body': json.dumps({
            'note_id': note_id,
            'version': version,
            'title': item.get('title', ''),
            'content': note_data,
            'decompression_latency': decompression_latency
        })
    }
