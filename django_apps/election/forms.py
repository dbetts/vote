from itertools import chain
from django.forms.utils import flatatt
import ast

from django import forms
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.html import conditional_escape
from django.forms.utils import ErrorList

from django.conf import settings
from django_apps.election.models import Election, Asset

try:
    import json
except ImportError:
    import simplejson as json

try:
    from django.utils.encoding import StrAndUnicode
except ImportError:
    from django.utils.encoding import python_2_unicode_compatible

    @python_2_unicode_compatible
    class StrAndUnicode(object):
        def __str__(self):
            return self.__unicode__()

import logging

from django_apps.election.models import PIN, Log, Mail_Log
from django_apps.election.models import Ballot, Question, Choice, Vote

class CheckboxSelectMultipleCustom(forms.SelectMultiple):
    def __init__(self, ballot_json):
        self.ballot_json = ballot_json
        super(CheckboxSelectMultipleCustom, self).__init__()

        
    def render(self, name, value, attrs=None, choices=()):
        # name = 37
        """
            value = [u'136',u'127',u'134'] OR
            value = {u'answer': [u'136', u'127', u'134'], u'question': u'Board of Directors', u'answer_eng': [u'Derrick Betts', u'Karen Baldwin', u'Steve M. Rapozo']} OR
            value = None
        """
        try:
            newValue = value.copy()
            if newValue['answer']:
                value = newValue['answer']
                names = newValue['answer_eng']
            else:
                value = value
                names = []
        except:
            value = value
            names = []

        if value is None: value = []
            
        has_id = attrs and 'id' in attrs
        attrs.update({u'name': name})
        final_attrs = self.build_attrs(attrs)

        output = [u'<ul>']
        # Normalize to strings
        str_values = set([force_text(v) for v in value])

        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = u' for="%s"' % final_attrs['id']
            else:
                label_for = ''

            if option_label == 999:
                
                cb = forms.CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
                option_value = force_text(option_value)
                rendered_cb = cb.render(name, option_value)

                post_key = final_attrs['name'] + '_write_in'
                post_id = final_attrs['name']
                final_attrs['id'] = post_key
                final_attrs['name'] = post_key
                field_value = None

                try:
                    field_value = self.ballot_json[post_key]
                except:
                    try:
                        for k, val in enumerate(self.ballot_json[post_id]['answer']):
                            if option_value == val:
                                field_value = self.ballot_json[post_id]['answer_eng'][k]
                    except:                        
                        try:
                            field_value = names[len(names)-1]
                        except:
                            field_value = ''
   
                inp = forms.TextInput(final_attrs)
                #try:
                rendered_inp = inp.render(final_attrs['name'], field_value, final_attrs)
                #except:
                #    rendered_inp = inp.render(name, '', final_attrs)
                output.append(u'<li><div style="display:block; font-size:14px;">%s %s</div></li>' % (rendered_cb, rendered_inp))
            else:
                cb = forms.CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
                option_value = force_text(option_value)
                rendered_cb = cb.render(name, option_value)
                option_label = conditional_escape(force_text(option_label))
                output.append(u'<li><label%s>%s %s</label></li>' % (label_for, rendered_cb, option_label))
        output.append(u'</ul>')
        return mark_safe(u'\n'.join(output))

    def id_for_label(self, id_):
        # See the comment for RadioSelect.id_for_label()
        if id_:
            id_ += '_0'
        return id_
    id_for_label = classmethod(id_for_label)


class RadioInput(StrAndUnicode):
    """
    An object used by RadioFieldRenderer that represents a single
    <input type='radio'>.
    """

    def __init__(self, ballot_json, name, value, attrs, choice, index):
        self.name, self.value = name, value
        self.attrs = attrs
        self.choice_value = force_text(choice[0])
        self.choice_label = force_text(choice[1])
        self.index = index
        self.ballot_json = ballot_json

    def __unicode__(self):
        if 'id' in self.attrs:
            label_for = ' for="%s_%s"' % (self.attrs['id'], self.index)
        else:
            label_for = ''
        choice_label = conditional_escape(force_text(self.choice_label))
        if choice_label == str(999):
            radio_inp = mark_safe(u'<div style="display:block;font-size:14px;">%s' % (self.tag()))

            # build an INPUT element
            post_key = self.name + '_write_in'
            self.attrs['id'] = post_key
            try:
                new_value = self.ballot_json[post_key]
            except:
                try:
                    new_value = self.ballot_json[self.name]['answer_eng'][0]
                except:
                    if self.value:
                        try:
                            dic = ast.literal_eval(self.value)
                            if "answer_eng" in dic:
                                new_value = dic["answer_eng"][0]
                            else:
                                new_value = self.value
                        except:
                            new_value = self.value
                    else:
                        new_value = ''
            inp = forms.TextInput(self.attrs)        
            rendered_inp = inp.render(post_key, new_value, self.attrs)          
            return mark_safe(u'%s %s</div>' % (radio_inp, rendered_inp))
        else:
            return mark_safe(u'<label%s>%s %s</label>' % (label_for, self.tag(), choice_label))

    def is_checked(self):
        return self.value == self.choice_value

    def tag(self):
        if 'id' in self.attrs:
            self.attrs['id'] = '%s_%s' % (self.attrs['id'], self.index)
        final_attrs = dict(self.attrs, type='radio', name=self.name, value=self.choice_value)
        if self.is_checked():
            final_attrs['checked'] = 'checked'
        return mark_safe(u'<input%s />' % flatatt(final_attrs))


class RadioFieldRenderer(StrAndUnicode):
    """
    An object used by RadioSelect to enable customization of radio widgets.
    """

    def __init__(self, ballot_json, name, value, attrs, choices):
        self.name, self.value, self.attrs = name, value, attrs
        self.choices = choices
        self.ballot_json = ballot_json

    def __iter__(self):
        for i, choice in enumerate(self.choices):
            yield RadioInput(self.ballot_json, self.name, self.value, self.attrs.copy(), choice, i)

    def __getitem__(self, idx):
        choice = self.choices[idx] # Let the IndexError propagate
        return RadioInput(self.ballot_json, self.name, self.value, self.attrs.copy(), choice, idx)

    def __unicode__(self):
        return self.render()

    def render(self):
        """Outputs a <ul> for this set of radio fields."""
        return mark_safe(u'<ul>\n%s\n</ul>' % u'\n'.join([u'<li>%s</li>'
                                                          % force_text(w) for w in self]))


class RadioSelectCustom(forms.Select):
    renderer = RadioFieldRenderer

    def __init__(self, ballot_json, *args, **kwargs):
        # Override the default renderer if we were passed one.
        renderer = kwargs.pop('renderer', None)
        self.ballot_json = ballot_json
        if renderer:
            self.renderer = renderer
        super(RadioSelectCustom, self).__init__(*args, **kwargs)

    def get_renderer(self, name, value, attrs=None, choices=()):
        """Returns an instance of the renderer."""
        if value is None: value = ''
        str_value = force_text(value) # Normalize to string.
        final_attrs = self.build_attrs(attrs)
        choices = list(chain(self.choices, choices))
        return self.renderer(self.ballot_json, name, str_value, final_attrs, choices)

    def render(self, name, value, attrs=None, choices=()):
        return self.get_renderer(name, value, attrs, choices).render()

    def id_for_label(self, id_):
        # RadioSelect is represented by multiple <input type="radio"> fields,
        # each of which has a distinct ID. The IDs are made distinct by a "_X"
        # suffix, where X is the zero-based index of the radio field. Thus,
        # the label for a RadioSelect should reference the first one ('_0').
        if id_:
            id_ += '_0'
        return id_
    id_for_label = classmethod(id_for_label)


class PINForm(forms.Form):
    pin = forms.CharField(max_length=20, label=_("Please enter your ballot PIN"))

    def __init__(self, request, *args, **kwargs):
        self.pin = request.session.get('pin')
        self.election = None
        self.request = request
        super(PINForm, self).__init__(*args, **kwargs)
        try:
            election = Election.objects.select_related().get(pk=self.request.session.get('election_id'))
            asset = Asset.objects.get(election=election)
            self.default_phone = asset.default_phone
        except Election.DoesNotExist:
            self.default_phone = settings.SUPPORT_PHONE

    def clean_pin(self):
        if self.cleaned_data['pin']:
            try:
                pin = PIN.objects.get(pin=self.cleaned_data['pin'])
                self.pin = pin
                self.election = pin.election
            except PIN.DoesNotExist:
                raise forms.ValidationError(mark_safe(u"It doesn't appear that \
                this is a valid PIN. If you feel you have reached this point \
                in error please contact us at "+self.default_phone))
            
            try:
                result = Log.objects.get(pin=pin.pin)
            except Log.DoesNotExist:
                pass
            else:
                logging.debug("Duplicate vote request inside of form--denied creating ballot for %s" % (self.cleaned_data['pin']))
                raise forms.ValidationError(u"PIN %s has already voted \
                    in this election - " % (self.cleaned_data['pin']))
            
            try:
                result = Mail_Log.objects.get(pin=pin.pin)
            except Mail_Log.DoesNotExist:
                pass
            else:
                logging.debug("Duplicate vote request inside of form from mail ballots--denied creating ballot for %s" % (self.cleaned_data['pin']))
                raise forms.ValidationError(u"PIN %s has already voted \
                    in this election or your mail ballot has been processed." % (self.cleaned_data['pin']))

            return self.cleaned_data['pin']


class ValidateForm(forms.Form):
    value = forms.CharField()

    def __init__(self, *args, **kwargs):
        
        if 'answer' in kwargs:
            self._answer = kwargs['answer']
            del(kwargs['answer'])

        return super(ValidateForm, self).__init__(*args, **kwargs)
    
    def clean_value(self):
        value = self.cleaned_data['value']
        
        if not value == self._answer:
            raise forms.ValidationError("We're sorry but that does not match our records")


class BallotForm(forms.Form):
    """
    This is a dynamic form that requires a ballot to be given on __init__(). 
    Each question becomes a field (either a ChoiceField or MultipleChoiceField,
    depending on if more than one answer is allowed).
    
    All fields are required. 
    
    Results are saved to the DB as JSON with English labels cached for both reports
    and the confirmation page.
    """

    def __init__(self, *args, **kwargs):

        self.pin = kwargs.pop('ballot_pin')
        self.posted = dict(*args)

        self.ballot = kwargs.pop('ballot')
        self.ballot_json = kwargs.pop('ballot_jn') # ballot_json["initial"][question_id]["answer_eng"]
        if not self.ballot_json:
            try:
                self.ballot_json = args[0]
            except:
                self.ballot_json = self.ballot_json
        
        super(BallotForm, self).__init__(*args, **kwargs)

        self.hasErrors = False
        
        self.questions = Question.objects.filter(ballot=self.ballot).order_by('ballot_question__order')
        self.choices = Choice.objects.select_related().filter(question__election=self.ballot.election)
        self.setup()
    
    def setup(self):
        """
        Store choices in a reverse lookup so we can economically fetch a choice by its id
        
        Then we loop through again and set up the field options and actually create the field
        """
        self.choices_reverse = {}
        
        for c in self.choices:
            self.choices_reverse[str(c.id)] = c

        for q in self.questions:

            opts = {}
            
            if q.max_responses == 1: # or q.min_responses == 0:
                opts['label'] = '%s (Choose %d)' % (q.question, q.max_responses)
            else:
                opts['label'] = '%s (Choose up to %d)' % (q.question, q.max_responses)
            
            choices = []
            
            for c in self.choices:
                if c.question == q:
                    """
                    If the c.order == 999, then this is a write-in so we need to set the proper tags, etc.
                    """
                    if c.order == 999:
                        c.answer = 999
                    choices.append((c.id, c.answer))
            
            """
            If a radio button question (max responses = 1) is optional, provide a
            way for the user to back out of a selection (since you can uncheck a
            radio button)
            """
            if q.max_responses == 1 and q.min_responses == 0:
                choices.append((0, 'Skip This Contest'))
            
            opts['choices'] = choices
            
            self.fields[str(q.id)] = self.decide_field(q, opts)
    
    def decide_field(self, question, opts):
        """
        Choose the field type and widget based on the max_responses value.
        One response allowed becomes a radio, multiple become check boxes.
        """

        opts['required'] = False
        
        if question.max_responses == 1: 
            opts['widget'] = RadioSelectCustom(self.ballot_json)
            return forms.ChoiceField(**opts)
        else:
            opts['widget'] = CheckboxSelectMultipleCustom(self.ballot_json)
            return forms.MultipleChoiceField(**opts)

    def clean(self):
        """
        Loop through the answers and make sure that the supplied data lines up with
        the required number of answers.
        """
        for q in self.questions:

            data = self.cleaned_data.get(str(q.id), False)

            if q.min_responses > 0 and not data:
                self._errors[str(q.id)] = self.error_class(["You must select an option to continue"])
                self.hasErrors = True

            if q.min_responses == 0 and q.max_responses == 1 and not data:
                self._errors[str(q.id)] = self.error_class(["You must select an option to continue"])
                self.hasErrors = True
            
            if data and q.max_responses > 1:
                question_value = self.cleaned_data[str(q.id)]
                if len(question_value) > q.max_responses:
                    self._errors[str(q.id)] = ErrorList(['You may only select at most %d choices' % q.max_responses])
                    self.hasErrors = True
        return self.cleaned_data
    
    def save(self, commit=True):
        """
        Cast the vote to the DB. Answers are stored as JSON:
        
        choices = [question_id:{'question': question,
                                'answer': answer,
                                'answer_eng': "answer readable"}]
        """
        choices = {}
        for q in self.questions:
            answer_eng = []

            # response is either a stringed integer or a list/tuple
            response = self.cleaned_data[str(q.id)]
            
            # if hasattr(response, '__iter__'):
            if type(response) is list or type(response) is tuple:
                for a in response:
                    if self.choices_reverse[a].answer == 999:
                        post_key = str(q.id) + '_write_in'
                        try:
                            answer_eng.append(self.ballot_json.__getitem__(post_key))
                        except:
                            answer_eng.append('')
                    else:
                        answer_eng.append(self.choices_reverse[a].answer)
                                    
            else:
                if not response == "0":
                    if self.choices_reverse[response].answer == 999:
                        post_key = str(q.id) + '_write_in'
                        try:
                            answer_eng.append(self.ballot_json.__getitem__(post_key))
                        except:
                            answer_eng.append('')
                    else:
                        answer_eng.append(self.choices_reverse[response].answer)
                    self.cleaned_data[str(q.id)] = [response]
            
            if not response == "0":
                choices[q.id] = {   'question': q.question, 
                                    'answer': response,
                                    'answer_eng': answer_eng}

        if commit:
            newValue = self.ballot_json.copy()
            logging.debug(newValue)

            # if self.ballot.election.enable_cast_vote_record == 1:
            if self.ballot.election.logic_and_accuracy == 1:
                return Vote.objects.create(election=self.ballot.election,
                                            ballot=self.ballot,
                                            choices=json.dumps(choices),
                                            pin=self.pin)
            else:
                return Vote.objects.create(election=self.ballot.election,
                                            ballot=self.ballot,
                                            choices=json.dumps(choices))

        else:
            return choices


class VerifyForm(forms.Form):
    confirmation_number = forms.CharField(label='Confirmation code')
    
    def clean_confirmation_number(self):
        
        data = self.cleaned_data
        
        confirmation_number = data.get('confirmation_number')
        
        try:
            v = Vote.objects.get(confirmation=confirmation_number)
        except Vote.DoesNotExist:
            raise forms.ValidationError("We do not have a record of that vote, please make sure you gave us \
            the confirmation code exactly as it was displayed")
        else:
            self.vote = v
        
        return data




