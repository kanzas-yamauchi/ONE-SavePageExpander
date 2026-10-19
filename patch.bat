@echo off
chcp 65001 >nul
rem ONE. セーブページ拡張 (パッチ適用)
setlocal
cd /d "%~dp0"
set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if defined PY goto run
set "BASE="
where py >nul 2>nul && set "BASE=py -3"
if not defined BASE ( where python >nul 2>nul && set "BASE=python" )
if not defined BASE ( echo Python 3 が見つからない。https://www.python.org/ から入れて。 & pause & exit /b 1 )
echo 初回だけ Python の部品 (Pillow, NumPy) を .venv に入れる...
%BASE% -m venv .venv || ( echo venv の作成に失敗 & pause & exit /b 1 )
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || ( echo 部品のインストールに失敗 & pause & exit /b 1 )
set "PY=.venv\Scripts\python.exe"
:run
"%PY%" -m onepatch install %*
pause
