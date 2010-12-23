import sys, os, shutil
import Image, ImageEnhance

def is_landscape(image):
    width, height = image.size 
    return width/height > 0

def process_image(source, destination):
    constant_width = 744
    try:

        image = Image.open(source, "r").convert("L")
        if is_landscape(image):
            image = image.transpose(Image.ROTATE_90)

        image = ImageEnhance.Sharpness(image).enhance(2)
        image.resize(fill_width(constant_width, *image.size), Image.BICUBIC).save(destination)
        return True
    except:
        print "invalid file, removing", source
        #os.remove(source)
        return False

def check_file(file):
    return os.access(file, os.F_OK)

def make_dir(dir):
    if False == os.access(dir, os.F_OK):
        try:
            os.makedirs(dir, 0777)
        except OSError:
            pass

def get_filelist(path):
    return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

def get_chapterlist(path):
    return [int(f) for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]

def fill_width(maxwidth, width, height):
    ratio = float(maxwidth)/float(width)
    return (int(width * ratio), int(height * ratio))

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4

def create_pdf(image_paths, output_filepath):
    image_paths.sort()
    pdf = Canvas(output_filepath)
    pdf.setAuthor("MangaCreator")
    for image_path in image_paths:
        image = Image.open(image_path)
        width, height = A4
        pdf.drawInlineImage(image, x=0, y=0, width=width, height=height)
        pdf.showPage()
    pdf.save()


input_path = "mangas"
cache_path = "processing"
output_path = "processed"
make_dir(output_path)

mangas = [
        "psyren",
        "historys-strongest-disciple-kenichi",
        "d-gray-man",
        "one-piece",
        ]
chapters = [1]


for manga in mangas:
    for chapter in get_chapterlist(os.path.join(input_path, manga)):
        input_filepath = "%s/%s/%d" % (input_path, manga, chapter)
        processing_filepath = "%s/%s/%d" % (cache_path, manga, chapter)
        document_filepath = "%s/%s-chapter-%d.pdf" % (output_path, manga, chapter)
        if check_file(document_filepath):
            print "skipped", document_filepath
            continue

        make_dir(processing_filepath)

        print "Processing %s chapter %d" % (manga, chapter)
        image_paths = []
        valid = True
        for filename in get_filelist(input_filepath):
            imagename = ".".join(filename.split(".")[:-1]) + ".jpg"
            output_filename = os.path.join(processing_filepath, imagename)

            if not check_file(document_filepath):
                if not process_image(os.path.join(input_filepath, filename), output_filename):
                    valid = False

            if valid:
                image_paths.append(output_filename)

        if valid:
            create_pdf(image_paths, document_filepath)
            print "Done"
        else:
            print "Invalid"
