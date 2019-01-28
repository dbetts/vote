import re

class PostToDictMiddleware(object):
    """
    Enables dictionaries to be used as POST/GET input similar to PHP. This 
    middleware automatically detects and re-encodes any available input.
    
    Example:
    
    <input name="example_dict[key]" value="value" />
    
    Normally this would have to be accessed by the full name: example_dict[key]
    but using this middleware that value is replaced by a dictionary named 
    example_dict that has a key named "key" and a value of "value".
    
    >>> example_dict = request.REQUEST[example_dict]
    >>> print example_dict[key]
    value
    
    """
    def __init__(self):
        
        self.dict_re = re.compile('([a-zA-Z][a-zA-Z0-9_]+)\[([a-zA-Z0-9_-]+)\]')
    
    def map(self, data):
        
        if not data:
            return data
        
        #The POST/GET QueryDicts can be immutable at times, so we record the
        #mutability, set it to be mutable and then reset it to the original
        #value before the end of processing
        orig_mutable_val = data._mutable
        data._mutable = True
        
        for k,v in data.items():
            
            var = self.dict_re.match(k)
            
            if var:
                if not var.group(1) in data:
                    data[var.group(1)] = {}
                    
                try:
                    data[var.group(1)][var.group(2)] = v
                except TypeError:
                    #This occurs when the form has a field named the same as 
                    #the intended dict. We ignore processing in that instance 
                    #so as to not delete data.
                    return data
                    
                del(data[k])
        
        data._mutable = orig_mutable_val
        
        return data
                    
    def process_request(self, request):
        
        request.POST = self.map(request.POST)
        request.GET = self.map(request.GET)
            
        return None
