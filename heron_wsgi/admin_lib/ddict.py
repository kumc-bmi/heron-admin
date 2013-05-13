class DataDict(object):
    '''
    .. todo:: use pkg_resources rather than os to get redcap_dd
    '''
    def __init__(self, name,
                 respath='../redcap_dd/', suffix='.csv'):
        import pkg_resources

        def open_it():
            return pkg_resources.resource_stream(
                __name__, respath + name + suffix)
        self._open = open_it

    def fields(self):
        import csv
        rows = csv.DictReader(self._open())
        for row in rows:
            yield row["Variable / Field Name"], row

    def radio(self, field_name):
        for n, row in self.fields():
            if n == field_name:
                choicetxt = row["Choices, Calculations, OR Slider Labels"]
                break
        else:
            raise KeyError
        return [tuple(choice.strip().split(", ", 1))
                for choice in choicetxt.split('|')]
