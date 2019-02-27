from django.http import Http404 #, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.template import RequestContext
from django.contrib.admin.views.decorators import staff_member_required

from django.contrib import messages
import subprocess

try:
    import json
except ImportError:
    from django.utils import simplejson as json

from django_apps.bulkimport.models import Job, Template, Log, Error
from django_apps.bulkimport.forms import JobForm, TemplateForm, JobFormTemplate
import logging


@staff_member_required
def render_to_admin(request, template, title, data, model, original=False, delete=True, **kwargs):
    """
    Helper method to correctly display admin like templates. Sets the variables that
    admin templates expect to see
    """

    # test for Meta class. If exists, add it.
    data['opts'] = model._meta
    data['admin'] = True
    data['title'] = title
    data['app_label'] = model._meta.app_label
    data['is_popup'] = '_popup' in request
    data['change'] = True
    data['show_delete'] = delete
    data['save_as'] = False
    data['has_delete_permission'] = delete
    data['has_add_permission'] = True
    data['has_change_permission'] = True
    data['add'] = False
    
    if original:
        data['original'] = original
        data['object'] = original
    else:
        data['change'] = False
        data['show_delete'] = False
        data['add'] = True
        data['original'] = False
    
    for k,v in kwargs.items():
        data[k] = v

    return render(request, template, data )


@staff_member_required
def job_add(request):
    templates = Template.objects.all()
    
    data = {}
        
    if request.method == 'POST':
        form = JobForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.save()
            return redirect('bulkimport_job_change', job_id=job.id)
    else:
        form = JobForm()
        
    data['form'] = form
    data['templates'] = templates
    extra = {'has_add_permission': False, 'has_change_permission': False, 'show_save': False}
    
    return render_to_admin(request, 'admin/bulkimport/job/change_form.html', 'Add job', data, Job, **extra)


@staff_member_required
def job_change(request, job_id):
    """
    Gathers the mapping data after a base job has been created. Mapping data
    associates columns of the CSV with a model field.
    """

    try:
        original = get_object_or_404(Job, pk=job_id)
    except Job.DoesNotExist:
        raise Http404
                
    data = {}
    
    extra = {'has_add_permission': False, 'has_change_permission': False, 'show_save': False}
    
    if request.method == "POST":
        data['mapping'] = request.POST.get('mapping', False)
        data['mapping_through'] = request.POST.get('mapping_through', False)
        data['required'] = request.POST.get('required', False)
        data['unique'] = request.POST.get('unique', False)
                
        form = JobForm(request.POST, instance=original)
                            
        if form.is_valid():
            f = form.save(commit=False)
            f.mapping = json.dumps(data['mapping'])
            f.mapping_through = json.dumps(data['mapping_through'])
            f.required = json.dumps(data['required'])
            f.unique = json.dumps(data['unique'])
            f.status = 'progress'
            f.save()

            """
                Start the import process from the cli so we can release the process.
                threading.Thread does not work for some odd reason, so we have to do it this way.
                We request the pid so the child process returns immediately while it works in
                the background.
            """
            logging.debug("")
            logging.debug("")
            logging.debug("Form is a POST and is Valid (Line 116). We are calling the threaded import.py file.")
            logging.debug("")
            logging.debug("")

            directory = "/home/merriman/django_apps/bulkimport/"
            the_pid = subprocess.Popen(["/usr/bin/python2.7", "import.py", str(f.id)],
                                       cwd=directory).pid
            
            return redirect('bulkimport_job_change', job_id=job_id)

    else:
        form = JobForm(instance=original)
        
        if original.mapping:
            data['mapping'] = json.loads(original.mapping)
            
        if original.mapping_through:
            data['mapping_through'] = json.loads(original.mapping_through)
        
        if original.required:
            data['required'] = json.loads(original.required)
            
        if original.unique:
            data['unique'] = json.loads(original.unique)
    
        if original.status != "new":
            data['count'] = Log.objects.filter(job=original).count()
            data['error_count'] = Error.objects.filter(job=original).count()
        
    data['form'] = form
    
    return render_to_admin(request, 
        'admin/bulkimport/job/change_form.html', 
        'Change Import Job',
        data,
        Job,
        original, 
        True,
        **extra)


@staff_member_required
def job_delete(request, job_id):
    """
    Deleting a job consists of not only deleting the Job object, 
    but also the objects that our Job created and the associated
    log entries. 
    """

    original = get_object_or_404(Job, pk=job_id)

    if request.method == "POST":
        cancel = request.POST.get('cancel', False)
        accept = request.POST.get('accept', False)

        if cancel:
            # 'admin:bulkimport_job_change' forces django to look for the reverse URL in the admin module ONLY
            # 'bulkimport_job_change' tells django to look for the reverse URL in the local module FIRST
            return redirect('bulkimport_job_change', job_id=job_id)

        if accept:
            #Actually do the delete, starting with any added objects

            added_objects = Log.objects.filter(job=original)

            for obj in added_objects:
                try:
                    obj.content_type.get_object_for_this_type(pk=obj.remote_pk).delete()
                except obj.content_type.model_class().DoesNotExist:
                    pass

                obj.delete()

            original.delete()

            messages.success(request, "Your job was deleted successfully.")

            return redirect('admin:bulkimport_job_changelist')
    else:
        logs_count = Log.objects.filter(job=original).count()
        data = {'original':original, 'logs_count':logs_count}

        return render_to_admin(request,
            'admin/bulkimport/job_delete.html',
            'Delete Import Job',
            data,
            Job,
            original)

# DEPRECATED ---
# def job_process(job_id):
#     """
#         Main workhorse of bulkimport--this function runs in the background
#         (via threading) and works through to complete a job. A fair amount
#         of trickery is involved in dynamically inserting to models. The
#         basic flow is:
#
#         Iterate through CSV file and, using the job's mapping data, decide
#         if we have to look up related objects. Combine all arguments and
#         finally create() the object. A record is kept for all created
#         objects so that we can delete imported records.
#     """
#
#     logging.debug("")
#     logging.debug("")
#     logging.debug("We are about to put the second thread to sleep for a bit...")
#     logging.debug("")
#     logging.debug("")
#
#     # We MUST wait until the calling script finishes BEFORE ANY of the DB queries will
#     # hit the database. So, we put this process to sleep a bit.
#     time.sleep(1)
#
#     original = Job.objects.get(pk=job_id)
#
#     if not original.mapping or not original.mapping_through:
#         raise Http404
#
#     original.status = 'progress'
#     original.save()
#
#     original_model = original.content_type.model_class()    # pin model
#     related_models = {}
#     m2m_models = {}
#
#     for f in original_model._meta.local_fields:
#         if hasattr(f, 'related'):
#             related_models[f.name] = f.related.parent_model
#
#     for f in original_model._meta.local_many_to_many:
#         m2m_models[f.name] = {'parent_model': f.related.parent_model, 'attname': f.attname}
#
#     mapping = json.loads(original.mapping)
#     mapping_through = json.loads(original.mapping_through)
#     required = json.loads(original.required)
#     unique = json.loads(original.unique)
#
#     lines = csv.reader(original.data.readlines(), quoting=csv.QUOTE_ALL)
#
#     added = 0
#
#     if not mapping:
#         original.status = "failed"
#         original.save()
#         return HttpResponse(True)
#
#     for line in lines:
#         args = {}
#         m2m_args = []
#         do_not_add = False
#
#         logging.debug("")
#         logging.debug("")
#         logging.debug("csv line: " + json.dumps(line))
#         logging.debug("")
#         logging.debug("")
#
#         for k,v in mapping.items():
#
#             if v is not None:
#                 try:
#                     val = line[int(v)]
#                 except:
#                     continue
#
#                 #If the field is required, check to make sure there is a value
#                 if required and required.has_key(k):
#                     if not val or val == '':
#                         Error.objects.create(   job=original,
#                                                 data=json.dumps(line),
#                                                 message="Missing required field")
#                         do_not_add = True
#                         continue
#
#                 #If the field is unique, check to make sure it doesn't already exist
#                 if unique and unique.has_key(k):
#                     unique_args = {str(k): val}
#                     c = original_model.objects.filter(**unique_args).count()
#                     if not c == 0:
#                         do_not_add = True
#                         Error.objects.create(   job=original,
#                                                 data=json.dumps(line),
#                                                 message="Duplicate value for unique field")
#                         break #continue  Was continue, changed to break DSB
#
#                 try:
#                     #If there's a related field
#                     relation = mapping_through[k]
#                 except (KeyError, TypeError):
#                     #No relation, so straigt key=value
#                     args[str(k)] = val
#
#                 else:
#                     if related_models.has_key(k):
#                         #FK field
#                         try:
#                             args[str(k)] = related_models[k].objects.get(**{str(relation):val})
#                         except:
#                             if required and required.has_key(k):
#                                 do_not_add = True
#                                 msg = "A required %s object was not found by %s='%s'" % (k, str(relation), val)
#                                 Error.objects.create(   job=original,
#                                                         data=json.dumps(line),
#                                                         message=msg)
#                                 break  # Added break DSB
#
#                             continue
#
#                 if m2m_models.has_key(k):
#                     vals = val.split(';')
#                     for m2m_val in vals:
#                         try:
#                             m2m_arg = { 'obj': m2m_models[k]['parent_model'].objects.get(**{str(relation):m2m_val}),
#                                         'attname': m2m_models[k]['attname']}
#                             m2m_args.append(m2m_arg)
#                         except m2m_models[k]['parent_model'].DoesNotExist:
#                             pass
#
#         if not do_not_add and args:
#             try:
#                 row = original_model.objects.create(**args)
#                 Log.objects.create(content_type=original.content_type, remote_pk=row.id, job=original)
#
#                 if m2m_args:
#                     for m2m_arg in m2m_args:
#                         m2m_row = getattr(row, m2m_arg['attname'])
#                         m2m_row.add(m2m_arg['obj'])
#
#                 added = added + 1
#
#             except Exception, e:
#                 arg_json = {}
#                 try:
#                     arg_json = json.dumps(args)
#
#                 except TypeError:
#                     for k,v in args.items():
#                         try:
#                             arg_json[k] = serializers.serialize("json", [v])
#                         except:
#                             pass
#
#                     arg_json = json.dumps(arg_json)
#
#                 if required and required.has_key(k):
#                     Error.objects.create(   job=original,
#                                             data=json.dumps(line),
#                                             message="Couldn't add row (%s)" % e,
#                                             extra=arg_json)
#
#             # if m2m_args:    #Moved up above on line ~ 308
#             #    for m2m_arg in m2m_args:
#             #        m2m_row = getattr(row, m2m_arg['attname'])
#             #        m2m_row.add(m2m_arg['obj'])
#
#         #do_not_add = False   REMOVED by DSB
#
#     # Uodate the status in the Job Model, bulkimport_job table.
#     if added > 0:
#         original.status = 'complete'
#     else:
#         original.status = 'failed'
#     original.save()
#
#     return HttpResponse(True)


@staff_member_required
def template_change(request, template_id):
    
    original = get_object_or_404(Template, pk=template_id)
    
    data = {}
    
    if request.method == "POST":
        
        data['mapping'] = request.POST.get('mapping', False)
        data['mapping_through'] = request.POST.get('mapping_through', False)
        data['required'] = request.POST.get('required', False)
        data['unique'] = request.POST.get('unique', False)
        
        form = TemplateForm(request.POST, instance=original)
                            
        if form.is_valid():
            f = form.save(commit=False)
            f.mapping = json.dumps(data['mapping'])
            f.mapping_through = json.dumps(data['mapping_through'])
            f.required = json.dumps(data['required'])
            f.unique = json.dumps(data['unique'])
            f.save()
            
        save_add_another = request.POST.get('_addanother', False)
        save_continue = request.POST.get('_save_continue', False)
        save = request.POST.get('_save', False)
        
        if save_add_another:
            return redirect('admin:bulkimport_template_add')
        
        if save_continue:
            return redirect('admin:bulkimport_template_change', template_id=template_id)
        
        if save:
            return redirect('admin:bulkimport_template_changelist')
            
            
    else:
        form = TemplateForm()
        
        if original.mapping:
            data['mapping'] = json.loads(original.mapping)
            
        if original.mapping_through:
            data['mapping_through'] = json.loads(original.mapping_through)
            
        if original.required:
            data['required'] = json.loads(original.required)
            
        if original.unique:
            data['unique'] = json.loads(original.unique)
    
    data['form'] = form
    
    return render_to_admin(request, 
        'admin/bulkimport/template_change.html', 
        'Change Template',
        data,
        Template,
        original)


@staff_member_required
def template_new_import(request, template_id):
    template = get_object_or_404(Template, pk=template_id)

    logging.debug("")
    logging.debug("Starting template_new_import on line 454.")
    logging.debug("")
    
    if request.method == "POST":
        form = JobFormTemplate( request.POST, request.FILES)
                        
        if form.is_valid():
            try:
                f = form.save(commit=False) # Just return the instance of the Model, not a DB INSERT
                f.content_type = template.content_type
                f.mapping = template.mapping
                f.mapping_through = template.mapping_through
                f.required = template.required
                f.unique = template.unique
                f.status = 'progress'
                f.template = template
                f.save()

                """
                    Start the import process from the cli so we can release the process.
                    threading.Thread does not work for some odd reason, so we have to do it this way.
                    We request the pid so the child process returns immediately while it works in
                    the background.
                """

                logging.debug("")
                logging.debug("Form is a POST and is Valid (Line 479). We are calling the threaded import.py file.")
                logging.debug("")

                directory = "/home/merriman/django_apps/bulkimport/"
                the_pid = subprocess.Popen(["/usr/bin/python3", "import.py", str(f.id)],
                                 cwd=directory).pid

                # 'admin:bulkimport_job_change' forces django to look for the reverse URL in the admin module ONLY
                # 'bulkimport_job_change' tells django to look for the reverse URL in the local module FIRST
                return redirect('bulkimport_job_change', job_id=f.id)

            except Exception as e:
                print(e)
        else:
            print(form.errors)
            
        
    else:
        logging.debug("")
        logging.debug("Form is NOT a POST")
        logging.debug("")

        form = JobFormTemplate()
    
    data = {'form': form}
    
    return render_to_admin(request, 
        'admin/bulkimport/template_add_new_job.html', 
        'New %s import' % template,
        data,
        Template,
        template, 
        False)

