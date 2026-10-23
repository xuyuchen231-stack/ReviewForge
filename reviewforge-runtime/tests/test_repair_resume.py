import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import reviewforge_v4 as rf


class RepairResumeTests(unittest.TestCase):
    def test_whole_section_failure_counts_even_without_block_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp); (ws/'reports').mkdir()
            state={'history':[{'section':10,'accepted':False,'reason':'Section inventory changed'}]}
            self.assertEqual(rf.unresolved_repairs(state,ws)[0]['section'],11)

    def test_resume_run_retries_selected_sections_and_preserves_other_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp); (ws/'reports').mkdir()
            tex='\\documentclass{article}\n\\begin{document}\n'+''.join('\\section{Part %d}\n'%i+'Original scientific explanation. '*10+'\n' for i in range(4))+'\\end{document}\n'
            (ws/'original.tex').write_text(tex)
            (ws/'review_en.tex').write_text(tex)
            (ws/'literature.json').write_text('[]')
            (ws/'reports/repair_queue.json').write_text(json.dumps([{'section':2,'block':1},{'section':4,'block':1}]))
            (ws/'v4_state.json').write_text(json.dumps({'stage':'finished_with_unresolved_reviews','section':4,'calls':0,'history':[],'deadline':time.time()+60}))
            visited=[]
            def repair(api,whole,head,body,papers,workspace,index,state,state_path):
                visited.append(index)
                state['section_pending_repairs']={'section':index+1,'items':[]}
                if index==3:state['deadline']=0
                return body
            with patch.object(rf,'CompatibleAPI',return_value=object()),patch.object(rf,'review_blocks',side_effect=repair):
                result=rf.run_v4(ws,resume=True,minimum=0)
            self.assertEqual(visited,[1,3])
            self.assertEqual(result['stage'],'translation')
            self.assertEqual(json.loads((ws/'reports/repair_queue.json').read_text()),[])
            after=(ws/'review_en.tex').read_text()
            for (_,a,b),(_,c,d) in zip(rf.extract_sections(tex),rf.extract_sections(after)):
                self.assertEqual(tex[a:b].strip(),after[c:d].strip())

    def test_completed_run_schedules_only_unresolved_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp); (ws/'reports').mkdir()
            (ws/'reports/repair_queue.json').write_text(json.dumps([{'section':3,'block':5}]))
            state={'stage':'finished_with_unresolved_reviews','section':13,'history':[{'section':10,'accepted':False}], 'deadline':time.time()+100}
            rf.prepare_repair_resume(state,ws)
            self.assertEqual(state['stage'],'writing')
            self.assertEqual(state['section'],2)
            self.assertEqual(state['repair_sections'],[2,10])

    def test_success_replaces_stale_queue_and_clears_section_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp); (ws/'reports').mkdir()
            (ws/'reports/repair_queue.json').write_text(json.dumps([{'section':3,'block':9},{'section':4,'block':1}]))
            (ws/'reports/failed_sections.json').write_text(json.dumps([{'section':3},{'section':4}]))
            rf.finish_section_repairs(ws,2,[])
            self.assertEqual(json.loads((ws/'reports/repair_queue.json').read_text()),[{'section':4,'block':1}])
            self.assertEqual(json.loads((ws/'reports/failed_sections.json').read_text()),[{'section':4}])

    def test_whitespace_block_never_calls_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp); (ws/'reports').mkdir()
            state={'deadline':time.time()+60,'calls':0}
            with patch.object(rf,'write_section',side_effect=AssertionError('Whitespace sent to model')):
                result=rf.review_blocks(None,'','Methods','\n\n',[],ws,0,state,ws/'state.json')
            self.assertEqual(result,'\n\n')
            self.assertEqual(state['section_pending_repairs']['items'],[])

    def test_invalid_repair_queue_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp); (ws/'reports').mkdir()
            (ws/'reports/repair_queue.json').write_text('{bad')
            with self.assertRaises(rf.GateError):
                rf.prepare_repair_resume({'stage':'finished_with_unresolved_reviews','history':[]},ws)


if __name__=='__main__': unittest.main()
