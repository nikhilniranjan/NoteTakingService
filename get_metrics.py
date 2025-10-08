import os
import json
import boto3
from botocore.exceptions import ClientError
import logging

# Environment variables (set in Lambda console or SAM/CloudFormation)
DDB_TABLE = os.environ.get('NOTES_TABLE', 'your-notes-table')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DDB_TABLE)

# Set up logging for Lambda/CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.ERROR)

def lambda_handler(event, context=None):
    # Only allow GET requests
    method = event.get('httpMethod', 'GET')
    if method != 'GET':
        logger.error(f"Invalid method: {method}")
        return {
            'statusCode': 405,
            'body': json.dumps({'error': 'Method Not Allowed'})
        }

    notes_metrics = []
    try:
        logger.info(f"Scanning DynamoDB table {DDB_TABLE} for metrics")
        response = table.scan()
        items = response.get('Items', [])
        for item in items:
            note_id = item.get('note_id')
            version = item.get('version')
            uncompressed_size = item.get('uncompressed_size')
            compression_ratio = item.get('compression_ratio')
            decompression_latency = item.get('decompression_latency')
            read_latency = item.get('read_latency')
            notes_metrics.append({
                'note_id': note_id,
                'version': version,
                'uncompressed_size': float(uncompressed_size) if uncompressed_size is not None else None,
                'compression_ratio': float(compression_ratio) if compression_ratio is not None else None,
                'decompression_latency': float(decompression_latency) if decompression_latency is not None else None,
                'read_latency': float(read_latency) if read_latency is not None else None
            })
        logger.info(f"Found {len(notes_metrics)} notes with metrics")
    except ClientError as e:
        logger.error(f"Failed to scan DynamoDB: {e.response['Error']['Message']}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f"Failed to fetch metrics: {e.response['Error']['Message']}"})
        }

    return {
        'statusCode': 200,
        'body': json.dumps({
            'notes_metrics': notes_metrics
        })
    }
