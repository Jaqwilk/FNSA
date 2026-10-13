"""Optional recollection of public post permalinks using Scrapling.

New captures are saved separately in collections/; the frozen data/ snapshot is preserved.
"""
import argparse
import csv
import json
import subprocess
import sys
import time
from datetime import datetime,timezone
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'tools'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit',type=int,default=5,help='Maximum post count (default: 5)')
    parser.add_argument('--group',help='Optional group_id from data/groups.csv')
    parser.add_argument('--run',action='store_true',help='Fetch new captures; otherwise print the plan only')
    args=parser.parse_args()
    if args.limit<1:parser.error('--limit must be positive')
    posts=list(csv.DictReader((BASE/'data/posts.csv').open()))
    if args.group:posts=[p for p in posts if p['group_id']==args.group]
    posts=posts[:args.limit]
    if not args.run:
        print('Public permalink plan; no requests made:')
        for p in posts:print(p['post_id'],p['source_url'])
        return
    from scrapling.fetchers import DynamicSession
    from extract_facebook_capture import extract,objects
    from scrapling.parser import Selector
    root=BASE/'collections'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    root.mkdir(parents=True)
    manifest={'started_at':datetime.now(timezone.utc).isoformat(),'visits':[],'snapshot_unchanged':True}
    with DynamicSession(headless=True,locale='en-US',load_dom=False,timeout=45000,retries=1,google_search=False,capture_xhr=r'/api/graphql/') as session:
        for item in posts:
            folder=root/item['post_id'];folder.mkdir()
            report={'post_id':item['post_id'],'group_id':item['group_id'],'url':item['source_url'],'collected_at':datetime.now(timezone.utc).isoformat(),'errors':[]}
            (folder/'report.json').write_text(json.dumps(report))
            def action(page):
                page.wait_for_timeout(5000)
                for name in ['Decline optional cookies','Reject optional cookies']:
                    button=page.get_by_role('button',name=name,exact=True)
                    if button.count() and button.first.is_visible():
                        button.first.click(timeout=5000);page.wait_for_timeout(2000);break
                close=page.get_by_role('button',name='Close',exact=True)
                if close.count() and close.first.is_visible():close.first.click(timeout=5000);page.wait_for_timeout(3000)
                (folder/'public_view.html').write_text(page.content())
                text=page.locator('body').inner_text()
                if any(t.lower() in text.lower() for t in ["You're Temporarily Blocked",'Too many requests','Confirm you are human']):
                    report['status']='access_limited'
            try:
                response=session.fetch(item['source_url'],page_action=action)
                report['http_status']=response.status
                for n,r in enumerate(response.captured_xhr):(folder/f'xhr_{n}.jsonl').write_bytes(r.body)
                if response.status in [403,429] or report.get('status')=='access_limited':
                    report['status']='access_limited'
                else:
                    records=extract(sorted(list(folder.glob('*.html'))+list(folder.glob('*.jsonl'))),item['group_id'])
                    report['target_found']=any(p['post_id']==item['post_id'] for p in records[0])
                    report['status']='captured' if report['target_found'] else 'target_not_served'
                    output=folder/'processed'
                    subprocess.run([sys.executable,str(BASE/'tools/extract_facebook_capture.py'),str(folder),'--group-id',item['group_id'],'--output',str(output)],check=True)
                    subprocess.run([sys.executable,str(BASE/'tools/enrich_facebook_capture.py'),str(folder),'--group-id',item['group_id'],'--output',str(output)],check=True)
                    # Author types and labels come only from explicit source objects.
                    needed={p['author_id'] for p in records[0]}|{c['author_id'] for c in records[5]}
                    actors={}
                    for raw in list(folder.glob('*.html'))+list(folder.glob('*.jsonl')):
                        scripts=Selector(raw.read_text()).css('script[type="application/json"]::text').getall() if raw.suffix=='.html' else raw.read_text().removeprefix('for (;;);').splitlines()
                        for s in scripts:
                            try:nodes=objects(json.loads(s))
                            except ValueError:continue
                            for node in nodes:
                                if str(node.get('id','')) in needed and node.get('__typename') in ['User','Page','GroupAnonAuthorProfile']:
                                    aid=str(node['id']);entry=actors.setdefault(aid,{})
                                    entry.update(actor_id=aid,actor_type=node['__typename'])
                                    if node.get('name'):entry['display_name']=node['name']
                                    entry['identity_scope']='group:'+item['group_id'] if node['__typename']=='GroupAnonAuthorProfile' else 'as_served'
                    with (output/'actor_metadata.csv').open('w',newline='') as f:
                        w=csv.DictWriter(f,fieldnames=['actor_id','actor_type','display_name','identity_scope']);w.writeheader();w.writerows(actors.values())
            except Exception as exc:report['errors'].append(str(exc));report['status']='error'
            (folder/'report.json').write_text(json.dumps(report,indent=2))
            manifest['visits'].append(report)
            (root/'manifest.json').write_text(json.dumps(manifest,indent=2))
            print(item['post_id'],report['status'])
            if report['status']=='access_limited':break
            time.sleep(5)
    manifest['finished_at']=datetime.now(timezone.utc).isoformat()
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('New collection:',root)


if __name__=='__main__':main()
