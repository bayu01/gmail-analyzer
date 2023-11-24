import sqlite3
import os
import pickle
import time

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_PICKLE_FILE = 'token.pickle'

# Reuse a connection
connection = sqlite3.connect('gmail_data.db')


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
    cursor = connection.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            message_id TEXT PRIMARY KEY,
            date_received BIGINT,
            from_email TEXT,
            domain_origin TEXT,
            size_of_email INTEGER,
            has_attachments INTEGER,
            subject TEXT
        )
    ''')

    commit_changes()


# Function to insert an email into the database
def insert_email(message_id, date_received, from_email, domain_origin, size_of_email, has_attachments, subject):
    cursor = connection.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO emails (message_id, date_received, from_email, domain_origin, size_of_email, has_attachments, subject)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (message_id, date_received, from_email, domain_origin, size_of_email, has_attachments, subject))


def list_messages(service, user_id='me', start_message_epoch=None, max_results=None):
    messages = []
    page_token = None
    query = f'after:{start_message_epoch // 1000}' if start_message_epoch else None

    total_messages = get_profile(service)  # Get the total number of messages
    messages_processed = 0
    start_time = time.time()

    while True:
        response = service.users().messages().list(userId=user_id, q=query, maxResults=max_results,
                                                   pageToken=page_token).execute()
        messages.extend(response.get('messages', []))

        # Increment messages_processed based on the number of messages in the current response
        messages_processed += len(response.get('messages', []))

        # Check if there are more messages
        if 'nextPageToken' in response:
            page_token = response['nextPageToken']

            # Calculate estimated time to complete based on progress
            elapsed_time = time.time() - start_time
            estimated_time_to_complete = (total_messages - messages_processed) * (
                    elapsed_time / messages_processed) if messages_processed > 0 else 0

            # Print remaining estimated time
            print(f"STAGE 1 of 2: Remaining Estimated Time: {estimated_time_to_complete:.2f} seconds")

            # Add a pause to avoid exceeding the rate limit
            time.sleep(0.5)  # You can adjust the duration based on your needs
        else:
            break

    end_time = time.time()
    elapsed_time = end_time - start_time

    # Calculate average time taken per message
    average_time_per_message = elapsed_time / messages_processed if messages_processed > 0 else 0

    # Print final statistics
    print(f"STAGE 1 Total Messages Queued: {messages_processed}")
    print(f"Average Time Per Message: {average_time_per_message:.2f} seconds")

    messages.reverse()
    return messages


# Function to get the last processed message epoch from the database
def get_last_processed_message():
    cursor = connection.cursor()

    cursor.execute('SELECT MAX(date_received) FROM emails')
    last_processed_message_epoch = cursor.fetchone()[0]

    return last_processed_message_epoch


def get_subject(message):
    subject_header = next((header['value'] for header in message['payload']['headers'] if header['name'] == 'Subject'),
                          None)
    return subject_header[:30] if subject_header else None


def get_from_email(message):
    from_header = next((header['value'] for header in message['payload']['headers'] if header['name'] == 'From'), None)

    # Check if the email address is enclosed in angle brackets
    start_index = from_header.find('<')
    end_index = from_header.find('>')

    if start_index != -1 and end_index != -1:
        return from_header[start_index + 1:end_index]
    else:
        return from_header


def commit_changes():
    connection.commit()
    # Optionally: Close and reopen the connection if needed
    # connection.close()
    # connection = sqlite3.connect('gmail_data.db')


# Main function
def main():
    service = get_gmail_service()

    # Initialize the database
    initialize_database()

    # Get the ID of the last processed message
    last_processed_message_epoch = get_last_processed_message()
    print(f"Last processed message ID: {last_processed_message_epoch}")

    # List and process messages starting from the last processed message
    messages = list_messages(service, start_message_epoch=last_processed_message_epoch)
    messages_to_insert = len(messages)
    print(f"Total Newer messages: {messages_to_insert}")
    batches_processed = 0
    start_time = time.time()

    batch_size = 500

    for i, msg in enumerate(messages, 1):
        message = get_message(service, msg_id=msg['id'])
        date_received = int(message['internalDate'])
        from_email = get_from_email(message)
        domain_origin = from_email.split('@')[1] if '@' in from_email else ''
        size_of_email = int(message['sizeEstimate'])
        has_attachments = 1 if 'parts' in message['payload'] else 0
        subject = get_subject(message)

        # Print information of the message
        print(f"Date Received: {date_received}")

        # Insert information into the database
        insert_email(msg['id'], date_received, from_email, domain_origin, size_of_email, has_attachments, subject)

        # Commit changes in batches
        if i % batch_size == 0:
            commit_changes()

            # Calculate estimated time to complete based on progress
            batches_processed = + 1
            elapsed_time = time.time() - start_time
            estimated_time_to_complete = (messages_to_insert - (batches_processed * batch_size)) * (
                    elapsed_time / (batches_processed * batch_size)) if batches_processed > 0 else 0

            # Print remaining estimated time
            print(f"STAGE 2 of 2: Remaining Estimated Time: {estimated_time_to_complete:.2f} seconds")

    # Commit any remaining changes
    commit_changes()
    batches_processed = + 1

    end_time = time.time()
    elapsed_time = end_time - start_time

    # Calculate average time taken per message
    average_time_per_message = elapsed_time / batches_processed if batches_processed > 0 else 0

    # Print final statistics
    print(f"STAGE 2 Total Batches Inserted: {batches_processed}")
    print(f"Average Time Per Batch Insert: {average_time_per_message:.2f} seconds")


if __name__ == '__main__':
    try:
        main()

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Close the connection in the finally block to ensure it's always closed
        connection.close()
