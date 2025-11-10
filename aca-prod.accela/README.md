# Lee County Permit Scraper

A GUI application to scrape permit data from Lee County's Accela portal.

## Quick Start

### Windows

```cmd
# 1. Create virtual environment
python -m venv venv

# 2. Activate virtual environment
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Chrome browser support
patchright install chrome

# 5. Run the application
python run_with_gui.py
```

### Mac / Linux

```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate virtual environment
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Chrome browser support
patchright install chrome

# 5. Run the application
python3 run_with_gui.py
```

**Note:** After first setup, you only need to activate the virtual environment and run the application:

**Windows:**
```cmd
venv\Scripts\activate
python run_with_gui.py
```

**Mac/Linux:**
```bash
source venv/bin/activate
python3 run_with_gui.py
```

That's it! The GUI will open and you can start scraping.

## Output

Results are saved in timestamped folders:

```
output/scrape_20251110_143052/
├── permits_data.json  (All permit data)
└── permits_data.csv   (Key fields for Excel)
```

## Troubleshooting

**"Module not found" error:**
```bash
pip install -r requirements.txt    # Windows
pip3 install -r requirements.txt   # Mac/Linux
```

**"Browser not found" error:**
```bash
patchright install chrome
```

**GUI doesn't open:**
- Make sure Python is installed
- Make sure all dependencies are installed
- Check that PyQt6 installed correctly
