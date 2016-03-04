import json

from django.db import models
from django.forms.fields import Field
from django.forms.utils import ValidationError

# modified version of JSONField and JSONFormField: bradjasper/django-jsonfield


class EnvironmentFormField(Field):
    def clean(self, value):
        if not value and not self.required:
            return None
        built = {}
        value = super(EnvironmentFormField, self).clean(value)
        kv_pairs = [v.strip() for v in value.split('\n') if v.strip()]
        for kv in kv_pairs:
            split = kv.split('=', 1)
            if len(split) != 2:
                raise ValidationError('Please enter valid key-value pairs.')
            built[split[0].strip()] = split[1].strip()
        return built


class EnvironmentField(models.TextField):
    """Generic textfield that serializes/unserializes JSON objects"""

    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase

    form_class = EnvironmentFormField

    def to_python(self, value):
        """Convert string value to JSON"""
        if isinstance(value, basestring):
            try:
                return json.loads(value)
            except ValueError:
                pass
        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        """Convert JSON object to a string"""
        if isinstance(value, basestring):
            return value
        return json.dumps(value)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)

    def value_from_object(self, obj):
        """Convert object to k=v\nk=v\n... input pairs."""
        obj_value = super(EnvironmentField, self).value_from_object(obj)
        if obj_value is None:
            return None
        if isinstance(obj_value, basestring):
            if not obj_value:
                return ''
            obj_value = json.loads(obj_value)
        input_pairs = []
        for k, v in obj_value.iteritems():
            input_pairs.append('%s=%s' % (k, v))
        return '\n'.join(input_pairs)

    def formfield(self, **kwargs):
        # Bypass the super of this class and skip directly to the
        # models.TextField's super.
        return super(models.TextField, self).formfield(
            form_class=EnvironmentFormField, **kwargs)

# add_introspection_rules([], ["^airmozilla\.main\.fields\.EnvironmentField"])
