import os
from flask import Flask, request, jsonify
from pathlib import Path
import magic
import hashlib
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import logging


# Налаштування лог-файлу
logging.basicConfig(
    filename="Log_errors.log",  # Файл для запису логів
    level=logging.ERROR,        # Логуємо помилки та критичні помилки
    format="%(asctime)s - %(levelname)s - %(message)s",  # Формат повідомлення
    datefmt="%Y-%m-%d %H:%M:%S"  # Формат дати та часу без мілісекунд
)


# API
app = Flask(__name__)


# Завантажуємо змінні з .env
load_dotenv()


def compress_image(image_file):
    try:
        image = Image.open(image_file)
    except Exception as e:
        logging.error(f"Error opening image: {e}")
        raise ValueError(f"Error opening image: {e}")

    # Розмір стискання
    max_size = 1 * 1024 * 1024

    # Якщо файл PNG — конвертуємо у RGB (JPEG не підтримує прозорість)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    # Конвертуємо все до JPEG для кращого стискання
    img_format = "JPEG"

    quality = 95
    buffer = BytesIO()

    while True:
        try:
            buffer.seek(0)
            buffer.truncate()
            image.save(buffer, format=img_format, quality=quality)
            size = buffer.tell()
            if size <= max_size or quality <= 10:
                break
            quality -= 5
        except Exception as e:
            logging.error(f"Error compressing image: {e}")
            raise ValueError(f"Error compressing image: {e}")

    buffer.seek(0)

    return buffer


# API_1: Документація в файлі API_DOC.md
# Завантаження файлу в задану папку
@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        hard_key = os.getenv("HARD_KEY")
        folder = os.getenv("UPLOAD_FOLDER")

        key = request.args.get("key")

        if key != hard_key:
            return jsonify({"error": "Access forbidden!"}), 403

        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files["file"]
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Зчитуємо файл
        file_bytes = file.read()
        file_size = len(file_bytes)

        # Спроба стиснути файл, якщо розмір перевищує 1 МБ
        max_size = 1 * 1024 * 1024

        if file_size > max_size:

            mime_type = magic.from_buffer(file_bytes, mime=True)

            if mime_type.startswith("image/"):
                compressed_file = compress_image(BytesIO(file_bytes))

                # Примусово міняємо розширення на .jpg
                save_path = os.path.join(folder, Path(file.filename).stem + ".jpg")

                with open(save_path, "wb") as f:
                    f.write(compressed_file.read())
            else:

                # Файл не є зображенням, зберігаємо як є
                save_path = os.path.join(folder, file.filename)
                file.save(save_path)
        else:
            # Якщо файл <=1 МБ, просто зберігаємо його
            save_path = os.path.join(folder, file.filename)
            file.save(save_path)

        # Інформація про файл
        data = {"fileName": file.filename,
                "id": hashlib.md5(str(file.filename).encode()).hexdigest(),
                "size": os.path.getsize(save_path),
                "title": Path(file.filename).stem,
                "type": magic.from_file(save_path, mime=True)}

        print(data)

        return jsonify({"message": "File uploaded successfully.",
                        "data": data}), 200

    except ValueError as e:
        # Логування помилок, що виникають при стисненні чи відкритті файлів
        logging.error(f"ValueError: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        # Логування загальних помилок
        logging.error(f"Unexpected error: {e}")
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
        print("File deleted successfully.")
        return jsonify({"message": "File deleted successfully.",
                        "fileName": filename}), 200
    else:
        print("The file does not exist")
        return jsonify({"message": "File does not exist.",
                        "fileName": filename}), 404


if __name__ == '__main__':
    app.run(debug=True, port=8080)

