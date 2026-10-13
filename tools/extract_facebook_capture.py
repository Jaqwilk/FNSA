"""Extract verified post/actor fields from Facebook JSON embedded in captured HTML."""
import argparse
import csv
import json
import re
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone
from pathlib import Path
from scrapling.parser import Selector

ROOT = Path(__file__).resolve().parents[1]


def objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)


def extract(paths, target_group=None):
    stories, groups, feedback, comment_objects, comment_links = {}, {}, {}, {}, {}
    for path in paths:
        report_path = path.parent / 'report.json'
        captured_at = json.loads(report_path.read_text()).get('collected_at', '') if report_path.exists() else ''
        if path.suffix == '.html':
            selector = Selector(path.read_text())
            scripts = selector.css('script[type="application/json"]::text').getall()
            for a in selector.css('a'):
                href = a.attrib.get('href','')
                match = re.search(r'/(?:posts|permalink)/(\d+)',href)
                cid = parse_qs(urlparse(href).query).get('comment_id',[])
                if match and cid:
                    comment_links[cid[0]] = (match.group(1), href.split('&')[0])
        else:
            scripts = path.read_text().removeprefix('for (;;);').splitlines()
        for script in scripts:
            try:
                data = json.loads(script)
            except ValueError:
                continue
            for obj in objects(data):
                if obj.get('id') and obj.get('legacy_fbid') and obj.get('author') and (obj.get('__typename') == 'Comment' or 'body' in obj):
                    comment = comment_objects.setdefault(str(obj['id']), {})
                    for k,v in obj.items():
                        if k in ['legacy_fbid','author','created_time','comment_direct_parent','depth','body'] and (v is not None or k == 'comment_direct_parent'):
                            comment[k] = v
                    comment['collected_at'] = captured_at
                if obj.get('__typename') == 'Group' and obj.get('id'):
                    group = groups.setdefault(str(obj['id']), {})
                    group.update({k: v for k, v in obj.items() if k in ['id', 'name', 'url'] and v is not None})
                if obj.get('id') and any(k in obj for k in ['reaction_count','share_count','total_comment_count']):
                    item = feedback.setdefault(str(obj['id']), {})
                    item.update({k:v for k,v in obj.items() if k in ['reaction_count','share_count','total_comment_count'] and v is not None})
                if obj.get('id') and (obj.get('__typename') == 'Story' or obj.get('post_id')):
                    key = str(obj['id'])
                    story = stories.setdefault(key, {})
                    story['collected_at'] = captured_at
                    for field in ['post_id', 'creation_time', 'actors', 'to', 'permalink_url', 'url', 'feedback']:
                        if obj.get(field) is not None:
                            if field == 'actors' and story.get(field):
                                old_score = sum(len(a) for a in story[field])
                                new_score = sum(len(a) for a in obj[field])
                                if old_score > new_score:
                                    continue
                            if field == 'feedback' and isinstance(obj[field],dict):
                                story.setdefault(field, {}).update(obj[field])
                            else:
                                story[field] = obj[field]
    users, posts, participation, engagement = {}, {}, {}, {}
    for story in stories.values():
        if not story.get('post_id'):
            continue
        post_id = str(story['post_id'])
        actors = story.get('actors') or []
        # Multiple actors are preserved as an unresolved author rather than guessed.
        author = actors[0] if len(actors) == 1 else {}
        author_id = str(author.get('id') or '')
        group = story.get('to') or {}
        group_id = str(group.get('id') or '') if group.get('__typename') == 'Group' else ''
        if target_group and group_id != target_group:
            continue
        ts = story.get('creation_time')
        stamp = datetime.fromtimestamp(ts, timezone.utc).isoformat() if isinstance(ts, (int, float)) else ''
        url = story.get('permalink_url') or story.get('url') or ''
        posts[post_id] = dict(post_id=post_id, author_id=author_id, group_id=group_id, timestamp=stamp, source_url=url, collected_at=story.get('collected_at',''))
        fb = feedback.get(str((story.get('feedback') or {}).get('id','')), {})
        def count(value):
            return value.get('count','') if isinstance(value,dict) else (value if isinstance(value,int) else '')
        if fb:
            engagement[post_id] = dict(post_id=post_id, reaction_count=count(fb.get('reaction_count')), share_count=count(fb.get('share_count')), comment_count=count(fb.get('total_comment_count')), source_url=url, collected_at=story.get('collected_at',''))
        if author_id and author.get('__typename') == 'User':
            users[author_id] = dict(user_id=author_id, username=author.get('username') or '', display_name=author.get('name') or '', source_url=url, collected_at=story.get('collected_at',''))
        if author_id and group_id and author.get('__typename') == 'User':
            participation[group_id, author_id] = dict(group_id=group_id, user_id=author_id, evidence_type='observed_post_author', source_url=url, collected_at=story.get('collected_at',''))
    comments = []
    for comment in comment_objects.values():
        cid = str(comment['legacy_fbid'])
        post_id, url = comment_links.get(cid, ('',''))
        if post_id not in posts:
            continue
        author = comment.get('author') or {}
        aid = str(author.get('id') or '')
        parent = comment.get('comment_direct_parent') or {}
        parent_id = str(parent.get('legacy_fbid') or '')
        if not parent_id and parent.get('id') in comment_objects:
            parent_id = str(comment_objects[parent['id']]['legacy_fbid'])
        ts = comment.get('created_time')
        stamp = datetime.fromtimestamp(ts, timezone.utc).isoformat() if isinstance(ts,(int,float)) else ''
        comments.append(dict(comment_id=cid, author_id=aid, parent_comment_id=parent_id, post_id=post_id, timestamp=stamp, source_url=url, collected_at=comment.get('collected_at',''), parent_relation_verified=comment.get('depth') == 0 or bool(parent_id)))
        if aid and author.get('__typename') == 'User':
            users.setdefault(aid,dict(user_id=aid, username=author.get('username') or '', display_name=author.get('name') or '', source_url=url, collected_at=comment.get('collected_at','')))
            gid = posts[post_id]['group_id']
            participation.setdefault((gid,aid),dict(group_id=gid, user_id=aid, evidence_type='observed_comment_author', source_url=url, collected_at=comment.get('collected_at','')))
    return list(posts.values()), list(users.values()), list(participation.values()), list(groups.values()), list(engagement.values()), comments


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path, nargs='+', help='HTML files or audit directories')
    parser.add_argument('--output', type=Path, default=ROOT/'data/processed/public_audit')
    parser.add_argument('--group-id', help='Only export posts attributed to this group')
    args = parser.parse_args()
    paths = [file for p in args.capture for file in (sorted(list(p.glob('*.html')) + list(p.glob('xhr_*.jsonl'))) if p.is_dir() else [p])]
    posts, users, participation, groups, engagement, comments = extract(paths, args.group_id)
    args.output.mkdir(parents=True, exist_ok=True)
    collected_at = datetime.now(timezone.utc).isoformat()
    datasets = [
        ('comments', comments, ['comment_id','author_id','parent_comment_id','post_id','timestamp','source_url','collected_at','parent_relation_verified']),
        ('engagement_counts', engagement, ['post_id','reaction_count','share_count','comment_count','source_url','collected_at']),
        ('posts', posts, ['post_id','author_id','group_id','timestamp','source_url','collected_at']),
        ('users', users, ['user_id','username','display_name','source_url','collected_at']),
        ('group_participation', participation, ['group_id','user_id','evidence_type','source_url','collected_at']),
    ]
    for name, rows, fields in datasets:
        with (args.output/f'{name}.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields+['processed_at'])
            writer.writeheader()
            writer.writerows(dict(row, processed_at=collected_at) for row in rows)
    summary = dict(comments=len(comments), replies=sum(bool(x['parent_comment_id']) for x in comments), posts=len(posts), users=len(users), observed_participation=len(participation),
                   groups=groups, captures=[str(p) for p in paths],
                   note='Only observed post/comment authors; not a complete membership list. username is blank when absent; display_name is separate. processed_at is extraction time; capture folders contain collection times.')
    (args.output/'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ['posts','users','observed_participation','comments','replies']}))


if __name__ == '__main__':
    main()
