import streamlit as st
import socket
from app import (
    load_emails_from_local_storage,
    get_new_emails,
    parse_email,
    get_gmail_service,
    save_emails_to_local_storage,
    send_email,
    save_draft,
    download_attachment,
    modify_labels,
    delete_email,
    move_to_trash,
)
import os
import datetime

def check_internet_connection():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

def refresh_emails(label=None):
    stored_emails = load_emails_from_local_storage() or []
    # If label is "SENT", fetch sent emails from Gmail
    if label == "SENT":
        # Only fetch new sent emails
        from app import get_gmail_service
        service = st.session_state.service
        sent_msgs = service.users().messages().list(userId='me', labelIds=['SENT'], maxResults=50).execute().get('messages', [])
        sent_ids = {email['id'] for email in stored_emails if 'SENT' in email.get('labels', [])}
        new_sent = [msg for msg in sent_msgs if msg['id'] not in sent_ids]
        parsed_emails = []
        for msg in new_sent:
            email = parse_email(service, msg['id'])
            if 'SENT' not in email.get('labels', []):
                email['labels'].append('SENT')
            parsed_emails.append(email)
        stored_emails.extend(parsed_emails)
        save_emails_to_local_storage(stored_emails)
        return stored_emails
    else:
        # Default: fetch inbox and others as before
        new_messages = get_new_emails(st.session_state.service, stored_emails)
        if new_messages:
            parsed_emails = []
            for msg in new_messages:
                email = parse_email(st.session_state.service, msg['id'])
                parsed_emails.append(email)
            stored_emails.extend(parsed_emails)
            save_emails_to_local_storage(stored_emails)
        return stored_emails

def render_sidebar():
    with st.sidebar:
        st.title("Mail Mentor")
        if st.button("🖊 Compose"):
            st.session_state.current_view = "compose"
        st.markdown("---")
        if st.button("📥 Inbox"):
            st.session_state.current_view = "inbox"
            st.session_state.filter_label = "INBOX"
        if st.button("⭐ Important"):
            st.session_state.current_view = "important"
            st.session_state.filter_label = "IMPORTANT"
        if st.button("🗃️ Archive"):
            st.session_state.current_view = "archive"
            st.session_state.filter_label = "ARCHIVE"
        if st.button("📤 Sent"):
            st.session_state.current_view = "sent"
            st.session_state.filter_label = "SENT"
        if st.button("📝 Drafts"):
            st.session_state.current_view = "drafts"
            st.session_state.filter_label = "DRAFT"
        if st.button("🔄 Refresh"):
            st.session_state.refresh = True

def render_email_list(emails):
    search_query = st.text_input("🔍 Smart Search...", key="text_search")
    if search_query:
        filtered_emails = [
            email for email in emails
            if search_query.lower() in email.get('subject', '').lower()
            or search_query.lower() in email.get('body', '').lower()
            or search_query.lower() in email.get('sender', '').lower()
            or any(search_query.lower() in label.lower() for label in email.get('labels', []))
        ]
        st.write(f"🔍 Found {len(filtered_emails)} matching emails")
    else:
        label = st.session_state.get("filter_label")
        if label:
            filtered_emails = [
                email for email in emails
                if label.lower() in [l.lower() for l in email.get('labels', [])]
            ]
        else:
            filtered_emails = emails

    if not filtered_emails:
        st.info("No emails to display.")
    else:
        for idx, email in enumerate(filtered_emails):
            with st.expander(f"{email.get('subject', '(No Subject)')} - {email.get('sender', 'Unknown')}"):
                st.markdown(f"**From:** {email.get('sender', 'Unknown')}")
                st.markdown(f"**To:** {email.get('to', '')}")
                st.markdown(f"**Date:** {email.get('date', '')}")
                st.markdown(f"**Labels:** {', '.join(email.get('labels', []))}")
                st.write(email.get('body', ''))
                # Attachments
                for att in email.get('attachments', []):
                    if st.button(f"Download {att['filename']}", key=f"att_{idx}_{att['filename']}"):
                        data = download_attachment(st.session_state.service, email['id'], att['attachment_id'])
                        st.download_button("Download", data, file_name=att['filename'])
                # Actions
                cols = st.columns(5)
                if cols[0].button("Delete", key=f"del_{idx}"):
                    # Delete from Gmail and local cache
                    delete_email(st.session_state.service, email['id'])
                    emails.remove(email)
                    save_emails_to_local_storage(emails)
                    st.rerun()
                if cols[1].button("Move to Trash", key=f"trash_{idx}"):
                    move_to_trash(st.session_state.service, email['id'])
                    email['labels'].append('TRASH')
                    save_emails_to_local_storage(emails)
                    st.rerun()
                if cols[2].button("Mark Important", key=f"imp_{idx}"):
                    if 'IMPORTANT' not in email['labels']:
                        modify_labels(st.session_state.service, email['id'], add_labels=['IMPORTANT'])
                        email['labels'].append('IMPORTANT')
                        save_emails_to_local_storage(emails)
                        st.rerun()
                if cols[3].button("Archive", key=f"arc_{idx}"):
                    if 'ARCHIVE' not in email['labels']:
                        modify_labels(st.session_state.service, email['id'], add_labels=['ARCHIVE'])
                        email['labels'].append('ARCHIVE')
                        save_emails_to_local_storage(emails)
                        st.rerun()
                if cols[4].button("Reply", key=f"rep_{idx}"):
                    st.session_state.current_view = "compose"
                    st.session_state.reply_to = email

def render_compose():
    st.header("Compose Email")
    to = st.text_input("To", value=st.session_state.get("reply_to", {}).get("sender", ""))
    subject = st.text_input("Subject", value="Re: " + st.session_state.get("reply_to", {}).get("subject", "") if st.session_state.get("reply_to") else "")
    body = st.text_area("Body", value="")
    attachment = st.file_uploader("Attachment", type=None)
    if st.button("Send"):
        # Pass attachment file object if present
        send_email(st.session_state.service, to, subject, body, attachment=attachment if attachment else None)
        st.success("Email sent!")
        # Add the sent email to local cache immediately
        sent_email = {
            'id': f"local-{datetime.datetime.now().timestamp()}",
            'subject': subject,
            'sender': st.session_state.service.users().getProfile(userId='me').execute()['emailAddress'],
            'to': to,
            'date': str(datetime.datetime.now()),
            'snippet': body[:100],
            'body': body,
            'attachments': [],
            'labels': ['SENT']
        }
        emails = load_emails_from_local_storage() or []
        emails.append(sent_email)
        save_emails_to_local_storage(emails)
        st.session_state.current_view = "sent"
        st.session_state.filter_label = "SENT"
        st.rerun()
    if st.button("Save as Draft"):
        save_draft(st.session_state.service, to, subject, body)
        st.success("Draft saved!")
        st.session_state.current_view = "drafts"

def render_ui():
    st.set_page_config(page_title="Mail Mentor", layout="wide")
    if 'current_view' not in st.session_state:
        st.session_state.current_view = "inbox"
    if 'filter_label' not in st.session_state:
        st.session_state.filter_label = "INBOX"
    if 'refresh' not in st.session_state:
        st.session_state.refresh = False

    render_sidebar()

    # Gmail service
    if 'service' not in st.session_state:
        with st.spinner("Connecting to Gmail..."):
            st.session_state.service = get_gmail_service()

    # Load or refresh emails
    label = st.session_state.get('filter_label')
    if st.session_state.refresh or not os.path.exists('email_cache.json'):
        with st.spinner("Fetching emails from Gmail..."):
            emails = refresh_emails(label=label)
            st.session_state.refresh = False
    else:
        emails = load_emails_from_local_storage() or []

    # Main view
    if st.session_state.current_view == "compose":
        render_compose()
    else:
        # Always refresh sent emails when viewing "Sent"
        if st.session_state.current_view == "sent":
            emails = refresh_emails(label="SENT")
        render_email_list(emails)

if __name__ == "__main__":
    render_ui()
