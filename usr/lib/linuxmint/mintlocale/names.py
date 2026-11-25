#!/usr/bin/python3
"""Language and country names for the locale lists.

The names come from /usr/share/linuxmint/mintlocale/{languages,countries},
which are in English. Where iso-codes has a translation of the name into the
interface language, that translation is used instead; otherwise the English
name from the file stays, so an English interface looks exactly as before.
"""

import gettext
import json

DATA_DIR = "/usr/share/linuxmint/mintlocale"
ISO_DIR = "/usr/share/iso-codes/json"


def _read_list(path):
    names = {}
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            split = line.strip().split("=")
            if len(split) == 2:
                names[split[0]] = split[1]
    return names


def _iso_entries(standard):
    try:
        with open("%s/iso_%s.json" % (ISO_DIR, standard), "r", encoding="utf-8") as file:
            return json.load(file)[standard]
    except (OSError, ValueError, KeyError):
        return []


def _translate(domain, msgid):
    try:
        translation = gettext.translation(domain)
    except OSError:
        return None
    text = translation.gettext(msgid)
    if text == msgid:
        return None
    return text[:1].upper() + text[1:]


def load_languages():
    names = _read_list("%s/languages" % DATA_DIR)
    by_code = {}
    for entry in _iso_entries("639-3"):
        by_code[entry["alpha_3"]] = entry["name"]
        if "alpha_2" in entry:
            by_code[entry["alpha_2"]] = entry["name"]
    for code in names:
        if code in by_code:
            names[code] = _translate("iso_639-3", by_code[code]) or names[code]
    return names


def load_countries():
    names = _read_list("%s/countries" % DATA_DIR)
    by_code = {}
    for entry in _iso_entries("3166-1"):
        by_code[entry["alpha_2"].lower()] = entry.get("common_name", entry["name"])
    for code in names:
        if code in by_code:
            names[code] = _translate("iso_3166-1", by_code[code]) or names[code]
    return names
