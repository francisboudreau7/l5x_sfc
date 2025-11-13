"""
Module for creating tags from Excel files.

This module provides functionality to read Excel files and create tags
(both Alias and Base types) in L5X tag elements. Can be used at any level
that has access to a Tags XML element.
"""

from l5x.tag import base_data_types, create_alias_tag, create_base_tag

try:
    import pandas
except ImportError:
    pandas = None


def create_tags_from_excel(tags_element, filepath):
    if pandas is None:
        raise ImportError(
            "pandas is required for Excel functionality. "
            "Install it with: pip install pandas openpyxl"
        )
    
    if tags_element is None:
        raise RuntimeError("tags_element cannot be None")
    
    # Read the Excel file
    df = pandas.read_excel(filepath)
    
    # Validate required columns
    required_columns = {'Name', 'TagType', 'AliasFor', 'DataType'}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Excel file missing required columns: {missing_columns}")
    
    # Process each row in the Excel file
    for idx, row in df.iterrows():
        tag_name = str(row['Name']).strip()
        tag_type = str(row['TagType']).strip()
        
        if not tag_name:
            raise ValueError(f"Row {idx + 2}: Name cannot be empty")
        
        try:
            if tag_type == 'Alias':
                # Create Alias tag
                alias_for = str(row['AliasFor']).strip() if pandas.notna(row['AliasFor']) else ""
                if not alias_for:
                    raise ValueError(f"Row {idx + 2}: AliasFor is required for Alias tags")
                
                create_alias_tag(tags_element, tag_name, alias_for)
            
            elif tag_type == 'Base':
                # Create Base tag
                data_type = str(row['DataType']).strip() if pandas.notna(row['DataType']) else ""
                if not data_type:
                    raise ValueError(f"Row {idx + 2}: DataType is required for Base tags")
                
                if data_type not in base_data_types:
                    valid_types = ', '.join(sorted(base_data_types.keys()))
                    raise ValueError(f"Row {idx + 2}: Invalid DataType '{data_type}'. Valid types: {valid_types}")
                
                create_base_tag(tags_element, tag_name, data_type)
            
            else:
                raise ValueError(f"Row {idx + 2}: Invalid TagType '{tag_type}'. Must be 'Alias' or 'Base'")
        
        except ValueError as e:
            # Re-raise with row context if not already included
            if "Row" not in str(e):
                raise ValueError(f"Row {idx + 2}: {str(e)}")
            raise
