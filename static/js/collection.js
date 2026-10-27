// Version B208 (F12 rev 2): no content change; ?v bumped B207->B208 in lockstep.
// Version B207 (F12): NEW FILE. Dream Cards prototype: card store + personal collection ("My World").
//   Loaded only by collection.html (after i18n.js, which supplies the language and the CSRF header).
//   Talks to GET /api/collection, POST /api/collection/buy and POST /api/collection/arrange.
//   Texts are a self-contained 4-language map (same approach as e2ee.js / SUPPORT_MSGS), so i18n.js
//   needed no new keys. Everything the member typed is shown with textContent (never as HTML).
(function () {
    'use strict';

    var MSG = {
        title:      { en: 'Dream Cards', he: 'כרטיסי חלומות', ar: 'بطاقات الأحلام', ru: 'Карточки мечты' },
        sub:        { en: 'Turn the points from your daily check-ins into cards for the things that inspire you, then build a world that is yours.',
                      he: 'הפכו את הנקודות מהצ׳ק־אין היומי לכרטיסים של מה שמעורר בכם השראה, ובנו עולם שהוא רק שלכם.',
                      ar: 'حوّلوا نقاط تسجيل الحضور اليومي إلى بطاقات لما يلهمكم، وابنوا عالمًا خاصًا بكم.',
                      ru: 'Превращайте очки за ежедневные отметки в карточки того, что вас вдохновляет, и стройте свой собственный мир.' },
        points:     { en: 'points', he: 'נקודות', ar: 'نقطة', ru: 'очков' },
        tab_store:  { en: 'Store', he: 'החנות', ar: 'المتجر', ru: 'Магазин' },
        tab_world:  { en: 'My World', he: 'העולם שלי', ar: 'عالمي', ru: 'Мой мир' },
        all:        { en: 'All', he: 'הכול', ar: 'الكل', ru: 'Все' },
        cat_luxury: { en: 'Dream Life', he: 'חיי חלום', ar: 'حياة الأحلام', ru: 'Жизнь мечты' },
        cat_sky:    { en: 'Sky & Strength', he: 'שמיים ועוצמה', ar: 'السماء والقوة', ru: 'Небо и сила' },
        cat_travel: { en: 'Adventure', he: 'הרפתקה', ar: 'مغامرة', ru: 'Приключения' },
        cat_creative: { en: 'Creativity', he: 'יצירה', ar: 'إبداع', ru: 'Творчество' },
        cat_learning: { en: 'Learning', he: 'למידה', ar: 'تعلّم', ru: 'Знания' },
        cat_giving: { en: 'Giving Back', he: 'נתינה', ar: 'العطاء', ru: 'Отдавать другим' },
        v_classic:  { en: 'Classic', he: 'קלאסי', ar: 'كلاسيكي', ru: 'Классика' },
        v_aurora:   { en: 'Aurora', he: 'זוהר', ar: 'شفق', ru: 'Сияние' },
        v_gold:     { en: 'Gold', he: 'זהב', ar: 'ذهبي', ru: 'Золото' },
        confirm:    { en: 'Confirm · {n}', he: 'אישור · {n}', ar: 'تأكيد · {n}', ru: 'Да · {n}' },
        owned:      { en: '✓ Yours', he: '✓ שלך', ar: '✓ لك', ru: '✓ Ваша' },
        needs_classic: { en: 'Collect the classic card first to unlock this variation.', he: 'אספו קודם את הכרטיס הקלאסי כדי לפתוח את הגרסה הזו.',
                      ar: 'اجمعوا البطاقة الكلاسيكية أولًا لفتح هذا الإصدار.', ru: 'Сначала соберите классическую карточку, чтобы открыть этот вариант.' },
        not_enough: { en: '{n} more points needed. Your daily check-in earns 15 to 20.', he: 'חסרות עוד {n} נקודות. הצ׳ק־אין היומי מזכה ב־15 עד 20.',
                      ar: 'تحتاجون إلى {n} نقطة إضافية. يمنحكم تسجيل الحضور اليومي من 15 إلى 20.', ru: 'Нужно ещё {n} очков. Ежедневная отметка даёт от 15 до 20.' },
        collectors1:{ en: 'In 1 member’s world', he: 'בעולם של חבר אחד', ar: 'في عالم عضو واحد', ru: 'В мире 1 участника' },
        collectors: { en: 'In {n} members’ worlds', he: 'בעולמות של {n} חברים', ar: 'في عوالم {n} أعضاء', ru: 'В мирах {n} участников' },
        first:      { en: 'Be the first to collect it', he: 'היו הראשונים לאסוף אותו', ar: 'كونوا أول من يجمعها', ru: 'Станьте первым, кто её соберёт' },
        added:      { en: 'Added to your world ✨', he: 'נוסף לעולם שלך ✨', ar: 'أُضيفت إلى عالمك ✨', ru: 'Добавлено в ваш мир ✨' },
        earn_hint:  { en: 'Points come from your daily check-in (15, plus 5 more when you keep a streak).', he: 'נקודות מגיעות מהצ׳ק־אין היומי (15, ועוד 5 כשאתם שומרים על רצף).',
                      ar: 'تأتي النقاط من تسجيل الحضور اليومي (15، و5 إضافية عند المواظبة).', ru: 'Очки начисляются за ежедневную отметку (15 и ещё 5 за серию).' },
        earn_link:  { en: 'Do today’s check-in', he: 'לצ׳ק־אין של היום', ar: 'سجّلوا حضور اليوم', ru: 'Отметиться сегодня' },
        empty:      { en: 'Your world is still empty. Pick your first card in the store and give it a meaning of your own.',
                      he: 'העולם שלך עדיין ריק. בחרו את הכרטיס הראשון בחנות ותנו לו משמעות משלכם.',
                      ar: 'عالمك لا يزال فارغًا. اختاروا بطاقتكم الأولى من المتجر وامنحوها معنى خاصًا بكم.',
                      ru: 'Ваш мир пока пуст. Выберите первую карточку в магазине и придайте ей свой смысл.' },
        go_store:   { en: 'Open the store', he: 'לחנות', ar: 'افتحوا المتجر', ru: 'В магазин' },
        shelf_main: { en: 'My first shelf', he: 'המדף הראשון שלי', ar: 'رفّي الأول', ru: 'Моя первая полка' },
        shelf_label:{ en: 'Shelf', he: 'מדף', ar: 'الرف', ru: 'Полка' },
        shelf_new:  { en: '+ New shelf…', he: '+ מדף חדש…', ar: '+ رف جديد…', ru: '+ Новая полка…' },
        shelf_ph:   { en: 'Name your shelf (e.g. Big dreams)', he: 'שם למדף (למשל: חלומות גדולים)', ar: 'سمّوا الرف (مثلًا: أحلام كبيرة)', ru: 'Название полки (например, Большие мечты)' },
        move:       { en: 'Move', he: 'העברה', ar: 'نقل', ru: 'Переместить' },
        note_ph:    { en: 'What does this card mean to you?', he: 'מה הכרטיס הזה אומר לך?', ar: 'ماذا تعني لك هذه البطاقة؟', ru: 'Что для вас значит эта карточка?' },
        saved:      { en: 'Saved', he: 'נשמר', ar: 'تم الحفظ', ru: 'Сохранено' },
        earlier:    { en: 'Move earlier', he: 'הזזה קדימה', ar: 'نقل إلى الأمام', ru: 'Переместить раньше' },
        later:      { en: 'Move later', he: 'הזזה אחורה', ar: 'نقل إلى الخلف', ru: 'Переместить позже' },
        err:        { en: 'Something went wrong. Please try again.', he: 'משהו השתבש. נסו שוב.', ar: 'حدث خطأ ما. حاولوا مرة أخرى.', ru: 'Что-то пошло не так. Попробуйте ещё раз.' },
        cards_1:    { en: '1 card', he: 'כרטיס אחד', ar: 'بطاقة واحدة', ru: 'Карточек: 1' },
        cards_n:    { en: '{n} cards', he: '{n} כרטיסים', ar: '{n} بطاقات', ru: 'Карточек: {n}' }
    };
    function lang() {
        try { if (window.i18n && window.i18n.getCurrentLanguage) { var l = window.i18n.getCurrentLanguage(); if (MSG.title[l]) return l; } } catch (_) {}
        try { var s = localStorage.getItem('selectedLanguage'); if (MSG.title[s]) return s; } catch (_) {}
        return 'en';
    }
    function T(k, n) { var m = MSG[k]; var s = m ? (m[lang()] || m.en) : k; return n === undefined ? s : s.replace('{n}', n); }
    function $(id) { return document.getElementById(id); }
    function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; }

    var S = { data: null, tab: 'store', cat: 'all', confirming: null, busy: false };
    try { if (sessionStorage.getItem('ts_dc_tab') === 'world') S.tab = 'world'; } catch (_) {}

    var toastTimer = null;
    function toast(text, isErr) {
        var t = document.querySelector('.toast');
        if (!t) { t = el('div', 'toast'); t.setAttribute('role', 'status'); document.body.appendChild(t); }
        t.className = 'toast' + (isErr ? ' err' : ''); t.textContent = text;
        clearTimeout(toastTimer); toastTimer = setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 3200);
    }

    function api(url, body) {
        var opt = { credentials: 'include', headers: { 'Content-Type': 'application/json' } };
        if (body) { opt.method = 'POST'; opt.body = JSON.stringify(body); }
        return fetch(url, opt).then(function (r) {
            if (r.status === 401) { window.location.href = '/'; throw new Error('auth'); }
            return r.json().catch(function () { return {}; }).then(function (d) { d.__status = r.status; return d; });
        });
    }
    function cardById(id) { var c = (S.data && S.data.cards) || []; for (var i = 0; i < c.length; i++) if (c[i].id === id) return c[i]; return null; }
    function owns(cardId, v) { return (S.data.items || []).some(function (i) { return i.card_id === cardId && i.variant === v; }); }
    function cardName(c) { return (c.names && (c.names[lang()] || c.names.en)) || c.id; }

    // ------------------------------------------------------------------ chrome (title, balance, tabs)
    function renderChrome() {
        var L = lang(), rtl = (L === 'he' || L === 'ar');
        document.documentElement.setAttribute('dir', rtl ? 'rtl' : 'ltr');
        document.documentElement.setAttribute('lang', L);
        $('dcTitle').textContent = T('title');
        $('dcSub').textContent = T('sub');
        document.title = T('title') + ' - TheraSocial';
        $('dcLang').value = L;
        $('dcBack').textContent = (rtl ? '→ ' : '← ') + 'TheraSocial';
        var b = $('dcBalance'); b.textContent = '';
        b.appendChild(document.createTextNode('✨ ' + (S.data ? S.data.balance : '…')));
        b.appendChild(el('small', null, T('points')));
        $('dcTabStore').textContent = T('tab_store');
        $('dcTabWorld').textContent = T('tab_world') + (S.data && S.data.items.length ? ' (' + S.data.items.length + ')' : '');
        $('dcTabStore').setAttribute('aria-selected', S.tab === 'store' ? 'true' : 'false');
        $('dcTabWorld').setAttribute('aria-selected', S.tab === 'world' ? 'true' : 'false');
    }

    function art(c, variant) {
        var a = el('div', 'art c-' + c.category);
        a.appendChild(el('span', 'cat', T('cat_' + c.category)));
        var e = el('span', null, c.emoji); e.setAttribute('aria-hidden', 'true'); a.appendChild(e);
        return a;
    }

    // ------------------------------------------------------------------ store
    function renderStore(view) {
        var hint = el('div', 'hint');
        hint.appendChild(document.createTextNode(T('earn_hint') + ' '));
        var a = el('a', null, T('earn_link')); a.href = '/parameters'; hint.appendChild(a);
        view.appendChild(hint);

        var chips = el('div', 'chips');
        ['all', 'luxury', 'sky', 'travel', 'creative', 'learning', 'giving'].forEach(function (k) {
            var ch = el('button', 'chip', k === 'all' ? T('all') : T('cat_' + k)); ch.type = 'button';
            ch.setAttribute('aria-pressed', S.cat === k ? 'true' : 'false');
            ch.addEventListener('click', function () { S.cat = k; S.confirming = null; render(); });
            chips.appendChild(ch);
        });
        view.appendChild(chips);

        var grid = el('div', 'grid');
        S.data.cards.forEach(function (c) {
            if (S.cat !== 'all' && c.category !== S.cat) return;
            var best = owns(c.id, 'gold') ? 'gold' : owns(c.id, 'aurora') ? 'aurora' : 'classic';
            var card = el('div', 'card' + (owns(c.id, 'classic') && best !== 'classic' ? ' v-' + best : ''));
            card.appendChild(art(c, best));
            var body = el('div', 'body');
            body.appendChild(el('div', 'name', cardName(c)));
            body.appendChild(el('div', 'meta', c.collectors > 1 ? T('collectors', c.collectors) : c.collectors === 1 ? T('collectors1') : T('first')));
            var vars = el('div', 'vars');
            c.variants.forEach(function (v) {
                var key = c.id + ':' + v.id, btn = el('button', 'vbtn'); btn.type = 'button';
                var label = T('v_' + v.id);
                if (owns(c.id, v.id)) { btn.className += ' owned'; btn.textContent = T('owned') + (v.id !== 'classic' ? ' · ' + label : ''); btn.disabled = true; }
                else if (v.id !== 'classic' && !owns(c.id, 'classic')) { btn.textContent = '🔒 ' + label; btn.title = T('needs_classic'); btn.addEventListener('click', function () { toast(T('needs_classic')); }); }
                else if (S.confirming === key) { btn.className += ' confirm'; btn.textContent = T('confirm', v.price); btn.addEventListener('click', function () { buy(c, v); }); }
                else {
                    if (v.id === 'classic') btn.className += ' primary';
                    btn.textContent = (v.id === 'classic' ? '' : label + ' · ') + v.price + ' ✨';
                    btn.addEventListener('click', function () {
                        if (S.data.balance < v.price) { toast(T('not_enough', v.price - S.data.balance)); return; }
                        S.confirming = key; render();
                    });
                }
                if (S.busy) btn.disabled = true;
                vars.appendChild(btn);
            });
            body.appendChild(vars);
            card.appendChild(body);
            grid.appendChild(card);
        });
        view.appendChild(grid);
    }

    function buy(c, v) {
        if (S.busy) return;
        S.busy = true; render();
        api('/api/collection/buy', { card_id: c.id, variant: v.id }).then(function (d) {
            S.busy = false; S.confirming = null;
            if (d.__status === 200 && d.cards) { S.data = d; toast(T('added')); }
            else if (d.code === 'not_enough') toast(T('not_enough', Math.max(1, v.price - S.data.balance)), true);
            else if (d.code === 'needs_classic') toast(T('needs_classic'), true);
            else if (d.code === 'owned') { toast(T('owned')); return load(); }
            else toast(T('err'), true);
            render();
        }).catch(function (e) { S.busy = false; if (e && e.message !== 'auth') { toast(T('err'), true); render(); } });
    }

    // ------------------------------------------------------------------ my world
    function shelves() {
        var names = [];
        S.data.items.forEach(function (i) { if (names.indexOf(i.shelf) === -1) names.push(i.shelf); });
        names.sort(function (a, b) { return a === '' ? -1 : b === '' ? 1 : a.localeCompare(b); });
        return names;
    }
    function shelfLabel(s) { return s === '' ? T('shelf_main') : s; }

    function save(changes, quiet) {
        return api('/api/collection/arrange', { items: changes }).then(function (d) {
            if (d.__status === 200 && d.items) { S.data = d; if (!quiet) toast(T('saved')); render(); }
            else toast(T('err'), true);
        }).catch(function (e) { if (e && e.message !== 'auth') toast(T('err'), true); });
    }
    // A note save only updates the data and shows a toast: no re-render, so typing in another card is never wiped.
    function saveNote(it, text) {
        return api('/api/collection/arrange', { items: [{ id: it.id, note: text }] }).then(function (d) {
            if (d.__status === 200 && d.items) { S.data.items.forEach(function (i) { if (i.id === it.id) i.note = text.trim().slice(0, 140); }); S.data.balance = d.balance; toast(T('saved')); }
            else toast(T('err'), true);
        }).catch(function (e) { if (e && e.message !== 'auth') toast(T('err'), true); });
    }
    function renumber(shelf, ordered) { return ordered.map(function (it, idx) { return { id: it.id, shelf: shelf, position: idx }; }); }

    function renderWorld(view) {
        if (!S.data.items.length) {
            var em = el('div', 'empty');
            em.appendChild(el('div', 'big', '🌱'));
            em.appendChild(el('p', null, T('empty')));
            var go = el('button', 'vbtn primary', T('go_store')); go.type = 'button'; go.style.marginTop = '14px'; go.style.flex = 'none'; go.style.padding = '10px 20px';
            go.addEventListener('click', function () { setTab('store'); });
            em.appendChild(go);
            view.appendChild(em);
            return;
        }
        var all = shelves();
        all.forEach(function (sh) {
            var list = S.data.items.filter(function (i) { return i.shelf === sh; })
                                   .sort(function (a, b) { return (a.position - b.position) || (a.id - b.id); });
            var sec = el('section', 'shelf');
            var h = el('h2', null, shelfLabel(sh) + ' '); h.appendChild(el('span', 'count', (list.length === 1 ? T('cards_1') : T('cards_n', list.length))));
            sec.appendChild(h);
            var grid = el('div', 'grid');
            list.forEach(function (it, idx) {
                var c = cardById(it.card_id); if (!c) return;
                var card = el('div', 'card' + (it.variant !== 'classic' ? ' v-' + it.variant : ''));
                card.appendChild(art(c, it.variant));
                var body = el('div', 'body');
                body.appendChild(el('div', 'name', cardName(c) + (it.variant !== 'classic' ? ' · ' + T('v_' + it.variant) : '')));

                var note = el('textarea', 'note'); note.maxLength = 140; note.dir = 'auto'; note.value = it.note || ''; note.placeholder = T('note_ph');
                note.setAttribute('aria-label', T('note_ph'));
                note.addEventListener('change', function () { saveNote(it, note.value); });
                body.appendChild(note);

                var row = el('div', 'row');
                var prev = el('button', 'mini', document.documentElement.dir === 'rtl' ? '→' : '←'); prev.type = 'button'; prev.title = T('earlier'); prev.setAttribute('aria-label', T('earlier'));
                var next = el('button', 'mini', document.documentElement.dir === 'rtl' ? '←' : '→'); next.type = 'button'; next.title = T('later'); next.setAttribute('aria-label', T('later'));
                prev.disabled = idx === 0; next.disabled = idx === list.length - 1;
                prev.addEventListener('click', function () { var o = list.slice(); o.splice(idx - 1, 0, o.splice(idx, 1)[0]); save(renumber(sh, o), true); });
                next.addEventListener('click', function () { var o = list.slice(); o.splice(idx + 1, 0, o.splice(idx, 1)[0]); save(renumber(sh, o), true); });

                var sel = el('select'); sel.setAttribute('aria-label', T('shelf_label'));
                all.forEach(function (name) { var op = el('option', null, shelfLabel(name)); op.value = name; if (name === sh) op.selected = true; sel.appendChild(op); });
                var opNew = el('option', null, T('shelf_new')); opNew.value = '__new__'; sel.appendChild(opNew);
                sel.addEventListener('change', function () {
                    if (sel.value !== '__new__') { moveTo(it, sel.value); return; }
                    var inp = el('input'); inp.type = 'text'; inp.maxLength = 40; inp.placeholder = T('shelf_ph'); inp.setAttribute('aria-label', T('shelf_ph'));
                    var ok = el('button', 'mini', '✓'); ok.type = 'button'; ok.setAttribute('aria-label', T('move'));
                    var go = function () { var v = inp.value.trim(); if (v) moveTo(it, v); };
                    ok.addEventListener('click', go);
                    inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); go(); } });
                    row.replaceChild(inp, sel); row.insertBefore(ok, inp.nextSibling); inp.focus();
                });
                row.appendChild(prev); row.appendChild(sel); row.appendChild(next);
                body.appendChild(row);
                card.appendChild(body);
                grid.appendChild(card);
            });
            sec.appendChild(grid);
            view.appendChild(sec);
        });
    }
    function moveTo(it, shelf) {
        if (shelf === it.shelf) return;
        var top = -1;
        S.data.items.forEach(function (i) { if (i.shelf === shelf && i.position > top) top = i.position; });
        save([{ id: it.id, shelf: shelf, position: top + 1 }], true);
    }

    // ------------------------------------------------------------------ main
    function render() {
        renderChrome();
        var view = $('dcView'); view.textContent = '';
        if (!S.data) { view.appendChild(el('div', 'loading', '…')); return; }
        if (S.tab === 'world') renderWorld(view); else renderStore(view);
    }
    function setTab(t) { S.tab = t; S.confirming = null; try { sessionStorage.setItem('ts_dc_tab', t); } catch (_) {} render(); window.scrollTo(0, 0); }
    function load() {
        return api('/api/collection').then(function (d) {
            if (d.__status === 200 && d.cards) { S.data = d; render(); }
            else { $('dcView').textContent = ''; $('dcView').appendChild(el('div', 'empty', T('err'))); }
        }).catch(function (e) { if (e && e.message !== 'auth') { $('dcView').textContent = ''; $('dcView').appendChild(el('div', 'empty', T('err'))); } });
    }

    function init() {
        $('dcTabStore').addEventListener('click', function () { setTab('store'); });
        $('dcTabWorld').addEventListener('click', function () { setTab('world'); });
        $('dcLang').addEventListener('change', function () {
            var v = this.value;
            try { if (window.i18n && window.i18n.setLanguage) { window._allowLanguagePost = true; window.i18n.setLanguage(v); } else localStorage.setItem('selectedLanguage', v); } catch (_) {}
            render();
        });
        window.addEventListener('languageChanged', function () { render(); });
        render();
        load();
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
