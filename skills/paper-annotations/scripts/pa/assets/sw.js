/* The shelf's service worker: enough of an app to open from the home screen,
   and nothing more.

   What it caches is the SHELL -- the shelf page itself and its icons -- so the
   app opens instantly and still opens when the computer is off. What it never
   caches is DATA: the queue, a card, the token. Those come from the computer
   or they do not come at all.

   That line is the whole design. A cached queue would be a second copy of the
   schedule living on the phone, and the moment it existed the reader could
   answer a card that is no longer due, or miss one that became due -- and
   grading it would still be impossible, because only the computer can append
   to notes/reviews/ (docs/adr/0003). An app that shows yesterday's cards and
   cannot record today's answers is worse than one that says it is offline. */
var SHELL = 'pa-shell-v1';
// Served by serve.py, so everything lives under /_pa/. These four are shell;
// every other /_pa/ path is data and goes to the network or nowhere.
var SHELL_PATHS = ['/_pa/shelf', '/_pa/sw.js', '/_pa/manifest.webmanifest'];

function isShell(url) {
  if (url.pathname.indexOf('/_pa/icon-') === 0) return true;
  if (SHELL_PATHS.indexOf(url.pathname) >= 0) return true;
  // A paper's own review page is a whole document; it is shell too, and the
  // schedule inside it is fetched separately and will simply fail offline.
  return url.pathname.indexOf('/p/') === 0;
}

self.addEventListener('install', function () {
  self.skipWaiting();
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (names) {
      return Promise.all(names.map(function (name) {
        return name === SHELL ? null : caches.delete(name);
      }));
    }).then(function () {
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', function (event) {
  var request = event.request;
  if (request.method !== 'GET') return;
  var url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (!isShell(url)) return; // data: the network answers it, or nobody does

  event.respondWith(
    // Network first: the computer's copy is always the right one, and the
    // cache exists for the case where there is no answer at all.
    fetch(request).then(function (response) {
      // A proxy in front of the server (tailscale serve) is still up when the
      // server behind it is not, and it answers with its own 502. That is the
      // computer being off as far as the reader is concerned -- the same
      // case as no answer at all, so it takes the same way out.
      if (response && response.status >= 502 && response.status <= 504) {
        throw new Error('upstream ' + response.status);
      }
      // 200 only -- the "needs a key" page is a 403 and must never be kept,
      // or a cookie that expired once would be remembered as the shelf.
      if (response && response.status === 200 && response.type === 'basic') {
        var copy = response.clone();
        caches.open(SHELL).then(function (cache) {
          cache.put(request, copy);
        });
      }
      return response;
    }).catch(function () {
      return caches.match(request).then(function (hit) {
        if (hit) return hit;
        return new Response(
          '<!doctype html><meta charset="utf-8">' +
          '<title>連不到電腦</title>' +
          '<style>body{font:15px/1.8 system-ui,sans-serif;margin:14vh auto;' +
          'max-width:30em;padding:0 22px;color:#1c1f24;background:#fcfcfa}</style>' +
          '<h1>連不到電腦</h1>' +
          '<p>複習紀錄只有跑 server 的那台電腦寫得進去，所以離線時看不到今天的卡，' +
          '也評不了分。</p><p>電腦開著、Tailscale 連著，重新整理就會回來。</p>',
          { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
        );
      });
    })
  );
});
