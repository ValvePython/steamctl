
import re

def pmt_confirmation(text, default_yes=None):

    while True:
        response = input("{} [{}/{}]: ".format(
            text,
            'YES' if default_yes == True else 'yes',
            'NO' if default_yes == False else 'no',
            )).strip()

        if not response:
            if default_yes is not None:
                return default_yes
            else:
                continue
        elif response.lower() in ('y', 'yes'):
            return True
        elif response.lower() in ('n', 'no'):
            return False

def pmt_input(text, regex=None, nmprefix='Invalid input.'):
    while True:
        response = input("{} ".format(text.rstrip(' ')))

        if regex and not re.search(regex, response):
            print(nmprefix, '', end='')
            continue

        return response

