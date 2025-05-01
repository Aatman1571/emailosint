# Email Investigation Tool

**Email Investigation Tool** is a comprehensive and powerful solution designed to help individuals and organizations detect and prevent email-based threats. It integrates two main components:

- **Email Header Analyzer**
- **Email OSINT**

## 🔍 Features

### 📬 Email Header Analyzer
- Analyzes raw email headers
- Provides hop-by-hop relay details
- Detects email spoofing attempts
- Assigns spam score using various metrics
- Checks email sender against known threat databases

### 🌐 Email OSINT

- Accepts an email address as input
- **Uses IntelX API**, one of the largest datasets available, to check for leaked or breached data linked to the email
- Scans over **121+ websites and platforms** to identify accounts associated with the email address
- Discovers platforms and websites associated with the email
- Generates time-delayed activity graphs
- Determines the likely country of origin
- Accepts an email address as input
- Identifies if the email has been in known data breaches
- Discovers platforms and websites linked to the email
- Includes time-delayed activity graphs
- Determines likely country of origin

## 🚀 Benefits

- Detects sophisticated phishing and spoofing attacks
- Enables early threat detection and response
- Supports cybersecurity operations and digital forensics
- Helps prevent data breaches and email compromise

## 🛠️ Installation

```bash
git clone https://github.com/yourusername/emailosint.git
cd "Email Header Analyzer"
pip install -r requirements.txt
```

## ▶️ Usage

Run the web interface locally:

```bash
python app.py
```

Then visit: [http://localhost:8080](http://localhost:8080)

## 📁 Directory Structure

- `modules/`: Email scanning and OSINT modules
- `templates/`: Web UI (Flask-based)
- `static/`: CSS and image assets
- `holehe/`: External OSINT integration

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
