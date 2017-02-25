from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext, Context, loader
from django.core.urlresolvers import reverse

from lookup.forms import LookupForm

def index(request):
    
    if request.method == "POST":
        form = LookupForm(request.POST)
        
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('lookup_thanks'))
    else:
        form = LookupForm()
        
    return render_to_response('lookup/index.html', {'form': form},
                    context_instance=RequestContext(request))


def thanks(request):
    
    return render_to_response('lookup/thanks.html', 
                    {},
                    context_instance=RequestContext(request))


