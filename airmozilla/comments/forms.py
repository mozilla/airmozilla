from django import forms

from airmozilla.base.forms import BaseForm
from airmozilla.comments.models import Comment


class CommentForm(BaseForm):

    name = forms.CharField(required=False)
    comment = forms.CharField(widget=forms.Textarea)
    reply_to = forms.IntegerField(required=False)

    def clean_reply_to(self):
        value = self.cleaned_data['reply_to']
        if value:
            try:
                value = Comment.objects.get(pk=value)
            except Comment.DoesNotExist:
                raise forms.ValidationError('Invalid reply_to')
        return value
