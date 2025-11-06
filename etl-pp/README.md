# Pacparts Scraper

A Python-based web scraper for extracting product information from Pacparts.com. This project consists of three scraping scripts designed to collect URLs and detailed information about Casio watch parts and models.

## 📋 Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Usage](#usage)
- [Scripts](#scripts)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## 🔍 Overview

This scraper project consists of three main scripts:

1. **scrape_pacparts_product_url.py** - Collects all product URLs (parts and models)
2. **scrape_pacparts_model_details.py** - Extracts detailed information about models
3. **scrape_pacparts_part_details.py** - Extracts detailed information about parts

## 💻 Installation

### Prerequisites

- Python 3.8 or higher
- Chrome browser installed on your system

### Step 1: Install Python

#### Windows
1. Download Python from [python.org](https://www.python.org/downloads/)
2. Run the installer and check "Add Python to PATH"
3. Verify installation:
```bash
python --version
```

#### macOS
```bash
# Using Homebrew
brew install python3

# Verify installation
python3 --version
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3 python3-pip

# Verify installation
python3 --version
```

#### Linux (Fedora/RHEL)
```bash
sudo dnf install python3 python3-pip

# Verify installation
python3 --version
```
```

### Step 2: Install Python Requirements

```bash
# Windows
pip install -r requirements.txt

# macOS/Linux
pip3 install -r requirements.txt
```

### Step 3: Install Patchright Chrome

After installing the Python packages, you need to install the Chrome browser for Patchright:

```bash
# Windows
patchright install chrome

# macOS/Linux
patchright install chrome
```

This command downloads and installs a patched version of Chrome that works with the scraper.

## 🚀 Usage

### Recommended Workflow

Run the scripts in this order for a complete scraping workflow:

#### 1. Collect Product URLs (First Step)

This script scrapes all product pages and separates URLs into parts and models.

```bash
# Windows
python scrape_pacparts_product_url.py

# macOS/Linux
python3 scrape_pacparts_product_url.py
```

**Output:**
- `casio_part_urls.csv` - All part URLs
- `casio_model_urls.csv` - All model URLs
- `failed_pages.txt` - Pages that failed to scrape (if any)

**What it does:**
- Navigates through all paginated product listing pages
- Extracts product URLs
- Classifies URLs as either parts or models
- Saves them to separate CSV files

#### 2. Scrape Model Details (Second Step)

Run this after collecting URLs to get detailed model information.

```bash
# Windows
python scrape_pacparts_model_details.py

# macOS/Linux
python3 scrape_pacparts_model_details.py
```

**Input:** `casio_model_urls.csv` (from step 1)

**Output:** `casio_model_details.csv`

**Data collected:**
- Model number and module number
- Manufacturer
- Product type and category
- Year
- Model image URL
- List of all part numbers for the model
- Parts count validation

#### 3. Scrape Part Details (Third Step)

Run this after collecting URLs to get detailed part information.

```bash
# Windows
python scrape_pacparts_part_details.py

# macOS/Linux
python3 scrape_pacparts_part_details.py
```

**Input:** `casio_part_urls.csv` (from step 1)

**Output:** `casio_part_details.csv`

**Data collected:**
- Part number
- Title/description
- Manufacturer
- Availability status
- List price
- Replacement part (if discontinued)
- Associated model numbers
- Part image URL

**Key settings to adjust:**
- `num_workers` - Number of concurrent browser tabs (more = faster, but more resource-intensive)
- `headless` - Set to `True` to run browser in background (no UI) -> not recommended with this setup
- `batch_size` - Number of URLs to process before restarting browser
- `page_timeout` - Maximum time to wait for page load (milliseconds)

## 🛠️ Troubleshooting

### Common Issues

#### 1. Chrome Not Found
```
Error: Executable doesn't exist at <path>
```
**Solution:** Run `patchright install chrome` again

#### 2. Timeout Errors
If pages are timing out frequently:
- Increase `page_timeout` in the config
- Reduce `num_workers` to decrease load
- Check your internet connection

#### 3. Module Not Found
```
ModuleNotFoundError: No module named 'patchright'
```
**Solution:** Reinstall requirements
```bash
pip install -r requirements.txt
```

#### 4. Permission Errors (Linux/macOS)
```bash
# Use sudo or pip with --user flag
pip3 install --user -r requirements.txt
```

#### 5. Browser Profile Issues
If the scraper behaves unexpectedly, delete the browser profile:
```bash
# Windows
rmdir /s browser_profile

# macOS/Linux
rm -rf browser_profile
```

### Performance Tips

1. **Adjust worker count** based on your system:
   - 2-4 workers for older systems
   - 5-8 workers for modern systems with good internet

2. **Use headless mode** for better performance:
   - Set `headless: bool = True` in config

3. **Monitor system resources**:
   - Each worker opens a browser tab
   - Close other applications if needed

## 📊 Output Files

| File | Description |
|------|-------------|
| `casio_part_urls.csv` | List of all part URLs |
| `casio_model_urls.csv` | List of all model URLs |
| `casio_model_details.csv` | Detailed model information with part numbers |
| `casio_part_details.csv` | Detailed part information with associated models |
| `failed_pages.txt` | Page numbers that failed to scrape (if any) |

## 📝 Notes

- The scraper uses a persistent browser profile (`browser_profile/`) to maintain session state
- Progress is displayed in real-time in the console
- Failed pages are tracked and can be retried later
- The scraper includes built-in retry logic for failed requests
- Batch processing prevents memory issues with large datasets

## ⚠️ Legal Notice

This scraper is for educational purposes. Always:
- Review the website's Terms of Service and robots.txt
- Respect rate limits and server resources
- Use responsibly and ethically

---

**Need help?** Check the troubleshooting section or review the configuration options above.
