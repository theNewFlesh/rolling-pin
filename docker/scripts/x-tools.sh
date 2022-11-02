# EXPORTS-----------------------------------------------------------------------
export PATH=:/home/ubuntu/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/ubuntu/.local/lib:/home/ubuntu/dev/__pypackages__/3.10/bin
export PYTHONPATH=/home/ubuntu/lunchbox/python:/home/ubuntu/.local/share/pdm/venv/lib/python3.10/site-packages/pdm/pep582:/home/ubuntu/.local/lib:/home/ubuntu/dev/__pypackages__/3.10/lib
export REPO_ENV="True"
export REPO="lunchbox"
export REPO_PATH="/home/ubuntu/$REPO"
export BUILD_PATH="/home/ubuntu/build"
export DEV_SOURCE="$REPO_PATH/docker/dev"
export DEV_TARGET="/home/ubuntu/dev"
export PROD_SOURCE="$REPO_PATH/docker/prod"
export PROD_TARGET="/home/ubuntu/prod"
export PROCS=`python3 -c 'import os; print(os.cpu_count())'`
export PROD_PYTHON_VERSION=">=3.7"
export X_TOOLS_PATH="$REPO_PATH/docker/scripts/x-tools.sh"

# HELPER-FUNCTIONS--------------------------------------------------------------
_x-link () {
    # Link given __pypackages__ directory to /home/ubuntu/__pypackages__
    # args: pypackages directory
    ln -sf $1 /home/ubuntu/__pypackages__;
}

_x-link-dev () {
    # Link /home/ubuntu/dev/__pypackages__ to /home/ubuntu/__pypackages__
    _x-link $DEV_TARGET/__pypackages__;
}

_x-link-prod () {
    # Link /home/ubuntu/prod/__pypackages__ to /home/ubuntu/__pypackages__
    _x-link $PROD_TARGET/__pypackages__;
}

_x-dir-copy () {
    # copy all contents of source into target, skipping __pypackages__ directory
    # args: source, target
    ls -pA $1 | grep -v '/' \
    | parallel "cp --force $1/{} $2/{}";
}

_x-from-dev-path () {
    # Copy lunchbox/docker/dev to /home/ubuntu/dev
    _x-dir-copy $DEV_SOURCE $DEV_TARGET;
}

_x-from-prod-path () {
    # Copy lunchbox/docker/prod to /home/ubuntu/prod
    _x-dir-copy $PROD_SOURCE $PROD_TARGET;
}

_x-to-dev-path () {
    # Copy /home/ubuntu/dev to lunchbox/docker/dev
    _x-dir-copy $DEV_TARGET $DEV_SOURCE;
}

_x-to-prod-path () {
    # Copy /home/ubuntu/prod to lunchbox/docker/prod
    _x-dir-copy $PROD_TARGET $PROD_SOURCE;
}

_x-build () {
    # Build production version of repo for publishing
    # args: type (test or prod)
    _x-link-dev;
    cd $REPO_PATH;
    rm -rf $BUILD_PATH;
    python3 docker/scripts/rolling_pin_command.py \
        docker/config/build.yaml \
        --groups base,$1;
}

_x-dev-workflow () {
    # Copies docker/dev to ~/dev, run a given command, and copies ~/dev bask to
    # docker/dev
    # args: command string
    local CWD=`pwd`;
    _x-link-dev;
    _x-dir-copy $DEV_SOURCE $DEV_TARGET;
    cd $DEV_TARGET;
    eval "$1";
    _x-dir-copy $DEV_TARGET $DEV_SOURCE;
    cd $CWD;
}

# TASK-FUNCTIONS----------------------------------------------------------------
x-build-pip-package () {
    # Generate pip package of repo in /home/ubuntu/build/repo
    x-library-install-prod;
    x-build-prod;
    cd $BUILD_PATH/repo;
    echo "${CYAN}BUILDING PIP PACKAGE${CLEAR}\n";
    pdm build -v;
}

x-build-prod () {
    # Build production version of repo for publishing
    echo "${CYAN}BUILDING PROD REPO${CLEAR}\n";
    _x-build prod;
}

x-build-publish () {
    # Publish pip package of repo to PyPi
    # args: user, password, comment
    x-test-lint;
    cd $REPO_PATH;
    x-test-prod;
    cd $REPO_PATH;
    x-build-pip-package;
    echo "${CYAN}PUBLISHING PIP PACKAGE TO PYPI${CLEAR}\n";
    cd $BUILD_PATH/repo;
    pdm publish \
        --no-build \
        --username "$1" \
        --password "$2" \
        --comment "$3" \
        --verbose;
}

x-build-test () {
    # Build test version of repo for tox testing
    echo "${CYAN}BUILDING TEST REPO${CLEAR}\n";
    _x-build test;
}

x-docs () {
    # Generate sphinx documentation
    echo "${CYAN}GENERATING DOCS${CLEAR}\n";
    _x-link-dev;
    cd $REPO_PATH;
    mkdir -p docs;
    pandoc README.md -o sphinx/intro.rst;
    sphinx-build sphinx docs;
    cp sphinx/style.css docs/_static/style.css;
    touch docs/.nojekyll;
    mkdir -p docs/resources;
}

x-docs-architecture () {
    # Generate architecture.svg diagram from all import statements
    echo "${CYAN}GENERATING ARCHITECTURE DIAGRAM${CLEAR}\n";
    _x-link-dev;
    python3 -c "import rolling_pin.repo_etl as rpo; \
rpo.write_repo_architecture( \
    '/home/ubuntu/$REPO/python', \
    'docs/architecture.svg', \
    exclude_regex='test|mock', \
    orient='lr', \
)";
}

x-docs-full () {
    # Generate documentation, coverage report, architecture diagram and code
    # metrics
    x-docs && x-test-coverage && x-docs-architecture && x-docs-metrics;
}

x-docs-metrics () {
    # Generate code metrics report, plots and tables
    echo "${CYAN}GENERATING METRICS${CLEAR}\n";
    _x-link-dev;
    cd $REPO_PATH;
    python3 -c "import rolling_pin.repo_etl as rpo; \
rpo.write_repo_plots_and_tables('python', 'docs/plots.html', 'docs')"
}

x-library-add () {
    # Add a given package to a given dependency group
    # args: package, group
    echo "${CYAN}ADDING PACKAGE TO DEV DEPENDENCIES${CLEAR}\n";
    _x-from-dev-path;
    cd $DEV_TARGET;
    if [[ $2 == 'none' ]] then
        pdm add $1 -v;
    else
        pdm add -dG $2 $1 -v;
    fi;
    _x-to-dev-path;
}

x-library-graph-dev () {
    # Graph dependencies in dev environment
    echo "${CYAN}DEV DEPENDENCY GRAPH${CLEAR}\n";
    cd $DEV_TARGET;
    pdm list --graph;
}

x-library-graph-prod () {
    # Graph dependencies in prod environment
    echo "${CYAN}PROD DEPENDENCY GRAPH${CLEAR}\n";
    cd $PROD_TARGET;
    pdm list --graph;
}

x-library-install-dev () {
    # Install all dependencies of dev/pyproject.toml into /home/ubuntu/dev
    echo "${CYAN}INSTALL DEV${CLEAR}\n";
    _x-dev-workflow "pdm install --no-self --dev -v";
}

x-library-install-prod () {
    # Install all dependencies of prod/pyproject.toml into /home/ubuntu/prod
    echo "${CYAN}INSTALL PROD${CLEAR}\n";
    _x-link-dev;
    python3 \
        docker/scripts/generate_pyproject.py \
            docker/dev/pyproject.toml \
            "$PROD_PYTHON_VERSION" \
            --groups test \
        > $PROD_TARGET/pyproject.toml;
    cd $PROD_TARGET;
    _x-from-prod-path;
    pdm install --no-self --dev -v;
    _x-to-prod-path;
}

x-library-list-dev () {
    # List packages in dev environment
    echo "${CYAN}DEV DEPENDENCIES${CLEAR}\n";
    cd $DEV_TARGET;
    pdm list;
}

x-library-list-prod () {
    # List packages in prod environment
    echo "${CYAN}PROD DEPENDENCIES${CLEAR}\n";
    cd $PROD_TARGET;
    pdm list;
}

x-library-lock () {
    # Update /home/ubuntu/dev/pdm.lock file
    echo "${CYAN}DEV DEPENDENCY LOCK${CLEAR}\n";
    _x-dev-workflow "pdm lock -v";
}

x-library-remove () {
    # Remove a given package from a given dependency group
    # args: package, group
    echo "${CYAN}REMOVING PACKAGE FROM DEV DEPENDENCIES${CLEAR}\n";
    _x-from-dev-path;
    cd $DEV_TARGET;
    if [[ $2 == 'none' ]] then
        pdm remove $1 -v;
    else
        pdm remove -dG $2 $1 -v;
    fi;
    _x-to-dev-path;
}

x-library-search () {
    # Search for pip packages
    # args: package name
    pdm search $1;
}

x-library-sync () {
    # Sync dev dependencies
    echo "${CYAN}SYNCING DEV DEPENDENCIES${CLEAR}\n";
    _x-dev-workflow "pdm sync --no-self --dev -v";
}

x-library-update () {
    # Update dev dependencies
    echo "${CYAN}UPDATING DEV DEPENDENCIES${CLEAR}\n";
    _x-dev-workflow "pdm update --no-self --dev -v";
}

x-session-app () {
    # Run lunchbox app
    echo "${CYAN}APP${CLEAR}\n";
    _x-link-dev;
    python3.10 python/$REPO/server/app.py;
}

x-session-lab () {
    # Run jupyter lab server
    echo "${CYAN}JUPYTER LAB${CLEAR}\n";
    _x-link-dev;
    jupyter lab --allow-root --ip=0.0.0.0 --no-browser;
}

x-session-python () {
    # Run python session with dev dependencies
    _x-link-dev;
    python3.10;
}

x-test-coverage () {
    # Generate test coverage report
    echo "${CYAN}GENERATING TEST COVERAGE REPORT${CLEAR}\n";
    _x-link-dev;
    cd $REPO_PATH;
    mkdir -p docs;
    pytest \
        -c docker/config/pytest.ini \
        --numprocesses $PROCS \
        --cov=python \
        --cov-config=docker/config/pytest.ini \
        --cov-report=html:docs/htmlcov \
        python;
}

x-test-dev () {
    # Run all tests
    echo "${CYAN}TESTING DEV${CLEAR}\n";
    _x-link-dev;
    cd $REPO_PATH;
    pytest -c docker/config/pytest.ini --numprocesses $PROCS python;
}

x-test-fast () {
    # Test all code excepts tests marked with SKIP_SLOWS_TESTS decorator
    echo "${CYAN}FAST TESTING DEV${CLEAR}\n";
    _x-link-dev;
    cd $REPO_PATH;
    SKIP_SLOW_TESTS=true \
    pytest -c docker/config/pytest.ini --numprocesses $PROCS python;
}

x-test-lint () {
    # Run linting and type checking
    _x-link-dev;
    cd $REPO_PATH;
    echo "${CYAN}LINTING${CLEAR}\n";
    flake8 python --config docker/config/flake8.ini;
    echo "${CYAN}TYPE CHECKING${CLEAR}\n";
    mypy python --config-file docker/config/mypy.ini;
}

x-test-prod () {
    # Run tests across all support python versions
    x-build-test;
    _x-link-prod;
    echo "${CYAN}TESTING PROD${CLEAR}\n";
    unset REPO_ENV;
    cd $BUILD_PATH/repo;
    tox;
}

x-version () {
    # Full resolution of repo: dependencies, linting, tests, docs, etc
    _x-link-dev;
    x-test-lint;
    x-library-install-dev;
    x-docs-full;
}

x-version-bump-major () {
    # Bump repo's major version
    echo "${CYAN}BUMPING MAJOR VERSION${CLEAR}\n";
    _x-dev-workflow "pdm bump major";
}

x-version-bump-minor () {
    # Bump repo's minor version
    echo "${CYAN}BUMPING MINOR VERSION${CLEAR}\n";
    _x-dev-workflow "pdm bump minor";
}

x-version-bump-patch () {
    # Bump repo's patch version
    echo "${CYAN}BUMPING PATCH VERSION${CLEAR}\n";
    _x-dev-workflow "pdm bump patch";
}
