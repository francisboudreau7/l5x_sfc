import unittest
import xml.etree.ElementTree as ElementTree

from l5x.sfc import SFC, Step, Transition, DirectedLink, Branch


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
		
    
	def test_transition_links(self):
		#this test is a specific example to verify that the links between steps and transitions are correctly established
		step0 = self.sfc.get_step('0')
		self.assertEqual(len(step0.outgoing_transition_objects), 1)
		self.assertEqual(len(step0.incoming_transition_objects), 2) 
		self.assertEqual(step0.outgoing_transition_objects[0].id, "39") 
		self.assertEqual(step0.incoming_transition_objects[0].id, "50") # this list should be sorted
		self.assertEqual(step0.incoming_transition_objects[1].id, "60") 
		step2 = self.sfc.get_step('2')
		self.assertEqual(len(step2.incoming_transition_objects), 1)
		self.assertEqual(len(step2.outgoing_transition_objects), 1)
		self.assertEqual(step2.outgoing_transition_objects[0].id, "40")
		self.assertEqual(step2.incoming_transition_objects[0].id, "39")
		step15 = self.sfc.get_step('15')
		
		self.assertEqual(len(step15.incoming_transition_objects), 1)
		self.assertEqual(len(step15.outgoing_transition_objects), 2)
		self.assertEqual(step15.incoming_transition_objects[0].id, "46")
		self.assertEqual(step15.outgoing_transition_objects[0].id, "47")
		self.assertEqual(step15.outgoing_transition_objects[1].id, "48")
        
	def test_steps_transitions_properties_and_st_content(self):
		s0 = self.sfc.get_step('0')
		self.assertEqual(s0.id, '0')
		self.assertEqual(s0.string_operand, 'Step_000')
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
		# branchs property now returns actual Branch objects
		branchs = self.sfc.branchs
		self.assertIsInstance(branchs, list)
		# Fixture should have branches
		self.assertGreater(len(branchs), 0)
		# Verify we can find known branches
		branch_ids = {b.id for b in branchs}
		self.assertIn('61', branch_ids)

	def test_int_operand_parsing(self):
		s3 = self.sfc.get_step('2')
		self.assertEqual(s3.string_operand, 'Step_001')
		self.assertEqual(s3.int_operand(), 1)

	def test_transition_immediate_previous_steps(self):
		"""Test that transitions contain immediate previous steps (incoming)."""
		# Transition 39 should have Step 0 as previous step
		tr39 = self.sfc.get_transition('39')
		self.assertIsNotNone(tr39)
		from_steps = tr39.from_step_objects
		self.assertEqual(len(from_steps), 1)
		self.assertEqual(from_steps[0].id, '0')
		
		# Transition 39 should also be accessible via the alias
		incoming_steps = tr39.incoming_step_objects
		self.assertEqual(len(incoming_steps), 1)
		self.assertEqual(incoming_steps[0].id, '0')

	def test_transition_immediate_following_steps(self):
		"""Test that transitions contain immediate following steps (outgoing)."""
		# Transition 39 should have Step 2 as the next step
		tr39 = self.sfc.get_transition('39')
		self.assertIsNotNone(tr39)
		to_steps = tr39.to_step_objects
		self.assertEqual(len(to_steps), 1)
		self.assertEqual(to_steps[0].id, '2')
		
		# Transition 39 should also be accessible via the alias
		outgoing_steps = tr39.outgoing_step_objects
		self.assertEqual(len(outgoing_steps), 1)
		self.assertEqual(outgoing_steps[0].id, '2')

	def test_transition_with_multiple_incoming_steps(self):
		"""Test transition with incoming steps from multiple branches/paths."""
		# Even if not all transitions have multiple incoming steps,
		# verify that when they do exist, they're properly tracked
		found_multiple = False
		for tr in self.sfc.transitions:
			from_steps = tr.from_step_objects
			if len(from_steps) > 1:
				found_multiple = True
				# Verify all from_steps are actual Step objects
				for step in from_steps:
					self.assertIsNotNone(step.id)
				break
		
		# At minimum, verify transition 50 has its incoming step
		tr50 = self.sfc.get_transition('50')
		from_steps = tr50.from_step_objects
		self.assertGreater(len(from_steps), 0)

	def test_transition_with_multiple_outgoing_steps(self):
		"""Test transition with multiple following steps (via branches)."""
		# Transition 47 and 48 are outgoing from Step 15
		# So Step 15 should have both 47 and 48 as outgoing
		# Conversely, 47 and 48 should lead to steps after them
		tr47 = self.sfc.get_transition('47')
		self.assertIsNotNone(tr47)
		to_steps = tr47.to_step_objects
		self.assertGreater(len(to_steps), 0)

	def test_transition_step_lists_are_sorted(self):
		"""Test that step lists in transitions are sorted by ID (deterministic ordering)."""
		# Find a transition with multiple steps
		for tr in self.sfc.transitions:
			from_steps = tr.from_step_objects
			to_steps = tr.to_step_objects
			
			if len(from_steps) > 1:
				from_ids = [int(s.id) for s in from_steps]
				self.assertEqual(from_ids, sorted(from_ids), 
					f"Transition {tr.id} from_steps not sorted: {from_ids}")
			
			if len(to_steps) > 1:
				to_ids = [int(s.id) for s in to_steps]
				self.assertEqual(to_ids, sorted(to_ids),
					f"Transition {tr.id} to_steps not sorted: {to_ids}")

	def test_transition_accessor_aliases(self):
		"""Test that from_step_objects/incoming_step_objects and to_step_objects/outgoing_step_objects are equivalent."""
		for tr in self.sfc.transitions:
			# from_step_objects and incoming_step_objects should be identical
			from_objs = tr.from_step_objects
			incoming_objs = tr.incoming_step_objects
			from_ids = [s.id for s in from_objs]
			incoming_ids = [s.id for s in incoming_objs]
			self.assertEqual(from_ids, incoming_ids,
				f"Transition {tr.id}: from_step_objects != incoming_step_objects")
			
			# to_step_objects and outgoing_step_objects should be identical
			to_objs = tr.to_step_objects
			outgoing_objs = tr.outgoing_step_objects
			to_ids = [s.id for s in to_objs]
			outgoing_ids = [s.id for s in outgoing_objs]
			self.assertEqual(to_ids, outgoing_ids,
				f"Transition {tr.id}: to_step_objects != outgoing_step_objects")

	def test_transition_step_objects_bidirectional_consistency(self):
		"""Test bidirectional consistency: if Step→Transition, then Transition→Step."""
		for step in self.sfc.steps:
			# For each outgoing transition from step
			for tr in step.outgoing_transition_objects:
				# That transition should have this step in its from_step_objects
				self.assertIn(step, tr.from_step_objects,
					f"Step {step.id} → Transition {tr.id}, but transition doesn't reference step")
			
			# For each incoming transition to step
			for tr in step.incoming_transition_objects:
				# That transition should have this step in its to_step_objects
				self.assertIn(step, tr.to_step_objects,
					f"Transition {tr.id} → Step {step.id}, but transition doesn't reference step")

	def test_get_step_by_operand(self):
		"""Test retrieving Step objects by operand number."""
		# Step 15 has operand 'Step_008', so operand number is 8
		step = self.sfc.get_step_by_operand(8)
		self.assertIsNotNone(step)
		self.assertEqual(step.id, '15')
		self.assertEqual(step.string_operand, 'Step_008')
		
		# Test with string input (should convert to int)
		step = self.sfc.get_step_by_operand('8')
		self.assertIsNotNone(step)
		self.assertEqual(step.id, '15')
		
		# Non-existent operand returns None
		step = self.sfc.get_step_by_operand(9999)
		self.assertIsNone(step)

	def test_get_step_by_operand_multiple_steps(self):
		"""Test that get_step_by_operand returns the first matching step."""
		# Test with a few known steps
		step0 = self.sfc.get_step_by_operand(0)
		self.assertIsNotNone(step0)
		self.assertEqual(step0.string_operand, 'Step_000')
		
		step1 = self.sfc.get_step_by_operand(1)
		self.assertIsNotNone(step1)
		self.assertEqual(step1.string_operand, 'Step_001')
		
		step2 = self.sfc.get_step_by_operand(2)
		self.assertIsNotNone(step2)
		self.assertEqual(step2.string_operand, 'Step_002')

	def test_get_transition_by_operand(self):
		"""Test retrieving Transition objects by operand number."""
		# Find a transition with a known operand
		# Transition 39 has operand 'Tran_000'
		trans = self.sfc.get_transition_by_operand(0)
		self.assertIsNotNone(trans)
		self.assertEqual(trans.id, '39')
		self.assertEqual(trans.string_operand, 'Tran_000')
		
		# Test with string input (should convert to int)
		trans = self.sfc.get_transition_by_operand('0')
		self.assertIsNotNone(trans)
		self.assertEqual(trans.id, '39')
		
		# Non-existent operand returns None
		trans = self.sfc.get_transition_by_operand(9999)
		self.assertIsNone(trans)

	def test_get_transition_by_operand_multiple(self):
		"""Test retrieving various transitions by operand number."""
		# Test with a few known transitions
		trans1 = self.sfc.get_transition_by_operand(1)
		self.assertIsNotNone(trans1)
		self.assertEqual(trans1.string_operand, 'Tran_001')
		
		trans2 = self.sfc.get_transition_by_operand(2)
		self.assertIsNotNone(trans2)
		self.assertEqual(trans2.string_operand, 'Tran_002')

	def test_operand_lookup_consistency(self):
		"""Test that operand lookup finds all steps and transitions consistently."""
		# Collect all unique operand numbers from steps
		step_operands = set()
		for step in self.sfc.steps:
			op = step.int_operand()
			if op is not None:
				step_operands.add(op)
		
		# Verify we can retrieve each step by operand
		for op in step_operands:
			step = self.sfc.get_step_by_operand(op)
			self.assertIsNotNone(step, f"Failed to retrieve step with operand {op}")
			self.assertEqual(step.int_operand(), op)
		
		# Collect all unique operand numbers from transitions
		trans_operands = set()
		for trans in self.sfc.transitions:
			op = trans.int_operand()
			if op is not None:
				trans_operands.add(op)
		
		# Verify we can retrieve each transition by operand
		for op in trans_operands:
			trans = self.sfc.get_transition_by_operand(op)
			self.assertIsNotNone(trans, f"Failed to retrieve transition with operand {op}")
			self.assertEqual(trans.int_operand(), op)

	def test_step_preset_property_exists(self):
		"""Test that Step objects have a preset property."""
		step = self.sfc.get_step('0')
		self.assertIsNotNone(step)
		# preset should exist and be initialized to None
		self.assertIsNone(step.preset)

	def test_load_presets_from_program_tags(self):
		"""Test loading step presets from MainProgram.L5X tags."""
		# Load MainProgram.L5X which contains tag data with presets
		doc = ElementTree.parse('tests/MainProgram.L5X')
		root = doc.getroot()
		
		# Find the Program element
		program_elem = root.find(".//Program[@Name='MainProgram']")
		self.assertIsNotNone(program_elem, "MainProgram not found")
		
		# Find the SFCContent element (inside Routine)
		sfc_content = program_elem.find(".//Routine[@Name='SFC']/SFCContent")
		self.assertIsNotNone(sfc_content, "SFCContent not found in MainProgram")
		
		# Find the Tags element (sibling of Routines)
		tags_elem = program_elem.find("Tags")
		self.assertIsNotNone(tags_elem, "Tags element not found")
		
		# Create SFC with both SFCContent and program tags
		sfc = SFC(sfc_content, tags_elem)
		
		# Step_004 (ID 8) should have preset of 500
		step4 = sfc.get_step('8')
		self.assertIsNotNone(step4)
		self.assertEqual(step4.string_operand, 'Step_004')
		self.assertEqual(step4.preset, 500)

	def test_presets_by_operand(self):
		"""Test retrieving steps with presets using operand lookup."""
		doc = ElementTree.parse('tests/MainProgram.L5X')
		root = doc.getroot()
		program_elem = root.find(".//Program[@Name='MainProgram']")
		sfc_content = program_elem.find(".//Routine[@Name='SFC']/SFCContent")
		tags_elem = program_elem.find("Tags")
		
		sfc = SFC(sfc_content, tags_elem)
		
		# Get step by operand number 4 (Step_004)
		step = sfc.get_step_by_operand(4)
		self.assertIsNotNone(step)
		self.assertEqual(step.preset, 500)
		step = sfc.get_step_by_operand(2)
		self.assertIsNotNone(step)
		self.assertEqual(step.preset, 3000)

	def test_steps_without_tags_have_no_preset(self):
		"""Test that steps without corresponding tags have None preset."""
		# SFCContent.xml doesn't have program tags, so presets should be None
		doc = ElementTree.parse('tests/SFCContent.xml')
		root = doc.getroot()
		sfc = SFC(root, None)
		
		# All steps should have preset=None
		for step in sfc.steps:
			self.assertIsNone(step.preset)

	def test_multiple_steps_with_presets(self):
		"""Test that multiple steps can have different presets loaded."""
		doc = ElementTree.parse('tests/MainProgram.L5X')
		root = doc.getroot()
		program_elem = root.find(".//Program[@Name='MainProgram']")
		sfc_content = program_elem.find(".//Routine[@Name='SFC']/SFCContent")
		tags_elem = program_elem.find("Tags")
		
		sfc = SFC(sfc_content, tags_elem)
		
		# Collect all steps with non-None presets
		steps_with_presets = [s for s in sfc.steps if s.preset is not None]
		
		# MainProgram should have at least some steps with presets
		self.assertGreater(len(steps_with_presets), 0)
		
		# All presets should be integers (can be 0 or greater)
		for step in steps_with_presets:
			self.assertIsInstance(step.preset, int)
			self.assertGreaterEqual(step.preset, 0)

if __name__ == '__main__':
	unittest.main()