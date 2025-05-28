
# Flask File Upload & Management API

This project provides a secure and efficient REST API built with Flask for uploading, compressing, saving, 
and deleting files — primarily images. It includes key features such as file type validation, 
Cyrillic-to-Latin filename conversion, size-based image compression, and access control using a predefined API key.

The API is designed for backend services (chatbots) that require controlled media uploads with automatic 
optimization and secure handling.

## Features

- Secure File Upload
Users must provide a valid API key (HARD_KEY) to access the upload endpoint.
- Filename Sanitization & Transliteration
The uploaded file’s name is transliterated from Cyrillic to Latin using unidecode, 
stripped of special characters, and appended with a unique suffix to avoid collisions.
- MIME Type Validation
MIME type is detected using the python-magic library to confirm the nature of the file content, not just its extension.
- File Size & Compression Handling
  - Files under 1MB are stored directly.
  - Image files larger than 1MB are:
    - Resized to a maximum dimension (width or height) of 1920px. 
    - Converted to JPEG format (with optional mode change from RGBA to RGB). 
    - Compressed by progressively lowering quality until size ≤ 1MB.
- Logging with Rotation
All actions (uploads, deletions, errors) are logged using Python’s logging module with RotatingFileHandler 
to prevent log bloating.
- File Metadata in Response
Each upload returns metadata including the filename, size, MIME type, unique ID (MD5 hash), title (without extension), 
and timestamp.
- File Deletion
A second endpoint allows secure deletion of a previously uploaded file via a JSON request.

## Requirements

- Python 3.8+
- Flask
- Pillow
- python-dotenv
- python-magic
- file (libmagic system dependency)
- unidecode