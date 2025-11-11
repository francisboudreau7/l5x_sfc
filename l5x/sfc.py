import xml.etree.ElementTree as ElementTree
from l5x.dom import CDATA_TAG, ElementDict


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
        
        
        steps_elements = self.element.findall('Step')
        self.steps =  dict([(el.attrib.get("ID"),Step(el),) for el in steps_elements])

    def steps(self):
        return self.steps

    @property
    def transitions(self):
        return [Transition(el) for el in self.element.findall('Transition')]


    @property
    def links(self):
        return [Link(el) for el in self.element.findall('Link')]

    @property
    def branchs(self):
        pass


class Step:
    def __init__(self, element=None):
        if element is None:
            self.element = ElementTree.Element("Step", attrib={})
        else:
            self.element = element

    @property
    def id(self):
        return self.element.attrib.get("ID")


    @property
    def operand(self):
        return self.element.attrib.get("Operand")

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


class Transition:
    def __init__(self, element=None):
        if element is None:
            self.element = ElementTree.Element("Transition", attrib={})
        else:
            self.element = element

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


class Link:
    def __init__(self, element=None):
        if element is None:
            self.element = ElementTree.Element("Link", attrib={})
        else:
            self.element = element

    @property
    def step_id(self):
        # Link may reference a Step by attribute or child
        if 'StepID' in self.element.attrib:
            return self.element.attrib['StepID']
        step = self.element.find('Step')
        if step is not None:
            return step.attrib.get('ID') or step.text
        return None
    

    @property
    def transition_id(self):
        if 'TransitionID' in self.element.attrib:
            return self.element.attrib['TransitionID']
        t = self.element.find('Transition')
        if t is not None:
            return t.attrib.get('ID') or t.text
        return None










