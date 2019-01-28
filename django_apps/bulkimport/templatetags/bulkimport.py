from django import template
from django.template import Variable

import csv

try:
    import json
except ImportError:
    from django.utils import simplejson as json

register = template.Library()

@register.tag
def fetch_column_headers_from(parser, token):
    try:
        tag_name, data, as_text, output_name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("usage: {% fetch_column_headers_from data as 'output' %}")
    return ColumnHeaders(data, output_name)

class ColumnHeaders(template.Node):
    
    def __init__(self, data, output_name):
        self.data = Variable(data)        
        self.output_name = Variable(output_name)        
    
    def render(self, context):
        data = self.data.resolve(context)
        output_name = self.output_name.resolve(context)
        
        lines = csv.reader(data.readlines(), quoting=csv.QUOTE_ALL)
        
        try:
            context[output_name] = lines.next()
        except Exception:
            return 'Your CSV file is not formatted correctly'
        
        return ''

@register.tag
def fetch_column_headers_from_model(parser, token):
    try:
        tag_name, model, as_text, output_name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("usage: {% fetch_column_headers_from_model model as 'output' %}")
    return ModelColumnHeaders(model, output_name)

class ModelColumnHeaders(template.Node):
    
    def __init__(self, model, output_name):
        self.model = Variable(model)        
        self.output_name = Variable(output_name)        
    
    def render(self, context):
        model = self.model.resolve(context)
        output_name = self.output_name.resolve(context)
        
        context[output_name] = model._meta.local_fields
        context["%s_m2m" % output_name] = model._meta.local_many_to_many
        return ''

@register.filter
def hash(h, k):
    #print h, k
    if hasattr(h, "__iter__"):
        if k in h:
            return h[k]
    return None
    

@register.tag
def bulkimport_missing_fields(parser, token):
    """
    Used in the Error Browser to list what fields were missing (if any)
    """
    try:
        tag_name, job, field_data = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("usage: {% bulkimport_missing_fields job field_data %}")
    return MissingFields(job, field_data)

class MissingFields(template.Node):
    def __init__(self, job, field_data):
        self.job = Variable(job)        
        self.field_data = Variable(field_data)        
    
    def render(self, context):
        job = self.job.resolve(context)
        field_data = self.field_data.resolve(context)
        
        required = json.loads(job.required)
        mapping = json.loads(job.mapping)
        
        supplied = json.loads(field_data)
        
        missing = []
        
        if hasattr(required, '__iter__'):
            for f in required:
                try:
                    d = supplied[int(mapping[f])]
                except IndexError:
                    missing.append(f)
                else:
                    if d == '':
                        missing.append(f)
        
            if missing:
                return "(%s)" % ','.join(missing)
            
        return ''




