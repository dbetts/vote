from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from datetime import datetime
import hashlib

IMPORT_CHOICES = (  
                    ('new', 'New'), 
                    ('progress', 'In Progress'), 
                    ('complete', 'Complete'), 
                    ('failed', 'Failed')
                )


def template_file_location(instance, filename):
    return "templates/%s" % filename

def import_file_location(instance, filename):
    folder = datetime.strftime(datetime.now(), "%B_%Y")
    return "imports/%s/%s" % (folder, filename)


class Log(models.Model):
    content_type = models.ForeignKey(ContentType)
    job = models.ForeignKey('Job')
    remote_pk = models.CharField(max_length=100)
    
    def __unicode__(self):
        
        return "%s - #%s" % (self.job, self.remote_pk)


class Error(models.Model):
    job = models.ForeignKey('Job')
    data = models.TextField(blank=True)
    extra = models.TextField(blank=True)
    message = models.TextField(blank=True)
    
    def __unicode__(self):
        return str(self.id)


class Template(models.Model):
    name = models.CharField(max_length=100)
    content_type = models.ForeignKey(ContentType)
    data = models.FileField('Example Data', upload_to=template_file_location)
    mapping = models.TextField(blank=True, editable=False)
    mapping_through = models.TextField(blank=True, editable=False)
    required = models.TextField(blank=True, editable=False)
    unique = models.TextField(blank=True, editable=False)
    
    class Meta:
        ordering = ['name']
    
    def __unicode__(self):
        return self.name
        
    def create_job(self):
        url = reverse('bulkimport_new_from_template', args=[self.id])
        return '<a href="%s">New %s import</a>' % (url, self.content_type)
        
    create_job.allow_tags = True
    
class Job(models.Model):
    data            = models.FileField(upload_to=import_file_location)
    checksum        = models.CharField(max_length=100, editable=False)
    date            = models.DateTimeField(default=datetime.today(), editable=False)
    content_type    = models.ForeignKey(ContentType)
    status          = models.CharField(max_length=20, choices=IMPORT_CHOICES, editable=False, blank=True)
    mapping         = models.TextField(blank=True, editable=False)
    mapping_through = models.TextField(blank=True, editable=False)
    required        = models.TextField(blank=True, editable=False)
    unique          = models.TextField(blank=True, editable=False)
    template        = models.ForeignKey(Template)
        
    def __unicode__(self):
        return "%s - %s" % (self.content_type, self.date)
    
    def save(self, *args, **kwargs):
        
        if not self.checksum:
            
            checksum = hashlib.md5()
            
            data = self.data.file
            while True:
                d = data.read(1024)
                if len(d) == 0:
                    break
                checksum.update(d)
            
            self.checksum = checksum.hexdigest()
        
        if not self.status:
            self.status = 'new'
            
        super(Job, self).save(*args, **kwargs)
