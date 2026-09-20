/* The review flow, shared by the two pages that run it: a paper's own review
   page (the queue in its sidebar, cards already in the DOM) and the shelf's
   今天要複習 (cards from several papers, fetched one at a time).

   Only the card's origin differs, so only that is a host hook. Everything the
   reader actually meets -- the staged reveal, the confidence question before
   it, the grade buttons and what they promise, the half-understood card's exit
   -- lives here once. Two copies of this would drift, and the drift would be
   invisible: both pages would still work, they would just be asking him to do
   slightly different things under the same name.

   Identity is `key`, not `id`: card ids restart at 0001 in every paper, so an
   id alone stops being an identity the moment two papers share a page. On a
   paper's own page key === id.

   window.paReview.mount(cfg) -> {draw, open, setState, setToken, find, state}

   cfg:
     list, count, line   where the queue, its "(N)" and the one-line summary go
     panel, body         the card container (carries data-stage) and the node
                         the stage controls are appended to
     state               the schedule to start from, or null
     slug                the paper, when every item belongs to one
     show(key,item,ok)   put that card's content into body; call ok(true) once
                         it is there, ok(false) if it could not be shown
     close()             the reader is done with the open card
     copy(text,ok,fail)  clipboard, which each page already solves its own way
     refresh(cb)         fetch the schedule again (optional: without it the
                         answer returned by the grade endpoint is used)
     after(said,key)     a card's status changed on disk (optional)
     rowExtra(item)      extra HTML inside a queue row, e.g. which paper
     scrollTop(el)       where to scroll after a stage change (optional) */
window.paReview = (function(){
  function esc(s){
    return String(s).replace(/[&<>"]/g,function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];
    });
  }
  function days(n){ return n>=365?'1 年':(n+' 天'); }
  function mmdd(iso){ return iso?iso.slice(5):''; }
  var GRADE_NAMES={again:'重來',hard:'困難',good:'良好',easy:'簡單'};

  function mount(cfg){
    var state=cfg.state||null, token='', busy=false;
    // What the open card is doing. read: everything shown, no grading.
    // review: question first, then the one line, then the rest, then a grade.
    // half: his own words first, the answer only after. The stage is a data
    // attribute on the panel and the stylesheet hides sections by it, so the
    // card's HTML is never taken apart.
    var mode='read', jolPick='', selfText='', current=null;
    var panel=cfg.panel, body=cfg.body, list=cfg.list;

    function keyOf(item){ return item.key||item.id; }
    function paperOf(item){ return (item&&item.paper)||cfg.slug||''; }
    function find(key){
      if(!state) return null;
      var all=(state.scheduled||[]).concat(state.queue||[]);
      for(var i=0;i<all.length;i++){ if(keyOf(all[i])===key) return all[i]; }
      return null;
    }
    function modeFor(it){ return it&&it.kind==='half'?'half':'review'; }
    function say(text){
      var s=document.getElementById('srssay');
      if(s) s.textContent=text;
    }

    // One line the reader can act on before opening anything: what is due,
    // what is stuck, and when the next one comes if nothing is.
    function draw(){
      if(!list) return;
      if(!state){ list.innerHTML=''; if(cfg.line) cfg.line.textContent=''; return; }
      var q=state.queue||[], due=state.due||0, half=state.half||0;
      if(cfg.count) cfg.count.textContent=due?'('+due+')':'';
      if(cfg.line){
        cfg.line.textContent='今天到期 '+due+' 張 · 半懂 '+half+' 張'+
          (state.next?' · 下一張 '+mmdd(state.next):'');
      }
      var html='';
      if(!q.length){
        // three different reasons for an empty list, three different sentences
        var msg;
        if(!state.tracked) msg='還沒有排程中的卡。卡片標成已解決，就會排進來。';
        else if(state.done_today) msg='今天做完了。'+
          (state.tomorrow?'明天 '+state.tomorrow+' 張。':
           (state.next?'下一張 '+mmdd(state.next)+'。':''));
        else msg='今天沒有到期的卡。'+(state.next?'下一張 '+mmdd(state.next)+'。':'');
        html='<div class="qempty">'+msg+'</div>';
      } else {
        html=q.map(function(it){
          var tag;
          if(it.kind==='half') tag='<span class="srstag half">半懂'+
            (it.since!=null?' '+it.since+' 天':'')+'</span>';
          else if(it.retry) tag='<span class="srstag retry">再答一次</span>';
          else tag='<span class="srstag due">到期</span>';
          return '<a class="qlink srsitem" href="'+esc(it.url||('#card-'+it.id))+
                 '" data-key="'+esc(keyOf(it))+'">'+
                 tag+'<span class="qtext">'+esc(it.question)+'</span>'+
                 (cfg.rowExtra?cfg.rowExtra(it):'')+'</a>';
        }).join('');
      }
      // The queue is cut at a length nobody finishes in one sitting rather
      // than paged; saying so is the honest half of that decision.
      if(state.queue_total&&state.queue_total>q.length){
        html+='<div class="srshint">還有 '+(state.queue_total-q.length)+
          ' 張排在後面，做完這些會再出現。</div>';
      }
      var parked=state.parked||[];
      if(parked.length){
        html+='<div class="srshint">'+parked.map(function(p){ return 'Q'+p.id; }).join('、')+
          ' 今天答錯 3 次了，明天再來。</div>';
      }
      var ahead=(state.scheduled||[]).filter(function(it){ return !it.ready&&!it.parked; });
      if(!due&&ahead.length){
        html+='<button class="srsahead" id="srsahead" data-key="'+esc(keyOf(ahead[0]))+'">'+
          '提前複習一張（'+mmdd(ahead[0].due)+' 才到期）</button>';
      }
      if(!token){
        html+='<div class="srshint">評分需要 <code>serve.py</code> 在跑——'+
          '複習紀錄要寫成檔案，這頁自己寫不了。</div>';
      }
      list.innerHTML=html;
      [].slice.call(list.querySelectorAll('.srsitem')).forEach(function(a){
        a.addEventListener('click',function(e){
          e.preventDefault();
          open(a.dataset.key,modeFor(find(a.dataset.key)));
        });
      });
      var aheadBtn=document.getElementById('srsahead');
      if(aheadBtn) aheadBtn.addEventListener('click',function(){
        open(aheadBtn.dataset.key,'review');
      });
    }

    // The controls under the card. Rebuilt at every stage, so there is never
    // a button on screen that belongs to a step already taken.
    function setStage(s){ panel.dataset.stage=s; }
    function controls(key,html){
      var old=body.querySelector('.stage');
      if(old) old.remove();
      if(!html) return;
      body.insertAdjacentHTML('beforeend','<div class="stage">'+html+'</div>');
      [].slice.call(body.querySelectorAll('.stage button')).forEach(function(b){
        b.addEventListener('click',function(){
          if(b.dataset.j){ jolPick=b.dataset.j; intuition(key); }
          else if(b.dataset.act==='full') full(key);
          else if(b.dataset.act==='toreview') open(key,'review');
          else if(b.dataset.act==='compare') compare(key);
          else if(b.dataset.act==='resolve'||b.dataset.act==='keep') cardWrite(key,b.dataset.act);
          else if(b.dataset.act==='copy') copySelf(key);
          else if(b.dataset.g) grade(key,b.dataset.g);
        });
      });
    }
    function gradeHtml(item){
      if(!token){
        return '<div class="hint">評分需要 <code>serve.py</code> 在跑；現在只能自己對答案。</div>';
      }
      if(!item||!item.preview) return '';
      var labels=[['again','重來'],['hard','困難'],['good','良好'],['easy','簡單']];
      return '<div class="srsbar" id="srsbar"><b>這題答得如何？</b><div class="srsbtns">'+
        labels.map(function(p){
          return '<button data-g="'+p[0]+'">'+p[1]+
                 '<sub>'+days(item.preview[p[0]])+'</sub></button>';
        }).join('')+'</div><span id="srssay"></span></div>';
    }

    // read: the whole card, and a way into review if it happens to be due
    function read(key){
      setStage('');
      var item=find(key);
      if(item&&item.kind==='scheduled'&&item.ready){
        controls(key,'<button class="wide" data-act="toreview">這題今天到期 · 用複習模式作答</button>');
      } else controls(key,'');
    }
    // review, step 1: the question and nothing else. He answers in his head
    // and says how sure he is before anything is shown -- the reveal is the
    // reward for having tried.
    function question(key){
      setStage('question');
      jolPick='';
      controls(key,'<b class="stage-t">先想答案。想到之後，你有多有把握？</b>'+
        '<div class="srsbtns jol">'+
        '<button data-j="sure" class="j-sure">想得起來</button>'+
        '<button data-j="vague" class="j-vague">模糊</button>'+
        '<button data-j="blank" class="j-blank">想不起來</button></div>'+
        '<div class="hint">按了才會看到一句話直覺。</div>');
    }
    // step 2: the one line and the links. Enough to check yourself against;
    // the full answer stays a click away so the line gets read on its own.
    function intuition(key){
      setStage('intuition');
      controls(key,'<button class="wide" data-act="full">看完整解答（卡點＋解答）</button>'+
        gradeHtml(find(key)));
    }
    function full(key){
      setStage('');
      controls(key,gradeHtml(find(key)));
    }

    // half: a card he never fully understood is not graded, it is finished.
    // He writes what he thinks it says, then sees the answer next to it.
    // paper + id, not the key: the key is a page-local identity and a draft
    // written on one page has to be found again from the other.
    function draftKey(key){
      var item=find(key);
      return 'pa-half:'+paperOf(item)+':'+((item&&item.id)||key);
    }
    function half(key){
      setStage('half-explain');
      selfText='';
      controls(key,'<b class="stage-t">先用自己的話說一遍，寫完再對解答。</b>'+
        '<textarea class="self" id="selftext" rows="4" '+
        'placeholder="不用完整，寫到卡住的地方也算。"></textarea>'+
        '<div class="srsbtns"><button data-act="compare">寫好了，比對解答</button></div>'+
        '<span id="srssay"></span>');
      var ta=document.getElementById('selftext');
      try{ var kept=localStorage.getItem(draftKey(key)); if(kept) ta.value=kept; }catch(e){}
      ta.addEventListener('input',function(){
        try{ localStorage.setItem(draftKey(key),ta.value); }catch(e){}
      });
      ta.focus();
    }
    function compare(key){
      var ta=document.getElementById('selftext');
      var text=ta?ta.value.trim():'';
      if(!text){ say('先寫一句再比對。'); return; }
      selfText=text;
      setStage('half-compare');
      var html='<div class="csec csec-mine"><b class="csec-t">你剛剛寫的</b><p>'+esc(text)+'</p></div>';
      if(token){
        html+='<b class="stage-t">對上了嗎？</b><div class="srsbtns half">'+
          '<button class="ok" data-act="resolve">懂了，進排程</button>'+
          '<button data-act="keep">還是半懂，先記下來</button></div>'+
          '<span id="srssay"></span>';
      } else {
        html+='<div class="hint">改狀態要 <code>serve.py</code> 在跑。'+
          '先把你寫的複製起來，貼回對話，Claude 會記進卡片。</div>'+
          '<div class="srsbtns"><button data-act="copy">複製你寫的話</button></div>'+
          '<span id="srssay"></span>';
      }
      controls(key,html);
      // the answer starts at the top; his own words wait at the bottom
      if(cfg.scrollTop) cfg.scrollTop(0);
    }
    function copySelf(key){
      var item=find(key);
      cfg.copy('Q'+((item&&item.id)||key)+' 自己的話：'+selfText,
        function(){ say('已複製'); },
        function(){ say('複製失敗，請手動選取'); });
    }
    function cardWrite(key,action){
      if(busy||!token) return;
      var item=find(key);
      if(!item) return;
      busy=true;
      say('寫入中…');
      fetch('/_pa/card',{
        method:'POST',
        headers:{'Content-Type':'application/json','X-PA-Token':token},
        body:JSON.stringify({paper:paperOf(item),id:item.id,action:action,text:selfText})
      }).then(function(r){ return r.json(); }).then(function(d){
        busy=false;
        if(d.error){ say('沒寫成功：'+d.error); return; }
        try{ localStorage.removeItem(draftKey(key)); }catch(e){}
        var said=d.status==='resolved'
          ?'Q'+item.id+' 已解決，進排程了；你寫的話記在卡片的「自己的話」。'
          :'Q'+item.id+' 還是半懂；你寫的話記在卡片的「自己的話」。';
        if(cfg.after) cfg.after(said,key);
      }).catch(function(){
        busy=false;
        say('沒寫成功，server 可能停了');
      });
    }

    function grade(key,g){
      if(busy||!token) return;
      var bar=document.getElementById('srsbar');
      var item=find(key);
      if(!bar||!item) return;
      busy=true;
      say('記錄中…');
      fetch('/_pa/review',{
        method:'POST',
        headers:{'Content-Type':'application/json','X-PA-Token':token},
        body:JSON.stringify({paper:paperOf(item),id:item.id,grade:g,jol:jolPick})
      }).then(function(r){ return r.json(); }).then(function(d){
        busy=false;
        if(d.error){ say('沒記錄成功：'+d.error); return; }
        say('');
        function settled(){
          draw();
          // Say what was written, then wait. Jumping to the next card the
          // instant a button is pressed hides the one thing worth reading
          // here: when this card comes back, or that his guess and his grade
          // disagree.
          var now=find(key);
          var msg=d.mismatch||('記錄了：'+GRADE_NAMES[g]+
            (now&&now.retry?'，今天再答一次':(now&&now.due?'，下次 '+mmdd(now.due):'')));
          [].slice.call(bar.querySelectorAll('button')).forEach(function(b){
            b.disabled=true; if(b.dataset.g===g) b.classList.add('picked');
          });
          var q=(state&&state.queue)||[];
          var next=null;
          for(var i=0;i<q.length;i++){ if(keyOf(q[i])!==key){ next=q[i]; break; } }
          if(!next&&q.length&&keyOf(q[0])===key) next=q[0];
          var label=!next?'今天做完了，關閉':(keyOf(next)===key?'再答一次這張':'下一張');
          bar.insertAdjacentHTML('beforeend','<div class="srsnext"><span>'+esc(msg)+
            '</span><button id="srsgo">'+label+'</button></div>');
          document.getElementById('srsgo').addEventListener('click',function(){
            if(next) open(keyOf(next),modeFor(next)); else cfg.close();
          });
          // the verdict is the last thing in the panel; make sure it is on screen
          if(cfg.scrollTop) cfg.scrollTop('end');
        }
        // The endpoint answers with the schedule of the card's own paper. On a
        // page showing one paper that is the whole truth; on the shelf it is
        // one paper's slice of it, so that page hands over a refresh instead.
        if(cfg.refresh) cfg.refresh(function(s){ if(s) state=s; settled(); });
        else { state=d.schedule; settled(); }
      }).catch(function(){
        busy=false;
        say('沒記錄成功，server 可能停了');
      });
    }

    function open(key,want){
      var item=find(key);
      var m=want||'read';
      if(item&&item.kind==='half') m='half';
      if(m==='review'&&!(item&&item.kind==='scheduled')) m='read';
      cfg.show(key,item,function(ok){
        // The host bails out on a card it cannot show -- filtered out of the
        // page, or gone from disk. Controls bolted on then would act on the
        // wrong question.
        if(!ok) return;
        current=key;
        mode=m;
        if(m==='review') question(key);
        else if(m==='half') half(key);
        else read(key);
      });
    }

    return {
      draw:draw,
      open:open,
      find:find,
      current:function(){ return current; },
      mode:function(){ return mode; },
      state:function(){ return state; },
      setState:function(s){ state=s; draw(); },
      setToken:function(t){ token=t||''; }
    };
  }

  return {mount:mount, esc:esc, mmdd:mmdd, days:days};
})();
