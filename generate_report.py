"""Build a minimalist academic PDF offline; customize report_config.json to reuse it."""
from pathlib import Path
import json, csv
from xml.sax.saxutils import escape
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import networkx as nx
from svglib.svglib import svg2rlg
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'SNA_Project_Step_by_Step.pdf'
PAPER_FIGS=ROOT/'figures'/'paper'
FONT_DIR=Path(matplotlib.get_data_path())/'fonts'/'ttf'
for name,file in [('PaperSerif','DejaVuSerif.ttf'),('PaperSerifBold','DejaVuSerif-Bold.ttf'),('PaperSerifItalic','DejaVuSerif-Italic.ttf'),('PaperSans','DejaVuSans.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(FONT_DIR/file)))
pdfmetrics.registerFontFamily('PaperSerif',normal='PaperSerif',bold='PaperSerifBold',italic='PaperSerifItalic',boldItalic='PaperSerifBold')
styles=getSampleStyleSheet()
style_defs={
 'BodyReport':dict(fontName='PaperSerif',fontSize=10,leading=14.5,spaceAfter=7,alignment=TA_JUSTIFY),
 'TitleReport':dict(fontName='PaperSerifBold',fontSize=19,leading=24,spaceAfter=9,alignment=TA_CENTER),
 'SubtitleReport':dict(fontName='PaperSerifItalic',fontSize=9.6,leading=14,spaceAfter=11,alignment=TA_CENTER),
 'AuthorReport':dict(fontName='PaperSerif',fontSize=11,leading=15,spaceAfter=4,alignment=TA_CENTER),
 'MetaReport':dict(fontName='PaperSerif',fontSize=8.3,leading=11.8,spaceAfter=2,alignment=TA_CENTER),
 'HeadReport':dict(fontName='PaperSerifBold',fontSize=11.5,leading=16,spaceBefore=13,spaceAfter=8,keepWithNext=True),
 'AbstractHead':dict(fontName='PaperSerifBold',fontSize=10,leading=14,spaceAfter=6,alignment=TA_CENTER,keepWithNext=True),
 'AbstractBody':dict(fontName='PaperSerif',fontSize=9,leading=12.8,spaceAfter=9,leftIndent=12,rightIndent=12,alignment=TA_JUSTIFY),
 'SmallReport':dict(fontName='PaperSerif',fontSize=8,leading=11.1,spaceAfter=7),
 'CaptionReport':dict(fontName='PaperSerif',fontSize=8,leading=11.5,spaceAfter=13),
 'TableCell':dict(fontName='PaperSerif',fontSize=7.9,leading=10.7),
 'TableHeader':dict(fontName='PaperSerifBold',fontSize=7.9,leading=10.7),
 'CodeReport':dict(fontName='Courier',fontSize=8,leading=12,spaceBefore=3,spaceAfter=9,leftIndent=9,borderPadding=7,borderColor=colors.black,borderWidth=.35),
 'ReferenceReport':dict(fontName='PaperSerif',fontSize=7.5,leading=10.5,spaceAfter=4,splitLongWords=True)
}
for name,kw in style_defs.items():styles.add(ParagraphStyle(name=name,textColor=colors.black,**kw))
story=[]
figure_number=0
table_number=0

def para(s,style='BodyReport'):story.append(Paragraph(s,styles[style]))
def page(title):para(title,'HeadReport')
def svg_flow(path,width,maxheight):
    d=svg2rlg(str(path))
    scale=min(width/d.width,maxheight/d.height)
    d.scale(scale,scale);d.width*=scale;d.height*=scale;d.hAlign='CENTER'
    return d

def figure(name,caption,width=475,maxheight=310):
    global figure_number
    figure_number+=1
    svg=PAPER_FIGS/(Path(name).stem+'.svg')
    d=svg_flow(svg,width,min(maxheight,240))
    cap=Paragraph(f'<b>Figure {figure_number}.</b> '+caption,styles['CaptionReport'])
    items=[Spacer(1,5),d,Spacer(1,7),cap]
    if story and isinstance(story[-1],Paragraph) and story[-1].style.name=='HeadReport':
        items.insert(0,story.pop())
    story.append(KeepTogether(items))

def table(rows,widths):
    global table_number
    table_number+=1
    cells=[[Paragraph(escape(str(v)),styles['TableHeader' if i==0 else 'TableCell']) for v in row] for i,row in enumerate(rows)]
    t=Table(cells,colWidths=widths,hAlign='CENTER',repeatRows=1)
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEABOVE',(0,0),(-1,0),.65,colors.black),('LINEBELOW',(0,0),(-1,0),.4,colors.black),('LINEBELOW',(0,-1),(-1,-1),.65,colors.black)]))
    story.append(t);story.append(Spacer(1,10))

def read(name):
    with (ROOT/'data'/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))

def footer(c,doc):
    c.setFillColor(colors.black);c.setFont('PaperSerif',7.5)
    if doc.page>1:
        c.drawString(54,A4[1]-28,'PUBLIC FACEBOOK SAMPLE - EXPLORATORY SNA')
        author=json.loads((ROOT/'report_config.json').read_text(encoding='utf-8'))['author']
        c.drawRightString(A4[0]-54,A4[1]-28,author)
    c.drawCentredString(A4[0]/2,24,str(doc.page))

def workflow():
    cells=[]
    for icon,label in [('database','Collect evidence'),('circle-check','Validate records'),('network','Construct graphs'),('file-text','Report results')]:
        d=svg_flow(ROOT/'assets/icons'/f'{icon}.svg',13,13)
        cells.append([d,Spacer(1,4),Paragraph(label,styles['SmallReport'])])
    t=Table([cells],colWidths=[118.75]*4)
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('ALIGN',(0,0),(-1,-1),'CENTER'),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEABOVE',(0,0),(-1,0),.35,colors.black),('LINEBELOW',(0,0),(-1,0),.35,colors.black)]))
    story.append(t);story.append(Spacer(1,7))

def scrapling_identity():
    im=Image(str(ROOT/'assets/scrapling.png'),width=30,height=30)
    label=Paragraph('<b>Scrapling</b><br/>Python scraping framework used for the public collection.',styles['SmallReport'])
    t=Table([[im,label]],colWidths=[43,432]);t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),7)]));story.append(t)

def make_paper_figures(summary):
    PAPER_FIGS.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Serif','font.size':8,'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'black','text.color':'black','xtick.color':'black','ytick.color':'black','svg.fonttype':'path'})
    def save(fig,name):
        fig.savefig(PAPER_FIGS/f'{name}.svg',bbox_inches='tight',facecolor='white');plt.close(fig)
    counts=pd.read_csv(ROOT/'results/group_counts.csv').query("variant == 'all_sample'")
    fig,ax=plt.subplots(figsize=(7,2.8));y=list(range(len(counts)))
    ax.barh([v+.17 for v in y],counts.posts,height=.32,color='white',edgecolor='black',label='Posts',linewidth=.6)
    ax.barh([v-.17 for v in y],counts.comments,height=.32,color='0.6',edgecolor='black',hatch='///',label='Comments',linewidth=.6)
    ax.set_yticks(y,counts.group_name);ax.set_xlabel('Recovered records');ax.legend(frameon=False,ncol=2,loc='lower right');fig.tight_layout();save(fig,'source_counts')
    fig,ax=plt.subplots(figsize=(6.8,2.55));keys=['all_sample','community_all','community_2026'];x=list(range(3))
    for delta,field,label,col,hatch in [(-.23,'posts','Posts','white',None),(0,'comments','Comments','0.65','///'),(.23,'events','Non-loop events','0.15',None)]:
        vals=[summary['variants'][k][field] if field!='events' else summary['variants'][k]['networks']['combined']['events_without_self_loops'] for k in keys]
        ax.bar([v+delta for v in x],vals,width=.22,color=col,edgecolor='black',hatch=hatch,label=label,linewidth=.6)
    ax.set_xticks(x,['Full sample','Two groups / all years','Two groups / 2026']);ax.set_ylabel('Recovered records');ax.legend(frameon=False,ncol=3,fontsize=7,loc='upper right');fig.tight_layout();save(fig,'variant_comparison')
    for variant in ['community_2026','community_all']:
        g=nx.read_graphml(ROOT/'results'/f'{variant}_interactions.graphml');g=g.subgraph(sorted(n for n in g if g.degree(n)>0)).copy()
        components=sorted(nx.weakly_connected_components(g),key=lambda c:(-len(c),sorted(c)))
        pos={}
        total=sum(len(c)**.5 for c in components)
        cursor=-1.5
        for component in components:
            width=3.0*(len(component)**.5)/total
            center=cursor+width/2
            sub=g.subgraph(sorted(component)).copy()
            local=nx.circular_layout(sub)
            for n,xy in local.items():pos[n]=(center+xy[0]*width*.37,xy[1]*.65)
            cursor+=width
        fig,ax=plt.subplots(figsize=(6.8,2.6))
        nx.draw_networkx_edges(g,pos,ax=ax,edge_color='black',width=.65,arrowsize=11,node_size=700,connectionstyle='arc3,rad=0.035')
        for anonymous,shape,fill in [(False,'o','white'),(True,'s','black')]:
            nodes=[n for n,d in g.nodes(data=True) if (d['actor_type']=='GroupAnonAuthorProfile')==anonymous]
            nx.draw_networkx_nodes(g,pos,ax=ax,nodelist=nodes,node_shape=shape,node_color=fill,edgecolors='black',linewidths=.7,node_size=700)
            nx.draw_networkx_labels(g,pos,ax=ax,labels={n:g.nodes[n]['label'] for n in nodes},font_family='DejaVu Serif',font_size=10,font_color='white' if anonymous else 'black')
        ax.margins(.12);ax.axis('off');fig.tight_layout();save(fig,variant+'_network')
    months=pd.read_csv(ROOT/'results/community_2026_publications.csv')
    fig,ax=plt.subplots(figsize=(6.8,2.3));ax.bar(months.publication_month,months.posts,color='white',edgecolor='black',linewidth=.7,width=.5)
    ax.set_xlabel('Publication month (Europe/Warsaw)');ax.set_ylabel('Recovered posts');fig.tight_layout();save(fig,'community_2026_publications')

def references():
    story.append(PageBreak())
    para('References and links','HeadReport')
    para('Project evidence: frozen CSV tables in data/, DATA_DICTIONARY.md, results/summary.json, results/validation.json and docs/COLLECTION_RELIABILITY.md. The URLs below are provided together for source attribution and further reading. Retrieved 13 October 2026.','SmallReport')
    links=[
      ('FNSA - project repository, code, data and report','https://github.com/Jaqwilk/FNSA'),
      ('Scrapling - original repository and logo source','https://github.com/D4Vinci/Scrapling'),
      ('Scrapling - Dynamic fetching documentation','https://scrapling.readthedocs.io/en/latest/fetching/dynamic.html'),
      ('Scrapling - Stealthy fetching documentation','https://scrapling.readthedocs.io/en/latest/fetching/stealthy.html'),
      ('Scrapling - Advanced spider documentation','https://scrapling.readthedocs.io/en/latest/spiders/advanced.html'),
      ('NetworkX - graph analysis documentation','https://networkx.org/documentation/stable/'),
      ('Kozminski University - official website','https://www.kozminski.edu.pl/en'),
      ('Kozminski University - official visual identity source for the flat logo','https://www.kozminski.edu.pl/sites/leon/files/files/logobook_mini_2018.pdf'),
      ('Lucide - original vector icons and license','https://lucide.dev/license'),
      ('Lucide - icon source repository','https://github.com/lucide-icons/lucide'),
      ('Leskovec et al. (2010), Kronecker Graphs, JMLR - layout reference','https://www.jmlr.org/papers/volume11/leskovec10a/leskovec10a.pdf'),
      ('Leskovec et al. (2008), Statistical Properties of Community Structure, WWW - layout reference','https://cs.stanford.edu/~jure/pubs/ncp-www08.pdf'),
    ]
    links.extend((r['name']+' - observed Facebook source',r['url']) for r in read('groups.csv'))
    entries=[]
    for i,(title,url) in enumerate(links,1):
        safe=escape(url,{'"':'&quot;'})
        entries.append(Paragraph(f'[{i}] {escape(title)}<br/><link href="{safe}" color="black">{safe}</link>',styles['ReferenceReport']))
    midpoint=(len(entries)+1)//2
    rows=[[entries[i],entries[i+midpoint] if i+midpoint<len(entries) else ''] for i in range(midpoint)]
    t=Table(rows,colWidths=[239,239],hAlign='CENTER')
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    story.append(t);story.append(Spacer(1,7))
    para('The research-paper examples informed typography and layout only; their findings are not used as evidence for this sample. The university logo is reproduced from its official flat-logo artwork; the Scrapling logo is reproduced from the original repository. The four workflow icons are Lucide vectors, not emoji. Asset sources and the icon license are preserved in assets/SOURCES.md and assets/icons/LICENSE.','SmallReport')

def main():
    global figure_number, table_number
    figure_number=0;table_number=0;story.clear()
    config=json.loads((ROOT/'report_config.json').read_text(encoding='utf-8'))
    summary=json.loads((ROOT/'results/summary.json').read_text(encoding='utf-8'))
    variants=summary['variants']; mainv=variants['community_2026'];net=mainv['networks']['combined']
    make_paper_figures(summary)
    university=svg_flow(ROOT/'assets/kozminski.svg',84,64)
    story.append(university);story.append(Spacer(1,12))
    para(escape(config['title']),'TitleReport')
    para('A simple guide to the data, method and results','SubtitleReport')
    para(escape(config['author']),'AuthorReport')
    para(escape(config['institution'])+' | '+escape(config['date']),'MetaReport')
    para(escape(config['document_type']),'MetaReport')
    story.append(Spacer(1,13))
    para('Abstract','AbstractHead')
    para('We used Scrapling to collect a small public Facebook sample and turn observed comments and tags into a network. The project includes the data, Python scripts, a notebook, figures and graph files. The main 2026 network has 27 profiles and 9 directed connections. It describes the records we could see, not all activity in the groups.','AbstractBody')
    workflow()

    page('1. What we collected')
    para('We collected the following sample on 13 October 2026 from public Facebook group pages. It includes posts from different years; it is not a complete history of the groups:')
    table([['Groups','Posts','Comments','Profiles','Tags','Profile-group pairs'],['7','63','25','73','5','71']],[55,55,70,70,70,155])
    para('Each post has an exact post ID, author ID, group ID and publication time. IDs connect records across the tables. The sample contains 66 served User profiles and 7 group-scoped anonymous profiles. A profile does not establish a verified real-world identity.')
    para('The main analysis uses two groups: Warsaw Expat Business Community (WEBC) and Expats in Warsaw, Poland. We ask: <b>who commented on whose posts, and who tagged whom, in the records we collected?</b> Both the parent post and its comment/tag must be dated 1 January through 13 October 2026 in Europe/Warsaw.')

    page('2. How we used Scrapling')
    scrapling_identity()
    para('<b>Step 1 - Open public content.</b> Scrapling loaded group previews and direct post links without logging in. Its browser fetcher captured the pages and the structured responses those pages requested.')
    para('<b>Step 2 - Extract records.</b> The Python tools read IDs, authors, groups, publication times, comments and explicit tags from the returned data. They saved the results as CSV tables.')
    para('<b>Step 3 - Check the data.</b> We removed duplicate records and checked IDs, links between tables and timestamps. Missing information was left blank. We did not invent users, comments or connections.')
    para('<b>Why collecting Facebook data was difficult.</b> The login prompt returned during scrolling. Group previews exposed different posts across visits, and comment expansion did not reveal everything. More scrolling and alternative tested browsers did not unlock complete history.')
    table([['Data type','What our tests supported'],['Core metadata','Post, author and group IDs; exact publication times from tested direct post links; observed posting/commenting in groups.'],['Public interactions','Comment IDs, authors and times, plus explicit tags when served. Repeated tests recovered the same selected comments and tags; total coverage was incomplete.'],['Optional context','Served text and reaction/share/comment totals where available. These are snippets or snapshots, not complete user-level networks.'],['Not established','Complete member/friend lists, individual reactor/sharer lists, reliable usernames or verified nested replies.']],[105,370])
    para('These are the usable data types verified in our logged-out tests, not every capability Facebook might offer. <b>Repeatable extraction is not complete coverage:</b> stable fields on tested records do not guarantee the same records on every visit or in every group. We base our conclusions only on the records actually collected.')

    page('3. How the network works')
    para('<b>Node = a profile.</b> A### labels make the drawing readable. Their mapping is stored in results/node_mapping.csv. They hide names in the drawing but do not anonymize the dataset. Anonymous profiles stay tied to their group; we do not infer who they are.')
    para('<b>Comment arrow:</b> comment author to post author. This is the chosen analysis rule; it does not prove that the comment directly addresses that person.')
    para('<b>Tag arrow:</b> content author to the explicitly tagged profile. A written name without an ID does not create an edge.')
    para('<b>Weight = number of observed events.</b> Repeated events between the same two profiles increase the weight. Self-comments stay in the source data but are removed from the analysis graph.')
    para('<b>Isolate = a profile without a recovered connection.</b> Isolates remain in the totals and graph files. The drawing shows only profiles with connections.')
    para('A separate profile-group graph records observed posting and commenting. It is not a membership or friendship list.')

    story.append(PageBreak())
    page('4. What we found in the collected data')
    rows=[['Sample','Profiles','Connections','Isolates']]
    for k,label in [('all_sample','All 7 groups / all years'),('community_all','Two community groups / all years'),('community_2026','Two community groups / 2026')]:
        n=variants[k]['networks']['combined'];rows.append([label,n['nodes'],n['edges'],n['isolates']])
    table(rows,[235,80,80,80])
    para(f'For the two groups in 2026, we collected <b>{mainv["posts"]} posts, {mainv["comments"]} comments and 3 explicit tags</b>. We found {net["nodes"]} profiles and {net["edges"]} arrows between profiles. An arrow means a recorded comment-to-post-author link or a tag; it is not a friendship.')
    para('<b>Most recorded commenting was around one post.</b> Five of the six comments were on a post by the anonymous profile A044, from five different profiles. A044 is the most connected profile in this sample because of that thread; we do not know the person behind it.')
    para('<b>We found two separate sets of connected profiles: 7 and 3.</b> No recorded arrow joins the sets. This describes the captured interactions, not two proven communities.')
    para('<b>Most collected profiles had no recorded connection: 17 out of 27.</b> Only 10 appear in the drawing. The sample captures many publishing profiles but few visible interactions; this does not mean the other 17 were inactive on Facebook.')
    para('<b>Tags add a different kind of link.</b> Three of the nine recorded events were explicit tags. They show which profiles were referenced, including profiles with no authored activity in our sample; they do not establish a conversation or group membership.')
    figure('community_2026_network.png','Main 2026 network. Open circles: served User profiles. Solid squares: group-scoped anonymous profiles. The 17 isolates remain in the graph files and totals.',maxheight=145)
    para('The larger samples in the table include other groups or older posts. Their larger totals reflect added records, not a measured change over time.')

    page('5. How far these conclusions go')
    para('The findings above describe our collected records only. Facebook exposed a limited, uneven sample, and our sources were not randomly selected. Missing arrows do not prove missing relationships. We cannot turn this sample into claims about complete membership, friendships or influence.')
    para('The next study should use the same groups and time window, record what was attempted and recovered, and collect more comparable comments and verified replies. Engagement totals must remain separate snapshots, not added user-level connections.')

    page('6. How to run the project')
    para('<b>Step 1.</b> Open the project folder and install the packages using Python 3.13, the tested version:')
    para('python3 -m venv .venv<br/>source .venv/bin/activate<br/>python -m pip install -r requirements.txt','CodeReport')
    para('<b>Step 2.</b> Rebuild the analysis, check the outputs and regenerate this report:')
    para('python analysis.py<br/>python validate_project.py<br/>python generate_report.py','CodeReport')
    para('<b>Step 3.</b> Open analysis.ipynb, choose the same Python environment and run all cells for the explained walkthrough. The delivered notebook already contains successful outputs. All 29 project validation checks passed.')
    para('The frozen inputs are in data/. The metrics and graph files are in results/, and charts are in figures/. README.md explains all files; DATA_DICTIONARY.md explains the fields.')
    para('This workflow runs offline. Optional new scraping is separate: collect_data.py saves fresh captures in collections/ without changing the frozen data. See README.md for its commands and collection limits.')
    references()
    doc=SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=54,leftMargin=54,topMargin=48,bottomMargin=48,title=config['title'],author=config['author'])
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(OUT)

if __name__=='__main__':main()
