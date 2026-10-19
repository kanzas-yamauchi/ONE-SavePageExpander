"""Locating the game and reading original files from the user's own install."""
import glob, os, re, sys, zipfile

from .dotnetmeta import Meta

APPID = '2432100'
GAME_DIR = 'ONE'
EXE = 'ONE.exe'


def steam_roots():
    roots = []
    if sys.platform.startswith('win'):
        try:
            import winreg
            for hive, key in [(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam'),
                              (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam')]:
                try:
                    with winreg.OpenKey(hive, key) as k:
                        for name in ('SteamPath', 'InstallPath'):
                            try:
                                roots.append(winreg.QueryValueEx(k, name)[0])
                            except OSError:
                                pass
                except OSError:
                    pass
        except ImportError:
            pass
        roots.append(r'C:\Program Files (x86)\Steam')
    else:
        h = os.path.expanduser('~')
        roots += [h + '/.local/share/Steam', h + '/.steam/steam', h + '/.steam/root',
                  h + '/.var/app/com.valvesoftware.Steam/.local/share/Steam']
    out = []
    for r in roots:
        r = os.path.normpath(r)
        if os.path.isdir(r) and r not in out:
            out.append(r)
    return out


def libraries():
    libs = []
    for root in steam_roots():
        libs.append(root)
        vdf = os.path.join(root, 'steamapps', 'libraryfolders.vdf')
        if os.path.isfile(vdf):
            txt = open(vdf, encoding='utf-8', errors='replace').read()
            for m in re.finditer(r'"path"\s+"([^"]+)"', txt):
                libs.append(os.path.normpath(m.group(1).replace('\\\\', '\\')))
    seen, out = set(), []
    for l in libs:
        k = os.path.realpath(l)
        if k not in seen:
            seen.add(k); out.append(l)
    return out


def find_game():
    for lib in libraries():
        g = os.path.join(lib, 'steamapps', 'common', GAME_DIR)
        if os.path.isfile(os.path.join(g, EXE)):
            return g
    return None


def save_dir(game):
    """Folder that holds the save data (novamicus/ONE*)."""
    if sys.platform.startswith('win'):
        p = os.path.join(os.environ.get('APPDATA', ''), 'novamicus')
    else:
        lib = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(game))))
        p = os.path.join(lib, 'steamapps', 'compatdata', APPID, 'pfx', 'drive_c', 'users',
                         'steamuser', 'AppData', 'Roaming', 'novamicus')
    return p if os.path.isdir(p) else None


def package_password(game):
    """Read the package password constant from the game's own assembly."""
    dlls = glob.glob(os.path.join(game, '*_Data', 'Managed', 'Assembly-CSharp.dll'))
    if not dlls:
        raise RuntimeError('Assembly-CSharp.dll not found')
    vals = set(Meta(open(dlls[0], 'rb').read()).string_constants('PackagePassword'))
    if len(vals) != 1:
        raise RuntimeError('package password constant not found in the game assembly')
    return vals.pop()


def read_original(game, paths):
    """Read the given files (forward-slash paths) from the game's data_*.dat packages."""
    cs = os.path.join(game, 'CatSystem')
    pwd = package_password(game).encode('utf-8')
    found = {}
    for pkg in sorted(glob.glob(os.path.join(cs, 'data_*.dat'))):
        try:
            z = zipfile.ZipFile(pkg)
        except zipfile.BadZipFile:
            continue
        names = {n.replace('\\', '/').lower(): n for n in z.namelist()}
        try:
            ver = int(z.read(names['@version'], pwd=pwd).decode('ascii', 'ignore').strip() or 0) if '@version' in names else 0
        except Exception:
            ver = 0
        for p in paths:
            n = names.get(p.lower())
            if n is not None and (p not in found or ver >= found[p][0]):
                found[p] = (ver, z.read(n, pwd=pwd), os.path.basename(pkg))
    missing = [p for p in paths if p not in found]
    if missing:
        raise RuntimeError('not found in game packages: ' + ', '.join(missing))
    return {p: v[1] for p, v in found.items()}, {p: v[2] for p, v in found.items()}
