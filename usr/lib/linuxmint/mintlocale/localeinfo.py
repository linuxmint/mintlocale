#!/usr/bin/python3
"""Names and flags of the locales, as the mintlocale windows show them"""

import os

DATA_DIR = "/usr/share/linuxmint/mintlocale"
FLAG_PATH = "/usr/share/iso-flag-png/%s.png"

# Languages shown with a regional flag rather than with the flag of their country
LANGUAGE_FLAGS = {
    "ca": "_catalonia",
    "cy": "_wales",
    "eu": "_basque",
    "gl": "_galicia",
}


def _load_names(file_name):
    names = {}
    with open(os.path.join(DATA_DIR, file_name), "r", encoding="utf-8") as names_file:
        for line in names_file:
            split = line.strip().split("=")
            if len(split) == 2:
                names[split[0]] = split[1]
    return names


class LocaleInfo:

    def __init__(self):
        self.languages = _load_names("languages")
        self.countries = _load_names("countries")

    def split_locale(self, locale_code):
        """The language code, country code and label of a locale code such as pt_BR or sr_RS@latin"""
        if "_" in locale_code:
            split = locale_code.split("_")
            language_code = split[0]
            language = self.languages.get(language_code, language_code)

            country_code = split[1].lower().split('@')[0].strip()
            country = self.countries.get(country_code, country_code)

            if '@' in split[1]:
                language_label = "%s (@%s), %s" % (language, split[1].split('@')[1].strip(), country)
            else:
                language_label = "%s, %s" % (language, country)
        else:
            language_label = self.languages.get(locale_code, locale_code)
            language_code = locale_code
            country_code = ""

        return (language_code, country_code, language_label)

    def get_flag_path(self, language_code, country_code):
        """The flag of a locale, or the generic one when there is none"""
        if language_code in LANGUAGE_FLAGS:
            flag_path = FLAG_PATH % LANGUAGE_FLAGS[language_code]
        elif country_code != "":
            flag_path = FLAG_PATH % country_code
        else:
            flag_path = FLAG_PATH % language_code

        if not os.path.exists(flag_path):
            flag_path = FLAG_PATH % "_generic"
        return flag_path
