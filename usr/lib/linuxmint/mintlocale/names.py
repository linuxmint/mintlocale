#!/usr/bin/python3
"""Language and country names for the locale lists.

The names come from /usr/share/linuxmint/mintlocale/{languages,countries},
which are in English. A name is translated through iso-codes only when
iso-codes has the same English name for the code and the translation is not
given to another code as well; otherwise the English name from the file stays.
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


def _capitalize(text):
    return text[:1].upper() + text[1:]


def _translations(names, iso_names, domain):
    try:
        translation = gettext.translation(domain)
    except OSError:
        return {}
    # Some translations in iso-codes are wrong and repeat the name of another entry
    owners = {}
    for entry, msgids in set(iso_names.values()):
        for msgid in msgids:
            if msgid:
                owners.setdefault(_capitalize(translation.gettext(msgid)), set()).add(entry)
    translated = {}
    for code, name in names.items():
        entry, msgids = iso_names.get(code, (None, ()))
        # A name such as "Spanish; Castilian" matches "Spanish"
        matches = [msgid for msgid in msgids if msgid in [name] + name.split("; ")]
        if matches:
            text = _capitalize(translation.gettext(matches[0]))
            if text not in (name, matches[0]) and owners[text] == {entry}:
                translated[code] = text
    return translated


def _translate(names, sources):
    translated = {}
    for iso_names, domain in reversed(sources):
        translated.update(_translations(names, iso_names, domain))
    # Keep the names apart: a translation must not be the name of another code
    texts = {}
    for code, text in dict(names, **translated).items():
        texts.setdefault(text, set()).add(names[code])
    return {code: translated[code] if code in translated and len(texts[translated[code]]) == 1 else name
            for code, name in names.items()}


def _language_names(standard):
    iso_names = {}
    for entry in _iso_entries(standard):
        for key in ("alpha_3", "alpha_2"):
            if key in entry:
                iso_names[entry[key]] = (entry["alpha_3"], (entry["name"],))
    return iso_names


def load_languages():
    # ISO 639-3 has the shorter names, 639-2 the ones of the file it lacks
    names = _read_list("%s/languages" % DATA_DIR)
    return _translate(names, [(_language_names(standard), "iso_%s" % standard) for standard in ("639-3", "639-2")])


def load_countries():
    names = _read_list("%s/countries" % DATA_DIR)
    iso_names = {}
    for entry in _iso_entries("3166-1"):
        iso_names[entry["alpha_2"].lower()] = (entry["alpha_2"], (entry.get("common_name"), entry["name"]))
    return _translate(names, [(iso_names, "iso_3166-1")])
