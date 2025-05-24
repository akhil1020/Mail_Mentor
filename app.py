

import streamlit as st
import base64
import io
import fitz  # PyMuPDF
from PIL import Image
import os
import json
import datetime
import time

#secrets
import os
from dotenv import load_dotenv

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import ssl
from httplib2 import Http
from google.auth.transport.requests import AuthorizedSession
from google.auth.transport.urllib3 import AuthorizedHttp
from functools import wraps
from ssl import SSLError
from socket import error as SocketError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
refresh_token = os.getenv("REFRESH_TOKEN")
access_token = os.getenv("ACCESS_TOKEN")
SCOPES = ['https://mail.google.com/']

def retry_on_ssl_error(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (SSLError, SocketError) as e:
                    retries += 1
                    if retries == max_retries:
                        st.error(f"⚠️ Network error: {str(e)}. Please try again later.")
                        return None
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

def save_emails_to_local_storage(emails):
    for email in emails:
        if 'stored_at' not in email:
            email['stored_at'] = datetime.datetime.now().isoformat()
    with open('email_cache.json', 'w') as f:
        json.dump(emails, f)

def load_emails_from_local_storage():
    try:
        with open('email_cache.json', 'r') as f:
            emails = json.load(f)
            return emails
    except FileNotFoundError:
        return []

@retry_on_ssl_error(max_retries=3, delay=1)
def get_new_emails(service, stored_emails):
    stored_ids = {email['id'] for email in stored_emails}
    messages = []
    next_page_token = None
    try:
        while True:
            response = service.users().messages().list(
                userId='me',
                maxResults=100,
                pageToken=next_page_token
            ).execute()
            batch = response.get('messages', [])
            new_messages = [msg for msg in batch if msg['id'] not in stored_ids]
            messages.extend(new_messages)
            if len(messages) >= 1000 or not response.get('nextPageToken'):
                break
            next_page_token = response.get('nextPageToken')
        return messages
    except Exception as e:
        st.error(f"⚠️ Error fetching emails: {str(e)}")
        return []

def get_gmail_service():
    creds = None
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token_file:
            token_file.write(creds.to_json())

    # http = AuthorizedHttp(creds, ssl_context=ssl_context)
    return build("gmail", "v1", credentials=creds)

@retry_on_ssl_error(max_retries=3, delay=1)
def download_attachment(service, message_id, attachment_id):
    try:
        attachment = service.users().messages().attachments().get(
            userId='me', messageId=message_id, id=attachment_id
        ).execute()
        data = attachment.get('data')
        if data:
            return base64.urlsafe_b64decode(data.encode())
        return None
    except Exception as e:
        st.error(f"⚠️ Error downloading attachment: {str(e)}")
        return None

def parse_email(service, msg_id):
    msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
    payload = msg['payload']
    headers = payload.get('headers', [])
    parts = payload.get('parts', [])

    def get_header(name):
        return next((h['value'] for h in headers if h['name'].lower() == name.lower()), '')

    subject = get_header('Subject')
    sender = get_header('From')
    date = get_header('Date')
    to = get_header('To')

    body = ''
    attachments = []

    def extract_parts(parts):
        nonlocal body, attachments
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                data = part['body'].get('data')
                if data:
                    body += base64.urlsafe_b64decode(data.encode()).decode(errors='ignore')
            elif part.get('filename'):
                attachment_id = part['body'].get('attachmentId')
                if attachment_id:
                    attachments.append({
                        'filename': part['filename'],
                        'attachment_id': attachment_id,
                        'mimeType': part['mimeType']
                    })
            if part.get('parts'):
                extract_parts(part['parts'])

    extract_parts(parts)

    return {
        'id': msg_id,
        'subject': subject,
        'sender': sender,
        'to': to,
        'date': date,
        'snippet': msg.get('snippet'),
        'body': body.strip(),
        'attachments': attachments,
        'labels': msg.get('labelIds', [])  # Gmail API returns labelIds
    }

def get_last_1000_emails(service, max_count=10):
    messages = []
    next_page_token = None

    while len(messages) < max_count:
        response = service.users().messages().list(
            userId='me',
            maxResults=10,
            pageToken=next_page_token
        ).execute()

        messages.extend(response.get('messages', []))
        next_page_token = response.get('nextPageToken')

        if not next_page_token:
            break

    messages = messages[:max_count]
    email_details = []

    progress = st.progress(0)
    for i, msg in enumerate(messages):
        try:
            email_data = parse_email(service, msg['id'])
            email_details.append(email_data)
        except Exception as e:
            print(f"Error fetching message {msg['id']}: {e}")
            continue
        progress.progress((i + 1) / len(messages))

    return email_details

def preview_pdf(file_data, filename):
    try:
        pdf = fitz.open(stream=file_data, filetype="pdf")
        if pdf.is_encrypted:
            st.error(f"⚠️ The PDF {filename} is encrypted and cannot be previewed.")
            return
        st.markdown(f"📄 **Preview of {filename}**")
        for page_num in range(min(3, len(pdf))):
            page = pdf.load_page(page_num)
            pix = page.get_pixmap()
            image_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(image_bytes))
            st.image(image, caption=f"{filename} - Page {page_num + 1}", use_container_width=True)
    except Exception as e:
        st.error(f"⚠️ Error loading PDF {filename}: {e}")
        print(f"Error loading PDF {filename}: {e}")

@retry_on_ssl_error(max_retries=3, delay=1)
def send_email(service, to, subject, body, attachment=None):
    try:
        if attachment:
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            message['from'] = service.users().getProfile(userId='me').execute()['emailAddress']
            message.attach(MIMEText(body, 'plain'))
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{attachment.name}"')
            message.attach(part)
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        else:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            message['from'] = service.users().getProfile(userId='me').execute()['emailAddress']
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        message = {'raw': raw}
        service.users().messages().send(userId='me', body=message).execute()
        return True
    except Exception as e:
        st.error(f"⚠️ Error sending email: {str(e)}")
        return False

@retry_on_ssl_error(max_retries=3, delay=1)
def save_draft(service, to, subject, body):
    try:
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        message['from'] = service.users().getProfile(userId='me').execute()['emailAddress']
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        draft = {'message': {'raw': raw}}
        service.users().drafts().create(userId='me', body=draft).execute()
        return True
    except Exception as e:
        st.error(f"⚠️ Error saving draft: {str(e)}")
        return False

# --- Gmail API: Modify, Delete, and Label Management ---

@retry_on_ssl_error(max_retries=3, delay=1)
def modify_labels(service, msg_id, add_labels=None, remove_labels=None):
    try:
        body = {}
        if add_labels:
            body['addLabelIds'] = add_labels
        if remove_labels:
            body['removeLabelIds'] = remove_labels
        service.users().messages().modify(userId='me', id=msg_id, body=body).execute()
        return True
    except Exception as e:
        st.error(f"⚠️ Error modifying labels: {str(e)}")
        return False

@retry_on_ssl_error(max_retries=3, delay=1)
def delete_email(service, msg_id):
    try:
        service.users().messages().delete(userId='me', id=msg_id).execute()
        return True
    except Exception as e:
        st.error(f"⚠️ Error deleting email: {str(e)}")
        return False

@retry_on_ssl_error(max_retries=3, delay=1)
def move_to_trash(service, msg_id):
    try:
        service.users().messages().trash(userId='me', id=msg_id).execute()
        return True
    except Exception as e:
        st.error(f"⚠️ Error moving email to trash: {str(e)}")
        return False

# Do not auto-fetch emails in __main__ for Streamlit apps
if __name__ == "__main__":
    print("This module provides Gmail functionality. Run ui.py to start the application.")
