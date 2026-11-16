import argparse,json
from core import conn,import_references,import_folder,search_turns,stats
p=argparse.ArgumentParser();p.add_argument('command',choices=['init','import','search','stats']);p.add_argument('argument',nargs='?',default='');p.add_argument('--character',type=int);a=p.parse_args();c=conn()
if a.command=='init':print('Enciklopédiák:',import_references(c))
elif a.command=='import':print(*import_folder(c,a.argument),sep='\n')
elif a.command=='search':print(json.dumps(search_turns(c,a.argument,a.character),ensure_ascii=False,indent=2))
else:print(json.dumps(stats(c),ensure_ascii=False,indent=2))
