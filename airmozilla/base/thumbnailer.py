import logging
import time
import subprocess
import os

from django.conf import settings

from sorl.thumbnail.base import ThumbnailBackend


logger = logging.getLogger('airmozilla.base.thumbnailer')


class OptimizingThumbnailBackend(ThumbnailBackend):

    def _create_thumbnail(
        self,
        source_image,
        geometry_string, options,
        thumbnail
    ):
        """override so we have an opportunity to first optimize the
        resulting thumbnail before it gets saved."""
        super(OptimizingThumbnailBackend, self)._create_thumbnail(
            source_image,
            geometry_string, options,
            thumbnail
        )
        image_path = os.path.join(settings.MEDIA_ROOT, thumbnail.name)
        if os.path.isfile(image_path) and image_path.endswith('.png'):
            self._optimize_png(image_path)

    def _optimize_png(self, path):
        binary_location = getattr(
            settings,
            'PNGQUANT_LOCATION',
            'pngquant'
        )
        if not binary_location:
            # it's probably been deliberately disabled
            return
        tmp_path = path.replace('.png', '.tmp.png')
        size_before = os.stat(path).st_size
        time_before = time.time()
        command = [
            binary_location,
            '-o', tmp_path,
            '--skip-if-larger',
            '--',
            path,
        ]
        out, err = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        ).communicate()
        # Because we use --skip-if-larger, when you resize an already
        # small PNG the resulting one might not be any smaller so you
        # can't guarantee that the new file was created.
        if not os.path.isfile(tmp_path):
            return
        os.rename(tmp_path, path)
        size_after = os.stat(path).st_size
        time_after = time.time()
        logger.info(
            'Reduced %s from %d to %d (took %.4fs)' % (
                os.path.basename(path),
                size_before,
                size_after,
                time_after - time_before
            )
        )
