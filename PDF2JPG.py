import sys
import fitz  # PyMuPDF to work with PDF files
from PIL import Image  # For image processing with the Pillow library
import io  # For input and output operations
import os  # For interacting with the operating system (file and directory management)
import logging  # For logging operations
from concurrent.futures import ThreadPoolExecutor  # To enable parallel processing
import configparser  # For reading and writing INI files
from logging.handlers import TimedRotatingFileHandler  # rotate logs every month
from datetime import datetime
import shutil
import zipfile #for handling ZIP files
from html2image import Html2Image

# Function to rename the log file if the month has changed
def rename_log_file():
    log_directory = "logs"
    log_file = os.path.join(log_directory, "conversion.log")
    current_time = datetime.now()

    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    if os.path.exists(log_file):
        #Get the last modified date of the log file
        file_creation_time = datetime.fromtimestamp(os.path.getmtime(log_file))
        if file_creation_time.month != current_time.month or file_creation_time.year != current_time.year:
            #Rename log file if current month is different
            new_log_name = os.path.join(log_directory, f'conversion_{file_creation_time.strftime("%Y-%m")}.log')
            shutil.move(log_file, new_log_name)
    
    #If the log file does not exist, a new one will be created
    return log_file

# Setup logging
def setup_logging():
    #Rename log file if month changed
    log_file = rename_log_file()

    # Logging configuration using TimedRotatingFileHandler
    log_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1)
    log_handler.suffix = "%Y-%m"
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    log_handler.setFormatter(log_formatter)

    console_handler = logging.StreamHandler()  
    console_handler.setFormatter(log_formatter)

    logging.basicConfig(level=logging.INFO, handlers=[log_handler, console_handler])

# Generic function to handle output directories and renaming
def create_output_directory(output_dir, relative_dir, base_name):
    output_path = os.path.join(output_dir, relative_dir, base_name)
    if not os.path.exists(output_path):
        os.makedirs(output_path)
        logging.info(f"Output directory created: {output_path}")
    return output_path

def resize_image(image, max_width, max_height):
    original_width, original_height = image.size
    aspect_ratio = original_width / original_height
    # If width is big
    if original_width > max_width:
        new_width = max_width
        new_height = int(new_width / aspect_ratio)
        image = image.resize((new_width, new_height), Image.LANCZOS)
    # If height is big
    if original_height > max_height:
        new_height = max_height
        new_width = int(aspect_ratio * new_height)
        image = image.resize((new_width, new_height), Image.LANCZOS)
    return image

# Function to convert PNG to JPG
def png_to_jpg(png_path, output_dir, relative_dir, quality=95, max_width=1920, max_height=1080):
    logging.info(f"Starting PNG conversion for: {png_path}")
    try:
        image = Image.open(png_path)
        base_name = os.path.splitext(os.path.basename(png_path))[0]
        png_output_dir = create_output_directory(output_dir, relative_dir, base_name)
        jpeg_path = os.path.join(png_output_dir, f'{base_name}.jpg')
         # Apply size
        image = resize_image(image, max_width, max_height)
        image = image.convert("RGB")  
        image.save(jpeg_path, 'JPEG', quality=quality)
        logging.info(f"PNG {png_path} converted to JPG at {jpeg_path}")
        rename_processed_file(png_path)
    except Exception as e:
        logging.error(f"Failed to convert PNG file: {png_path}, Error: {e}")

def html_to_jpg(html_path, output_dir, relative_dir, dpi=300, quality=95, max_width=1920, max_height=1080):
    logging.info(f"Starting HTML conversion for: {html_path}")
    try:
        hti = Html2Image()
        base_name = os.path.splitext(os.path.basename(html_path))[0]
        html_output_dir = create_output_directory(output_dir, relative_dir, base_name)

        # Use filename instead of the full file path
        jpg_file_name = f'{base_name}.jpg'

        # Only file name is given using Html2Image
        hti.screenshot(
            html_file=html_path,
            save_as=jpg_file_name,
            size=(max_width, max_height)
        )
        # Move the file saved with the screenshot to the correct directory
        full_jpg_path = os.path.join(html_output_dir, jpg_file_name)
        shutil.move(jpg_file_name, full_jpg_path)

        # Open the image again to adjust the quality and save it.
        with Image.open(full_jpg_path) as img:
            img.save(full_jpg_path, 'JPEG', quality=quality)

        logging.info(f"HTML {html_path} converted to JPG at {full_jpg_path}")

        rename_processed_file(html_path)
        return True
    except Exception as e:
        logging.error(f"Failed to convert HTML file: {html_path}, Error: {e}")
        return False

# Updated rename_processed_file function to rename HTML correctly
def rename_processed_file(file_path):
    file_dir, file_name = os.path.split(file_path)
    base_name, extension = os.path.splitext(file_name)
    
    # Define the new file name based on the file type
    if extension.lower() in ['.pdf', '.png', '.html', '.zip']:
        processed_file_name = f"{base_name}_processed{extension}"
    else:
        # If the file type is not recognized, don't rename
        logging.warning(f"Unrecognized file type for renaming: {file_path}")
        return
    
    processed_file_path = os.path.join(file_dir, processed_file_name)
    
    try:
        os.rename(file_path, processed_file_path)
        logging.info(f"Renamed file to: {processed_file_path}")
    except Exception as e:
        logging.error(f"Failed to rename file: {file_path}, Error: {e}")

# Function to convert PDF to JPG
def pdf_to_jpg(pdf_path, output_dir, relative_dir, dpi=300, quality=95, max_width=1920, max_height=1080):
    logging.info(f"Starting conversion for: {pdf_path}")
    try:
        # Open the PDF document
        pdf_document = fitz.open(pdf_path)
        logging.info(f"PDF file opened successfully: {pdf_path}")
    except Exception as e:
        logging.error(f"Failed to open PDF file: {pdf_path}, Error: {e}")
        return False
    
    # Stores the JPEG image in the same directory structure as relative_dir in output_directory
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    pdf_output_dir = create_output_directory(output_dir, relative_dir, base_name)

    # Iterate over each page in the PDF
    for page_number in range(len(pdf_document)):
        try:
            # Load the page and create a pixmap
            page = pdf_document.load_page(page_number)
            pix = page.get_pixmap(dpi=dpi)
            img_data = io.BytesIO(pix.tobytes(output='jpeg'))
            image = Image.open(img_data)
            # Boyutlandırmayı uygula
            image = resize_image(image, max_width, max_height)
            jpeg_path = os.path.join(pdf_output_dir, f'{base_name}_page_{page_number + 1}.jpg')
            image.save(jpeg_path, 'JPEG', quality=quality)
            logging.info(f'Page {page_number + 1} of {pdf_path} saved as {jpeg_path}')
        except Exception as e:
            logging.error(f"Failed to convert page {page_number + 1} of {pdf_path}, Error: {e}")
            return False
        
    pdf_document.close()
    rename_processed_file(pdf_path)
    return True

# Function to process ZIP files and convert contents
def process_zip_file(zip_path, output_dir, dpi=300, quality=95, max_width=1920, max_height=1080):
    logging.info(f"Processing ZIP file: {zip_path}")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            base_name = os.path.splitext(os.path.basename(zip_path))[0]
            zip_output_dir = create_output_directory(output_dir, "", base_name)
            zip_ref.extractall(zip_output_dir)

            # Process the extracted files, ignoring files in '__MACOSX' folder
            process_files_in_directory(zip_output_dir, output_dir, dpi, quality, max_width, max_height)

            # Rename the original ZIP to indicate it has been processed
            rename_processed_file(zip_path)
    except Exception as e:
        logging.error(f"Failed to process ZIP file: {zip_path}, Error: {e}")

# General function to process files in a directory
def process_files_in_directory(input_dir, output_dir, dpi=300, quality=95, max_width=1920, max_height=1080):
    if not os.path.isdir(input_dir):
        logging.error(f"Invalid input directory: {input_dir}")
        print("Invalid input directory. Please provide a valid path.")
        return

    file_tasks = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            file_path = os.path.join(root, file)
            relative_dir = os.path.relpath(root, input_dir)

            # Skip files inside '__MACOSX' folder
            if '__MACOSX' in file_path:
                logging.info(f"Skipping file from '__MACOSX': {file_path}")
                continue

            # PDF files
            if file.endswith(".pdf") and not file.endswith("_processed.pdf"):
                file_tasks.append((pdf_to_jpg, file_path, output_dir, relative_dir, dpi, quality, max_width, max_height))
            
            # PNG files
            elif file.endswith(".png") and not file.endswith("_processed.png"):
                file_tasks.append((png_to_jpg, file_path, output_dir, relative_dir, quality, max_width, max_height))
            
            # HTML files
            elif file.endswith(".html") and not file.endswith("_processed.html"):
                file_tasks.append((html_to_jpg, file_path, output_dir, relative_dir, quality, max_width, max_height))  
            
            # ZIP files (in case ZIPs are nested)
            elif file.endswith(".zip") and not file.endswith("_processed.zip"):
                file_tasks.append((process_zip_file, file_path, output_dir, dpi, quality, max_width, max_height))

    total_files = len(file_tasks)
    logging.info(f"Found {total_files} files to process.")
    successful_conversions = 0
    failed_conversions = 0

    # Parallel processing
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(task[0], *task[1:]): task[1] for task in file_tasks}
        for future in futures:
            try:
                result = future.result()
                if result is None or result:  
                    successful_conversions += 1
                else:
                    failed_conversions += 1
                    logging.error(f"Conversion failed for: {futures[future]}")
            except Exception as e:
                failed_conversions += 1
                logging.error(f"Unexpected error occurred for: {futures[future]}, Error: {e}")

    logging.info(f"Conversion process completed. Successful: {successful_conversions}, Failed: {failed_conversions}")

# Main function
if __name__ == "__main__":
    setup_logging()

    ini_file_path = "settings.ini"
    logging.info(f"Checking for INI file at: {ini_file_path}")

    # Kontrol: INI dosyası var mı?
    if not os.path.isfile(ini_file_path):  # Dosyanın varlığı ve bir dosya olup olmadığını kontrol et
        logging.error(f"INI file does not exist at path: {ini_file_path}.")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(ini_file_path)

    input_directory = config.get('Settings', 'input_directory', fallback=None)
    output_directory = config.get('Settings', 'output_directory', fallback=None)

    try:
        dpi = config.getint('Settings', 'dpi', fallback=300)
    except ValueError:
        dpi = 300

    try:
        quality = config.getint('Settings', 'quality', fallback=95)
    except ValueError:
        quality = 95

    try:
        max_width = config.getint('Settings', 'max_width', fallback=1920)  
    except ValueError:
        max_width = 1920      

    try:
        max_height = config.getint('Settings', 'max_height', fallback=1080)
    except ValueError:
        max_height = 1080        

    if not input_directory or not output_directory:
        logging.error("Key values are empty. Please fill them in the INI file.")
        print("Key values are empty. Please fill them in the INI file.")
        sys.exit(1)

    logging.info(f"Input directory: {input_directory}")
    logging.info(f"Output directory: {output_directory}")
    logging.info(f"DPI: {dpi}")
    logging.info(f"Quality: {quality}")
    logging.info(f"Max Width: {max_width}")
    logging.info(f"Max Height: {max_height}")

    if not os.path.isdir(input_directory):
        logging.error(f"Invalid input directory: {input_directory}")
        print("Invalid input directory. Please provide a valid path.")
        sys.exit(1)
    if not os.path.isdir(output_directory):
        logging.error(f"Invalid output directory: {output_directory}")
        print("Invalid output directory. Please provide a valid path.")
        sys.exit(1)

    process_files_in_directory(input_directory, output_directory, dpi, quality, max_width, max_height)
    logging.info("Conversion process completed.")
