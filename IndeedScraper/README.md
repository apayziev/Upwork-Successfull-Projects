# Indeed Construction Job Scraper

A Python web scraper that extracts construction job listings from Indeed.com.

---

## Quick Start

### 1. Install Python
Make sure you have **Python 3.8 or higher** installed:
```bash
python --version
```

### 2. Set Up Virtual Environment

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements_botasaurus.txt
```

### 4. Run the Scraper

**Mac/Linux:**
```bash
python3 indeed_scraper.py
```

**Windows:**
```bash
python indeed_scraper.py
```

---

## What It Does

1. Opens a Chrome browser automatically
2. Extracts all construction skill categories from Indeed
3. Scrapes job listings for each skill across all pages
4. Saves everything to a single CSV file

---

## Output

**Location:** `indeed_construction_YYYYMMDD_HHMMSS/construction_all_jobs.csv`

**Columns:**
- Job Title
- Employer Name
- City, State, Postal Code
- Street Address
- Salary
- Job Type
- Description
- Job URL
- Scraped Date

---

## Troubleshooting

**Virtual environment won't activate?**
- Mac/Linux: Try `chmod +x venv/bin/activate`
- Windows: Run PowerShell as admin and execute:
  ```bash
  Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

**Python command not found?**
- Try `python3` or `py` instead of `python`

**Installation errors?**
```bash
pip install --upgrade pip
pip install -r requirements_botasaurus.txt
```

---

## Requirements

- Python 3.8+
- 4GB RAM minimum (8GB recommended)
- 500MB free disk space
- Internet connection

---

## Done?

Deactivate the virtual environment:
```bash
deactivate
```

---

**Questions?** Check that:
- ✓ Python 3.8+ is installed
- ✓ Virtual environment is activated `(venv)`
- ✓ All packages installed successfully
