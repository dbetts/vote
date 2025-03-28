from django.db import models
from django.conf import settings

import random
import datetime
import uuid

class PIN(models.Model):
    pin = models.CharField(max_length=20)
    ballot = models.ForeignKey('Ballot')
    election = models.ForeignKey('Election')
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=200, blank=True, null=True)
    validation_start = models.CharField(max_length=20, blank=True, null=True)
    validation_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):  # def __unicode__(self):
        return "%s" % self.pin
        
    class Meta:
        verbose_name = "PIN"


class Invalid_Response(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    identification = models.CharField(max_length=100)
    digits = models.CharField(max_length=100)

    def __str__(self):  # def __unicode__(self):
        return "%s - %s" % (self.identification, self.created_at)

   
def election_file_location(instance, filename):
    return "audio/%d/%s" % (instance.id, filename)

def image_file_location(instance, filename):
    folder = datetime.datetime.strftime(instance.election.create_date, "%B_%Y")
    return "%s/%d/%s" % (folder, instance.election.id, filename)


class Election(models.Model):
    name = models.CharField(max_length=100)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    create_date = models.DateTimeField(auto_now_add=True)

    # enable_cast_vote_record = models.BooleanField()
    logic_and_accuracy = models.BooleanField()
    live_election = models.BooleanField()

    audio_start = models.FileField(upload_to=election_file_location, 
                        blank=True, 
                        null=True)
        
    audio_end = models.FileField(upload_to=election_file_location, 
                        blank=True, 
                        null=True)
    
    audio_finished = models.FileField(upload_to=election_file_location, 
                        blank=True, 
                        null=True,
                        help_text="You have finished voting, to cast your ballot please \
                        press 1 followed by the pound key.")
    
    audio_repeat = models.FileField(upload_to=election_file_location, 
                                        blank=True, 
                                        null=True,
                                        help_text="To repeat this question press *#")
        
    audio_invalid_response = models.FileField(upload_to=election_file_location, 
                        blank=True, 
                        null=True,
                        help_text="We're sorry, but the digits you entered are an invalid response.")
        
    audio_error = models.FileField(upload_to=election_file_location, 
                        blank=True, 
                        null=True,
                        help_text="We're sorry, but there has been an error. Please call back later.")
    
    audio_if_done = models.FileField(upload_to=election_file_location, 
                        blank=True,
                        null=True,
                        help_text="For multiple response questions, (99#)")
    
    audio_privacy = models.FileField(upload_to=election_file_location, 
                        blank=True, 
                        null=True,
                        help_text="Info about voting system privacy")
    
    audio_pin = models.FileField(upload_to=election_file_location, 
                    blank=True, 
                    null=True,
                    help_text="To begin the voting process please enter your PIN followed by the pound key.")
                    
    audio_already_voted = models.FileField(upload_to=election_file_location, 
                    blank=True, 
                    null=True,
                    help_text="We're sorry, but the entered PIN has already voted in this election.")
    
    audio_if_banned = models.FileField(upload_to=election_file_location,
                        blank=True,
                        null=True,
                        help_text="We're sorry, it looks like are having trouble entering your PIN")

    def __str__(self): # was changed from __unicade__() to __str__()
        return self.name
    
    def active(self):
        now = datetime.datetime.today()
        
        if (not self.start_time or now > self.start_time) and (not self.end_time or now < self.end_time):
            return True
        
        return False
    
    def active_election(self):
        
        status = 'no'
        
        if self.active():
            status = 'yes'
            
        return '<img alt="0" src="%simg/admin/icon-%s.gif"/>' % (settings.ADMIN_MEDIA_PREFIX, status)
    
    active_election.allow_tags = True
    
    @property
    def phone_vote_count(self):
        return self.vote_set.filter(phone=True).count()
    
    @property
    def web_vote_count(self):
        return self.vote_set.filter(phone=False).count()


class Log(models.Model):
    election    = models.ForeignKey(Election)
    pin         = models.ForeignKey(PIN) #models.IntegerField() #ForeignKey(PIN)
    time        = models.DateTimeField(auto_now_add=True)

    def __str__(self):  # def __unicode__(self):
        return "%s" % self.pin
    
    def save(self, *args, **kwargs):
        
        try:
            Mail_Log.objects.get(pin=self.pin)
        except Mail_Log.DoesNotExist:
            pass
        else:
            raise Exception("%s is already in the mail vote log" % self.pin)
        
        try:
            Log.objects.get(pin=self.pin)
        except Log.DoesNotExist:
            pass
        else:
            raise Exception("%s is already in the vote log" % self.pin)
        
        super(Log, self).save(*args, **kwargs)


class Mail_Log(models.Model):
    election    = models.ForeignKey(Election)
    pin         = models.ForeignKey(PIN) # IntegerField()
    time        = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Mail Ballot Log'

    def __str__(self):  # def __unicode__(self):
        return "%s" % self.pin
    
    def save(self, *args, **kwargs):
        
        try:
            Log.objects.get(pin=self.pin)
        except Log.DoesNotExist:
            pass
        else:
            raise Exception("%s is already in the vote log" % self.pin)

        try:
            Mail_Log.objects.get(pin=self.pin)
        except Mail_Log.DoesNotExist:
            pass
        else:
            raise Exception("%s is already in the mail vote log" % self.pin)
        
        super(Mail_Log, self).save(*args, **kwargs)


def ballot_file_location(instance, filename):
    return "audio/%d/ballots/%d/%s" % (instance.election.id, instance.id, filename)

class Ballot(models.Model):
    election = models.ForeignKey(Election)
    name = models.CharField(max_length=100)
    questions = models.ManyToManyField('Question', through='Ballot_Question')
    audio = models.FileField(upload_to=ballot_file_location, blank=True, null=True)

    def __str__(self):  # def __unicode__(self):
        return self.name


def question_file_location(instance, filename):
    return "audio/%d/question/%d/%s" % (instance.election.id, instance.id, filename)
  
class Question(models.Model):
    election = models.ForeignKey(Election)
    question = models.TextField()
    max_responses = models.IntegerField('Max responses')
    min_responses = models.IntegerField('Min responses', default=1)
    choices = models.ManyToManyField('Choice', 
        null=True, 
        blank=True,
        related_name='question_choices')
    audio = models.FileField(upload_to=question_file_location, blank=True, null=True)

    def __str__(self):  # def __unicode__(self):
        return self.question


def choice_file_location(instance, filename):
    return "audio/%d/choice/%d/%s" % (instance.question.election.id, instance.id, filename)
        
class Choice(models.Model):
    question = models.ForeignKey(Question)
    answer = models.TextField()
    order = models.IntegerField()
    audio_choice = models.FileField(upload_to=choice_file_location, blank=True, null=True)
    audio_confirm = models.FileField(upload_to=choice_file_location, blank=True, null=True)
    phone_option = models.IntegerField(blank=True, null=True)
    
    class Meta:
        ordering = ('order',)

    def __str__(self):  # def __unicode__(self):
        return "%s (%s)" % (self.answer, self.question)


class Ballot_Question(models.Model):
    question = models.ForeignKey(Question)
    ballot = models.ForeignKey(Ballot)
    order = models.IntegerField()
    
    class Meta:
        ordering = ('order',)
        verbose_name = 'Ballot Question'
        verbose_name_plural = 'Ballot Questions'

    def __str__(self):  # def __unicode__(self):
        return self.question.question

           
class Vote(models.Model):
    uuid            = models.CharField(max_length=100, editable=False)
    confirmation    = models.CharField(max_length=50, editable=False)
    election        = models.ForeignKey(Election)
    ballot          = models.ForeignKey(Ballot)
    choices         = models.TextField()
    phone           = models.BooleanField(default=False)
    pin             = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):  # def __unicode__(self):
        return "%s" % self.confirmation
        
    def save(self, *args, **kwargs):
        """
        Votes are tagged with both a UUID and confirmation number. The 
        UUID is meant for URLs and confirmation is meant for people to
        input. The UUID changes every time the record is publicly viewed.
        """
        
        if not self.confirmation:
            self.confirmation = str(random.random())[2:10]
            
        if not self.uuid:
            self.uuid = uuid.uuid1()
            
        super(Vote, self).save(*args, **kwargs)
        
    def reset_uuid(self):
        self.uuid = uuid.uuid1()
        self.save()


class Phone_Session(models.Model):
    uuid        = models.CharField(max_length=100)
    time        = models.DateTimeField(auto_now_add=True)
    election    = models.ForeignKey(Election)
    pin         = models.ForeignKey(PIN)
    next_question = models.ForeignKey(Question, null=True)


class Phone_Choice(models.Model):
    session     = models.ForeignKey(Phone_Session)
    time        = models.DateTimeField(auto_now_add=True)
    question    = models.ForeignKey(Question)
    choice      = models.ForeignKey(Choice)


class Asset(models.Model):
    election        = models.OneToOneField(Election)
    sub_domain      = models.CharField(max_length=64, editable=True)
    default_phone   = models.CharField(max_length=16, editable=True)
    default_email   = models.CharField(max_length=64, editable=True)
    vote_phone      = models.CharField(max_length=16, editable=True, blank=True, null=True)
    header_image    = models.FileField(upload_to=image_file_location, blank=True, null=True)
    validation_text = models.CharField(max_length=1024, editable=True)
    ballot_extra    = models.TextField(editable=True)
    exit_url        = models.CharField(max_length=1024, editable=True)

    def __str__(self):  # def __unicode__(self):
        return "%s (%s)" % (self.default_phone, self.default_email)


