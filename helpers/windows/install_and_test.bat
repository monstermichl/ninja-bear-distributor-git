rem Make sure the script is executed from the current directory even if it's called from somewhere else.
pushd %~dp0

install.bat || call :exit -1
test.bat || call :exit -2

rem Exit script successfully.
call :exit 0

:_exit
    popd    
    exit %1
