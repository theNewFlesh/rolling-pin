# Rolling-Pin
A library of generic tools for ETL work and visualization of JSON blobs and python repositories

**[Documentation](https://thenewflesh.github.io/rolling-pin/)**

# Installation
`pip install rolling-pin`

# For Developers
## Installation
1. Install [docker](https://docs.docker.com/v17.09/engine/installation)
2. Install [docker-machine](https://docs.docker.com/machine/install-machine) (if running on macOS or Windows)
3. Ensure docker-machine has at least 4 GB of memory allocated to it.
4. `cd rolling-pin`
5. `chmod +x bin/rolling-pin`
6. `bin/rolling-pin start`

The service should take a few minutes to start up.

Run `bin/rolling-pin --help` for more help on the command line tool.

## Conda Environment Creation
Running a conda environment is not recommended.

However, if you would still like to build one, do the following:
1. `conda create -y -n rolling-pin-env python==3.7`
2. `source activate rolling-pin-env`
3. `pip install -r docker/requirements.txt`
