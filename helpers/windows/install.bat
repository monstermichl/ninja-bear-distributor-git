@echo off

rem Make sure the script is executed in the example directory even if it's called from somewhere else.
pushd %~dp0\..\..

rem Install required build packages.
python -m pip install build wheel || call :_exit -1

rem Build locally (https://packaging.python.org/en/latest/discussions/setup-py-deprecated/#what-commands-should-be-used-instead).
python -m build || call :_exit -2

rem Install this module (https://github.com/pypa/pip/issues/9110#issuecomment-723675528).
python -m pip install --force-reinstall . || call :_exit -3

rem Exit script successfully.
call :_exit 0

:_exit
    popd
    exit /B %1
