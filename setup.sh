#!/bin/bash
set -e
export MAMBA_EXE="/home/runner/.local/bin/micromamba";
export MAMBA_ROOT_PREFIX="/home/runner/micromamba";

# check if MAMBA_EXE exists and is executable
if ! [ -x "$MAMBA_EXE" ]; then
    echo "Installing micromamba"
    curl micro.mamba.pm/install.sh | bash
fi
# >>> mamba initialize >>>
# !! Contents within this block are managed by 'mamba init' !!
__mamba_setup="$("$MAMBA_EXE" shell hook --shell bash --prefix "$MAMBA_ROOT_PREFIX" 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__mamba_setup"
else
    if [ -f "/home/runner/micromamba/etc/profile.d/micromamba.sh" ]; then
        . "/home/runner/micromamba/etc/profile.d/micromamba.sh"
    else
        export  PATH="/home/runner/micromamba/bin:$PATH"  # extra space after export prevents interference from conda init
    fi
fi
unset __mamba_setup
# <<< mamba initialize <<<


# check if env exists
if ! micromamba env list | grep -q giru
then
    echo "Creating environment"
    micromamba env create -f "/home/runner/$REPL_SLUG/environment.yml" -y
fi


micromamba activate giru
which python
which python3

printenv

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
