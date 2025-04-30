# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


import boto3
import logging
import json
from PyPDF2 import PdfReader
import io


logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
bedrock_runtime = boto3.client('bedrock-runtime')


def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))
    # Get the value of "S3Bucket" key name
    s3_bucket = event.get("s3Bucket")
    # Get the value of "S3ObjectKey" key name
    s3_object_key = event.get("s3ObjectKey")

    pdf_text = read_pdf_from_s3(s3_bucket, s3_object_key)
    bedrock_response = invoke_bedrock_model(pdf_text)

    # Get the value of "metadata" key name
    metadata = event.get("metadata")
    # Get the document "attributes" from the metadata
    document_attributes = metadata.get("attributes")

    new_key = s3_object_key.split("/")[-1].split(".")[0] + "_cde.txt"

    s3_client.put_object(Bucket=s3_bucket,
                         Key=new_key,
                         Body=bedrock_response.encode('utf-8'))

    return {
        "version": "v0",
        "s3ObjectKey": new_key,
        "metadataUpdates": document_attributes
    }


def read_pdf_from_s3(bucket_name, file_key):
    try:
        # Get the PDF file from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        pdf_file = io.BytesIO(response['Body'].read())

        # Read PDF content
        pdf_reader = PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error reading PDF from S3: {str(e)}")
        return None


def invoke_bedrock_model(text_content, model_id="amazon.nova-micro-v1:0"):
    try:
        # Prepare the request body
        request_body = {
                "inferenceConfig": {
                    "max_new_tokens": 1000
                },
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": (
                                    f"Remove the SSN,"
                                    f"Date of Birth from this text: {text_content}"
                                ) 
                            }
                        ]
                    }
                ]
            }

        # Invoke the model
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        # Parse and return the response
        response_body = json.loads(response['body'].read())
        logger.info("Response from Bedrock model: %s", response_body)
        return response_body['output']['message']['content'][0]['text']
    except Exception as e:
        print(f"Error invoking Bedrock model: {str(e)}")
        return None
