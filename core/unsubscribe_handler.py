from imapclient import IMAPClient # Import imapclient
from imapclient.exceptions import LoginError, IMAPClientError # Import specific exceptions
from core.localization import get_text, get_formatted, get_current_language
from core.encryption import decrypt_password
import time
import email
from email.header import decode_header
from email.utils import parseaddr
import re
import threading
from PyQt6.QtCore import QObject, pyqtSignal
from core.config_manager import load_config, get_tasks, save_task
import ssl # Import ssl for context
import logging
from core.version import get_version_string # Import version function

# Logger setup using LogManager if available, otherwise basic config
try:
    from .log_manager import LogManager
    log_manager = LogManager()
    logger = log_manager.get_logger("unsubscribe_handler")
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("unsubscribe_handler")

class UnsubscribeHandler(QObject):
    """Handles checking IMAP inbox for unsubscribe requests and processing them."""

    # Signal emitted when a recipient is successfully unsubscribed
    # Arguments: task_id (str), unsubscribed_email (str)
    unsubscribe_processed = pyqtSignal(str, str)
    # Signal emitted when IMAP check fails after retries
    # Arguments: error_message (str)
    imap_check_failed = pyqtSignal(str)

    def __init__(self, config=None):
        super().__init__()
        self.config = config or load_config()
        self.imap_settings = self.config.get("global_settings", {}).get("email_settings", {}).get("imap_settings", {})
        self.sender_email = self.config.get("global_settings", {}).get("email_settings", {}).get("sender_email", "")

    def _connect_imap(self):
        """Connects to the IMAP server using imapclient with retry logic."""
        server = self.imap_settings.get("server")
        port = self.imap_settings.get("port", 993)
        security = self.imap_settings.get("security", "SSL/TLS")
        username = self.imap_settings.get("username") or self.sender_email # Use sender if username not set
        encrypted_password = self.imap_settings.get("password")
        use_smtp_creds = self.imap_settings.get("use_smtp_credentials_for_imap", False)

        if use_smtp_creds:
            username = self.config.get("global_settings", {}).get("email_settings", {}).get("sender_email", "")
            encrypted_password = self.config.get("global_settings", {}).get("email_settings", {}).get("email_password", "")
            logger.info("Using SMTP credentials for IMAP login.")

        if not all([server, username, encrypted_password]):
            logger.error(get_text("imap_settings_incomplete"))
            raise ConnectionError(get_text("imap_settings_incomplete"))

        password = decrypt_password(encrypted_password)
        if not password:
             logger.error(get_text("imap_password_decryption_failed"))
             raise ConnectionError(get_text("imap_password_decryption_failed"))

        logger.info(get_formatted("connecting_to_imap", server, port))
        max_retries = 3
        retry_delay = 5 # seconds

        # Create SSL context if using SSL/TLS
        ssl_context = None
        use_ssl = (security == "SSL/TLS")
        if use_ssl:
            ssl_context = ssl.create_default_context()

        for attempt in range(max_retries):
            client = None
            try:
                # Establish connection using IMAPClient
                client = IMAPClient(server, port=port, ssl=use_ssl, ssl_context=ssl_context, timeout=15)
                logger.info(f"IMAPClient connected to {server}:{port} (SSL: {use_ssl})")

                # Handle STARTTLS if needed (imapclient does this automatically if ssl=False and server supports it)
                # No explicit starttls() call needed like in imaplib

                # Login
                client.login(username, password)
                logger.info(get_text("imap_connection_successful"))

                # --- Send IMAP ID command (Corrected Method) ---
                try:
                    client_id_info = {
                        b'name': b'NeuroFeed', # Use bytes for keys and values
                        b'version': get_version_string().encode('utf-8'),
                        b'vendor': b'NeuroFeedApp',
                        # b'support-email': b'your-support-email@example.com' # Optional
                    }
                    logger.info(f"Sending IMAP ID command with info: {client_id_info}")
                    # Corrected method call: id_() instead of id()
                    id_response = client.id_(client_id_info)
                    logger.info(f"IMAP ID command response: {id_response}")
                except AttributeError:
                     logger.error("The 'id_' method is not available in this version of imapclient. Cannot send ID.")
                except Exception as id_err:
                    # Log warning but don't fail connection if ID command fails
                    logger.warning(f"Failed to send IMAP ID command: {id_err}")
                # --- End IMAP ID command ---

                # --- Log Capabilities (imapclient style) ---
                try:
                    capabilities = client.capabilities()
                    logger.info(f"Server capabilities: {capabilities}")
                except Exception as cap_err:
                    logger.warning(f"Could not retrieve server capabilities: {cap_err}")
                # --- End Log Capabilities ---

                # --- Try NOOP (imapclient style) ---
                try:
                    logger.info("Sending NOOP command...")
                    noop_resp = client.noop()
                    logger.info(f"NOOP Response: {noop_resp}")
                except Exception as noop_err:
                    logger.warning(f"Error sending NOOP command: {noop_err}")
                # --- End NOOP ---

                return client # Return the connected client object

            except LoginError as e:
                error_str = str(e)
                is_unsafe_login = "unsafe login" in error_str.lower() or "授权码" in error_str.lower()
                if is_unsafe_login:
                    unsafe_login_msg = get_text("imap_unsafe_login_error")
                    logger.error(f"{unsafe_login_msg} Server response: {error_str}")
                    if client: client.logout() # Logout if connected
                    raise ConnectionAbortedError(unsafe_login_msg) from e

                logger.warning(get_formatted("imap_connection_attempt_failed", attempt + 1, max_retries, e))
                if client: client.logout()
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error(get_text("imap_connection_failed_retries"))
                    raise ConnectionError(get_text("imap_connection_failed_retries")) from e
            except ConnectionAbortedError as cae:
                 if client: client.logout()
                 raise cae
            except (IMAPClientError, OSError, ssl.SSLError) as e: # Catch broader connection errors
                 logger.warning(get_formatted("imap_connection_attempt_failed", attempt + 1, max_retries, e))
                 if client:
                     try: client.logout()
                     except: pass # Ignore logout errors during connection failure
                 if attempt < max_retries - 1:
                     time.sleep(retry_delay)
                 else:
                     logger.error(get_text("imap_connection_failed_retries"))
                     raise ConnectionError(get_text("imap_connection_failed_retries")) from e
            except Exception as e:
                 logger.error(get_formatted("imap_unexpected_error", e), exc_info=True)
                 if client:
                     try: client.logout()
                     except: pass
                 raise ConnectionError(get_formatted("imap_unexpected_error", e)) from e
        return None

    def check_for_unsubscribes(self):
        """Checks the IMAP inbox using imapclient."""
        logger.info(get_text("checking_imap_for_unsubscribes"))
        client = None
        try:
            client = self._connect_imap()
            if not client:
                logger.error("IMAP connection failed unexpectedly without raising an error.")
                self.imap_check_failed.emit(get_text("imap_connection_failed_retries"))
                return

            # --- Select Mailbox using imapclient ---
            selected_folder_info = None
            folder_to_try = 'INBOX'
            try:
                logger.info(f"Attempting to select folder: '{folder_to_try}'")
                # select_folder returns folder status information
                selected_folder_info = client.select_folder(folder_to_try, readonly=False)
                logger.info(get_formatted("imap_inbox_selected", selected_folder_info.get(b'EXISTS', b'?')))

            except IMAPClient.Error as select_error: # Catch imapclient specific errors
                 error_str = str(select_error)
                 is_unsafe_login = "unsafe login" in error_str.lower() or "授权码" in error_str.lower()
                 if is_unsafe_login:
                     unsafe_login_msg = get_text("imap_unsafe_login_error")
                     logger.error(f"Folder selection failed: {unsafe_login_msg} Server response: {error_str}")
                     self.imap_check_failed.emit(f"{unsafe_login_msg} (during SELECT)")
                     return # Stop processing

                 logger.warning(f"Failed to select folder '{folder_to_try}': {error_str}. Listing folders.")
                 # List folders logic (imapclient style)
                 try:
                     folders = client.list_folders()
                     available_folders = [f[2] for f in folders] # Folder name is the 3rd element
                     logger.info(f"Available folders: {available_folders}")

                     # Try alternative names
                     common_inbox_names = ['INBOX']
                     if get_current_language() == 'zh':
                         common_inbox_names.append('收件箱')

                     selected_alternative = False
                     for name in common_inbox_names:
                         if name in available_folders and name.upper() != 'INBOX':
                             logger.info(f"Attempting to select alternative folder: '{name}'")
                             try:
                                 selected_folder_info = client.select_folder(name, readonly=False)
                                 logger.info(f"Successfully selected alternative folder '{name}'. Messages: {selected_folder_info.get(b'EXISTS', b'?')}")
                                 selected_alternative = True
                                 break
                             except IMAPClient.Error as alt_select_error:
                                 logger.warning(f"Failed to select alternative folder '{name}': {alt_select_error}")

                     if not selected_alternative:
                         logger.error(f"Could not select INBOX or any common alternative folder.")
                         self.imap_check_failed.emit(f"Failed to select INBOX or alternatives. Check logs for available folders.")
                         return
                 except Exception as list_err:
                      logger.error(f"Error listing folders: {list_err}")
                      self.imap_check_failed.emit(f"Error listing folders: {list_err}")
                      return
            except Exception as e: # Catch other unexpected errors during select
                 logger.error(get_formatted("imap_select_inbox_failed", str(e)), exc_info=True)
                 self.imap_check_failed.emit(get_formatted("imap_select_inbox_failed", str(e)))
                 return
            # --- End Select Mailbox ---

            # --- Search Logic using imapclient ---
            subject_pattern = 'Unsubscribe:'
            logger.info(f"Searching for UNSEEN emails...")
            # imapclient search returns list of message IDs (integers)
            msg_ids = client.search(['UNSEEN'])

            if not msg_ids:
                logger.info(get_text("no_new_unsubscribe_emails"))
            else:
                logger.info(get_formatted("found_potential_unsubscribe_emails", len(msg_ids)))
                processed_count = 0

                # Fetch headers for relevant messages
                # Note: imapclient fetch returns a dictionary {msg_id: {data_item: value}}
                # Fetch only Subject and From headers
                fetch_items = [b'BODY[HEADER.FIELDS (SUBJECT FROM)]']
                # Fetch in chunks to avoid overwhelming the server/memory if many messages
                chunk_size = 100
                for i in range(0, len(msg_ids), chunk_size):
                    chunk_ids = msg_ids[i:i+chunk_size]
                    try:
                        messages_data = client.fetch(chunk_ids, fetch_items)
                    except Exception as fetch_err:
                         logger.error(f"Error fetching message chunk ({chunk_ids}): {fetch_err}")
                         continue # Skip this chunk

                    for msg_id, data in messages_data.items():
                        try:
                            header_bytes = data.get(fetch_items[0])
                            if not header_bytes:
                                logger.warning(f"No header data found for message ID {msg_id}")
                                continue

                            headers = email.message_from_bytes(header_bytes)
                            subject_header = headers.get('Subject', '')
                            sender_header = headers.get('From', '')

                            # Decode subject
                            subject, encoding = decode_header(subject_header)[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(encoding or 'utf-8', errors='replace')

                            # Check subject pattern
                            if subject_pattern in subject:
                                match = re.search(r'Unsubscribe:\s*([a-f0-9\-]+)', subject, re.IGNORECASE)
                                if match:
                                    task_id_from_subject = match.group(1)
                                    sender_email = parseaddr(sender_header)[1]
                                    if sender_email:
                                        logger.info(get_formatted("processing_unsubscribe_request", sender_email, task_id_from_subject))
                                        if self.process_unsubscribe_request(task_id_from_subject, sender_email):
                                            # Mark email as read (Seen) using add_flags
                                            try:
                                                client.add_flags(msg_id, [b'\\Seen'])
                                                logger.info(get_formatted("marked_email_as_read", msg_id))
                                                processed_count += 1
                                            except Exception as flag_err:
                                                logger.warning(f"Failed to mark email ID {msg_id} as read: {flag_err}")
                                        else:
                                            logger.warning(get_formatted("unsubscribe_processing_failed_email", sender_email, task_id_from_subject))
                                    else:
                                        logger.warning(get_formatted("could_not_parse_sender", msg_id, sender_header))
                                else:
                                    logger.debug(f"Email ID {msg_id} has 'Unsubscribe:' but no valid Task ID found in subject: '{subject}'")

                        except Exception as process_err:
                            logger.error(get_formatted("error_processing_email_id", msg_id, process_err), exc_info=True)

                logger.info(get_formatted("unsubscribe_check_complete", processed_count))
            # --- End Search Logic ---

        except ConnectionAbortedError as cae:
             logger.error(f"IMAP connection aborted: {cae}")
             self.imap_check_failed.emit(str(cae))
        except ConnectionError as e:
            logger.error(get_formatted("imap_connection_error_during_check", e))
            self.imap_check_failed.emit(str(e))
        except IMAPClientError as e: # Catch specific imapclient errors
             logger.error(f"IMAPClient error during check: {e}", exc_info=True)
             self.imap_check_failed.emit(f"IMAPClient error: {e}")
        except Exception as e:
            logger.error(get_formatted("unexpected_error_during_check", e), exc_info=True)
            self.imap_check_failed.emit(get_formatted("unexpected_error_during_check", str(e)))
        finally:
            if client:
                try:
                    client.logout()
                    logger.info(get_text("imap_logged_out"))
                except Exception as logout_err:
                    logger.warning(get_formatted("imap_logout_error", logout_err))

    def process_unsubscribe_request(self, task_id: str, sender_email: str) -> bool:
        """Removes the sender from the specified task's recipient list."""
        try:
            tasks = get_tasks()
            task_to_update = None
            for task in tasks:
                if task.task_id == task_id:
                    task_to_update = task
                    break

            if not task_to_update:
                logger.warning(get_formatted("unsubscribe_task_not_found", task_id, sender_email))
                return False # Indicate failure, but don't stop overall check

            if sender_email in task_to_update.recipients:
                task_to_update.recipients.remove(sender_email)
                # Also remove from status if present
                if sender_email in task_to_update.recipients_status:
                    del task_to_update.recipients_status[sender_email]

                save_task(task_to_update)
                logger.info(get_formatted("recipient_unsubscribed", sender_email, task_to_update.name, task_id))
                # Emit signal for UI update
                self.unsubscribe_processed.emit(task_id, sender_email)
                return True
            else:
                logger.info(get_formatted("recipient_not_found_in_task", sender_email, task_to_update.name, task_id))
                return True # Consider it processed even if not found

        except Exception as e:
            logger.error(get_formatted("error_processing_unsubscribe", sender_email, task_id, e), exc_info=True)
            return False

# --- Manual Trigger Function ---
_unsubscribe_handler_instance = None

def get_unsubscribe_handler():
    """Gets a shared instance of the UnsubscribeHandler."""
    global _unsubscribe_handler_instance
    if _unsubscribe_handler_instance is None:
        _unsubscribe_handler_instance = UnsubscribeHandler()
    return _unsubscribe_handler_instance

def trigger_unsubscribe_check():
    """Manually triggers the check for unsubscribe emails."""
    logger.info(get_text("manual_unsubscribe_check_triggered"))
    handler = get_unsubscribe_handler()
    # Run in a separate thread to avoid blocking if called from UI
    thread = threading.Thread(target=handler.check_for_unsubscribes, daemon=True)
    thread.start()
    logger.info(get_text("unsubscribe_check_started_background"))

