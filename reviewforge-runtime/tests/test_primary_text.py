import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from primary_text import acquire


class PrimaryTextTests(unittest.TestCase):
    def test_public_pdf_acquired_once_with_identity_and_provenance(self):
        import fitz
        pdf=fitz.open();page=pdf.new_page();page.insert_textbox(fitz.Rect(20,20,580,820),'10.1234/example\n'+('Primary study methods and validation data.\n'*30),fontsize=10);blob=pdf.tobytes();pdf.close();calls=[]
        def fetch(url):
            calls.append(url)
            if 'api.crossref' in url:return json.dumps({'message':{'DOI':'10.1234/example','link':[{'URL':'https://publisher.example/source.pdf','content-type':'application/pdf'}]}}).encode()
            return blob
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'source').mkdir();entry={'source_directory':'source','doi':'10.1234/example'}
            self.assertEqual(acquire(root,entry,fetch)['status'],'ACQUIRED_PUBLIC_FULL_TEXT')
            self.assertEqual(acquire(root,entry,fetch)['status'],'CACHED_FULL_TEXT')
            self.assertEqual(len(calls),2)
            self.assertTrue((root/'source/fulltext/pages.json').exists())

    def test_wrong_doi_and_recent_failure_do_not_become_fulltext_or_findings(self):
        calls=[]
        def fetch(url):calls.append(url);return json.dumps({'message':{'DOI':'10.9999/wrong'}}).encode()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'source').mkdir();entry={'source_directory':'source','doi':'10.1234/example'};now=dt.datetime(2026,11,3,tzinfo=dt.timezone.utc)
            result=acquire(root,entry,fetch,now)
            self.assertEqual(result['status'],'NO_PUBLIC_FULL_TEXT');self.assertIn('not evidence',result['interpretation'])
            acquire(root,entry,fetch,now);self.assertEqual(len(calls),1)
            self.assertFalse((root/'source/fulltext/source.txt').exists())
