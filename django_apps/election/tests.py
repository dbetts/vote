import unittest
from django.test.client import Client
from election.models import Election, PIN, Log, PhoneSession, Ballot

class PhoneCase(unittest.TestCase):

    def setUp(self):
        self.c = Client()
        self.data = None
        self.url = '/phone/'
        Election.objects.create(name='Demo')
        
    def post(self):
        return self.c.post(self.url, self.data, 'text/xml')

    def testStartCall(self):
        self.data = '<?xml version="1.0"?><campaign menuid="33588-583950220" callid="123" action="5" duration="5"/>'
        result = self.post()
        self.assertEquals(result.content, '')

    def testPINCall(self):
        PIN.objects.create(id='1234', election_id=1)
        self.data = '<?xml version="1.0"?><prompt menuid="33588-583950220" callid="123" promptid="3" keypress="1234#"/>'
        result = self.post()
        self.assertEquals(result.content, '<prompt goto="22"/>')
    
    def testVote(self):
        self.data = '<?xml version="1.0"?><prompt menuid="33588-583950220" callid="123" promptid="3" keypress="1"/>'
        result = self.post()
        self.assertEquals(result.content, '<prompt goto="23"/>')
