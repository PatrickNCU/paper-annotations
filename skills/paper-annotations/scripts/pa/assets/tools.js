
// The one corner button, on both pages.
//
// The page never sends a command. It sends one of the action NAMES baked into
// #pa-actions at build time, and the server builds the command line out of its
// own paths (pa/actions.py) -- the same rule every other write endpoint here
// follows. What is baked in is the label, the hint, and the command each
// action is equivalent to, so a page with no server behind it can grey the
// button out and still say what it would have run. A button that vanishes when
// the server is not up teaches the reader nothing.
(function(){
  var tag=document.getElementById('pa-actions');
  if(!tag) return;
  var conf={};
  try{ conf=JSON.parse(tag.textContent)||{}; }catch(e){ return; }
  var list=conf.actions||[];
  if(!list.length) return;
  var byName={};
  list.forEach(function(a){ byName[a.name]=a; });

  function esc(s){
    return String(s==null?'':s).replace(/[&<>"]/g,function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];
    });
  }
  // file:// often refuses the async clipboard, so keep the old way as backup.
  function copyText(text,ok,fail){
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
    if(navigator.clipboard&&navigator.clipboard.writeText){
      navigator.clipboard.writeText(text).then(function(){ ok&&ok(); },manual);
    } else { manual(); }
  }

  // Which paper this page is, taken from where it was served. Empty when the
  // server mounts only one, which it reads as "the only one".
  var slug=(function(){
    var m=/^\/p\/([^\/]+)\//.exec(location.pathname);
    try{ return m?decodeURIComponent(m[1]):''; }catch(e){ return m?m[1]:''; }
  })();

  // ---- the page's own explanation ---------------------------------------
  // Shown the first time and never again once it is closed. The hiding itself
  // happens before the body paints (a class set on <html> in the head), so
  // this only has to remember the decision and offer a way back -- the text
  // carries warnings like 請勿直接編輯 that should not vanish for good.
  var intro=document.getElementById('intro');
  var introGone=document.getElementById('introgone');
  var INTRO_KEY='pa-intro';
  function introHide(){
    document.documentElement.classList.add('intro-off');
    try{ localStorage.setItem(INTRO_KEY,'off'); }catch(e){}
    if(introGone) introGone.hidden=false;
  }
  // Deliberately does NOT clear the stored decision: he asked to see it once
  // more, not to be shown it again every time from now on.
  function introShow(){
    document.documentElement.classList.remove('intro-off');
    if(introGone) introGone.hidden=true;
    if(intro) intro.scrollIntoView({block:'nearest'});
  }
  if(intro){
    var x=intro.querySelector('.introx');
    if(x) x.addEventListener('click',introHide);
  }

  // ---- the corner ------------------------------------------------------
  var box=document.createElement('div');
  box.id='patools';
  box.innerHTML='<div id="patoolsmenu" hidden></div>'+
    '<button id="patoolsbtn" aria-haspopup="true" aria-expanded="false"></button>';
  document.body.appendChild(box);
  var menu=document.getElementById('patoolsmenu');
  var btn=document.getElementById('patoolsbtn');

  var out=document.createElement('section');
  out.id='paout'; out.hidden=true;
  out.innerHTML=
    '<div class="pahead"><span id="patitle"></span><span class="pastat" id="pastat"></span>'+
    '<button class="paclose" id="paclose" aria-label="關閉">✕</button></div>'+
    '<textarea id="papaste" hidden placeholder="把複習頁「複製畫記」的完整輸出貼在這裡"></textarea>'+
    '<pre id="palog"></pre>'+
    '<div class="paverdict" id="paverdict" hidden></div>'+
    '<div class="pabar" id="pabar" hidden></div>';
  document.body.appendChild(out);
  var title=document.getElementById('patitle');
  var stat=document.getElementById('pastat');
  var log=document.getElementById('palog');
  var paste=document.getElementById('papaste');
  var verdictBox=document.getElementById('paverdict');
  var bar=document.getElementById('pabar');

  var token='', busy='';

  function paint(){
    [].slice.call(menu.querySelectorAll('.patool')).forEach(function(b){
      var a=byName[b.dataset.id];
      if(!a) return;  // 這一頁怎麼用 runs nothing, so nothing here applies to it
      // Everything is off while something runs, the running one included: a
      // button you can press that does nothing reads as a broken button.
      b.disabled=!token||!!busy;
      if(!token) b.title='server 沒開，這顆按不動。它等同於：\n'+a.cmd;
      else if(busy===a.name) b.title='正在跑';
      else if(busy) b.title='等「'+byName[busy].label+'」跑完再按';
      else b.title=a.cmd;
    });
    btn.textContent=busy?'⚙ 執行中…':(token?'⚙ 工具':'⚙ 工具（要開 server）');
    btn.classList.toggle('busy',!!busy);
  }

  function build(){
    var html='';
    list.forEach(function(a){
      if(a.hidden) return;
      html+='<button class="patool" data-id="'+esc(a.name)+'">'+esc(a.label)+
            '<span class="phint">'+esc(a.hint)+'</span></button>';
    });
    if(intro) html+='<button class="patool pdoc" data-doc="1">這一頁怎麼用</button>';
    menu.innerHTML=html;
    paint();
  }
  build();

  function menuOpen(on){
    menu.hidden=!on;
    btn.setAttribute('aria-expanded',on?'true':'false');
  }
  btn.addEventListener('click',function(){ menuOpen(menu.hidden); });
  document.addEventListener('click',function(ev){
    if(!box.contains(ev.target)) menuOpen(false);
  });
  document.addEventListener('keydown',function(ev){
    if(ev.key==='Escape') menuOpen(false);
  });
  menu.addEventListener('click',function(ev){
    var b=ev.target.closest?ev.target.closest('.patool'):null;
    if(!b) return;
    if(b.dataset.doc){ introShow(); menuOpen(false); return; }
    if(b.disabled) return;
    menuOpen(false);
    var a=byName[b.dataset.id];
    if(a&&a.stdin) askPaste(a); else start(a.name,'');
  });

  // ---- the output panel -------------------------------------------------
  function open(label){
    title.textContent=label;
    stat.textContent='';
    log.textContent='';
    verdictBox.hidden=true; verdictBox.className='paverdict';
    bar.hidden=true; bar.innerHTML='';
    paste.hidden=true; paste.value='';
    out.hidden=false;
  }
  document.getElementById('paclose').addEventListener('click',function(){
    // Closing the panel does not stop the run -- the script is already going.
    // The corner button keeps saying 執行中… so the state is still on screen.
    out.hidden=true;
  });
  function line(text,cls){
    var at=log.scrollTop+log.clientHeight>=log.scrollHeight-4;
    var span=document.createElement('span');
    if(cls) span.className=cls;
    span.textContent=text+'\n';
    log.appendChild(span);
    if(at) log.scrollTop=log.scrollHeight;
  }
  function verdict(ok,text){
    verdictBox.textContent=text;
    verdictBox.className='paverdict '+(ok?'good':'bad');
    verdictBox.hidden=false;
  }
  function button(label,cls,fn){
    var b=document.createElement('button');
    b.textContent=label;
    if(cls) b.className=cls;
    b.addEventListener('click',fn);
    bar.appendChild(b);
    bar.hidden=false;
  }

  function askPaste(a){
    open(a.label);
    paste.hidden=false;
    stat.textContent='貼上之後按「送出」';
    line('這一步會把貼上的文字交給 '+a.name+'，沒有貼東西就不會跑。','pacmd');
    button('送出','go',function(){
      var text=paste.value;
      if(!text.trim()){ stat.textContent='還沒貼上任何東西'; return; }
      bar.innerHTML=''; bar.hidden=true; paste.hidden=true;
      start(a.name,text);
    });
    button('取消','',function(){ out.hidden=true; });
    paste.focus();
  }

  function start(name,text){
    var a=byName[name];
    if(!a||busy||!token) return;
    busy=name; paint();
    open(a.label);
    stat.textContent='執行中…';
    fetch('/_pa/run',{
      method:'POST',
      headers:{'Content-Type':'application/json','X-PA-Token':token},
      body:JSON.stringify({paper:slug,action:name,text:text||''})
    }).then(function(r){
      if(!r.ok){
        return r.json().then(function(d){ throw new Error((d&&d.error)||('HTTP '+r.status)); },
                             function(){ throw new Error('HTTP '+r.status); });
      }
      if(!r.body||!r.body.getReader){
        // no streaming here: still correct, just all at once at the end
        return r.text().then(function(all){
          all.split('\n').forEach(function(one){ if(one) take(one); });
        });
      }
      return pump(r.body.getReader());
    }).catch(function(why){
      busy=''; paint();
      stat.textContent='';
      verdict(false,String((why&&why.message)||why||'連不上 server'));
    });
  }

  function pump(reader){
    var dec=new TextDecoder('utf-8'), buf='';
    function step(){
      return reader.read().then(function(res){
        if(res.value) buf+=dec.decode(res.value,{stream:true});
        var cut;
        while((cut=buf.indexOf('\n'))>=0){
          var one=buf.slice(0,cut); buf=buf.slice(cut+1);
          if(one.trim()) take(one);
        }
        if(!res.done) return step();
        if(buf.trim()) take(buf);
        // The stream ended without a done line: the server went away mid-run,
        // and the reader must not be told it finished.
        if(busy){
          busy=''; paint();
          stat.textContent='';
          verdict(false,'server 中途斷了，這個動作可能沒跑完。重開 server 之後再按一次。');
        }
      });
    }
    return step();
  }

  function take(raw){
    var d;
    try{ d=JSON.parse(raw); }catch(e){ return; }
    if(d.step){
      stat.textContent=d.of>1?('第 '+d.step+' / '+d.of+' 步'):'執行中…';
      line('$ '+d.cmd,'pacmd');
      return;
    }
    if(d.line!==undefined){
      line(d.line,/[🔴⚠]/.test(d.line)?'pabad':'');
      return;
    }
    if(d.done) finish(d);
  }

  function finish(d){
    var name=busy;
    busy=''; paint();
    stat.textContent='';
    var a=byName[name]||{};
    verdict(d.ok,d.ok?('✓ '+(a.label||'')+' 做完了'):
      ('✗ '+(a.label||'')+' 沒有跑完。上面最後幾行就是原因。'));
    if(d.out){
      // A page cannot hand over a file; it can only say where the file is.
      line('','');
      line(d.out,'pacmd');
      button('複製路徑','',function(){
        copyText(d.out,function(){ stat.textContent='已複製路徑'; },
                        function(){ stat.textContent='複製失敗，請手動選取上面那一行'; });
      });
    }
    if(d.reload){
      // Never reloads by itself: this replaces the page being read, and a
      // reload takes the reader's scroll position with it.
      button('這一頁已經重建，重新載入','go',function(){ location.reload(); });
      button('等一下','',function(){ out.hidden=true; });
    }
    offer(name,d.ok);
  }

  // An action that writes is offered only after the dry run it belongs to, and
  // only when that dry run actually succeeded. The server checks this too.
  function offer(name,ok){
    if(!ok) return;
    list.forEach(function(a){
      if(a.writes!==name) return;
      button(a.label,'go',function(){
        if(!window.confirm(a.label+'？\n\n'+a.hint+'\n這會改到 notes/ 裡的卡片。')) return;
        start(a.name,'');
      });
    });
  }

  // Without this the buttons stay grey and say why. The probe is the only
  // thing that turns them on.
  fetch('/_pa/hello',{headers:{'Accept':'application/json'}})
    .then(function(r){ return r.ok?r.json():null; })
    .then(function(d){ if(d&&d.token){ token=d.token; paint(); } })
    .catch(function(){});
})();
