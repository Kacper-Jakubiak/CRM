from integrations.reading_emails import process_new_emails


def pull_new_emails(db):
  return process_new_emails(db)