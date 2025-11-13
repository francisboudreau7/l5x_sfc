
'''
Module to implement the Program class, which represents a single program within an L5X project.

'''
from l5x.tag import Scope
from l5x.dom import ElementDict
from l5x.rung import Rung
from l5x.ladder import Ladder
from l5x.sfc import SFC
from l5x.excel import create_tags_from_excel
import xml.etree.ElementTree as ElementTree
        


#placehold for the Routine class, which should be defined in a separate module
class Routine:
     def __init__(self, element, lang):
        self.element = element
        self.lang = lang
        #this implies that there is already a routines created, and we want to extract !
        #when we want to create routines, maybe use a separate constructor ?
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
        #only works if there's only one...need to generalize later
        #also need to pass in Tags from Program level to get Timers/Counters hidden in Steps
        #for now i will assume that the file contains new timer tags and counter tags for ladder already created...might need to auto-create later..elsewhere
        # Only initialize SFC if an SFC routine exists
        self.sfc = None
        if routines_element is not None:
            try:
                sfc_routine = self.routines['SFC']
                self.sfc = SFC(sfc_routine.sfc_element, element.find('Tags'))
            except KeyError:
                # No SFC routine in this program
                pass
                                

        super().__init__(element, lang)

    def convert_sfc_to_ladder_routines(self):
        #take the SFC object self.sfc
        #put it into the ladder_converter
        #ladder_converter(SFC) -> List(Routines)
        #append these routines into the program -> self.routines.append()
        pass

    def create_tags_from_excel(self, filepath):
        tags_element = self.element.find('Tags')
        if tags_element is None:
            raise RuntimeError("Program has no Tags element")
        
        create_tags_from_excel(tags_element, filepath)
        

        
        

    
    
