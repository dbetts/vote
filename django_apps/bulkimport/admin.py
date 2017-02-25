from django.contrib import admin
from django_apps.bulkimport.models import Job, Template
from django_apps.bulkimport.forms import TemplateForm, JobForm

class JobAdmin(admin.ModelAdmin):
    list_display = ('date', 'content_type', 'status')
    list_filter = ('status',)
    form = JobForm

class TemplateAdmin(admin.ModelAdmin):
    list_display    = ('name', 'create_job')
    form = TemplateForm
    
admin.site.register(Job, JobAdmin)
admin.site.register(Template, TemplateAdmin)