"""Validate the frozen project, notebook execution and exported graphs offline."""
from pathlib import Path
import csv
import hashlib
import json
import math
import networkx as nx
import nbformat

BASE = Path(__file__).resolve().parent

def validate():
    data = {}
    hashes = {}
    for path in sorted((BASE/'data').glob('*.csv')):
        with path.open(encoding='utf-8', newline='') as f:
            data[path.stem] = list(csv.DictReader(f))
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    ids = lambda table, field: {r[field] for r in data[table]}
    actors, posts, groups = ids('actors','actor_id'), ids('posts','post_id'), ids('groups','group_id')
    checks = {}
    for table, field in [('posts','post_id'), ('comments','comment_id'), ('actors','actor_id'), ('groups','group_id'), ('interaction_events','event_id')]:
        checks[f'{table}_unique_ids'] = len(ids(table,field)) == len(data[table]) and '' not in ids(table,field)
    checks['post_actor_group_joins'] = all(r['author_id'] in actors and r['group_id'] in groups for r in data['posts'])
    checks['comment_actor_post_joins'] = all(r['author_id'] in actors and r['post_id'] in posts for r in data['comments'])
    checks['interaction_endpoint_joins'] = all(r['source_actor_id'] in actors and r['target_actor_id'] in actors and r['group_id'] in groups and r['post_id'] in posts for r in data['interaction_events'])
    checks['mention_endpoint_joins'] = all(r['source_actor_id'] in actors and r['target_actor_id'] in actors and r['post_id'] in posts for r in data['mentions'])
    checks['participation_joins'] = all(r['actor_id'] in actors and r['group_id'] in groups for r in data['participation'])
    from datetime import datetime
    checks['timezone_aware_publication_times'] = all(datetime.fromisoformat(r['timestamp']).tzinfo is not None for table in ['posts','comments','interaction_events'] for r in data[table])
    summary = json.loads((BASE/'results/summary.json').read_text())
    variants = {}
    for variant, result in summary['variants'].items():
        g = nx.read_graphml(BASE/'results'/f'{variant}_interactions.graphml')
        b = nx.read_graphml(BASE/'results'/f'{variant}_participation.graphml')
        m = result['networks']['combined']
        checks[f'{variant}_graph_counts'] = (len(g),g.number_of_edges(),len(list(nx.isolates(g)))) == (m['nodes'],m['edges'],m['isolates'])
        checks[f'{variant}_weights_no_loops'] = nx.number_of_selfloops(g)==0 and sum(d['weight'] for _,_,d in g.edges(data=True))==m['events_without_self_loops']
        checks[f'{variant}_density_components'] = math.isclose(nx.density(g),m['density']) and nx.number_weakly_connected_components(g)==m['weak_components']
        checks[f'{variant}_participation_weights'] = nx.is_bipartite(b) and sum(d['weight'] for _,_,d in b.edges(data=True))==result['posts']+result['comments']
        checks[f'{variant}_anonymous_scope'] = all(n == f"anonymous:{d['identity_scope'].split(':',1)[1]}:{d['actor_id']}" for n,d in g.nodes(data=True) if d['actor_type']=='GroupAnonAuthorProfile')
        variants[variant] = {k:m[k] for k in ['nodes','active_nodes','isolates','edges','events_without_self_loops','density','weak_components']}
    n = nbformat.read(BASE/'analysis.ipynb',as_version=4)
    cells = [c for c in n.cells if c.cell_type=='code']
    checks['notebook_all_cells_executed'] = all(c.execution_count is not None for c in cells)
    checks['notebook_no_errors'] = not any(o.output_type=='error' for c in cells for o in c.outputs)
    checks['analysis_assertions'] = all(summary['validation'].values())
    report = {'status':'passed' if all(checks.values()) else 'failed','checks':checks,'table_counts':{k:len(v) for k,v in data.items()},'combined_networks':variants,'data_sha256':hashes,'scope':'Offline project validation; successful extraction does not establish complete public coverage.'}
    (BASE/'results/validation.json').write_text(json.dumps(report,indent=2)+'\n')
    assert all(checks.values()), [k for k,v in checks.items() if not v]
    print(f"All {len(checks)} project checks passed; {len(cells)} notebook code cells executed.")
    return report

if __name__=='__main__':
    validate()
