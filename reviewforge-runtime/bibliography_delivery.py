"""Prepare inline bibliography labels from supplied metadata without changing originals."""
import re
from manuscript_integrity import citekeys

def escape(value):
    return re.sub(r'([&%$#_{}])',lambda m:'\\'+m.group(1),str(value))

def prepare_inline_bibliography(tex,catalogue):
    if r'\end{thebibliography}' not in tex:return tex,[],[]
    known=set(re.findall(r'\\bibitem(?:\[[^]]*\])?\{([^}]+)\}',tex));missing=citekeys(tex)-known;added=[];entries=[]
    for key in sorted(missing):
        row=catalogue.get(key,{})
        if row.get('metadata_status')!='REGISTERED_METADATA' or not all(row.get(f) for f in ('title','year','doi')):continue
        entries.append('\\bibitem{'+key+'}\n'+escape('; '.join(row.get('authors',[])))+'. '+escape(row['title'])+'. '+escape(row.get('venue',''))+' ('+str(row['year'])+'). DOI: \\url{https://doi.org/'+row['doi']+'}.\n')
        added.append(key)
    tex=tex.replace(r'\end{thebibliography}','\n'.join(entries)+'\n'+r'\end{thebibliography}',1) if entries else tex
    def label(match):
        key,body=match.groups();row=catalogue.get(key,{})
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
        if not author or not year:return match.group()
        # Natbib interprets parentheses as its author/year label delimiters.
        author=author.replace('(','').replace(')','').replace('[','').replace(']','')
        return '\\bibitem['+author+'('+str(year)+')]{'+key+'}'+body
    pattern=r'\\bibitem\{([^{}]+)\}([\s\S]*?)(?=\\bibitem(?:\[[^]]*\])?\{|\\end\{thebibliography\})'
    tex=re.sub(pattern,label,tex)
    return tex,added,sorted(missing-set(added))
