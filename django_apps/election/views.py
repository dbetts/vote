from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext, Context
from django.template.loader import get_template
from django.core.urlresolvers import reverse
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings

try:
    import json
except ImportError:
    import simplejson as json

import logging
import datetime

import twilio

from django_apps.election.forms import PINForm, BallotForm, VerifyForm, ValidateForm
from django_apps.election.models import Election, PIN, Log, Mail_Log, Ballot, Question, Vote, Asset
from django_apps.election.models import Phone_Session, Phone_Choice, Choice, Ballot_Question
from django_apps.election.models import Invalid_Response
from itertools import chain

def _check_if_banned_request(identification):
    
    yesterday = datetime.datetime.now() - datetime.timedelta(minutes=1)
    
    r = Invalid_Response.objects.filter(identification=identification,
                                        created_at__gt=yesterday)
                                        
    if r.count() > 9:
        return True
    
    return False

def _if_banned(request):
    return render_to_response('election/banned.html',
                    {},
                    context_instance=RequestContext(request))

def set_initial_session_vars(request):
    # Set a session var to hold the sub-domain name used for DB calls when building pages.
    # This is needed if the page is already pointed to the /pin/ location and the
    # user changes the sub-domain
    subDomain = request.get_host().split('.').pop(0)
    request.session['subdomain'] = subDomain
    try:
        assetModel = Asset.objects.select_related().get(sub_domain=subDomain)
        request.session['election_id'] = assetModel.election_id
    except Asset.DoesNotExist:
        request.session['election_id'] = 0


def index(request):
    set_initial_session_vars(request)

    """
    If there's only one language, we skip around the user having to select
    it.
    """
    if len(settings.LANGUAGES) == 1:
        return HttpResponseRedirect(reverse('election_pin'))
    
    return render_to_response('election/index.html', {},
                    context_instance=RequestContext(request))


class Object(object):
    pass

def pin(request):
    set_initial_session_vars(request)

    """
    A PIN is required to fetch a ballot
    """
    
    if _check_if_banned_request(request.META['REMOTE_ADDR']):
        return _if_banned(request)
    
    if request.method == "POST":
        form = PINForm(request, data=request.POST)
        if form.is_valid():
            request.session['pin'] = form.cleaned_data['pin']
            if request.session['election_id'] == 0:
                request.session['election_id'] = form.election.id

            return HttpResponseRedirect(reverse('election_validate'))
        else:
            # This writes failed attempts to the DB and returns to the page with no errors?
            Invalid_Response.objects.create(identification=request.META['REMOTE_ADDR'],
                                            digits=request.POST['pin'])

            #If the user is banned, then give them a hard time. Send them to election/banned.html
            if _check_if_banned_request(request.META['REMOTE_ADDR']):
                return _if_banned(request)
    else:
        form = PINForm(request)

        # if not hasattr(form, 'pin'):
        #     form = Object()
        #     form.pin = Object()
        #     form.pin.name = 'pin'
        #     form.pin.value = ''

    try:
        election = Election.objects.select_related().get(pk=request.session.get('election_id'))
        asset = Asset.objects.get(election=election)
        page_banner_source = settings.UPLOAD_URL + asset.header_image.name

        if (not page_banner_source):
            page_banner_source = settings.MEDIA_URL + 'images/banner.jpg'

    except Election.DoesNotExist:
        # An exception is raised when there is no Election with the supplied election_id
        # Usually this happens when there is no sub-domain that matches the input URL.
        page_banner_source = settings.MEDIA_URL + 'images/banner.jpg'
    
    return render_to_response('election/pin.html',
                    {
                        'form': form,
                        'page_banner': page_banner_source,
                        'domain': request.session.get('subdomain', 'default'),
                        'theElectionId': request.session.get('election_id', 'no idea'),
                    },
                    context_instance=RequestContext(request))


def validate(request):
    """
    Uses a second form of authentication (either phone or validation ID)
    to identify the user
    """

    if _check_if_banned_request(request.META['REMOTE_ADDR']):
        return _if_banned(request)

    pin = get_object_or_404(PIN, pin=request.session.get('pin'))
    asset = Asset.objects.get(election=pin.election)
    validation_text = asset.validation_text

    if not validation_text:
        validation_text = 'Last four digits of your account number starting with'

    validate_against = pin.validation_start
    validate_answer = pin.validation_number

    if not validate_against:
        return HttpResponseRedirect(reverse('election_ballot', args=[pin.election.id]))
    
    if request.method == "POST":
        form = ValidateForm(request.POST, answer=validate_answer)
        
        if form.is_valid():
            ####return HttpResponseRedirect(reverse('election_welcome', args=[pin.election.id]))
            return HttpResponseRedirect(reverse('election_ballot', args=[pin.election.id]))
        else:
            Invalid_Response.objects.create(identification=request.META['REMOTE_ADDR'],
                                            digits=request.POST['value'])
            if _check_if_banned_request(request.META['REMOTE_ADDR']):
                return _if_banned(request)
            
    else:
        form = ValidateForm()
        
    context = {
                'validation_text': validation_text,
                #'validation_method': validation_method,
                'validate_against': validate_against,
                'form': form,
                'custom_footer': '<a class="link2" href="/pin">If this isn''t you click here.</a>'
               }
            
    return render_to_response('election/validate.html', 
                context,
                context_instance=RequestContext(request))

# DEPRECATED - This method is not being called any longer.
def welcome(request, election_id):
    """
    Interstitial page between the PIN entry and ballot creation
    """
    
    election = get_object_or_404(Election, pk=election_id)
    
    if not election.active():
        """
        Elections are open during a set of datetimes, if we're not in the middle
        show an error
        """
        return render_to_response('election/not_active.html', 
                        {'election': election,},
                        context_instance=RequestContext(request))
                        
    pin = get_object_or_404(PIN, pin=request.session.get('pin'), election=election)
    
    return render_to_response('election/welcome.html', 
                {'election': election, 'pin': pin},
                context_instance=RequestContext(request))


def ballot(request, election_id, change=False, cast=False):
    """
    Presents and attempts to save a ballot. A valid unused PIN is required to
    process. 
    """
    
    election = get_object_or_404(Election, pk=election_id)
    
    if not election.active():
        """
        Elections are open during a set of datetimes, if we're not in the middle
        show an error
        """
        return render_to_response('election/not_active.html', 
                        {'election': election,},
                        context_instance=RequestContext(request))
                        
    pin = get_object_or_404(PIN, pin=request.session.get('pin'), election=election)
    
    try:
        Log.objects.get(pin=pin.pin)
    except Log.DoesNotExist:
        pass
    else:
        logging.debug("Duplicate vote request outside of form--denied creating ballot for %s" % pin.pin)
        raise Http404
        
    try:
        Mail_Log.objects.get(pin=pin.pin)
    except Mail_Log.DoesNotExist:
        pass
    else:
        logging.debug("Duplicate vote request from mail ballot made outside of form--denied creating ballot for %s" % pin.pin)
        raise Http404
    
    try:
        ballot = Ballot.objects.get(pk=pin.ballot.id, election=election)
    except Ballot.DoesNotExist:
        logging.debug("Ballot ID %d could not be found for Election %d" % (pin.ballot_id, election.id))        
        raise Http404
    
    questions = Question.objects.filter(ballot=ballot).order_by('ballot_question__order')
    
    ballot_json = False
    initial_data = {}
    
    if request.POST.get('ballot_json', False):
        ballot_json = json.loads(request.POST.get('ballot_json'))
        
    if ballot_json:
        for question_id in ballot_json:
            initial_data[question_id] = ballot_json[question_id]['answer']
            
    """
    By default N/A questions aren't in the JSON data, so need to them back in
    for correct display of the modify ballot form
    """
    if initial_data:
        for q in questions:
            if q.min_responses == 0 and q.max_responses == 1 and not initial_data.has_key(str(q.id)):
                initial_data[str(q.id)] = "0"

    if request.method == "POST" and not change:
        form_post = request.POST
        logging.info("Message was posted")
        logging.info(form_post)
        form = BallotForm(form_post, ballot_jn=ballot_json, ballot=ballot)
        logging.info("Form was created")
        
        logging.debug("Processing ballot for %s" % pin.pin)
        if form.is_valid():
            logging.debug("Ballot for %s is valid" % pin.pin)
            
            if cast:
                confirmation = form.save()
                if confirmation:
                    logging.debug("Ballot for %s has been saved" % pin.pin)
                    Log.objects.create(election=election, pin=pin.pin)
                    return HttpResponseRedirect(reverse('election_confirm', args=[confirmation.uuid]))
                else:
                    logging.debug("Ballot for %s could not be saved" % pin.pin)
            else:
                preview_ballot = form.save(commit=False)
                
                data = {'preview_ballot': preview_ballot, 
                        'election': election,
                        'questions': questions,
                        'ballot_json': json.dumps(preview_ballot),
                        'form': form}
                return render_to_response('election/ballot_preview.html', 
                                data,
                                context_instance=RequestContext(request))
        else:
            logging.debug("Ballot for %s had form errors" % pin.pin)
    else:
        form = BallotForm(ballot_jn=ballot_json, ballot=pin.ballot, initial=initial_data)
        logging.debug("Presenting ballot for %s" % pin.pin)

    try:
        asset = Asset.objects.get(election=election)
        ballot_extra = asset.ballot_extra

        if (not ballot_extra):
            ballot_extra = ''

    except Asset.DoesNotExist:
        # An exception is raised when there is no Asset with the supplied election_id
        # Usually this happens when there is no sub-domain that matches the input URL.
        ballot_extra = ''


    return render_to_response('election/ballot.html', 
                    {   'election': election,
                        'pin': pin,
                        'form': form,
                        'ballot_extra': ballot_extra
                    },
                    context_instance=RequestContext(request))


def db_hash(h, k):
    if hasattr(h, "__iter__"):
        if k in h:
            return h[k]
        if str(k) in h:
            return h[str(k)]
    return None


def confirm(request, uuid):
    """
    Present the vote confirmation screen that gives voter their ID
    and shows how their vote was tallied.
    """

    try:
        election = Election.objects.select_related().get(pk=request.session.get('election_id'))
        asset = Asset.objects.get(election=election)
        exit_url = asset.exit_url

        if (not exit_url):
            exit_url = settings.DEFAULT_EXIT_PAGE

    except Asset.DoesNotExist:
        # An exception is raised when there is no Asset with the supplied election_id
        # Usually this happens when there is no sub-domain that matches the input URL.
        exit_url = settings.DEFAULT_EXIT_PAGE
    
    try:
        vote = Vote.objects.get(uuid=uuid)
    except Vote.DoesNotExist:
        return render_to_response('election/confirm_error.html',
                        context_instance=RequestContext(request))
                        
    try:
        del request.session['pin']
    except KeyError:
        pass
    
    #questions = Question.objects.filter(ballot=vote.ballot)
    # This is a test to see if the order is correct.
    questions = Question.objects.filter(ballot=vote.ballot).order_by('ballot_question__order')
    ballot = json.loads(vote.choices)

    data = {
        'vote': vote,
        'ballot': ballot,
        'questions': questions,
        'exit_url': exit_url
    }
            
    return render_to_response('election/confirm.html', data,
                    context_instance=RequestContext(request))


def verify(request):
    """
    Looks up a vote record by its confirmation code and forwards to the 
    confirm view with that vote's UUID. The UUID changes on each request, 
    so the page remains secure (even if the URL is stuck in a browser history
    somewhere).
    """
    if request.method == "POST":
        form = VerifyForm(request.POST)
        
        if form.is_valid():
            return HttpResponseRedirect(reverse('election_confirm', args=[form.vote.uuid]))
    else:
        form = VerifyForm()
    
    return render_to_response('election/verify.html', 
                {
                    'form': form,
                    'custom_footer': '<a class="link2" href="/pin">If this isn''t you click here.</a>'
                 },
                context_instance=RequestContext(request))


@staff_member_required
def pin_status(request, election_id):
    import csv, os
    
    try:
        election = Election.objects.select_related().get(pk=election_id)
    except Election.DoesNotExist:
        raise Http404    
    
    response = HttpResponse(mimetype='application/csv')
    response['Content-Disposition'] = 'attachment; filename=election_%s_pin_status.csv' % (election_id)
    
    response.write("Election: %s\n\nPIN, VOTE BOOLEAN\n\n" % (election.name))
    
    pins = election.pin_set.all()
    
    for pin in pins:
        count = pin.log_set.count()
        response.write("%s, %s\n" % (pin.pin, count))
        
        
    return response


@staff_member_required
def vote_status(request, election_id):
    import csv, os
    
    try:
        election = Election.objects.select_related().get(pk=election_id)
    except Election.DoesNotExist:
        raise Http404    
    
    response = HttpResponse(mimetype='application/csv')
    response['Content-Disposition'] = 'attachment; filename=election_%s_ballots.csv' % (election_id)
    
    writer = csv.writer(response)
    
    writer.writerow(['ELECTION: %s' % election.name])
    writer.writerow(['CONFIRMATION', 'VOTES'])
    
    votes = election.vote_set.all()
    
    for vote in votes:
        writer.writerow([vote.confirmation, vote.choices])
        
    return response


@staff_member_required
def results(request, election_id):
    
    try:
        election = Election.objects.select_related().get(pk=election_id)
    except Election.DoesNotExist:
        raise Http404    
    
    ballots = Ballot.objects.filter(election=election)
    votes = Vote.objects.filter(election=election)    
    pins = PIN.objects.filter(election=election)    
    
    return render_to_response('admin/election/election/results.html', 
                {'election': election,
                 'ballots': ballots,
                 'pins': pins,
                 'votes': votes},
                context_instance=RequestContext(request))


def render_to_phone(data):
    
    response = HttpResponse(data)
    response['Content-Type'] = 'text/xml'
    
    return response


def error_to_phone(msg, audio=False, redirect=False):
    r = twilio.Response()
    
    if audio:
        r.addPlay(audio.url)
    else:
        r.addSay(msg)
    
    if redirect:
        r.addRedirect(redirect)
    
    return render_to_phone(r)


def _phone_template(template, data = {}):
    template = get_template(template)
    return template.render(Context(data))


def _return_phone_uuid(request):
    return request.REQUEST.get('CallGuid', False)


def _return_session(request):
    uuid = _return_phone_uuid(request)
    
    if not uuid:
        raise Http404
        
    try:
        session = Phone_Session.objects.select_related().get(uuid=uuid)
    except Phone_Session.DoesNotExist:
        logging.debug("Phone %s - No matching session" % (uuid))
        raise Http404
    
    return session


def phone_index(request, election_id):
    uuid = request.REQUEST.get('CallGuid', False)
    logging.debug("Phone %s - phone_index election_id=%s" % (uuid, election_id))
    
    election = get_object_or_404(Election, pk=election_id)  
    
    r = twilio.Response()
    
    g = twilio.Gather(action=reverse('election_phone_welcome', args=[election_id]))
    
    if election.audio_start:
        g.append(twilio.Play(election.audio_start.url))
    else:
        g.append(twilio.Say(_phone_template('election/phone/welcome.txt', {'election': election})))
    
    r.append(g)
    r.addRedirect(reverse('election_phone_index', args=[election_id]))
    return render_to_phone(r)


def phone_welcome(request, election_id):
    
    uuid = request.REQUEST.get('CallGuid', False)
    phone_number = request.REQUEST.get('Caller', False)
    digits = request.REQUEST.get('Digits', False)
    
    logging.debug("Phone %s - phone_welcome election_id=%s" % (uuid, election_id))
            
    election = get_object_or_404(Election, pk=election_id)
    
    if _check_if_banned_request(phone_number):
        return error_to_phone(_phone_template('election/phone/banned.txt'),
                                                audio=election.audio_if_banned)
    
    r = twilio.Response()
    
    if digits == '1':
        r.addRedirect(reverse('election_phone_ballot', args=[election_id]))
    elif digits == '9':
        r.addRedirect(reverse('election_phone_info', args=[election_id]))
    else:
        return error_to_phone(_phone_template('election/phone/_invalid_response.txt', 
                                                {'digits': digits}),
                                                redirect=reverse("election_phone_index", args=[election_id]),
                                                audio=election.audio_invalid_response)
    return render_to_phone(r)


def phone_info(request, election_id):
    uuid = request.REQUEST.get('CallGuid', False)
    logging.debug("Phone %s - phone_info election_id=%s" % (uuid, election_id))
    
    election = get_object_or_404(Election, pk=election_id)
    
    digits = request.REQUEST.get('Digits', False)
    
    r = twilio.Response()
        
    if digits:
        if digits == '1':
            r.addRedirect(reverse('election_phone_ballot', args=[election_id]))
        elif digits == '2':
            r.addRedirect(reverse('election_phone_info', args=[election_id]))
        else:
            return error_to_phone(_phone_template('election/phone/_invalid_response.txt', 
                                                    {'digits': digits}),
                                                    redirect=reverse("election_phone_welcome", args=[election_id]),
                                                    audio=election.audio_invalid_response)
    else:
        g = twilio.Gather(timeout=10, action=reverse('election_phone_info', args=[election_id]))
        
        if election.audio_privacy:
            g.append(twilio.Play(election.audio_privacy.url))
        else:
            g.append(twilio.Say(_phone_template('election/phone/welcome_more_info.txt', {'election': election})))
        
        r.append(g)
    return render_to_phone(r)

     
def phone_ballot(request, election_id):
    
    uuid = _return_phone_uuid(request)
    phone_number = request.REQUEST.get('Caller', False)
    pin_digits = request.REQUEST.get('Digits', False)
    
    logging.debug("Phone %s - phone_ballot election_id=%s" % (uuid, election_id))
    
    election = get_object_or_404(Election, pk=election_id)
    
    if not election.active():
        logging.debug("Phone %s - Election (%s) is inactive" % (uuid, election))
        return error_to_phone(_phone_template('election/phone/inactive.txt', {'election': election}))
        
    if _check_if_banned_request(phone_number):
        return error_to_phone(_phone_template('election/phone/banned.txt'),
                                                audio=election.audio_if_banned)    
    if not pin_digits:
        """
        If there aren't any digits we need to tell the user to provide them
        """
        r = twilio.Response()
        
        g = twilio.Gather(timeout=10, action=reverse('election_phone_ballot', args=[election_id]))
        
        if election.audio_pin:
            g.append(twilio.Play(election.audio_pin.url))
        else:
            g.append(twilio.Say(_phone_template('election/phone/welcome_pin.txt', {})))
        
        r.append(g)
        
        return render_to_phone(r)
                
    try:
        pin = PIN.objects.get(pin=pin_digits, election=election)
    except PIN.DoesNotExist:
        Invalid_Response.objects.create(identification=phone_number,
                                        digits=pin_digits)
        
        logging.debug("Phone %s - PIN (%s) not found" % (uuid, pin_digits))
        return error_to_phone("We're sorry, but the PIN %s was not found." % pin_digits, 
                                redirect=reverse("election_phone_ballot", args=[election_id]))
    
    try:
        Log.objects.get(pin=pin)
    except Log.DoesNotExist:
        pass
    else:
        logging.debug("Phone %s - Duplicate vote request outside of form--denied creating ballot" % uuid)
        return error_to_phone("We're sorry, but the entered PIN has already voted in this election.",
                                audio=election.audio_already_voted)
                                
    try:
        Mail_Log.objects.get(pin=pin)
    except Mail_Log.DoesNotExist:
        pass
    else:
        logging.debug("Phone %s - Duplicate vote request outside of form from mail log--denied creating ballot" % uuid)
        return error_to_phone("We're sorry, but the entered PIN has already voted in this election.",
                                audio=election.audio_already_voted)
    
    try:
        ballot = Ballot.objects.get(pk=pin.ballot.id, election=election)
    except Ballot.DoesNotExist:
        logging.debug("Phone - %s Ballot ID %d could not be found for Election %d" % 
                        (uuid, pin.ballot_id, election.id))        
        return error_to_phone("We're sorry, but your ballot could not be generated.", 
                                audio=election.audio_error)
    
    try:
        session = Phone_Session.objects.get(uuid=uuid)
    except:
        session = Phone_Session.objects.create( uuid=uuid, 
                                                election=election, 
                                                pin=pin,
                                                next_question=ballot.questions.all().order_by('ballot_question__order')[0])
    else:
        logging.debug("Phone %s - phone_ballot User had an existing session" % uuid)
        
    r = twilio.Response()
    r.addRedirect(reverse('election_phone_verify', args=[election_id]))
    
    return render_to_phone(r)


def phone_verify(request, election_id):
    """
    Verifies the user against their phone number or verification value
    """
    
    def proceed_to_questions(session, election):
        """
        Skips users onto the questions, this is a nested function because it's used
        both when we can't validate and must move on and when we do validate correctly.
        """
        ballot = Ballot.objects.get(pk=session.pin.ballot_id, election=election)
        
        r = twilio.Response()
        
        if ballot.audio:
            r.addPlay(ballot.audio.url)
        else:
            r.addSay(_phone_template('election/phone/ballot_start.txt', {'ballot': ballot}))
        r.addPause(length=2)
        r.addRedirect(reverse('election_phone_question', args=[session.next_question.id]))
        
        return render_to_phone(r)
        
    uuid = request.REQUEST.get('CallGuid', False)
    phone_number = request.REQUEST.get('Caller', False)
    logging.debug("Phone %s - phone_info election_id=%s" % (uuid, election_id))
        
    election = get_object_or_404(Election, pk=election_id)
        
    if _check_if_banned_request(phone_number):
        logging.debug("Phone %s - phone_info banned" % (uuid, election_id))
        return error_to_phone(_phone_template('election/phone/banned.txt'),
                                                audio=election.audio_if_banned)    
        
    session = _return_session(request)
    
    digits = request.REQUEST.get('Digits', False)
        
    if session.pin.phone:
        validate_against = session.pin.phone[:6]
        validate_answer = session.pin.phone[6:10]
        template = 'election/phone/welcome_verify.txt'
    elif session.pin.validation_number:
        validate_against = session.pin.validation_number[:5]
        validate_answer = session.pin.validation_number[5:9]
        template = 'election/phone/welcome_verify_validation_number.txt'
    else:
        """
        PIN has no phone or validation number, so we need to skip the verification
        """
        return proceed_to_questions(session=session, election=election)
    
    if digits:
        logging.debug("Phone %s - phone_info digits supplied: %s" % (uuid, digits))
        logging.debug("Phone %s - phone_info validating against: %s" % (uuid, validate_answer))
        
        if digits == validate_answer:
            logging.debug("Phone %s - phone_info valid, forward to questions" % (uuid))            
            return proceed_to_questions(session=session, election=election)
        else:
            logging.debug("Phone %s - phone_info invalid, cycle back" % (uuid))
            Invalid_Response.objects.create(identification=phone_number,
                                            digits=digits)
                              
            return error_to_phone("We're sorry, %s is an invalid response" % digits,
                                    redirect=reverse("election_phone_verify", 
                                    args=[election_id]))
    else:
        r = twilio.Response()
        
        g = twilio.Gather(timeout=10, action=reverse('election_phone_verify', args=[election_id]))
        g.append(twilio.Say(_phone_template(template, {'validate_against': validate_against })))
        
        r.append(g)
    
    return render_to_phone(r)

    
def phone_question(request, question_id):
    
    session = _return_session(request)
    digits = request.REQUEST.get('Digits', False)
        
    try:
        question = Question.objects.get(id=question_id)
    except:
        raise Http404
        
    r = twilio.Response()
    
    if question.max_responses > 1:
        limit = Phone_Choice.objects.filter(session=session, question=question).values_list('choice_id', flat=True)
    else:
        limit = []
                    
    if not limit:
        if question.audio:
            r.addPlay(question.audio.url)
        else:
            r.addSay(_phone_template('election/phone/question.txt', 
                    {'question': question, 'session': session}))
    
    g = twilio.Gather(timeout=10, 
                        action=reverse('election_phone_answer', 
                        args=[question_id]))
                    
    for choice in question.choices.all().exclude(pk__in=limit):
        
        if choice.audio_choice:
            g.append(twilio.Play(choice.audio_choice.url))
        else:
            g.append(twilio.Say(_phone_template('election/phone/choice.txt', 
                                {'choice': choice})))
    
    if limit:
        if session.election.audio_if_done:
            g.append(twilio.Play(session.election.audio_if_done.url))
        else:
            g.append(twilio.Say(_phone_template('election/phone/if_done.txt')))
            
    if session.election.audio_repeat:
        g.append(twilio.Play(session.election.audio_repeat.url))
    else:
        r.append(twilio.Say(_phone_template('election/phone/_repeat.txt')))
    
    r.append(g)
        
    r.addRedirect(reverse('election_phone_question', args=[question_id]))
    
    logging.debug("Phone %s - Presenting question \"%s\"" % (session.uuid, question))
    return render_to_phone(r)


def phone_answer(request, question_id):
    
    def next_question(session, question, digits, limit, choice=False):
        
        try:
            order = Ballot_Question.objects.get(ballot=session.pin.ballot, question=question).order
        except Ballot_Question.DoesNotExist:
            logging.debug("Phone %s - Ballot %s question %s does not exist" % (session.uuid, session.pin.ballot, question))
            return error_to_phone("We're sorry, but there has been an error. Please call back later.",
                                    audio=session.election.audio_error)
        
        moving_on = True
                
        if choice and question.max_responses > 1 and len(limit) < question.max_responses:
            moving_on = False
        
        if not moving_on:
            """
            If they aren't skipping on they need to see the same question again, so we 
            don't adjust session.next_question
            """
            pass
        else:
        
            next_question = Question.objects.filter(ballot=session.pin.ballot, 
                                                    ballot_question__order__gt=order).order_by('ballot_question__order')
                                            
            if next_question.count() == 0:
                session.next_question = None
            else:
                session.next_question = next_question[0]
            
            session.save()
        
        r = twilio.Response()
        
        if choice:
            if choice.audio_confirm:
                r.addPlay(choice.audio_confirm.url)
            else:
                r.addSay(_phone_template('election/phone/answer.txt', 
                            {'question': question, 'choice': choice}))
        
        if session.next_question == None:
            r.addRedirect(reverse('election_phone_finished'))
        else:    
            r.addRedirect(reverse('election_phone_question', 
                            args=[session.next_question.id]))
        return r
        
    session = _return_session(request)
    
    try:
        question = Question.objects.get(id=question_id)
    except Exception, e:
        logging.debug("Phone %s - Processing question ID #\"%s\", question not found" % (session.uuid, question_id))
        raise Http404
    
    if question.max_responses > 1:
        """
        For multiple response questions, we pull the previously chosen responses so they can
        be excluded from valid responses and used to direct properly to the next question.
        """
        limit = Phone_Choice.objects.filter(session=session, question=question).values_list('choice_id', flat=True)
        
        if len(limit) == question.max_responses:
            logging.debug("Phone %s - Possible hack, attempting to answer more than allowed for %s" % (session.uuid, question))
            raise Http404
    else:
        limit = []
        
    logging.debug("Phone %s - Processing question \"%s\" answer" % (session.uuid, question))
    
    digits = request.REQUEST.get('Digits', False)
    
    if not digits:
        logging.debug("Phone %s - No digits provided, can't answer" % (session.uuid))
        raise Http404
    
    logging.debug("Phone %s - Digits: %s" % (session.uuid, digits))
    
    """
    This error comes up several times, so we create it once at return it when needed
    """
    invalid_response_error = error_to_phone(_phone_template('election/phone/_invalid_response.txt', 
                                                {'digits': digits}),
                                                redirect=reverse("election_phone_question", args=[question_id]),
                                                audio=session.election.audio_invalid_response)
    if digits == '*':
        """
        The user has requested the choices to be repeated
        """
        r = twilio.Response()
        r.addRedirect(reverse("election_phone_question", args=[question_id]))
        return render_to_phone(r)
    
    try:
        digits = int(digits)
    except ValueError, AssertionError:
        return invalid_response_error
        
    if digits == 99:
        """
        User wants to skip question
        """
        if len(limit) >= question.min_responses:
            logging.debug("Phone %s - moving to next question" % (session.uuid))
        
            r = next_question(session=session, question=question, digits=digits, limit=limit)
            return render_to_phone(r)
            
    try:
        choice = question.choices.get(phone_option=digits)
    except Choice.DoesNotExist:
        return invalid_response_error
    
    
    if choice.id in limit:
        return invalid_response_error
    
    if question.max_responses > 1:
        Phone_Choice.objects.create(session=session, 
                                    question=question, 
                                    choice=choice)
        limit = Phone_Choice.objects.filter(session=session, question=question).values_list('choice_id', flat=True)
        
    else:
                                    
        try:
            selection = Phone_Choice.objects.get(session=session, question=question)
        except Phone_Choice.DoesNotExist:    
            Phone_Choice.objects.create(session=session, 
                                        question=question, 
                                        choice=choice)
        else:
            selection.choice = choice
            selection.save()
    
    r = next_question(session=session, 
                        question=question, 
                        digits=digits, 
                        limit=limit,
                        choice=choice)
        
    return render_to_phone(r)


def phone_finished(request):
    
    session = _return_session(request)
    
    r = twilio.Response()
    
    g = twilio.Gather(action=reverse('election_phone_cast_ballot'))
    
    if session.election.audio_finished:
        g.append(twilio.Play(session.election.audio_finished.url))
    else:
        g.append(twilio.Say(_phone_template('election/phone/finish.txt')))
        
    r.append(g)
    
    r.addSay(_phone_template('election/phone/finish_warning.txt'))
    r.addRedirect(reverse('election_phone_finished'))
    
    return render_to_phone(r)


def phone_cast_ballot(request):
    
    session = _return_session(request)
    
    digits = request.REQUEST.get('Digits', False)
    
    if not digits == "1":
        return error_to_phone("%s is not a valid entry" % digits, 
                    redirect=reverse('election_phone_finished'))
    
    try:
        Log.objects.get(pin=session.pin)
    except Log.DoesNotExist:
        pass
    else:
        logging.debug("Phone %s Duplicate vote request, denied casting ballot" % session.uuid)
        return error_to_phone("You have already cast a ballot for this election.")
        
    ballot_choices = {}
    
    choices = session.phone_choice_set.all()
    
    questions = session.phone_choice_set.all()
    questions.query.group_by = ['question_id']
    
    for q in questions:
        answer = []
        answer_eng = []
        
        for c in choices:
            if c.question == q.question:
                answer.append(c.choice.id)
                answer_eng.append(c.choice.answer)
        
        ballot_choices[q.question.id] = {'question': q.question.question, 
                                         'answer': answer,
                                         'answer_eng': answer_eng}
                                
    logging.debug("Phone %s - Attempting to save vote " % session.uuid)
    
    try:
        v = Vote.objects.create(election=session.election, 
                                ballot=session.pin.ballot, 
                                choices=json.dumps(ballot_choices),
                                phone=True)
    except Exception,e :
        logging.debug("Phone %s - problem saving vote for: %s" % (session.uuid, e))
        return error_to_phone("There was an error processing your ballot. Your vote has not been cast.")
    else:
        logging.debug("Phone %s - Ballot has been saved" % session.uuid)
        
        try:
            Log.objects.create(election=session.election, pin=session.pin)
        except:
            v.delete()
            logging.debug("Phone %s - Couldn't save log, deleting vote" % session.uuid)    
            return error_to_phone("There was an error processing your ballot. Your vote has not been cast.")
    
    r = twilio.Response()
    
    if session.election.audio_end:
        r.addPlay(session.election.audio_end.url)
    
    r.addSay(_phone_template('election/phone/thanks.txt', {'vote': v }))
            
    return render_to_phone(r)

