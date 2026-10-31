import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from publication_figures import validate_plan,add_planned_figures

class PublicationFigureTests(unittest.TestCase):
 def spec(self):
  return {'id':'concept','source_keys':['A'],'after_heading':r'\subsection{Model}','lead_in':'Figure~{FIG} distinguishes the interfaces.','caption':'Conceptual construction. ','panels':[{'title':'Distinct role '+str(i),'note':'An evidence-bounded question.','nodes':[{'text':'Input'},{'text':'Output'}]} for i in range(4)]}
 def test_unknown_source_or_path_id_is_rejected(self):
  spec=self.spec()
  with self.assertRaises(ValueError):validate_plan(spec,[])
  spec['id']='../escape'
  with self.assertRaises(ValueError):validate_plan(spec,['A'])
 def test_insertion_preserves_existing_prose_and_avoids_duplicate_figures(self):
  source=r'\subsection{Model}'+'\nOriginal prose.\n'+r'\subsection{Next}Next.\begin{thebibliography}{9}\bibitem{A}Reference.\end{thebibliography}'
  with tempfile.TemporaryDirectory() as t,patch('publication_figures.render_concept',return_value={'semantic_verification':False}):
   out,report=add_planned_figures(source,{'figures':[self.spec()]},Path(t))
   self.assertIn('Original prose.',out);self.assertIn(r'\begin{figure*}',out);self.assertIn(r'\cite{A}',out)
   self.assertEqual(report['added'],1);self.assertEqual(report['model_calls'],0)
   self.assertEqual(add_planned_figures(out,{'figures':[self.spec()]},Path(t))[0],out)
