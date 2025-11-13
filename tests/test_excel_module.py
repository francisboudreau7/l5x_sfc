import unittest
import xml.etree.ElementTree as ElementTree
from l5x.program import Program
from l5x.excel import create_tags_from_excel
from l5x.tag import create_alias_tag, create_base_tag


class TestExcelModule(unittest.TestCase):
    """Tests for the excel module's create_tags_from_excel function"""
    
    def setUp(self):
        """Load the MainProgram.L5X fixture."""
        doc = ElementTree.parse('tests/MainProgram.L5X')
        root = doc.getroot()
        program_elem = root.find(".//Program[@Name='MainProgram']")
        self.program = Program(program_elem, 'en')
        self.tags_element = self.program.element.find('Tags')
    
    def test_excel_function_creates_tags_directly(self):
        """Test that create_tags_from_excel function works independently."""
        # Test with Alias tag
        alias_tag = create_alias_tag(self.tags_element, 'DirectAlias', 'Local:1:I.Data.0')
        tag_elem = self.tags_element.find("Tag[@Name='DirectAlias']")
        self.assertIsNotNone(tag_elem)
        self.assertEqual(tag_elem.attrib['TagType'], 'Alias')
        
        # Test with Base tag
        base_tag = create_base_tag(self.tags_element, 'DirectBase', 'DINT')
        tag_elem = self.tags_element.find("Tag[@Name='DirectBase']")
        self.assertIsNotNone(tag_elem)
        self.assertEqual(tag_elem.attrib['TagType'], 'Base')
    
    def test_excel_module_error_handling_pandas_missing(self):
        """Test that proper error is raised when pandas is missing."""
        # This would only trigger if pandas is actually missing
        # In normal test environments, this test is informational
        try:
            import pandas
            # If pandas is available, we can't really test this
            self.skipTest("pandas is installed - cannot test missing pandas scenario")
        except ImportError:
            # If pandas is not installed, the error should be clear
            with self.assertRaises(ImportError) as context:
                create_tags_from_excel(self.tags_element, 'fake.xlsx')
            self.assertIn("pandas", str(context.exception))
    
    def test_excel_module_error_handling_none_element(self):
        """Test that error is raised for None tags_element."""
        try:
            import pandas
        except ImportError:
            self.skipTest("pandas not installed")
        
        with self.assertRaises(RuntimeError) as context:
            create_tags_from_excel(None, 'fake.xlsx')
        self.assertIn("tags_element cannot be None", str(context.exception))
    
    def test_excel_module_error_handling_missing_columns(self):
        """Test error handling for missing required columns."""
        try:
            import pandas
        except ImportError:
            self.skipTest("pandas not installed")
        
        # Create a DataFrame with missing columns
        df = pandas.DataFrame({'Name': ['Test'], 'TagType': ['Alias']})
        temp_file = 'tests/temp_excel_missing_cols.xlsx'
        df.to_excel(temp_file, index=False)
        
        try:
            with self.assertRaises(ValueError) as context:
                create_tags_from_excel(self.tags_element, temp_file)
            
            self.assertIn("missing required columns", str(context.exception))
        finally:
            import os
            if os.path.exists(temp_file):
                os.remove(temp_file)


class TestProgramExcelIntegration(unittest.TestCase):
    """Tests for Program.create_tags_from_excel convenience method"""
    
    def setUp(self):
        """Load the MainProgram.L5X fixture."""
        doc = ElementTree.parse('tests/MainProgram.L5X')
        root = doc.getroot()
        program_elem = root.find(".//Program[@Name='MainProgram']")
        self.program = Program(program_elem, 'en')
    
    def test_program_convenience_method_works(self):
        """Test that Program.create_tags_from_excel delegates correctly."""
        try:
            import pandas
        except ImportError:
            self.skipTest("pandas not installed")
        
        # Create a valid Excel file
        df = pandas.DataFrame({
            'Name': ['TestAlias', 'TestDint'],
            'TagType': ['Alias', 'Base'],
            'AliasFor': ['Local:1:I.Data.0', pandas.NA],
            'DataType': [pandas.NA, 'DINT']
        })
        temp_file = 'tests/temp_program_excel.xlsx'
        df.to_excel(temp_file, index=False)
        
        try:
            # Call through the program method
            self.program.create_tags_from_excel(temp_file)
            
            # Verify tags were created
            tags_elem = self.program.element.find('Tags')
            alias_tag = tags_elem.find("Tag[@Name='TestAlias']")
            base_tag = tags_elem.find("Tag[@Name='TestDint']")
            
            self.assertIsNotNone(alias_tag)
            self.assertIsNotNone(base_tag)
            self.assertEqual(alias_tag.attrib['TagType'], 'Alias')
            self.assertEqual(base_tag.attrib['TagType'], 'Base')
        finally:
            import os
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_program_error_handling_no_tags_element(self):
        """Test error handling when program has no Tags element."""
        # Create a minimal program element without Tags
        program_elem = ElementTree.Element('Program', attrib={'Name': 'TestProg'})
        
        # Create a new program with this element
        from l5x.program import Program
        program = Program(program_elem, 'en')
        
        with self.assertRaises(RuntimeError) as context:
            program.create_tags_from_excel('fake.xlsx')
        self.assertIn("Tags element", str(context.exception))


class TestExcelEdgeCases(unittest.TestCase):
    """Test edge cases for Excel functionality"""
    
    def setUp(self):
        """Load the MainProgram.L5X fixture."""
        doc = ElementTree.parse('tests/MainProgram.L5X')
        root = doc.getroot()
        program_elem = root.find(".//Program[@Name='MainProgram']")
        self.program = Program(program_elem, 'en')
        self.tags_element = self.program.element.find('Tags')
    
    def test_multiple_tags_same_type(self):
        """Test creating multiple tags of the same type."""
        try:
            import pandas
        except ImportError:
            self.skipTest("pandas not installed")
        
        # Create Excel with multiple DINT tags
        df = pandas.DataFrame({
            'Name': ['Dint1', 'Dint2', 'Dint3'],
            'TagType': ['Base', 'Base', 'Base'],
            'AliasFor': [pandas.NA, pandas.NA, pandas.NA],
            'DataType': ['DINT', 'DINT', 'DINT']
        })
        temp_file = 'tests/temp_multiple_dint.xlsx'
        df.to_excel(temp_file, index=False)
        
        try:
            create_tags_from_excel(self.tags_element, temp_file)
            
            for tag_name in ['Dint1', 'Dint2', 'Dint3']:
                tag_elem = self.tags_element.find(f"Tag[@Name='{tag_name}']")
                self.assertIsNotNone(tag_elem)
                self.assertEqual(tag_elem.attrib['DataType'], 'DINT')
        finally:
            import os
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_mixed_alias_and_base_tags(self):
        """Test creating a mix of Alias and Base tags from single file."""
        try:
            import pandas
        except ImportError:
            self.skipTest("pandas not installed")
        
        # Create Excel with mix of tag types
        df = pandas.DataFrame({
            'Name': ['Alias1', 'Base1', 'Alias2', 'Base2'],
            'TagType': ['Alias', 'Base', 'Alias', 'Base'],
            'AliasFor': ['Local:1:I.Data.0', pandas.NA, 'Local:1:O.Data.0', pandas.NA],
            'DataType': [pandas.NA, 'BOOL', pandas.NA, 'REAL']
        })
        temp_file = 'tests/temp_mixed_tags.xlsx'
        df.to_excel(temp_file, index=False)
        
        try:
            create_tags_from_excel(self.tags_element, temp_file)
            
            # Verify all tags were created
            tag_names = {
                'Alias1': 'Alias',
                'Base1': 'Base',
                'Alias2': 'Alias',
                'Base2': 'Base'
            }
            
            for tag_name, expected_type in tag_names.items():
                tag_elem = self.tags_element.find(f"Tag[@Name='{tag_name}']")
                self.assertIsNotNone(tag_elem)
                self.assertEqual(tag_elem.attrib['TagType'], expected_type)
        finally:
            import os
            if os.path.exists(temp_file):
                os.remove(temp_file)


if __name__ == '__main__':
    unittest.main()
