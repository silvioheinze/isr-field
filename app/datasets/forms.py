from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import Group, User
from django.utils.translation import gettext_lazy as _
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
        # Set default field_type to 'choice' for new fields
        if not self.instance.pk:
            self.fields['field_type'].initial = 'choice'
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
        """Normalize choices for choice fields"""
        choices = self.cleaned_data.get('choices', '')

        normalized_choices = []
        if isinstance(choices, str):
            normalized_choices = [choice.strip() for choice in choices.split(',') if choice.strip()]
        elif isinstance(choices, (list, tuple)):
            normalized_choices = [str(choice).strip() for choice in choices if str(choice).strip()]
        
        return ', '.join(normalized_choices) if normalized_choices else ''

    def clean(self):
        cleaned_data = super().clean()
        field_type = cleaned_data.get('field_type')
        choices = cleaned_data.get('choices', '')
        typology = cleaned_data.get('typology')
        
        # Validate that choice fields have either manual choices or a typology
        if field_type == 'choice':
            # Check if choices are provided (after normalization)
            has_choices = bool(choices and choices.strip())
            # Check if typology is provided
            has_typology = bool(typology)
            
            if not (has_choices or has_typology):
                self.add_error('choices', 'Provide manual choices or select a typology for choice fields.')
        
        # Handle typology category
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


class EmailAuthenticationForm(AuthenticationForm):
    """Authentication form that uses email + password credentials."""

    username = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={
            'autofocus': True,
            'class': 'form-control',
            'placeholder': 'user@example.com'
        })
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": _("Please enter a correct email address and password. Both fields may be case-sensitive."),
        "multiple_accounts": _("Multiple accounts are associated with this email address. Contact an administrator."),
    }

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if email and password:
            users = User.objects.filter(email__iexact=email)

            if not users.exists():
                raise forms.ValidationError(
                    self.error_messages["invalid_login"],
                    code="invalid_login",
                )

            if users.count() > 1:
                raise forms.ValidationError(
                    self.error_messages["multiple_accounts"],
                    code="multiple_accounts",
                )

            user = users.first()
            self.user_cache = authenticate(
                self.request,
                username=user.get_username(),
                password=password,
            )

            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages["invalid_login"],
                    code="invalid_login",
                )

            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'user@example.com'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_('A user with that email address already exists.'))
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        if commit:
            user.save()
        return user


class TransferOwnershipForm(forms.Form):
    """Form for transferring dataset ownership"""
    new_owner = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Select the user who will become the new owner of this dataset."
    )

    def __init__(self, *args, **kwargs):
        current_owner = kwargs.pop('current_owner', None)
        super().__init__(*args, **kwargs)
        # Exclude the current owner from the list
        queryset = User.objects.filter(is_active=True).order_by('username')
        if current_owner:
            queryset = queryset.exclude(id=current_owner.id)
        self.fields['new_owner'].queryset = queryset
