import csv


class DataDict(object):
    @classmethod
    def from_csv(cls, fp):
        return cls(list(csv.DictReader(fp)))

    def __init__(self, rows):
        self.rows = rows

    def fields(self):
        for row in self.rows:
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
