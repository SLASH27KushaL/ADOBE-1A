**PDF Outline Extractor**
=========================

This project provides a containerized solution for extracting the title and hierarchical outline (H1, H2, H3 headings) from PDF documents. It uses a sophisticated pipeline that can leverage a PDF's table of contents (if available) or fall back to heuristic and semantic analysis to determine the document structure.

**Prerequisites**
-----------------

Before you begin, ensure you have **Docker** installed and running on your system.

**1\. Building the Docker Image**
---------------------------------

To build the Docker image, open your terminal or PowerShell, navigate to the root directory of this project, and run the following command.

docker build -t task1a .

This command will:

1.  Start with a Python 3.10 base image.
    
2.  Install all necessary Python dependencies from requirements.txt.
    
3.  Download the en\_core\_web\_sm Spacy model for natural language processing.
    
4.  Copy the source code (src), configuration (configs), and the entrypoint script into the image.
    
5.  Set entrypoint.sh as the executable to be run when the container starts.
    

**2\. Running the Docker Container**
------------------------------------

After building the image, you can run the extraction pipeline. The command below mounts the project's input and output directories into the container.

**You must run this command from the root directory of the project.**

### **For Windows (PowerShell)**

docker run --rm \`  -v "${PWD}\\input:/app/input" \`  -v "${PWD}\\output:/app/output" \`  task1a

### **For macOS / Linux (bash, zsh)**

docker run --rm \\  -v "$(pwd)/input:/app/input" \\  -v "$(pwd)/output:/app/output" \\  task1a

### **Explanation**

*   **docker run**: The command to start a new container.
    
*   **\--rm**: This flag automatically removes the container once it finishes its task, keeping your system clean.
    
*   **\-v**: This flag mounts a host directory into the container.
    
*   "${PWD}\\input:/app/input" (PowerShell) or "$(pwd)/input:/app/input" (bash) maps the input folder from your project to the /app/input folder inside the container. The script reads PDFs from here.
    
*   The next line does the same for the output folder, where the script will write the resulting .json files.
    
*   **task1a**: This is the name of the image you built, which you are telling Docker to run.
    

The script will process each PDF found in the input directory and create a corresponding .json file in the output directory.

**Configuration**
-----------------

The extraction logic can be fine-tuned by modifying the configuration file located at configs/task1a.yaml. This file contains various thresholds and weights for scoring headings, defining levels, and enabling or disabling different processing steps.

**Project Structure**
------------------------------------------------------------------------------------
├── configs/
│   └── task1a.yaml     # Main configuration for the pipeline
├── docker/
│   ├── Dockerfile      # Instructions to build the Docker image
│   └── entrypoint.sh   # Script that runs the Python application
├── input/              # Place your source PDFs here
├── output/             # Extracted JSON results will be saved here
├── src/
│   ├── common/         # Shared utilities for PDF reading and config loading
│   └── task1a/         # Core logic for the extraction pipeline
└── requirements.txt    # Python dependencies
