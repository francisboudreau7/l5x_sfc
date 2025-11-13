=========================
RSLogix .L5X Interface
=========================

This package provides a Pythonic interface for RSLogix .L5X export files,
with support for reading and modifying tags, controller configuration, and
modules. This fork adds two key features for SFC analysis and tag management.


Installation
-------------------------

::

	pip install pandas openpyxl  # Required for Excel feature


SFC Analysis
--------------------------------------

Extract actions and steps from SFC routines. This enables creating a summary
of SFC logic for analysis or for generating equivalent ladder routines
programmatically.

::

	prj = l5x.Project('project.L5X')
	sfc = prj.routines[0].sfc.print_summary()

The plan is to eventually add the ability to programmatically generate ladder routines
from the SFC and write them back to the L5X file.


Add Tags from Excel
-------------------------------

Quickly populate tags by importing from an Excel file:

::

	prj = l5x.Project('project.L5X')
	prj.programs['MainProgram'].create_tags_from_excel('tags.xlsx')
	prj.write('project_updated.L5X')

Excel file format (tags.xlsx):

::

	Name           TagType  AliasFor              DataType
	LocalInput     Alias    Local:1:I.Data.0
	Counter        Base                          DINT
	Temperature    Base                          REAL
	RunFlag        Base                          BOOL

Supported data types: SINT, INT, DINT, BOOL, REAL


Base Library Features
---------------------

This fork is based on the l5x library which supports reading/modifying:

- Tags (controller and program scoped)
- Tag properties (value, description, data type)
- Controller configuration
- Module configuration and communication paths

See original project documentation for detailed tag access examples.

