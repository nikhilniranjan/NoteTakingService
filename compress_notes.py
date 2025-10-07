import os
#import os
#os.environ["ZSTD_USE_BACKEND"] = "cffi"
import json
import boto3
import pyzstd as zstd
#import zstandard as zstd
#from compression import zstd
from botocore.exceptions import ClientError
import logging

# Environment variables (set in Lambda console or SAM/CloudFormation)
S3_BUCKET = os.environ.get('NOTES_BUCKET', 'your-notes-bucket')
DDB_TABLE = os.environ.get('NOTES_TABLE', 'your-notes-table')

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

table = dynamodb.Table(DDB_TABLE)

# Set up logging for Lambda/CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context=None):
	# SQS event: event['Records'] is a list of SQS messages
	#TBD: remove for loop
	for record in event.get('Records', []):
		try:
			body = json.loads(record['body'])
			note_id = body['note_id']
			version = str(body.get('version', '1'))
			s3_key = body['s3_key']
			logger.info(f"Processing note_id={note_id}, version={version}, s3_key={s3_key}")
		except Exception as e:
			logger.error(f"Malformed SQS message: {e}")
			continue

		# 1. Fetch note from S3
		try:
			logger.info(f"Fetching note from S3: bucket={S3_BUCKET}, key={s3_key}")
			s3_obj = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
			note_data = s3_obj['Body'].read()
			logger.info(f"Successfully fetched note from S3: {s3_key}")
		except ClientError as e:
			logger.error(f"Failed to fetch note from S3: {e.response['Error']['Message']}")
			continue

		# 2. Compress note with zstd
		try:
			logger.info(f"Compressing note_id={note_id}, version={version}")
			compressed = zstd.compress(note_data)
			logger.info(f"Compression successful for note_id={note_id}, version={version}")
		except Exception as e:
			logger.error(f"Compression failed for note_id={note_id}, version={version}: {e}")
			continue

		# 3. Write compressed note back to S3 (new key)
		compressed_key = s3_key.replace('.txt', '.zst')
		try:
			logger.info(f"Writing compressed note to S3: bucket={S3_BUCKET}, key={compressed_key}")
			s3.put_object(Bucket=S3_BUCKET, Key=compressed_key, Body=compressed)
			logger.info(f"Successfully wrote compressed note to S3: {compressed_key}")
			# Delete the uncompressed note after successful compression
			logger.info(f"Deleting uncompressed note from S3: bucket={S3_BUCKET}, key={s3_key}")
			s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
			logger.info(f"Successfully deleted uncompressed note from S3: {s3_key}")
		except ClientError as e:
			logger.error(f"Failed to write compressed note to S3 or delete uncompressed note: {e.response['Error']['Message']}")
			continue

		# 4. Update DynamoDB metadata for the correct version
		try:
			logger.info(f"Updating DynamoDB metadata for note_id={note_id}, version={version}")
			table.update_item(
				Key={'note_id': note_id, 'version': version},
				UpdateExpression="SET compressed_key = :ck, compression_status = :s",
				ExpressionAttributeValues={
					':ck': compressed_key,
					':s': 'compressed'
				}
			)
			logger.info(f"Successfully updated DynamoDB for note_id={note_id}, version={version}")
		except ClientError as e:
			logger.error(f"Failed to update DynamoDB: {e.response['Error']['Message']}")
			continue

		logger.info(f"Note {note_id} (version {version}) compressed and updated successfully.")

