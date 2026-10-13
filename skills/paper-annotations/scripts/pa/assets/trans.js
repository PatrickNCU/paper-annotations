// 譯文對照: the translation column, switched on and off from the corner.
//
// The translation is already in the page (pa/translation.py drops a cell after
// every block it translates); this only shows it, keeps the reader's place
// while the layout changes under them, and lets the split between the two
// columns be dragged. Syncing the scroll is not this file's job at all: each
// translated block sits in the same grid row as its source, so there is one
// scroll and nothing to keep in step.
(function(){
  var btn=document.getElementById('trtoggle');
  if(!btn) return;
  var root=document.documentElement;
  var main=document.getElementById('main');
  var split=document.getElementById('trsplit');
  var ready=btn.dataset.ready==='1';
  var KEY='pa-tr:'+(document.body.dataset.paper||'');
  var SPLIT='pa-tr-split';
  var GAP=56, WIDE=900;

  function store(k,v){ try{ if(v===null) localStorage.removeItem(k); else localStorage.setItem(k,v); }catch(e){} }

  // A word next to the button when there is nothing to show yet: pressing it
  // and getting an empty column would teach the reader the button is broken.
  var msg=null, msgTimer=0;
  function say(text){
    if(!msg){
      msg=document.createElement('div');
      msg.id='trmsg'; msg.setAttribute('role','status');
      document.body.appendChild(msg);
    }
    msg.textContent=text; msg.hidden=false;
    clearTimeout(msgTimer);
    msgTimer=setTimeout(function(){ msg.hidden=true; },6000);
  }

  // The block at the top of the screen before the switch is put back at the
  // same height after it -- both layouts move every paragraph.
  function holdPlace(change){
    var x=main.getBoundingClientRect().left+40, y=Math.min(140,window.innerHeight/3);
    var el=document.elementFromPoint(x,y);
    var block=el&&el.closest?el.closest('.chunk>*'):null;
    var before=block?block.getBoundingClientRect().top:0;
    change();
    if(block) window.scrollBy(0,block.getBoundingClientRect().top-before);
  }

  function paint(){
    var on=root.classList.contains('tr-on');
    btn.setAttribute('aria-pressed',on?'true':'false');
    placeSplit();
    // the card labels in the margin measure their paragraph; it just moved
    window.dispatchEvent(new Event('resize'));
  }

  btn.addEventListener('click',function(){
    if(!ready){
      say('這篇還沒有譯文。\n'+
          '・在對話裡說「翻譯這篇的 S130」，翻好重建後這顆就能用\n'+
          '・左下「工具 → 譯文設定」可以挑章節、整理術語表');
      return;
    }
    var on=!root.classList.contains('tr-on');
    holdPlace(function(){ root.classList.toggle('tr-on',on); paint(); });
    store(KEY,on?'on':null);
    if(on&&btn.title) say(btn.title);
  });

  // ---- the split ---------------------------------------------------------
  // One handle for the whole page, fixed to the screen, rather than one per
  // section: it has to be grabbable wherever the reader happens to be.
  var frac=0.5;
  try{ var kept=parseFloat(localStorage.getItem(SPLIT)); if(kept>=0.3&&kept<=0.7) frac=kept; }catch(e){}
  function apply(f){ frac=f; root.style.setProperty('--trf',String(f)); }
  apply(frac);
  function inner(){
    var r=main.getBoundingClientRect(), cs=getComputedStyle(main);
    var l=r.left+parseFloat(cs.paddingLeft), w=r.width-parseFloat(cs.paddingLeft)-parseFloat(cs.paddingRight);
    return {l:l,w:w};
  }
  function placeSplit(){
    if(!split) return;
    var on=root.classList.contains('tr-on')&&window.innerWidth>=WIDE;
    split.hidden=!on;
    if(!on) return;
    var b=inner();
    split.style.left=(b.l+(b.w-GAP)*frac+GAP/2-split.offsetWidth/2)+'px';
  }
  window.addEventListener('resize',function(){ placeSplit(); });
  if(split){
    var dragging=false;
    split.addEventListener('pointerdown',function(e){
      dragging=true; split.setPointerCapture(e.pointerId);
      split.classList.add('drag'); e.preventDefault();
    });
    split.addEventListener('pointermove',function(e){
      if(!dragging) return;
      var b=inner();
      var f=(e.clientX-b.l-GAP/2)/(b.w-GAP);
      apply(Math.max(0.3,Math.min(0.7,Math.round(f*100)/100)));
      placeSplit();
    });
    function stop(){
      if(!dragging) return;
      dragging=false; split.classList.remove('drag');
      store(SPLIT,Math.abs(frac-0.5)<0.005?null:String(frac));
      window.dispatchEvent(new Event('resize'));
    }
    split.addEventListener('pointerup',stop);
    split.addEventListener('pointercancel',stop);
    // back to even, the way a double-click resets a split everywhere else
    split.addEventListener('dblclick',function(){
      apply(0.5); store(SPLIT,null); placeSplit();
      window.dispatchEvent(new Event('resize'));
    });
  }

  if(!ready) root.classList.remove('tr-on');
  paint();
})();

// 譯文設定: how far the translation has got, the glossary, the preferences.
//
// Opened from the 工具 menu. Nothing here translates -- the agent does, in the
// conversation -- so the progress tab ends in a request to copy into the chat,
// not in a job. The glossary and the preferences are the two files the agent
// reads first (pa/translation.py), at two levels: the shelf's, shared by every
// paper, and this paper's, which overrides it. They are written through the
// server; with no server the panel shows what the build saw and says why it
// cannot change it.
(function(){
  var tag=document.getElementById('pa-trset');
  if(!tag) return;
  var data;
  try{ data=JSON.parse(tag.textContent); }catch(e){ return; }
  var token='', live=false;
  var slug=(function(){
    var m=/^\/p\/([^\/]+)\//.exec(location.pathname);
    try{ return m?decodeURIComponent(m[1]):''; }catch(e){ return m?m[1]:''; }
  })();
  var paperTitle=document.title.replace(/\s+—\s+疑問註記$/,'');
  var tab='status', scope=null, editing=-1, picked={}, langDraft={};

  function esc(s){
    return String(s==null?'':s).replace(/[&<>"]/g,function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; });
  }
  function copyText(text,ok,fail){
    function manual(){
      var t=document.createElement('textarea');
      t.value=text; t.setAttribute('readonly','');
      t.style.cssText='position:fixed;top:-1000px;left:0;opacity:0';
      document.body.appendChild(t); t.select();
      var good=false;
      try{ good=document.execCommand('copy'); }catch(e){}
      document.body.removeChild(t);
      if(good) ok(); else fail();
    }
    if(navigator.clipboard&&navigator.clipboard.writeText)
      navigator.clipboard.writeText(text).then(ok,manual);
    else manual();
  }

  var ov=document.createElement('div');
  ov.id='trsetov'; ov.hidden=true;
  var box=document.createElement('section');
  box.id='trset'; box.hidden=true; box.tabIndex=-1;
  box.setAttribute('role','dialog'); box.setAttribute('aria-modal','true');
  box.setAttribute('aria-labelledby','trsettitle');
  box.innerHTML=
    '<header class="tshead"><h2 id="trsettitle">譯文設定</h2>'+
    '<span class="tsstat" id="tsstat" role="status"></span>'+
    '<button class="tsx" id="tsx" aria-label="關閉">✕</button></header>'+
    '<nav class="tstabs" role="tablist">'+
    '<button role="tab" data-tab="status">翻譯進度</button>'+
    '<button role="tab" data-tab="terms">術語表</button>'+
    '<button role="tab" data-tab="lang">語言偏好</button></nav>'+
    '<div class="tsbody" id="tsbody"></div>';
  document.body.appendChild(ov);
  document.body.appendChild(box);
  var bodyEl=document.getElementById('tsbody');
  var stat=document.getElementById('tsstat');
  var statTimer=0;
  function say(text,bad){
    stat.textContent=text; stat.className='tsstat'+(bad?' bad':'');
    clearTimeout(statTimer);
    if(!bad) statTimer=setTimeout(function(){ stat.textContent=''; },3500);
  }

  function scopes(){ return data.scopes||[]; }
  function scopeData(name){
    var out=null;
    scopes().forEach(function(s){ if(s.scope===name) out=s; });
    return out;
  }
  function currentScope(){
    if(!scope||!scopeData(scope)) scope=(scopeData('shelf')?'shelf':'paper');
    return scopeData(scope);
  }

  // ---- 翻譯進度 ----------------------------------------------------------
  function sectionTitle(id){
    var sec=document.getElementById(id);
    var h=sec&&sec.querySelector('h1,h2,h3,h4');
    return h?h.textContent.trim():id.replace(/^S\d+-/,'').replace(/-/g,' ');
  }
  function shortId(id){ var m=/^(S\d+)/.exec(id); return m?m[1]:id; }
  function drawStatus(){
    var rows=data.sections||[], t={total:0,ok:0,stale:0,none:0};
    rows.forEach(function(r){ t.total+=r.total; t.ok+=r.ok; t.stale+=r.stale; t.none+=r.none; });
    var html='<div class="tssum">'+
      '<div><b class="ok">'+t.ok+'</b><span>已翻</span></div>'+
      '<div><b class="stale">'+t.stale+'</b><span>待更新</span></div>'+
      '<div><b>'+t.none+'</b><span>未翻</span></div></div>';
    if(!rows.length){
      bodyEl.innerHTML=html+'<p class="tsempty">這篇沒有可以翻譯的段落。</p>';
      return;
    }
    html+='<div class="tsbar"><span class="tshint">勾章節 → 複製請求 → 貼到對話裡。參考文獻不翻。</span>'+
      '<button data-act="gaps">選有缺的</button><button data-act="none">清除</button></div>'+
      '<ul class="tslist">';
    rows.forEach(function(r){
      var done=r.total?Math.round(r.ok/r.total*100):0;
      var state=r.stale?'待更新 '+r.stale+' 段':(r.none?'未翻 '+r.none+' 段':'完成');
      var cls=r.stale?'stale':(r.none?(r.ok?'part':'none'):'ok');
      html+='<li class="'+cls+'"><label><input type="checkbox" data-id="'+esc(r.id)+'"'+
        (picked[r.id]?' checked':'')+'><span class="tsid">'+esc(shortId(r.id))+'</span>'+
        '<span class="tsname">'+esc(sectionTitle(r.id))+'</span></label>'+
        '<span class="tsmeter" title="已翻 '+r.ok+' / '+r.total+' 段"><i style="width:'+done+'%"></i></span>'+
        '<span class="tsstate">'+esc(state)+'</span>'+
        '<button class="tsjump" data-jump="'+esc(r.id)+'" title="跳到這一節" aria-label="跳到這一節">⤴</button></li>';
    });
    html+='</ul><div class="tsfoot"><span id="tspicked"></span>'+
      '<button class="go" data-act="copy">複製翻譯請求</button></div>';
    bodyEl.innerHTML=html;
    countPicked();
  }
  function pickedIds(){
    return (data.sections||[]).filter(function(r){ return picked[r.id]; })
      .map(function(r){ return r.id; });
  }
  function countPicked(){
    var el=document.getElementById('tspicked');
    if(!el) return;
    var ids=pickedIds();
    el.textContent=ids.length?('已選 '+ids.length+' 節'):'還沒選章節';
  }
  function request(ids){
    return '請翻譯「'+paperTitle+'」的 '+ids.map(shortId).join('、')+
      '（缺的和待更新的都要）。\n論文資料夾：'+data.work;
  }

  // ---- 術語表 ------------------------------------------------------------
  function scopeSwitch(){
    if(scopes().length<2)
      return '<div class="tsscope"><span class="one">'+esc(currentScope().label)+'</span></div>';
    return '<div class="tsscope" role="radiogroup">'+scopes().map(function(s){
      return '<button role="radio" data-scope="'+s.scope+'" aria-checked="'+
        (s.scope===scope?'true':'false')+'">'+esc(s.label)+'</button>';
    }).join('')+'</div>';
  }
  function otherTerms(){
    var other=scopeData(scope==='paper'?'shelf':'paper'), map={};
    if(other) other.terms.rows.forEach(function(r){ map[r.term.toLowerCase()]=r.use; });
    return map;
  }
  function lockNote(){
    return live?'':'<p class="tslock">要開著 server（開啟書房.cmd）才能修改；現在顯示的是建置這一頁時的內容。</p>';
  }
  function drawTerms(){
    var s=currentScope(), rows=s.terms.rows, other=otherTerms();
    var dis=live?'':' disabled';
    var html=scopeSwitch()+
      '<p class="tspath">'+esc(s.terms.path)+'</p>'+lockNote()+
      '<ul class="tshint"><li>'+(scope==='paper'?
        '只套用在這篇；和書房共用的表寫了同一個詞時，以這裡為準。':
        '書房裡每一篇都套用；某篇要不一樣，就在那篇的術語表另寫一條。')+
      '</li><li>改了不會讓既有譯文變成待更新；要套用，請 agent 重翻用到的段落。</li></ul>';
    html+='<table class="tsterms"><thead><tr><th>原文</th><th>譯法</th><th>備註</th><th></th></tr></thead><tbody>';
    if(!rows.length)
      html+='<tr class="empty"><td colspan="4">還沒有術語。加一條，翻譯時就會照著寫。</td></tr>';
    rows.forEach(function(r,i){
      var key=r.term.toLowerCase(), clash='';
      if(key in other)
        clash='<span class="tsclash">'+(scope==='paper'?'覆寫書房：':'這篇另有譯法：')+esc(other[key])+'</span>';
      if(i===editing){
        html+='<tr class="edit"><td><input data-f="term" value="'+esc(r.term)+'"></td>'+
          '<td><input data-f="use" value="'+esc(r.use)+'"></td>'+
          '<td><input data-f="note" value="'+esc(r.note)+'"></td>'+
          '<td class="act"><button class="go" data-act="saverow" data-i="'+i+'">儲存</button>'+
          '<button data-act="cancel">取消</button></td></tr>';
      } else {
        html+='<tr><td>'+esc(r.term)+'</td><td>'+esc(r.use)+clash+'</td><td class="note">'+esc(r.note)+'</td>'+
          '<td class="act"><button data-act="edit" data-i="'+i+'"'+dis+'>編輯</button>'+
          '<button data-act="del" data-i="'+i+'"'+dis+'>刪除</button></td></tr>';
      }
    });
    html+='</tbody><tfoot><tr class="add">'+
      '<td><input id="tsnt" placeholder="原文，例如 wirelength"'+dis+'></td>'+
      '<td><input id="tsnu" placeholder="譯法，例如 線長"'+dis+'></td>'+
      '<td><input id="tsnn" placeholder="備註（可空白）"'+dis+'></td>'+
      '<td class="act"><button class="go" data-act="add"'+dis+'>新增</button></td></tr></tfoot></table>';
    bodyEl.innerHTML=html;
  }
  function saveTerms(rows,done){
    var s=currentScope();
    post({kind:'terms',scope:s.scope,rows:rows,rev:s.terms.rev},function(){
      editing=-1; say('已存進 '+s.terms.path.split(/[\\\/]/).pop()); draw(); if(done) done();
    });
  }

  // ---- 語言偏好 ----------------------------------------------------------
  function drawLang(){
    var s=currentScope();
    var text=(s.scope in langDraft)?langDraft[s.scope]:s.languages.text;
    var dirty=text!==s.languages.text;
    var html='<details class="tsdefault"><summary>內建的預設規則（每篇都套用）</summary>'+
      '<div class="tsdeftext">'+esc(data['default']||'')+'</div></details>'+
      scopeSwitch()+'<p class="tspath">'+esc(s.languages.path)+'</p>'+lockNote()+
      '<ul class="tshint"><li>套用順序：預設 → 書房共用 → 這篇論文，越後面越優先，只覆寫寫到的部分。</li>'+
      '<li>改了不會讓既有譯文變成待更新。</li></ul>'+
      '<textarea id="tslang" spellcheck="false"'+(live?'':' readonly')+
      ' placeholder="例：\n- 數學名詞一律用中文：梯度、步長、收斂\n- 語氣用書面語，不用「你」\n- bin 保留英文，不譯成「格子」">'+
      esc(text)+'</textarea>'+
      '<div class="tsfoot"><span>'+(dirty?'還沒儲存':'')+'</span>'+
      '<button data-act="revert"'+(dirty?'':' disabled')+'>還原</button>'+
      '<button class="go" data-act="savelang"'+(live&&dirty?'':' disabled')+'>儲存</button></div>';
    bodyEl.innerHTML=html;
  }

  // ---- plumbing ----------------------------------------------------------
  function draw(){
    [].forEach.call(box.querySelectorAll('.tstabs button'),function(b){
      b.setAttribute('aria-selected',b.dataset.tab===tab?'true':'false');
    });
    if(tab==='status') drawStatus();
    else if(tab==='terms') drawTerms();
    else drawLang();
  }
  function post(body,ok){
    if(!live){ say('server 沒開，改不了',true); return; }
    body.paper=slug;
    say('儲存中…');
    fetch('/_pa/translation',{method:'POST',
      headers:{'Content-Type':'application/json','X-PA-Token':token},
      body:JSON.stringify(body)
    }).then(function(r){ return r.json(); }).then(function(d){
      if(d.error){ say(d.error,true); return; }
      data=d; ok();
    }).catch(function(){ say('連不上 server，沒有存到',true); });
  }
  function refresh(){
    if(!live) return;
    fetch('/_pa/translation?p='+encodeURIComponent(slug),{headers:{'Accept':'application/json'}})
      .then(function(r){ return r.ok?r.json():null; })
      .then(function(d){ if(d&&d.scopes){ data=d; draw(); } }).catch(function(){});
  }
  function dirtyLang(){
    return Object.keys(langDraft).some(function(k){
      var s=scopeData(k); return s&&langDraft[k]!==s.languages.text; });
  }
  function open(){
    ov.hidden=false; box.hidden=false;
    draw(); box.focus(); refresh();
  }
  function close(){
    if(dirtyLang()&&!window.confirm('語言偏好還沒儲存，要放棄嗎？')) return;
    langDraft={}; editing=-1;
    ov.hidden=true; box.hidden=true;
  }
  window.paTrSettings={open:open};

  ov.addEventListener('click',close);
  document.getElementById('tsx').addEventListener('click',close);
  box.addEventListener('keydown',function(e){
    if(e.key==='Escape'){ e.stopPropagation(); close(); }
    if(e.key==='Enter'&&e.target.closest&&e.target.closest('tfoot')){
      e.preventDefault(); act('add',null);
    }
  });
  box.querySelector('.tstabs').addEventListener('click',function(e){
    var b=e.target.closest('button'); if(!b) return;
    tab=b.dataset.tab; editing=-1; draw();
  });
  bodyEl.addEventListener('change',function(e){
    if(e.target.matches('input[type=checkbox][data-id]')){
      picked[e.target.dataset.id]=e.target.checked; countPicked();
    }
  });
  bodyEl.addEventListener('input',function(e){
    if(e.target.id==='tslang'){
      var s=currentScope(), had=(s.scope in langDraft)&&langDraft[s.scope]!==s.languages.text;
      langDraft[s.scope]=e.target.value;
      var now=e.target.value!==s.languages.text;
      if(now!==had){
        var pos=e.target.selectionStart; drawLang();
        var t=document.getElementById('tslang'); t.focus(); t.setSelectionRange(pos,pos);
      }
    }
  });
  bodyEl.addEventListener('click',function(e){
    var b=e.target.closest('button'); if(!b||b.disabled) return;
    if(b.dataset.scope){ scope=b.dataset.scope; editing=-1; draw(); return; }
    if(b.dataset.jump){
      close();
      var sec=document.getElementById(b.dataset.jump);
      if(sec) sec.scrollIntoView({block:'start'});
      return;
    }
    act(b.dataset.act,b);
  });
  function act(name,b){
    var s=currentScope(), rows=s?s.terms.rows.slice():[];
    if(name==='gaps'){
      (data.sections||[]).forEach(function(r){ picked[r.id]=!!(r.none||r.stale); });
      drawStatus();
    } else if(name==='none'){
      picked={}; drawStatus();
    } else if(name==='copy'){
      var ids=pickedIds();
      if(!ids.length){ say('先勾要翻的章節',true); return; }
      copyText(request(ids),function(){ say('已複製，貼到對話裡'); },
               function(){ say('複製失敗',true); });
    } else if(name==='add'){
      if(!live) return;
      var t=document.getElementById('tsnt'), u=document.getElementById('tsnu'), n=document.getElementById('tsnn');
      if(!t||!t.value.trim()){ say('先填原文',true); if(t) t.focus(); return; }
      if(!u.value.trim()){ say('譯法還沒填',true); u.focus(); return; }
      rows.push({term:t.value.trim(),use:u.value.trim(),note:n.value.trim()});
      saveTerms(rows,function(){ var t2=document.getElementById('tsnt'); if(t2) t2.focus(); });
    } else if(name==='edit'){
      editing=+b.dataset.i; drawTerms();
      var first=bodyEl.querySelector('tr.edit input'); if(first) first.focus();
    } else if(name==='cancel'){
      editing=-1; drawTerms();
    } else if(name==='saverow'){
      var row={};
      [].forEach.call(bodyEl.querySelectorAll('tr.edit input'),function(inp){ row[inp.dataset.f]=inp.value.trim(); });
      rows[+b.dataset.i]=row;
      saveTerms(rows);
    } else if(name==='del'){
      var r=rows[+b.dataset.i];
      if(!window.confirm('從'+s.label+'的術語表刪掉「'+r.term+'」？')) return;
      rows.splice(+b.dataset.i,1);
      saveTerms(rows);
    } else if(name==='revert'){
      delete langDraft[s.scope]; drawLang();
    } else if(name==='savelang'){
      post({kind:'languages',scope:s.scope,text:langDraft[s.scope],rev:s.languages.rev},function(){
        delete langDraft[s.scope];
        say('已存進 '+s.languages.path.split(/[\\\/]/).pop()); draw();
      });
    }
  }

  fetch('/_pa/hello',{headers:{'Accept':'application/json'}})
    .then(function(r){ return r.ok?r.json():null; })
    .then(function(d){
      if(d&&d.token){ token=d.token; live=true; if(!box.hidden){ draw(); refresh(); } }
    }).catch(function(){});
})();
