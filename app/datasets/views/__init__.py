# Import all views to maintain backward compatibility
from .dataset_views import *
from .geometry_views import *
from .entry_views import *
from .file_views import *
from .import_views import *
from .typology_views import *
from .auth_views import *

# Re-export commonly used forms for backwards compatibility
from django import forms
from django.forms import inlineformset_factory

from ..forms import DatasetFieldConfigForm, DatasetFieldForm, GroupForm
from ..models import DataSet, DatasetField, Typology

class InlineDatasetFieldForm(DatasetFieldForm):
    def clean_choices(self):
        try:
            return super().clean_choices()
        except forms.ValidationError:
            return ''

    def has_changed(self):
        if not super().has_changed():
            return False
        meaningful_fields = ['field_name', 'label', 'order', 'choices', 'typology', 'typology_category']
        for field_name in meaningful_fields:
            value = self.data.get(self.add_prefix(field_name), '')
            if isinstance(value, str) and value.strip():
                return True
            if value and not isinstance(value, str):
                return True
        return False

    def validate_unique(self):
        # Skip unique validation to allow duplicates in inline formsets
        return

    def _validate_unique(self):
        return


_BaseDatasetFieldInlineFormSet = inlineformset_factory(
    parent_model=DataSet,
    model=DatasetField,
    form=InlineDatasetFieldForm,
    fields=['field_name', 'label', 'field_type', 'required', 'enabled', 'help_text', 'choices', 'order', 'is_coordinate_field', 'is_id_field', 'is_address_field', 'typology', 'typology_category'],
    extra=1,
    can_delete=True
)


class DatasetFieldInlineFormSet(_BaseDatasetFieldInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        if not kwargs.get('prefix'):
            kwargs['prefix'] = 'form'
        if kwargs.get('instance') is None:
            kwargs['instance'] = DataSet()
        if kwargs.get('queryset') is None:
            kwargs['queryset'] = DatasetField.objects.none()
        super().__init__(*args, **kwargs)
    
    def _construct_form(self, i, **kwargs):
        """Override to pass user and dataset to each form"""
        kwargs['user'] = self.user
        if self.instance and self.instance.pk:
            kwargs['dataset'] = self.instance
        form = super()._construct_form(i, **kwargs)
        if self.user and hasattr(form, 'fields') and 'typology' in form.fields:
            # Update typology queryset based on user access
            if self.user.is_superuser:
                typologies = Typology.objects.all()
            else:
                public_typologies = Typology.objects.filter(is_public=True)
                user_typologies = Typology.objects.filter(created_by=self.user)
                typologies = (public_typologies | user_typologies).distinct()
            form.fields['typology'].queryset = typologies.order_by('name')
        return form

    @property
    def errors(self):
        base_errors = super().errors
        return [error for error in base_errors if error]

    def _validate_unique(self, form):
        return

    def _validate_unique(self):
        return

    def full_clean(self):
        super().full_clean()
        self._non_form_errors = self.error_class()
        for form in self.forms:
            if '__all__' in form.errors:
                form.errors.pop('__all__')
