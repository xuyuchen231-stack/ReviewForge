"""Checkpointed prose translation with immutable TeX tokens; no English fallback."""
import hashlib
import json
import re
import time
from pathlib import Path

from reviewforge import atomic_json


class TranslationError(ValueError):
    pass


TOKEN = re.compile(r'RFPROTECT\d{6}TOKEN')
# Keep scientific/programmatic environments opaque. Captions and table prose outside
# these environments remain translatable. Embedded TikZ labels require separate editing.
OPAQUE = re.compile(
    r'\\begin\{(equation\*?|eqnarray\*?|align\*?|gather\*?|multline\*?|displaymath|math|'
    r'tikzpicture|verbatim\*?|lstlisting|thebibliography)\}.*?\\end\{\1\}'
    r'|\\\[.*?\\\]|\\\(.*?\\\)|(?<!\\)\$\$.*?(?<!\\)\$\$|(?<!\\)\$.*?(?<!\\)\$', re.S)
COMMAND = re.compile(r'\\([A-Za-z]+\*?|.)', re.S)
# Scientific organism names are identifiers, including when italicized. Keep
# this explicit rather than treating every capitalized/italic English word as one.
_SCIENTIFIC_NAMES=('Pichia pastoris','P. pastoris','Komagataella phaffii','K. phaffii','Escherichia coli','E. coli','Saccharomyces cerevisiae','S. cerevisiae','Bacillus subtilis','B. subtilis','Corynebacterium glutamicum','C. glutamicum','Aspergillus niger','A. niger','Yarrowia lipolytica','Y. lipolytica','Pseudomonas putida','P. putida','Pichia','Komagataella','Escherichia','Saccharomyces','Bacillus','Corynebacterium','Aspergillus','Yarrowia','Pseudomonas','Enterobacter')
SCIENTIFIC_NAMES = re.compile(r'(?<![A-Za-z])(?:'+'|'.join(r'(?:\s+|\\\s+|~)'.join(re.escape(word) for word in name.split()) for name in _SCIENTIFIC_NAMES)+r')(?![A-Za-z])')
OPAQUE_ARGS = {'cite', 'citep', 'citet', 'parencite', 'textcite', 'autocite',
               'footcite', 'nocite', 'ref', 'eqref', 'autoref', 'cref', 'Cref',
               'label', 'includegraphics', 'bibliography', 'bibliographystyle',
               'url', 'path', 'input', 'include', 'hspace', 'vspace', 'cline',
               'cmidrule', 'color', 'textcolor', 'href', 'begin', 'end', 'ensuremath'}


def group_end(text, start, left='{', right='}'):
    depth = 0
    for i in range(start, len(text)):
        # An odd run of backslashes escapes a delimiter.
        slashes = len(text[:i]) - len(text[:i].rstrip('\\'))
        if slashes % 2:
            continue
        if text[i] == left:
            depth += 1
        elif text[i] == right:
            depth -= 1
            if depth == 0:
                return i + 1
    raise TranslationError('Unclosed TeX group; repair source before translating')


def mask_tex(text):
    """Mask commands, arguments that are identifiers, math, comments and numbers."""
    if TOKEN.search(text):
        raise TranslationError('Reserved translation token already present in source')
    saved = []
    def protect(value):
        token = f'RFPROTECT{len(saved):06d}TOKEN'
        saved.append(value)
        return token
    out = []
    i = 0
    depth = 0
    def next_nonspace(pos):
        while pos < len(text):
            if text[pos].isspace(): pos += 1
            elif text[pos] == '%':
                end = text.find('\n', pos)
                pos = len(text) if end < 0 else end + 1
            else: break
        return pos
    while i < len(text):
        opaque = OPAQUE.match(text, i)
        if opaque:
            out.append(protect(opaque.group())); i = opaque.end(); continue
        if text[i] == '%':
            end = text.find('\n', i)
            end = len(text) if end < 0 else end
            out.append(protect(text[i:end])); i = end; continue
        command = COMMAND.match(text, i)
        if command:
            name = command.group(1).rstrip('*')
            end = command.end()
            # Preserve optional command arguments and identifier arguments exactly.
            pos = next_nonspace(end)
            while pos < len(text) and text[pos] == '[':
                end = group_end(text, pos, '[', ']'); pos = next_nonspace(end)
            arg_count = 2 if name in ('multicolumn', 'multirow') else 1 if name in OPAQUE_ARGS else 0
            for _ in range(arg_count):
                pos = next_nonspace(end)
                if pos < len(text) and text[pos] == '{': end = group_end(text, pos)
            if name == 'begin':
                env = re.search(r'\{([^{}]+)\}$',text[i:end])
                pos = next_nonspace(end)
                if pos < len(text) and text[pos] == '[':
                    end = group_end(text, pos, '[', ']')
                # Tabular column specification is not natural-language prose.
                if env and env.group(1) in ('tabular','tabular*','tabularx','array'):
                    pos = next_nonspace(end)
                    for _ in range(2 if env.group(1) in ('tabular*','tabularx') else 1):
                        if pos < len(text) and text[pos] == '{':
                            end = group_end(text, pos); pos = next_nonspace(end)
            out.append(protect(text[i:end])); i = end; continue
        if text[i] in '{}&~#$':
            if text[i] == '{': depth += 1
            elif text[i] == '}': depth -= 1
            if depth < 0: raise TranslationError('Unmatched closing TeX brace')
            out.append(protect(text[i])); i += 1; continue
        scientific_name=SCIENTIFIC_NAMES.match(text,i)
        if scientific_name:
            out.append(protect(scientific_name.group()));i=scientific_name.end();continue
        number = re.match(r'\d+(?:[.,]\d+)*', text[i:])
        if number:
            out.append(protect(number.group())); i += len(number.group()); continue
        out.append(text[i]); i += 1
    if depth: raise TranslationError('Unclosed TeX brace; repair source before translating')
    return ''.join(out), saved


def validate_unit(source, candidate):
    if not isinstance(candidate, str) or not candidate.strip():
        return False, 'Empty translation'
    if TOKEN.findall(source) != TOKEN.findall(candidate):
        return False, 'Protected tokens changed, reordered or omitted'
    prose = TOKEN.sub('', candidate)
    if re.search(r'[\\{}$&\d]|```', prose):
        return False, 'Translation introduced TeX syntax'
    original = TOKEN.sub('', source)
    if any(not word.isupper() for word in re.findall(r'[A-Za-z]{2,}', original)) and not re.search(r'[\u3400-\u9fff]', prose):
        return False, 'English text has no Chinese translation'
    if re.search(r'(?:\b[A-Za-z][A-Za-z-]*[ ,;:]*){12,}', prose):
        return False, 'Long untranslated English span'
    for before, after in zip(TOKEN.split(source), TOKEN.split(candidate)):
        words = re.findall(r'\b[A-Za-z]{2,}\b', before)
        if any(not word.isupper() for word in words) and not re.search(r'[\u3400-\u9fff]', after):
            return False, 'Untranslated prose between protected tokens'
        old_words = re.findall(r'\b[A-Za-z]+\b', before.lower())
        new_words = re.findall(r'\b[A-Za-z]+\b', after.lower())
        triples = {tuple(old_words[i:i+3]) for i in range(len(old_words)-2)}
        if any(tuple(new_words[i:i+3]) in triples for i in range(len(new_words)-2)):
            return False, 'Untranslated English phrase retained'
    if len(prose.strip()) < max(1, len(re.findall(r'\b[A-Za-z]+\b', original)) // 2):
        return False, 'Likely truncated translation'
    return True, ''


def prose_units(masked, limit=1800):
    # Bound requests without ever splitting a protected token or ordinary word.
    units, current = [], ''
    for part in re.findall(r'RFPROTECT\d{6}TOKEN|\s+|[^\s]+?(?=RFPROTECT\d{6}TOKEN|\s|$)', masked):
        if current and len(current) + len(part) > limit:
            units.append(current); current = ''
        current += part
        if '\n\n' in part:
            units.append(current); current = ''
    if current:
        units.append(current)
    return units


def translate_fragment(text, ask, directory, context, reports, deadline=None):
    masked, saved = mask_tex(text)
    output = []
    for unit in prose_units(masked):
        if not re.search(r'[A-Za-z]{2}', TOKEN.sub('', unit)):
            output.append(unit); continue
        digest = hashlib.sha256((context + '\0' + unit).encode()).hexdigest()
        path = directory / (digest + '.json')
        entry = {'id': digest, 'status': 'FAILED', 'attempts': 0}
        candidate = None
        if path.exists():
            try:
                cached = json.loads(path.read_text(encoding='utf-8'))
                if cached.get('source_sha256') == digest and validate_unit(unit, cached.get('text'))[0]:
                    candidate = cached['text']; entry['cached'] = True
            except (ValueError, OSError, TypeError):
                pass
        if candidate is None:
            for attempt in range(2):
                if deadline is not None and time.time() >= deadline:
                    entry['reason'] = 'Translation deadline reached'; break
                entry['attempts'] += 1
                try:
                    translated = ask(unit, entry.get('reason', ''))
                    ok, why = validate_unit(unit, translated)
                    if ok:
                        candidate = translated; break
                    entry['reason'] = why
                except Exception as exc:
                    entry['reason'] = type(exc).__name__ + ': translation request failed'
            if candidate is None and len(unit) > 600 and (deadline is None or time.time() < deadline):
                # A bounded second pass uses smaller chunks; it cannot recurse forever.
                smaller = prose_units(unit, 600)
                pieces = []
                for piece in smaller:
                    if not re.search(r'[A-Za-z]{2}', TOKEN.sub('', piece)):
                        pieces.append(piece); continue
                    if deadline is not None and time.time() >= deadline:
                        break
                    try:
                        value = ask(piece, 'Previous larger block failed; translate this smaller unit completely.')
                        entry['attempts'] += 1
                        if not validate_unit(piece, value)[0]: break
                        pieces.append(value)
                    except Exception:
                        break
                if len(pieces) == len(smaller): candidate = ''.join(pieces)
        if candidate is not None:
            # Preserve boundaries between commands/paragraphs even if the model strips whitespace.
            candidate = re.match(r'\s*', unit).group() + candidate.strip() + re.search(r'\s*$', unit).group()
            atomic_json(path, {'source_sha256': digest, 'text': candidate})
            entry['status'] = 'PASS'
            output.append(candidate)
        reports.append(entry)
        atomic_json(directory.parent/'translation_progress.json', reports)
        if candidate is None:
            raise TranslationError('Translation unit failed: ' + digest[:12] + '; ' + entry.get('reason', 'incomplete'))
    result = ''.join(output)
    return TOKEN.sub(lambda m: saved[int(m.group()[9:15])], result)


def translate_document(tex, workspace, ask, context='', deadline=None):
    ws = Path(workspace)
    directory = ws/'reports'/'translation_units'
    directory.mkdir(parents=True, exist_ok=True)
    reports = []
    report = {'status': 'FAILED', 'source_sha256': hashlib.sha256(tex.encode()).hexdigest(),
              'units': reports, 'limitations': ['Text inside protected TikZ/math/verbatim and external figures is preserved; inspect visually.']}
    try:
        start = tex.find(r'\begin{document}')
        end = tex.rfind(r'\end{document}')
        if start < 0 or end < start: raise TranslationError('Complete TeX document required')
        visible_body = re.sub(r'(?m)(?<!\\)%.*$', '', tex[start:end])
        if re.search(r'\\(?:input|include)\b', visible_body):
            raise TranslationError('Flatten external input/include manuscript sections before translation')
        preamble = tex[:start]
        title = re.search(r'\\title(?:\[[^]]*\])?\{', preamble)
        if title:
            stop = group_end(preamble, title.end()-1)
            original = preamble[title.end():stop-1]
            value = translate_fragment(original, ask, directory, context, reports, deadline)
            preamble = preamble[:title.end()] + value + preamble[stop-1:]
        if not re.search(r'\\(?:usepackage(?:\[[^]]*\])?\{[^}]*ctex|documentclass(?:\[[^]]*\])?\{ctex)', preamble):
            preamble += '\\usepackage[UTF8]{ctex}\n'
        body = translate_fragment(tex[start:end], ask, directory, context, reports, deadline)
        result = preamble + body + tex[end:]
        report.update(status='PASS', output_sha256=hashlib.sha256(result.encode()).hexdigest(), completed_units=len(reports))
        return result
    finally:
        atomic_json(ws/'reports'/'translation_gate.json', report)
