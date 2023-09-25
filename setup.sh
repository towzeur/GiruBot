#!/bin/bash

set -e

#export ENV_NAME=$(echo "$REPL_SLUG" | tr '[:upper:]' '[:lower:]')

export MAMBA_ROOT_PREFIX="/home/runner/micromamba";
export MAMBA_EXE=$MAMBA_ROOT_PREFIX"/envs/$REPL_SLUG/bin/python";


# check if MAMBA_EXE exists and is executable
#if ! [ -x "$MAMBA_EXE" ]; then
uname --machine
if ! [ -x "./bin/micromamba" ]; then
    echo "Installing micromamba"
    # Linux Intel (x86_64):
    curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
    # Linux ARM64:
    #curl -Ls https://micro.mamba.pm/api/micromamba/linux-aarch64/latest | tar -xvj bin/micromamba
fi

echo "shell hook micromamba"
eval "$(./bin/micromamba shell hook -s posix)"


# check if env exists
echo "Check if env exists"
if ! micromamba env list | grep -q $REPL_SLUG ; then
    echo "Creating environment"
    micromamba env create -f "/home/runner/$REPL_SLUG/environment.yml" -y
fi

echo "Activate env"
micromamba activate $REPL_SLUG
which python
which python3
#printenv

# find arguments --name that need to be run
# and run them
for arg in "$@"
do
    if [ "$arg" == "--filename" ]
    then
        echo "Running $2"
        python $2
    fi
done
