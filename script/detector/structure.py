"""Groupes syntaxiques partagés par les mesures de structure et les tricolons."""

from dataclasses import dataclass
import re

from .morphalou import lexical_map


BLOCK_BREAK = re.compile(r"\n[ \t]*\n+|(?:^|\n)[ \t]*#{1,6}[ \t][^\n]*(?:\n|$)")
SENTENCE_END = re.compile(r'[.!?…](?:[ \u00a0]*[»”"]+(?:\s+|$)|(?!\s*[»”"])(?:\s+|$)|(?=[«“]))')
SUBORDINATORS = {"comme", "comment", "dont", "lorsque", "où", "parce", "pourquoi", "puisque", "quand", "que", "qui", "quoique", "si", "tandis"}


@dataclass
class ClauseAnalysis:
    display: list[str]
    key: str
    start: int
    end: int
    kind: str


def _trim(text, start, end):
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def sentence_ranges(text):
    start = 0
    for block in [*BLOCK_BREAK.finditer(text), None]:
        end = block.start() if block else len(text)
        cursor = start
        for boundary in SENTENCE_END.finditer(text, start, end):
            left, right = _trim(text, cursor, boundary.start() + 1)
            if left < right:
                yield left, right
            cursor = boundary.end()
        left, right = _trim(text, cursor, end)
        if left < right:
            yield left, right
        start = block.end() if block else end


def _is_hinge(token):
    return (
        token.pos_ == "SCONJ"
        or "Rel" in token.morph.get("PronType")
        or token.lower_.rstrip("'’") in SUBORDINATORS
        or token.lower_ == "pour" and "Inf" in token.head.morph.get("VerbForm")
        or token.lower_ in {"pendant", "alors", "afin"} and token.i + 1 < len(token.doc) and token.doc[token.i + 1].lower_ == "que"
    )


def _category(token, mapping):
    if _is_hinge(token):
        return "CHARNIÈRE"
    if "Part" in token.morph.get("VerbForm"):
        return "VERBE" if any(child.dep_.startswith("aux") for child in token.children) else "ADJECTIF"
    if token.pos_ in {"VERB", "AUX"}:
        return "VERBE"
    # Répare les prédicats homographes dont spaCy reconnaît le sujet ou la coordination.
    if token.pos_ in {"ADJ", "NOUN"} and (
        token.dep_ == "acl:relcl" and any(child.dep_.startswith("nsubj") for child in token.children)
        or token.pos_ == "NOUN" and any(child.dep_.startswith("nsubj") for child in token.children) and not any(child.pos_ == "DET" or child.dep_ == "cop" for child in token.children)
        or token.dep_ == "conj" and token.head.pos_ == "VERB" and "Fin" in token.head.morph.get("VerbForm") and not any(child.pos_ == "DET" for child in token.children)
        or token.head.pos_ == "PRON" and mapping.get(token.lower_, ("", ""))[1].lower().startswith("verbe")
    ):
        return "VERBE"
    return {"PRON": "PRONOM", "NOUN": "NOM", "PROPN": "NOM", "ADJ": "ADJECTIF", "ADV": "ADVERBE", "CCONJ": "CONJONCTION"}.get(token.pos_, "")


def _roles(tokens, categories):
    result = []
    for token in tokens:
        category = categories[token.i]
        if category == "NOM" and result and result[-1] == "PRONOM":
            category = "VERBE"
        if category and not (result and result[-1] == category and category in {"VERBE", "PRONOM", "CHARNIÈRE"}):
            result.append(category)
    return result


def _clause_signature(roles):
    if not roles:
        return []
    if "CHARNIÈRE" in roles:
        index = roles.index("CHARNIÈRE")
        return _clause_signature(roles[:index]) + ["CHARNIÈRE"] + _clause_signature(roles[index + 1:])
    if roles[0] == "CONJONCTION":
        roles = roles[1:]
    if not roles:
        return []
    if "VERBE" not in roles:
        if "NOM" in roles:
            return ["NOM", "COMPLÉMENT"] if roles.index("NOM") < len(roles) - 1 else ["NOM"]
        return ["COMPLÉMENT"]
    verb = roles.index("VERBE")
    return (["SUJET"] if verb else []) + ["VERBE"] + (["COMPLÉMENT"] if verb < len(roles) - 1 else [])


def analyze_clause(tokens, categories, start, end):
    roles = _clause_signature(_roles(tokens, categories))
    intro = roles[:2] if roles[:2] == ["SUJET", "VERBE"] and len(roles) > 2 else []
    rest = roles[2:] if intro else roles
    hinge = next((token for token in tokens if categories[token.i] == "CHARNIÈRE"), None)
    content = [categories[token.i] for token in tokens if categories[token.i] and categories[token.i] not in {"PRONOM", "CONJONCTION"}]
    kind = content[-1] if content else ""
    if hinge is not None and "CHARNIÈRE" in rest:
        index = rest.index("CHARNIÈRE")
        head, tail = rest[:index], rest[index + 1:]
        if "VERBE" in tail:
            if head:
                key = head[1:] if head[0] == "NOM" and len(head) > 1 else head
                head_content = [categories[token.i] for token in tokens if token.idx < hinge.idx and categories[token.i]]
                return ClauseAnalysis(intro + head, " ".join(key), start, hinge.idx, head_content[-1] if head_content else "")
            label = hinge.lower_.rstrip("'’")
            return ClauseAnalysis(intro + [label, "SUBORDONNÉE"], f"{label} SUBORDONNÉE", hinge.idx if intro else start, end, "SUBORDONNÉE")
        if intro:
            return ClauseAnalysis(intro + ["COMPLÉMENT"], "COMPLÉMENT", hinge.idx + len(hinge), end, kind)
        return ClauseAnalysis(head + [hinge.lower_] + tail, " ".join(tail), hinge.idx + len(hinge), end, kind)
    nominal = rest[:1] == ["NOM"] and len(rest) > 1
    key = intro + rest if intro else rest[1:] if nominal else rest
    return ClauseAnalysis(intro + rest, " ".join(key), start, end, kind)


def _bare_preposition(tokens):
    return bool(tokens and tokens[0].pos_ == "ADP" and tokens[0].lower_ != "pour" and not _is_hinge(tokens[0]))


def _group_tokens(tokens):
    groups = [[]]
    for token in tokens:
        if token.text == ",":
            groups.append([])
        elif not token.is_space and not token.is_punct:
            groups[-1].append(token)
    return [group for group in groups if group]


def _merge_prepositions(groups):
    merged = []
    has_head = False
    for group in groups:
        bare = _bare_preposition(group)
        if merged and bare and has_head:
            merged[-1].extend(group)
        else:
            merged.append(group)
        has_head |= not bare
    return merged


def _analyze_groups(tokens, categories, start, end):
    groups = _group_tokens(tokens)
    # Une coordination finale ferme aussi les énumérations adjectivales et verbales.
    if len(groups) >= 2:
        last = groups[-1]
        coordinations = [index for index, token in enumerate(last) if token.lower_ in {"et", "ou", "ni"}]
        if coordinations:
            split = coordinations[-1]
            left, right = last[:split], last[split + 1:]
            if left and right:
                groups[-1:] = [left, right]
                if len(groups) >= 4:
                    anchor = groups[-3]
                    verbs = [index for index, token in enumerate(anchor) if categories[token.i] == "VERBE"]
                    if verbs and not _bare_preposition(anchor):
                        prefix, first = anchor[:verbs[-1] + 1], anchor[verbs[-1] + 1:]
                        items = [first, *groups[-2:]]
                        if all(item and _clause_signature(_roles(item, categories))[:1] == ["NOM"] for item in items):
                            groups[-3:] = [prefix, *items]
    groups = _merge_prepositions(groups)
    analyses = []
    for index, group in enumerate(groups):
        left = start if index == 0 else group[0].idx
        right = end if index == len(groups) - 1 else group[-1].idx + len(group[-1])
        analyses.append(analyze_clause(group, categories, left, right))
    for index, group in enumerate(groups[:-1]):
        if not _bare_preposition(group):
            break
        analyses[index].display = ["CADRATIF"]
        analyses[index].key = "CADRATIF"
    index = 0
    while index + 2 < len(analyses):
        run = analyses[index:index + 3]
        following = analyses[index + 1:index + 4]
        if len(following) == 3 and following[0].key and all(item.key == following[0].key for item in following) and run[0].display[:2] == ["SUJET", "VERBE"]:
            index += 1
            continue
        if all(item.display and item.display[0] in {"NOM", "COMPLÉMENT"} for item in run) and len({item.kind for item in run}) == 1:
            for item in run:
                item.key = "NOM" if run[0].display[0] == "NOM" else "COMPLÉMENT"
        elif run[0].display[:2] == ["SUJET", "VERBE"] and run[0].display[-1] == "COMPLÉMENT" and all(item.display and item.display[0] in {"NOM", "COMPLÉMENT"} and item.kind == run[0].kind for item in run[1:]):
            for item in run:
                item.key = "COMPLÉMENT"
        elif run[0].display == ["SUJET", "VERBE"] and all(item.display == ["VERBE"] for item in run[1:]):
            for item in run:
                item.key = "VERBE"
        # Le premier relatif peut être précédé de son nom support.
        elif run[1].kind == run[2].kind == "SUBORDONNÉE" and run[1].key == run[2].key:
            hinge = next((token for token in groups[index] if categories[token.i] == "CHARNIÈRE"), None)
            if hinge is not None and run[1].key == f"{hinge.lower_} SUBORDONNÉE":
                run[0].key = run[1].key
                run[0].kind = "SUBORDONNÉE"
        index += 1
    return analyses


def analyze_structure(text, doc):
    if doc is None:
        return [], ()
    mapping = lexical_map(token.lower_ for token in doc if token.pos_ in {"ADJ", "NOUN"} and token.head.pos_ == "PRON")
    categories = {token.i: _category(token, mapping) for token in doc}
    signatures, tricolons = [], []
    cursor = 0
    for start, end in sentence_ranges(text):
        while cursor < len(doc) and doc[cursor].idx < start:
            cursor += 1
        stop = cursor
        while stop < len(doc) and doc[stop].idx < end:
            stop += 1
        tokens = list(doc[cursor:stop])
        cursor = stop
        analyses = _analyze_groups(tokens, categories, start, end)
        if not any(item.display for item in analyses):
            continue
        signatures.append(" , ".join(" ".join(item.display) for item in analyses) + (" ." if text[end - 1] == "." else ""))
        run_start = 0
        while run_start < len(analyses):
            run_end = run_start + 1
            while run_end < len(analyses) and analyses[run_end].key == analyses[run_start].key:
                run_end += 1
            count = run_end - run_start
            # Une liste coordonnée de quatre éléments reste une seule énumération.
            coordinated = any(token.lower_ in {"et", "ou", "ni"} for token in tokens)
            if analyses[run_start].key and "," in text[start:end] and not (count % 3 and coordinated):
                for index in range(run_start, run_end - 2, 3):
                    left, right = _trim(text, analyses[index].start, analyses[index + 2].end)
                    tricolons.append((left, right))
            run_start = run_end
    return signatures, tuple(tricolons)


def ternary_char_ranges(text, doc):
    return analyze_structure(text, doc)[1]
