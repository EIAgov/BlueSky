
BlueSky Prototype model
=================================================

============
Sphinx Documentation Structure
============


Sphinx organizes the documentation into the following sections:

Package Overview
----------------
The documentation starts with a general overview of the main package structure. In this project, the top-level package is `src`. Inside the `src` package, you will find the following main packages:

- **electricity**: Contains modules related to electricity modeling and calculations.
- **hydrogen**: Contains modules for hydrogen energy production, storage, and consumption.
- **residential**: Contains models and utilities related to residential energy use.
- **integrator**: Integrates components from various energy sources (electricity, hydrogen, etc.) into a cohesive system.

Submodules and Subpackages
--------------------------
Each package may contain additional submodules and subpackages, which are organized in the documentation as follows:

- **Package**: Each package (e.g., electricity, hydrogen) is documented with a high-level description of its purpose and contents.
- **Submodules**: The individual Python modules within each package are listed and documented. For example, the `integrator` package may contain submodules like `runner.py`, `utilites.py`, and `progress_plot.py`. Each of these modules will have its own section.
- **Subpackages**: If a package contains nested subpackages, these are also documented. For instance, if `electricity` has a subpackage `scripts`, it will have its own subsection with corresponding submodules.

Each module's docstrings are captured to provide detailed information about functions, classes, methods, and attributes.

Example Structure
-----------------
For the `src` package, Sphinx might organize the contents as follows:

.. code-block:: text

   src (package)/
   ├── integrator (subpackage)/
   │   ├── input
   │   └── runner.py (module)
   └── models (subpackage)/
      ├── electricity (package)/
      │   └── scripts (subpackage)/
      │       ├── electricity_model.py (module)
      │       └── preprocessor.py
      ├── hydrogen/
      │   ├── utilities/
      │   │   └── h2_functions.py
      │   ├── model/
      │   │   └── h2_model.py
      │   └── etc.
      └── residential/
         └── scripts/
               ├── residential.py
               └── utilites.py

In the HTML and Markdown outputs, each package and subpackage is represented with links **below** to the respective modules, making it easy to navigate between different sections of the documentation.

Use the **Search bar** on the top left to search for a specific function or module.






.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules
   src.integrator
   src.models.electricity
   src
   src.models
   src.models.residential.scripts
   src.models.residential
   src.models.hydrogen.utilities
   src.models.hydrogen.tests
   src.models.hydrogen
   src.models.hydrogen.region_network
   src.models.hydrogen.network
   src.models.hydrogen.model
   src.models.electricity.scripts
   src.models.electricity.scripts.common
