"""Extract served text and explicitly tagged actor edges from saved Facebook JSON."""
import argparse
import csv
import json
from pathlib import Path
from scrapling.parser import Selector
from extract_facebook_capture import objects, extract, ROOT


def enrich(folder, group_id):
    paths=sorted(list(folder.glob('*.html'))+list(folder.glob('xhr_*.jsonl')))
    posts,users,participation,groups,engagement,comments=extract(paths,group_id)
    post_map={p['post_id']:p for p in posts};comment_map={c['comment_id']:c for c in comments}
    nodes=[]
    for path in paths:
        if path.suffix=='.html': scripts=Selector(path.read_text()).css('script[type="application/json"]::text').getall()
        else:scripts=path.read_text().removeprefix('for (;;);').splitlines()
        for script in scripts:
            try:nodes.extend(objects(json.loads(script)))
            except ValueError:continue
    story_ids={str(n['id']):str(n['post_id']) for n in nodes if n.get('id') and str(n.get('post_id','')) in post_map}
    comment_ids={str(n['id']):str(n['legacy_fbid']) for n in nodes if n.get('id') and str(n.get('legacy_fbid','')) in comment_map}
    texts={};mentions={}
    for node in nodes:
        internal_id=str(node.get('id',''))
        if internal_id in story_ids and isinstance(node.get('message'),dict):
            kind='post';item_id=story_ids[internal_id];body=node['message'];record=post_map[item_id]
        elif internal_id in comment_ids and isinstance(node.get('body'),dict):
            kind='comment';item_id=comment_ids[internal_id];body=node['body'];record=comment_map[item_id]
        else:continue
        text=body.get('text')
        if not isinstance(text,str) or not text:continue
        key=(kind,item_id)
        row={'record_type':kind,'record_id':item_id,'post_id':record['post_id'],'text':text,'source_url':record['source_url'],'collected_at':record['collected_at'],'text_completeness':'as_served'}
        if key not in texts or len(text)>len(texts[key]['text']):texts[key]=row
        source_id=record.get('author_id','')
        for span in body.get('ranges',[]):
            entity=span.get('entity') or {}
            target_id=str(entity.get('id') or '');target_type=entity.get('__typename') or entity.get('__isEntity')
            if not source_id or not target_id or target_type not in {'User','Page'}:continue
            offset,length=span.get('offset'),span.get('length')
            if not isinstance(offset,int) or not isinstance(length,int):continue
            label=text.encode('utf-16-le')[offset*2:(offset+length)*2].decode('utf-16-le',errors='replace')
            edge={'source_actor_id':source_id,'target_actor_id':target_id,'target_actor_type':target_type,
                  'interaction_type':'tagged_mention','record_type':kind,'record_id':item_id,
                  'post_id':record['post_id'],'timestamp':record['timestamp'],'tagged_label':label,
                  'offset_utf16':offset,'length_utf16':length,'source_url':record['source_url'],'collected_at':record['collected_at']}
            mentions[(kind,item_id,target_id,offset,length)]=edge
    return list(texts.values()),list(mentions.values())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture',type=Path)
    parser.add_argument('--group-id',default='2673424766123352')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    texts,mentions=enrich(args.capture,args.group_id)
    args.output.mkdir(parents=True,exist_ok=True)
    schemas={'served_text':['record_type','record_id','post_id','text','source_url','collected_at','text_completeness'],
             'mentions':['source_actor_id','target_actor_id','target_actor_type','interaction_type','record_type','record_id','post_id','timestamp','tagged_label','offset_utf16','length_utf16','source_url','collected_at']}
    for name,rows in [('served_text',texts),('mentions',mentions)]:
        with (args.output/f'{name}.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=schemas[name]);w.writeheader();w.writerows(rows)
    summary={'post_texts':sum(t['record_type']=='post' for t in texts),'comment_texts':sum(t['record_type']=='comment' for t in texts),'tagged_mentions':len(mentions),
             'mention_keys':sorted('|'.join(str(e[k]) for k in ['record_type','record_id','source_actor_id','target_actor_id','offset_utf16','length_utf16']) for e in mentions)}
    (args.output/'enrichment_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))


if __name__=='__main__':main()
