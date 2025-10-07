
import os
import json
import boto3
from botocore.exceptions import ClientError
import logging

# Environment variables (set in Lambda console or SAM/CloudFormation)
S3_BUCKET = os.environ.get('NOTES_BUCKET', 'your-notes-bucket')
DDB_TABLE = os.environ.get('NOTES_TABLE', 'your-notes-table')
SQS_QUEUE_URL = os.environ.get('NOTES_QUEUE_URL', 'https://sqs.region.amazonaws.com/123456789012/your-queue')


s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DDB_TABLE)
sqs = boto3.client('sqs')

# Set up logging for Lambda/CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)




def lambda_handler(event, context=None):
	# Support both POST (create) and PUT (update) requests
	method = event.get('httpMethod', 'POST')
	logger.info(f"Received {method} request: {event}")
	try:
		body = event['body'] if isinstance(event['body'], dict) else json.loads(event['body'])
		note_id = body['note_id']
		version = str(body.get('version', '1'))  # Default to version 1 if not provided
		content = body['content']
		title = body.get('title', '')
		#author = body.get('author', '')
		logger.info(f"Parsed input: note_id={note_id}, version={version}, title={title}")
	except Exception as e:
		logger.error(f"Invalid input: {e}")
		return {
			'statusCode': 400,
			'body': json.dumps({'error': f'Invalid input: {e}'})
		}

	# 1. Store note in S3 (versioned key)
	s3_key = f"notes/{note_id}_v{version}.txt"
	try:
		logger.info(f"Storing note in S3: bucket={S3_BUCKET}, key={s3_key}")
		s3.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=content.encode('utf-8'))
		logger.info(f"Successfully stored note in S3: {s3_key}")
	except ClientError as e:
		logger.error(f"Failed to store note in S3: {e.response['Error']['Message']}")
		return {
			'statusCode': 500,
			'body': json.dumps({'error': f'Failed to store note in S3: {e.response['Error']['Message']}'})
		}

	# 2. Store/update metadata in DynamoDB (versioned)
	try:
		logger.info(f"Storing metadata in DynamoDB: table={DDB_TABLE}, note_id={note_id}, version={version}")
		table.put_item(Item={
			'note_id': note_id,
			'version': version,
			's3_key': s3_key,
			'title': title,
			# 'author': author,
			'status': 'uploaded'
		})
		logger.info(f"Successfully stored metadata in DynamoDB for note_id={note_id}, version={version}")
	except ClientError as e:
		logger.error(f"Failed to store metadata in DynamoDB: {e.response['Error']['Message']}")
		return {
			'statusCode': 500,
			'body': json.dumps({'error': f'Failed to store metadata in DynamoDB: {e.response['Error']['Message']}'})
		}

	# 3. Put message in SQS queue (include version)
	try:
		logger.info(f"Enqueuing SQS message: queue_url={SQS_QUEUE_URL}, note_id={note_id}, version={version}")
		sqs.send_message(
			QueueUrl=SQS_QUEUE_URL,
			MessageBody=json.dumps({'note_id': note_id, 'version': version, 's3_key': s3_key})
		)
		logger.info(f"Successfully enqueued SQS message for note_id={note_id}, version={version}")
	except ClientError as e:
		logger.error(f"Failed to enqueue SQS message: {e.response['Error']['Message']}")
		return {
			'statusCode': 500,
			'body': json.dumps({'error': f'Failed to enqueue SQS message: {e.response['Error']['Message']}'})
		}

	# 4. Return success response
	logger.info(f"Note {note_id} v{version} {'updated' if method == 'PUT' else 'uploaded'} successfully")
	return {
		'statusCode': 200,
		'body': json.dumps({
			'message': f'Note {"updated" if method == "PUT" else "uploaded"} successfully',
			'note_id': note_id,
			'version': version,
			's3_key': s3_key
		})
	}

