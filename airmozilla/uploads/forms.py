from airmozilla.base.forms import BaseModelForm
from airmozilla.uploads.models import Upload


class SaveForm(BaseModelForm):

    class Meta:
        model = Upload
        fields = ('url', 'upload_time')
