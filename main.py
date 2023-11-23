from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def get_gmail_service():
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    credentials = flow.run_local_server(port=0)
    return build('gmail', 'v1', credentials=credentials)


def list_messages(service, user_id='me', max_results=10):
    response = service.users().messages().list(userId=user_id, maxResults=max_results).execute()
    messages = response.get('messages', [])
    return messages


def get_message(service, user_id='me', msg_id=''):
    message = service.users().messages().get(userId=user_id, id=msg_id).execute()
    return message


def main():
    service = get_gmail_service()
    messages = list_messages(service)

    for msg in messages:
        message = get_message(service, msg_id=msg['id'])
        subject = [header['value'] for header in message['payload']['headers'] if header['name'] == 'Subject'][0]
        print(f"Subject: {subject}")


if __name__ == '__main__':
    main()
