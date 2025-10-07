
import os
import json
import boto3
from botocore.exceptions import ClientError

# Environment variables (set in Lambda console or SAM/CloudFormation)
S3_BUCKET = os.environ.get('NOTES_BUCKET', 'your-notes-bucket')
DDB_TABLE = os.environ.get('NOTES_TABLE', 'your-notes-table')
SQS_QUEUE_URL = os.environ.get('NOTES_QUEUE_URL', 'https://sqs.region.amazonaws.com/123456789012/your-queue')

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DDB_TABLE)
sqs = boto3.client('sqs')

def lambda_handler(event, context=None):
	# Parse input (API Gateway proxy integration: event['body'] is JSON string)
	try:
		body = event['body'] if isinstance(event['body'], dict) else json.loads(event['body'])
		note_id = body['note_id']
		content = body['content']
		title = body.get('title', '')
		#author = body.get('author', '')
	except Exception as e:
		return {
			'statusCode': 400,
			'body': json.dumps({'error': f'Invalid input: {e}'})
		}

	# 1. Store note in S3
	s3_key = f"notes/{note_id}.txt"
	try:
		s3.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=content.encode('utf-8'))
	except ClientError as e:
		return {
			'statusCode': 500,
			'body': json.dumps({'error': f'Failed to store note in S3: {e.response["Error"]["Message"]}'})
		}

	# 2. Store metadata in DynamoDB
	try:
		table.put_item(Item={
			'note_id': note_id,
			's3_key': s3_key,
			'title': title,
			#'author': author,
			'status': 'uploaded'
		})
	except ClientError as e:
		return {
			'statusCode': 500,
			'body': json.dumps({'error': f'Failed to store metadata in DynamoDB: {e.response["Error"]["Message"]}'})
		}

	# 3. Put message in SQS queue
	try:
		sqs.send_message(
			QueueUrl=SQS_QUEUE_URL,
			MessageBody=json.dumps({'note_id': note_id, 's3_key': s3_key})
		)
	except ClientError as e:
		return {
			'statusCode': 500,
			'body': json.dumps({'error': f'Failed to enqueue SQS message: {e.response["Error"]["Message"]}'})
		}

	# 4. Return success response
	return {
		'statusCode': 200,
		'body': json.dumps({
			'message': 'Note uploaded successfully',
			'note_id': note_id,
			's3_key': s3_key
		})
	}

