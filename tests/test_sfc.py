import unittest
import xml.etree.ElementTree as ElementTree

from l5x.sfc import SFC, Step, Transition, Link, DirectedLink, Branch


class SFCParsing(unittest.TestCase):
	def setUp(self):
		# load the provided SFCContent.xml fixture
		doc = ElementTree.parse('tests/SFCContent.xml')
		self.root = doc.getroot()
		self.sfc = SFC(self.root)

		# empty SFC for edge-case testing
		self.empty_sfc = SFC()

	def test_steps_and_transitions_lookup(self):
		# some known nodes exist in the fixture
		self.assertIsNotNone(self.sfc.get_step('4'))
		self.assertIsNotNone(self.sfc.get_step('15'))
		self.assertIsNotNone(self.sfc.get_transition('42'))

		# non-existent lookup returns None
		self.assertIsNone(self.sfc.get_step('9999'))
		self.assertIsNone(self.sfc.get_transition('9999'))

	def test_get_elements_by_tag_with_none_and_empty(self):
		# calling internal helper with None returns empty dict
		self.assertEqual(self.empty_sfc._get_elements_by_tag(None, 'Step', Step), {})
		# calling with element that has no matching tags returns empty dict
		foo = ElementTree.Element('Foo')
		self.assertEqual(self.empty_sfc._get_elements_by_tag(foo, 'Step', Step), {})

	def test_branches_and_leg_mapping(self):
		# branches parsed
		branches = self.sfc._branches
		self.assertIn('61', branches)
		self.assertIn('64', branches)
		b61 = branches['61']
		self.assertIsInstance(b61, Branch)
		# legs mapping
		self.assertIn('62', self.sfc._leg_to_branch)
		self.assertEqual(self.sfc._leg_to_branch['62'], '61')

	def test_directed_links_and_directedlink_props(self):
		dl_list = self.sfc.directed_links
		self.assertTrue(len(dl_list) > 0)
		# find a known directed link
		found = [d for d in dl_list if d.from_id == '4' and d.to_id == '61']
		self.assertTrue(found)
		d = found[0]
		self.assertIsInstance(d, DirectedLink)
		self.assertEqual(d.from_id, '4')
		self.assertEqual(d.to_id, '61')

	def test_steps_transitions_properties_and_st_content(self):
		s0 = self.sfc.get_step('0')
		self.assertEqual(s0.id, '0')
		self.assertEqual(s0.operand, 'Step_000')
		# In the raw SFCContent fixture STContent is nested under Action/Body
		# and is not converted into the CDATAContent element; Step.st will be None
		self.assertIsNone(s0.st)

	def test_id_based_vs_object_links(self):
		# ID-based incoming/outgoing lists on Step are not used in this fixture (empty)
		s2 = self.sfc.get_step('2')
		self.assertEqual(s2.incoming_transitions, [])
		# But object-level incoming transitions should include transition 39
		incoming_objs = {t.id for t in s2.incoming_transition_objects}
		self.assertIn('39', incoming_objs)

	def test_transition_condition_and_object_links(self):
		tr42 = self.sfc.get_transition('42')
		self.assertIsNotNone(tr42)
		# Condition text in the fixture is nested; Transition.condition will be None
		self.assertIsNone(tr42.condition)
		# object-level to_steps should include step '8'
		to_ids = {s.id for s in tr42.to_step_objects}
		self.assertIn('8', to_ids)


	def test_branchs_property(self):
		# branchs property currently returns an empty list
		self.assertEqual(self.sfc.branchs, [])


if __name__ == '__main__':
	unittest.main()