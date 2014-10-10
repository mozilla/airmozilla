import os


def filename_to_notes(filename):
    filename, _ = os.path.splitext(filename)
    return filename.replace('_', ' ')
