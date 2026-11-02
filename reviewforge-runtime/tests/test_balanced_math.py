import unittest
from unittest.mock import patch
from math_layout import pack_rows, unfold_continuation


class BalancedMathTests(unittest.TestCase):
    def test_independent_relations_keep_a_natural_break_after_the_comma(self):
        from math_layout import breakpoints
        cuts=breakpoints('a=b, c=d')
        self.assertEqual(cuts[4],0)
        self.assertGreater(cuts[6],cuts[4])

    def test_new_relation_starts_at_lhs_without_an_inline_spacing_indent(self):
        from math_layout import aligned_rows
        result=aligned_rows(['a=b,',r'\qquad c=d'])
        self.assertIn('\nc&=d',result)
        self.assertNotIn(r'\qquad',result)

    def test_equality_chain_prefers_complete_first_relation(self):
        from math_layout import breakpoints,aligned_rows
        cuts=breakpoints('r=y-z=a+b')
        self.assertGreater(cuts[1],cuts[5])
        self.assertIn('\n&-z=a+b',aligned_rows(['r=y','-z=a+b']))
        self.assertNotIn('-z&=',aligned_rows(['r=y','-z=a+b']))

    def test_untagged_author_aligned_system_is_preserved(self):
        from math_layout import balanced_math
        source=r'\begin{document}\[\begin{aligned}&x_{\mathrm{longname}}=1\\&-y_{\mathrm{longname}}=2\end{aligned}\]\end{document}'
        with patch('math_layout.tex_widths') as measure:
            self.assertEqual(balanced_math(source,'.'),(source,0))
        measure.assert_not_called()

    def test_expired_probe_budget_does_not_launch_compiler(self):
        from math_layout import tex_widths
        with patch('math_layout.shutil.which',return_value='xelatex'),patch('math_layout.time.time',return_value=100),patch('bounded_process.run_process_tree') as launch:
            with self.assertRaises(TimeoutError):tex_widths(['a=b'],'', '.',deadline=102)
        launch.assert_not_called()

    def test_short_equation_is_not_split_at_every_operator(self):
        text='R2=R1+d,  D2=D1+d'
        cuts={2:4,5:2,10:0,12:4,15:2}
        widths={(a,b):float(b-a) for a in [0,*cuts] for b in [*cuts,len(text)] if a<b}
        self.assertEqual(pack_rows(text,cuts,widths,100),[text])

    def test_two_complete_relations_are_preferred_over_operator_fragments(self):
        text='a=b+c, d=e+f'
        cuts={1:4,3:2,7:0,8:4,10:2}
        widths={(a,b):float(b-a) for a in [0,*cuts] for b in [*cuts,len(text)] if a<b}
        self.assertEqual(pack_rows(text,cuts,widths,7),['a=b+c,','d=e+f'])

    def test_only_exporter_continuations_are_unfolded(self):
        self.assertEqual(unfold_continuation(r'\begin{aligned}&R2\\&=R1\\&+d\end{aligned}',exporter_owned=True),'R2 =R1 +d')
        original=r'\begin{aligned}x&=1\\y&=2\end{aligned}'
        self.assertEqual(unfold_continuation(original),original)
