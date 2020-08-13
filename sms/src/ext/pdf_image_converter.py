import os.path
import pdf2image

# DECLARE CONSTANTS
DPI = 200
OUTPUT_FOLDER = None
FIRST_PAGE = None
LAST_PAGE = None
FORMAT = 'png'
THREAD_COUNT = 1
USERPWD = None
USE_CROPBOX = False
STRICT = False


def pdftoimage(pdf_path,
               dpi=DPI,
               output_folder=OUTPUT_FOLDER,
               first_page=FIRST_PAGE,
               last_page=LAST_PAGE,
               fmt=FORMAT,
               thread_count=THREAD_COUNT,
               userpw=USERPWD,
               use_cropbox=USE_CROPBOX,
               strict=STRICT):
    # This method reads a pdf and converts it into a sequence of images
    # PDF_PATH sets the path to the PDF file
    # dpi parameter assists in adjusting the resolution of the image
    # output_folder parameter sets the path to the folder to which the PIL images can be stored (optional)
    # first_page parameter allows you to set a first page to be processed by pdftoppm
    # last_page parameter allows you to set a last page to be processed by pdftoppm
    # fmt parameter allows to set the format of pdftoppm conversion (PpmImageFile, TIFF)
    # thread_count parameter allows you to set how many thread will be used for conversion.
    # userpw parameter allows you to set a password to unlock the converted PDF
    # use_cropbox parameter allows you to use the crop box instead of the media box when converting
    # strict parameter allows you to catch pdftoppm syntax error with a custom type PDFSyntaxError

    base_path = os.path.split(pdf_path)[0]
    file_name = os.path.split(pdf_path)[1][:-4]

    # start_time = time.time()
    pil_images = pdf2image.convert_from_path(pdf_path,
                                             dpi=DPI,
                                             output_folder=OUTPUT_FOLDER,
                                             first_page=FIRST_PAGE,
                                             last_page=LAST_PAGE,
                                             fmt=FORMAT,
                                             thread_count=THREAD_COUNT,
                                             userpw=USERPWD,
                                             use_cropbox=USE_CROPBOX,
                                             strict=STRICT)

    # This part helps in converting the images in PIL Image file format to the required image format
    if len(pil_images) > 1:
        index = 1
        for image in pil_images:
            image.save(os.path.join(base_path, file_name + "_" + str(index) + "." + FORMAT))
            index += 1
    else:
        pil_images[0].save(os.path.join(base_path, file_name + "." + FORMAT))


if __name__ == "__main__":
    pdftoimage(pdf_path=input('Enter the pdf file path...'))
