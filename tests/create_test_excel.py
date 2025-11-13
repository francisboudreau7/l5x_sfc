import pandas as pd
import os

# Create test data
data = {
    'Name': ['TestAlias', 'TestBool', 'TestDint'],
    'TagType': ['Alias', 'Base', 'Base'],
    'AliasFor': ['Local:1:O.Data.0', pd.NA, pd.NA],
    'DataType': [pd.NA, 'BOOL', 'DINT']
}

df = pd.DataFrame(data)

# Save to Excel
output_path = os.path.join(os.path.dirname(__file__), 'test_tags_input.xlsx')
df.to_excel(output_path, index=False)

print(f"Test Excel file created: {output_path}")
