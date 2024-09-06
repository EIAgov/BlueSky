# BlueSky Model Documentation

This folder contains code documentation for the the BlueSky model, which is documented using [Sphinx](https://www.sphinx-doc.org/). Sphinx allows us to automatically generate documentation from the codebase and provides outputs in various formats, including HTML and Markdown.

- [BlueSky Model Documentation](#bluesky-model-documentation)
    - [Overview](#overview)
    - [How to Access the Documentation](#how-to-access-the-documentation)
        - [HTML Output](#html-output)
        - [Alternatively:](#alternatively)
        - [Markdown Output](#markdown-output)
            - [On GitLab](#on-gitlab)
            - [Locally in VS-Code](#locally-in-vs-code)
        - [PDF documentation](#pdf-documentation)
    - [Work in Progress and Feedback](#work-in-progress-and-feedback)

## Overview

The energy model consists of several packages and subpackages that are organized into functional sections. The primary goal of the documentation is to help users understand how the different components fit together and how they can be used.

The documentation is generated using Sphinx, and the output is available in both HTML and Markdown formats. The documentation automatically captures docstrings from the code, organizes modules and packages, and provides references to each class, function, and method.


## How to Access the Documentation

In general, the **HTML** code documentation provided in the **`docs`** folder is the **BEST** method for exploring BlueSky code documentation. Below are instructions for viewing the html and markdown code documentation outputs.  


### HTML Output

1. Clone the BlueSky repository. Instructions can be found [here](https://git.eia.gov/oea/nextgen-bluesky/bluesky_prototype/-/wikis/Clone-a-repo-using-VS-code)

2. From the cloned **bluesky_prototype** directory, open the **`docs`** folder and *click* on the following file: **`html_documentation.bat`**

3. This should open the code documentation locally using your web browser. 

### Alternatively:

1. From the cloned **bluesky_prototype** directory, Navigate to the following: `docs\build\html`

2. *Click* on file called `index`. This should open a webpage and allow you to navigate and click on links to the code documentation. 


### Markdown Output

#### On GitLab

Markdown [Table of Contents](build/markdown/index.md)

#### Locally in VS-Code

1. From the cloned **bluesky_prototype** directory in VS-Code, Navigate to the following: `docs\build\markdown`

2. *Click* on file called `index`. Using the markdown preview functionality of VS-Code, you should be able to follow the markdown Table of contents list.  

### PDF documentation

Use the PDF link on the Wiki homepage to access the latest version of code documentation. 
[PDF documentation](https://git.eia.gov/oea/nextgen-bluesky/bluesky_prototype/-/wikis/home)

## Work in Progress and Feedback

Please note that this documentation is a **work in progress**. As the model evolves, additional details and sections will be added. The documents generated (html, markdown, pdf) are not meant for external publication at this time. 

We welcome any feedback, suggestions, or contributions that could help improve the clarity and usefulness of the documentation. If you encounter any gaps or areas that need further explanation, feel free to open an issue or submit a pull request to enhance the documentation.

See [FAQ section](https://git.eia.gov/oea/nextgen-bluesky/bluesky_prototype/-/wikis/html-(local)-code-documentation-instructions) for additional assistance

