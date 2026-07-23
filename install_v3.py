from __future__ import annotations
import argparse, getpass, re, shutil, sys
from datetime import datetime
from pathlib import Path


def find_root(start: Path) -> Path:
    for p in [start, *start.parents[:2]]:
        if (p/'app.py').exists(): return p
    raise SystemExit('app.py bulunamadı. Yamayı uygulama ana klasörüne çıkarın.')


def patch_app(app_file: Path) -> None:
    text=app_file.read_text(encoding='utf-8-sig')
    backup=app_file.with_name(f"app.py.v2.9_backup_{datetime.now():%Y%m%d_%H%M%S}")
    shutil.copy2(app_file, backup)
    if 'from enterprise_v3 import register_enterprise_v3' not in text:
        lines=text.splitlines()
        insert=0
        for i,line in enumerate(lines):
            if line.startswith(('import ','from ')): insert=i+1
        lines.insert(insert,'from enterprise_v3 import register_enterprise_v3')
        text='\n'.join(lines)+'\n'
    if 'register_enterprise_v3(app)' not in text:
        marker=re.search(r'^if\s+__name__\s*==\s*[\'\"]__main__[\'\"]\s*:',text,re.M)
        if marker: text=text[:marker.start()]+'\n# v3.0 Kurumsal modül\nregister_enterprise_v3(app)\n\n'+text[marker.start():]
        else: text+='\n# v3.0 Kurumsal modül\nregister_enterprise_v3(app)\n'
    text=re.sub(r'(?m)^(VERSION\s*=\s*)[\'\"][^\'\"]+[\'\"]',r'\1"3.0.0"',text)
    app_file.write_text(text,encoding='utf-8',newline='\n')
    print('app.py yedeklendi ve v3.0 modülü bağlandı:',backup.name)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--non-interactive',action='store_true');ap.add_argument('--admin-user',default='admin');ap.add_argument('--admin-password');args=ap.parse_args()
    root=find_root(Path.cwd());patch_app(root/'app.py')
    sys.path.insert(0,str(root))
    from flask import Flask
    from enterprise_v3 import init_enterprise_db, create_or_update_admin
    app=Flask(__name__,root_path=str(root));app.config['V3_DATABASE']=str(root/'data'/'audit.db');app.secret_key='installer'
    init_enterprise_db(app)
    password=args.admin_password
    if not password and not args.non_interactive:
        while True:
            p1=getpass.getpass('v3.0 yönetici parolası (en az 10 karakter): ');p2=getpass.getpass('Parolayı tekrar girin: ')
            if len(p1)>=10 and p1==p2: password=p1;break
            print('Parolalar eşleşmeli ve en az 10 karakter olmalıdır.')
    if not password: password='ChangeMe_2026!'
    with app.app_context(): create_or_update_admin(args.admin_user,password)
    print('\nKurulum tamamlandı. Kurumsal giriş: http://127.0.0.1:5055/v3/')
    print('Kullanıcı:',args.admin_user)
    if password=='ChangeMe_2026!': print('Geçici parola: ChangeMe_2026! (ilk girişte değiştirin)')

if __name__=='__main__': main()
