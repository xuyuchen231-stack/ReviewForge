import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from publication_figures import validate_plan,add_planned_figures

class PublicationFigureTests(unittest.TestCase):
 def test_commented_generated_label_cannot_delete_author_data_figure(self):
  source=r'\subsection{Model}\begin{figure}\includegraphics{real-data.pdf}\label{fig:author-data}'+'\n% '+r'\label{fig:rf-old}'+'\n% '+r'\label{fig:rf-concept}'+'\n'+r'\end{figure}\begin{thebibliography}{9}\bibitem{A}Reference.\end{thebibliography}'
  spec=self.spec();spec['replaces']=['old']
  with tempfile.TemporaryDirectory() as folder,patch('publication_figures.render_concept',return_value={}):
   result,_=add_planned_figures(source,{'figures':[spec]},Path(folder))
  self.assertIn(r'\includegraphics{real-data.pdf}',result);self.assertIn(r'\label{fig:author-data}',result)
  from bibliography_delivery import active_text
  self.assertIn(r'\label{fig:rf-concept}',active_text(result))

 def test_owned_replacement_maps_references_and_single_column_marker(self):
  source=r'\subsection{Model}See \ref{fig:rf-old}.\begin{figure*}\includegraphics{figures/old.pdf}\label{fig:rf-old}\end{figure*}\begin{thebibliography}{9}\bibitem{A}Reference.\end{thebibliography}'
  spec=self.spec();spec.update(replaces=['old'],span='single')
  with tempfile.TemporaryDirectory() as folder,patch('publication_figures.render_concept',return_value={}):
   result,_=add_planned_figures(source,{'figures':[spec]},Path(folder))
  self.assertNotIn(r'\label{fig:rf-old}',result);self.assertIn(r'\ref{fig:rf-concept}',result)
  self.assertIn('% RF_SINGLE_COLUMN_FIGURE',result);self.assertIn(r'width=\columnwidth',result)
 def test_workflow_plan_has_its_own_validated_geometry(self):
  spec=self.spec();spec.update(layout='workflow',nodes=['Define claim','Lock independent split','Final test'])
  self.assertTrue(validate_plan(spec,['A']))
  spec['nodes']=['Too few']
  with self.assertRaises(ValueError):validate_plan(spec,['A'])
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
   self.assertIn('Original prose.',out);self.assertIn(r'\begin{figure}',out);self.assertIn(r'\cite{A}',out)
   self.assertEqual(report['added'],1);self.assertEqual(report['model_calls'],0)
   self.assertEqual(add_planned_figures(out,{'figures':[self.spec()]},Path(t))[0],out)
   already_canonicalized=out.replace(r'\bibitem{A}',r'\bibitem{canonicalA}')
   self.assertEqual(add_planned_figures(already_canonicalized,{'figures':[self.spec()]},Path(t))[0],already_canonicalized)
