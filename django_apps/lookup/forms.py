from django import forms
from django.contrib.localflavor.us.forms import USPhoneNumberField
from django.core.mail import mail_managers
from django.template import Context
from django.template.loader import get_template

class LookupForm(forms.Form):
    name = forms.CharField()
    phone = USPhoneNumberField()
    email = forms.EmailField()
    last_4 = forms.IntegerField()
    
    def clean_last_4(self):
        data = self.cleaned_data
        
        if data['last_4'] < 1000 or data['last_4'] > 9999:
            raise forms.ValidationError("Please enter 4 digits")
        
        return data['last_4']
    
    def save(self):
        template = get_template('lookup/email.html')
        context = Context({'data': self.cleaned_data})
        mail_managers('Aloha PIN request', template.render(context))