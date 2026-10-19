"""Command line: python -m onepatch {install|uninstall|build} [--game DIR] [--out DIR]"""
import argparse, datetime, hashlib, json, os, shutil, subprocess, sys

from . import __version__
from .gamefiles import find_game, read_original, save_dir, EXE
from .generate import PATHS, NPAGES, PER, generate, is_patched, PatchError

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP = os.path.join(HERE, 'backup')


def sha(b): return hashlib.sha256(b).hexdigest()


def game_running():
    try:
        if sys.platform.startswith('win'):
            out = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {EXE}'], capture_output=True, text=True).stdout
            return EXE.lower() in out.lower()
    except FileNotFoundError:
        return False
    # Linux (Proton/Wine): a process whose argv[0] is ...\\ONE.exe
    for pid in os.listdir('/proc') if os.path.isdir('/proc') else []:
        if not pid.isdigit():
            continue
        try:
            argv0 = open(f'/proc/{pid}/cmdline', 'rb').read().split(b'\0')[0].decode('utf-8', 'replace')
        except OSError:
            continue
        if argv0.replace('\\', '/').rsplit('/', 1)[-1].lower() == EXE.lower():
            return True
    return False


def resolve_game(arg):
    g = arg or find_game()
    if not g or not os.path.isfile(os.path.join(g, EXE)):
        sys.exit('ONE. のインストール先が見つからない。--game でフォルダを指定して。')
    return os.path.abspath(g)


def build(game):
    orig, src = read_original(game, PATHS)
    for p in PATHS:
        print(f'  読み込み: {p}  ({src[p]})')
    try:
        return generate(orig)
    except PatchError as e:
        sys.exit(f'生成できなかった: {e}\nゲームのバージョンが想定と違う可能性がある。何も変更してない。')


def cmd_build(a):
    game = resolve_game(a.game)
    out = build(game)
    for p, data in out.items():
        dst = os.path.join(a.out, 'CatSystem', *p.split('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(data)
        print(f'  生成: {dst}  sha256={sha(data)}')


def cmd_install(a):
    game = resolve_game(a.game)
    print(f'ゲーム: {game}')
    if game_running():
        sys.exit('ゲームが起動中。終了してからもう一度実行して。')
    out = build(game)     # everything is generated before anything is touched
    cs = os.path.join(game, 'CatSystem')
    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    bk = os.path.join(BACKUP, ts); os.makedirs(bk, exist_ok=True)
    sd = save_dir(game)
    if sd:
        arc = shutil.make_archive(os.path.join(bk, 'saves'), 'zip', os.path.dirname(sd), os.path.basename(sd))
        print(f'セーブをバックアップ: {arc}')
    else:
        print('セーブフォルダが見つからなかった（まだセーブが無い？）。バックアップは省略。')
    for p in PATHS:
        dst = os.path.join(cs, *p.split('/'))
        if os.path.isfile(dst) and not is_patched(p, open(dst, 'rb').read()):
            b = os.path.join(bk, 'CatSystem', *p.split('/'))
            os.makedirs(os.path.dirname(b), exist_ok=True); shutil.copy2(dst, b)
            print(f'既存ファイルを退避: {p}')
    for p, data in out.items():
        dst = os.path.join(cs, *p.split('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        tmp = dst + '.tmp'
        open(tmp, 'wb').write(data); os.replace(tmp, dst)
    json.dump({'game': game, 'version': __version__, 'files': {p: sha(d) for p, d in out.items()}},
              open(os.path.join(BACKUP, 'last_install.json'), 'w', encoding='utf-8'), indent=1)
    print()
    print(f'適用完了。セーブ/ロード画面が {NPAGES}ページ({NPAGES * 6}枠) になった。')
    groups = ' / '.join(f'{g * PER + 1}-{(g + 1) * PER}' for g in range(NPAGES // PER))
    print(f'ページボタンの下の ◀ ▶ で {groups} を切り替え。元に戻すときは unpatch。')


def cmd_uninstall(a):
    game = a.game
    if not game:
        try:
            game = json.load(open(os.path.join(BACKUP, 'last_install.json'), encoding='utf-8'))['game']
        except Exception:
            game = None
    game = resolve_game(game)
    print(f'ゲーム: {game}')
    if game_running():
        sys.exit('ゲームが起動中。終了してからもう一度実行して。')
    cs = os.path.join(game, 'CatSystem')
    for p in PATHS:
        dst = os.path.join(cs, *p.split('/'))
        if not os.path.isfile(dst):
            continue
        if is_patched(p, open(dst, 'rb').read()):
            os.remove(dst); print(f'削除: {p}')
        else:
            print(f'スキップ（このパッチのファイルではない）: {p}')
    for d in ('image/sys', 'image', 'fes'):
        try:
            os.rmdir(os.path.join(cs, *d.split('/')))
        except OSError:
            pass
    print()
    print('取り外し完了。元の 15ページ(90枠) に戻った。セーブデータは消してない。')
    print('91枠目以降のセーブはフォルダに残ってる。もう一度パッチを当てれば見える。')


def main():
    ap = argparse.ArgumentParser(prog='onepatch', description='ONE. save page expander')
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('install', 'uninstall', 'build'):
        s = sub.add_parser(name)
        s.add_argument('--game', help='game folder (…/steamapps/common/ONE)')
        if name == 'build':
            s.add_argument('--out', required=True, help='output folder (game folder is not touched)')
    a = ap.parse_args()
    {'install': cmd_install, 'uninstall': cmd_uninstall, 'build': cmd_build}[a.cmd](a)


if __name__ == '__main__':
    main()
