import sqlite3
import os
import pickle
import time

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_PICKLE_FILE = 'token.pickle'


def get_gmail_service():
    # Load credentials from file if available, otherwise authenticate and save
    credentials = None
    if os.path.exists(TOKEN_PICKLE_FILE):
        with open(TOKEN_PICKLE_FILE, 'rb') as token:
            credentials = pickle.load(token)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            credentials = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(TOKEN_PICKLE_FILE, 'wb') as token:
            pickle.dump(credentials, token)

    # Build the Gmail service
    service = build('gmail', 'v1', credentials=credentials)
    return service


# Función para obtener el perfil del usuario y el número total de mensajes
def get_profile(service, user_id='me'):
    profile = service.users().getProfile(userId=user_id).execute()
    total_messages = profile['messagesTotal']
    return total_messages


# Function to get details of a message
def get_message(service, user_id='me', msg_id=''):
    message = service.users().messages().get(userId=user_id, id=msg_id).execute()
    return message


# Function to initialize the database
def initialize_database():
    connection = sqlite3.connect('gmail_data.db')
    cursor = connection.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            message_id TEXT PRIMARY KEY,
            date_received TEXT,
            from_email TEXT,
            domain_origin TEXT,
            size_of_email TEXT,
            has_attachments INTEGER,
            subject TEXT
        )
    ''')

    connection.commit()
    connection.close()


# Function to insert an email into the database
def insert_email(message_id, date_received, from_email, domain_origin, size_of_email, has_attachments, subject):
    connection = sqlite3.connect('gmail_data.db')
    cursor = connection.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO emails (message_id, date_received, from_email, domain_origin, size_of_email, has_attachments, subject)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (message_id, date_received, from_email, domain_origin, size_of_email, has_attachments, subject))

    connection.commit()
    connection.close()


def list_messages(service, user_id='me', start_message_id=None, max_results=None):
    messages = []
    page_token = None
    query = f'after:{int(get_message(service, msg_id=start_message_id)["internalDate"]) // 1000}' if start_message_id else None

    while True:
        response = service.users().messages().list(userId=user_id, q=query, maxResults=max_results,
                                                   pageToken=page_token).execute()
        addtl_msgs = response.get('messages', [])
        print(f'messages added to the queue: {addtl_msgs}')
        messages.extend(addtl_msgs)
        print(f'total messages in queue: {len(messages)}')

        # Check if there are more messages
        if 'nextPageToken' in response:
            page_token = response['nextPageToken']

            # Add a pause to avoid exceeding the rate limit
            time.sleep(0.5)  # You can adjust the duration based on your needs
        else:
            break

    return messages


# Function to get the last processed message ID from the database
def get_last_processed_message():
    connection = sqlite3.connect('gmail_data.db')
    cursor = connection.cursor()

    cursor.execute('SELECT MAX(message_id) FROM emails')
    last_processed_message_id = cursor.fetchone()[0]

    connection.close()

    return last_processed_message_id


def get_subject(message):
    subject_header = next((header['value'] for header in message['payload']['headers'] if header['name'] == 'Subject'), None)
    return subject_header[:20] if subject_header else None


def get_from_email(message):
    from_header = next((header['value'] for header in message['payload']['headers'] if header['name'] == 'From'), None)

    # Check if the email address is enclosed in angle brackets
    start_index = from_header.find('<')
    end_index = from_header.find('>')

    if start_index != -1 and end_index != -1:
        return from_header[start_index + 1:end_index]
    else:
        return from_header

# Main function
def main():
    service = get_gmail_service()

    # Initialize the database
    initialize_database()

    # Get the number of total messages
    total_messages = get_profile(service)
    print(f"Total messages in the account: {total_messages}")

    # Get the ID of the last processed message
    last_processed_message_id = get_last_processed_message()
    last_processed_message_id = "18bfe32a9e3a62b8"
    print(f"Last processed message ID: {last_processed_message_id}")

    # List and process messages starting from the last processed message
    messages = list_messages(service, start_message_id=last_processed_message_id)

    for msg in messages:
        message = get_message(service, msg_id=msg['id'])
        date_received = message['internalDate']
        from_email = get_from_email(message)
        domain_origin = from_email.split('@')[1] if '@' in from_email else ''
        size_of_email = message['sizeEstimate']
        has_attachments = 1 if 'parts' in message['payload'] else 0
        subject = get_subject(message)

        # Print information of the message
        print(f"Message ID: {msg['id']}")
        print(f"Date Received: {date_received}")
        print(f"From Email: {from_email}")
        print(f"Domain Origin: {domain_origin}")
        print(f"Size of Email: {size_of_email} bytes")
        print(f"Has Attachments: {'Yes' if has_attachments else 'No'}")
        print(f"Subject: {subject}")
        print("-" * 50)

        # Insert information into the database
        insert_email(msg['id'], date_received, from_email, domain_origin, size_of_email, has_attachments, subject)


if __name__ == '__main__':
    main()
