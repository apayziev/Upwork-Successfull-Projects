# Circle Community Scraper

A powerful web scraping tool designed to extract member data from Circle Community platforms. This project successfully extracted data from over 2,700 community members, including their profiles, social media links, and roles.

## 🔍 Data Extracted

The scraper collects the following information for each member:
- Profile URL
- Full Name
- Role/Title
- Social Media Links:
  - LinkedIn
  - Twitter
  - Facebook
  - Instagram
  - TikTok
- Personal/Company Website

## 📊 Statistics
- Total Members Scraped: 2,747+
- Data Format: CSV
- Last Updated: December 19, 2024

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/circle-community-scraper.git
cd circle-community-scraper
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## 🔧 Requirements

- Python 3.8+
- Dependencies:
  - selenium==4.16.0
  - requests==2.32.3
  - attrs==24.3.0
  - And other dependencies listed in requirements.txt

## 🔑 Configuration

1. Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```

2. Update the `.env` file with your credentials and settings

## 📝 Usage

1. Ensure you have the correct URLs in `members_urls.txt`
2. Run the scraper:
```bash
python main.py
```

The scraped data will be saved in CSV format with a timestamp (e.g., `members_data_20241219_134354.csv`).

## 📈 Output

The scraper generates a CSV file containing member information with the following columns:
- Profile URL
- Full Name
- Role
- LinkedIn
- Twitter
- Facebook
- Instagram
- TikTok
- Website

## ⚠️ Disclaimer

This tool is for educational purposes only. Please respect website terms of service and implement appropriate delays between requests to avoid overwhelming the target servers.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
