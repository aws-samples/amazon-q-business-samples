from googleapiclient.discovery import build
from google.oauth2 import service_account
import json
import boto3
import io
import os
from googleapiclient.http import MediaIoBaseUpload

def get_service_account_creds():
    secret_name = os.environ.get('SECRET_NAME')
    region_name = os.environ.get('REGION_NAME') 
    
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        creds_dict = json.loads(get_secret_value_response['SecretString'])
        print("Successfully retrieved secret from Secrets Manager")
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        return credentials
    except Exception as e:
        print(f"Error getting credentials: {str(e)}")
        raise e

def get_user_email_from_cognito(username, user_pool_id):
    """Get user email from Cognito using the username"""
    try:
        cognito = boto3.client('cognito-idp')
        response = cognito.admin_get_user(
            UserPoolId=user_pool_id,
            Username=username
        )
        
        for attr in response['UserAttributes']:
            if attr['Name'] == 'email':
                return attr['Value']
        
        return None
    except Exception as e:
        print(f"Error getting user from Cognito: {str(e)}")
        raise e

def check_shared_drive_permission(drive_service, folder_id, user_email):
    """Check if user has permission to access a shared drive folder"""
    try:
        # Get folder info with shared drive support
        folder = drive_service.files().get(
            fileId=folder_id,
            supportsAllDrives=True,
            fields='id,name,driveId,parents'
        ).execute()
        
        drive_id = folder.get('driveId')
        if not drive_id:
            print("This is not a shared drive folder")
            return False
        
        print(f"Checking shared drive: {drive_id}")
        
        # Check shared drive permissions
        permissions = drive_service.permissions().list(
            fileId=drive_id,
            supportsAllDrives=True,
            fields='permissions(emailAddress,role,type,domain)'
        ).execute()
        
        for permission in permissions.get('permissions', []):
            # Check domain permission
            if permission.get('type') == 'domain':
                user_domain = user_email.split('@')[1] if '@' in user_email else ''
                perm_domain = permission.get('domain')
                if user_domain and perm_domain and user_domain == perm_domain:
                    role = permission.get('role', '').lower()
                    if role in ['organizer', 'fileorganizer', 'writer', 'contributor']:
                        print(f"User has domain {role} access to shared drive")
                        return True
            
            # Check direct user permission
            if permission.get('emailAddress') == user_email:
                role = permission.get('role', '').lower()
                if role in ['organizer', 'fileorganizer', 'writer', 'contributor']:
                    print(f"User has direct {role} access to shared drive")
                    return True
        
        print(f"User {user_email} does not have write access to shared drive")
        return False
        
    except Exception as e:
        print(f"Error checking shared drive access: {str(e)}")
        raise e

def lambda_handler(event, context):
    try:
        print(f"Event: {json.dumps(event)}")
        
        username = None
        user_pool_id = os.environ.get('COGNITO_USER_POOL_ID')
        
        if 'requestContext' in event and 'authorizer' in event['requestContext'] and 'jwt' in event['requestContext']['authorizer']:
            jwt_claims = event['requestContext']['authorizer']['jwt']['claims']
            username = jwt_claims.get('username') or jwt_claims.get('cognito:username')
        elif 'requestContext' in event and 'authorizer' in event['requestContext'] and 'claims' in event['requestContext']['authorizer']:
            claims = event['requestContext']['authorizer']['claims']
            username = claims.get('username') or claims.get('cognito:username')
        
        if not username:
            return {
                'statusCode': 401,
                'body': json.dumps({'message': 'Authentication required. No username found in request.'})
            }
        try:
            user_email = get_user_email_from_cognito(username, user_pool_id)
        except Exception as e:
            print(f"Failed to retrieve user email: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({'message': 'Failed to retrieve user information.'})
            }
        if not user_email:
            return {
                'statusCode': 401,
                'body': json.dumps({'message': 'Could not retrieve user email from Cognito.'})
            }
            
        print(f"Retrieved user email: {user_email}")
        
        body = json.loads(event['body'])
        file_name = body['fileName']
        folder_id = body['folderId']  # This should be a shared drive folder ID
        mime_type = body.get('mimeType', 'text/plain')
        file_content = body['fileContent'].encode('utf-8')
        
        credentials = get_service_account_creds()
        drive_service = build('drive', 'v3', credentials=credentials)
        
        # Check shared drive access
        try:
            has_access = check_shared_drive_permission(drive_service, folder_id, user_email)
        except Exception as e:
            print(f"Failed to check shared drive permissions: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({'message': 'Failed to verify shared drive permissions.'})
            }
        if not has_access:
            return {
                'statusCode': 403,
                'body': json.dumps({'message': 'Access denied. You do not have permission to upload to this shared drive folder.'})
            }
        
        # Upload file to shared drive
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        media = MediaIoBaseUpload(
            io.BytesIO(file_content),
            mimetype=mime_type,
            resumable=True
        )
        
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            supportsAllDrives=True,
            fields='id,webViewLink'
        ).execute()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'fileId': file.get('id'),
                'webViewLink': file.get('webViewLink')
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }