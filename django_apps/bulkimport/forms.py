from django import forms
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django_apps.bulkimport.models import Template, Job

class TemplateForm(forms.ModelForm):
    content_type_name = settings.CONTENT_TYPE_MODELS
    content_type = forms.ModelChoiceField(ContentType.objects.filter(model__in=content_type_name))
    
    class Meta:
        model = Template
        fields = '__all__'

class JobForm(forms.ModelForm):
    content_type_name = settings.CONTENT_TYPE_MODELS
    content_type = forms.ModelChoiceField(ContentType.objects.filter(model__in=content_type_name))
        
    class Meta:
        model = Job
        fields = '__all__'
    
class JobFormTemplate(forms.ModelForm):
    
    class Meta:
        exclude = ('content_type','template')
        model = Job