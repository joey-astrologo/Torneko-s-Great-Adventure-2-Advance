"""A Japanese glyph elsewhere in a scenario must not confirm an unrelated caller."""
import unittest

from tools.summarize_caller_audit import output_evidence


class CallerOutputEvidenceTests(unittest.TestCase):
    def sample(self):
        row = dict(call=0x080332AE, consumer=0x08000FB8, compiled_argument=0x08064248)
        event = dict(call=row['call'], consumer=row['consumer'], arguments=[0x03007000, row['compiled_argument'], 5, 0], frame=10)
        case = dict(case='sample', route_error=None, confirmed_japanese_output=True, calls=[event],
                    unclassified_glyphs=[dict(reader_source=None, final_queue=0, frame=11)],
                    final_queues=[dict(source=0x03007000, frame=11)])
        return row, case

    def test_matching_source_and_output_confirm(self):
        row, case = self.sample()
        self.assertEqual(output_evidence(row, case)[0]['final_queue_indices'], [0])

    def test_unrelated_japanese_output_does_not_confirm(self):
        row, case = self.sample()
        case['final_queues'][0]['source'] = 0x03006000
        self.assertEqual(output_evidence(row, case), [])

    def test_player_wrapper_copy_keeps_provenance(self):
        row, case = self.sample()
        case['calls'].append(dict(call=0x0801585C, consumer=0x08000FB8,
                                  arguments=[0x03006000,0x03007000,0,0],frame=10))
        case['final_queues'][0]['source'] = 0x03006000
        self.assertTrue(output_evidence(row, case))

    def test_incomplete_route_is_not_a_confirmation(self):
        row, case = self.sample()
        case['route_error'] = 'Expected caller not reached'
        self.assertEqual(output_evidence(row, case), [])
