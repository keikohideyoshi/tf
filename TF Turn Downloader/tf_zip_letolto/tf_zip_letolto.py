#!/usr/bin/env python3
"""TF ZIP downloader and safe, flat HTML collector."""
import argparse
import re
import sys
import zipfile
from pathlib import Path

URL = 'https://beholder.hu/?m=tf&in=karakter.php&karakter={}'
PROFILE = Path.home() / '.local/share/tf-zip-letolto/browser-profile'


def safe_filename(name):
    name = name.replace('\\', '/').split('/')[-1]
    return re.sub(r'[\x00-\x1f<>:"|?*]', '_', name).strip(' .') or 'ismeretlen.htm'


def collect_html(zip_folder, html_folder):
    """Extract HTML files without directories; avoid overwrites and unsafe paths."""
    html_folder.mkdir(parents=True, exist_ok=True)
    zips = sorted(zip_folder.glob('*.zip'))
    extracted = unchanged = errors = 0
    for number, archive in enumerate(zips, 1):
        try:
            with zipfile.ZipFile(archive) as zf:
                members = [m for m in zf.infolist() if not m.is_dir() and m.filename.lower().endswith(('.htm', '.html'))]
                for member in members:
                    original = safe_filename(member.filename)
                    # Prefix by archive stem to prevent collisions between turns.
                    prefix = safe_filename(archive.stem)
                    dest = html_folder / f'{prefix}__{original}'
                    try:
                        data = zf.read(member)  # validates CRC
                        if dest.exists() and dest.read_bytes() == data:
                            unchanged += 1
                            continue
                        if dest.exists():
                            suffix = 2
                            while (html_folder / f'{prefix}__{suffix}__{original}').exists():
                                suffix += 1
                            dest = html_folder / f'{prefix}__{suffix}__{original}'
                        dest.write_bytes(data)
                        extracted += 1
                    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                        errors += 1
                        print(f'  Hiba: {archive.name} / {member.filename}: {exc}')
            print(f'[{number}/{len(zips)}] Feldolgozva: {archive.name} ({len(members)} HTML)')
        except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
            errors += 1
            print(f'  Hibás ZIP: {archive.name}: {exc}')
    print(f'HTML-ek: új {extracted}, változatlan {unchanged}, hiba {errors}.')
    print(f'HTML célmappa: {html_folder}')
    return errors


def download_zips(character, target):
    from playwright.sync_api import sync_playwright
    target.mkdir(parents=True, exist_ok=True)
    PROFILE.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(str(PROFILE), headless=False, accept_downloads=True)
        page = browser.pages[0] if browser.pages else browser.new_page()
        try:
            page.goto(URL.format(character), wait_until='domcontentloaded', timeout=60000)
            print('\nJelentkezz be, ha szükséges, és nyisd meg a karakteroldalt.')
            input('Ha látszanak a (ZIP) linkek, nyomj ENTER-t... ')
            if character not in page.url.upper():
                page.goto(URL.format(character), wait_until='domcontentloaded', timeout=60000)
            links = page.locator('a').filter(has_text=re.compile(r'^\s*\(\s*ZIP\s*\)\s*$', re.I))
            count = links.count()
            print(f'ZIP-linkek: {count}')
            if not count:
                return 1
            success = skipped = failed = 0
            for index in range(count):
                try:
                    with page.expect_download(timeout=45000) as event:
                        links.nth(index).click(timeout=15000)
                    dl = event.value
                    filename = safe_filename(dl.suggested_filename)
                    if not filename.lower().endswith('.zip'):
                        raise ValueError(f'Nem ZIP: {filename}')
                    dest = target / filename
                    if dest.exists() and dest.stat().st_size > 0:
                        skipped += 1
                        print(f'[{index+1}/{count}] Meglévő: {filename}')
                        continue
                    dl.save_as(dest)
                    if not zipfile.is_zipfile(dest):
                        dest.unlink(missing_ok=True)
                        raise ValueError(f'Érvénytelen ZIP: {filename}')
                    success += 1
                    print(f'[{index+1}/{count}] Letöltve: {filename}')
                except Exception as exc:
                    failed += 1
                    print(f'[{index+1}/{count}] Hiba: {exc}')
                    if character not in page.url.upper():
                        page.goto(URL.format(character), wait_until='domcontentloaded', timeout=60000)
            print(f'Letöltés kész: új {success}, meglévő {skipped}, hiba {failed}.')
            return failed
        finally:
            browser.close()


def main():
    parser = argparse.ArgumentParser(description='TF ZIP letöltő és HTML kigyűjtő')
    parser.add_argument('--karakter', default='TF3042')
    parser.add_argument('--cel', type=Path, default=None, help='A ZIP-ek meglévő mappája')
    parser.add_argument('--html-cel', type=Path, default=None, help='A kigyűjtött HTML-ek mappája')
    parser.add_argument('--html-only', action='store_true', help='Csak a meglévő ZIP-ekből gyűjt HTML-t, böngésző nélkül')
    args = parser.parse_args()
    character = args.karakter.upper().strip()
    if not re.fullmatch(r'TF\d+', character):
        parser.error('Karakterazonosító példa: TF3042')
    target = (args.cel or Path.home() / 'Letöltések' / 'TF' / character).expanduser().resolve()
    html_target = (args.html_cel or target / 'HTML').expanduser().resolve()
    if not args.html_only:
        download_errors = download_zips(character, target)
    else:
        download_errors = 0
    if not target.exists():
        print(f'Nem létezik a ZIP-mappa: {target}')
        return 1
    extraction_errors = collect_html(target, html_target)
    return 1 if download_errors or extraction_errors else 0


if __name__ == '__main__':
    sys.exit(main())
