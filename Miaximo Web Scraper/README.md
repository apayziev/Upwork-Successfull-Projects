# The **Automated GIF Download from [Mixamo Website](https://www.mixamo.com/)** 

## Overview
The **Automated GIF Download from Mixamo Website** project is a Python script designed to automate downloading GIF animations from the Mixamo website. Mixamo is a widely used platform that provides 3D character animations for various applications, including game development, animation projects, and more. This script simplifies the task of collecting GIF animations from Mixamo, making it a valuable tool for content creators and developers.

## Key Features

- **Web Scraping with Selenium:** The project utilizes Selenium, a web scraping library, to interact with the Mixamo website. It extracts information about GIF animations, including titles, descriptions, and GIF URLs.

- **Sanitizing and Truncating Descriptions:** Animation descriptions are cleaned and truncated to ensure they are suitable for use as filenames. Special characters are removed, and descriptions are trimmed to a specified maximum length.

- **Parallel GIF Downloads:** To improve efficiency, the project employs a ThreadPoolExecutor to download GIFs from the current page in parallel. This allows for faster acquisition of animations.

- **Pagination Support:** The script is designed to navigate multiple pages of Mixamo's animation catalog. It automatically clicks on the "Next Page" button and waits for the next set of animations to load before continuing the download process.

- **Directory Management:** The project creates a directory for storing downloaded GIFs if it doesn't already exist. GIFs are saved in this directory with filenames that include the animation's index, title, and sanitized description.

# Installation guide

1. Create an environment inside the project folder:<br/>
For Win:
    `python -m venv env`<br/>
For macOS:
    `virtualenv venv`

2. Activate environment:<br/>
For Win: 
    `.\env\Scripts\activate`<br />
For MacOS: 
    `source venv/bin/activate`

3. Installing all required packages:
    `pip install -r requirments.txt`

4. Modify the `params.py` file to set your desired parameters

5. Run the following command to download gifs:
    `python main.py`
6. Enjoy the program. Happy animating with Mixamo!

## Use Cases

- **Game Development:** Game developers can use this tool to quickly gather animated character resources for their games.

- **Animation Projects:** Animators and multimedia creators can automate the collection of animated assets for their projects.

- **Asset Compilation:** Anyone interested in building a library of Mixamo animations can benefit from this automated downloading tool.

## Benefits

- **Time-Saving:** Automating the download process saves users significant time compared to manually downloading each animation.

- **Efficiency:** Parallel downloads and pagination support enhance the efficiency of gathering Mixamo assets.

- **Organization:** The script provides well-organized and descriptive filenames for downloaded GIFs.
