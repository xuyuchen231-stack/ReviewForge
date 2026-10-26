"""Prepare inline bibliography labels from supplied metadata without changing originals."""
import re
from manuscript_integrity import CITES

def active_text(text):
    """Mask comments without changing offsets, preserving escaped percent signs."""
    active=[]
    for line in text.splitlines(keepends=True):
        for index,char in enumerate(line):
            if char=='%' and (index-len(line[:index].rstrip('\\')))%2==0:
                line=line[:index]+''.join('\n' if c=='\n' else ' ' for c in line[index:]);break
        active.append(line)
    return ''.join(active)

def citation_order(text):
    """First-use order in active, flattened manuscript text (not bibliography)."""
    active=active_text(text).split(r'\begin{thebibliography}',1)[0]
    return list(dict.fromkeys(key.strip() for group in CITES.findall(active)
                              for key in group.split(',') if key.strip()))

def order_inline_bibliography(tex):
    # Author/year publishers may require alphabetical ordering instead.
    active=active_text(tex)
    if re.search(r'\\setcitestyle\{[^}]*\bauthoryear\b',active):return tex
    if re.search(r'\\(?:usepackage|RequirePackage)(?:\[[^]]*\])?\{[^}]*\bnatbib\b',active):
        numeric=re.search(r'\\(?:usepackage|RequirePackage)\[[^]]*\b(?:numbers|super)\b[^]]*\]\{natbib\}|\\setcitestyle\{[^}]*\bnumbers\b',active)
        if not numeric or re.search(r'\\(?:usepackage|RequirePackage)\[[^]]*\bauthoryear\b[^]]*\]\{natbib\}',active):return tex
    environment=re.search(r'(\\begin\{thebibliography\}\{[^{}]*\})([\s\S]*?)(\\end\{thebibliography\})',active)
    if not environment:return tex
    body=tex[environment.start(2):environment.end(2)]
    matches=list(re.finditer(r'\\bibitem(?:\[[^]]*\])?\{([^{}]+)\}',active_text(body)))
    if not matches:return tex
    keys=[m.group(1) for m in matches]
    if len(keys)!=len(set(keys)):raise ValueError('Duplicate bibliography keys; resolve before delivery')
    entries={m.group(1):body[m.start():matches[i+1].start() if i+1<len(matches) else len(body)] for i,m in enumerate(matches)}
    ordered=[key for key in citation_order(tex) if key in entries]
    ordered.extend(key for key in keys if key not in ordered)
    replacement=body[:matches[0].start()]+''.join(entries[key] for key in ordered)
    return tex[:environment.start(2)]+replacement+tex[environment.end(2):]

def escape(value):
    return re.sub(r'([&%$#_{}])',lambda m:'\\'+m.group(1),str(value))

def prepare_inline_bibliography(tex,catalogue):
    if r'\end{thebibliography}' not in active_text(tex):return tex,[],[]
    known=set(re.findall(r'\\bibitem(?:\[[^]]*\])?\{([^}]+)\}',active_text(tex)));missing=set(citation_order(tex))-known;added=[];entries=[]
    for key in sorted(missing):
        row=catalogue.get(key,{})
        if row.get('metadata_status')!='REGISTERED_METADATA' or not all(row.get(f) for f in ('title','year','doi')):continue
        entries.append('\\bibitem{'+key+'}\n'+escape('; '.join(row.get('authors',[])))+'. '+escape(row['title'])+'. '+escape(row.get('venue',''))+' ('+str(row['year'])+'). DOI: \\url{https://doi.org/'+row['doi']+'}.\n')
        added.append(key)
    if entries:
        end=active_text(tex).find(r'\end{thebibliography}')
        tex=tex[:end]+'\n'.join(entries)+'\n'+tex[end:]
    def label(match):
        key=match.group(1);body=tex[match.start(2):match.end(2)];row=catalogue.get(key,{})
        authors=row.get('authors',[]);year=row.get('year');author=None
        if row.get('metadata_status')=='REGISTERED_METADATA' and authors and year:
            author=escape(authors[0])+(' et al.' if len(authors)>1 else '')
        else:
            # Existing manual entries may already supply an explicit surname/year.
            first=re.match(r'\s*([^,;\n.{}\\]+),\s*[^;\n]+',body)
            # A DOI or URL may contain an unrelated four-digit number; it is
            # an identifier, not an alternative publication year.
            dating=re.sub(r'\\url\{[^}]*\}|https?://\S+|10\.\d{4,9}/\S+','',body)
            dates=set(re.findall(r'(?<!\d)((?:19|20)\d{2})(?!\d)',dating))
            date=re.search(r'(?<!\d)((?:19|20)\d{2})(?!\d)(?:\}|\))?\s*[,.;]',dating)
            if first and date and len(dates)==1:author=first.group(1).strip()+(' et al.' if ';' in body[:body.find(date.group(1))] else '');year=date.group(1)
        if not author or not year:return tex[match.start():match.end()]
        # Natbib interprets parentheses as its author/year label delimiters.
        author=author.replace('(','').replace(')','').replace('[','').replace(']','')
        return '\\bibitem['+author+'('+str(year)+')]{'+key+'}'+body
    pattern=r'\\bibitem\{([^{}]+)\}([\s\S]*?)(?=\\bibitem(?:\[[^]]*\])?\{|\\end\{thebibliography\})'
    for match in reversed(list(re.finditer(pattern,active_text(tex)))):
        tex=tex[:match.start()]+label(match)+tex[match.end():]
    return order_inline_bibliography(tex),added,sorted(missing-set(added))
