
'''
Module to implement the Program class, which represents a single program within an L5X project.

'''
from l5x.tag import Scope
from l5x.dom import ElementDict
from l5x.rung import Rung
from l5x.ladder import Ladder
from l5x.sfc import SFC
        


#placehold for the Routine class, which should be defined in a separate module
class Routine:
     def __init__(self, element, lang):
        self.element = element
        self.lang = lang
        
        if self.element.attrib.get("Type") == "RLL":
            self.rll_content_element = element.find("RLLContent")
            logic_list = self.rll_content_element.findall("Rung")
            if logic_list is None:
                logic_list = []
            rung_list = [Rung(rung_element, lang) for rung_element in logic_list]
            self.ladder = Ladder(element=self.rll_content_element, rungs=rung_list)
        if self.element.attrib.get("Type") == "SFC":
            self.sfc_element = element.find("SFCContent")



class Program(Scope):
    def __init__(self, element, lang):
        #attributes that have to do with XML
        self.lang = lang
        self.element = element

        #attributes that involve the PLC data
        routines_element = element.find('Routines')
        self.routines = ElementDict(parent=routines_element,
                                    key_attr='Name',
                                    value_type=Routine,
                                    value_args=[lang])
        
        self.sfc = SFC(self.routines['SFC'].sfc_element) #only works if there's only one 
                                

        super().__init__(element, lang)

        
        

    
    
