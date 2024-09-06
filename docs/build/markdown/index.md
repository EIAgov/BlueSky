# BlueSky Prototype model

## Sphinx Documentation Structure

Sphinx organizes the documentation into the following sections:

### Package Overview

The documentation starts with a general overview of the main package structure. In this project, the top-level package is src. Inside the src package, you will find the following main packages:

- **electricity**: Contains modules related to electricity modeling and calculations.
- **hydrogen**: Contains modules for hydrogen energy production, storage, and consumption.
- **residential**: Contains models and utilities related to residential energy use.
- **integrator**: Integrates components from various energy sources (electricity, hydrogen, etc.) into a cohesive system.

### Submodules and Subpackages

Each package may contain additional submodules and subpackages, which are organized in the documentation as follows:

- **Package**: Each package (e.g., electricity, hydrogen) is documented with a high-level description of its purpose and contents.
- **Submodules**: The individual Python modules within each package are listed and documented. For example, the integrator package may contain submodules like runner.py, utilites.py, and progress_plot.py. Each of these modules will have its own section.
- **Subpackages**: If a package contains nested subpackages, these are also documented. For instance, if electricity has a subpackage scripts, it will have its own subsection with corresponding submodules.

Each module’s docstrings are captured to provide detailed information about functions, classes, methods, and attributes.

### Example Structure

For the src package, Sphinx might organize the contents as follows:

```text
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
```

In the HTML and Markdown outputs, each package and subpackage is represented with links **below** to the respective modules, making it easy to navigate between different sections of the documentation.

Use the **Search bar** on the top left to search for a specific function or module.

### Contents:

* [src](modules.md)
  * [src package](src.md)
* [src.integrator package](src.integrator.md)
  * [Submodules](src.integrator.md#submodules)
  * [src.integrator.config_setup module](src.integrator.md#module-src.integrator.config_setup)
  * [src.integrator.gs_elec_hyd_res module](src.integrator.md#module-src.integrator.gs_elec_hyd_res)
  * [src.integrator.progress_plot module](src.integrator.md#module-src.integrator.progress_plot)
  * [src.integrator.runner module](src.integrator.md#module-src.integrator.runner)
  * [src.integrator.unified_elec_hyd_res module](src.integrator.md#module-src.integrator.unified_elec_hyd_res)
  * [src.integrator.utilities module](src.integrator.md#module-src.integrator.utilities)
  * [Module contents](src.integrator.md#module-src.integrator)
* [src.models.electricity package](src.models.electricity.md)
  * [Subpackages](src.models.electricity.md#subpackages)
  * [Module contents](src.models.electricity.md#module-src.models.electricity)
* [src package](src.md)
  * [Subpackages](src.md#subpackages)
  * [Submodules](src.md#submodules)
  * [src.block_experiment module](src.md#module-src.block_experiment)
  * [Module contents](src.md#module-src)
* [src.models package](src.models.md)
  * [Subpackages](src.models.md#subpackages)
  * [Module contents](src.models.md#module-src.models)
* [src.models.residential.scripts package](src.models.residential.scripts.md)
  * [Submodules](src.models.residential.scripts.md#submodules)
  * [src.models.residential.scripts.residential module](src.models.residential.scripts.md#module-src.models.residential.scripts.residential)
  * [src.models.residential.scripts.utilities module](src.models.residential.scripts.md#module-src.models.residential.scripts.utilities)
  * [Module contents](src.models.residential.scripts.md#module-src.models.residential.scripts)
* [src.models.residential package](src.models.residential.md)
  * [Subpackages](src.models.residential.md#subpackages)
  * [Submodules](src.models.residential.md#submodules)
  * [src.models.residential.residential_block module](src.models.residential.md#module-src.models.residential.residential_block)
  * [Module contents](src.models.residential.md#module-src.models.residential)
* [src.models.hydrogen.utilities package](src.models.hydrogen.utilities.md)
  * [Submodules](src.models.hydrogen.utilities.md#submodules)
  * [src.models.hydrogen.utilities.h2_functions module](src.models.hydrogen.utilities.md#module-src.models.hydrogen.utilities.h2_functions)
  * [Module contents](src.models.hydrogen.utilities.md#module-src.models.hydrogen.utilities)
* [src.models.hydrogen.tests package](src.models.hydrogen.tests.md)
  * [Submodules](src.models.hydrogen.tests.md#submodules)
  * [src.models.hydrogen.tests.test_single_region_solve module](src.models.hydrogen.tests.md#src-models-hydrogen-tests-test-single-region-solve-module)
  * [src.models.hydrogen.tests.test_three_region_solve module](src.models.hydrogen.tests.md#src-models-hydrogen-tests-test-three-region-solve-module)
  * [Module contents](src.models.hydrogen.tests.md#module-contents)
* [src.models.hydrogen package](src.models.hydrogen.md)
  * [Subpackages](src.models.hydrogen.md#subpackages)
  * [Submodules](src.models.hydrogen.md#submodules)
  * [src.models.hydrogen.main module](src.models.hydrogen.md#src-models-hydrogen-main-module)
  * [Module contents](src.models.hydrogen.md#module-src.models.hydrogen)
* [src.models.hydrogen.region_network package](src.models.hydrogen.region_network.md)
  * [Submodules](src.models.hydrogen.region_network.md#submodules)
  * [src.models.hydrogen.region_network.arc module](src.models.hydrogen.region_network.md#src-models-hydrogen-region-network-arc-module)
  * [src.models.hydrogen.region_network.context module](src.models.hydrogen.region_network.md#module-src.models.hydrogen.region_network.context)
  * [src.models.hydrogen.region_network.hub module](src.models.hydrogen.region_network.md#src-models-hydrogen-region-network-hub-module)
  * [src.models.hydrogen.region_network.network module](src.models.hydrogen.region_network.md#src-models-hydrogen-region-network-network-module)
  * [src.models.hydrogen.region_network.region_data module](src.models.hydrogen.region_network.md#module-src.models.hydrogen.region_network.region_data)
  * [src.models.hydrogen.region_network.runner module](src.models.hydrogen.region_network.md#src-models-hydrogen-region-network-runner-module)
  * [Module contents](src.models.hydrogen.region_network.md#module-src.models.hydrogen.region_network)
* [src.models.hydrogen.network package](src.models.hydrogen.network.md)
  * [Submodules](src.models.hydrogen.network.md#submodules)
  * [src.models.hydrogen.network.grid module](src.models.hydrogen.network.md#module-src.models.hydrogen.network.grid)
  * [src.models.hydrogen.network.grid_data module](src.models.hydrogen.network.md#module-src.models.hydrogen.network.grid_data)
  * [src.models.hydrogen.network.hub module](src.models.hydrogen.network.md#module-src.models.hydrogen.network.hub)
  * [src.models.hydrogen.network.region module](src.models.hydrogen.network.md#module-src.models.hydrogen.network.region)
  * [src.models.hydrogen.network.registry module](src.models.hydrogen.network.md#module-src.models.hydrogen.network.registry)
  * [src.models.hydrogen.network.transportation_arc module](src.models.hydrogen.network.md#module-src.models.hydrogen.network.transportation_arc)
  * [Module contents](src.models.hydrogen.network.md#module-src.models.hydrogen.network)
* [src.models.hydrogen.model package](src.models.hydrogen.model.md)
  * [Submodules](src.models.hydrogen.model.md#submodules)
  * [src.models.hydrogen.model.actions module](src.models.hydrogen.model.md#module-src.models.hydrogen.model.actions)
  * [src.models.hydrogen.model.h2_model module](src.models.hydrogen.model.md#module-src.models.hydrogen.model.h2_model)
  * [src.models.hydrogen.model.validators module](src.models.hydrogen.model.md#module-src.models.hydrogen.model.validators)
  * [Module contents](src.models.hydrogen.model.md#module-src.models.hydrogen.model)
* [src.models.electricity.scripts package](src.models.electricity.scripts.md)
  * [Subpackages](src.models.electricity.scripts.md#subpackages)
  * [Submodules](src.models.electricity.scripts.md#submodules)
  * [src.models.electricity.scripts.electricity_model module](src.models.electricity.scripts.md#module-src.models.electricity.scripts.electricity_model)
  * [src.models.electricity.scripts.postprocessor module](src.models.electricity.scripts.md#module-src.models.electricity.scripts.postprocessor)
  * [src.models.electricity.scripts.preprocessor module](src.models.electricity.scripts.md#module-src.models.electricity.scripts.preprocessor)
  * [src.models.electricity.scripts.runner module](src.models.electricity.scripts.md#module-src.models.electricity.scripts.runner)
  * [src.models.electricity.scripts.utilities module](src.models.electricity.scripts.md#module-src.models.electricity.scripts.utilities)
  * [Module contents](src.models.electricity.scripts.md#module-src.models.electricity.scripts)
* [src.models.electricity.scripts.common package](src.models.electricity.scripts.common.md)
  * [Submodules](src.models.electricity.scripts.common.md#submodules)
  * [src.models.electricity.scripts.common.common module](src.models.electricity.scripts.common.md#module-src.models.electricity.scripts.common.common)
  * [src.models.electricity.scripts.common.common_debug module](src.models.electricity.scripts.common.md#module-src.models.electricity.scripts.common.common_debug)
  * [Module contents](src.models.electricity.scripts.common.md#module-src.models.electricity.scripts.common)
