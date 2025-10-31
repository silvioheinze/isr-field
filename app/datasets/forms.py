from django import forms
from django.contrib.auth.models import Group
from .models import DatasetFieldConfig, DatasetField, Typology


class DatasetFieldConfigForm(forms.ModelForm):
    """Form for configuring dataset field settings"""
    
    class Meta:
        model = DatasetFieldConfig
        fields = [
            'usage_code1_label', 'usage_code1_enabled',
            'usage_code2_label', 'usage_code2_enabled', 
            'usage_code3_label', 'usage_code3_enabled',
            'cat_inno_label', 'cat_inno_enabled',
            'cat_wert_label', 'cat_wert_enabled',
            'cat_fili_label', 'cat_fili_enabled',
            'year_label', 'year_enabled',
            'name_label', 'name_enabled'
        ]
        widgets = {
            'usage_code1_label': forms.TextInput(attrs={'class': 'form-control'}),
            'usage_code1_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'usage_code2_label': forms.TextInput(attrs={'class': 'form-control'}),
            'usage_code2_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'usage_code3_label': forms.TextInput(attrs={'class': 'form-control'}),
            'usage_code3_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cat_inno_label': forms.TextInput(attrs={'class': 'form-control'}),
            'cat_inno_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cat_wert_label': forms.TextInput(attrs={'class': 'form-control'}),
            'cat_wert_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cat_fili_label': forms.TextInput(attrs={'class': 'form-control'}),
            'cat_fili_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'year_label': forms.TextInput(attrs={'class': 'form-control'}),
            'year_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'name_label': forms.TextInput(attrs={'class': 'form-control'}),
            'name_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DatasetFieldForm(forms.ModelForm):
    """Form for creating and editing dataset fields"""
    
    class Meta:
        model = DatasetField
        fields = ['field_name', 'label', 'field_type', 'required', 'enabled', 'help_text', 'choices', 'order', 'is_coordinate_field', 'is_id_field', 'is_address_field', 'typology', 'typology_category']
        widgets = {
            'field_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'field_name'}),
            'label': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Display Label'}),
            'field_type': forms.Select(attrs={'class': 'form-select'}),
            'required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'help_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'choices': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Option 1, Option 2, Option 3'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_coordinate_field': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_id_field': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_address_field': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'typology': forms.Select(attrs={'class': 'form-select'}),
            'typology_category': forms.Select(attrs={'class': 'form-select'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate typology choices
        self.fields['typology'].queryset = Typology.objects.all().order_by('name')
        self.fields['typology'].empty_label = "No typology selected"
        self.fields['typology_category'].required = False
        self.fields['typology_category'].choices = [('', 'All categories')]

        typology_id = None
        if self.data.get('typology'):
            typology_id = self.data.get('typology')
        elif self.initial.get('typology'):
            typology_id = self.initial.get('typology')
        elif getattr(self.instance, 'typology_id', None):
            typology_id = self.instance.typology_id

        if typology_id:
            try:
                typology = Typology.objects.get(pk=typology_id)
                categories = (
                    typology.entries.order_by('category')
                    .values_list('category', flat=True)
                    .distinct()
                )
                self.fields['typology_category'].choices += [
                    (category, category)
                    for category in categories
                    if category
                ]
            except Typology.DoesNotExist:
                pass
    
    def clean_field_name(self):
        """Validate field name"""
        field_name = self.cleaned_data.get('field_name')
        if field_name:
            # Convert to lowercase and replace spaces with underscores
            field_name = field_name.lower().replace(' ', '_')
            # Remove any non-alphanumeric characters except underscores
            import re
            field_name = re.sub(r'[^a-z0-9_]', '', field_name)
            # Ensure it starts with a letter
            if field_name and not field_name[0].isalpha():
                field_name = 'field_' + field_name
        return field_name
    
    def clean_choices(self):
        """Validate choices for choice fields"""
        choices = self.cleaned_data.get('choices')
        field_type = self.cleaned_data.get('field_type')
        typology = self.cleaned_data.get('typology')

        normalized_choices = []
        if isinstance(choices, str):
            normalized_choices = [choice.strip() for choice in choices.split(',') if choice.strip()]
        elif isinstance(choices, (list, tuple)):
            normalized_choices = [str(choice).strip() for choice in choices if str(choice).strip()]
        
        if field_type == 'choice' and not (normalized_choices or typology):
            raise forms.ValidationError("Provide manual choices or select a typology for choice fields.")
        
        return ', '.join(normalized_choices) if normalized_choices else ''

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('typology'):
            cleaned_data['typology_category'] = ''
        else:
            typology_category = cleaned_data.get('typology_category')
            available_categories = [choice[0] for choice in self.fields['typology_category'].choices if choice[0]]
            if typology_category and typology_category not in available_categories:
                self.add_error('typology_category', 'Selected category is not available for this typology.')
        return cleaned_data


class GroupForm(forms.ModelForm):
    """Form for creating and editing groups"""
    
    class Meta:
        model = Group
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'})
        }
