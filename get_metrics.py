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
logger.setLevel(logging.INFO)

def lambda_handler(event, context=None):
    # Only allow GET requests
    method = event.get('httpMethod', 'GET')
    if method != 'GET':
        logger.error(f"Invalid method: {method}")
        return {
            'statusCode': 405,
            'body': json.dumps({'error': 'Method Not Allowed'})
        }

    compression_ratios = []
    latencies = []
    try:
        logger.info(f"Scanning DynamoDB table {DDB_TABLE} for metrics")
        response = table.scan()
        items = response.get('Items', [])
        for item in items:
            cr = item.get('compression_ratio')
            lat = item.get('decompression_latency')
            if cr is not None:
                compression_ratios.append(cr)
            if lat is not None:
                latencies.append(lat)
        logger.info(f"Found {len(compression_ratios)} compression ratios and {len(latencies)} latencies")
    except ClientError as e:
        logger.error(f"Failed to scan DynamoDB: {e.response['Error']['Message']}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to fetch metrics: {e.response['Error']['Message']}'})
        }

    return {
        'statusCode': 200,
        'body': json.dumps({
            'compression_ratios': compression_ratios,
            'decompression_latencies': latencies
        })
    }
