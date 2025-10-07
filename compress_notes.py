import os
#import os
#os.environ["ZSTD_USE_BACKEND"] = "cffi"
import json
import boto3
import pyzstd as zstd
#import zstandard as zstd
#from compression import zstd
from botocore.exceptions import ClientError

# Environment variables (set in Lambda console or SAM/CloudFormation)
S3_BUCKET = os.environ.get('NOTES_BUCKET', 'your-notes-bucket')
DDB_TABLE = os.environ.get('NOTES_TABLE', 'your-notes-table')

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DDB_TABLE)


def lambda_handler(event, context=None):
	# SQS event: event['Records'] is a list of SQS messages
	for record in event.get('Records', []):
		try:
			body = json.loads(record['body'])
			note_id = body['note_id']
			version = str(body.get('version', '1'))
			s3_key = body['s3_key']
		except Exception as e:
			print(f"Malformed SQS message: {e}")
			continue

		# 1. Fetch note from S3
		try:
			s3_obj = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
			note_data = s3_obj['Body'].read()
		except ClientError as e:
			print(f"Failed to fetch note from S3: {e.response['Error']['Message']}")
			continue

		# 2. Compress note with zstd
		try:
			compressed = zstd.compress(note_data)
		except Exception as e:
			print(f"Compression failed: {e}")
			continue


		# 3. Write compressed note back to S3 (new key)
		compressed_key = s3_key.replace('.txt', '.zst')
		try:
			s3.put_object(Bucket=S3_BUCKET, Key=compressed_key, Body=compressed)
			# Delete the uncompressed note after successful compression
			s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
		except ClientError as e:
			print(f"Failed to write compressed note to S3 or delete uncompressed note: {e.response['Error']['Message']}")
			continue

		# 4. Update DynamoDB metadata for the correct version
		try:
			table.update_item(
				Key={'note_id': note_id, 'version': version},
				UpdateExpression="SET compressed_key = :ck, compression_status = :s",
				ExpressionAttributeValues={
					':ck': compressed_key,
					':s': 'compressed'
				}
			)
		except ClientError as e:
			print(f"Failed to update DynamoDB: {e.response['Error']['Message']}")
			continue

		print(f"Note {note_id} (version {version}) compressed and updated successfully.")

