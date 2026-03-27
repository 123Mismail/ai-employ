import os.path
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Use absolute paths for credentials and token to avoid CWD issues
REPO_ROOT = Path(__file__).parent.parent.parent.parent
CREDENTIALS_PATH = REPO_ROOT / 'credentials.json'
TOKEN_PATH = REPO_ROOT / 'token.json'

def get_gmail_service():
    """Handles OAuth2 flow and returns Gmail service object."""
    creds = None
    
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(f"Missing '{CREDENTIALS_PATH}'. Please download it from Google Cloud Console.")
            
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

if __name__ == "__main__":
    try:
        service = get_gmail_service()
        print("Successfully authenticated with Gmail API!")
    except Exception as e:
        print(f"Auth failed: {e}")
