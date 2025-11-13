import unittest
import xml.etree.ElementTree as ElementTree
from l5x.program import Program
from l5x.tag import create_alias_tag, create_base_tag


class TestTagFactoryFunctions(unittest.TestCase):
    """Tests for tag factory functions in tag.py"""
    
    def setUp(self):
        """Load the MainProgram.L5X fixture."""
        doc = ElementTree.parse('tests/MainProgram.L5X')
        root = doc.getroot()
        program_elem = root.find(".//Program[@Name='MainProgram']")
        self.program = Program(program_elem, 'en')
        self.tags_element = self.program.element.find('Tags')
    
    def test_create_alias_tag_success(self):
        """Test successfully creating an Alias tag."""
        alias_tag = create_alias_tag(self.tags_element, 'MyAlias', 'Local:1:I.Data.0')
        
        # Verify the tag was created in XML
        tag_elem = self.tags_element.find("Tag[@Name='MyAlias']")
        self.assertIsNotNone(tag_elem)
        self.assertEqual(tag_elem.attrib['TagType'], 'Alias')
        self.assertEqual(tag_elem.attrib['AliasFor'], 'Local:1:I.Data.0')
        self.assertEqual(tag_elem.attrib['Radix'], 'Decimal')
        self.assertEqual(tag_elem.attrib['ExternalAccess'], 'Read/Write')
    
    def test_create_alias_tag_empty_name(self):
        """Test that empty name raises ValueError."""
        with self.assertRaises(ValueError) as context:
            create_alias_tag(self.tags_element, '', 'Local:1:I.Data.0')
        self.assertIn("name must be a non-empty string", str(context.exception))
    
    def test_create_alias_tag_empty_aliastfor(self):
        """Test that empty AliasFor raises ValueError."""
        with self.assertRaises(ValueError) as context:
            create_alias_tag(self.tags_element, 'BadAlias', '')
        self.assertIn("AliasFor must be a non-empty string", str(context.exception))
    
    def test_create_base_tag_dint_success(self):
        """Test successfully creating a Base DINT tag."""
        tag_obj = create_base_tag(self.tags_element, 'MyDint', 'DINT')
        
        # Verify the tag was created in XML
        tag_elem = self.tags_element.find("Tag[@Name='MyDint']")
        self.assertIsNotNone(tag_elem)
        self.assertEqual(tag_elem.attrib['TagType'], 'Base')
        self.assertEqual(tag_elem.attrib['DataType'], 'DINT')
        self.assertEqual(tag_elem.attrib['Constant'], 'false')
        self.assertEqual(tag_elem.attrib['Radix'], 'Decimal')
        
        # Verify Data elements exist
        data_elements = tag_elem.findall('Data')
        self.assertEqual(len(data_elements), 2)
        
        # Check L5K format
        l5k_data = tag_elem.find("Data[@Format='L5K']")
        self.assertIsNotNone(l5k_data)
        self.assertIn('CDATA', l5k_data.text)
        
        # Check Decorated format
        decorated_data = tag_elem.find("Data[@Format='Decorated']")
        self.assertIsNotNone(decorated_data)
        data_value = decorated_data.find('DataValue')
        self.assertIsNotNone(data_value)
        self.assertEqual(data_value.attrib['DataType'], 'DINT')
        self.assertEqual(data_value.attrib['Value'], '0')
    
    def test_create_base_tag_bool_success(self):
        """Test successfully creating a Base BOOL tag."""
        tag_obj = create_base_tag(self.tags_element, 'MyBool', 'BOOL')
        
        tag_elem = self.tags_element.find("Tag[@Name='MyBool']")
        self.assertIsNotNone(tag_elem)
        self.assertEqual(tag_elem.attrib['DataType'], 'BOOL')
    
    def test_create_base_tag_real_success(self):
        """Test successfully creating a Base REAL tag."""
        tag_obj = create_base_tag(self.tags_element, 'MyReal', 'REAL')
        
        tag_elem = self.tags_element.find("Tag[@Name='MyReal']")
        self.assertIsNotNone(tag_elem)
        self.assertEqual(tag_elem.attrib['DataType'], 'REAL')
        
        # Check default value for REAL is 0.0
        decorated_data = tag_elem.find("Data[@Format='Decorated']")
        data_value = decorated_data.find('DataValue')
        self.assertEqual(data_value.attrib['Value'], '0.0')
    
    def test_create_base_tag_empty_name(self):
        """Test that empty name raises ValueError."""
        with self.assertRaises(ValueError) as context:
            create_base_tag(self.tags_element, '', 'DINT')
        self.assertIn("name must be a non-empty string", str(context.exception))
    
    def test_create_base_tag_invalid_datatype(self):
        """Test that invalid DataType raises ValueError."""
        with self.assertRaises(ValueError) as context:
            create_base_tag(self.tags_element, 'BadBase', 'INVALID_TYPE')
        self.assertIn("Invalid DataType", str(context.exception))
        self.assertIn("Valid types are", str(context.exception))
    
    def test_create_base_tag_all_valid_types(self):
        """Test creating Base tags for all valid data types."""
        valid_types = ['SINT', 'INT', 'DINT', 'BOOL', 'REAL']
        
        for data_type in valid_types:
            tag_name = f'Test_{data_type}'
            tag_obj = create_base_tag(self.tags_element, tag_name, data_type)
            
            tag_elem = self.tags_element.find(f"Tag[@Name='{tag_name}']")
            self.assertIsNotNone(tag_elem)
            self.assertEqual(tag_elem.attrib['DataType'], data_type)


class TestCreateTagsFromExcelMethod(unittest.TestCase):
    """Tests for the create_tags_from_excel method in Program class"""
    
    def setUp(self):
        """Load the MainProgram.L5X fixture."""
        doc = ElementTree.parse('tests/MainProgram.L5X')
        root = doc.getroot()
        program_elem = root.find(".//Program[@Name='MainProgram']")
        self.program = Program(program_elem, 'en')
    
    def test_create_tags_from_excel_missing_columns(self):
        """Test error handling for missing required columns."""
        try:
            import pandas
        except ImportError:
            self.skipTest("pandas not installed - cannot test Excel functionality")
        
        # Create a DataFrame with missing columns
        df = pandas.DataFrame({'Name': ['Test'], 'TagType': ['Alias']})
        temp_file = 'tests/temp_missing_cols.xlsx'
        df.to_excel(temp_file, index=False)
        
        try:
            # Should raise ValueError for missing columns
            with self.assertRaises(ValueError) as context:
                self.program.create_tags_from_excel(temp_file)
            
            self.assertIn("missing required columns", str(context.exception))
        finally:
            # Clean up
            import os
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_create_tags_from_excel_empty_name(self):
        """Test error handling when tag name is empty."""
        try:
            import pandas
        except ImportError:
            self.skipTest("pandas not installed - cannot test Excel functionality")
        
        # Create a DataFrame with empty name
        df = pandas.DataFrame({
            'Name': [''],
            'TagType': ['Base'],
            'AliasFor': [pandas.NA],
            'DataType': ['DINT']
        })
        temp_file = 'tests/temp_empty_name.xlsx'
        df.to_excel(temp_file, index=False)
        
        try:
            with self.assertRaises(ValueError) as context:
                self.program.create_tags_from_excel(temp_file)
            
            self.assertIn("Name cannot be empty", str(context.exception))
        finally:
            import os
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_create_tags_from_excel_alias_without_aliastfor(self):
        """Test error handling when Alias tag has no AliasFor value."""
        try:
            import pandas
        except ImportError:
            self.skipTest("pandas not installed - cannot test Excel functionality")
        
        # Create a DataFrame with Alias tag but no AliasFor
        df = pandas.DataFrame({
            'Name': ['TestAlias'],
            'TagType': ['Alias'],
            'AliasFor': [''],
            'DataType': [pandas.NA]
        })
        temp_file = 'tests/temp_no_aliastfor.xlsx'
        df.to_excel(temp_file, index=False)
        
        try:
            with self.assertRaises(ValueError) as context:
                self.program.create_tags_from_excel(temp_file)
            
            self.assertIn("AliasFor is required", str(context.exception))
        finally:
            import os
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_create_tags_from_excel_base_without_datatype(self):
        """Test error handling when Base tag has no DataType value."""
        try:
            import pandas
        except ImportError:
            self.skipTest("pandas not installed - cannot test Excel functionality")
        
        # Create a DataFrame with Base tag but no DataType
        df = pandas.DataFrame({
            'Name': ['TestBase'],
            'TagType': ['Base'],
            'AliasFor': [pandas.NA],
            'DataType': ['']
        })
        temp_file = 'tests/temp_no_datatype.xlsx'
        df.to_excel(temp_file, index=False)
        
        try:
            with self.assertRaises(ValueError) as context:
                self.program.create_tags_from_excel(temp_file)
            
            self.assertIn("DataType is required", str(context.exception))
        finally:
            import os
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_create_tags_from_excel_invalid_datatype(self):
        """Test error handling for invalid DataType."""
        try:
            import pandas
        except ImportError:
            self.skipTest("pandas not installed - cannot test Excel functionality")
        
        # Create a DataFrame with invalid DataType
        df = pandas.DataFrame({
            'Name': ['TestBase'],
            'TagType': ['Base'],
            'AliasFor': [pandas.NA],
            'DataType': ['INVALID_TYPE']
        })
        temp_file = 'tests/temp_invalid_type.xlsx'
        df.to_excel(temp_file, index=False)
        
        try:
            with self.assertRaises(ValueError) as context:
                self.program.create_tags_from_excel(temp_file)
            
            self.assertIn("Invalid DataType", str(context.exception))
        finally:
            import os
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_create_tags_from_excel_invalid_tagtype(self):
        """Test error handling for invalid TagType."""
        try:
            import pandas
        except ImportError:
            self.skipTest("pandas not installed - cannot test Excel functionality")
        
        # Create a DataFrame with invalid TagType
        df = pandas.DataFrame({
            'Name': ['TestTag'],
            'TagType': ['InvalidType'],
            'AliasFor': [pandas.NA],
            'DataType': [pandas.NA]
        })
        temp_file = 'tests/temp_invalid_tagtype.xlsx'
        df.to_excel(temp_file, index=False)
        
        try:
            with self.assertRaises(ValueError) as context:
                self.program.create_tags_from_excel(temp_file)
            
            self.assertIn("Invalid TagType", str(context.exception))
        finally:
            import os
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_create_tags_from_excel_returns_self(self):
        """Test that create_tags_from_excel modifies the program in place.
        
        Since tags_element is modified in place (XML element), the changes
        are reflected in the project without needing a return value.
        """
        try:
            import pandas
        except ImportError:
            self.skipTest("pandas not installed - cannot test Excel functionality")
        
        # Create a DataFrame with valid tags
        df = pandas.DataFrame({
            'Name': ['TestDint'],
            'TagType': ['Base'],
            'AliasFor': [pandas.NA],
            'DataType': ['DINT']
        })
        temp_file = 'tests/temp_method_chaining.xlsx'
        df.to_excel(temp_file, index=False)
        
        try:
            # Call create_tags_from_excel (returns None)
            result = self.program.create_tags_from_excel(temp_file)
            
            # Verify the return value is None (proper Python style)
            self.assertIsNone(result)
            
            # Verify tags were actually created in the program
            # The XML element was modified in place
            tag_elem = self.program.element.find("Tags/Tag[@Name='TestDint']")
            self.assertIsNotNone(tag_elem)
            self.assertEqual(tag_elem.attrib['DataType'], 'DINT')
        finally:
            import os
            if os.path.exists(temp_file):
                os.remove(temp_file)
        """Test error handling for missing required columns."""
        try:
            import pandas
        except ImportError:
            self.skipTest("pandas not installed")
        
        # Create a DataFrame with missing columns
        df = pandas.DataFrame({'Name': ['Test'], 'TagType': ['Alias']})
        # Save to a temporary file
        temp_file = 'tests/temp_missing_cols.xlsx'
        df.to_excel(temp_file, index=False)
        
        # Should raise ValueError for missing columns
        with self.assertRaises(ValueError) as context:
            self.program.create_tags_from_excel(temp_file)
        
        self.assertIn("missing required columns", str(context.exception))
        
        # Clean up
        import os
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    def test_create_tags_from_excel_alias_without_aliastfor(self):
        """Test error handling when Alias tag has no AliasFor value."""
        try:
            import pandas
        except ImportError:
            self.skipTest("pandas not installed")
        
        # Create a DataFrame with Alias tag but no AliasFor
        df = pandas.DataFrame({
            'Name': ['TestAlias'],
            'TagType': ['Alias'],
            'AliasFor': [''],
            'DataType': [pandas.NA]
        })
        temp_file = 'tests/temp_no_aliastfor.xlsx'
        df.to_excel(temp_file, index=False)
        
        # Should raise ValueError
        with self.assertRaises(ValueError) as context:
            self.program.create_tags_from_excel(temp_file)
        
        self.assertIn("AliasFor is required", str(context.exception))
        
        # Clean up
        import os
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    def test_create_tags_from_excel_base_without_datatype(self):
        """Test error handling when Base tag has no DataType value."""
        try:
            import pandas
        except ImportError:
            self.skipTest("pandas not installed")
        
        # Create a DataFrame with Base tag but no DataType
        df = pandas.DataFrame({
            'Name': ['TestBase'],
            'TagType': ['Base'],
            'AliasFor': [pandas.NA],
            'DataType': ['']
        })
        temp_file = 'tests/temp_no_datatype.xlsx'
        df.to_excel(temp_file, index=False)
        
        # Should raise ValueError
        with self.assertRaises(ValueError) as context:
            self.program.create_tags_from_excel(temp_file)
        
        self.assertIn("DataType is required", str(context.exception))
        
        # Clean up
        import os
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    def test_create_tags_from_excel_invalid_datatype(self):
        """Test error handling for invalid DataType."""
        try:
            import pandas
        except ImportError:
            self.skipTest("pandas not installed")
        
        # Create a DataFrame with invalid DataType
        df = pandas.DataFrame({
            'Name': ['TestBase'],
            'TagType': ['Base'],
            'AliasFor': [pandas.NA],
            'DataType': ['INVALID_TYPE']
        })
        temp_file = 'tests/temp_invalid_type.xlsx'
        df.to_excel(temp_file, index=False)
        
        # Should raise ValueError
        with self.assertRaises(ValueError) as context:
            self.program.create_tags_from_excel(temp_file)
        
        self.assertIn("Invalid DataType", str(context.exception))
        
        # Clean up
        import os
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    def test_create_tags_from_excel_invalid_tagtype(self):
        """Test error handling for invalid TagType."""
        try:
            import pandas
        except ImportError:
            self.skipTest("pandas not installed")
        
        # Create a DataFrame with invalid TagType
        df = pandas.DataFrame({
            'Name': ['TestTag'],
            'TagType': ['InvalidType'],
            'AliasFor': [pandas.NA],
            'DataType': [pandas.NA]
        })
        temp_file = 'tests/temp_invalid_tagtype.xlsx'
        df.to_excel(temp_file, index=False)
        
        # Should raise ValueError
        with self.assertRaises(ValueError) as context:
            self.program.create_tags_from_excel(temp_file)
        
        self.assertIn("Invalid TagType", str(context.exception))
        
        # Clean up
        import os
        if os.path.exists(temp_file):
            os.remove(temp_file)


if __name__ == '__main__':
    unittest.main()
