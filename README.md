
# Flask File Upload & Compression API

This project is a simple Flask-based API for uploading, compressing, and deleting files, with special handling for image compression. 
It includes error logging, MIME-type detection, and basic access control via an API key.

## Features

- API for Uploading files to a specified folder
- Compress images larger than 1MB (converted to JPEG)
- API key access control via .env
- API for Deleting uploaded files
- Error logging
- MIME type detection using python-magic

## Requirements

- Python 3.8+
- Flask
- Pillow
- python-dotenv
- python-magic
- file (libmagic system dependency)