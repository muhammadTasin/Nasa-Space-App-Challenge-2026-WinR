"""Convert Bangla typed in the legacy Bijoy / SutonnyMJ encoding to Unicode.

BARI and BRRI publications set Bangla in Bijoy fonts (SutonnyMJ, MeghnaMJ, ...): the PDF text layer holds ASCII and
Latin-1 look-alikes ("K…wl" = krishi), one code per glyph. Conversion maps each glyph code to Unicode, then moves
the vowel signs typed before their consonant (i, e, oi) after it and the reph typed after its consonant before it.
This follows the table and reordering of the common open-source Bijoy converters; only text in a Bijoy font
should be passed in (English set in Times New Roman would be garbled). Digits are kept as ASCII so numbers stay
machine-readable.

Usage: from bijoy import to_unicode; to_unicode("K…wl cÖhyw³ nvZeB") -> "কৃষি প্রযুক্তি হাতবই"
"""
from __future__ import annotations

import re
import unicodedata

HALANT = "্"
KARS = set("ািীুূৃেৈোৌৗ")
PRE_KARS = set("িেৈ")  # i, e, oi: typed before the consonant in Bijoy
POST_KARS = KARS - PRE_KARS
CONSONANTS = set("কখগঘঙচছজঝঞটঠডঢণতথদধনপফবভমযরলশষসহৎড়ঢ়য়")

# glyph code -> Unicode; conjunct glyphs first (matched longest-first below)
MAP = {
    "i¨": "র‍্য", "ª¨": "্র্য", "°": "ক্ক", "±": "ক্ট", "³": "ক্ত", "K¡": "ক্ব", "¯Œ": "স্ক্র", "µ": "ক্র",
    "K¬": "ক্ল", "¶": "ক্ষ", "ÿ": "ক্ষ", "·": "ক্স", "¸": "গু", "»": "গ্ধ", "Mœ": "গ্ন", "M¥": "গ্ম", "Mø": "গ্ল",
    "Mªy": "গ্রু", "¼": "ঙ্ক", "•¶": "ঙ্ক্ষ", "•L": "ঙ্খ", "½": "ঙ্গ", "•N": "ঙ্ঘ", "”P": "চ্চ", "”Q": "চ্ছ",
    "”Q¡": "চ্ছ্ব", "”T": "চ্ঞ", "¾¡": "জ্জ্ব", "¾": "জ্জ", "À": "জ্ঝ", "Á": "জ্ঞ", "R¡": "জ্ব", "Â": "ঞ্চ",
    "Ã": "ঞ্ছ", "Ä": "ঞ্জ", "Å": "ঞ্ঝ", "Æ": "ট্ট", "U¡": "ট্ব", "U¥": "ট্ম", "Ç": "ড্ড", "È": "ণ্ট", "É": "ণ্ঠ",
    "Ý": "ন্স", "Ð": "ণ্ড", "š‘": "ন্তু", "Y^": "ণ্ব", "Ë": "ত্ত", "Ë¡": "ত্ত্ব", "Ì": "ত্থ", "Z¥": "ত্ম",
    "š—¡": "ন্ত্ব", "Z¡": "ত্ব", "Î": "ত্র", "_¡": "থ্ব", "˜M": "দ্গ", "˜N": "দ্ঘ", "Ï": "দ্দ", "×": "দ্ধ",
    "˜¡": "দ্ব", "Ø": "দ্ব", "™¢": "দ্ভ", "Ù": "দ্ম", "`ª": "দ্র", "aŸ": "ধ্ব", "a¥": "ধ্ম", "›U": "ন্ট",
    "Ú": "ন্ঠ", "Û": "ন্ড", "šÍ": "ন্ত", "š—": "ন্ত", "š¿": "ন্ত্র", "š’": "ন্থ", "›`": "ন্দ", "›Ø": "ন্দ্ব",
    "Ü": "ন্ধ", "bœ": "ন্ন", "š^": "ন্ব", "b¥": "ন্ম", "Þ": "প্ট", "ß": "প্ত", "cœ": "প্ন", "à": "প্প",
    "c­": "প্ল", "á": "প্স", "d¬": "ফ্ল", "â": "ব্জ", "ã": "ব্দ", "ä": "ব্ধ", "eŸ": "ব্ব", "e­": "ব্ল",
    "å": "ভ্র", "gœ": "ম্ন", "¤ú": "ম্প", "ç": "ম্ফ", "¤^": "ম্ব", "¤¢": "ম্ভ", "¤£": "ম্ভ্র", "¤§": "ম্ম",
    "¤­": "ম্ল", "«": "্র", "iæ": "রু", "iƒ": "রূ", "é": "ল্ক", "ê": "ল্গ", "ë": "ল্ট", "ì": "ল্ড",
    "í": "ল্প", "î": "ল্ফ", "j¦": "ল্ব", "j¥": "ল্ম", "jø": "ল্ল", "ï": "শু", "ð": "শ্চ", "kœ": "শ্ন",
    "k¦": "শ্ব", "k¥": "শ্ম", "kø": "শ্ল", "®‹": "ষ্ক", "®Œ": "ষ্ক্র", "ó": "ষ্ট", "ô": "ষ্ঠ", "ò": "ষ্ণ",
    "®ú": "ষ্প", "õ": "ষ্ফ", "®§": "ষ্ম", "¯‹": "স্ক", "÷": "স্ট", "ö": "স্খ", "¯Í": "স্ত", "¯‘": "স্তু",
    "¯’": "স্থ", "mœ": "স্ন", "¯ú": "স্প", "ù": "স্ফ", "¯^": "স্ব", "¯§": "স্ম", "¯­": "স্ল", "û": "হু",
    "nè": "হ্ণ", "nŸ": "হ্ব", "ý": "হ্ন", "þ": "হ্ম", "n¬": "হ্ল", "ü": "হৃ", "©": "র্",
    "Av": "আ", "A": "অ", "B": "ই", "C": "ঈ", "D": "উ", "E": "ঊ", "F": "ঋ", "G": "এ", "H": "ঐ", "I": "ও", "J": "ঔ",
    "K": "ক", "L": "খ", "M": "গ", "N": "ঘ", "O": "ঙ", "P": "চ", "Q": "ছ", "R": "জ", "S": "ঝ", "T": "ঞ", "U": "ট",
    "V": "ঠ", "W": "ড", "X": "ঢ", "Y": "ণ", "Z": "ত", "_": "থ", "`": "দ", "a": "ধ", "b": "ন", "c": "প", "d": "ফ",
    "e": "ব", "f": "ভ", "g": "ম", "h": "য", "i": "র", "j": "ল", "k": "শ", "l": "ষ", "m": "স", "n": "হ",
    "o": "ড়", "p": "ঢ়", "q": "য়", "r": "ৎ", "s": "ং", "t": "ঃ", "u": "ঁ",
    "v": "া", "w": "ি", "x": "ী", "y": "ু", "z": "ু", "~": "ূ", "„": "ৃ", "…": "ৃ", "‡": "ে", "†": "ে", "ˆ": "ৈ",
    "‰": "ৈ", "Š": "ৗ", "æ": "ু", "ƒ": "ূ", "|": "।", "&": HALANT, "^": "্ব", "‹": "্ক", "Œ": "্ক্র", "”": "চ্",
    "—": "্ত", "˜": "দ্", "™": "দ্", "š": "ন্", "›": "ন্", "œ": "্ন", "Ÿ": "্ব", "¡": "্ব", "¢": "্ভ", "£": "্ভ্র",
    "¤": "ম্", "¥": "্ম", "¦": "্ব", "§": "্ম", "¨": "্য", "ª": "্র", "¬": "্ল", "­": "্ল", "®": "ষ্",
    "¯": "স্", "Ö": "্র", "Í": "্ত", "¿": "্ত্র", "ú": "্প", "ø": "্ল", "Ò": "“", "Ó": "”", "Ô": "‘", "Õ": "’",
    "Ñ": "–", "$": "৳",
}
_PATTERN = re.compile("|".join(re.escape(k) for k in sorted(MAP, key=len, reverse=True)))


def _rearrange(s: list[str]) -> list[str]:
    i = 0
    while i < len(s):
        # a vowel sign typed between a consonant and its halant cluster: 'kar + halant + C' -> 'halant + C + kar'
        if 0 < i < len(s) - 1 and s[i] == HALANT and s[i - 1] in KARS:
            s[i - 1], s[i], s[i + 1] = s[i], s[i + 1], s[i - 1]
        # 'ra + halant + kar' -> 'kar + ra + halant'
        if 0 < i < len(s) - 1 and s[i] == HALANT and s[i - 1] == "র" and (i < 2 or s[i - 2] != HALANT) \
                and s[i + 1] in KARS:
            s[i - 1], s[i], s[i + 1] = s[i + 1], s[i - 1], s[i]
        # reph (typed after its consonant cluster): move 'ra + halant' before the cluster
        if i < len(s) - 1 and s[i] == "র" and s[i + 1] == HALANT and (i == 0 or s[i - 1] != HALANT):
            j = 1
            while i - j >= 0:
                if s[i - j] in CONSONANTS and i - j - 1 >= 0 and s[i - j - 1] == HALANT:
                    j += 2
                elif j == 1 and s[i - j] in KARS:
                    j += 1
                else:
                    break
            if i - j >= 0:
                s = s[:i - j] + [s[i], s[i + 1]] + s[i - j:i] + s[i + 2:]
            i += 2
            continue
        # vowel signs i, e, oi (typed before the consonant cluster): move after it; e + ... + aa/au length -> o/au
        if i < len(s) - 1 and s[i] in PRE_KARS and not s[i + 1].isspace():
            j = 1
            while i + j < len(s) and s[i + j] in CONSONANTS:
                if i + j + 1 < len(s) and s[i + j + 1] == HALANT:
                    j += 2
                else:
                    break
            kar, after = s[i], i + j + 1
            if kar == "ে" and after < len(s) and s[after] == "া":
                mid, after = ["ো"], after + 1
            elif kar == "ে" and after < len(s) and s[after] == "ৗ":
                mid, after = ["ৌ"], after + 1
            else:
                mid = [kar]
            s = s[:i] + s[i + 1:i + j + 1] + mid + s[after:]
            i += j
        # chandrabindu typed before a following vowel sign
        if i < len(s) - 1 and s[i] == "ঁ" and s[i + 1] in POST_KARS:
            s[i], s[i + 1] = s[i + 1], s[i]
        i += 1
    return s


def to_unicode(text: str) -> str:
    """Unicode Bangla in NFC: the nukta letters come out as base + nukta (য + ়), as NFC requires."""
    s = _PATTERN.sub(lambda m: MAP[m.group(0)], text).replace(HALANT + HALANT, HALANT)  # 'ম্' + '্ব' -> 'ম্ব'
    s = "".join(_rearrange(list(s))).replace("অা", "আ")  # 'A u v' typed for aa-with-chandrabindu
    return unicodedata.normalize("NFC", s)
