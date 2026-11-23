import argparse, collections, datetime, html, json, os, pathlib, subprocess, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
USER = 'WassimBenAzzoun'

def api(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': USER + '-profile'}
    if os.getenv('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    with urllib.request.urlopen('https://api.github.com/' + path, timeout=30) as response:
        return json.load(response)

def aggregate(repos):
    langs = collections.Counter()
    for repo in repos:
        if not repo.get('isFork'):
            for lang in repo.get('languages', []):
                langs[lang['node']['name']] += lang['size']
    return {'repositories': len(repos), 'originals': sum(not r['isFork'] for r in repos), 'stars': sum(r['stargazerCount'] for r in repos), 'forks': sum(r.get('forkCount', 0) for r in repos), 'languages': dict(langs)}

def card(title, body, height):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="860" height="{height}" viewBox="0 0 860 {height}" role="img" aria-label="{html.escape(title)}"><rect x="1" y="1" width="858" height="{height-2}" rx="20" fill="#0d1117" stroke="#263449"/><style>text{{font-family:Segoe UI,Arial,sans-serif}}</style><text x="32" y="40" fill="#e6edf3" font-size="19" font-weight="700">{html.escape(title)}</text>{body}</svg>'''

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh-private', action='store_true')
    args = parser.parse_args()
    snapshot_path = ROOT / 'assets' / 'private-aggregates.json'
    if args.refresh_private:
        raw = subprocess.check_output(['gh','repo','list',USER,'--limit','1000','--json','isPrivate,isFork,languages,stargazerCount,forkCount'], text=True)
        private = aggregate([r for r in json.loads(raw) if r['isPrivate']])
        private['snapshot_date'] = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
        snapshot_path.write_text(json.dumps(private, indent=2) + '\n', encoding='utf-8')
    private = json.loads(snapshot_path.read_text(encoding='utf-8'))
    repos = []
    page = 1
    while True:
        batch = api(f'users/{USER}/repos?type=owner&per_page=100&page={page}')
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    public = aggregate([{'isFork':r['fork'],'stargazerCount':r['stargazers_count'],'forkCount':r['forks_count'],'languages':[]} for r in repos])
    langs = collections.Counter(private['languages'])
    for repo in repos:
        if not repo['fork']:
            langs.update(api(f'repos/{USER}/{repo["name"]}/languages'))
    user = api(f'users/{USER}')
    metrics = [('Repositories',public['repositories'] + private['repositories']),('Public',public['repositories']),('Private',private['repositories']),('Stars earned',public['stars'] + private['stars']),('Followers',user['followers']),('Forks received',public['forks'] + private['forks'])]
    body = ''
    for i, (label, value) in enumerate(metrics):
        x = 32 + (i % 3) * 275
        y = 91 + (i // 3) * 83
        body += f'<text x="{x}" y="{y}" fill="{["#67e8f9","#c4b5fd","#86efac"][i%3]}" font-size="32" font-weight="700">{value}</text><text x="{x}" y="{y+24}" fill="#9daec3" font-size="13">{label}</text>'
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
    body += f'<text x="32" y="229" fill="#8b949e" font-size="11">Public data: {now} UTC · Private aggregates: {private["snapshot_date"]}</text>'
    (ROOT/'assets'/'stats.svg').write_text(card('GitHub by the numbers',body,250),encoding='utf-8')
    total = sum(langs.values())
    colors = ['#67e8f9','#c4b5fd','#86efac','#f9a8d4','#fcd34d','#93c5fd','#fdba74','#a5b4fc']
    top = langs.most_common(8)
    body = '<text x="32" y="65" fill="#8b949e" font-size="12">Public + private original repositories · share of code bytes</text>'
    for i,(name,size) in enumerate(top):
        y = 98 + i * 37
        pct = size / total * 100 if total else 0
        body += f'<text x="32" y="{y}" fill="#c9d1d9" font-size="13">{html.escape(name)}</text><rect x="190" y="{y-11}" width="550" height="10" rx="5" fill="#1c2634"/><rect x="190" y="{y-11}" width="{max(1,550*pct/100):.1f}" height="10" rx="5" fill="{colors[i]}"/><text x="765" y="{y}" fill="{colors[i]}" font-size="13">{pct:.1f}%</text>'
    body += f'<text x="32" y="{105+len(top)*37}" fill="#8b949e" font-size="11">Top 8 of {len(langs)} languages · Forks excluded · Private snapshot: {private["snapshot_date"]}</text>'
    (ROOT/'assets'/'languages.svg').write_text(card('Languages I build with',body,130+len(top)*37),encoding='utf-8')
    print('Generated aggregate stats and language cards; no private repository names saved.')

if __name__ == '__main__':
    main()
