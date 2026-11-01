"""Extract minimal public role-page listings from saved Wellfound HTML.

This parser does not fetch pages, authenticate, bypass access controls, or infer
location from a search page. Wellfound's markup is not a documented API.
"""
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlsplit

_JOB = re.compile(r'^/jobs/\d+-[A-Za-z0-9][A-Za-z0-9-]*(?:[?#].*)?$')
_COMPANY = re.compile(r'^/company/[A-Za-z0-9][A-Za-z0-9-]*(?:[/?#].*)?$')
_VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

class _RolePage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth=0; self.card_depth=None; self.company=None; self.jobs=[]; self.anchor=None; self.results=[]

    def handle_starttag(self, tag, attrs):
        data=dict(attrs)
        if tag not in _VOID: self.depth+=1
        classes=set((data.get('class') or '').split())
        if tag=='div' and self.card_depth is None and {'mb-6','rounded','border-gray-400'}.issubset(classes):
            self.card_depth=self.depth; self.company=None; self.jobs=[]
        if self.card_depth is not None and tag=='a':
            href=data.get('href') or ''
            if _JOB.match(href): self.anchor=('job',href,[])
            elif _COMPANY.match(href): self.anchor=('company',href,[])

    def handle_data(self, data):
        if self.anchor is not None: self.anchor[2].append(data)

    def handle_endtag(self, tag):
        if tag=='a' and self.anchor is not None:
            kind,href,parts=self.anchor; text=' '.join(''.join(parts).split()); self.anchor=None
            if kind=='company' and text and self.company is None: self.company=text
            elif kind=='job' and text: self.jobs.append((href,text))
        if tag=='div' and self.card_depth is not None and self.depth==self.card_depth:
            self.results.extend((href,title,self.company) for href,title in self.jobs)
            self.card_depth=None; self.jobs=[]; self.company=None
        if tag not in _VOID: self.depth=max(0,self.depth-1)


def parse_wellfound_role(html: str, source_url: str, artifact_ref: str, *, india_only: bool=False) -> list[dict]:
    """Extract visible listing links and employers; keep unspecified fields unknown."""
    try:
        parsed=urlsplit(source_url)
        if (parsed.scheme not in {'https','http'} or parsed.hostname not in {'wellfound.com','www.wellfound.com'}
                or parsed.username is not None or parsed.password is not None):
            return []
        if not (parsed.path.startswith('/role/') or parsed.path.startswith('/location/')):
            return []
    except ValueError:
        return []
    if india_only or not isinstance(html,str) or len(html)>5_000_000:
        return []
    parser=_RolePage(); parser.feed(html); parser.close(); output=[]; seen=set()
    for href,title,company in parser.results:
        url=urljoin('https://wellfound.com',href.split('#',1)[0])
        if url in seen: continue
        seen.add(url)
        output.append({'schema_version':1,'parser_version':'wellfound-role-v1','title':title,
                       'company':company,'location':None,'is_india':False,'salary':None,
                       'description':None,'application_url':url,'source_name':'Wellfound',
                       'source_url':source_url,'artifact_ref':artifact_ref})
    return output
