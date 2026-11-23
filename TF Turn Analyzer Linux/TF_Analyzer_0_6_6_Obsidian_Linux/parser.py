from email.parser import BytesParser
from email.message import Message
from email import policy
from bs4 import BeautifulSoup
from pathlib import Path
import re, hashlib, json, sqlite3, zlib

DB = Path(__file__).parent / 'tf_analyzer.sqlite3'

def extract_html(data):
    msg = BytesParser(policy=policy.default).parsebytes(data)
    parts = [p for p in msg.walk() if p.get_content_type() == 'text/html']
    if not parts:
        raise ValueError('A fájlban nem található HTML-rész.')
    part = parts[0]
    raw = part.get_payload(decode=True)
    charset = part.get_content_charset() or 'utf-8'
    try:
        return raw.decode(charset)
    except (LookupError, UnicodeDecodeError):
        return raw.decode('utf-8', errors='replace')

def extract_plain_html(data):
    """Decode standalone HTML, preserving the original game HTML tags."""
    # UTF-8 BOM, HTML5 meta charset, legacy HTML content-type and common TF encodings.
    if data.startswith(b'\xef\xbb\xbf'):
        return data.decode('utf-8-sig')
    head = data[:8192]
    m = re.search(rb'<meta\b[^>]*?charset\s*=\s*["\']?([\w.-]+)', head, re.I)
    if not m:
        m = re.search(rb'<meta\b[^>]*?content\s*=\s*["\'][^"\']*?charset\s*=\s*([\w.-]+)', head, re.I)
    charsets = [m.group(1).decode('ascii', 'ignore') if m else None, 'utf-8', 'windows-1250', 'iso-8859-2']
    for charset in charsets:
        if not charset:
            continue
        try:
            return data.decode(charset)
        except (UnicodeError, LookupError):
            continue
    return data.decode('windows-1250', errors='replace')

def extract_turn_html(data, filename=''):
    ext = Path(filename).suffix.lower()
    if ext in ('.html', '.htm'):
        return extract_plain_html(data)
    if ext in ('.mhtml', '.mht'):
        return extract_html(data)
    raise ValueError('Nem támogatott fájlformátum (HTML, HTM, MHTML vagy MHT szükséges).')

def parse_turn(data, filename=''):
    html = extract_turn_html(data, filename)
    soup = BeautifulSoup(html, 'html.parser')
    for x in soup(['script','style','noscript']): x.decompose()
    text = soup.get_text('\n', strip=True)
    title = soup.title.get_text(' ',strip=True) if soup.title else filename
    match = re.search(r'(\d+)\.\s*fordul',title,re.I) or re.search(r'(\d+)\.\s*FORDUL',text[:5000],re.I)
    number = int(match.group(1)) if match else None
    char_match = re.search(r'KALANDOZ[ÓO]\s*:\s*#\s*(\d+)',text,re.I)
    character = char_match.group(1) if char_match else 'ismeretlen'
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    commands=[];events=[];failures=[]
    for i,line in enumerate(lines):
        m=re.match(r'^(vv|tf|mak|kld|sze|be|lm|h|e|v|p|k)\s+(\d+(?:\s+\d+){0,8})\s*$',line,re.I)
        if m: commands.append({'line':i+1,'command':m.group(1).upper(),'arguments':m.group(2),'context':' | '.join(lines[i:i+5])[:500]})
        for hit in re.finditer(r'(?<!\w)([+-]\s*\d+)\s*TVP\b',line,re.I):
            events.append({'line':i+1,'kind':'tvp_change','amount':int(hit.group(1).replace(' ','')),'source':' | '.join(lines[max(0,i-2):i+2])[:400]})
        m=re.search(r'(\d+)\s+pontot használtál fel,\s*van még\s*(\d+)',line,re.I)
        if m: events.append({'line':i+1,'kind':'points_spent_unverified','amount':-int(m.group(1)),'source':line[:400]})
    # Csak a HTML-ben hiba osztállyal megjelölt üzenetek számítanak hibának.
    for span in soup.select('span.hiba'):
        msg=span.get_text(' ',strip=True)
        if msg:
            failures.append({'line':None,'text':msg})
    fight_markers=[{'line':i+1,'text':line[:240]} for i,line in enumerate(lines) if re.search(r'\bharc kezdődik\b|\bmegtámad\b|\bcsata kezdődik\b',line,re.I)]
    return {'hash':hashlib.sha256(data).hexdigest(),'filename':filename,'title':title,'turn':number,'character':character,'lines':len(lines),'commands':commands,'events':events,'fight_markers':fight_markers,'failures':failures,'text':text,'_html':html}

def connect():
    con=sqlite3.connect(DB)
    con.execute('''CREATE TABLE IF NOT EXISTS turns (hash TEXT PRIMARY KEY, filename TEXT, turn_number INTEGER, character TEXT, title TEXT, line_count INTEGER, payload TEXT)''')
    con.execute('''CREATE TABLE IF NOT EXISTS turn_html (hash TEXT PRIMARY KEY REFERENCES turns(hash), html_zlib BLOB NOT NULL)''')
    con.commit()
    return con

def save(parsed):
    con=connect()
    payload={k:v for k,v in parsed.items() if k!='_html'}
    existing=con.execute('SELECT 1 FROM turns WHERE hash=?',(parsed['hash'],)).fetchone()
    if not existing:
        con.execute('INSERT INTO turns VALUES (?,?,?,?,?,?,?)',(parsed['hash'],parsed['filename'],parsed['turn'],parsed['character'],parsed['title'],parsed['lines'],json.dumps(payload,ensure_ascii=False)))
    # Crucial: restore HTML even for a previously imported turn with same hash.
    html=parsed.get('_html')
    if html is not None:
        con.execute('INSERT OR REPLACE INTO turn_html(hash,html_zlib) VALUES (?,?)',(parsed['hash'],sqlite3.Binary(zlib.compress(html.encode('utf-8'),level=6))))
    con.commit();con.close()
    return not bool(existing)

def clear_database():
    """Clear imported turns and their HTML in a single SQLite transaction.

    Keep the database file and schema so a fresh import works immediately.
    """
    con = connect()
    try:
        with con:
            con.execute('DELETE FROM turn_html')
            con.execute('DELETE FROM turns')
    finally:
        con.close()

def load_all():
    con=connect()
    rows=con.execute('SELECT t.payload,h.html_zlib FROM turns t LEFT JOIN turn_html h ON h.hash=t.hash ORDER BY t.turn_number').fetchall()
    con.close()
    data=[]
    for payload,packed in rows:
        obj=json.loads(payload)
        obj['_html']=zlib.decompress(packed).decode('utf-8') if packed is not None else None
        data.append(obj)
    return data

# Backwards compatibility for existing scripts using the former function name.
def parse_mhtml(data, filename=''):
    return parse_turn(data, filename)
