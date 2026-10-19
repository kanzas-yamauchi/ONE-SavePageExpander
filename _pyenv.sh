# shared by patch.sh / unpatch.sh: picks a Python that has Pillow + NumPy
pause(){ echo; read -r -p "Enterで閉じる..." _ ; }
PY=""
if [ -x .venv/bin/python ] && .venv/bin/python -c "import PIL, numpy" 2>/dev/null; then
  PY=.venv/bin/python
elif python3 -c "import PIL, numpy" 2>/dev/null; then
  PY=python3
else
  command -v python3 >/dev/null || { echo "python3 が見つからない。インストールして。"; pause; exit 1; }
  echo "初回だけ Python の部品 (Pillow, NumPy) を .venv に入れる..."
  python3 -m venv .venv && .venv/bin/python -m pip install -q -r requirements.txt \
    || { echo "部品のインストールに失敗した（ネット接続を確認して）"; pause; exit 1; }
  PY=.venv/bin/python
fi
