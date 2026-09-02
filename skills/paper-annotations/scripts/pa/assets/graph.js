
// The note link graph, in three layers.
//
// Why three: the first version put every paper in its own column and drew the
// links between columns. Three papers looked good; ten would need 3000px and
// every line would cross every other. Each layer here is readable because of
// what is *in that layer*, not because the shelf happens to be small:
//
//   1. the shelf   -- a matrix, papers on both axes. No line can cross another.
//   2. two papers  -- one page about one pair. Bounded by that pair.
//   3. one note    -- its immediate neighbours. Bounded by that note's degree,
//                     which is why this is the one embedded in the review page.
//
// Nothing here computes a position. The layout is a table and three columns, so
// the same data draws the same picture on every build.
window.paGraph = (function(){
  var api={};

  function esc(s){
    return String(s==null?'':s).replace(/[&<>"]/g,function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];
    });
  }
  function cut(s,n){
    s=String(s||'');
    return s.length>n?s.slice(0,n-1)+'…':s;
  }
  function key(a,b){ return a+'>'+b; }
  // Note text comes from the catalog, which keeps it as written -- so a point
  // about $\nabla^2\psi$ arrives here as source. The page's own KaTeX pass ran
  // at load, before any of this existed, so anything drawn now asks for its own.
  function mathify(el){
    if(!window.renderMathInElement) return;
    try{
      window.renderMathInElement(el,{
        delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],
        ignoredClasses:['no-math'],throwOnError:false,strict:false});
    }catch(e){}
  }

  // ---- shared bits -------------------------------------------------------

  function paperOf(data,slug){
    for(var i=0;i<data.papers.length;i++){ if(data.papers[i].slug===slug) return data.papers[i]; }
    return {slug:slug,short:slug,title:slug,notes:0};
  }
  // Carries data-note so that wherever there is a panel to open it in, a
  // reference is also the way into that note's own neighbourhood. Where there
  // is not -- inside a card -- nothing is bound to it and it stays plain text.
  function noteRef(data,id){
    var n=data.notes[id];
    if(!n) return esc(id);
    return '<span data-note="'+esc(id)+'">'+esc(paperOf(data,n.slug).short)+
      ' · '+n.kind+n.id+'</span>';
  }
  function noteText(data,id){
    var n=data.notes[id];
    return n?esc(cut(n.text,150)):'';
  }
  // Forward label on the note that declared it, reverse label on the target --
  // one link, read from either end, stored once.
  function typeLabel(data,type,reverse){
    var pair=(data.types||{})[type]||[type,type];
    return reverse?pair[1]:pair[0];
  }
  function linkRow(data,edge,from){
    var other=from===edge.from?edge.to:edge.from;
    var reverse=from!==edge.from;
    return '<div class="glink">'+
      '<span class="gtype '+esc(edge.type)+'">'+esc(typeLabel(data,edge.type,reverse))+'</span>'+
      '<span class="gnote">'+noteText(data,other)+'</span>'+
      '<span class="gref">'+noteRef(data,other)+'</span></div>';
  }

  // ---- layer 1: the shelf matrix ----------------------------------------

  api.matrix=function(host,data){
    var chosen='';
    var citeSet={};
    (data.cites||[]).forEach(function(c){ citeSet[key(c.from,c.to)]=c; });

    function shown(){
      if(!chosen) return data.papers;
      return data.papers.filter(function(p){ return (p.topics||[]).indexOf(chosen)>=0; });
    }
    function cell(a,b){
      var pair=data.pairs[key(a.slug,b.slug)];
      if(a.slug===b.slug){
        // The diagonal carries the paper's own size, so "this row is busy
        // because I wrote a lot about it" is visible instead of normalised away.
        var own=pair?pair.links:0;
        return '<button class="gcell self" data-a="'+esc(a.slug)+'" data-b="'+esc(b.slug)+'" '+
          'title="'+esc(a.title)+'：筆記 '+a.notes+' 則'+(own?('，其中 '+own+' 條線在自己內部'):'')+'">'+
          '<span class="gb">'+a.notes+'</span>'+
          (own?'<span class="gx">'+own+'</span>':'')+'</button>';
      }
      var cited=!!citeSet[key(a.slug,b.slug)];
      if(!pair){
        if(!cited) return '<span class="gcell empty"></span>';
        return '<button class="gcell gap" data-a="'+esc(a.slug)+'" data-b="'+esc(b.slug)+'" '+
          'title="'+esc(a.short)+' 引用了 '+esc(b.short)+'，但你一條線都還沒接">'+
          '<span class="gx">引用</span></button>';
      }
      return '<button class="gcell'+(cited&&!pair.links?' gap':'')+'" '+
        'data-a="'+esc(a.slug)+'" data-b="'+esc(b.slug)+'" '+
        'title="'+esc(a.short)+' → '+esc(b.short)+'：廣度 '+pair.breadth+
        '（'+pair.src.length+' 則對 '+pair.dst.length+' 則），共 '+pair.links+' 條線">'+
        (pair.contra?'<i class="gc"></i>':'')+
        '<span class="gb">'+pair.breadth+'</span>'+
        '<span class="gx">'+pair.links+'</span></button>';
    }

    function draw(){
      var list=shown();
      var topics={};
      data.papers.forEach(function(p){ (p.topics||[]).forEach(function(t){ topics[t]=(topics[t]||0)+1; }); });
      var chips='<span class="gfilter">分類</span>'+
        '<button class="gchip'+(chosen?'':' on')+'" data-topic="">全部 '+data.papers.length+'</button>'+
        Object.keys(topics).sort().map(function(t){
          return '<button class="gchip'+(chosen===t?' on':'')+'" data-topic="'+esc(t)+'">'+
            esc((data.topicNames||{})[t]||t)+' '+topics[t]+'</button>';
        }).join('');

      var html='<div class="gwrap"><div class="gtop">'+chips+'</div>';
      if(!list.length){
        html+='<div class="qempty">這個分類底下還沒有論文。</div></div>';
        host.innerHTML=html;
        mathify(host);
        wire();
        return;
      }
      html+='<div class="gscroll"><table class="gmx"><thead><tr>'+
        '<th class="corner">從 ↓ ／ 到 →</th>'+
        list.map(function(p){ return '<th><span title="'+esc(p.title)+'">'+esc(p.short)+'</span></th>'; }).join('')+
        '</tr></thead><tbody>'+
        list.map(function(a){
          return '<tr><th title="'+esc(a.title)+'">'+esc(a.short)+'</th>'+
            list.map(function(b){ return '<td>'+cell(a,b)+'</td>'; }).join('')+'</tr>';
        }).join('')+
        '</tbody></table></div>';
      html+='<div class="glegend">'+
        '格子裡的大字是<b>廣度</b>：兩邊各有幾則不同的筆記真的參與，取比較窄的那一邊。'+
        '小字是原始<b>線條數</b>。四條線可能是四個關係，也可能是同一則筆記發出四條——'+
        '用條數看這兩種一模一樣，用廣度就分得出來。<br>'+
        '<span class="gdot"></span> 這一格裡有<b>牴觸</b>。'+
        '<span class="gdash"></span> <b>引用了卻還沒接線</b>：機械上有關係，你還沒寫下判斷。'+
        '對角線是那一篇自己的<b>筆記總數</b>，所以「這一列本來就筆記多」看得見。'+
        '</div>';
      html+=todo(list);
      html+='<div id="gpair" hidden></div></div>';
      host.innerHTML=html;
      mathify(host);
      wire();
    }

    // The two lists a round can actually act on. Links do not appear by
    // themselves -- these are where they come from.
    function todo(list){
      var live={};
      list.forEach(function(p){ live[p.slug]=true; });
      var gaps=(data.cites||[]).filter(function(c){
        var pair=data.pairs[key(c.from,c.to)];
        return live[c.from]&&live[c.to]&&(!pair||!pair.links);
      });
      var lonely=[];
      var touched={};
      (data.edges||[]).forEach(function(e){ touched[e.from]=true; touched[e.to]=true; });
      Object.keys(data.notes).sort().forEach(function(id){
        if(touched[id]||!live[data.notes[id].slug]) return;
        lonely.push(id);
      });
      return '<div class="gtodo">'+
        '<div class="gbox"><h3>引用了，但還沒接線（'+gaps.length+'）</h3>'+
        (gaps.length?'<ul>'+gaps.slice(0,12).map(function(c){
          return '<li>'+esc(paperOf(data,c.from).short)+' → '+esc(paperOf(data,c.to).short)+'</li>';
        }).join('')+'</ul>'+(gaps.length>12?'<div class="gmore">還有 '+(gaps.length-12)+' 對</div>':'')
          :'<div class="qempty">沒有這種空洞。</div>')+'</div>'+
        '<div class="gbox"><h3>還沒接過任何線的筆記（'+lonely.length+'）</h3>'+
        (lonely.length?'<ul>'+lonely.slice(0,12).map(function(id){
          return '<li>'+noteRef(data,id)+' — '+noteText(data,id)+'</li>';
        }).join('')+'</ul>'+(lonely.length>12?'<div class="gmore">還有 '+(lonely.length-12)+' 則</div>':'')
          :'<div class="qempty">每一則都接過線了。</div>')+'</div>'+
        '</div>';
    }

    function wire(){
      [].slice.call(host.querySelectorAll('.gchip')).forEach(function(b){
        b.addEventListener('click',function(){ chosen=b.dataset.topic||''; draw(); });
      });
      [].slice.call(host.querySelectorAll('.gcell[data-a]')).forEach(function(b){
        b.addEventListener('click',function(){ pair(b.dataset.a,b.dataset.b); });
      });
    }
    // Delegated, and bound once: the references live inside the panel this
    // handler writes into, so per-element binding would go stale on every draw
    // and re-binding in draw() would stack a new handler each time.
    host.addEventListener('click',function(ev){
      var el=ev.target.closest?ev.target.closest('[data-note]'):null;
      if(el&&data.notes[el.dataset.note]) one(el.dataset.note);
    });

    // Layer 3, reachable from here: one note's own neighbourhood, in the same
    // panel the pair view uses -- two panels open at once is two things to close.
    function one(id){
      var box=host.querySelector('#gpair');
      if(!box) return;
      var n=data.notes[id];
      box.innerHTML='<div class="ghead"><h3>'+noteRef(data,id)+'</h3>'+
        '<button class="gclose">收起</button></div>'+
        '<div class="gquote">'+noteText(data,id)+
        (n.where?'<br><b>'+esc(n.where)+'</b>':'')+'</div>'+
        '<div class="gsec"><div id="gone"></div></div>';
      api.ego(box.querySelector('#gone'),data,id);
      var inner=box.querySelector('#gone .gego');
      if(inner) inner.classList.add('plain');
      box.hidden=false;
      box.querySelector('.gclose').addEventListener('click',function(){ box.hidden=true; });
      mathify(box);
      box.scrollIntoView({block:'nearest'});
    }

    // ---- layer 2: one pair of papers ------------------------------------
    function pair(a,b){
      var box=host.querySelector('#gpair');
      if(!box) return;
      var A=paperOf(data,a), B=paperOf(data,b);
      var row=data.pairs[key(a,b)];
      var back=a===b?null:data.pairs[key(b,a)];
      var html='<div class="ghead"><h3>'+esc(A.short)+(a===b?'（自己內部）':' → '+esc(B.short))+'</h3>'+
        '<button class="gclose">收起</button></div>';

      // 1. what is mechanically true, before anything anyone judged
      var cite=[];
      (data.cites||[]).forEach(function(c){
        if((c.from===a&&c.to===b)||(c.from===b&&c.to===a)) cite.push(c);
      });
      html+='<div class="gsec"><h4>機械事實（參考文獻標題比對）</h4>';
      if(!cite.length&&a!==b) html+='<div class="qempty">這兩篇沒有互相引用，或參考文獻還沒抽出來。</div>';
      cite.forEach(function(c){
        html+='<div class="gquote"><b>'+esc(paperOf(data,c.from).short)+'</b> 引用了 <b>'+
          esc(paperOf(data,c.to).short)+'</b>';
        (c.sites||[]).forEach(function(s){
          html+='<br><code>'+esc(s.file)+'</code><br>「'+esc(s.text)+'」';
        });
        html+='</div>';
      });
      html+='</div>';

      // 2. the links themselves, with the two inflation warnings when they apply
      var edges=(data.edges||[]).filter(function(e){
        return data.notes[e.from].slug===a&&data.notes[e.to].slug===b;
      });
      html+='<div class="gsec"><h4>你接過的線（'+edges.length+' 條，廣度 '+
        (row?row.breadth:0)+'）</h4>';
      if(row&&row.fan>1&&row.breadth<=1){
        html+='<div class="gwarn">其中 '+row.fan+' 條都從同一則發出（'+noteRef(data,row.fanof)+
          '），所以廣度只有 '+row.breadth+'：那是一個關係被寫成 '+row.fan+
          ' 條，不是 '+row.fan+' 個關係。</div>';
      }
      if(row&&row.links>1&&row.secs.length===1){
        html+='<div class="gwarn">這一邊的筆記全部落在「'+esc(row.secs[0])+
          '」：這通常代表你在那一節卡比較多，不是兩篇整體很像。</div>';
      }
      if(!edges.length) html+='<div class="qempty">還沒有從這一邊接出去的線。</div>';
      edges.forEach(function(e){
        html+='<div class="glink"><span class="gtype '+esc(e.type)+'">'+
          esc(typeLabel(data,e.type,false))+'</span>'+
          '<span class="gnote">'+noteText(data,e.from)+'</span>'+
          '<span class="gref">'+noteRef(data,e.from)+' → '+noteRef(data,e.to)+'</span></div>'+
          '<div class="gquote">→ '+noteText(data,e.to)+'</div>';
      });
      html+='</div>';

      if(back&&back.links){
        html+='<div class="gsec"><h4>反方向（'+esc(B.short)+' → '+esc(A.short)+
          '，'+back.links+' 條）</h4>';
        (data.edges||[]).filter(function(e){
          return data.notes[e.from].slug===b&&data.notes[e.to].slug===a;
        }).forEach(function(e){
          html+=linkRow(data,e,e.from);
        });
        html+='</div>';
      }

      // 3. candidates: same tag, no line. The tool puts them in front of him
      //    and stops there -- it does not decide that two notes are related.
      if(a!==b){
        var linked={};
        (data.edges||[]).forEach(function(e){ linked[e.from+'|'+e.to]=true; linked[e.to+'|'+e.from]=true; });
        var cand=[];
        Object.keys(data.notes).sort().forEach(function(x){
          if(data.notes[x].slug!==a) return;
          Object.keys(data.notes).sort().forEach(function(y){
            if(data.notes[y].slug!==b||linked[x+'|'+y]) return;
            var shared=(data.notes[x].tags||[]).filter(function(t){
              return (data.notes[y].tags||[]).indexOf(t)>=0; });
            if(shared.length) cand.push({x:x,y:y,tags:shared});
          });
        });
        // Sorted by how many tags they share, because one shared tag between
        // two papers on the same subject is nearly everything and says little.
        cand.sort(function(p,q){
          return q.tags.length-p.tags.length||(p.x<q.x?-1:p.x>q.x?1:(p.y<q.y?-1:1));
        });
        html+='<div class="gsec"><h4>共用標籤但還沒接（'+cand.length+'）</h4>';
        if(!cand.length) html+='<div class="qempty">沒有共用標籤的組合。</div>';
        cand.slice(0,8).forEach(function(c){
          html+='<div class="glink"><span class="gtype">'+esc(c.tags.join('、'))+'</span>'+
            '<span class="gnote">'+noteText(data,c.x)+'<br>'+noteText(data,c.y)+'</span>'+
            '<span class="gref">'+noteRef(data,c.x)+' · '+noteRef(data,c.y)+'</span></div>';
        });
        if(cand.length>8){
          html+='<div class="gmore">還有 '+(cand.length-8)+
            ' 組沒列出來——上面是共用標籤最多的幾組。這只是候選，接不接由你判斷。</div>';
        }
        html+='</div>';
      }

      box.innerHTML=html;
      mathify(box);
      box.hidden=false;
      box.querySelector('.gclose').addEventListener('click',function(){ box.hidden=true; });
      box.scrollIntoView({block:'nearest'});
    }

    draw();
  };

  // ---- layer 3: one note's neighbours ------------------------------------
  //
  // Two shapes, because a card in the review page already prints its own links
  // -- with a 先想 prompt in front of them, which is the point of that flow.
  // Repeating them underneath would be noise, so inside a card this draws only
  // the ring the card cannot show: where those neighbours go next.
  //
  //   ring 1 (the shelf): 指向這一則 / 這一則指向, the full neighbourhood.
  //   ring 2 (a card):    再往外一跳, grouped by the neighbour it goes through.
  //
  // Either way the size follows this note's own degree, never the shelf's.

  function ring1(data,id,limit){
    var into=(data.edges||[]).filter(function(e){ return e.to===id; });
    var outof=(data.edges||[]).filter(function(e){ return e.from===id; });
    if(!into.length&&!outof.length){
      return '<div class="qempty">這一則還沒接過任何線。'+
        '想到它跟別篇的哪一句對得上，就在回合裡說。</div>';
    }
    function side(title,list,dir){
      var html='<div class="gside"><b>'+title+'（'+list.length+'）</b>';
      list.slice(0,limit).forEach(function(e){
        var other=dir==='in'?e.from:e.to;
        html+='<div class="glink"><span class="gtype '+esc(e.type)+'">'+
          esc(typeLabel(data,e.type,dir==='in'))+'</span>'+
          '<span class="gnote">'+noteText(data,other)+'</span>'+
          '<span class="gref">'+noteRef(data,other)+'</span></div>';
      });
      if(list.length>limit){
        html+='<div class="gmore">還有 '+(list.length-limit)+
          ' 條沒畫出來——這一則接得太多了，用型別篩過再看。</div>';
      }
      return html+'</div>';
    }
    return (into.length?side('指向這一則',into,'in'):'')+
           (outof.length?side('這一則指向',outof,'out'):'');
  }

  function ring2(data,id,limit){
    var first=[];
    (data.edges||[]).forEach(function(e){
      var other=e.to===id?e.from:(e.from===id?e.to:'');
      if(other&&first.indexOf(other)<0) first.push(other);
    });
    var html='';
    first.sort().forEach(function(via){
      var more=(data.edges||[]).filter(function(e){
        var other=e.from===via?e.to:(e.to===via?e.from:'');
        return other&&other!==id&&first.indexOf(other)<0;
      });
      if(!more.length) return;
      html+='<div class="gside"><b>經過 '+noteRef(data,via)+'（'+more.length+'）</b>';
      more.slice(0,limit).forEach(function(e){
        var other=e.from===via?e.to:e.from;
        html+='<div class="glink"><span class="gtype '+esc(e.type)+'">'+
          esc(typeLabel(data,e.type,e.to===via))+'</span>'+
          '<span class="gnote">'+noteText(data,other)+'</span>'+
          '<span class="gref">'+noteRef(data,other)+'</span></div>';
      });
      if(more.length>limit) html+='<div class="gmore">還有 '+(more.length-limit)+' 條</div>';
      html+='</div>';
    });
    return html;
  }

  api.ego=function(host,data,id,opts){
    host.innerHTML='';
    if(!data||!data.notes||!data.notes[id]) return;
    var limit=data.limit||10;
    var second=(opts||{}).ring===2;
    var body=second?ring2(data,id,limit):ring1(data,id,limit);
    // Nothing beyond the first ring is not worth a heading of its own; the
    // card already showed the first ring.
    if(second&&!body) return;
    host.innerHTML='<div class="gego"><h4>'+(second?'再往外一跳':'連結')+'</h4>'+
      (second?'<div class="ghint">這一則的鄰居又接到哪裡去。第一圈在上面的連結列裡。</div>':'')+
      body+'</div>';
    mathify(host);
  };

  return api;
})();
