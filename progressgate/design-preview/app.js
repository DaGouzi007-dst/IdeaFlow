(() => {
  'use strict';
  const icon = name => `<svg aria-hidden="true"><use href="#i-${name}"></use></svg>`;
  const brandMark = () => `<svg class="idea-logo" viewBox="0 0 104 84" aria-hidden="true" focusable="false"><path class="logo-forest" d="M8 61V37c0-8 4-14 12-17L56 8c9-3 17 0 18 8 1 6-3 9-9 11l-10 3c-10 3-15 9-15 19v17c0 6-4 10-10 10H21C13 76 8 71 8 61Z"/><circle class="logo-blue" cx="57" cy="42" r="8"/><path class="logo-clay" d="M49 64c1-6 6-8 13-10 6-2 9-5 12-11 2-5 5-5 8-1l9 10c4 5 5 9 5 14 0 7-4 10-11 10H60c-8 0-12-4-11-12Z"/></svg>`;
  const ideas = [
    {id:'trace',title:'让每个想法都能回到原文',summary:'记录想法与来源消息的关联，保留产生它时的上下文。',status:'已采纳',when:'今天',tone:'',conversation:'让想法和原文保持联系',excerpt:'如果一个想法来自不止一条消息，我希望回头能看到它们各自的上下文。',decision:'一个想法允许关联多条来源消息。',task:'设计来源消息的展示方式'},
    {id:'import',title:'先验证一种真实的对话格式',summary:'从经过脱敏的样例入手，检查导入结果与消息顺序。',status:'讨论中',when:'昨天',tone:'amber',conversation:'如何开始导入对话',excerpt:'先让一种格式可靠地进入系统，再根据真实样例扩展。',decision:'先选定一种经过验证的导入格式。',task:'准备经过脱敏的对话样例'},
    {id:'block',title:'让阻塞记录留下下一步',summary:'记录遇到的问题、尝试过的方法和下一步计划。',status:'已采纳',when:'周二',tone:'blue',conversation:'如何记录推进中的问题',excerpt:'一个任务卡住时，我想知道已经尝试了什么，以及接下来还能做什么。',decision:'阻塞时保留原因、尝试过程和下一步。',task:'设计阻塞记录的表单'},
    {id:'search',title:'关键词搜索时保留上下文',summary:'找到匹配的消息后，能顺着对话继续阅读。',status:'待整理',when:'周一',tone:'',conversation:'让想法和原文保持联系',excerpt:'找到一条消息之后，还需要看看它前后在讨论什么。',decision:'优先支持打开消息所在的上下文。',task:'设计搜索结果与原文的跳转'}
  ];
  const tasks = [
    {title:'准备经过脱敏的对话样例',status:'已阻塞',note:'等待可用于验证格式的示例。',related:'先验证一种真实的对话格式'},
    {title:'设计来源消息的展示方式',status:'进行中',note:'让想法与原始消息之间可以往返。',related:'让每个想法都能回到原文'},
    {title:'设计阻塞记录的表单',status:'待开始',note:'整理原因、尝试过程与下一步。',related:'让阻塞记录留下下一步'}
  ];
  const conversations = [
    {id:'trace',title:'让想法和原文保持联系',summary:'关于来源、上下文，以及如何找到一段讨论。',date:'今天',messages:6},
    {id:'import',title:'如何开始导入对话',summary:'从一份可验证的对话样例开始，逐步扩展。',date:'昨天',messages:4},
    {id:'block',title:'如何记录推进中的问题',summary:'任务卡住时应该保留哪些信息。',date:'周二',messages:5}
  ];
  const state={filter:'全部',idea:null,search:false,lastFocus:null,theme:'dark',draft:null,selectedText:'',sidebarCollapsed:false,taskSelected:1,taskFilter:'全部'};
  try { state.theme=localStorage.getItem('ideaflow-compact-theme')||'dark'; } catch (_) {}
  if(!['dark','light'].includes(state.theme)) state.theme='dark';
  const $=s=>document.querySelector(s);
  function escapeText(value){return String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  function route(){const [name,id,anchor]=location.hash.slice(1).split('/');return {name:['home','ideas','conversations','conversation','tasks'].includes(name)?name:'home',id:id||'trace',anchor:anchor||''};}
  function go(name,id){location.hash=`#${name}${id?'/'+id:''}`;}
  const sections=[['home','概览','grid'],['conversations','对话','chat'],['ideas','想法','spark'],['tasks','决策与任务','check']];
  function titleArea(kicker,title,description,action=''){return `<div class="page-eyebrow">${kicker}</div><div class="page-title"><div><h1>${title}</h1><p>${description}</p></div>${action}</div>`;}
  function shell(page){
    const active=page.name==='conversation'?'conversations':page.name;
    return `<div class="app"><aside class="work-sidebar" aria-label="工作区侧栏"><div class="sidebar-brand-row"><a href="#home" class="side-logo" aria-label="IdeaFlow 首页"><span class="brand-marker">${brandMark()}</span><span class="sidebar-label brand-word">IdeaFlow</span></a><button class="sidebar-toggle" data-action="toggle-sidebar" aria-label="收起导航" aria-expanded="true" title="收起导航">${icon('left')}</button></div><div class="sidebar-project sidebar-label"><span class="project-block" aria-hidden="true">${brandMark()}</span><span><strong>IdeaFlow</strong><small>示例工作区</small></span></div><nav class="side-nav" aria-label="工作区导航">${sections.map(([id,label,symbol])=>`<a href="#${id}" class="workspace-link ${id===active?'active':''}" aria-label="${label}" ${id===active?'aria-current="page"':''}>${icon(symbol)}<span class="sidebar-label">${label}</span></a>`).join('')}</nav><div class="recent-side sidebar-label"><div class="side-caption">最近对话 <a href="#conversations" aria-label="查看全部对话">${icon('arrow')}</a></div>${conversations.slice(0,2).map(c=>`<a class="recent-link" href="#conversation/${c.id}">${escapeText(c.title)}</a>`).join('')}</div><div class="side-footnote sidebar-label"><span class="side-presence"></span> 界面探索 · 示例内容</div></aside><div class="work-main-shell"><header class="work-header"><div class="header-location"><span>IdeaFlow</span><span class="header-slash">/</span><strong id="header-current">${{home:'概览',ideas:'想法',conversations:'对话',conversation:'对话',tasks:'决策与任务'}[page.name]}</strong></div><div class="header-actions"><button class="search-trigger" data-action="search" aria-label="搜索示例内容">${icon('search')}<span>搜索</span><kbd>Ctrl K</kbd></button><button class="theme-switch" data-action="theme" aria-label="${state.theme==='dark'?'切换到浅色':'切换到深色'}模式">${state.theme==='dark'?'☼ 浅色':'◐ 深色'}</button><span class="demo-label">示例</span></div></header><main class="page-shell"><div id="main-content"></div></main></div></div><div class="scrim" data-action="close-drawer"></div><aside class="drawer" id="drawer" aria-hidden="true"></aside><div id="modal"></div>`;
  }
  function flowArt(){return `<div class="hero-art" aria-hidden="true"><svg viewBox="0 0 430 250" preserveAspectRatio="xMidYMid meet"><defs><linearGradient id="line"><stop stop-color="#a7dcc2" stop-opacity=".12"/><stop offset="1" stop-color="#c9eedb" stop-opacity=".8"/></linearGradient></defs><path d="M16 127 C92 127 98 55 169 55 S263 172 340 139 S405 100 435 100" fill="none" stroke="url(#line)" stroke-width="1"/><path d="M-10 150 C85 150 105 86 169 86 S262 194 344 166 S405 128 446 128" fill="none" stroke="#86bda5" stroke-opacity=".19" stroke-width="1"/><path d="M0 101 C75 100 110 24 169 24 S274 146 344 113 S400 76 440 76" fill="none" stroke="#c0ddce" stroke-opacity=".12" stroke-width="1"/><circle cx="169" cy="55" r="22" fill="#a2ceba" fill-opacity=".07"/><circle cx="169" cy="55" r="4" fill="#c2e2d1"/><circle cx="341" cy="139" r="28" fill="#a2ceba" fill-opacity=".07"/><circle cx="341" cy="139" r="5" fill="#c2e2d1"/><circle cx="84" cy="110" r="3" fill="#a9d1bc"/><circle cx="257" cy="121" r="3.5" fill="#b8d9c8"/><circle cx="257" cy="121" r="11" fill="none" stroke="#a6d6ba" stroke-opacity=".26"/><circle cx="341" cy="139" r="45" fill="none" stroke="#a2ceba" stroke-opacity=".1"/></svg></div>`;}
  function ideaRow(idea,full=false){let statusClass=idea.status==='讨论中'?'pending':'';return `<button class="idea-row" data-action="idea" data-id="${idea.id}"><span class="item-mark ${idea.tone}">${icon('spark')}</span><span><strong>${escapeText(idea.title)}</strong><span class="sub">${escapeText(idea.summary)}</span></span>${full?`<span class="list-actions"><span class="status ${statusClass}">${idea.status}</span><span class="row-date">${idea.when}</span></span>`:`<span class="row-date">${idea.when}</span>`}</button>`;}
  function home(){
    return `<div class="viewport studio-home"><div class="overview-title"><div><p class="overview-eyebrow">WORKSPACE / 示例项目</p><h1>工作区</h1><p>从对话中整理想法，让下一步更清楚。</p></div><a class="open-conversations" href="#conversations">查看所有对话 ${icon('arrow')}</a></div><div class="studio-grid"><div class="studio-primary"><section class="conversation-section"><div class="studio-section-head"><div><span class="section-index">CONVERSATIONS / 对话</span><h2>最近的对话</h2></div><a href="#conversations" class="studio-more">全部对话 ${icon('arrow')}</a></div><div class="conversation-rows">${conversations.map((c,n)=>`<a class="studio-conversation ${n===0?'conversation-current':''}" href="#conversation/${c.id}"><span class="conversation-badge ${n===1?'badge-peach':n===2?'badge-blue':''}">${icon('chat')}</span><span class="conversation-copy"><strong>${escapeText(c.title)}</strong><small>${escapeText(c.summary)}</small></span><span class="conversation-date">${escapeText(c.date)}</span><span class="row-arrow">${icon('arrow')}</span></a>`).join('')}</div></section><section class="overview-thread"><div class="thread-label">一个想法 · 一条线索</div><div class="thread-body"><div><h2>让灵感有来处</h2><p>选中对话中的内容，记录为想法；想回顾时，可以再回到原文。</p><a href="#conversation/trace">试试从对话中记录 ${icon('arrow')}</a></div><div class="thread-example"><span>对话摘录</span><p>“如果一个想法来自不止一条消息……”</p><small>↳ 让每个想法都能回到原文</small></div></div></section></div><aside class="studio-secondary"><section class="studio-ideas"><div class="studio-section-head"><div><span class="section-index">IDEAS / 想法</span><h2>最近整理</h2></div><a href="#ideas" class="studio-more">全部 ${icon('arrow')}</a></div><div class="studio-idea-list">${ideas.slice(0,3).map((i,n)=>`<button class="studio-idea" data-action="idea" data-id="${i.id}"><span class="idea-color idea-color-${n}"></span><span class="studio-idea-copy"><strong>${escapeText(i.title)}</strong><small>${escapeText(i.summary)}</small><span>${escapeText(i.status)} <b>·</b> ${escapeText(i.when)}</span></span>${icon('arrow')}</button>`).join('')}</div></section><section class="studio-tasks"><div class="studio-section-head"><div><span class="section-index">PROGRESS / 进度</span><h2>接下来的事</h2></div><a href="#tasks" class="studio-more">全部 ${icon('arrow')}</a></div><div class="studio-task-list">${tasks.map((t,n)=>`<button class="studio-task" data-action="task" data-index="${n}"><span class="studio-task-dot ${t.status==='已阻塞'?'blocked':t.status==='进行中'?'doing':''}"></span><span><strong>${escapeText(t.title)}</strong><small>${escapeText(t.status)}</small></span>${icon('chevron')}</button>`).join('')}</div></section></aside></div><div class="studio-footer"><span>IDEAFLOW / 工作区探索</span><span>示例内容 · 不代表真实项目进度</span></div></div>`;
  }
  function ideaPage(){let filter=state.filter;let filtered=ideas.filter(i=>filter==='全部'||i.status===filter);return `<div class="viewport content-area">${titleArea('IdeaFlow / Ideas','想法','把零散的思考整理起来，也保留它们最初的样子。',`<button class="button" data-action="about-demo">${icon('plus')} 新建想法</button>`)}<div class="toolbar">${['全部','已采纳','讨论中','待整理'].map(f=>`<button class="tab ${filter===f?'active':''}" data-action="filter" data-value="${f}">${f}</button>`).join('')}<div class="spacer"></div><span class="quiet">${filtered.length} 个想法</span></div><div class="list-heading">最近整理</div><div class="result-list">${filtered.map(i=>ideaRow(i,true)).join('')||'<div class="empty">这个分类下还没有示例想法。</div>'}</div></div>`;}
  function conversationsPage(){return `<div class="viewport content-area">${titleArea('IdeaFlow / Conversations','对话','所有想法都始于某一次交流。',`<button class="button" data-action="about-demo">${icon('plus')} 导入对话</button>`)}<div class="toolbar"><span class="tab active">最近导入</span><div class="spacer"></div><span class="quiet">${conversations.length} 段对话</span></div><div class="list-heading">示例对话</div><div class="result-list">${conversations.map(c=>`<a class="idea-row" href="#conversation/${c.id}"><span class="item-mark blue">${icon('chat')}</span><span><strong>${c.title}</strong><span class="sub">${c.summary}</span></span><span class="row-date">${c.date}　${c.messages} 条消息</span></a>`).join('')}</div></div>`;}
  function conversationPage(id){
    const c=conversations.find(x=>x.id===id)||conversations[0];
    const related=ideas.find(x=>x.id===c.id)||ideas[0];
    const connected=ideas.filter(i=>i.sourceConversation===c.id);
    const actions=`<div class="message-actions"><button data-action="capture-message" class="message-action">${icon('plus')}<span>记录为想法</span></button><button data-action="copy-message" class="message-action">${icon('doc')}<span>复制</span></button></div>`;
    return `<div class="viewport reading-page"><a class="section-action back-link" href="#conversations">← 返回对话列表</a><div class="convo-layout"><article class="reading"><div class="page-eyebrow">CONVERSATION · 对话原文</div><h1 class="reading-title">${c.title}</h1><div class="reading-meta"><span class="badge">示例对话</span><span>·</span><span>最近更新 ${c.date}</span><span>·</span><span>节选内容</span></div><div class="reading-rule"></div><p class="interaction-hint">选中一段文字，或将鼠标移到消息上，可记录为想法。</p><div class="message" id="msg-1" data-message="1"><span class="message-icon">你</span><div class="message-main"><div class="message-head"><strong>用户</strong><span>01 / 对话片段</span></div><div class="message-copy"><p>${related.excerpt}</p><p>有什么办法能让这些信息在后面整理想法和推进任务时，仍然保留彼此之间的联系？</p></div>${actions}</div></div><div class="message" id="msg-2" data-message="2"><span class="message-icon ai">AI</span><div class="message-main"><div class="message-head"><strong>助手</strong><span>02 / 对话片段</span></div><div class="message-copy"><p>可以先把原始内容保留下来，再让整理出的想法指向它的来源。这样既能单独查看想法，也能在需要时回到当时的讨论。</p><div class="quote">${related.decision}</div><p>如果想法进一步形成决定或任务，也可以保留这些关联，方便之后回顾为什么这样做。</p></div>${actions}</div></div></article><aside class="reading-aside"><div class="aside-heading">FROM THIS CONVERSATION / 相关想法</div><button class="source-item" data-action="idea" data-id="${related.id}"><small>关联想法　↗</small><strong>${related.title}</strong><span>${related.summary}</span></button>${connected.map(i=>`<button class="source-item added-source" data-action="idea" data-id="${i.id}"><small>刚刚记录　↗</small><strong>${escapeText(i.title)}</strong><span>${escapeText(i.summary)}</span></button>`).join('')}<p class="path-note">查看想法时仍能回到原文，理解当时的上下文。</p><p class="prototype-hint">演示记录只在当前页面保留。</p></aside></div><div class="selection-pop" id="selection-pop" hidden><button data-action="capture-selection">${icon('plus')} 记录这段为想法</button></div><div class="toast" id="toast" role="status" aria-live="polite"></div></div>`;
  }
  function taskPage(){
    const filters=['全部','进行中','已阻塞','待开始','已完成'];
    const shown=tasks.map((t,n)=>({t,n})).filter(({t})=>state.taskFilter==='全部'||t.status===state.taskFilter);
    return `<div class="task-workspace viewport"><header class="task-heading"><div><div class="task-project-name"><span class="task-project-dot"></span> IdeaFlow <span class="task-project-slash">/</span> 示例工作区</div><h1>决策与任务</h1><p>从讨论到行动，让每一步都有迹可循。</p></div><button class="task-new" data-action="about-demo">${icon('plus')} 新建任务</button></header><div class="task-layout ${state.taskSelected===null?'detail-closed':''}"><section class="task-board" aria-label="任务列表"><div class="task-board-top"><div><h2>任务 <span>${tasks.length}</span></h2><p>在这里查看和推进当前的工作</p></div><span class="task-demo-label">示例内容</span></div><div class="task-filters" aria-label="按状态筛选">${filters.map(f=>`<button data-action="task-filter" data-value="${f}" class="task-filter ${state.taskFilter===f?'active':''}" aria-pressed="${state.taskFilter===f}">${f}</button>`).join('')}</div><div class="task-list-caption"><span>${state.taskFilter==='全部'?'全部任务':state.taskFilter}</span><span>${shown.length} 项</span></div><div class="task-rows">${shown.map(({t,n})=>`<button class="task-row ${state.taskSelected===n?'selected':''}" data-action="select-task" data-index="${n}" aria-pressed="${state.taskSelected===n}"><span class="task-row-copy"><span class="task-row-top"><strong>${escapeText(t.title)}</strong><span class="row-state ${taskTone(t.status)}"><i class="task-dot ${taskTone(t.status)}"></i>${escapeText(t.status)}</span></span><small>${escapeText(t.note)}</small><span class="task-row-meta">${icon('link')} <span>关联想法</span><b>·</b> <span class="related-name">${escapeText(t.related)}</span></span></span><span class="task-row-arrow">${icon('arrow')}</span></button>`).join('')||'<div class="task-empty">这个状态下还没有任务。</div>'}</div><div class="task-list-foot">${icon('link')} <span>选择任务，查看关联的想法和对话。</span></div></section><aside class="task-detail" aria-label="任务详情">${taskDetail()}</aside></div><div class="task-bottom-note">示例数据 · 状态更改仅在当前页面保留</div></div>`;
  }
  function taskTone(status){return ({'已阻塞':'clay','进行中':'blue','待开始':'sand','已完成':'sage'})[status]||'sand';}
  function taskDetail(){
    if(state.taskSelected===null)return '';
    const t=tasks[state.taskSelected];if(!t)return '';
    const idea=ideas.find(i=>i.title===t.related);
    const convo=conversations.find(c=>c.id===idea?.id);
    const nextSteps=['收集并确认可用于验证的脱敏样例。','整理展示方式，并与来源追溯部分对齐。','梳理阻塞原因、尝试过程和下一步的填写方式。'];
    const next=t.status==='已完成'?'已完成，可以回顾相关讨论。':nextSteps[state.taskSelected];
    return `<div class="detail-top"><span><i class="task-dot ${taskTone(t.status)}"></i> 任务详情</span><button class="detail-close" data-action="close-task-detail" aria-label="关闭任务详情">${icon('close')}</button></div><div class="detail-scroll"><h2>${escapeText(t.title)}</h2><p class="detail-intro">${escapeText(t.note)}</p><div class="task-status-line"><label for="task-status">状态</label><div class="task-select-wrap ${taskTone(t.status)}"><select id="task-status" aria-label="更改示例任务状态">${['待开始','进行中','已阻塞','已完成'].map(status=>`<option ${t.status===status?'selected':''}>${status}</option>`).join('')}</select></div></div><div class="detail-divider"></div><div class="detail-section-title">下一步</div><div class="next-step ${taskTone(t.status)}"><span class="next-step-marker">${icon('arrow')}</span><p>${escapeText(next)}</p></div><details class="detail-origin"><summary><span>${icon('link')} 关联想法与来源</span><span class="origin-summary-right">查看 ${icon('chevron')}</span></summary><div class="origin-card"><div class="origin-card-label">${icon('spark')} 关联想法</div><button data-action="idea" data-id="${escapeText(idea?.id||'trace')}">${escapeText(t.related)} ${icon('arrow')}</button><p>${escapeText(idea?.summary||'')}</p></div>${idea&&convo?`<a class="source-line" href="#conversation/${convo.id}/1"><span>${icon('chat')}<span><small>来源对话</small><strong>${escapeText(convo.title)}</strong></span></span>${icon('arrow')}</a>`:''}</details><p class="detail-hint">示例任务 · 内容仅用于展示</p></div>`;
  }
  function updateTaskSelection(n){
    const previous=state.taskSelected;
    state.taskSelected=n;
    const layout=$('.task-layout');if(!layout)return;
    const detail=layout.querySelector('.task-detail');
    clearTimeout(updateTaskSelection.clearTimer);
    if(n===null){
      if(detail.contains(document.activeElement))layout.querySelector(`[data-action="select-task"][data-index="${previous}"]`)?.focus({preventScroll:true});
      detail.setAttribute('aria-hidden','true');detail.inert=true;
      layout.classList.add('detail-closed');
      updateTaskSelection.clearTimer=setTimeout(()=>{if(state.taskSelected===null)detail.innerHTML='';},480);
    }else{
      detail.innerHTML=taskDetail();detail.removeAttribute('aria-hidden');detail.inert=false;
      layout.classList.remove('detail-closed');
      const content=detail.querySelector('.detail-scroll');if(content)content.classList.add('detail-content-arriving');
    }
    layout.querySelectorAll('.task-row').forEach(row=>{const selected=Number(row.dataset.index)===n;row.classList.toggle('selected',selected);row.setAttribute('aria-pressed',String(selected));});
  }
  function refreshTaskPage(){const area=$('#main-content');if(area&&route().name==='tasks')area.innerHTML=taskPage();}
  function render(){
    const p=route(), active=p.name==='conversation'?'conversations':p.name;
    document.documentElement.dataset.theme=state.theme;
    if(!$('#main-content')) $('#app').innerHTML=shell(p);
    document.body.classList.remove('show-drawer');
    const d=$('#drawer'); if(d.contains(document.activeElement)){const main=$('#main-content');main.setAttribute('tabindex','-1');main.focus({preventScroll:true});} d.setAttribute('aria-hidden','true');
    if(state.search){state.search=false; $('#modal').innerHTML='';}
    $('#header-current').textContent=({home:'概览',ideas:'想法',conversations:'对话',conversation:'对话',tasks:'决策与任务'})[p.name];
    document.querySelectorAll('.workspace-link').forEach(link=>{
      const current=link.getAttribute('href')===`#${active}`;
      link.classList.toggle('active',current);
      if(current) link.setAttribute('aria-current','page'); else link.removeAttribute('aria-current');
    });
    $('#main-content').innerHTML=({home,ideas:ideaPage,conversations:conversationsPage,conversation:()=>conversationPage(p.id),tasks:taskPage})[p.name]();
    document.title=`${{home:'概览',ideas:'想法',conversations:'对话',conversation:'对话原文',tasks:'决策与任务'}[p.name]} · IdeaFlow`;
    window.scrollTo({top:0,behavior:'instant'});
    if(p.name==='conversation'&&/^[12]$/.test(p.anchor)) requestAnimationFrame(()=>{
      const message=$(`#msg-${p.anchor}`); if(message){message.scrollIntoView({block:'center',behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});message.classList.add('source-highlight');setTimeout(()=>message.classList.remove('source-highlight'),2200);}
    });
  }
  function drawer(inner,label){state.lastFocus=document.activeElement;const d=$('#drawer');d.innerHTML=`<div class="drawer-head"><span>${label}</span><button class="icon-btn" data-action="close-drawer" aria-label="关闭详情">${icon('close')}</button></div><div class="drawer-content">${inner}</div>`;d.setAttribute('role','dialog');d.setAttribute('aria-modal','true');d.setAttribute('aria-label',label);d.setAttribute('aria-hidden','false');document.body.classList.add('show-drawer');d.querySelector('button').focus({preventScroll:true});}
  function showIdea(id){
    const i=ideas.find(x=>x.id===id);if(!i)return;state.idea=i.id;
    const source=i.sourceConversation|| (i.id==='search'?'trace':i.id);
    const anchor=i.sourceMessage||'1';
    const secondary=i.isDraft?'<div class="detail-block"><div class="detail-head">整理状态</div><div class="detail-content">待整理 · 这条记录仅在本次演示中保留。</div></div>':`<div class="detail-block"><div class="detail-head">相关决策</div><div class="detail-content">${escapeText(i.decision)}</div></div><div class="detail-block"><div class="detail-head">关联任务</div><div class="detail-content">${escapeText(i.task)}<br><a class="detail-link" href="#tasks">查看任务 ${icon('arrow')}</a></div></div>`;
    drawer(`<span class="badge">想法 · ${escapeText(i.status)}</span><h2>${escapeText(i.title)}</h2><p class="drawer-desc">${escapeText(i.summary)}</p><div class="detail-block"><div class="detail-head">来源片段 <span>来自示例对话</span></div><div class="detail-content source-excerpt">“${escapeText(i.excerpt)}”<br><a class="detail-link" href="#conversation/${source}/${anchor}">回到这条消息 ${icon('arrow')}</a></div></div>${secondary}`,'想法详情');
  }
  function showCapture(text, message){
    const c=conversations.find(x=>x.id===route().id)||conversations[0];
    state.draft={excerpt:text,sourceConversation:c.id,sourceMessage:message,conversation:c.title};
    $('#selection-pop')?.setAttribute('hidden','');
    window.getSelection()?.removeAllRanges();
    drawer(`<span class="badge">从对话中整理</span><h2>记录一个想法</h2><p class="drawer-desc">给这段内容起个名字，之后可以随时回到来源。</p><form id="capture-form"><label class="form-label" for="idea-title">想法标题</label><input id="idea-title" class="form-input" name="title" placeholder="例如：保留想法的来源" maxlength="80" required><label class="form-label" for="idea-summary">说明 <span>选填</span></label><textarea id="idea-summary" class="form-input form-textarea" name="summary" placeholder="补充一点你的理解"></textarea><div class="detail-block"><div class="detail-head">来源片段 <span>${escapeText(c.title)}</span></div><div class="detail-content source-excerpt">“${escapeText(text)}”</div></div><button class="save-idea" type="submit">保存到想法 ${icon('arrow')}</button><p class="prototype-hint">演示记录只在当前页面保留，刷新后会消失。</p></form>`,'记录想法');
    $('#idea-title').focus({preventScroll:true});
  }
  function toast(message){const t=$('#toast');if(!t)return;t.textContent=message;t.classList.add('visible');clearTimeout(toast.timer);toast.timer=setTimeout(()=>t.classList.remove('visible'),1800);}
  function showTask(n){let t=tasks[n];if(!t)return;drawer(`<span class="badge">任务 · ${t.status}</span><h2>${t.title}</h2><p class="drawer-desc">${t.note}</p><div class="detail-block"><div class="detail-head">相关想法</div><div class="detail-content">${t.related}</div></div><div class="detail-block"><div class="detail-head">下一步</div><div class="detail-content">${t.status==='已阻塞'?'收集并确认可使用的脱敏样例。':'继续细化并与相关模块对齐。'}</div></div>`,'任务详情');}
  function closeDrawer(){document.body.classList.remove('show-drawer');let d=$('#drawer');d.setAttribute('aria-hidden','true');if(state.lastFocus&&document.contains(state.lastFocus))state.lastFocus.focus({preventScroll:true});}
  function searchResults(value){let q=value.trim().toLowerCase();let matches=ideas.filter(i=>!q||(i.title+i.summary+i.excerpt).toLowerCase().includes(q));return matches.length?matches.map(i=>`<button class="search-result" data-action="search-idea" data-id="${i.id}">${icon('spark')}<span><strong>${escapeText(i.title)}</strong><small>想法 · ${escapeText(i.summary)}</small></span></button>`).join(''):'<div class="empty">没有找到相关示例内容。</div>';}
  function openSearch(){state.lastFocus=document.activeElement;state.search=true;$('#modal').innerHTML=`<div class="search-overlay" data-action="search-backdrop"><div class="search-modal" role="dialog" aria-modal="true" aria-label="搜索示例内容"><div class="search-input-wrap">${icon('search')}<input id="search-input" placeholder="搜索示例想法…" aria-label="搜索示例想法"><kbd>ESC</kbd></div><div class="search-body" id="search-results">${searchResults('')}</div></div></div>`;$('#search-input').focus();}
  function closeSearch(){
    state.search=false;
    const overlay=$('#modal .search-overlay');
    if(overlay){overlay.classList.add('is-closing'); setTimeout(()=>overlay.remove(),160);}
    if(state.lastFocus&&document.contains(state.lastFocus))state.lastFocus.focus({preventScroll:true});
  }
  document.addEventListener('click',e=>{
    const link=e.target.closest('a[href^="#conversation/"]');
    if(link&&link.getAttribute('href')===location.hash){
      e.preventDefault();closeDrawer();const p=route();const message=$(`#msg-${p.anchor}`);
      if(message){message.scrollIntoView({block:'center',behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});message.classList.add('source-highlight');setTimeout(()=>message.classList.remove('source-highlight'),2200);}return;
    }
    let button=e.target.closest('[data-action]');if(!button)return;let action=button.dataset.action;if(action==='toggle-sidebar'){state.sidebarCollapsed=!state.sidebarCollapsed;$('.app').classList.toggle('sidebar-collapsed',state.sidebarCollapsed);button.setAttribute('aria-expanded',String(!state.sidebarCollapsed));button.setAttribute('aria-label',state.sidebarCollapsed?'展开导航':'收起导航');button.title=state.sidebarCollapsed?'展开导航':'收起导航';}else if(action==='theme'){state.theme=state.theme==='dark'?'light':'dark';try{localStorage.setItem('ideaflow-compact-theme',state.theme)}catch(_){} document.documentElement.dataset.theme=state.theme;button.setAttribute('aria-label',state.theme==='dark'?'切换到浅色模式':'切换到深色模式');button.textContent=state.theme==='dark'?'☼ 浅色':'◐ 深色';}else if(action==='capture-message'){const message=button.closest('.message');showCapture(message.querySelector('.message-copy').innerText.trim(),message.dataset.message)}else if(action==='capture-selection'){showCapture(state.selectedText,state.selectedMessage)}else if(action==='copy-message'){const message=button.closest('.message').querySelector('.message-copy').innerText.trim();if(navigator.clipboard?.writeText)navigator.clipboard.writeText(message).then(()=>toast('已复制')).catch(()=>toast('复制失败，请选中文字后复制'));else toast('请选中文字后复制')}else if(action==='idea')showIdea(button.dataset.id);else if(action==='task')showTask(Number(button.dataset.index));else if(action==='select-task'){updateTaskSelection(Number(button.dataset.index));}else if(action==='close-task-detail'){updateTaskSelection(null);}else if(action==='task-filter'){state.taskFilter=button.dataset.value;if(state.taskFilter!=='全部'&&(state.taskSelected===null||tasks[state.taskSelected].status!==state.taskFilter)){const first=tasks.findIndex(t=>t.status===state.taskFilter);state.taskSelected=first<0?null:first;}refreshTaskPage();document.querySelector(`[data-action="task-filter"][data-value="${state.taskFilter}"]`)?.focus({preventScroll:true});}else if(action==='close-drawer')closeDrawer();else if(action==='filter'){state.filter=button.dataset.value;$('#main-content').innerHTML=ideaPage();document.querySelector(`.tab[data-value="${state.filter}"]`)?.focus({preventScroll:true})}else if(action==='search')openSearch();else if(action==='search-backdrop'&&e.target===button)closeSearch();else if(action==='search-idea'){let id=button.dataset.id;closeSearch();showIdea(id)}else if(action==='about-demo'){drawer('<span class="badge">设计概念</span><h2>这里是交互原型</h2><p class="drawer-desc">此版本用于体验页面、层次和操作流程，内容均为示例。可以在示例对话中体验记录想法；演示记录只在本次页面停留期间保留。其他创建和保存功能仍需开发。</p>','关于此原型')}});
  document.addEventListener('submit',e=>{
    if(e.target.id!=='capture-form')return;
    e.preventDefault();const form=e.target;const title=form.elements.title.value.trim();if(!title)return;
    const draft=state.draft;if(!draft)return;
    const id=`demo-${Date.now()}`;ideas.unshift({id,title,summary:form.elements.summary.value.trim()||'从对话中记录的想法',status:'待整理',when:'刚刚',tone:'blue',conversation:draft.conversation,excerpt:draft.excerpt,sourceConversation:draft.sourceConversation,sourceMessage:draft.sourceMessage,isDraft:true});
    state.draft=null;state.filter='全部';closeDrawer();
    const aside=$('.reading-aside');if(aside){const b=document.createElement('button');b.className='source-item added-source';b.dataset.action='idea';b.dataset.id=id;b.innerHTML=`<small>刚刚记录　↗</small><strong>${escapeText(title)}</strong><span>从对话中记录的想法</span>`;aside.insertBefore(b,aside.querySelector('.path-note'));}
    toast('已记录到想法（演示）');
  });
  document.addEventListener('mouseup',e=>{
    if(e.target.closest('.selection-pop, .drawer'))return;
    const pop=$('#selection-pop');if(!pop)return;
    const selection=window.getSelection();const text=selection?.toString().trim();
    const node=selection?.anchorNode;const element=node?.nodeType===1?node:node?.parentElement;
    const start=element?.closest('.message-copy');const endNode=selection?.focusNode;const endElement=endNode?.nodeType===1?endNode:endNode?.parentElement;
    if(!text||!start||!start.contains(endElement)){pop.hidden=true;return;}
    state.selectedText=text;state.selectedMessage=start.closest('.message').dataset.message;
    const rect=selection.getRangeAt(0).getBoundingClientRect();pop.style.left=`${Math.max(12,Math.min(window.innerWidth-190,rect.left+rect.width/2-90))}px`;pop.style.top=`${Math.max(8,rect.top-48)}px`;pop.hidden=false;
  });
  document.addEventListener('mousedown',e=>{if(e.target.closest('[data-action="capture-selection"]'))e.preventDefault();else if(!e.target.closest('.message-copy')){const pop=$('#selection-pop');if(pop)pop.hidden=true;}});
  document.addEventListener('change',e=>{if(e.target.id==='task-status' && state.taskSelected!==null){tasks[state.taskSelected].status=e.target.value;if(state.taskFilter!=='全部'&&state.taskFilter!==e.target.value)state.taskFilter='全部';refreshTaskPage();$('#task-status')?.focus({preventScroll:true});}});
  document.addEventListener('input',e=>{if(e.target.id==='search-input')$('#search-results').innerHTML=searchResults(e.target.value)});
  document.addEventListener('keydown',e=>{
    if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();if(!state.search)openSearch();return;}
    if(e.key==='Escape'){if(state.search)closeSearch();else if(document.body.classList.contains('show-drawer'))closeDrawer();else if(route().name==='tasks'&&state.taskSelected!==null){updateTaskSelection(null);}return;}
    if(state.search&&e.key==='ArrowDown'&&e.target.id==='search-input'){
      const first=$('#search-results .search-result'); if(first){e.preventDefault();first.focus();} return;
    }
    const dialog=state.search?$('#modal .search-modal'):document.body.classList.contains('show-drawer')?$('#drawer'):null;
    if(e.key==='Tab'&&dialog){
      const items=[...dialog.querySelectorAll('button:not([disabled]),a[href],input:not([disabled]),textarea:not([disabled])')].filter(el=>el.offsetParent!==null);
      if(!items.length)return;
      if(e.shiftKey&&document.activeElement===items[0]){e.preventDefault();items[items.length-1].focus();}
      else if(!e.shiftKey&&document.activeElement===items[items.length-1]){e.preventDefault();items[0].focus();}
    }
  });
  window.addEventListener('hashchange',()=>{
    if(document.startViewTransition && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) document.startViewTransition(()=>render());
    else render();
  });render();
})();
