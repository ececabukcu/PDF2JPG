# PDF2JPG

PDF2JPG is a Python tool designed to convert PDF files into JPG images. It supports batch conversion and provides detailed logging of each step in the process.

## Description

This project is a Python program that converts PDF files in a specified directory to JPEG format. The program first checks for an INI configuration file to retrieve settings for the input directory, output directory, DPI (dots per inch), and quality. If the INI file does not exist, an example INI file is created. The program converts the PDF files to JPEG format at the specified DPI and quality settings, and saves the converted files to the specified output directory. Upon completion, the program renames the original PDF files to _processed.pdf, so that the same file is not processed again. This ensures that the file is not seen again.

## Features

- Convert PDF to JPG
- Batch conversion of multiple PDF files
- Detailed logging of each step
- Error handling and logging

## Installation

### Prerequisites

Make sure you have Python 3.x installed on your machine.
To install all dependencies listed in a “requirements.txt” file, use the following pip command:
pip install -r requirements.txt

### Clone the Repository

```sh
git clone https://github.com/ececabukcu/PDF2JPG.git
cd PDF2JPG

