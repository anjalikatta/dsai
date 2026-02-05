#!/bin/bash

# Local .bashrc for this repository
# This file contains project-specific bash configurations

# Add LM Studio to PATH for this project (here's mine)
export PATH="$PATH:/c/Users/tmf77/.lmstudio/bin"
alias lms='/c/Users/tmf77/.lmstudio/bin/lms.exe'

export PATH="$PATH:/c/Users/tmf77/AppData/Local/Programs/Ollama"
alias ollama='/c/Users/tmf77/AppData/Local/Programs/Ollama/ollama.exe'

# --- R Configuration ---
export PATH="$PATH:/c/Program Files/R/R-4.5.2/bin"
alias Rscript='/c/Program Files/R/R-4.5.2/bin/Rscript.exe'

# --- Python Configuration (Windows Store Version) ---
# This is the path where your python.exe lives
export PATH="$PATH:/c/Users/akatt/AppData/Local/Microsoft/WindowsApps"
alias python='/c/Users/akatt/AppData/Local/Microsoft/WindowsApps/python.exe'

# --- Python Scripts (Uvicorn, Pip, FastAPI) ---
# IMPORTANT: This is the messy path from your error message!
export PATH="$PATH:/c/Users/akatt/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0/LocalCache/local-packages/Python311/Scripts"

echo "✅ Environment configured for akatt."