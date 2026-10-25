@echo off
setlocal
pushd "%~dp0"
set "LAB_PYTHON="
set "LAB_PYTHON_ARGS="
rem Python incluido con Codex, si esta disponible en esta PC.
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
echo No se encontro Python. Instala Python 3.10 o posterior desde python.org.
goto done

:found_python
"%LAB_PYTHON%" %LAB_PYTHON_ARGS% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo Se necesita Python 3.10 o posterior.
    goto done
)
echo EJEMPLO 1: correo normal ficticio
"%LAB_PYTHON%" %LAB_PYTHON_ARGS% phishing_analyzer.py examples\normal.eml
echo.
echo EJEMPLO 2: correo sospechoso ficticio
"%LAB_PYTHON%" %LAB_PYTHON_ARGS% phishing_analyzer.py examples\sospechoso.eml

:done
popd
echo.
pause
