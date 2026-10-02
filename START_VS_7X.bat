@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
python -m streamlit run VS_7X_OPTION_ENGINE.py
pause
