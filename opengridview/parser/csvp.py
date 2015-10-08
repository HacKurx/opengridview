from opengridview.parser import Parser
import csv

class ParserCsv(Parser):

  def __init__(self,config):
    Parser.__init__(self,config) # Base
    self.headers = None
    self.header_names = None
    if config.has_key('headers'):
      self.header_names = config['headers']

  def read_stream(self, stream, item_func, header_func):
    while True:
      line = stream.readline()
      if line:
        if self.config.has_key('separator'):
          reader = csv.reader([line],delimiter=self.config['separator'])
        else:
          reader = csv.reader([line])
        row = reader.next()
        if not self.headers:
          if not self.header_names:
            # This is the first row. Use it to set header names
            self.header_names = row
            continue # Don't process as input
          else:
            # This is the first value row. Use it to set headers with values
            # TODO handle types nicer http://stackoverflow.com/a/32397436
            val_types = [type(i) for i in row]
            val_types = self.inflate_truncate(val_types,len(self.header_names))
            self.headers = zip(self.header_names,val_types)
            header_func(self.headers)
        row = self.inflate_truncate(row,len(self.headers))
        item_func(row)
      else:
        break
