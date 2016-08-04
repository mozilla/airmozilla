import pycaption

from django import http
from django.shortcuts import get_object_or_404

from airmozilla.closedcaptions.models import ClosedCaptions


class TxtWriter(pycaption.base.BaseWriter):
    def write(self, caption_set):
        lang = caption_set.get_languages()[0]
        captions = caption_set.get_captions(lang)
        output = 'Language: {}\n\n'.format(lang)
        for caption in captions:
            output += '{start} --> {end}\n{text}\n\n'.format(
                start=caption.format_start(),
                end=caption.format_end(),
                text=caption.get_text().replace('\n', ' '),
            )
        return output


SUPPORTED_WRITERS = {
    'dfxp': pycaption.DFXPWriter,
    'ttml': pycaption.DFXPWriter,
    'sami': pycaption.SAMIWriter,
    'srt': pycaption.SRTWriter,
    'scc': pycaption.SCCWriter,
    'webvtt': pycaption.WebVTTWriter,
    'txt': TxtWriter,
}

FILE_EXTENSIONS = {
    'dfxp': 'dfxp.xml',
    'dfxp': 'dfxp',
    'ttml': 'dfxp',
    'sami': 'sami',
    'srt': 'srt',
    'scc': 'scc',
    'webvtt': 'vtt',
    'txt': 'txt',
}

CONTENT_TYPES = {
    'txt': 'text/plain',
    'sami': ' text/xml',
    'dfxp': 'application/ttml+xml; charset=utf-8',
    'vtt': 'text/vtt',
}


def download(request, filename_hash, id, slug, extension):
    closedcaptions = get_object_or_404(
        ClosedCaptions,
        id=id,
        event__slug__iexact=slug,
    )
    if extension not in FILE_EXTENSIONS.values():
        raise http.Http404('Unrecognized extension')
    if closedcaptions.filename_hash != filename_hash:
        raise http.Http404('Unrecognized hash')

    for key, ext in FILE_EXTENSIONS.items():
        if ext == extension:
            output_writer = SUPPORTED_WRITERS[key]
    content = closedcaptions.file.read()
    if not (
        closedcaptions.file.name.lower().endswith('.ttml') or
        closedcaptions.file.name.lower().endswith('.dfxp')
    ):
        content = content.decode('utf-8')

    reader = pycaption.detect_format(content)
    assert reader
    converter = pycaption.CaptionConverter()
    converter.read(content, reader())
    response = http.HttpResponse()
    response['Content-Type'] = CONTENT_TYPES.get(extension, 'text/plain')
    response.write(converter.write(output_writer()))
    return response
