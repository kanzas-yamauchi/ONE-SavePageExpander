# ONE-SavePageExpander

Steam版 **『ONE. ～輝く季節へ～』**（appid 2432100）のセーブ/ロード画面を
**15ページ（90枠）→ 75ページ（450枠）** に増やす非公式ツール。

> **免責事項**
> これは非公式のファンメイドツールで、VISUAL ARTS / Key / novamicus ほか権利者とは一切関係ありません。
> 利用には正規に購入・インストールしたゲームが必要です。ゲームのファイルやデータはこのリポジトリに含まれていません。
> 使用は自己責任でお願いします。セーブデータの破損などについて作者は責任を負いません（適用時にセーブは自動でバックアップされます）。
> 問題が起きても公式サポートには問い合わせないでください。

## 何をするか

```
 ┌──────── セーブ/ロード画面 ────────┐
 │ [ 1][ 9]                            │   ページボタンは今までどおり 15個 + Q
 │ [ 2][10]      セーブ枠 ×6           │   その下に ◀ ▶ を追加して
 │  …   …        (No.001〜450)        │   1-15 / 16-30 / 31-45 / 46-60 / 61-75
 │ [ 8][ Q]                            │   の組を切り替える
 │ [◀][▶]                              │
 └─────────────────────────────────────┘
```

- ページ 16〜75 のボタン画像は、**あなたのゲームに入っている** 1〜10 のボタンから数字を切り出して組み立てる
- 枠番号は 3桁（No.100〜450）まで表示する
- PageUp/PageDown・Qページ（クイックセーブ）・最新セーブの「NEW」表示は 450枠に対応している
- ゲーム本体のファイル（`data_0x.dat` など）は書き換えない。
  ゲームの `CatSystem/` フォルダに上書き用のファイルを 3つ追加するだけ（ゲームはここにあるファイルを優先して読む）

### 上限が 75ページの理由
Steamクラウドの上限は 1000ファイル。1枠でファイルを 2つ（データ＋プレビュー）使う。
450枠なら設定ファイルなどを含めても約 930ファイルで、上限内に収まる。

## 仕組み（著作物を含まない理由）

このリポジトリにあるのは **自作のコードだけ**。適用するときに、あなたのPC上で次の処理をする。

1. Steam のライブラリから ONE. のインストール先を探す
2. ゲームのアセンブリ（`ONE_Data/Managed/Assembly-CSharp.dll`）から、データパッケージを開くためのキーを読み取る
   （.NET のメタデータを解析する自作コード。キーはリポジトリに入っていない）
3. `CatSystem/data_01.dat`, `data_03.dat` から次の 3ファイルを取り出す
   `fes/saveload.cstx`, `image/sys/sys_saveload.atx`, `image/sys/sys_saveload_panel.atx`
4. 取り出したファイルを、ルールに従ってプログラムで書き換える
   - スクリプト: ページ数、◀▶ボタン、3桁表示などの命令を追加・置換する
   - 画像: 数字を組み立ててボタン画像を作る。部品の配置を追加する
5. 生成した 3ファイルを `ONE/CatSystem/` の下に書き込む

想定と違うバージョンのゲームでは、置き換える場所が見つからなければ何も書き込まずに中止する。

## 必要なもの

- Steam版 ONE.（Linux は Proton で動作）
- Python 3.8 以上
- Python の部品 Pillow と NumPy（`requirements.txt`）。
  初回実行時に、このフォルダの `.venv/` へ自動で入れる（インターネット接続が必要）。
  自分で入れる場合は `pip install -r requirements.txt`

## 使い方

ゲームを終了してから実行する。Steam の起動オプションは変えなくていい。

### Linux（Steam Deck / Bazzite など）
- **適用**: `ONE_patch.desktop` をダブルクリック（または端末で `./patch.sh`）
- **取り外し**: `ONE_unpatch.desktop`（または `./unpatch.sh`）
- `.desktop` を開くとき「信頼する／実行を許可」を聞かれたら許可する。
  zip で落とした場合は `chmod +x *.sh *.desktop` が必要なことがある

### Windows
- **適用**: `patch.bat` をダブルクリック
- **取り外し**: `unpatch.bat`
- Python は https://www.python.org/ から入れる（`py` ランチャーがあればそれを使う）

### 手動 / 上級者向け
```
python -m onepatch install   [--game ".../steamapps/common/ONE"]
python -m onepatch uninstall [--game ...]
python -m onepatch build --out ./out [--game ...]   # ゲームフォルダは触らず ./out に生成するだけ
```

## バックアップと取り外し

- 適用のたびに、セーブフォルダ（`novamicus/`）を `backup/日時/saves.zip` に保存する
  - Linux: `steamapps/compatdata/2432100/pfx/drive_c/users/steamuser/AppData/Roaming/novamicus`
  - Windows: `%APPDATA%\novamicus`
- 同じ場所にこのツール以外のファイルがあった場合は、それも `backup/` に退避する
- 取り外しでは、このツールが作ったファイルだと確認できたものだけを消す。セーブは消さない
- 取り外すと 91枠目以降のセーブは画面に出なくなるけど、ファイルは残る。もう一度適用すれば見える

## 注意

- ゲームがアップデートされたら、一度取り外してから適用し直すのがおすすめ
  （その時点のゲームデータから作り直すため）
- 「ゲームファイルの整合性を確認」をしても追加したファイルは消えない。消したいときは取り外しを使う
- Windows 版のスクリプトは Linux 版と同じ Python コードを使うけど、実機での確認は少ない

---

## English (short)

Unofficial tool that expands the save/load screen of the Steam release of *ONE. ～輝く季節へ～*
from 15 pages (90 slots) to 75 pages (450 slots). Not affiliated with VISUAL ARTS, Key or novamicus.
You must own the game. Use at your own risk.

The repository contains no game data. At install time the tool reads the package key from the
game's own assembly, extracts three files from your installation, modifies them programmatically
(rule-based script edits, tab images recomposed from your own digit glyphs), and writes three
override files into `ONE/CatSystem/`. `unpatch` removes them. Saves are backed up first.

Requirements: Python 3.8+, Pillow, NumPy (`pip install -r requirements.txt`; the launcher
scripts create a local `.venv` automatically). Run `patch.sh` / `ONE_patch.desktop` on Linux or
`patch.bat` on Windows. Code is MIT-licensed (see `LICENSE`).
