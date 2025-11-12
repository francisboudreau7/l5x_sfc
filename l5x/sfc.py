import xml.etree.ElementTree as ElementTree
from l5x.dom import CDATA_TAG, ElementDict
import re

class SFC:
    def __init__(self, _sfc_content_element=None):
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
        """Return Step object by operand number or None.
        
        Operand format for Steps is typically 'Step_XXX' where XXX is the operand number.
        For example, Step_008 has operand number 8.
        
        Args:
            operand_num: The numeric operand to search for (int or str)
        
        Returns:
            Step object with matching operand number, or None if not found.
        """
        for step in self._steps.values():
            if step.int_operand() == int(operand_num):
                return step
        return None
    
    def get_transition_by_operand(self, operand_num):
        """Return Transition object by operand number or None.
        
        Operand format for Transitions is typically 'Tran_XXX' where XXX is the operand number.
        
        Args:
            operand_num: The numeric operand to search for (int or str)
        
        Returns:
            Transition object with matching operand number, or None if not found.
        """
        for transition in self._transitions.values():
            if transition.int_operand() == int(operand_num):
                return transition
        return None

    @property
    def branchs(self):
        """Return list of Branch objects parsed from the SFC."""
        return list(self._branches.values())
    
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

        def bfs(start, forward=True, target_kind='transition'):
            """Return set of node ids of kind target_kind reachable from start.

            forward=True follows adj, otherwise uses radj (reverse).
            """
            q = [start]
            seen = {start}
            found = set()
            while q:
                cur = q.pop(0)
                # check current
                if node_type(cur) == target_kind:
                    found.add(cur)
                    # do not stop; continue to find all reachable targets
                # explore neighbors
                neighbors = adj.get(cur, []) if forward else radj.get(cur, [])
                for nb in neighbors:
                    if nb in seen:
                        continue
                    seen.add(nb)
                    q.append(nb)
            return found

        # For each step, find transitions reachable forward (outgoing) and backward (incoming)
        for sid, step_obj in self._steps.items():
            # outgoing transitions: BFS forward from step id
            tr_ids = bfs(sid, forward=True, target_kind='transition')
            for tid in tr_ids:
                tr_obj = self._transitions.get(tid)
                if tr_obj is None:
                    continue
                step_obj.add_outgoing_transition(tr_obj)
                tr_obj.add_from_step(step_obj)

            # incoming transitions: BFS backward from step id
            tr_in_ids = bfs(sid, forward=False, target_kind='transition')
            for tid in tr_in_ids:
                tr_obj = self._transitions.get(tid)
                if tr_obj is None:
                    continue
                step_obj.add_incoming_transition(tr_obj)
                tr_obj.add_to_step(step_obj)


class Step:
    def __init__(self, element=None):
        if element is None:
            self.element = ElementTree.Element("Step", attrib={})
        else:
            self.element = element
        # object references to Transition instances
        self._incoming_objs = []
        self._outgoing_objs = []

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
            matches = re.findall("(\d+)", op)
            if matches:
                return int(matches[0])
            return None
        except ValueError:
            return None



    # STContent is usually stored as CDATA under STContent tag
    @property
    def st(self):
        elem = self.element.find('STContent')
        if elem is None:
            return None
        cdata = elem.find(CDATA_TAG)
        return None if cdata is None else cdata.text



    # Convenience accessors for transitions linking to/from this step
    @property
    def incoming_transitions(self):
        # returns list of transition IDs referenced in <From> children, if any
        out = []
        from_parent = self.element.find('From')
        if from_parent is None:
            return out
        for t in from_parent.findall('Transition'):
            if 'ID' in t.attrib:
                out.append(t.attrib['ID'])
            elif t.text:
                out.append(t.text)
        return out

    @property
    def outgoing_transitions(self):
        out = []
        to_parent = self.element.find('To')
        if to_parent is None:
            return out
        for t in to_parent.findall('Transition'):
            if 'ID' in t.attrib:
                out.append(t.attrib['ID'])
            elif t.text:
                out.append(t.text)
        return out

    # object-level accessors
    def add_incoming_transition(self, transition):
        if transition not in self._incoming_objs:
            self._incoming_objs.append(transition)

    def add_outgoing_transition(self, transition):
        if transition not in self._outgoing_objs:
            self._outgoing_objs.append(transition)

    @property
    def incoming_transition_objects(self):
        """Return list of Transition objects incoming to this Step."""
        return list(self._incoming_objs)

    @property
    def outgoing_transition_objects(self):
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
    def condition(self):
        # condition may be stored as CDATA under Condition tag
        elem = self.element.find('Condition')
        if elem is None:
            return None
        cdata = elem.find(CDATA_TAG)
        return None if cdata is None else cdata.text

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
        return list(self._from_steps_objs)

    @property
    def to_step_objects(self):
        return list(self._to_steps_objs)


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










