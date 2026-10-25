@echo off
setlocal
pushd "%~dp0"
set "LAB_PYTHON="
set "LAB_PYTHON_ARGS="
set "LAB_RESULT=1"
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
    set "LAB_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    goto found_python
)
where py >nul 2>nul
if not errorlevel 1 (
    set "LAB_PYTHON=py"
    set "LAB_PYTHON_ARGS=-3"
    goto found_python
)
echo Se necesita Python 3.10 o posterior. Descargalo desde python.org.
goto done

:found_python
"%LAB_PYTHON%" %LAB_PYTHON_ARGS% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo Se necesita Python 3.10 o posterior.
    goto done
)
"%LAB_PYTHON%" %LAB_PYTHON_ARGS% demo_portfolio.py
set "LAB_RESULT=%ERRORLEVEL%"

:done
popd
echo.
pause
exit /b %LAB_RESULT%
