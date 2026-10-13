"""Repeatable local corpus analysis; run: python analysis.py."""
from pathlib import Path
import json
import math
from collections import Counter
import pandas as pd
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

COMMUNITY = {'2673424766123352', '20442701688'}
START = pd.Timestamp('2026-01-01', tz='Europe/Warsaw').tz_convert('UTC')
VARIANT_NAMES = {'all_sample':'Full sample', 'community_all':'Two community groups', 'community_2026':'Two communities: 2026'}
END = pd.Timestamp('2026-10-13 23:59:59.999999', tz='Europe/Warsaw').tz_convert('UTC')

def run_analysis(project_dir=None):
    base = Path(project_dir) if project_dir else Path(__file__).resolve().parent
    out, figs = base/'results', base/'figures'
    out.mkdir(exist_ok=True); figs.mkdir(exist_ok=True)
    data = {name: pd.read_csv(base/'data'/f'{name}.csv', dtype=str, keep_default_na=False)
            for name in ['posts','comments','actors','groups','mentions','interaction_events','participation']}
    posts, comments, actors, events = (data[x] for x in ['posts','comments','actors','interaction_events'])
    assert posts.post_id.is_unique and comments.comment_id.is_unique and events.event_id.is_unique
    assert set(comments.post_id) <= set(posts.post_id)
    assert set(events.post_id) <= set(posts.post_id)
    actor_info = {r['actor_id']:r for r in actors.to_dict('records')}
    def node(actor, gid):
        assert actor in actor_info, f'Unknown actor {actor}'
        r = actor_info[actor]
        if r['actor_type']=='GroupAnonAuthorProfile' or r['identity_scope'].startswith('group:'):
            scope = r['identity_scope'].split(':',1)[1] if r['identity_scope'].startswith('group:') else gid
            assert scope == gid, f'Anonymous profile outside its group: {actor}'
            return f'anonymous:{gid}:{actor}'
        return str(actor)
    post_group = dict(zip(posts.post_id, posts.group_id))
    all_nodes = set()
    for r in posts.to_dict('records'): all_nodes.add(node(r['author_id'],r['group_id']))
    for r in comments.to_dict('records'): all_nodes.add(node(r['author_id'],post_group[r['post_id']]))
    for r in events.to_dict('records'):
        all_nodes.update([node(r['source_actor_id'],r['group_id']),node(r['target_actor_id'],r['group_id'])])
    labels = {n:f'A{i:03d}' for i,n in enumerate(sorted(all_nodes),1)}
    pd.DataFrame([{'pseudonym':label,'node_id':n,'actor_id':n.split(':')[-1],
                   'identity_scope':actor_info[n.split(':')[-1]]['identity_scope'],
                   'actor_type':actor_info[n.split(':')[-1]]['actor_type']} for n,label in labels.items()]).to_csv(out/'node_mapping.csv',index=False)
    summaries, metrics, groups_rows, component_rows = [], [], [], []
    summary = {'collection_day':'2026-10-13','timezone':'Europe/Warsaw','variants':{},
               'conventions':{'direction':'Comment author → post author or verified parent comment author; mention author → mentioned actor',
               'weights':'Number of observed events; self-loops removed from analytical graphs.',
               'nodes':'All observed authors of selected posts and comments and endpoints of selected interactions; isolates retained.',
               'participation':'Bipartite actor–group graph: counts of posts and comments; observed activity does not establish interpersonal relationships or membership.',
               'betweenness':'Directed graph, unweighted distance, NetworkX normalization; descriptive measure, not evidence of influence.',
               '2026':'Post published during 2026-01-01–2026-10-13 (Europe/Warsaw); comments and mentions must have a selected parent post and their own timestamp within the interval.',
               'limitations':'Sample of accessible records, not the full group population; missing interactions in the sample do not establish absent relationships.'}}
    plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150})
    for variant in ['all_sample','community_all','community_2026']:
        p = posts.copy()
        if variant!='all_sample': p=p[p.group_id.isin(COMMUNITY)].copy()
        if variant=='community_2026': p=p[pd.to_datetime(p.timestamp,utc=True).between(START,END)].copy()
        c=comments[comments.post_id.isin(p.post_id)].copy()
        e=events[events.post_id.isin(p.post_id)].copy()
        if variant=='community_2026':
            c=c[pd.to_datetime(c.timestamp,utc=True).between(START,END)].copy()
            e=e[pd.to_datetime(e.timestamp,utc=True).between(START,END)].copy()
        observed=set(); activity=Counter()
        for r in p.to_dict('records'):
            n=node(r['author_id'],r['group_id']); observed.add(n); activity[(n,r['group_id'])]+=1
        for r in c.to_dict('records'):
            gid=post_group[r['post_id']]; n=node(r['author_id'],gid); observed.add(n); activity[(n,gid)]+=1
        e['source_node']=[node(r['source_actor_id'],r['group_id']) for r in e.to_dict('records')]
        e['target_node']=[node(r['target_actor_id'],r['group_id']) for r in e.to_dict('records')]
        e['self_loop'] = e.source_node==e.target_node
        observed.update(e.source_node); observed.update(e.target_node)
        e.to_csv(out/f'{variant}_events.csv',index=False)
        networks={}
        for kind in ['comments','mentions','combined']:
            selected=e if kind=='combined' else e[e.interaction_type.str.contains('mention' if kind=='mentions' else 'comment')]
            g=nx.DiGraph(variant=variant, network=kind)
            g.add_nodes_from((n,{'label':labels[n], 'actor_id':n.split(':')[-1], 'actor_type':actor_info[n.split(':')[-1]]['actor_type'], 'identity_scope':actor_info[n.split(':')[-1]]['identity_scope']}) for n in sorted(observed))
            for r in selected[~selected.self_loop].to_dict('records'):
                u,v=r['source_node'],r['target_node']
                if g.has_edge(u,v): g[u][v]['weight']+=1
                else:g.add_edge(u,v,weight=1)
            assert sum(w['weight'] for _,_,w in g.edges(data=True)) == len(selected[~selected.self_loop])
            weak=sorted(nx.weakly_connected_components(g),key=lambda x:(-len(x),sorted(x)))
            strong=list(nx.strongly_connected_components(g))
            row={'variant':variant,'network':kind,'nodes':len(g),'edges':g.number_of_edges(),
                 'events_raw':len(selected),'events_without_self_loops':int((~selected.self_loop).sum()),
                 'self_loop_events_removed':int(selected.self_loop.sum()),
                 'self_loop_pairs_removed':selected[selected.self_loop].source_node.nunique(),
                 'isolates':len(list(nx.isolates(g))),'active_nodes':sum(g.degree(n)>0 for n in g),
                 'density':nx.density(g),'weak_components':len(weak),'strong_components':len(strong),
                 'largest_weak_component':len(weak[0]) if weak else 0}
            row['top_degree']=[{'pseudonym':labels[n],'degree':g.degree(n),'strength':g.degree(n,weight='weight')} for n in sorted(g,key=lambda n:(-g.degree(n),labels[n]))[:5]]
            row['weak_component_sizes']=[len(comp) for comp in weak]
            summaries.append({k:v for k,v in row.items() if k not in ('top_degree','weak_component_sizes')}); networks[kind]=row
            between=nx.betweenness_centrality(g,weight=None)
            assert all(math.isfinite(x) for x in between.values())
            assert sum(dict(g.in_degree(weight='weight')).values()) == row['events_without_self_loops']
            assert sum(dict(g.out_degree(weight='weight')).values()) == row['events_without_self_loops']
            for n in g:
                metrics.append({'variant':variant,'network':kind,'node_id':n,'pseudonym':labels[n],
                    'in_degree':g.in_degree(n),'out_degree':g.out_degree(n),'in_strength':g.in_degree(n,weight='weight'),
                    'out_strength':g.out_degree(n,weight='weight'),'betweenness_unweighted':between[n]})
            for i, comp in enumerate(weak,1):
                for n in sorted(comp):component_rows.append({'variant':variant,'network':kind,'component':i,'component_size':len(comp),'node_id':n,'pseudonym':labels[n]})
            if kind=='combined':
                nx.write_graphml(g,out/f'{variant}_interactions.graphml')
                pd.DataFrame([{'source':u,'target':v,'weight':a['weight']} for u,v,a in g.edges(data=True)],columns=['source','target','weight']).to_csv(out/f'{variant}_edges.csv',index=False)
                active=g.subgraph([n for n in g if g.degree(n)>0]).copy()
                fig,ax=plt.subplots(figsize=(10,7));pos=nx.spring_layout(active,seed=42,weight='weight',k=1.2)
                nx.draw_networkx(active,pos,ax=ax,labels={n:labels[n] for n in active},node_color=['#d79b5b' if actor_info[n.split(':')[-1]]['actor_type']=='GroupAnonAuthorProfile' else '#a9c6d9' for n in active],node_size=650,font_size=10,arrowsize=14,width=[0.8+0.4*a['weight'] for _,_,a in active.edges(data=True)])
                ax.set_title(f'Observed interactions: {VARIANT_NAMES[variant]}\nActive nodes; {row["isolates"]} isolates omitted from this figure');ax.axis('off');fig.tight_layout();fig.savefig(figs/f'{variant}_network.png');plt.close(fig)
        b=nx.Graph(variant=variant,network='participation')
        for (n,gid),count in activity.items():
            b.add_node(n,bipartite=0,label=labels[n],actor_id=n.split(':')[-1],actor_type=actor_info[n.split(':')[-1]]['actor_type'],identity_scope=actor_info[n.split(':')[-1]]['identity_scope']);b.add_node('group:'+gid,bipartite=1,label='Group '+gid)
            b.add_edge(n,'group:'+gid,weight=count)
        assert sum(d['weight'] for _,_,d in b.edges(data=True))==len(p)+len(c)
        nx.write_graphml(b,out/f'{variant}_participation.graphml')
        for r in data['groups'].to_dict('records'):
            gid=r['group_id']; pp=p[p.group_id==gid]; cc=c[c.post_id.isin(pp.post_id)]
            groups_rows.append({'variant':variant,'group_id':gid,'group_name':r['name'],'posts':len(pp),'comments':len(cc),'interaction_events':int((e.group_id==gid).sum())})
        counts=pd.to_datetime(p.timestamp,utc=True).dt.tz_convert('Europe/Warsaw').dt.strftime('%Y-%m').value_counts().sort_index()
        counts.rename_axis('publication_month').reset_index(name='posts').to_csv(out/f'{variant}_publications.csv',index=False)
        fig,ax=plt.subplots(figsize=(10,4));counts.plot.bar(ax=ax,color='#477a9b');ax.set(xlabel='Publication month (Europe/Warsaw)',ylabel='Number of posts',title=f'Posts by publication time: {VARIANT_NAMES[variant]}');fig.tight_layout();fig.savefig(figs/f'{variant}_publications.png');plt.close(fig)
        summary['variants'][variant]={'posts':len(p),'comments':len(c),'groups_with_posts':p.group_id.nunique(),'networks':networks,'participation':{'nodes':len(b),'edges':b.number_of_edges(),'activity_events':len(p)+len(c)}}
    pd.DataFrame(summaries).to_csv(out/'summary_networks.csv',index=False)
    pd.DataFrame(metrics).to_csv(out/'node_metrics.csv',index=False)
    pd.DataFrame(groups_rows).to_csv(out/'group_counts.csv',index=False)
    pd.DataFrame(component_rows).to_csv(out/'components.csv',index=False)
    comparison=pd.DataFrame([{'variant':VARIANT_NAMES[v],'Posts':s['posts'],'Comments':s['comments'],'Interactions excluding self-loops':s['networks']['combined']['events_without_self_loops']} for v,s in summary['variants'].items()]).set_index('variant')
    fig,ax=plt.subplots(figsize=(9,4));comparison.plot.bar(ax=ax,color=['#477a9b','#82a8a1','#cf9c60']);ax.set(xlabel='',ylabel='Number of records',title='Comparison of three sample variants');ax.tick_params(axis='x',rotation=0);fig.tight_layout();fig.savefig(figs/'variant_comparison.png');plt.close(fig)
    group_counts=pd.DataFrame(groups_rows).query("variant == 'all_sample'").set_index('group_name')[['posts','comments']]
    fig,ax=plt.subplots(figsize=(10,5));group_counts.rename(columns={'posts':'Posts','comments':'Comments'}).plot.barh(ax=ax,color=['#477a9b','#82a8a1']);ax.set(xlabel='Number of records',ylabel='',title='Sample sources: observed posts and comments');fig.tight_layout();fig.savefig(figs/'source_counts.png');plt.close(fig)
    summary['validation']={'unique_post_comment_event_ids':True,'parent_post_joins':True,'known_actors':True,'anonymous_group_scope':True,'interaction_weight_conservation':True,'participation_weight_conservation':True,'finite_metrics':True}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    return summary

if __name__=='__main__':
    result=run_analysis()
    print(json.dumps(result,ensure_ascii=False,indent=2))
