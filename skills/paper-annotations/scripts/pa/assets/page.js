
(function(){
  var cards=[].slice.call(document.querySelectorAll('.qcard'));
  var showAI=document.getElementById('showai');
  var filter=document.getElementById('statusf');
  var search=document.getElementById('q');
  var links=[].slice.call(document.querySelectorAll('a.qlink'));
  // A highlight is its card's footprint in the text, so it follows the card:
  // hide the card and the mark goes with it, leaving the sentence untouched.
  var marks=[].slice.call(document.querySelectorAll('mark[data-id]'));

  var themeBtn=document.getElementById('theme');
  var modes=[['system','🌗 跟隨系統'],['light','☀️ 淺色'],['dark','🌙 深色']];
  // memory holds the truth; storage is only persistence. Reading the mode back
  // from storage would leave the toggle stuck wherever storage is unavailable
  // (file:// in some browsers, private mode).
  var mode='system';
  try{var saved=localStorage.getItem('pa-theme');
      if(saved==='light'||saved==='dark'||saved==='system') mode=saved;}catch(e){}
  function setMode(m){
    mode=m;
    if(m==='system'){document.documentElement.removeAttribute('data-theme');}
    else{document.documentElement.setAttribute('data-theme',m);}
    try{localStorage.setItem('pa-theme',m);}catch(e){}
    for(var i=0;i<modes.length;i++){ if(modes[i][0]===m) themeBtn.textContent=modes[i][1]; }
  }
  setMode(mode);
  themeBtn.addEventListener('click',function(){
    var i=0;
    for(var j=0;j<modes.length;j++){ if(modes[j][0]===mode) i=j; }
    setMode(modes[(i+1)%modes.length][0]);
  });

  // file:// often refuses the async clipboard, so the old way stays as backup.
  function copyText(text,ok,fail){
    if(navigator.clipboard&&navigator.clipboard.writeText){
      navigator.clipboard.writeText(text).then(function(){ ok&&ok(); },manual);
    } else { manual(); }
    function manual(){
      var t=document.createElement('textarea');
      t.value=text; t.setAttribute('readonly','');
      t.style.cssText='position:fixed;top:-1000px;left:0;opacity:0';
      document.body.appendChild(t); t.select();
      var good=false;
      try{ good=document.execCommand('copy'); }catch(e){}
      document.body.removeChild(t);
      if(good){ ok&&ok(); } else { fail&&fail(); }
    }
  }

  function apply(){
    var want=filter.value, ai=showAI.classList.contains('on');
    var term=(search.value||'').toLowerCase();
    var shown={};
    cards.forEach(function(c){
      var ok=true;
      if(want==='none') ok=false;
      else if(want!=='all'&&c.dataset.status!==want) ok=false;
      if(!ai&&c.dataset.origin==='suggested') ok=false;
      if(term&&c.textContent.toLowerCase().indexOf(term)<0) ok=false;
      c.classList.toggle('hidden',!ok);
      shown[c.dataset.id]=ok;
    });
    // the list mirrors the cards, so a filtered-out question cannot be clicked
    links.forEach(function(a){
      var id=a.getAttribute('href').replace('#card-','');
      a.classList.toggle('hidden', shown[id]===false);
    });
    marks.forEach(function(k){
      k.classList.toggle('off', shown[k.dataset.id]===false);
    });
    if(current&&shown[current]===false) closeCard();
  }
  showAI.addEventListener('click',function(){ showAI.classList.toggle('on'); apply(); });
  filter.addEventListener('change',apply);
  search.addEventListener('input',apply);

  // Pointing at the handle opens the sidebar; clicking pins it. Driven from
  // JS rather than :hover so the handle's geometry can be held still until the
  // slide is over -- see the stylesheet for why that is the whole ballgame.
  var body=document.body;
  var wrap=document.getElementById('sidewrap');
  var pinned=false, leaveTimer=0, slideTimer=0;
  // the label's own width, so the fold starts from where it actually ends
  var stxt=document.querySelector('#sidetoggle .stxt');
  if(stxt){
    document.documentElement.style.setProperty(
      '--stxt-w',(Math.ceil(stxt.getBoundingClientRect().width)+1)+'px');
  }
  // read the duration rather than repeating it: reduced-motion drops the rule
  // entirely, and 0s then falls out of this by itself
  function slideMs(){
    var d=(getComputedStyle(wrap).transitionDuration||'0s').split(',')[0].trim();
    var n=parseFloat(d)||0;
    return /ms$/.test(d)?n:n*1000;
  }
  function openSide(){
    clearTimeout(leaveTimer); leaveTimer=0;
    body.classList.remove('side-closing');
    if(body.classList.contains('side-open')) return;
    body.classList.add('side-open');
    clearTimeout(slideTimer);
    slideTimer=setTimeout(function(){ body.classList.add('side-settled'); },slideMs());
  }
  function closeSide(){
    pinned=false;
    if(!body.classList.contains('side-open')) return;
    body.classList.remove('side-open');
    body.classList.add('side-closing');
    clearTimeout(slideTimer);
    slideTimer=setTimeout(function(){
      body.classList.remove('side-settled');
      body.classList.remove('side-closing');
    },slideMs());
  }
  wrap.addEventListener('mouseenter',function(){
    if(!body.classList.contains('side-closing')) openSide();
  });
  wrap.addEventListener('mouseleave',function(){
    if(pinned) return;
    clearTimeout(leaveTimer);
    // a pointer that clips the edge on its way somewhere else should not
    // slam the drawer shut behind it
    leaveTimer=setTimeout(closeSide,180);
  });
  document.getElementById('sidetoggle').addEventListener('click',function(){
    if(pinned){ closeSide(); return; }
    pinned=true; openSide();
  });

  // Draft area. Nothing leaves the page from here -- the copy button is the
  // whole point: read the paragraph, write the question, paste it into chat.
  var pad=document.getElementById('notepad');
  var stat=document.getElementById('nstat');
  var KEY='pa-draft:'+(document.title||'');
  try{ var kept=localStorage.getItem(KEY); if(kept) pad.value=kept; }catch(e){}
  function say(msg){ stat.textContent=msg; setTimeout(function(){ stat.textContent=''; },1600); }
  pad.addEventListener('input',function(){
    try{ localStorage.setItem(KEY,pad.value); }catch(e){}
  });
  document.getElementById('notetab').addEventListener('click',function(){
    body.classList.add('note-on'); pad.focus();
  });
  document.getElementById('noteclose').addEventListener('click',function(){
    body.classList.remove('note-on');
  });
  document.getElementById('ncopy').addEventListener('click',function(){
    if(!pad.value){ say('還沒有內容'); return; }
    copyText(pad.value,function(){ say('已複製'); },function(){ say('複製失敗，請手動選取'); });
  });
  document.getElementById('nclear').addEventListener('click',function(){
    if(!pad.value) return;
    pad.value=''; try{ localStorage.removeItem(KEY); }catch(e){} say('已清空'); pad.focus();
  });

  // A card opens over the paper and closes again -- it never pushes the text
  // around, so the page reads as a paper however many questions pile up.
  var panel=document.getElementById('panel');
  var panelIn=document.getElementById('panel-in');
  var ov=document.getElementById('ov');
  var jump=document.getElementById('pjump');
  var current=null;
  function openCard(id){
    var card=document.getElementById('card-'+id);
    if(!card||card.classList.contains('hidden')) return;
    var parts=[].slice.call(card.children), head='', rest='';
    parts.forEach(function(n){
      if(n.tagName==='SUMMARY') head=n.innerHTML; else rest+=n.outerHTML;
    });
    panelIn.innerHTML='<div class="ptitle">'+head+'</div>'+rest;
    panel.dataset.status=card.dataset.status||'open';
    current=id;
    jump.hidden=!document.querySelector('mark[data-id="'+id+'"]');
    panel.hidden=false; ov.hidden=false;
    panel.scrollTop=0;
    panel.focus();
  }
  function closeCard(){ panel.hidden=true; ov.hidden=true; current=null; }
  document.getElementById('main').addEventListener('click',function(e){
    var m=e.target.closest?e.target.closest('mark[data-id]'):null;
    if(m&&!m.classList.contains('off')) openCard(m.dataset.id);
  });
  links.forEach(function(a){
    a.addEventListener('click',function(e){
      e.preventDefault();
      openCard(a.getAttribute('href').replace('#card-',''));
    });
  });
  jump.addEventListener('click',function(){
    var m=current&&document.querySelector('mark[data-id="'+current+'"]');
    closeCard();
    if(m) m.scrollIntoView({block:'center'});
  });
  document.getElementById('pclose').addEventListener('click',closeCard);
  ov.addEventListener('click',closeCard);
  document.addEventListener('keydown',function(e){
    if(e.key!=='Escape') return;
    var np=document.getElementById('hlnote');
    if(np&&!np.hidden){ np.hidden=true; np.dataset.i=''; return; }
    if(hlBar&&!hlBar.hidden){ hlHide(); return; }
    if(!panel.hidden){ closeCard(); return; }
    if(body.classList.contains('note-on')&&document.activeElement!==pad){
      body.classList.remove('note-on');
    }
  });
  // Formulas light up as a whole while selected -- see the .katex rules in the
  // stylesheet for why the browser's own painting is switched off there.
  var lit=[],pending=0;
  function relight(){
    pending=0;
    while(lit.length) lit.pop().classList.remove('sel');
    var s=window.getSelection();
    if(!s||s.isCollapsed||!s.rangeCount) return;
    var scope=s.getRangeAt(0).commonAncestorContainer;
    if(scope.nodeType===3) scope=scope.parentNode;
    if(!scope||!scope.querySelectorAll) return;
    // a selection sitting entirely inside one formula has no .katex below it
    var own=scope.closest?scope.closest('.katex'):null;
    if(own){ own.classList.add('sel'); lit.push(own); }
    var found=scope.querySelectorAll('.katex');
    for(var i=0;i<found.length;i++){
      if(s.containsNode(found[i],true)){ found[i].classList.add('sel'); lit.push(found[i]); }
    }
  }
  // setTimeout rather than requestAnimationFrame: rAF is suspended while the
  // page is not being painted, which would leave the class stale.
  document.addEventListener('selectionchange',function(){
    if(pending) return;
    pending=setTimeout(relight,0);
  });

  // ---- Highlighter -------------------------------------------------------
  // The reader's own marks, kept in the browser. This page is opened from
  // file:// with nothing behind it, so it cannot write into notes/; what it can
  // do is hold them and hand them back on request (「複製畫記」) for the agent
  // to file properly. They are a working layer, like the draft drawer -- the
  // cards remain the only thing the build treats as truth.
  var HL_OK=!!(window.CSS&&window.CSS.highlights&&window.Highlight&&window.Map);
  var hlBtn=document.getElementById('hlon');
  var hlBar=document.getElementById('hlbar');
  var hlStat=document.getElementById('hlstat');
  var hlDel=document.getElementById('hldel');
  // Keyed by the paper, not by the file's path or a digest of its text: the
  // page moves and gets rebuilt constantly, and either of those would drop
  // every mark the next time a card was added.
  var hlKey='pa-hl:'+(body.dataset.paper||document.title||'');
  var hlItems=[], hlOn=true, hlPick=-1, hlMaps={}, hlZone=null;
  // set once the page knows whether serve.py is behind it
  var paToken='', paMark=function(){};

  function hlNorm(s){ return (s||'').replace(/\s+/g,' ').trim(); }
  function hlSec(node){
    var el=node&&node.nodeType===3?node.parentElement:node;
    return el&&el.closest?el.closest('#main .chunk'):null;
  }
  // Text index over one section. The MathML twin is skipped for the same
  // reason it is unselectable: it repeats every formula, and counting it would
  // put every offset after a formula in the wrong place.
  function hlMap(sec){
    if(hlMaps[sec.id]) return hlMaps[sec.id];
    var walk=document.createTreeWalker(sec,NodeFilter.SHOW_TEXT,{acceptNode:function(n){
      var p=n.parentElement;
      if(!p||!n.nodeValue) return NodeFilter.FILTER_REJECT;
      return p.closest('.katex-mathml,.qcard')?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT;
    }});
    var m={txt:'',nodes:[],offs:[],at:new Map()},n;
    while((n=walk.nextNode())){
      m.at.set(n,m.nodes.length); m.offs.push(m.txt.length);
      m.nodes.push(n); m.txt+=n.nodeValue;
    }
    m.zw=new RegExp(ZW).test(m.txt);
    hlMaps[sec.id]=m; return m;
  }
  function hlIndex(map,node,off){
    var i=map.at.get(node);
    if(i!==undefined) return map.offs[i]+off;
    // An element boundary: formulas select whole, so a selection edge often
    // lands beside a .katex rather than inside text. Take the first mapped
    // node at or after the boundary.
    var b=document.createRange();
    try{ b.setStart(node,off); }catch(e){ return 0; }
    b.collapse(true);
    var lo=0,hi=map.nodes.length;
    while(lo<hi){
      var mid=(lo+hi)>>1, cmp;
      try{ cmp=b.comparePoint(map.nodes[mid],0); }catch(e){ cmp=0; }
      if(cmp>=0) hi=mid; else lo=mid+1;
    }
    return lo<map.nodes.length?map.offs[lo]:map.txt.length;
  }
  function hlPos(map,idx){
    var lo=0,hi=map.nodes.length-1,i=0;
    while(lo<=hi){
      var mid=(lo+hi)>>1;
      if(map.offs[mid]<=idx){ i=mid; lo=mid+1; } else hi=mid-1; }
    var node=map.nodes[i];
    return {node:node,off:Math.max(0,Math.min(idx-map.offs[i],node.nodeValue.length))};
  }
  function hlRange(map,a,b){
    var s=hlPos(map,a), e=hlPos(map,b), r=document.createRange();
    try{ r.setStart(s.node,s.off); r.setEnd(e.node,e.off); }catch(err){ return null; }
    return r;
  }
  function hlHead(a,b){ var i=0; while(i<a.length&&i<b.length&&a[i]===b[i]) i++; return i; }
  function hlTail(a,b){
    var i=0;
    while(i<a.length&&i<b.length&&a[a.length-1-i]===b[b.length-1-i]) i++;
    return i;
  }
  // KaTeX seeds rendered formulas with zero-width breaks, and what gets handed
  // over -- and so what ends up in notes/marks/ -- has them stripped out to be
  // readable. The search therefore has to tolerate them turning up anywhere,
  // including mid-token, which is exactly where KaTeX puts them. Only sections
  // that actually contain one pay for the per-character form.
  var ZW='[\u200b-\u200f\ufeff]';
  function hlEsc(s){ return s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'); }
  function hlPattern(exact,zw){
    var gap=zw?'(?:\\s|'+ZW+')+':'\\s+';
    return hlNorm(exact).split(' ').map(function(tok){
      return zw?tok.split('').map(hlEsc).join(ZW+'*'):hlEsc(tok);
    }).join(gap);
  }
  // Re-find a stored mark after reload. Whitespace-tolerant, exactly like the
  // Python side: the rendered text wraps differently from the Markdown. When
  // the sentence occurs more than once the neighbours decide which one.
  function hlLocate(it){
    var sec=document.getElementById(it.sec);
    if(!sec||!it.exact) return null;
    var map=hlMap(sec), re;
    try{ re=new RegExp(hlPattern(hlPlain(it.exact),map.zw),'g'); }
    catch(e){ return null; }
    var hits=[],m;
    while((m=re.exec(map.txt))){
      hits.push(m);
      if(re.lastIndex<=m.index) re.lastIndex=m.index+1;
      if(hits.length>80) break;
    }
    if(!hits.length) return null;
    var best=hits[0];
    if(hits.length>1){
      var top=-1;
      hits.forEach(function(h){
        var end=h.index+h[0].length;
        var score=hlTail(hlNorm(hlPlain(map.txt.slice(Math.max(0,h.index-60),h.index))),
                         hlPlain(it.prefix))
                 +hlHead(hlNorm(hlPlain(map.txt.slice(end,end+60))),hlPlain(it.suffix));
        if(score>top){ top=score; best=h; }
      });
    }
    return hlRange(map,best.index,best.index+best[0].length);
  }
  function hlPaint(){
    if(!HL_OK) return;
    ['1','2','3','4'].forEach(function(c){
      CSS.highlights.delete('pa-hl'+c); CSS.highlights.delete('pa-hl'+c+'n'); });
    if(!hlOn) return;
    var by={};
    hlItems.forEach(function(it){
      if(!it.range) return;
      var key=it.color+(it.note?'n':'');
      (by[key]=by[key]||[]).push(it.range);
    });
    Object.keys(by).forEach(function(k){
      var h=new Highlight();
      by[k].forEach(function(r){ h.add(r); });
      CSS.highlights.set('pa-hl'+k,h);
    });
  }
  // Only what the browser is holding. The filed ones came out of notes/marks/
  // and belong to the build; writing them back here would give every mark two
  // homes and no way to tell which one is current.
  function hlLocal(){
    return hlItems.filter(function(it){ return it.src!=='file'; });
  }
  function hlSave(){
    try{
      localStorage.setItem(hlKey,JSON.stringify(hlLocal().map(function(it){
        return {s:it.sec,f:it.file||'',e:it.exact,p:it.prefix,x:it.suffix,
                c:it.color,n:it.note||''}; })));
    }catch(e){}
  }
  // Marks that no longer resolve are kept, not dropped: they still carry the
  // sentence, and 「複製畫記」 lists them so nothing disappears silently.
  function hlStatus(){
    if(!HL_OK){ hlStat.textContent='這個瀏覽器不支援畫記（需要較新版 Chrome／Edge／Safari／Firefox）'; return; }
    var lost=0, local=0;
    hlItems.forEach(function(it){
      if(!it.range) lost++;
      if(it.src!=='file') local++;
    });
    if(!hlItems.length){ hlStat.textContent='選取正文就能畫記'; return; }
    var msg=hlItems.length+' 條畫記';
    // the distinction that matters: filed ones survive a rebuild, the rest
    // live in this browser only until they are handed over
    if(local) msg+='，其中 '+local+' 條還沒落檔';
    if(lost) msg+='；'+lost+' 條找不到原文';
    if(!hlOn) msg+='（已隱藏）';
    hlStat.textContent=msg;
  }
  var hlTimer=0;
  function hlSay(msg){
    hlStat.textContent=msg;
    clearTimeout(hlTimer);
    hlTimer=setTimeout(hlStatus,2200);
  }
  function hlHide(){ hlBar.hidden=true; hlPick=-1; hlZone=null; }
  function hlPlace(rect){
    hlBar.hidden=false;
    var w=hlBar.offsetWidth, h=hlBar.offsetHeight;
    var x=Math.min(Math.max(6,rect.left+rect.width/2-w/2),window.innerWidth-w-6);
    var y=rect.top-h-8;
    if(y<6) y=rect.bottom+8;
    hlBar.style.left=x+'px'; hlBar.style.top=y+'px';
    // Where the pointer may wander before the palette is taken to be finished
    // with: the text it belongs to, the palette itself, and room to travel
    // between the two.
    var box=hlBar.getBoundingClientRect();
    hlZone={l:Math.min(rect.left,box.left)-60, r:Math.max(rect.right,box.right)+60,
            t:Math.min(rect.top,box.top)-60, b:Math.max(rect.bottom,box.bottom)+60};
  }
  function hlAdd(color){
    var sel=window.getSelection();
    if(!sel||sel.isCollapsed||!sel.rangeCount) return -1;
    var r=sel.getRangeAt(0), sec=hlSec(r.startContainer);
    if(!sec){ hlSay('只能在正文裡畫記'); return -1; }
    if(hlSec(r.endContainer)!==sec){ hlSay('畫記不能跨章節，請分兩次'); return -1; }
    var map=hlMap(sec);
    var a=hlIndex(map,r.startContainer,r.startOffset);
    var b=hlIndex(map,r.endContainer,r.endOffset);
    if(b<a){ var t=a; a=b; b=t; }
    while(a<b&&/\s/.test(map.txt.charAt(a))) a++;
    while(b>a&&/\s/.test(map.txt.charAt(b-1))) b--;
    var exact=hlNorm(map.txt.slice(a,b));
    if(exact.length<2){ hlSay('選取太短'); return -1; }
    var it={sec:sec.id,file:sec.dataset.src||(sec.id+'.md'),
      exact:exact,color:color,note:'',src:'local',
      prefix:hlNorm(map.txt.slice(Math.max(0,a-48),a)),
      suffix:hlNorm(map.txt.slice(b,b+48))};
    it.range=hlRange(map,a,b);
    if(!it.range){ hlSay('這段定位不到，請換個選取範圍'); return -1; }
    hlItems.push(it);
    if(!hlOn){ hlOn=true; hlBtn.classList.add('on'); }
    hlSave(); hlPaint(); hlStatus();
    sel.removeAllRanges();
    // The palette stays, now aimed at what was just drawn: the moment you most
    // often want it back is straight after, to change the colour, write a note
    // or undo. It clears itself once the pointer leaves.
    hlPick=hlItems.length-1;
    hlDel.hidden=false;
    hlPlace(it.range.getBoundingClientRect());
    return hlPick;
  }
  function hlAt(x,y){
    var r=null;
    if(document.caretRangeFromPoint) r=document.caretRangeFromPoint(x,y);
    else if(document.caretPositionFromPoint){
      var p=document.caretPositionFromPoint(x,y);
      if(p){ r=document.createRange(); r.setStart(p.offsetNode,p.offset); }
    }
    if(!r) return -1;
    for(var i=hlItems.length-1;i>=0;i--){
      if(!hlItems[i].range) continue;
      try{
        if(hlItems[i].range.comparePoint(r.startContainer,r.startOffset)===0) return i;
      }catch(e){}
    }
    return -1;
  }
  // KaTeX seeds rendered formulas with zero-width breaks. They have to stay in
  // what is stored -- \s does not match them, so stripping them would stop the
  // mark being found again -- but they are noise in the handed-over text.
  function hlPlain(s){ return (s||'').replace(/[\u200b-\u200f\ufeff]/g,''); }
  function hlReport(){
    var names={'1':'yellow','2':'green','3':'blue','4':'red'};
    var list=hlLocal();
    var out=['螢光筆畫記 '+list.length+' 條 — '+document.title.replace(' — 疑問註記',''),
             '（這些還沒落檔，請 agent 依 SKILL 的格式寫進 notes/marks/ 再重建）',''];
    list.forEach(function(it,i){
      out.push((i+1)+'. file: '+(it.file||it.sec)+'  color: '+(names[it.color]||'yellow')
        +(it.range?'':'  ⚠️ 目前定位不到'));
      out.push('   exact:  '+hlPlain(it.exact));
      out.push('   prefix: '+hlPlain(it.prefix));
      out.push('   suffix: '+hlPlain(it.suffix));
      if(it.note) out.push('   note:   '+it.note.replace(/\n/g,'\n           '));
    });
    return out.join('\n');
  }

  // Writing on a highlight, the thing obsidian-annotator gets right: the mark
  // and what you wanted to say about it are one object, not two.
  var hlNote=document.getElementById('hlnote');
  var hlPad=document.getElementById('hlnotepad');
  // A mark on disk is editable only while something can write to disk. Without
  // a server the page has no way to change the file, and pretending otherwise
  // would leave the two disagreeing.
  function hlWritable(it){ return it && (it.src!=='file' || !!paToken); }
  function hlEdit(i){
    if(i<0||!hlItems[i]||!hlWritable(hlItems[i])) return;
    hlNote.dataset.i=String(i);
    hlPad.value=hlItems[i].note||'';
    hlNote.hidden=false;
    var r=hlItems[i].range?hlItems[i].range.getBoundingClientRect():null;
    var w=hlNote.offsetWidth, h=hlNote.offsetHeight;
    var x=r?Math.min(Math.max(8,r.left),window.innerWidth-w-8):(window.innerWidth-w)/2;
    var y=r?(r.bottom+10):(window.innerHeight-h)/2;
    if(y+h>window.innerHeight-8) y=Math.max(8,(r?r.top:0)-h-10);
    hlNote.style.left=x+'px'; hlNote.style.top=y+'px';
    hlHide();
    hlPad.focus();
  }
  function hlEditClose(){ hlNote.hidden=true; hlNote.dataset.i=''; }
  // A filed mark is read-only here: it lives in notes/marks/, and letting the
  // page edit it would give the same note two masters.
  function hlShowNote(it){
    panelIn.innerHTML='<div class="ptitle">'+esc(hlPlain(it.exact))+'</div>'
      +'<div class="csec csec-key"><b class="csec-t">畫記註解</b><p>'
      +esc(it.note).replace(/\n{2,}/g,'</p><p>').replace(/\n/g,'<br>')+'</p></div>';
    panel.dataset.status='';
    current=null;
    jump.hidden=true;
    panel.hidden=false; ov.hidden=false;
    panel.scrollTop=0; panel.focus();
  }
  function esc(s){
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // Hovering a noted mark shows what it says. Rect arithmetic first and only
  // then caret work: this runs off mousemove, and a highlight that spans three
  // lines has three boxes, not one.
  var hlTip=document.getElementById('hltip');
  var tipAt=-1, tipTimer=0, tipLast=0;
  function tipHide(){ clearTimeout(tipTimer); hlTip.hidden=true; tipAt=-1; }
  function tipFind(x,y){
    for(var i=hlItems.length-1;i>=0;i--){
      var it=hlItems[i];
      if(!it.note||!it.range) continue;
      var boxes=it.range.getClientRects();
      for(var j=0;j<boxes.length;j++){
        var r=boxes[j];
        if(x>=r.left&&x<=r.right&&y>=r.top&&y<=r.bottom) return i;
      }
    }
    return -1;
  }
  function tipShow(i,x,y){
    if(!hlItems[i]) return;
    hlTip.textContent=hlItems[i].note;
    hlTip.hidden=false;
    var w=hlTip.offsetWidth, h=hlTip.offsetHeight;
    var left=Math.min(x+14,window.innerWidth-w-8);
    var top=y+18;
    if(top+h>window.innerHeight-8) top=Math.max(8,y-h-12);
    hlTip.style.left=Math.max(8,left)+'px';
    hlTip.style.top=top+'px';
    tipAt=i;
  }

  if(HL_OK){
    document.getElementById('hlnotebtn').addEventListener('mousedown',function(e){
      e.preventDefault();
    });
    document.getElementById('hlnotebtn').addEventListener('click',function(){
      // straight from a selection: draw it first, then write on it
      hlEdit(hlPick>=0?hlPick:hlAdd('1'));
    });
    document.getElementById('hlnoteok').addEventListener('click',function(){
      var i=parseInt(hlNote.dataset.i,10);
      if(!isNaN(i)&&hlItems[i]){
        var it=hlItems[i], text=hlPad.value.trim();
        // filed: let paMark apply it, so a failed write can put it back
        if(it.src==='file'){ hlEditClose(); paMark(it,'update',{note:text}); return; }
        it.note=text;
        hlSave(); hlPaint(); hlStatus();
      }
      hlEditClose();
    });
    document.getElementById('hlnotecancel').addEventListener('click',hlEditClose);
    document.getElementById('hlnotedel').addEventListener('click',function(){
      var i=parseInt(hlNote.dataset.i,10);
      if(!isNaN(i)&&hlItems[i]){
        var it=hlItems[i];
        if(it.src==='file'){ hlEditClose(); paMark(it,'delete'); return; }
        hlItems.splice(i,1);
        hlSave(); hlPaint(); hlStatus();
      }
      hlEditClose();
    });
    [].slice.call(hlBar.querySelectorAll('[data-c]')).forEach(function(btn){
      btn.addEventListener('mousedown',function(e){ e.preventDefault(); });
      btn.addEventListener('click',function(){
        var c=btn.dataset.c;
        // recolouring keeps the palette up, so a second try costs nothing
        if(hlPick<0){ hlAdd(c); return; }
        var it=hlItems[hlPick];
        if(it.src==='file'){ hlHide(); paMark(it,'update',{color:c}); return; }
        it.color=c;
        hlSave(); hlPaint();
      });
    });
    hlDel.addEventListener('mousedown',function(e){ e.preventDefault(); });
    hlDel.addEventListener('click',function(){
      if(hlPick<0) return;
      var it=hlItems[hlPick];
      if(it.src==='file'){ hlHide(); paMark(it,'delete'); return; }
      hlItems.splice(hlPick,1);
      hlSave(); hlPaint(); hlStatus(); hlHide();
    });
    // Distinguish a click from a drag: with user-select:all a bare click on a
    // formula already IS a selection, and the selection branch below used to
    // shadow the mark underneath -- managing a formula highlight took two
    // clicks where highlighted text took one.
    var downAt=null;
    document.addEventListener('mousedown',function(e){ downAt=[e.clientX,e.clientY]; });
    // mouseup, not selectionchange: during a drag the bar would chase the
    // pointer. The timeout lets the selection settle first.
    document.addEventListener('mouseup',function(e){
      if(hlBar.contains(e.target)) return;
      // Off means off: a live selection must not raise the palette either.
      // And a click on the page furniture is not a reading gesture -- it does
      // not always clear the selection, which would put the palette straight
      // back over the paper the moment the reader reached for a button.
      var chrome=e.target.closest&&e.target.closest('#sidewrap,#notewrap,#panel,#ov,#hlnote');
      if(!hlOn||chrome){ hlHide(); return; }
      setTimeout(function(){
        if(!panel.hidden){ hlHide(); return; }
        function manage(i){
          var it=hlItems[i];
          // a filed mark shows what it says; one still in the browser is
          // still yours to change
          // filed and no server behind the page: it can only be read here
          if(it.src==='file'&&!paToken){
            hlHide(); if(it.note) hlShowNote(it); return;
          }
          hlPick=i; hlDel.hidden=false;
          hlPlace(it.range.getBoundingClientRect());
        }
        // clicking a mark opens its card -- that gesture stays as it was
        var onCard=e.target.closest&&e.target.closest('mark[data-id]');
        var sel=window.getSelection();
        if(sel&&!sel.isCollapsed&&sel.rangeCount&&hlSec(sel.getRangeAt(0).startContainer)){
          // A selection without a drag is user-select:all handing over a
          // whole formula. Aimed at an existing mark, that gesture means
          // "this mark", not "a new mark on top of it": drop the automatic
          // selection and manage the mark, one click, same as text.
          var clicked=downAt&&Math.abs(e.clientX-downAt[0])<5&&Math.abs(e.clientY-downAt[1])<5;
          var hit=clicked&&!onCard?hlAt(e.clientX,e.clientY):-1;
          if(hit>=0){ sel.removeAllRanges(); manage(hit); return; }
          hlPick=-1; hlDel.hidden=true;
          hlPlace(sel.getRangeAt(0).getBoundingClientRect());
          return;
        }
        var i=onCard?-1:hlAt(e.clientX,e.clientY);
        if(i>=0&&hlOn){ manage(i); return; }
        hlHide();
      },0);
    });
    document.addEventListener('selectionchange',function(){
      var sel=window.getSelection();
      if(hlPick<0&&(!sel||sel.isCollapsed)) hlHide();
    });
    // Raised from a click on a mark, or straight after drawing one, there is no
    // selection to collapse and nothing above would ever take it down again --
    // it just sat over the paper. Walking away dismisses it. While text is
    // still selected it stays put: the reader is mid-decision.
    document.addEventListener('mousemove',function(e){
      if(hlBar.hidden||!hlZone) return;
      var sel=window.getSelection();
      if(sel&&!sel.isCollapsed) return;
      if(e.clientX<hlZone.l||e.clientX>hlZone.r||
         e.clientY<hlZone.t||e.clientY>hlZone.b) hlHide();
    });
    document.addEventListener('mousemove',function(e){
      // anything the reader has deliberately opened outranks a tooltip
      if(!hlOn||!panel.hidden||!hlNote.hidden||!hlBar.hidden){ tipHide(); return; }
      var now=Date.now();
      if(now-tipLast<60) return;
      tipLast=now;
      var i=tipFind(e.clientX,e.clientY);
      if(i<0){ tipHide(); return; }
      // both halves matter: the index on its own goes stale the moment
      // anything hides the tooltip without clearing it, and hovering the
      // same mark again would then do nothing at all
      if(i===tipAt&&!hlTip.hidden) return;
      clearTimeout(tipTimer);
      var x=e.clientX, y=e.clientY;
      // a short wait, so sweeping the pointer across the page stays quiet
      tipTimer=setTimeout(function(){ tipShow(i,x,y); },120);
    });
    // The palette is placed in viewport coordinates, so once the text has
    // scrolled it is pointing at nothing. Three listeners rather than one:
    // scroll alone is fired during the rendering steps and does not always
    // arrive, so the input that caused the scroll is watched as well.
    function hlDrop(){ hlHide(); tipHide(); }
    window.addEventListener('scroll',hlDrop,true);
    document.addEventListener('wheel',hlDrop,{passive:true});
    document.addEventListener('touchmove',hlDrop,{passive:true});
    var SCROLLKEY=/^(Page|Arrow|Home|End| )/;
    document.addEventListener('keydown',function(e){
      if(!hlBar.hidden&&SCROLLKEY.test(e.key)) hlHide();
    });
    hlBtn.addEventListener('click',function(){
      hlOn=!hlOn;
      hlBtn.classList.toggle('on',hlOn);
      hlHide(); tipHide(); hlPaint(); hlStatus();
    });
    // serve.py is running behind this page: the save button can then do the
    // whole handoff itself. Opened straight off disk the probe fails, the
    // button never appears, and 複製畫記 stays the way through.
    var saveBtn=document.getElementById('hlsave');
    // A filed mark has exactly one home, notes/marks/. Changing it from the
    // page means rewriting that file, so the page asks the server to do it and
    // then reloads onto the rebuilt result -- no second copy anywhere.
    // The server can go away while the page stays open -- closing its window is
    // how you stop it. From then on the page must stop claiming it can write:
    // hide the save button, put filed marks back to read-only, and say so once.
    function paOffline(){
      if(!paToken) return;
      paToken='';
      saveBtn.hidden=true;
      hlSay('server 已經停了。畫記還留著，重新啟動後才能再存檔');
    }
    // The change is applied here rather than by the caller, so that a failed
    // write can be put back. Showing a colour or a note that never reached the
    // file is worse than refusing outright.
    paMark=function(it,action,change){
      if(!paToken||!it.id) return;
      var before={color:it.color,note:it.note};
      if(change){
        if('color' in change) it.color=change.color;
        if('note' in change) it.note=change.note;
      }
      function undo(){
        it.color=before.color; it.note=before.note;
        hlPaint(); hlStatus();
      }
      hlSay(action==='delete'?'刪除中…':'更新中…');
      fetch('/_pa/mark',{
        method:'POST',
        headers:{'Content-Type':'application/json','X-PA-Token':paToken},
        body:JSON.stringify({id:it.id,action:action,
          color:{'1':'yellow','2':'green','3':'blue','4':'red'}[it.color]||'yellow',
          note:it.note||''})
      }).then(function(r){ return r.json(); }).then(function(d){
        if(d.ok&&d.rebuilt){ location.reload(); return; }
        undo();
        hlSay('失敗：'+(d.error||'重建沒有成功'));
      }).catch(function(){ undo(); paOffline(); });
    };
    fetch('/_pa/hello',{headers:{'Accept':'application/json'}})
      .then(function(r){ return r.ok?r.json():null; })
      .then(function(d){ if(d&&d.token){ paToken=d.token; saveBtn.hidden=false; } })
      .catch(function(){});
    saveBtn.addEventListener('click',function(){
      var list=hlLocal();
      if(!list.length){ hlSay('沒有還沒落檔的畫記'); return; }
      saveBtn.disabled=true;
      hlSay('存檔中…');
      fetch('/_pa/marks',{
        method:'POST',
        headers:{'Content-Type':'application/json','X-PA-Token':paToken},
        body:JSON.stringify({marks:list.map(function(it){
          return {file:it.file||'',color:{'1':'yellow','2':'green','3':'blue','4':'red'}[it.color]||'yellow',
                  exact:hlPlain(it.exact),prefix:hlPlain(it.prefix),
                  suffix:hlPlain(it.suffix),note:it.note||''};
        })})
      }).then(function(r){ return r.json(); }).then(function(d){
        saveBtn.disabled=false;
        if(d.error){ hlSay('存檔失敗：'+d.error); return; }
        if(d.bad&&d.bad.length){ hlSay('存了 '+d.written+' 條，'+d.bad.length+' 條有問題'); }
        // reload rather than patch the page: the rebuild already produced the
        // page with these marks filed, and that is the one worth looking at
        if(d.written&&d.rebuilt){ location.reload(); return; }
        if(!d.written) hlSay('這些畫記已經存過了');
      }).catch(function(){
        saveBtn.disabled=false;
        paOffline();
      });
    });
    document.getElementById('hlcopy').addEventListener('click',function(){
      if(!hlItems.length){ hlSay('還沒有畫記'); return; }
      copyText(hlReport(),function(){ hlSay('已複製 '+hlItems.length+' 條'); },
               function(){ hlSay('複製失敗'); });
    });
    // Clearing has to mean what it says. Wiping only the browser layer looked
    // like it worked and then everything came back on reload, because the
    // filed marks were still on disk -- so say which of the two is happening,
    // with the number, before doing it.
    document.getElementById('hlclear').addEventListener('click',function(){
      var total=hlItems.length;
      if(!total) return;
      var local=hlLocal().length, filed=total-local;
      if(filed&&!paToken&&!local){
        hlSay('已落檔的 '+filed+' 條要改檔案，或開 serve.py 後再清');
        return;
      }
      var wipeFiles=filed>0&&!!paToken;
      var msg;
      if(wipeFiles){
        msg='清空全部 '+total+' 條畫記？其中 '+filed
           +' 條會連 notes/marks/ 裡的檔案一起刪掉，無法復原。';
      } else if(filed){
        msg='這裡只能清掉還沒落檔的 '+local+' 條；已落檔的 '+filed
           +' 條會留著（要改檔案，或開 serve.py 後再清一次）。要繼續嗎？';
      } else {
        msg='清空全部 '+total+' 條畫記？這個動作無法復原。';
      }
      if(!window.confirm(msg)) return;
      try{ localStorage.removeItem(hlKey); }catch(e){}
      // the filed ones stay on screen unless their files are actually going
      hlItems=wipeFiles?[]:hlItems.filter(function(it){ return it.src==='file'; });
      hlPaint(); hlStatus(); hlHide(); tipHide();
      if(wipeFiles){
        hlSay('刪除中…');
        fetch('/_pa/mark',{method:'POST',
          headers:{'Content-Type':'application/json','X-PA-Token':paToken},
          body:JSON.stringify({action:'clear'})
        }).then(function(r){ return r.json(); }).then(function(d){
          if(d.ok&&d.rebuilt){ location.reload(); return; }
          hlSay('刪除失敗：'+(d.error||'重建沒有成功'));
        }).catch(function(){ hlSay('刪除失敗，server 可能停了'); });
      }
    });
  } else {
    hlBtn.disabled=true;
    document.getElementById('hlcopy').disabled=true;
    document.getElementById('hlclear').disabled=true;
  }
  // After KaTeX: it rewrites every formula into a subtree, and a range built
  // before that points at nodes which no longer exist. Its listener is
  // registered in <head>, so ours runs second.
  function hlInit(){
    if(HL_OK){
      hlItems=[];
      var filed={};
      var tag=document.getElementById('pa-marks');
      var fromFile=[];
      if(tag){ try{ fromFile=JSON.parse(tag.textContent||'[]')||[]; }catch(e){ fromFile=[]; } }
      fromFile.forEach(function(d){
        var it={sec:d.s,file:d.f||'',exact:d.e,prefix:d.p||'',suffix:d.x||'',
                color:d.c||'1',note:d.n||'',src:'file',id:d.id};
        it.range=hlLocate(it);
        // hlPlain on the key: the browser copy keeps KaTeX's zero-width
        // breaks, the filed copy was stripped of them on save -- compared
        // raw, a mark that touched a formula never matched its filed twin
        // and stayed "還沒落檔" forever, painted twice.
        filed[it.sec+'\u0000'+hlPlain(it.exact)]=true;
        hlItems.push(it);
      });
      var raw=null;
      try{ raw=localStorage.getItem(hlKey); }catch(e){}
      var data=[];
      if(raw){ try{ data=JSON.parse(raw)||[]; }catch(e){ data=[]; } }
      var filedAny=false;
      data.forEach(function(d){
        // already written into notes/marks/ -- drop the browser's copy rather
        // than paint the same sentence twice
        if(filed[d.s+'\u0000'+hlPlain(d.e)]){ filedAny=true; return; }
        var it={sec:d.s,file:d.f||'',exact:d.e,prefix:d.p||'',suffix:d.x||'',
                color:d.c||'1',note:d.n||'',src:'local'};
        it.range=hlLocate(it);
        hlItems.push(it);
      });
      if(filedAny) hlSave();
      hlPaint();
    }
    hlStatus();
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',hlInit);
  else setTimeout(hlInit,0);

  apply();
})();
