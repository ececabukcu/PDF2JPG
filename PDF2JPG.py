import sys
import fitz  # PyMuPDF to work with PDF files
from PIL import Image  # For image processing with the Pillow library
import io  # For input and output operations
import os  # For interacting with the operating system (file and directory management)
import logging  # For logging operations
from concurrent.futures import ThreadPoolExecutor  # To enable parallel processing
import configparser  # For reading and writing INI files

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("pdf_to_jpg.log"),
    logging.StreamHandler()
])

# Function to convert PDF to JPG
def pdf_to_jpg(pdf_path, output_dir, relative_dir, dpi=300, quality=95):  # DPI and quality parameters added
    logging.info(f"Starting conversion for: {pdf_path}")
    try:
        # Open the PDF document
        pdf_document = fitz.open(pdf_path)
        logging.info(f"PDF file opened successfully: {pdf_path}")
    except Exception as e:
        logging.error(f"Failed to open PDF file: {pdf_path}, Error: {e}")
        return False
    
    #Stores the JPEG image in the same directory structure as relative_dir in output_directory
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    pdf_output_dir = os.path.join(output_dir, relative_dir, pdf_name) #relative_dir is combined with output_directory to create the folder structure where JPEG files will be saved

    # Create the output directory if it does not exist
    if not os.path.exists(pdf_output_dir):
        os.makedirs(pdf_output_dir)
        logging.info(f"Output directory created: {pdf_output_dir}")

    # Iterate over each page in the PDF
    for page_number in range(len(pdf_document)):
        try:
            # Load the page and create a pixmap
            page = pdf_document.load_page(page_number)
            pix = page.get_pixmap(dpi=dpi)  # Creating pixmap using the DPI parameter
            img_data = io.BytesIO(pix.tobytes(output='jpeg'))
            image = Image.open(img_data)
            jpeg_path = os.path.join(pdf_output_dir, f'{pdf_name}_page_{page_number + 1}.jpg')
            image.save(jpeg_path, 'JPEG', quality=quality)  # Quality parameter added
            logging.info(f'Page {page_number + 1} of {pdf_path} saved as {jpeg_path}')
        except Exception as e:
            logging.error(f"Failed to convert page {page_number + 1} of {pdf_path}, Error: {e}")
            pdf_document.close()
            return False
    
    pdf_document.close()
    
    # Rename the original PDF file to avoid reprocessing
    processed_pdf_path = pdf_path.replace('.pdf', '_processed.pdf')
    try:
        os.rename(pdf_path, processed_pdf_path)
        logging.info(f"Renamed PDF file to: {processed_pdf_path}")
    except Exception as e:
        logging.error(f"Failed to rename PDF file: {pdf_path}, Error: {e}")
        return False

    return True

# Function to process all PDFs in a directory
def process_pdfs_in_directory(input_dir, output_dir, dpi=300, quality=95):
    # Check if input directory is valid
    if not os.path.isdir(input_dir):
        logging.error(f"Invalid input directory: {input_dir}")
        print("Invalid input directory. Please provide a valid path.")
        return

    # Check if output directory is valid
    if not os.path.isdir(output_dir):
        logging.error(f"Invalid output directory: {output_dir}")
        print("Invalid output directory. Please provide a valid path.")
        return

    pdf_files = []
    # os.walk through the input directory and find all PDF files
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".pdf") and not file.endswith("_processed.pdf"):
                relative_dir = os.path.relpath(root, input_dir) #Calculates the difference between the file path and the input_directory
                pdf_files.append((os.path.join(root, file), relative_dir))
    
    total_files = len(pdf_files)
    logging.info(f"Found {total_files} PDF files to convert.")
    successful_conversions = 0
    failed_conversions = 0

    # Using ThreadPoolExecutor to process multiple PDFs concurrently
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(pdf_to_jpg, pdf_path, output_dir, relative_dir, dpi, quality): pdf_path for pdf_path, relative_dir in pdf_files}
        for future in futures:
            try:
                result = future.result()  # Get the result of the conversion
                if result:
                    successful_conversions += 1
                else:
                    failed_conversions += 1
                    logging.error(f"Conversion failed for: {futures[future]}")
            except Exception as e:
                failed_conversions += 1
                logging.error(f"Unexpected error occurred for: {futures[future]}, Error: {e}")

    logging.info(f"Conversion process completed. Successful: {successful_conversions}, Failed: {failed_conversions}")
    print(f"Conversion process completed. Successful: {successful_conversions}, Failed: {failed_conversions}")

# Main function
if __name__ == "__main__":
    ini_file_path = "settings.ini"  # Specify the path to the INI file
    logging.info(f"Checking for INI file at: {ini_file_path}")
    
    if not os.path.exists(ini_file_path):
        logging.error(f"INI file does not exist at path: {ini_file_path}. Creating example INI file.")
        create_example_ini_file(ini_file_path)
        print("The INI file does not exist. An example INI file has been created: settings.ini")
        sys.exit(1)
    
    config = configparser.ConfigParser()
    config.read(ini_file_path)
    
    input_directory = config.get('Settings', 'input_directory', fallback=None)
    output_directory = config.get('Settings', 'output_directory', fallback=None)
    
    # Use default values if there's an error retrieving DPI and quality values
    try:
        dpi = config.getint('Settings', 'dpi', fallback=300)
    except ValueError:
        dpi = 300  # Default DPI value
    
    try:
        quality = config.getint('Settings', 'quality', fallback=95)
    except ValueError:
        quality = 95  # Default quality value
    
    if not input_directory or not output_directory:
        logging.error("Key values are empty. Please fill them in the INI file.")
        print("Key values are empty. Please fill them in the INI file.")
        sys.exit(1)
    
    logging.info(f"Input directory: {input_directory}")
    logging.info(f"Output directory: {output_directory}")
    logging.info(f"DPI: {dpi}")
    logging.info(f"Quality: {quality}")
    
    # Validate directories
    if not os.path.isdir(input_directory):
        logging.error(f"Invalid input directory: {input_directory}")
        print("Invalid input directory. Please provide a valid path.")
        sys.exit(1)
    if not os.path.isdir(output_directory):
        logging.error(f"Invalid output directory: {output_directory}")
        print("Invalid output directory. Please provide a valid path.")
        sys.exit(1)
    
    logging.info("Starting PDF to JPG conversion process.")
    process_pdfs_in_directory(input_directory, output_directory, dpi, quality)
    logging.info("PDF to JPG conversion process completed.")
