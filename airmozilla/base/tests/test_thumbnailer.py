import os

from django.conf import settings
from django.test import TestCase

from sorl.thumbnail.images import ImageFile
from sorl.thumbnail import default


from airmozilla.base.thumbnailer import OptimizingThumbnailBackend


fake_pngquant_path = os.path.join(
    os.path.dirname(__file__),
    'fake-pngquant.py'
)
sample_image_path = os.path.join(
    os.path.dirname(__file__),
    'joyofcoding.png'
)


class TestOptimizingThumbnailBackend(TestCase):

    def test_create_thumbnail_with_pngquant_location(self):
        thumbnail = ImageFile(
            os.path.basename(sample_image_path),
            default.storage
        )
        size_before = os.stat(sample_image_path).st_size

        with self.settings(PNGQUANT_LOCATION=fake_pngquant_path):
            with open(sample_image_path, 'rb') as source:
                source_image = default.engine.get_image(source)
            backend = OptimizingThumbnailBackend()
            backend._create_thumbnail(
                source_image,
                '100x100', OptimizingThumbnailBackend.default_options,
                thumbnail
            )
        destination = os.path.join(
            settings.MEDIA_ROOT,
            os.path.basename(sample_image_path)
        )
        size_after = os.stat(destination).st_size
        self.assertTrue(size_after < size_before)
