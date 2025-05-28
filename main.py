import os
from flask import Flask, request, jsonify
import re
from pathlib import Path
import magic
import hashlib
from datetime import datetime
import uuid
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
from unidecode import unidecode
import logging
from logging.handlers import RotatingFileHandler
import traceback


# Максимальний розмір файлу (в байтах) 1 МБ
MAX_FILE_SIZE = 1 * 1024 * 1024
# Максимальна роздільна здатність по більшій стороні
MAX_IMAGE_DIMENSION = 1920


# Створюємо лог-файл з ротацією
log_handler = RotatingFileHandler("logs.log", maxBytes=1_000_000, backupCount=5)
log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
log_handler.setFormatter(log_formatter)

# Підключаємо до кореневого логера
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)


# API
app = Flask(__name__)


# Завантажуємо змінні з .env
load_dotenv()


def generate_correct_unique_filename(filename):

    # Отримуємо чисту частину імені файлу без розширення
    base_name, extension = os.path.splitext(filename)

    # Перетворюємо кирилицю в латиницю
    base_name = unidecode(base_name)

    # Очищення імені файлу та перетворення назви файлу в ASCII-дружню версію
    base_name = re.sub(r"[^\w\s-]", "", base_name)  # Забираємо все, крім букв/цифр/_/пробілів
    base_name = re.sub(r"[-\s]+", "_", base_name)  # Пробіли/дефіси і підкреслення

    if not base_name:
        base_name = "file"

    # Генеруємо 8-символьний унікальний суфікс за допомогою UUID
    unique_suffix = uuid.uuid4().hex[:8]
    final_filename = f"{base_name}_{unique_suffix}{extension}"

    return final_filename


def resize_compress_image(file_name, image_file):
    try:
        image = Image.open(image_file)
    except Exception as e:
        logging.error(f"Error opening image {file_name}: {e}")
        raise ValueError(f"Error opening image: {e}")

    # Якщо файл PNG — конвертуємо у RGB (JPEG не підтримує прозорість)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    # Зменшення роздільної здатності, якщо перевищує max_dimension
    width, height = image.size
    max_current_dim = max(width, height)
    if max_current_dim > MAX_IMAGE_DIMENSION:
        scale = MAX_IMAGE_DIMENSION / max_current_dim
        new_size = (int(width * scale), int(height * scale))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    # Конвертуємо все до JPEG для кращого стискання
    img_format = "JPEG"

    quality = 95
    buffer = BytesIO()

    # Стискання зображення з поступовим зменшенням якості
    while True:
        try:
            buffer.seek(0)
            buffer.truncate()
            image.save(buffer, format=img_format, quality=quality)
            size = buffer.tell()
            if size <= MAX_FILE_SIZE or quality <= 10:
                break
            quality -= 5
        except Exception as e:
            logging.error(f"Error compressing image {file_name}: {e}")
            raise ValueError(f"Error compressing image: {e}")

    logging.info(f"Image {file_name} compressed to {size} bytes at quality={quality}")
    buffer.seek(0)

    return buffer


# API_1: Документація в файлі API_DOC.md
# Завантаження файлу в задану папку
@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        hard_key = os.getenv("HARD_KEY")
        folder = os.getenv("UPLOAD_FOLDER")
        os.makedirs(folder, exist_ok=True)

        key = request.args.get("key")

        if key != hard_key:
            logging.warning(f"Access forbidden attempt with key: {key}")
            return jsonify({"error": "Access forbidden!"}), 403

        if "file" not in request.files:
            logging.warning("No file part in request.")
            return jsonify({"error": "No file part"}), 400

        # Отримуємо файл
        original_file = request.files["file"]

        if original_file.filename == '':
            logging.warning("No selected file in request.")
            return jsonify({"error": "No selected file"}), 400

        # Зчитуємо файл (розмір, ім'я, тип)
        file_bytes = original_file.read()
        file_size = len(file_bytes)
        file_name = original_file.filename
        mime_type = magic.from_buffer(file_bytes, mime=True)

        # Генеруємо унікальне правильне ім’я (перетворюємо кирилицю)
        final_filename = generate_correct_unique_filename(file_name)

        # Спроба стиснути файл, якщо розмір перевищує 1 МБ

        if file_size > MAX_FILE_SIZE and mime_type.startswith("image/"):

            # зменшуємо та стискаємо файл
            compressed_file = resize_compress_image(final_filename, BytesIO(file_bytes))

            # Зміна розширення на .jpg
            final_filename = os.path.splitext(final_filename)[0] + ".jpg"

            # зберігаємо файл
            save_path = os.path.join(folder, final_filename)
            with open(save_path, "wb") as f:
                f.write(compressed_file.read())

        # Файл не є зображенням або розмір файлу <=1 МБ, зберігаємо як є
        else:

            # Просто зберігаємо як є
            save_path = os.path.join(folder, final_filename)
            with open(save_path, "wb") as f:
                f.write(file_bytes)

        # Інформація про файл
        data = {"fileName": final_filename,
                "id": hashlib.md5(final_filename.encode()).hexdigest(),
                "size": os.path.getsize(save_path),
                "title": Path(final_filename).stem,
                "type": mime_type,
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}

        logging.info(f"Uploaded file: {data}")

        return jsonify({"message": "File uploaded successfully.",
                        "data": data}), 200

    except ValueError as e:
        # Логування помилок, що виникають при стисненні чи відкритті файлів
        logging.error(f"ValueError during file processing: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        # Логування загальних помилок
        logging.error("Unexpected error:\n" + traceback.format_exc())
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


# API_2: Документація в файлі API_DOC.md
# Видалення файлу з заданої папки
@app.route("/delete", methods=["POST"])
def delete_file():

    user_data = request.get_json()
    filename = user_data["fileName"]

    folder = os.getenv("UPLOAD_FOLDER")

    file_path = Path(os.path.join(folder, filename))

    if file_path.is_file():
        os.remove(file_path)

        logging.info(f"Deleted file: {filename}")
        return jsonify({"message": "File deleted successfully.",
                        "fileName": filename}), 200
    else:
        logging.error(f"File does not exist in the upload folder: {filename}")
        return jsonify({"message": "File does not exist.",
                        "fileName": filename}), 404



