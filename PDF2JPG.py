import sys  # Python sistem spesifik parametreleri ve fonksiyonları için
import fitz  # PyMuPDF #pdf dosyalarını işlemek için
from PIL import Image  # Pillow kütüphanesi ile görüntü işleme
import io  # Girdi ve çıktı işlemleri için
import os  # İşletim sistemi ile ilgili işlemler (dosya ve dizin yönetimi gibi) için
import logging  # Loglama işlemleri için
from concurrent.futures import ThreadPoolExecutor  # Paralel işlemeyi sağlamak için
import configparser  # INI dosyasını okumak ve yazmak için


# Log yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("pdf_to_jpg.log"),
    logging.StreamHandler()
])

def pdf_to_jpg(pdf_path, output_dir, dpi=300, quality=95):  # DPI ve kalite parametreleri eklendi
    logging.info(f"Starting conversion for: {pdf_path}")
    try:
        pdf_document = fitz.open(pdf_path)
        logging.info(f"PDF file opened successfully: {pdf_path}")
    except Exception as e:
        logging.error(f"Failed to open PDF file: {pdf_path}, Error: {e}")
        return False
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logging.info(f"Output directory created: {output_dir}")

    # pdf to jpg
    for page_number in range(len(pdf_document)):
        try:
            page = pdf_document.load_page(page_number)
            pix = page.get_pixmap(dpi=dpi)  # DPI parametresi kullanılarak pixmap oluşturma
            img_data = io.BytesIO(pix.tobytes(output='jpeg'))
            image = Image.open(img_data)
            jpeg_path = os.path.join(output_dir, f'{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{page_number + 1}.jpg')
            image.save(jpeg_path, 'JPEG', quality=quality)  # Kalite parametresi eklendi
            logging.info(f'Page {page_number + 1} of {pdf_path} saved as {jpeg_path}')
        except Exception as e:
            logging.error(f"Failed to convert page {page_number + 1} of {pdf_path}, Error: {e}")
            pdf_document.close()
            return False
    
    pdf_document.close()
    
    # dönüşen pdf dosyalarının ismi değişiyor tekrar dönüştürmemek için
    processed_pdf_path = pdf_path.replace('.pdf', '_processed.pdf')
    try:
        os.rename(pdf_path, processed_pdf_path)
        logging.info(f"Renamed PDF file to: {processed_pdf_path}")
    except Exception as e:
        logging.error(f"Failed to rename PDF file: {pdf_path}, Error: {e}")
        return False

    return True

def process_pdfs_in_directory(input_dir, output_dir, dpi=300, quality=95):  # DPI ve kalite parametreleri eklendi
    if not os.path.isdir(input_dir):
        logging.error(f"Invalid input directory: {input_dir}")
        print("Invalid input directory. Please provide a valid path.")
        return

    if not os.path.isdir(output_dir):
        logging.error(f"Invalid output directory: {output_dir}")
        print("Invalid output directory. Please provide a valid path.")
        return

    pdf_files = [f for f in os.listdir(input_dir) if f.endswith(".pdf") and not f.endswith("_processed.pdf")]
    total_files = len(pdf_files)
    logging.info(f"Found {total_files} PDF files to convert.")
    successful_conversions = 0
    failed_conversions = 0

    # thread kullanarak zamandan ve performanstan kazanıyoruz 
    # thread sayesinde hata oluşan PDF dosyası diğer dosyaların dönüşümüne engel olmaz. Her pdfe ayrı bir thread atayarak paralel dönüşüm sağlarız
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(pdf_to_jpg, os.path.join(input_dir, filename), output_dir, dpi, quality): filename for filename in pdf_files}
        for future in futures:
            try:
                result = future.result()  # her treadin sonucunu temsil eder bu sonuçlara ileride ulaşmayı sağlar
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

def create_example_ini_file(ini_file_path):
    example_ini_content = """[Settings]
input_directory = 
output_directory = 
dpi = 300
quality = 95
"""
    with open(ini_file_path, "w") as example_file:
        example_file.write(example_ini_content)
    logging.info(f"Created example INI file at {ini_file_path}")

def update_ini_file(ini_file_path, input_directory, output_directory, dpi, quality):
    config = configparser.ConfigParser()
    config.read(ini_file_path)
    
    if 'Settings' not in config:
        config.add_section('Settings')
    
    config.set('Settings', 'input_directory', input_directory)
    config.set('Settings', 'output_directory', output_directory)
    config.set('Settings', 'dpi', str(dpi))
    config.set('Settings', 'quality', str(quality))
    
    with open(ini_file_path, 'w') as configfile:
        config.write(configfile)
    logging.info(f"Updated INI file at {ini_file_path} with input and output directories, dpi, and quality.")

if __name__ == "__main__":
    ini_file_path = "settings.ini"  # INI dosyasının yolunu belirt
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
    
    # DPI ve kalite değerlerini alırken hata oluşursa varsayılan değerleri kullanın
    try:
        dpi = config.getint('Settings', 'dpi', fallback=300)
    except ValueError:
        dpi = 300  # Varsayılan DPI değeri
    
    try:
        quality = config.getint('Settings', 'quality', fallback=95)
    except ValueError:
        quality = 95  # Varsayılan kalite değeri
    
    if not input_directory or not output_directory:
        logging.error("Key values are empty. Please fill them in the INI file.")
        print("Key values are empty. Please fill them in the INI file.")
        sys.exit(1)
    
    logging.info(f"Input directory: {input_directory}")
    logging.info(f"Output directory: {output_directory}")
    logging.info(f"DPI: {dpi}")
    logging.info(f"Quality: {quality}")
    
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
