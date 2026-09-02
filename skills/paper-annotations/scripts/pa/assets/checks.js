
// Section checkpoints.
//
// The build already put a readable question at the end of each section; this
// turns it into the thing that actually asks. What it does not do is judge:
// there is no model on this page, so after he writes an answer the section's
// own point is shown and HE says whether he got it -- the same honesty the
// grading buttons run on.
//
// Two attempts, never three. The second swaps in a differently-worded hint; a
// second miss stops asking and files a suggested card instead, because "until
// you know it" is what the review loop is for and that loop already exists.
(function(){
  var tag=document.getElementById('pa-checks');
  if(!tag) return;
  var conf={};
  try{ conf=JSON.parse(tag.textContent)||{}; }catch(e){ return; }
  var rows=conf.checks||[];
  if(!rows.length) return;

  var byId={}, order=[];
  rows.forEach(function(r){ byId[r.id]=r; order.push(r.id); });

  function esc(s){
    return String(s==null?'':s).replace(/[&<>"]/g,function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];
    });
  }
  function mathify(el){
    if(!window.renderMathInElement) return;
    try{
      window.renderMathInElement(el,{
        delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],
        ignoredClasses:['no-math'],throwOnError:false,strict:false});
    }catch(e){}
  }

  var slug=(function(){
    var m=/^\/p\/([^\/]+)\//.exec(location.pathname);
    try{ return m?decodeURIComponent(m[1]):''; }catch(e){ return m?m[1]:''; }
  })();
  var token='';

  // ---- the pieces of the page a checkpoint works with --------------------

  function boxOf(id){ return document.getElementById('check-'+id); }
  function sectionOf(id){
    var box=boxOf(id);
    return box&&box.closest?box.closest('section.chunk'):null;
  }
  function pointsOf(id){
    var sec=sectionOf(id);
    return sec?[].slice.call(sec.querySelectorAll('.pnote')):[];
  }
  // The sentence the question was written from. Read off the page rather than
  // shipped again in JSON -- it is already an element, with its maths rendered.
  function answerOf(id){
    var row=byId[id], target=String(row.target||'').replace(/^[Pp]/,'');
    if(!target) return '';
    var el=document.getElementById('point-'+target);
    if(!el) return '';
    var copy=el.cloneNode(true);
    [].slice.call(copy.querySelectorAll('.pk,.xlinks')).forEach(function(n){ n.remove(); });
    return copy.innerHTML;
  }
  function done(state){ return state==='pass'||state==='skip'||state==='card'; }

  // ---- covering the section's points -------------------------------------

  function veil(id){
    var row=byId[id], list=pointsOf(id), sec=sectionOf(id);
    if(!sec) return;
    var note=sec.querySelector('.cpveiled');
    if(!note&&list.length){
      note=document.createElement('div');
      note.className='cpveiled';
      list[0].parentNode.insertBefore(note,list[0]);
    }
    var hide=!done(row.state)&&list.length>0;
    list.forEach(function(p){ p.classList.toggle('cpveil',hide); });
    if(note){
      note.hidden=!hide;
      note.textContent='這一節有 '+list.length+' 則要點，先答過下面的檢查點再看'+
        '——不然答案就在眼前了。';
    }
  }

  // ---- the running skeleton ----------------------------------------------

  // What to call a section in the running summary.
  //
  // innerHTML, not textContent: a heading with maths in it has already been
  // rendered, and reading it back as text yields the source and the rendered
  // form run together. A long section is split into pieces and only the first
  // carries the heading, so a headingless piece borrows the nearest one before
  // it and says it is a continuation -- the file stem is not a section title.
  function label(sec,fallback){
    var head=sec?sec.querySelector('h1,h2,h3'):null;
    if(head) return head.innerHTML;
    var back=sec?sec.previousElementSibling:null;
    while(back){
      var earlier=back.querySelector?back.querySelector('h1,h2,h3'):null;
      if(earlier) return earlier.innerHTML+'（續）';
      back=back.previousElementSibling;
    }
    return esc(fallback);
  }

  // A finished checkpoint with no server behind it looks exactly like a
  // finished one that was written down, until the page is reloaded and it is
  // back to unanswered. Say so while it is still on screen -- but only about
  // the ones he moved here and now: the states the page was built with came
  // off the log and are on disk whether or not a server is running.
  function unsaved(id){
    return byId[id].local?'<div class="cpwarn">沒開 server，這個結果只在這一頁上，'+
      '重新載入就沒了。要留下來就開 server 再答一次。</div>':'';
  }

  function summary(id){
    var upto=order.indexOf(id), html='', total=0;
    for(var i=0;i<upto;i++){
      var other=byId[order[i]];
      if(!done(other.state)) continue;
      var list=pointsOf(other.id);
      if(!list.length) continue;
      html+='<div class="cpsec">'+label(sectionOf(other.id),other.section)+'</div><ul>';
      list.forEach(function(p){
        var copy=p.cloneNode(true);
        [].slice.call(copy.querySelectorAll('.pk,.xlinks')).forEach(function(n){ n.remove(); });
        html+='<li>'+copy.innerHTML+'</li>';
        total++;
      });
      html+='</ul>';
    }
    if(!total) return '';
    return '<details class="cpsum"><summary>到這裡為止，這篇說了什麼（前面 '+total+
      ' 則要點）——這一節的就在上面</summary>'+html+'</details>';
  }

  // ---- one checkpoint ----------------------------------------------------

  function draw(id){
    var row=byId[id], box=boxOf(id);
    if(!box) return;
    var title=box.getAttribute('data-title')||'';
    box.dataset.state=row.state;
    var html='';
    if(row.state==='todo'||row.state==='again'){
      html+='<div class="cpt">段落檢查點'+(row.state==='again'?' · 第 2 次':'')+'</div>'+
        '<p class="cpq">'+esc(row.question)+'</p>';
      if(row.state==='again'&&row.hint) html+='<p class="cph">'+esc(row.hint)+'</p>';
      if(row.phase==='judge'){
        html+='<div class="cpmine"><b>你寫的</b>'+esc(row.draft||'')+'</div>'+
          '<div class="cpans"><b>這一節的要點說</b>'+(answerOf(id)||'（找不到對應的要點）')+'</div>'+
          '<p class="cpq" style="font-size:14px;margin-top:10px">答到了嗎？只有你知道。</p>'+
          '<div class="cpbar"><button class="go" data-act="pass">答到了</button>'+
          '<button data-act="miss">沒答到</button></div>';
      } else {
        html+='<textarea rows="3" placeholder="先寫，不用完整。寫到卡住的地方也算。">'+
          esc(row.draft||'')+'</textarea>'+
          '<div class="cpbar"><button class="go" data-act="compare">對答案</button>'+
          '<button class="soft" data-act="skip">跳過，直接看要點</button></div>';
      }
      html+='<div class="cpsay" data-say>'+(token?'':
        '沒開 server，這裡照樣可以自測，但答了不會記錄。')+'</div>';
    } else if(row.state==='pass'){
      html+='<div class="cpt">段落檢查點 · 過了 ✓'+(row.tries>1?'（第 2 次）':'')+'</div>'+
        '<div class="cpsay">這一節的要點已經打開了，就在上面。</div>'+unsaved(id)+summary(id);
    } else if(row.state==='skip'){
      html+='<div class="cpt">段落檢查點 · 跳過 ⏭</div>'+
        '<div class="cpsay">要點直接打開了；目錄上這一節標著跳過，想補答隨時可以。</div>'+
        '<div class="cpbar"><button data-act="retry">現在補答</button></div>'+
        unsaved(id)+summary(id);
    } else if(row.state==='card'){
      html+='<div class="cpt">段落檢查點 · 沒過，成了卡片 ✗</div>'+
        '<p class="cpq" style="font-size:14px">'+esc(row.question)+'</p>'+
        '<div class="cpsay">兩次都沒答到，不再問第三次'+
        (row.card?('——記成疑問卡 <a href="#card-'+esc(row.card)+'">Q'+esc(row.card)+
          '</a>（origin: suggested）。解決了它就會進複習排程。'):'。')+
        '這個檢查點不會再擋你。</div>'+unsaved(id)+
        '<div class="cpans"><b>這一節的要點說</b>'+(answerOf(id)||'（找不到對應的要點）')+'</div>'+
        summary(id);
    }
    box.innerHTML=html;
    mathify(box);
    wire(id);
    veil(id);
    marks();
  }

  function wire(id){
    var box=boxOf(id), row=byId[id];
    var area=box.querySelector('textarea');
    if(area){
      area.addEventListener('input',function(){ row.draft=area.value; });
    }
    [].slice.call(box.querySelectorAll('button[data-act]')).forEach(function(b){
      b.addEventListener('click',function(){ act(id,b.dataset.act,b); });
    });
  }

  function say(id,text){
    var el=boxOf(id).querySelector('[data-say]');
    if(el) el.textContent=text;
  }

  function act(id,what,btn){
    var row=byId[id], box=boxOf(id);
    if(what==='compare'){
      var area=box.querySelector('textarea');
      if(!area||!area.value.trim()){ say(id,'先寫一句再對答案——寫不出來也是一種答案，那就按跳過。'); return; }
      row.draft=area.value.trim();
      row.phase='judge';
      draw(id);
      return;
    }
    if(what==='retry'){ row.state='again'; row.phase='write'; row.draft=''; draw(id); return; }
    if(what==='skip'){ send(id,'skip','',btn); return; }
    if(what==='pass'||what==='miss'){ send(id,what,row.draft||'',btn); return; }
  }

  // Records the attempt. Without a server the state still moves on screen, but
  // the page says so rather than pretending it was written down -- the same
  // rule grading follows (docs/adr/0003).
  function send(id,verdict,text,btn){
    var row=byId[id];
    if(!token){
      local(id,verdict);
      say(id,'沒開 server，這一次沒有記錄下來。開了之後再答一次才會留下。');
      return;
    }
    [].slice.call(boxOf(id).querySelectorAll('button')).forEach(function(b){ b.disabled=true; });
    say(id,'記錄中…');
    fetch('/_pa/check',{
      method:'POST',
      headers:{'Content-Type':'application/json','X-PA-Token':token},
      body:JSON.stringify({paper:slug,id:id,verdict:verdict,text:text})
    }).then(function(r){ return r.json(); }).then(function(d){
      if(d.error){
        [].slice.call(boxOf(id).querySelectorAll('button')).forEach(function(b){ b.disabled=false; });
        say(id,'沒記錄成功：'+d.error);
        return;
      }
      row.state=d.state;
      row.card=d.card||row.card;
      row.local=false;
      row.phase='write';
      if(verdict!=='skip') row.tries=(row.tries||0)+1;
      row.draft='';
      draw(id);
      if(d.note) say(id,d.note);
      if(d.reload){
        var bar=boxOf(id).querySelector('.cpsay');
        if(bar){
          bar.insertAdjacentHTML('beforeend',
            '<div class="cpbar"><button class="go" data-reload="1">'+
            '這一頁已經重建，重新載入</button></div>');
          var go=bar.querySelector('[data-reload]');
          if(go) go.addEventListener('click',function(){ location.reload(); });
        }
      }
    }).catch(function(){
      [].slice.call(boxOf(id).querySelectorAll('button')).forEach(function(b){ b.disabled=false; });
      say(id,'沒記錄成功，server 可能停了。');
    });
  }

  // What the page does when there is nothing to write to: move, and admit it.
  function local(id,verdict){
    var row=byId[id];
    row.phase='write';
    row.draft='';
    row.local=true;
    if(verdict==='skip'){ row.state='skip'; }
    else if(verdict==='pass'){ row.state='pass'; row.tries=(row.tries||0)+1; }
    else {
      row.tries=(row.tries||0)+1;
      row.state=row.tries>=(conf.max||2)?'card':'again';
    }
    draw(id);
  }

  // ---- the contents ------------------------------------------------------

  // 'again' gets its own glyph rather than sharing '●' with "you are here":
  // half-filled reads as half way through, and the two do not always coincide.
  var GLYPH={todo:'○',again:'◐',pass:'✓',skip:'⏭',card:'✗'};
  var WORD={todo:'還沒答',again:'答過一次，還有第二次',pass:'過了',
            skip:'跳過',card:'沒過，成了卡片'};
  function marks(){
    // The first unanswered one is where he is up to; everything before it that
    // is still 'todo' was skipped over rather than reached.
    var now='';
    for(var i=0;i<order.length;i++){
      if(!done(byId[order[i]].state)){ now=order[i]; break; }
    }
    // Grouped by heading, not one per checkpoint: a section that continues the
    // one before it has no heading of its own, so two checkpoints can land on
    // the same line of the contents. Two marks there, rather than one silently
    // overwriting the other.
    var byAnchor={};
    rows.forEach(function(row){
      if(!row.anchor) return;
      (byAnchor[row.anchor]=byAnchor[row.anchor]||[]).push(row);
    });
    Object.keys(byAnchor).forEach(function(anchor){
      var link=document.querySelector('#side a[href="#'+anchor+'"]');
      if(!link) return;
      var holder=link.querySelector('.cpmarks');
      if(!holder){
        holder=document.createElement('span');
        holder.className='cpmarks';
        link.insertBefore(holder,link.firstChild);
      }
      holder.innerHTML='';
      byAnchor[anchor].forEach(function(row){
        var here=row.id===now;
        var mark=document.createElement('span');
        mark.className='cpmark'+(here?' now':' '+row.state);
        mark.textContent=here?'●':GLYPH[row.state];
        mark.title=here?'現在這一節':WORD[row.state];
        holder.appendChild(mark);
      });
    });
  }

  // ---- start -------------------------------------------------------------

  rows.forEach(function(row){
    row.phase='write';
    row.draft='';
    if(boxOf(row.id)) draw(row.id);
  });
  var key=document.querySelector('#side .cpkey');
  if(!key){
    var qlist=document.getElementById('qlist');
    if(qlist&&rows.length){
      qlist.insertAdjacentHTML('beforebegin',
        '<div class="cpkey">段落檢查點：○ 還沒答 · ◐ 答過一次 · ● 現在這節 · '+
        '✓ 過了 · ⏭ 跳過 · ✗ 成了卡片</div>');
    }
  }
  marks();

  fetch('/_pa/hello',{headers:{'Accept':'application/json'}})
    .then(function(r){ return r.ok?r.json():null; })
    .then(function(d){
      if(!d||!d.token) return;
      token=d.token;
      rows.forEach(function(row){ if(boxOf(row.id)) draw(row.id); });
      // The page was built at some point in the past; anything answered since
      // then is in the log and not in this HTML. Ask, rather than show him a
      // question he has already answered.
      return fetch('/_pa/checks?p='+encodeURIComponent(slug),
                   {headers:{'Accept':'application/json'}})
        .then(function(r){ return r.ok?r.json():null; })
        .then(function(live){
          if(!live||!live.rows) return;
          var moved=0;
          live.rows.forEach(function(r){
            var row=byId[r.id];
            if(!row||row.state===r.state) return;
            row.state=r.state;
            row.tries=r.tries;
            row.card=r.card||row.card;
            row.phase='write';
            row.draft='';
            moved++;
            if(boxOf(row.id)) draw(row.id);
          });
          if(moved) marks();
        });
    })
    .catch(function(){});
})();
