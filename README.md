# Gmail Analyzer

Gmail Analyzer is a Python script that interacts with the Gmail API to retrieve and analyze email messages. It fetches information such as date received, sender email, domain origin, size of the email, presence of attachments, and the subject of the email.

## Getting Started

### Prerequisites

- Python 3
- Google Cloud Platform project with the Gmail API enabled
- OAuth 2.0 credentials file (`credentials.json`)

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/bayu01/gmail-analyzer.git
   
2. `pip install -r requirements.txt`


### Usage

Run the script by executing:

```bash
python gmail_analyzer.py
```

The script will authenticate with Gmail, fetch all the email metadata and store it on a sqlite3 db

## Features
* Authentication with Gmail API using OAuth 2.0 credentials.
* Retrieval of email information such as date received, sender email, domain origin, size of the email, presence of attachments, and subject.
* Database storage (SQLite) of email information for later analysis.


## Database Schema

The script uses SQLite to store email information. The database schema is as follows:

```sqlite-sql
CREATE TABLE IF NOT EXISTS emails (
   message_id TEXT PRIMARY KEY,
   date_received BIGINT,
   from_email TEXT,
   domain_origin TEXT,
   size_of_email INTEGER,
   has_attachments INTEGER,
   subject TEXT
);
```

## Sample Data

Here is an example of how the data might look in the database:


| message_id       | date_received | from_email              | domain_origin | size_of_email | has_attachments | subject                 |
|------------------|---------------|-------------------------|---------------|---------------|-----------------|-------------------------|
| 145488604a5b2bf0 | 1461694886000 | john.doe@example.com    | example.com   | 1500          | 1               | "FWD: Meeting Tomorrow" |
| 130d2587bf896d3b | 1419017670000 | alice.smith@example.org | example.org   | 1200          | 0               | "RE: Proposal Attached" |
| ...              | ...           | ...                     | ...           | ...           | ...             | ...                     |

