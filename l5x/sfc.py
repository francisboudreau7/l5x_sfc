import xml.etree.ElementTree as ElementTree
from l5x.dom import CDATA_TAG, ElementDict
import re

class SFC:
    def __init__(self, _sfc_content_element=None, program_tags_element=None):
        """
        SFC container for Steps, Transitions, Links, Timers and Counters.
        Accepts an XML element or will create an empty SFC element.
        """
        if _sfc_content_element is None:
            self.element = ElementTree.Element("SFC")
        else:
            self.element = _sfc_content_element
        
        
        # create internal maps of id -> object
        self._steps = self._get_elements_by_tag(self.element, 'Step', Step)
        self._transitions = self._get_elements_by_tag(self.element, 'Transition', Transition)

        # parse directed links (if present) and wire up Step <-> Transition relations
        # parse branches and legs
        self._branches = self._get_branches(self.element)
        # map leg id -> branch id
        self._leg_to_branch = {}
        for bid, br in self._branches.items():
            for leg in br.legs:
                self._leg_to_branch[leg] = bid

        self.directed_links = [DirectedLink(el) for el in self.element.findall('DirectedLink')]
        self._build_relations()
        
        # Load timer presets from program tags if provided
        if program_tags_element is not None:
            self._load_step_presets(program_tags_element)

    
    def _get_elements_by_tag(self, parent, tag, cls):
        """Return a dict mapping element ID -> instance(cls(element)).

        If parent is None or there are no elements, returns an empty dict.
        """
        out = {}
        if parent is None:
            return out
        for el in parent.findall(tag):
            eid = el.attrib.get('ID')
            if eid is None:
                continue
            out[eid] = cls(el)
        return out

    def _get_branches(self, parent):
        """Parse Branch elements and return mapping id->Branch."""
        out = {}
        if parent is None:
            return out
        for el in parent.findall('Branch'):
            bid = el.attrib.get('ID')
            if bid is None:
                continue
            legs = [l.attrib.get('ID') for l in el.findall('Leg') if l.attrib.get('ID')]
            flow = el.attrib.get('BranchFlow')
            brtype = el.attrib.get('BranchType')
            out[bid] = Branch(bid, legs, flow, brtype)
        return out


    @property
    def steps(self):
        """Return list of Step objects parsed from the SFC."""
        return list(self._steps.values())

    @property
    def transitions(self):
        """Return list of Transition objects parsed from the SFC."""
        return list(self._transitions.values())

    def get_step(self, id_):
        """Return Step object by ID or None."""
        return self._steps.get(id_)

    def get_transition(self, id_):
        """Return Transition object by ID or None."""
        return self._transitions.get(id_)

    def get_step_by_operand(self, operand_num):
        """Return Step object by operand number or None. """
        for step in self._steps.values():
            if step.int_operand() == int(operand_num):
                return step
        return None
    
    def get_transition_by_operand(self, operand_num):
        """Return Transition object by operand number or None. """
        for transition in self._transitions.values():
            if transition.int_operand() == int(operand_num):
                return transition
        return None

    @property
    def branchs(self):
        """Return list of Branch objects parsed from the SFC."""
        return list(self._branches.values())
    @property
    def actions_lookup_table(self):
        """Conveniance method to return dict mapping action text to list of step operand integers.
        {'action_text': [step_operand_int, step_operand_int, ...], ...}
        """
        return dict([(action,[step.int_operand() for step in steps]) for (action,steps) in self.actions])


    @property
    def actions(self):
        """Return list of tuples (action_text, [Step, Step, ...]) grouping steps by unique action content.
        
        Each unique action (ST content) is paired with all Step objects that contain it.
        If a step has multiple lines, they are joined with newlines.
        Actions are sorted alphabetically by their text content.
        
        Returns:
            List[Tuple[str, List[Step]]]: List of (action_text, steps_list) tuples,
                sorted by action_text alphabetically.
        
        Example:
            If step_014 and step_018 both have action "B:=0;", the result includes:
            ("B:=0;", [step_014_object, step_018_object])
        """
        action_map = {}
        
        # Group steps by their action content
        for step in self._steps.values():
            st_content = step.st
            if not st_content:
                continue
            
            # Join multiple lines with newlines to form the full action text
            action_text = '\n'.join(st_content)
            
            # Add step to the action's list
            if action_text not in action_map:
                action_map[action_text] = []
            action_map[action_text].append(step)
        
        # Sort steps within each action by their ID (numerically)
        for action_steps in action_map.values():
            action_steps.sort(key=lambda s: int(s.id) if s.id and s.id.isdigit() else float('inf'))
        
        # Return sorted list of tuples by action text
        return sorted(action_map.items(), key=lambda x: x[0])
    
    def _build_relations(self):
        """Walk DirectedLink entries and wire Step/Transition object references.

        For links that reference a Step on one side and a Transition on the other,
        create mutual references: Step._incoming/_outgoing refer to Transition objects
        and Transition._from/_to refer to Step objects.
        Links involving other node types are kept in `directed_links` for future use.
        """
        # build adjacency maps from directed links
        adj = {}
        radj = {}
        for dl in self.directed_links:
            frm = dl.from_id
            to = dl.to_id
            if frm is None or to is None:
                continue
            adj.setdefault(frm, []).append(to)
            radj.setdefault(to, []).append(frm)

        # incorporate branch -> leg or leg -> branch edges based on BranchFlow
        for bid, br in self._branches.items():
            if (br.flow or '').lower() == 'diverge':
                # branch -> legs
                for leg in br.legs:
                    adj.setdefault(bid, []).append(leg)
                    radj.setdefault(leg, []).append(bid)
            else:
                # converge (or unspecified) treat as legs -> branch
                for leg in br.legs:
                    adj.setdefault(leg, []).append(bid)
                    radj.setdefault(bid, []).append(leg)

        def node_type(nid):
            if nid in self._steps:
                return 'step'
            if nid in self._transitions:
                return 'transition'
            if nid in self._branches:
                return 'branch'
            if nid in self._leg_to_branch:
                return 'leg'
            return 'other'

        def find_immediate_transitions(start, forward=True):
            """Find immediate/next transitions from a start node (Step or Transition).
            
            Traversal may pass through Branch/Leg nodes but stops at the first Transition.
            Never crosses from one Step to another Step directly.
            """
            q = [start]
            seen = {start}
            found = set()
            while q:
                cur = q.pop(0)
                cur_type = node_type(cur)
                neighbors = adj.get(cur, []) if forward else radj.get(cur, [])
                for nb in neighbors:
                    if nb in seen:
                        continue
                    seen.add(nb)
                    nb_type = node_type(nb)
                    if nb_type == 'transition':
                        # found a transition, add it but don't explore beyond
                        found.add(nb)
                    elif nb_type in ('branch', 'leg'):
                        # pass through branch/leg nodes
                        q.append(nb)
                    # skip steps and other types
            return found

        # For each step, find immediate next/previous transitions
        for sid, step_obj in self._steps.items():
            # outgoing transitions: immediate next transitions (may pass through branch/leg)
            tr_ids = find_immediate_transitions(sid, forward=True)
            for tid in sorted(tr_ids, key=lambda x: int(x)):
                tr_obj = self._transitions.get(tid)
                if tr_obj is None:
                    continue
                step_obj.add_outgoing_transition(tr_obj)
                tr_obj.add_from_step(step_obj)

            # incoming transitions: immediate previous transitions
            tr_in_ids = find_immediate_transitions(sid, forward=False)
            for tid in sorted(tr_in_ids, key=lambda x: int(x)):
                tr_obj = self._transitions.get(tid)
                if tr_obj is None:
                    continue
                step_obj.add_incoming_transition(tr_obj)
                tr_obj.add_to_step(step_obj)

        # ensure deterministic ordering for all step/transition object lists
        for step_obj in self._steps.values():
            step_obj._incoming_objs.sort(key=lambda t: int(t.id))
            step_obj._outgoing_objs.sort(key=lambda t: int(t.id))
        for tr_obj in self._transitions.values():
            tr_obj._from_steps_objs.sort(key=lambda s: int(s.id))
            tr_obj._to_steps_objs.sort(key=lambda s: int(s.id))

    def _load_step_presets(self, program_tags_element):
        """Load timer preset values from program tags into Step objects.
        
        Looks for tags named after Step operands (e.g., 'Step_004') and extracts
        the PRE (preset) value from the SFC_STEP data type.
        
        Args:
            program_tags_element: XML element containing <Tag> elements from Program
        """
        if program_tags_element is None:
            return
        
        # For each Step, find its corresponding tag and extract preset
        for step in self._steps.values():
            operand = step.string_operand
            if operand is None:
                continue
            
            # Find the tag with matching name
            tag_elem = program_tags_element.find(f".//Tag[@Name='{operand}']")
            if tag_elem is None:
                continue
            
            # Extract PRE value from the decorated data structure
            # Look for <DataValueMember Name="PRE" ... Value="500"/>
            pre_elem = tag_elem.find(".//DataValueMember[@Name='PRE']")
            if pre_elem is not None:
                pre_value = pre_elem.attrib.get('Value')
                if pre_value is not None:
                    try:
                        step.preset = int(pre_value)
                    except ValueError:
                        pass
    def print_summary(self):
        print("")
        print("")
        print("SFC Summary:")
        print("")
        print(f"STEPS Total:{len(self.steps)}")
        print("___________________________________")
        print("")
        print("INCOMING -> STEP -> OUTGOING")
        print("___________________________________")
        for step in self.steps:
            step_ids = [step.id for step in self.steps]
            incoming_ids = [tr.int_operand() for tr in step.incoming_transitions]
            outgoing_ids = [tr.int_operand() for tr in step.outgoing_transitions]
            print(f"{str(incoming_ids):<10}{step.int_operand():<10}{str(outgoing_ids)}")
        print("")
        print("")
        print("")
        print(f"TRANSITIONS Total:{len(self.transitions)}")
        print("___________________________________")
        print("")
        print("|Transition|Incoming Step|Condition|")
        print("___________________________________")
        for transition in self.transitions:
            incoming_ids = [step.int_operand() for step in transition.incoming_steps]
            print(f"     {transition.int_operand():<10}{str(incoming_ids):<10}{transition.condition}")  
        print("")
        print("")
        print("")
        print("")
        print(f"ACTIONS Total:{len(self.actions)}")
        print("___________________________________")
        print("")
        print(f"{'Action':<25} Step")
        print("___________________________________")
        for action, steps in self.actions:
            step_ids = [step.id for step in steps]
            print(f"{action:<25} {step_ids}")
        print("")
        print("")
        print("")
        print("")
        print(f"TIMERS Total:{len([step for step in self.steps if step.preset is not None and step.preset != 0 ])}")
        print("___________________________________")
        print("")
        print(f"Step     Preset(ms)")
        print("___________________________________")
        for step in self.steps:
            if step.preset is not None and step.preset != 0:
                print(f"Step {step.int_operand():<10}{step.preset} ms")


class Step:
    def __init__(self, element=None):
        if element is None:
            self.element = ElementTree.Element("Step", attrib={})
        else:
            self.element = element
        # object references to Transition instances
        self._incoming_objs = []
        self._outgoing_objs = []
        # Timer preset value (in milliseconds)
        self.preset = None

    @property
    def id(self):
        return self.element.attrib.get("ID")

    @property
    def is_initial_step(self):
        """Return True if this is the initial step, False otherwise."""
        initial_step_attr = self.element.attrib.get("InitialStep", "false")
        return initial_step_attr.lower() == "true"

    @property
    def string_operand(self):
        return self.element.attrib.get("Operand")
    
    def int_operand(self):
        """Return Operand as integer if possible, else None."""
        op = self.string_operand
        if op is None:
            return None
        try:
            matches = re.findall("(\d+)", op)
            if matches:
                return int(matches[0])
            return None
        except ValueError:
            return None



    # STContent is usually stored as CDATA under STContent tag
    @property
    def st(self):
        """Return list of non-empty ST (Structured Text) lines from the step's actions.
        
        Parses content from Action/Body/STContent/Line elements.
        Returns a list of strings (line content), excluding empty lines.
        Returns an empty list if no content found.
        """
        st_lines = []
        
        # Look for Action elements within this Step....
        # can there be multiple? maybe not. 
        # Will change later if needed. Now we assume multiple actions possible.
        for action in self.element.findall('Action'):
            # Navigate to Body/STContent
            body = action.find('Body')
            if body is None:
                continue
            
            st_content = body.find('STContent')
            if st_content is None:
                continue
            
            # Extract text from each Line element
            for line_elem in st_content.findall('Line'):
                # Line can contain text directly or CDATA
                text = None
                
                # First try to get CDATA content
                cdata_elem = line_elem.find(CDATA_TAG)
                if cdata_elem is not None and cdata_elem.text:
                    text = cdata_elem.text
                # Otherwise, get direct text content
                elif line_elem.text:
                    text = line_elem.text
                
                if text:
                    # Only add non-empty lines (after stripping whitespace)
                    stripped = text.strip()
                    if stripped:
                        st_lines.append(stripped)
        
        return st_lines

    # object-level accessors
    def add_incoming_transition(self, transition):
        if transition not in self._incoming_objs:
            self._incoming_objs.append(transition)

    def add_outgoing_transition(self, transition):
        if transition not in self._outgoing_objs:
            self._outgoing_objs.append(transition)

    @property
    def incoming_transitions(self):
        """Return list of Transition objects incoming to this Step."""
        return list(self._incoming_objs)

    @property
    def outgoing_transitions(self):
        """Return list of Transition objects outgoing from this Step."""
        return list(self._outgoing_objs)


class Transition:
    def __init__(self, element=None):
        if element is None:
            self.element = ElementTree.Element("Transition", attrib={})
        else:
            self.element = element
        # object references to Step instances
        self._from_steps_objs = []
        self._to_steps_objs = []

    @property
    def id(self):
        return self.element.attrib.get("ID")
    
    @property
    def string_operand(self):
        return self.element.attrib.get("Operand")
    
    def int_operand(self):
        """Return Operand as integer if possible, else None."""
        op = self.string_operand
        if op is None:
            return None
        try:
            matches = re.findall("\\d+", op)
            if matches:
                return int(matches[0])
            return None
        except ValueError:
            return None

    @property
    def condition(self):
        #this looks an awful lot like the Step.st property
        #There might be a way to refactor later to avoid code duplication
        elem = self.element.find('Condition')
        conditions = []
        if elem is None:
            return None
        st_content = elem.find('STContent')
        if st_content is None:
                return None
            
            # Extract text from each Line element
        for line_elem in st_content.findall('Line'):
            # Line can contain text directly or CDATA
            text = None
                
            # First try to get CDATA content
            cdata_elem = line_elem.find(CDATA_TAG)
            if cdata_elem is not None and cdata_elem.text:
                text = cdata_elem.text
            # Otherwise, get direct text content
            elif line_elem.text:
                text = line_elem.text
                
            if text:
                # Only add non-empty lines (after stripping whitespace)
                stripped = text.strip()
                if stripped:
                    conditions.append(stripped)
        return conditions
        

    @property
    def from_steps(self):
        out = []
        for s in self.element.findall('From/Step'):
            if 'ID' in s.attrib:
                out.append(s.attrib['ID'])
            elif s.text:
                out.append(s.text)
        return out

    @property
    def to_steps(self):
        out = []
        for s in self.element.findall('To/Step'):
            if 'ID' in s.attrib:
                out.append(s.attrib['ID'])
            elif s.text:
                out.append(s.text)
        return out

    # object-level accessors
    def add_from_step(self, step):
        if step not in self._from_steps_objs:
            self._from_steps_objs.append(step)

    def add_to_step(self, step):
        if step not in self._to_steps_objs:
            self._to_steps_objs.append(step)

    @property
    def from_step_objects(self):
        """Return list of Step objects that come immediately before this Transition."""
        return list(self._from_steps_objs)

    @property
    def to_step_objects(self):
        """Return list of Step objects that come immediately after this Transition."""
        return list(self._to_steps_objs)
    
    @property
    def incoming_steps(self):
        """Alias for from_step_objects: Steps immediately before this Transition."""
        return self.from_step_objects
    
    @property
    def outgoing_steps(self):
        """Alias for to_step_objects: Steps immediately after this Transition."""
        return self.to_step_objects

class Branch:
    def __init__(self, id_, legs=None, flow=None, brtype=None):
        self.id = id_
        self.legs = legs or []
        self.flow = flow
        self.type = brtype


class DirectedLink:
    def __init__(self, element=None):
        if element is None:
            self.element = ElementTree.Element('DirectedLink', attrib={})
        else:
            self.element = element

    @property
    def from_id(self):
        return self.element.attrib.get('FromID')

    @property
    def to_id(self):
        return self.element.attrib.get('ToID')










