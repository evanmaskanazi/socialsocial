// Version B208 (F12 rev 2): set up / unlock / manage private messaging at any time, not only when a prompt appears.
//   * Settings > Account gets a "Private messaging" card (index.html has one empty placeholder div,
//     #tsE2EESettings; this file fills it): Turn on / Unlock / Change passphrase / Lock on this device.
//   * A small status button under the Messages heading (index.html) and in the Circles messages sidebar
//     (circles page), placed by this file, opens the same actions.
//   * Change passphrase: re-wraps the SAME private key with the new passphrase (current one required), so no
//     message becomes unreadable and other devices stay unlocked.
//   * Lock on this device: removes the key from this device only (useful on a shared computer).
//   * The setup/unlock dialog says where to find this later, so "Not now" is never a dead end.
//   No server change: Change passphrase uses the existing POST /api/e2ee/key with replace=true and the same
//   public key.
// Version B207 (F12): review round 3 fixes, all small and local to this file:
//   1. A tab that unlocked BEFORE the passphrase was reset on another device kept the old key for up to
//      5 minutes (new messages showed as "cannot be decrypted"). The server key record is now re-checked
//      every 30 s, the same window the send path already used.
//   2. A failed lookup of the recipient's public key (network error / 503) was treated as "recipient has
//      no key", so the PLAIN text was posted to the server (which then refused it). Now the send stops
//      here with "Something went wrong" and the text never leaves the browser.
//   3. Signing in as a different member in the same tab could reuse the previous member's key for up to
//      30 s. Any sign-in/sign-up request now forces a fresh "who is signed in" check.
//   4. A message over 5000 characters was posted as plain text just to be refused; it is refused here now.
//   5. The "not end-to-end encrypted" notice is shown once per person per page, not on every message.
//   6. Password managers: the dialog carries a hidden username field ("TheraSocial messages"), so saving
//      the messages passphrase can no longer overwrite the saved LOGIN password.
//   7. Independent review: sign-in also re-checks who is signed in when its response arrives; a send now
//      checks its own public-key lookup (a parallel read could replace the cache entry and cause a false error).
// Version B206 (F11): NEW FILE. End-to-end encryption for private messages.
//
// HOW IT WORKS (nothing in the existing message code had to change):
//   This file wraps window.fetch for the message endpoints only, the same additive pattern as the
//   A41 CSRF interceptor in i18n.js. Every other request passes straight through untouched.
//     POST /api/messages             -> the text is encrypted in the browser before it is sent
//     GET  /api/messages             -> encrypted texts in the reply are decrypted before the page sees them
//     GET  /api/messages/conversations -> same, for the conversation-list preview
//     GET  /api/user/export-data     -> messages in the export are decrypted so the download stays readable
//     POST /api/auth/logout          -> this device's key is removed
//   index.html and circles-messages.js keep calling fetch exactly as before and receive plain text.
//
// KEYS:
//   * Each member has one ECDH P-256 key pair, created in the browser.
//   * The PUBLIC key is stored on the server (GET /api/e2ee/pubkey/<id>).
//   * The PRIVATE key is wrapped (AES-GCM) with a key derived from a "messages passphrase"
//     (PBKDF2-SHA256, 600k rounds) and only that wrapped blob is stored on the server, so the
//     server cannot open it. Any device can fetch the blob and unlock it with the passphrase.
//   * After unlocking, the private key is kept on this device as a NON-EXTRACTABLE key in
//     IndexedDB, so the passphrase is asked once per device (and again after logout).
//   * Per conversation, both people derive the same AES-256-GCM key (ECDH + HKDF), so the sender
//     can also read their own sent messages. A fresh random IV is used for every message and the
//     sender/recipient ids are bound in as authenticated data (the server cannot swap them).
//   * Stored form of a message: "e2ee:v1:<iv>:<ciphertext>" (base64url) in the existing
//     messages.content column. Older plain-text messages are shown as they are.
//
// CRISIS NOTICE: the server can no longer read a message, so the crisis-wording check that used to
//   run on the server now runs here, before encryption, and only a yes/no flag is sent along.
(function () {
    'use strict';
    if (typeof window === 'undefined' || window.__tsE2EE) return;
    var subtle = window.crypto && window.crypto.subtle;
    if (!subtle || typeof window.fetch !== 'function' || typeof TextEncoder === 'undefined') {
        window.__tsE2EE = { supported: false };
        return;
    }
    window.__tsE2EE = { supported: true };

    var PREFIX = 'e2ee:v1:';
    var ITER = 600000;
    var enc = new TextEncoder();
    var dec = new TextDecoder();
    var prevFetch = window.fetch.bind(window);   // i18n.js (loaded first) already adds the CSRF header

    // ------------------------------------------------------------------ texts (en/he/ar/ru)
    // Self-contained map (same approach as SUPPORT_MSGS on the support page) so i18n.js is untouched.
    var MSG = {
        setup_title: { en: 'Set up private messaging', he: 'הגדרת הודעות פרטיות', ar: 'إعداد الرسائل الخاصة', ru: 'Настройка личных сообщений' },
        setup_intro: {
            en: 'Your messages are end-to-end encrypted: only you and the person you write to can read them, not even TheraSocial. Choose a messages passphrase. It unlocks your messages on each of your devices. We cannot recover it for you.',
            he: 'ההודעות שלכם מוצפנות מקצה לקצה: רק אתם והאדם שאליו אתם כותבים יכולים לקרוא אותן, גם TheraSocial לא. בחרו ביטוי סיסמה להודעות. הוא פותח את ההודעות שלכם בכל אחד מהמכשירים שלכם. לא נוכל לשחזר אותו עבורכם.',
            ar: 'رسائلكم مشفّرة من طرف إلى طرف: أنتم والشخص الذي تراسلونه فقط يمكنكم قراءتها، ولا يستطيع TheraSocial قراءتها أيضًا. اختاروا عبارة مرور للرسائل. تفتح رسائلكم على كل أجهزتكم. لا يمكننا استعادتها لكم.',
            ru: 'Ваши сообщения защищены сквозным шифрованием: их можете прочитать только вы и ваш собеседник, даже TheraSocial не может. Придумайте парольную фразу для сообщений. Она открывает ваши сообщения на каждом устройстве. Мы не можем её восстановить.'
        },
        unlock_title: { en: 'Unlock your messages', he: 'פתיחת ההודעות שלכם', ar: 'فتح رسائلكم', ru: 'Разблокировка сообщений' },
        unlock_intro: {
            en: 'Enter your messages passphrase to read and send messages on this device.',
            he: 'הזינו את ביטוי הסיסמה להודעות כדי לקרוא ולשלוח הודעות במכשיר זה.',
            ar: 'أدخلوا عبارة المرور للرسائل لقراءة الرسائل وإرسالها على هذا الجهاز.',
            ru: 'Введите парольную фразу, чтобы читать и отправлять сообщения на этом устройстве.'
        },
        pass_label: { en: 'Messages passphrase', he: 'ביטוי סיסמה להודעות', ar: 'عبارة مرور الرسائل', ru: 'Парольная фраза для сообщений' },
        confirm_label: { en: 'Confirm passphrase', he: 'אימות ביטוי הסיסמה', ar: 'تأكيد عبارة المرور', ru: 'Повторите парольную фразу' },
        btn_create: { en: 'Turn on private messaging', he: 'הפעלת הודעות פרטיות', ar: 'تفعيل الرسائل الخاصة', ru: 'Включить личные сообщения' },
        btn_unlock: { en: 'Unlock', he: 'פתיחה', ar: 'فتح', ru: 'Разблокировать' },
        btn_cancel: { en: 'Not now', he: 'לא עכשיו', ar: 'ليس الآن', ru: 'Не сейчас' },
        forgot: { en: 'Forgot your passphrase?', he: 'שכחתם את ביטוי הסיסמה?', ar: 'نسيتم عبارة المرور؟', ru: 'Забыли парольную фразу?' },
        reset_warn: {
            en: 'Starting over creates new keys. Your earlier encrypted messages will no longer be readable by you or the people you wrote to. Continue?',
            he: 'התחלה מחדש תיצור מפתחות חדשים. הודעות מוצפנות קודמות לא יהיו קריאות עבורכם ועבור האנשים שכתבתם להם. להמשיך?',
            ar: 'البدء من جديد ينشئ مفاتيح جديدة. لن تتمكنوا أنتم ولا الأشخاص الذين راسلتموهم من قراءة رسائلكم المشفّرة السابقة. هل تريدون المتابعة؟',
            ru: 'Если начать заново, будут созданы новые ключи. Ранее зашифрованные сообщения станут недоступны ни вам, ни вашим собеседникам. Продолжить?'
        },
        btn_reset: { en: 'Start over', he: 'התחלה מחדש', ar: 'البدء من جديد', ru: 'Начать заново' },
        err_short: { en: 'Use at least 10 characters.', he: 'השתמשו ב-10 תווים לפחות.', ar: 'استخدموا 10 أحرف على الأقل.', ru: 'Используйте не менее 10 символов.' },
        err_mismatch: { en: 'The two passphrases do not match.', he: 'ביטויי הסיסמה אינם תואמים.', ar: 'عبارتا المرور غير متطابقتين.', ru: 'Парольные фразы не совпадают.' },
        err_wrong: { en: 'That passphrase did not unlock your messages.', he: 'ביטוי הסיסמה לא פתח את ההודעות.', ar: 'لم تفتح عبارة المرور هذه رسائلكم.', ru: 'Эта парольная фраза не открыла ваши сообщения.' },
        err_generic: { en: 'Something went wrong. Please try again.', he: 'משהו השתבש. נסו שוב.', ar: 'حدث خطأ ما. حاولوا مرة أخرى.', ru: 'Что-то пошло не так. Попробуйте ещё раз.' },
        busy: { en: 'Working…', he: 'מעבד…', ar: 'جارٍ المعالجة…', ru: 'Обработка…' },
        locked_ph: { en: '🔒 Encrypted message. Unlock to read.', he: '🔒 הודעה מוצפנת. פתחו כדי לקרוא.', ar: '🔒 رسالة مشفّرة. افتحوها لقراءتها.', ru: '🔒 Зашифрованное сообщение. Разблокируйте, чтобы прочитать.' },
        undecr_ph: { en: '🔒 This message cannot be decrypted on this device.', he: '🔒 לא ניתן לפענח הודעה זו במכשיר זה.', ar: '🔒 تعذّر فك تشفير هذه الرسالة على هذا الجهاز.', ru: '🔒 Это сообщение не удаётся расшифровать на этом устройстве.' },
        no_unlock_send: {
            en: 'Messages stay locked until you unlock them, so this message was not sent.',
            he: 'ההודעות נעולות עד שתפתחו אותן, ולכן ההודעה לא נשלחה.',
            ar: 'تبقى الرسائل مقفلة حتى تفتحوها، لذلك لم تُرسل الرسالة.',
            ru: 'Сообщения остаются заблокированными, пока вы их не разблокируете, поэтому сообщение не отправлено.'
        },
        recipient_no_key: {
            en: 'This person has not turned on private messaging yet, so a message cannot be sent to them securely.',
            he: 'האדם הזה עדיין לא הפעיל הודעות פרטיות, ולכן אי אפשר לשלוח לו הודעה באופן מאובטח.',
            ar: 'لم يفعّل هذا الشخص الرسائل الخاصة بعد، لذلك لا يمكن إرسال رسالة إليه بشكل آمن.',
            ru: 'Этот человек ещё не включил личные сообщения, поэтому отправить ему сообщение безопасно нельзя.'
        },
        plaintext_refused: {
            en: 'Messages must be sent securely. Reload the page and try again.',
            he: 'יש לשלוח הודעות באופן מאובטח. רעננו את הדף ונסו שוב.',
            ar: 'يجب إرسال الرسائل بشكل آمن. أعيدوا تحميل الصفحة وحاولوا مرة أخرى.',
            ru: 'Сообщения нужно отправлять безопасно. Обновите страницу и повторите попытку.'
        },
        err_exists: {
            en: 'Private messaging is already set up for your account. Enter your passphrase to unlock it.',
            he: 'הודעות פרטיות כבר הוגדרו בחשבון שלכם. הזינו את ביטוי הסיסמה כדי לפתוח.',
            ar: 'تم إعداد الرسائل الخاصة لحسابكم بالفعل. أدخلوا عبارة المرور لفتحها.',
            ru: 'Личные сообщения уже настроены для вашей учётной записи. Введите парольную фразу, чтобы разблокировать.'
        },
        export_locked: {
            en: 'Your messages were not unlocked, so they are still encrypted in this export.',
            he: 'ההודעות לא נפתחו, ולכן הן עדיין מוצפנות בייצוא זה.',
            ar: 'لم تُفتح رسائلكم، لذلك لا تزال مشفّرة في هذا التصدير.',
            ru: 'Сообщения не были разблокированы, поэтому в этом экспорте они остаются зашифрованными.'
        },
        notice_self: {
            en: 'Private messaging is not turned on for you yet, so this message was not end-to-end encrypted.',
            he: 'הודעות פרטיות עדיין לא הופעלו אצלך, ולכן הודעה זו לא הוצפנה מקצה לקצה.',
            ar: 'الرسائل الخاصة غير مفعّلة لديك بعد، لذلك لم تُشفَّر هذه الرسالة من طرف إلى طرف.',
            ru: 'Личные сообщения у вас ещё не включены, поэтому это сообщение не было зашифровано сквозным шифрованием.'
        },
        notice_locked: {
            en: 'Your private messages are locked, so this message was not end-to-end encrypted.',
            he: 'ההודעות הפרטיות שלך נעולות, ולכן הודעה זו לא הוצפנה מקצה לקצה.',
            ar: 'رسائلك الخاصة مقفلة، لذلك لم تُشفَّر هذه الرسالة من طرف إلى طرف.',
            ru: 'Ваши личные сообщения заблокированы, поэтому это сообщение не было зашифровано сквозным шифрованием.'
        },
        // F12 rev 2: managing private messaging at any time
        settings_title: { en: 'Private messaging', he: 'הודעות פרטיות', ar: 'الرسائل الخاصة', ru: 'Личные сообщения' },
        status_on: { en: 'On. Your messages are end-to-end encrypted and unlocked on this device.', he: 'פעיל. ההודעות שלכם מוצפנות מקצה לקצה ופתוחות במכשיר זה.', ar: 'مفعّلة. رسائلكم مشفّرة من طرف إلى طرف ومفتوحة على هذا الجهاز.', ru: 'Включено. Ваши сообщения защищены сквозным шифрованием и разблокированы на этом устройстве.' },
        status_locked: { en: 'Set up, but locked on this device. Unlock with your messages passphrase to read and send.', he: 'מוגדר, אך נעול במכשיר זה. פתחו עם ביטוי הסיסמה להודעות כדי לקרוא ולשלוח.', ar: 'مُعدّة لكنها مقفلة على هذا الجهاز. افتحوها بعبارة مرور الرسائل للقراءة والإرسال.', ru: 'Настроено, но заблокировано на этом устройстве. Разблокируйте парольной фразой, чтобы читать и отправлять.' },
        status_off: { en: 'Off. Turn it on so that only you and the people you write to can read your messages.', he: 'כבוי. הפעילו כדי שרק אתם והאנשים שאתם כותבים להם תוכלו לקרוא את ההודעות.', ar: 'غير مفعّلة. فعّلوها كي لا يقرأ رسائلكم سواكم ومن تراسلونهم.', ru: 'Выключено. Включите, чтобы ваши сообщения могли читать только вы и ваши собеседники.' },
        pill_on: { en: '🔒 Private messaging: on', he: '🔒 הודעות פרטיות: פעיל', ar: '🔒 الرسائل الخاصة: مفعّلة', ru: '🔒 Личные сообщения: вкл.' },
        pill_locked: { en: '🔓 Unlock private messages', he: '🔓 פתיחת ההודעות הפרטיות', ar: '🔓 فتح الرسائل الخاصة', ru: '🔓 Разблокировать сообщения' },
        pill_off: { en: '🔓 Turn on private messaging', he: '🔓 הפעלת הודעות פרטיות', ar: '🔓 تفعيل الرسائل الخاصة', ru: '🔓 Включить личные сообщения' },
        btn_change_pass: { en: 'Change passphrase', he: 'שינוי ביטוי הסיסמה', ar: 'تغيير عبارة المرور', ru: 'Сменить парольную фразу' },
        btn_lock: { en: 'Lock on this device', he: 'נעילה במכשיר זה', ar: 'قفل على هذا الجهاز', ru: 'Заблокировать на этом устройстве' },
        btn_close: { en: 'Close', he: 'סגירה', ar: 'إغلاق', ru: 'Закрыть' },
        lock_hint: { en: 'Locking removes the key from this device only, for example on a shared computer. Your messages stay safe and open again with your passphrase.', he: 'נעילה מסירה את המפתח ממכשיר זה בלבד, למשל במחשב משותף. ההודעות נשארות שמורות ונפתחות שוב עם ביטוי הסיסמה.', ar: 'القفل يزيل المفتاح من هذا الجهاز فقط، مثلًا على حاسوب مشترك. تبقى رسائلكم آمنة وتُفتح مجددًا بعبارة المرور.', ru: 'Блокировка удаляет ключ только с этого устройства, например на общем компьютере. Сообщения остаются в безопасности и снова открываются парольной фразой.' },
        change_title: { en: 'Change your messages passphrase', he: 'שינוי ביטוי הסיסמה להודעות', ar: 'تغيير عبارة مرور الرسائل', ru: 'Смена парольной фразы' },
        change_intro: { en: 'Only the passphrase changes: all your messages stay readable, and your other devices stay unlocked. Use the new passphrase next time a device asks.', he: 'רק ביטוי הסיסמה משתנה: כל ההודעות נשארות קריאות, והמכשירים האחרים שלכם נשארים פתוחים. השתמשו בביטוי החדש בפעם הבאה שמכשיר יבקש.', ar: 'تتغيّر عبارة المرور فقط: تبقى كل رسائلكم مقروءة وتبقى أجهزتكم الأخرى مفتوحة. استخدموا العبارة الجديدة في المرة القادمة التي يطلبها جهاز.', ru: 'Меняется только парольная фраза: все сообщения остаются читаемыми, а другие устройства остаются разблокированными. Используйте новую фразу, когда устройство попросит.' },
        current_label: { en: 'Current passphrase', he: 'ביטוי הסיסמה הנוכחי', ar: 'عبارة المرور الحالية', ru: 'Текущая парольная фраза' },
        new_label: { en: 'New passphrase', he: 'ביטוי סיסמה חדש', ar: 'عبارة المرور الجديدة', ru: 'Новая парольная фраза' },
        changed_ok: { en: 'Your messages passphrase was changed.', he: 'ביטוי הסיסמה להודעות שונה.', ar: 'تم تغيير عبارة مرور الرسائل.', ru: 'Парольная фраза изменена.' },
        locked_ok: { en: 'Private messages are now locked on this device.', he: 'ההודעות הפרטיות נעולות כעת במכשיר זה.', ar: 'الرسائل الخاصة مقفلة الآن على هذا الجهاز.', ru: 'Личные сообщения заблокированы на этом устройстве.' },
        ready_ok: { en: 'Private messaging is on. Open a conversation to read it.', he: 'ההודעות הפרטיות פעילות. פתחו שיחה כדי לקרוא.', ar: 'الرسائل الخاصة مفعّلة. افتحوا محادثة لقراءتها.', ru: 'Личные сообщения включены. Откройте переписку, чтобы прочитать.' },
        later_hint: { en: 'You can do this later in Settings › Account › Private messaging, or with the 🔓 button in Messages.', he: 'אפשר לעשות זאת גם מאוחר יותר בהגדרות › חשבון › הודעות פרטיות, או בכפתור 🔓 בהודעות.', ar: 'يمكنكم فعل ذلك لاحقًا من الإعدادات › الحساب › الرسائل الخاصة، أو بزر 🔓 في الرسائل.', ru: 'Это можно сделать позже: Настройки › Аккаунт › Личные сообщения или кнопкой 🔓 в Сообщениях.' },
        notice_plain: {
            en: 'This person has not turned on private messaging yet, so this message was not end-to-end encrypted.',
            he: 'האדם הזה עדיין לא הפעיל הודעות פרטיות, ולכן הודעה זו לא הוצפנה מקצה לקצה.',
            ar: 'لم يفعّل هذا الشخص الرسائل الخاصة بعد، لذلك لم تُشفَّر هذه الرسالة من طرف إلى طرف.',
            ru: 'Этот человек ещё не включил личные сообщения, поэтому это сообщение не было зашифровано сквозным шифрованием.'
        }
    };
    function lang() {
        try { if (window.i18n && window.i18n.getCurrentLanguage) { var l = window.i18n.getCurrentLanguage(); if (l) return l; } } catch (_) {}
        try { return localStorage.getItem('selectedLanguage') || 'en'; } catch (_) { return 'en'; }
    }
    function T(key) { var m = MSG[key]; return m ? (m[lang()] || m.en) : key; }
    function toastText(s, type) {
        try {
            if (typeof window.showNotification === 'function') window.showNotification(s, type || 'info');
            else if (typeof window.showMessage === 'function') window.showMessage(s, type || 'info');
        } catch (_) {}
    }
    function toast(key, type) { toastText(T(key), type); }

    // ------------------------------------------------------------------ small helpers
    function b64u(buf) {
        var b = new Uint8Array(buf), s = '';
        for (var i = 0; i < b.length; i++) s += String.fromCharCode(b[i]);
        return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    }
    function unb64u(s) {
        s = String(s).replace(/-/g, '+').replace(/_/g, '/');
        while (s.length % 4) s += '=';
        var bin = atob(s), out = new Uint8Array(bin.length);
        for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
        return out;
    }
    function rand(n) { return window.crypto.getRandomValues(new Uint8Array(n)); }
    function fpOf(pubStr) {                       // short comparable id of a public key (JSON string)
        try { var j = JSON.parse(pubStr); return j.x + '.' + j.y; } catch (_) { return ''; }
    }
    function pathOf(input) {
        try { var u = new URL(typeof input === 'string' ? input : input.url, window.location.href);
              return u.origin === window.location.origin ? u : null; } catch (_) { return null; }
    }
    function jsonResp(status, obj) {
        return new Response(JSON.stringify(obj), { status: status, headers: { 'Content-Type': 'application/json' } });
    }
    function getJSON(url) {
        return prevFetch(url, { credentials: 'include' }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
    }

    // ------------------------------------------------------------------ state
    function getDeclined() { try { return sessionStorage.getItem('ts_e2ee_declined') === '1'; } catch (_) { return false; } }
    function setDeclined(v) {
        S.declined = !!v;
        try { if (v) sessionStorage.setItem('ts_e2ee_declined', '1'); else sessionStorage.removeItem('ts_e2ee_declined'); } catch (_) {}
    }
    var S = { dismissedAt: 0, uid: null, uidT: 0, priv: null, fp: null, server: undefined, serverT: 0, declined: getDeclined(), pending: null };
    var forceAt = {};     // partner id -> last forced public-key re-read
    var pubCache = {};    // partner id -> { t, none, p: Promise<{jwkStr,key,fp}|null> }
    var pairCache = {};   // partner id -> { fp, p: Promise<CryptoKey> }

    function resetMemory() {     // a different member is now signed in on this page: forget everything held in memory
        S.uid = null; S.priv = null; S.fp = null; S.server = undefined; S.serverT = 0; S.pending = null;
        pubCache = {}; pairCache = {}; forceAt = {};
        setDeclined(false);
    }
    // Who is signed in right now. Re-checked every 30 s so a session that expired and was replaced by
    // another member's login on the same page can never use the previous member's key.
    function getMe() {
        if (S.uid && Date.now() - S.uidT < 30000) return Promise.resolve(S.uid);
        return getJSON('/api/user/profile').then(function (u) {
            var id = (u && u.id) ? u.id : null;
            if (id && S.uid && id !== S.uid) resetMemory();
            if (id) { S.uid = id; S.uidT = Date.now(); }
            return S.uid;
        });
    }
    function getServerKey(force) {
        if (S.server && !force && Date.now() - S.serverT < 30000) return Promise.resolve(S.server);   // F12: was 300000 (5 min)
        return getJSON('/api/e2ee/key').then(function (k) {
            if (k) { S.server = k; S.serverT = Date.now(); }
            return k || S.server || null;      // a failed lookup is never remembered
        });
    }

    // ------------------------------------------------------------------ device key store (IndexedDB)
    function idbOpen() {
        return new Promise(function (res, rej) {
            try {
                var r = window.indexedDB.open('ts_e2ee', 1);
                r.onupgradeneeded = function () { r.result.createObjectStore('keys'); };
                r.onsuccess = function () { res(r.result); };
                r.onerror = function () { rej(r.error); };
            } catch (e) { rej(e); }
        });
    }
    function idbOp(mode, fn) {
        return idbOpen().then(function (db) {
            return new Promise(function (res, rej) {
                var tx = db.transaction('keys', mode), out;
                tx.oncomplete = function () { db.close(); res(out); };
                tx.onerror = tx.onabort = function () { db.close(); rej(tx.error); };
                var rq = fn(tx.objectStore('keys'));
                if (rq) rq.onsuccess = function () { out = rq.result; };
            });
        });
    }
    function loadLocal(uid) {
        return idbOp('readonly', function (st) { return st.get('dev'); }).then(function (rec) {
            if (rec && rec.uid === uid && rec.priv) { S.priv = rec.priv; S.fp = rec.fp; }
        }).catch(function () {});
    }
    function saveLocal(uid) {
        return idbOp('readwrite', function (st) { return st.put({ uid: uid, priv: S.priv, fp: S.fp }, 'dev'); }).catch(function () {});
    }
    function clearLocal() {
        resetMemory();
        return idbOp('readwrite', function (st) { return st.delete('dev'); }).catch(function () {});
    }

    // ------------------------------------------------------------------ key creation / unlock
    function passKey(pass, salt, iter) {
        return subtle.importKey('raw', enc.encode(pass.normalize('NFKC')), 'PBKDF2', false, ['deriveKey']).then(function (base) {
            return subtle.deriveKey({ name: 'PBKDF2', salt: salt, iterations: iter, hash: 'SHA-256' }, base,
                { name: 'AES-GCM', length: 256 }, false, ['wrapKey', 'unwrapKey']);
        });
    }
    var ECDH = { name: 'ECDH', namedCurve: 'P-256' };

    async function createKey(pass, replace, uid) {
        var kp = await subtle.generateKey(ECDH, true, ['deriveBits']);
        var salt = rand(16), iv = rand(12);
        var wk = await passKey(pass, salt, ITER);
        var wrapped = await subtle.wrapKey('pkcs8', kp.privateKey, wk, { name: 'AES-GCM', iv: iv });
        var jwk = await subtle.exportKey('jwk', kp.publicKey);
        var pubStr = JSON.stringify({ kty: jwk.kty, crv: jwk.crv, x: jwk.x, y: jwk.y });
        var blob = JSON.stringify({ v: 1, i: ITER, s: b64u(salt), n: b64u(iv), c: b64u(wrapped) });
        var r = await prevFetch('/api/e2ee/key', {
            method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ public_key: pubStr, wrapped_private_key: blob, replace: !!replace })
        });
        if (r.status === 409) {      // set up meanwhile on another device/tab: switch this dialog to "unlock"
            await getServerKey(true);
            var e409 = new Error('exists'); e409.code = 'err_exists'; e409.switchTo = 'unlock'; throw e409;
        }
        if (!r.ok) throw new Error('save failed');
        // keep only a NON-extractable copy on this device
        S.priv = await subtle.unwrapKey('pkcs8', wrapped, wk, { name: 'AES-GCM', iv: iv }, ECDH, false, ['deriveBits']);
        S.fp = fpOf(pubStr);
        S.server = { has_key: true, public_key: pubStr, wrapped_private_key: blob }; S.serverT = Date.now();
        pubCache = {}; pairCache = {};
        await saveLocal(uid);
    }
    async function unlockKey(pass, uid) {
        await getServerKey(true).catch(function () {});     // always unlock against the CURRENT stored key (it may have been reset elsewhere)
        var sk = S.server;
        if (!sk || !sk.has_key) { var eg = new Error('no key'); eg.code = 'err_generic'; throw eg; }
        var b = JSON.parse(sk.wrapped_private_key);
        var wk = await passKey(pass, unb64u(b.s), b.i);
        try {
            S.priv = await subtle.unwrapKey('pkcs8', unb64u(b.c), wk, { name: 'AES-GCM', iv: unb64u(b.n) }, ECDH, false, ['deriveBits']);
        } catch (_) { var e = new Error('wrong'); e.code = 'err_wrong'; throw e; }
        S.fp = fpOf(sk.public_key);
        pubCache = {}; pairCache = {};
        await saveLocal(uid);
    }

    // F12 rev 2: re-wrap the SAME private key with a new passphrase. The public key does not change, so no
    // message becomes unreadable and other devices that are already unlocked stay unlocked.
    async function changeKey(oldPass, newPass, uid) {
        await getServerKey(true).catch(function () {});
        var sk = S.server;
        if (!sk || !sk.has_key) { var eg = new Error('no key'); eg.code = 'err_generic'; throw eg; }
        var b = JSON.parse(sk.wrapped_private_key);
        var wkOld = await passKey(oldPass, unb64u(b.s), b.i), priv;
        try { priv = await subtle.unwrapKey('pkcs8', unb64u(b.c), wkOld, { name: 'AES-GCM', iv: unb64u(b.n) }, ECDH, true, ['deriveBits']); }
        catch (_) { var e = new Error('wrong'); e.code = 'err_wrong'; throw e; }
        var salt = rand(16), iv = rand(12);
        var wk = await passKey(newPass, salt, ITER);
        var wrapped = await subtle.wrapKey('pkcs8', priv, wk, { name: 'AES-GCM', iv: iv });
        var blob = JSON.stringify({ v: 1, i: ITER, s: b64u(salt), n: b64u(iv), c: b64u(wrapped) });
        var r = await prevFetch('/api/e2ee/key', {
            method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ public_key: sk.public_key, wrapped_private_key: blob, replace: true })
        });
        if (!r.ok) throw new Error('save failed');
        S.priv = await subtle.unwrapKey('pkcs8', wrapped, wk, { name: 'AES-GCM', iv: iv }, ECDH, false, ['deriveBits']);
        S.fp = fpOf(sk.public_key);
        S.server = { has_key: true, public_key: sk.public_key, wrapped_private_key: blob }; S.serverT = Date.now();
        await saveLocal(uid);
    }
    function runFor(uid) {
        return function (mode, pass, replace, old) {
            return mode === 'unlock' ? unlockKey(pass, uid) : mode === 'change' ? changeKey(old, pass, uid) : createKey(pass, replace, uid);
        };
    }

    // ------------------------------------------------------------------ dialog (setup / unlock / change / manage)
    function el(tag, css, text) {
        var n = document.createElement(tag);
        if (css) n.style.cssText = css;
        if (text) n.textContent = text;
        return n;
    }
    function dialog(cfg) {
        return new Promise(function (resolve) {
            var rtl = (lang() === 'he' || lang() === 'ar');
            var mode = cfg.mode, replace = false, resetting = false;
            var ov = el('div', 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(30,40,50,.55);z-index:2147483000;display:flex;align-items:center;justify-content:center;padding:16px;');
            ov.setAttribute('role', 'dialog'); ov.setAttribute('aria-modal', 'true'); ov.setAttribute('dir', rtl ? 'rtl' : 'ltr');
            var card = el('div', 'background:#fff;color:#2d3748;max-width:440px;width:100%;border-radius:16px;padding:24px;box-shadow:0 20px 60px rgba(0,0,0,.3);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;max-height:92vh;overflow:auto;');
            ov.appendChild(card);
            function close(v) { if (v === false) S.dismissedAt = Date.now(); document.removeEventListener('keydown', onKey, true); if (ov.parentNode) ov.parentNode.removeChild(ov); resolve(v); }
            function onKey(e) { if (e.key === 'Escape') { e.stopPropagation(); close(false); } }
            document.addEventListener('keydown', onKey, true);
            var INPUT = 'width:100%;box-sizing:border-box;padding:10px 12px;margin:4px 0 12px;border:2px solid #cbd5e0;border-radius:8px;font-size:16px;background:#fff;color:#2d3748;';
            var BTN = 'padding:10px 20px;border:none;border-radius:22px;font-size:15px;cursor:pointer;';

            function render() {
                card.textContent = '';
                var setup = mode === 'setup', change = mode === 'change';
                if (mode === 'manage') {           // F12 rev 2: already on and unlocked
                    card.appendChild(el('h2', 'margin:0 0 10px;font-size:20px;color:#3D4852;', T('settings_title')));
                    card.appendChild(el('p', 'margin:0 0 10px;line-height:1.5;', T('status_on')));
                    card.appendChild(el('p', 'margin:0 0 16px;line-height:1.5;font-size:14px;color:#6B7280;', T('lock_hint')));
                    var mr = el('div', 'display:flex;gap:10px;flex-wrap:wrap;');
                    var bc = el('button', BTN + 'background:#5A7A93;color:#fff;', T('btn_change_pass')); bc.type = 'button';
                    var bl = el('button', BTN + 'background:#edf2f7;color:#2d3748;', T('btn_lock')); bl.type = 'button';
                    var bx = el('button', BTN + 'background:#edf2f7;color:#2d3748;', T('btn_close')); bx.type = 'button';
                    bc.onclick = function () { mode = 'change'; render(); };
                    bl.onclick = function () { if (cfg.lock) cfg.lock(); close('locked'); };
                    bx.onclick = function () { close(null); };
                    mr.appendChild(bc); mr.appendChild(bl); mr.appendChild(bx); card.appendChild(mr);
                    setTimeout(function () { try { bc.focus(); } catch (_) {} }, 0);
                    return;
                }
                card.appendChild(el('h2', 'margin:0 0 10px;font-size:20px;color:#3D4852;', T(setup ? 'setup_title' : change ? 'change_title' : 'unlock_title')));
                if (resetting) {
                    card.appendChild(el('p', 'margin:0 0 16px;line-height:1.5;', T('reset_warn')));
                    var rr = el('div', 'display:flex;gap:10px;flex-wrap:wrap;');
                    var go = el('button', BTN + 'background:#C17C74;color:#fff;', T('btn_reset')); go.type = 'button';
                    var back = el('button', BTN + 'background:#edf2f7;color:#2d3748;', T('btn_cancel')); back.type = 'button';
                    go.onclick = function () { mode = 'setup'; replace = true; resetting = false; render(); };
                    back.onclick = function () { resetting = false; render(); };
                    rr.appendChild(go); rr.appendChild(back); card.appendChild(rr);
                    return;
                }
                card.appendChild(el('p', 'margin:0 0 14px;line-height:1.5;', T(setup ? 'setup_intro' : change ? 'change_intro' : 'unlock_intro')));
                // F12: a hidden username so a password manager files this passphrase separately from the login password.
                var un = el('input', 'position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;'); un.type = 'text'; un.tabIndex = -1;
                un.autocomplete = 'username'; un.value = 'TheraSocial messages'; un.setAttribute('aria-hidden', 'true'); un.readOnly = true; card.appendChild(un);
                var i0 = null;
                if (change) {
                    card.appendChild(el('label', 'font-weight:600;font-size:14px;', T('current_label')));
                    i0 = el('input', INPUT); i0.type = 'password'; i0.autocomplete = 'current-password'; card.appendChild(i0);
                }
                var l1 = el('label', 'font-weight:600;font-size:14px;', T(change ? 'new_label' : 'pass_label'));
                var i1 = el('input', INPUT); i1.type = 'password'; i1.autocomplete = (setup || change) ? 'new-password' : 'current-password';
                card.appendChild(l1); card.appendChild(i1);
                var i2 = null;
                if (setup || change) {
                    card.appendChild(el('label', 'font-weight:600;font-size:14px;', T('confirm_label')));
                    i2 = el('input', INPUT); i2.type = 'password'; i2.autocomplete = 'new-password'; card.appendChild(i2);
                }
                var err = el('div', 'color:#C17C74;min-height:20px;font-size:14px;margin-bottom:8px;'); err.setAttribute('role', 'alert'); card.appendChild(err);
                var row = el('div', 'display:flex;gap:10px;flex-wrap:wrap;align-items:center;');
                var okLabel = T(setup ? 'btn_create' : change ? 'btn_change_pass' : 'btn_unlock');
                var ok = el('button', BTN + 'background:#5A7A93;color:#fff;', okLabel); ok.type = 'button';
                var no = el('button', BTN + 'background:#edf2f7;color:#2d3748;', T('btn_cancel')); no.type = 'button';
                row.appendChild(ok); row.appendChild(no); card.appendChild(row);
                if (!change) card.appendChild(el('p', 'margin:12px 0 0;font-size:13px;line-height:1.45;color:#6B7280;', T('later_hint')));   // F12 rev 2
                if (!setup && !change) {
                    var fg = el('button', 'margin-top:14px;background:none;border:none;color:#5A7A93;text-decoration:underline;cursor:pointer;font-size:14px;padding:0;', T('forgot')); fg.type = 'button';
                    fg.onclick = function () { resetting = true; render(); };
                    card.appendChild(fg);
                }
                function fail(k) { err.textContent = T(k); }
                function busy(b) { ok.disabled = no.disabled = b; ok.textContent = b ? T('busy') : okLabel; }
                async function submit() {
                    err.textContent = '';
                    var p1 = i1.value, p2 = i2 ? i2.value : null;
                    if (change && !i0.value) return;
                    if (setup || change) {
                        if (Array.from(p1).length < 10) return fail('err_short');
                        if (p1 !== p2) return fail('err_mismatch');
                    } else if (!p1) return;
                    busy(true);
                    try { await cfg.run(mode, p1, replace, i0 ? i0.value : null); close(change ? 'changed' : true); }
                    catch (e) {
                        busy(false);
                        if (e && e.switchTo) { mode = e.switchTo; replace = false; render(); var al = card.querySelector('[role=alert]'); if (al) al.textContent = T(e.code || 'err_generic'); }
                        else fail(e && e.code ? e.code : 'err_generic');
                    }
                }
                ok.onclick = submit;
                no.onclick = function () { close(false); };
                [i0, i1, i2].forEach(function (i) { if (i) i.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); submit(); } }); });
                setTimeout(function () { try { (i0 || i1).focus(); } catch (_) {} }, 0);
            }
            render();
            document.body.appendChild(ov);
        });
    }

    // Resolves to true when this device holds the private key. allowPrompt: may ask the member.
    // promptWhen: optional predicate on the server key record, deciding whether asking is worthwhile.
    function ensureReady(allowPrompt, needAsk) {
        if (S.pending) {
            // Share a running check only if it was allowed to ask (or this caller will not ask); otherwise wait, then ask.
            if (S.pendingPrompt || !allowPrompt) return S.pending;
            return S.pending.then(function () { return ensureReady(allowPrompt, needAsk); });
        }
        S.pendingPrompt = !!allowPrompt;
        var p = (async function () {
            var uid = await getMe();
            if (!uid) return false;
            if (!S.priv) await loadLocal(uid);
            var sk = await getServerKey();
            if (S.priv && sk && (!sk.has_key || (S.fp && fpOf(sk.public_key) !== S.fp))) {
                // The key was reset elsewhere (or the server record is gone): this device's copy is stale.
                S.priv = null; S.fp = null; pubCache = {}; pairCache = {};
                await idbOp('readwrite', function (st) { return st.delete('dev'); }).catch(function () {});
            }
            if (S.priv) return true;
            if (!allowPrompt || !sk) return false;
            if (!sk.has_key && sk !== S.server) return false;
            if (needAsk && !needAsk(sk)) return false;
            var done = await dialog({
                mode: sk.has_key ? 'unlock' : 'setup',
                run: runFor(uid)
            });
            return !!(done && S.priv);
        })();
        S.pending = p;
        var clear = function () { S.pending = null; };
        p.then(clear, clear);
        return p;
    }

    // ------------------------------------------------------------------ shared secret per conversation
    // Caches hold the PROMISE, so a long thread triggers one lookup per person, not one per message.
    // "No key" (404) is remembered for 60 s; a failed lookup is never remembered.
    function pubFetch(id) {
        return prevFetch('/api/e2ee/pubkey/' + id, { credentials: 'include' }).then(function (resp) {
            if (resp.status === 404) return null;
            if (!resp.ok) return false;
            return resp.json().then(function (r) {
                if (!r || !r.public_key) return null;
                return subtle.importKey('jwk', JSON.parse(r.public_key), ECDH, false, []).then(function (key) {
                    return { jwkStr: r.public_key, key: key, fp: fpOf(r.public_key) };
                }, function () { return null; });      // an unusable stored key counts as "no key"
            });
        }).catch(function () { return false; });
    }
    function getPub(id, force) {
        var c = pubCache[id];
        if (c && !force && !(c.none && Date.now() - c.t > 60000)) return c.p;
        var entry = { t: Date.now(), none: false };
        entry.p = pubFetch(id).then(function (r) {
            if (r === false) { if (pubCache[id] === entry) delete pubCache[id]; return null; }
            if (r === null) entry.none = true;
            return r;
        });
        pubCache[id] = entry;
        return entry.p;
    }
    async function pairKey(partnerId, force) {
        var pub = await getPub(partnerId, force);
        if (!pub) return null;
        var pc = pairCache[partnerId];
        if (pc && pc.fp === pub.fp) return pc.p;
        var entry = { fp: pub.fp };
        entry.p = (async function () {
            var bits = await subtle.deriveBits({ name: 'ECDH', public: pub.key }, S.priv, 256);
            var hk = await subtle.importKey('raw', bits, 'HKDF', false, ['deriveKey']);
            var lo = Math.min(S.uid, partnerId), hi = Math.max(S.uid, partnerId);
            return subtle.deriveKey({ name: 'HKDF', hash: 'SHA-256', salt: enc.encode('therasocial-e2ee-v1'), info: enc.encode(lo + ':' + hi) },
                hk, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
        })();
        entry.p.catch(function () { if (pairCache[partnerId] === entry) delete pairCache[partnerId]; });
        pairCache[partnerId] = entry;
        return entry.p;
    }
    async function encryptText(text, partnerId) {
        var key = await pairKey(partnerId, false);
        if (!key) return null;
        var iv = rand(12);
        var ct = await subtle.encrypt({ name: 'AES-GCM', iv: iv, additionalData: enc.encode(S.uid + '>' + partnerId) }, key, enc.encode(text));
        return PREFIX + b64u(iv) + ':' + b64u(ct);
    }
    async function decryptText(content, senderId, recipientId, partnerId) {
        if (typeof content !== 'string' || content.indexOf(PREFIX) !== 0) return content;   // older plain-text message
        if (!S.priv) return T('locked_ph');
        var parts = content.slice(PREFIX.length).split(':');
        if (parts.length !== 2) return T('undecr_ph');
        for (var attempt = 0; attempt < 2; attempt++) {
            try {
                var force = attempt === 1 && Date.now() - (forceAt[partnerId] || 0) > 30000;   // at most one forced re-read per partner per 30 s
                if (force) forceAt[partnerId] = Date.now();
                var key = await pairKey(partnerId, force);   // 2nd try re-reads the partner's current public key
                if (!key) break;
                var pt = await subtle.decrypt({ name: 'AES-GCM', iv: unb64u(parts[0]), additionalData: enc.encode(senderId + '>' + recipientId) }, key, unb64u(parts[1]));
                return dec.decode(pt);
            } catch (_) { /* try again with a fresh public key, then give up */ }
        }
        return T('undecr_ph');
    }

    // ------------------------------------------------------------------ message moderation (client-side now)
    // Exact port of ContentModerator.check_content() in security.py (A26): the server can no longer read
    // an encrypted message, so the same rules run here BEFORE encryption.
    //   crisis wording        -> message is delivered, sender sees the support notice (crisis=1)
    //   prohibited wording    -> message is refused (same text the server used)
    //   concerning wording    -> support notice, unless the text also asks for help
    var MOD = {
        crisis: [/\b(?:suicide|self.?harm|kill.?myself)\b/i, /\b(?:end.?it.?all|no.?point.?living)\b/i],
        harmful: [/\bsuicid(?:e|al)\b/i, /\bself[- ]?harm\b/i, /\bkill[- ]?myself\b/i, /\bcut[- ]?myself\b/i, /\boverdos(?:e|ing)\b/i, /\bend[- ]?my[- ]?life\b/i],
        prohibited: [/\bkill[- ]?yourself\b/i, /\bcut[- ]?yourself\b/i, /\bharm[- ]?yourself\b/i, /\bend[- ]?your[- ]?life\b/i,
                     /\bgo\s+(?:die|kill\s+yourself)\b/i, /\byou\s+(?:should|deserve\s+to|ought\s+to)\s+(?:die|overdose|kill\s+yourself)\b/i],
        help: ['help', 'support', 'crisis', 'emergency', 'therapist', 'counselor', 'hotline']
    };
    function anyRe(list, s) { for (var i = 0; i < list.length; i++) if (list[i].test(s)) return true; return false; }
    // returns 'prohibited' | 'crisis' | null
    function moderate(text) {
        try {
            var lower = String(text).toLowerCase();
            if (anyRe(MOD.crisis, lower)) return 'crisis';
            var concern = anyRe(MOD.harmful, lower);
            if (anyRe(MOD.prohibited, lower)) return 'prohibited';
            if (concern && !MOD.help.some(function (k) { return lower.indexOf(k) !== -1; })) return 'crisis';
        } catch (_) {}
        return null;
    }

    // ------------------------------------------------------------------ F12 rev 2: manage at any time
    // Status from what this page already knows (no network): 'signed_out' | 'unknown' | 'off' | 'locked' | 'on'.
    function statusNow() {
        if (!S.uid) return 'signed_out';
        if (!S.server) return 'unknown';
        if (!S.server.has_key) return 'off';
        return S.priv ? 'on' : 'locked';
    }
    function lockDevice() {
        // Remove this device's key (memory + IndexedDB); keep who is signed in, so the controls stay visible.
        S.priv = null; S.fp = null; pubCache = {}; pairCache = {};
        idbOp('readwrite', function (st) { return st.delete('dev'); }).catch(function () {});
        setDeclined(true);            // do not ask again in this tab until the member chooses to unlock
    }
    var managing = false;
    async function manage() {
        if (managing) return;
        managing = true;
        try {
            setDeclined(false);
            var ready = await safeReady(false);
            var uid = S.uid;
            if (!uid) return;
            if (!ready) {
                var t0 = Date.now();
                ready = await safeReady(true);              // shows "Turn on" or "Unlock" as needed
                if (ready) toast('ready_ok', 'success'); else if (S.dismissedAt >= t0) setDeclined(true);
            } else {
                var res = await dialog({ mode: 'manage', run: runFor(uid), lock: lockDevice });
                if (res === 'changed') toast('changed_ok', 'success');
                else if (res === 'locked') toast('locked_ok', 'info');
            }
        } finally { managing = false; refreshUI(); }
    }
    var PILL = 'display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border-radius:999px;border:1px solid #CFD8E3;background:#fff;color:#3D4852;font-size:13px;font-weight:600;cursor:pointer;line-height:1.3;';
    function pillFor(host, css) {
        var b = host.querySelector('#tsE2EEPill');
        if (!b) {
            b = document.createElement('button'); b.type = 'button'; b.id = 'tsE2EEPill';
            b.addEventListener('click', manage);
            host.appendChild(b);
        }
        b.style.cssText = PILL + css;
        return b;
    }
    function refreshUI() {
        try {
            var st = statusNow();
            var show = st === 'on' || st === 'locked' || st === 'off';
            var sig = st + ':' + lang();
            // Nothing changed and both places are already up to date: do not touch the page (the observer
            // below would otherwise see our own edits and call this again).
            var pOld = document.getElementById('tsE2EEPill'), cOld = document.getElementById('tsE2EESettings');
            var needPill = document.querySelector('#messagesView > h2') || document.querySelector('.conversations-sidebar .sidebar-header');
            if ((!needPill || (pOld && pOld.getAttribute('data-sig') === sig)) && (!cOld || cOld.getAttribute('data-sig') === sig)) {
                if (st === 'unknown' || st === 'signed_out') primeStatus((cOld && cOld.offsetParent !== null) || (pOld && pOld.parentNode && pOld.parentNode.offsetParent !== null) || (needPill && needPill.offsetParent !== null));
                return;
            }
            // 1. Messages heading (index.html) or the Circles messages sidebar header (circles-messages.js)
            var h = document.querySelector('#messagesView > h2');
            var host = null, css = '';
            if (h) {
                host = document.getElementById('tsE2EEPillRow');
                if (!host) { host = document.createElement('div'); host.id = 'tsE2EEPillRow'; host.style.cssText = 'margin:-8px 0 14px;'; h.parentNode.insertBefore(host, h.nextSibling); }
            } else {
                host = document.querySelector('.conversations-sidebar .sidebar-header');
                css = 'margin-top:8px;';
            }
            if (host) {
                var b = pillFor(host, css);
                b.setAttribute('data-sig', sig);
                b.style.display = show ? 'inline-flex' : 'none';
                if (st === 'on') { b.textContent = T('pill_on'); b.style.background = '#EEF4EF'; b.style.borderColor = '#CFE0D2'; b.style.color = '#3F6B4A'; }
                else b.textContent = T(st === 'locked' ? 'pill_locked' : 'pill_off');
            }
            // 2. Settings > Account card (index.html placeholder #tsE2EESettings)
            var card = document.getElementById('tsE2EESettings');
            if (card) {
                card.setAttribute('data-sig', sig);
                card.style.display = show ? '' : 'none';
                if (show) {
                    card.textContent = '';
                    card.setAttribute('dir', (lang() === 'he' || lang() === 'ar') ? 'rtl' : 'ltr');
                    var t = document.createElement('h3'); t.style.cssText = 'color:var(--primary,#5A7A93);margin-bottom:12px;'; t.textContent = T('settings_title');
                    var d = document.createElement('p'); d.style.cssText = 'color:#6B7280;margin-bottom:16px;line-height:1.5;'; d.textContent = T(st === 'on' ? 'status_on' : st === 'locked' ? 'status_locked' : 'status_off');
                    var row = document.createElement('div'); row.style.cssText = 'display:flex;gap:10px;flex-wrap:wrap;';
                    var main = document.createElement('button'); main.type = 'button'; main.className = 'btn btn-primary'; main.style.width = 'auto';
                    main.textContent = st === 'on' ? T('btn_change_pass') : st === 'locked' ? T('btn_unlock') : T('btn_create');
                    main.addEventListener('click', manage);
                    row.appendChild(main);
                    if (st === 'on') {
                        var lk = document.createElement('button'); lk.type = 'button'; lk.className = 'btn btn-secondary'; lk.style.width = 'auto';
                        lk.textContent = T('btn_lock');
                        lk.addEventListener('click', function () { lockDevice(); toast('locked_ok', 'info'); refreshUI(); });
                        row.appendChild(lk);
                    }
                    card.appendChild(t); card.appendChild(d); card.appendChild(row);
                    if (st === 'on') { var hn = document.createElement('p'); hn.style.cssText = 'color:#6B7280;margin-top:12px;font-size:13px;line-height:1.45;'; hn.textContent = T('lock_hint'); card.appendChild(hn); }
                }
            }
            // Status not known yet but one of the places is on screen: look it up once (no prompt).
            var visible = (card && card.offsetParent !== null) || (host && host.offsetParent !== null);
            if (st === 'unknown' || (st === 'signed_out' && visible)) primeStatus(visible);
        } catch (_) {}
    }
    var primeAt = 0;
    function primeStatus(visible) {
        if (!visible || Date.now() - primeAt < 30000) return;
        primeAt = Date.now();
        safeReady(false).then(refreshUI, refreshUI);
    }
    var uiQueued = false;
    function queueUI() { if (uiQueued) return; uiQueued = true; setTimeout(function () { uiQueued = false; refreshUI(); }, 150); }
    function startUI() {
        refreshUI();
        try {
            // Views are shown/re-rendered by the app at any time (the Circles messages panel is built by
            // circles-messages.js); re-place the button and card when the page changes. Cheap: two lookups.
            new MutationObserver(queueUI).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style'] });
        } catch (_) {}
        window.addEventListener('languageChanged', queueUI);
    }
    window.__tsE2EE.manage = manage;
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', startUI); else startUI();

    // ------------------------------------------------------------------ the fetch wrappers
    async function sendFlow(input, init, retried) {
        var body;
        try { body = JSON.parse(init.body); } catch (_) { return prevFetch(input, init); }
        if (!body || typeof body.content !== 'string' || !body.recipient_id) return prevFetch(input, init);
        // Over the 5000-character limit: let the server answer exactly as it always did (it never sees the text of an encrypted message).
        if (Array.from(body.content.trim()).length > 5000) return jsonResp(400, { error: 'Message too long. Maximum 5000 characters allowed.' });   // F12: refused here, so the text never reaches the server (same wording as the server)
        var partnerId = parseInt(body.recipient_id, 10);
        var verdict = moderate(body.content);
        if (verdict === 'prohibited') return blocked('Content contains prohibited terms');
        var tStart = Date.now();
        // Ask again only if this member has a key to unlock (needed to encrypt) or has not declined setting one up.
        var ready = await safeReady(true, function (sk) { return sk.has_key || !S.declined; });
        if (ready) setDeclined(false); else if (S.dismissedAt >= tStart) setDeclined(true);
        if (!ready) {
            // Not unlocked/set up. Let the server decide: while rolling out (transitional) it accepts plain text
            // unless BOTH members have keys; otherwise it refuses and the member is told why.
            var r1 = await prevFetch(input, init);
            var hasOwnKey = !!(S.server && S.server.has_key);
            if (r1.ok) { noticeOnce(hasOwnKey ? 'notice_locked' : 'notice_self', partnerId); return r1; }
            if (r1.status === 400) {
                try {
                    var d1 = await r1.clone().json();
                    if (d1 && d1.e2ee_error && !hasOwnKey && !retried) {
                        // Refused because the sender has no key and earlier declined setup: offer setup once more, then retry.
                        if (await safeReady(true)) return sendFlow(input, init, true);
                    } else if (d1 && d1.e2ee_error === 'plaintext_refused' && hasOwnKey) {
                        return localError('no_unlock_send', 'locked');
                    }
                } catch (_) {}
            }
            return annotate(r1);
        }
        // The key may have been reset on another device/tab since this one unlocked: never encrypt with a stale key.
        if (Date.now() - S.serverT > 30000) {
            var cur = await getServerKey(true).catch(function () { return null; });
            if (cur && cur.public_key && S.fp && fpOf(cur.public_key) !== S.fp) {
                S.priv = null; S.fp = null; pairCache = {};
                if (!(await safeReady(true))) return localError('no_unlock_send', 'locked');
            }
        }
        // Always look the recipient's key up afresh when sending, so a recipient who has just turned on
        // private messaging (or reset their key) is picked up at once.
        var lookupP = getPub(partnerId, true);
        var lookup = pubCache[partnerId];   // F12: this send's own lookup, captured before a parallel read can replace it
        await lookupP;
        var cipher;
        try { cipher = await encryptText(body.content, partnerId); }
        catch (_) { return localError('err_generic', 'encrypt_failed'); }
        if (!cipher) {
            // F12: only a CONFIRMED "no key" (404) may fall back to plain text; a failed lookup stops here.
            if (!lookup || !lookup.none) return localError('err_generic', 'lookup_failed');
            // Recipient has no key yet: send as before; the server decides (it refuses when private messaging is required).
            var r0 = await prevFetch(input, init);
            if (r0.ok) noticeOnce('notice_plain', partnerId);
            return annotate(r0);
        }
        var out = {};
        for (var k in body) if (Object.prototype.hasOwnProperty.call(body, k)) out[k] = body[k];
        out.content = cipher; out.e2ee = 1; out.crisis = verdict === 'crisis' ? 1 : 0;
        var opts = {};
        for (var o in init) if (Object.prototype.hasOwnProperty.call(init, o)) opts[o] = init[o];
        opts.body = JSON.stringify(out);
        return annotate(await prevFetch(input, opts));
    }
    var noticed = {};   // F12: plain-text notice shown once per person per page
    function noticeOnce(key, partnerId) { if (noticed[key + ':' + partnerId]) return; noticed[key + ':' + partnerId] = 1; toast(key, 'warning'); }
    function safeReady(allow, ask) { return ensureReady(allow, ask).catch(function () { return false; }).then(function (v) { queueUI(); return v; }); }
    function blocked(text) {      // refused here instead of by the server (same wording the server used)
        if (typeof window.apiCall !== 'function') toastText(text, 'error');
        return jsonResp(400, { error: text });
    }
    function localError(key, code) {
        if (typeof window.apiCall !== 'function') toast(key, 'error');   // circles page shows only a generic error otherwise
        return jsonResp(400, { error: T(key), e2ee_error: code });
    }
    // Swap the server's English e2ee error codes for the member's language.
    async function annotate(resp) {
        if (resp.ok || resp.status !== 400) return resp;
        try {
            var d = await resp.clone().json();
            if (d && d.e2ee_error && MSG[d.e2ee_error]) {
                if (typeof window.apiCall !== 'function') toast(d.e2ee_error, 'error');
                d.error = T(d.e2ee_error);
                return jsonResp(400, d);
            }
        } catch (_) {}
        return resp;
    }

    function hasCipher(s) { return typeof s === 'string' && s.indexOf(PREFIX) === 0; }
    function anyCipher(data) {
        var scan = function (arr, f) { return (arr || []).some(function (m) { return m && hasCipher(f(m)); }); };
        return scan(data.messages, function (m) { return m.content; }) || scan(data.sent, function (m) { return m.content; }) ||
               scan(data.received, function (m) { return m.content; }) ||
               scan(data.conversations, function (c) { return c.last_message && c.last_message.content; }) ||
               scan(data.messages_sent, function (m) { return m.content; }) || scan(data.messages_received, function (m) { return m.content; });
    }

    async function readFlow(input, init, kind, url) {
        var resp = await prevFetch(input, init);
        if (!resp.ok) return resp;
        var data;
        try { data = await resp.clone().json(); } catch (_) { return resp; }
        if (!data || typeof data !== 'object') return resp;
        var cipher;
        try { cipher = anyCipher(data); } catch (_) { return resp; }
        try {
            if (kind === 'export') {
                if (!cipher) return resp;
                await safeReady(true);
                if (!S.priv) { toast('export_locked', 'warning'); return resp; }   // leave the export exactly as the server sent it
            } else {
                // Ask when there is something to unlock, or when this member has no key at all yet
                // (so others can message them securely). Never nag again after "Not now".
                var tAsk = Date.now();
                var ready = await safeReady(!S.declined, function (sk) { return cipher || !sk.has_key; });
                if (!ready && !S.priv && !S.declined && S.dismissedAt >= tAsk) setDeclined(true);   // only when a dialog was actually dismissed
                if (!cipher) return resp;
            }
        } catch (_) { return resp; }
        var me = await getMe();
        try {
            var jobs = [];
            var fix = function (m, sId, rId, pId) { jobs.push(decryptText(m.content, sId, rId, pId).then(function (t) { m.content = t; })); };
            var wantId = parseInt(url.searchParams.get('recipient_id'), 10);
            (data.messages || []).forEach(function (m) {
                if (!m || !m.sender || !m.recipient) return;
                fix(m, m.sender.id, m.recipient.id, wantId || (m.sender.id === me ? m.recipient.id : m.sender.id));
            });
            (data.sent || []).forEach(function (m) { if (m && m.sender && m.recipient) fix(m, m.sender.id, m.recipient.id, m.recipient.id); });
            (data.received || []).forEach(function (m) { if (m && m.sender && m.recipient) fix(m, m.sender.id, m.recipient.id, m.sender.id); });
            (data.conversations || []).forEach(function (c) {
                if (!c || !c.user || !c.last_message) return;
                var own = c.last_message.is_own === true, pid = c.user.id;
                fix(c.last_message, own ? me : pid, own ? pid : me, pid);
            });
            (data.messages_sent || []).forEach(function (m) { if (m) fix(m, me, m.recipient_id, m.recipient_id); });
            (data.messages_received || []).forEach(function (m) { if (m) fix(m, m.sender_id, me, m.sender_id); });
            await Promise.all(jobs);
        } catch (_) { return resp; }
        return jsonResp(resp.status, data);
    }

    window.fetch = function (input, init) {
        try {
            if (typeof input !== 'string') return prevFetch(input, init);   // the app always passes a string URL here
            var u = pathOf(input);
            if (!u) return prevFetch(input, init);
            var method = String((init && init.method) || 'GET').toUpperCase();
            var p = u.pathname;
            if (p === '/api/messages' && method === 'POST' && init && init.body) return sendFlow(input, init);
            if (p === '/api/messages' && method === 'GET') return readFlow(input, init, 'messages', u);
            if (p === '/api/messages/conversations' && method === 'GET') return readFlow(input, init, 'conversations', u);
            if (p === '/api/user/export-data' && method === 'GET') return readFlow(input, init, 'export', u);
            if (method === 'POST' && p.indexOf('/api/auth/') === 0 && p !== '/api/auth/logout') S.uidT = 0;   // F12: sign-in may change who is signed in
            if (p === '/api/auth/logout' && method === 'POST') {
                return Promise.race([clearLocal(), new Promise(function (r) { setTimeout(r, 500); })]).then(function () { return prevFetch(input, init); });
            }
            if (method === 'POST' && p.indexOf('/api/auth/') === 0) return prevFetch(input, init).then(function (r) { S.uidT = 0; return r; });   // F12: and again once the sign-in has completed
        } catch (_) { /* fall through to the untouched request */ }
        return prevFetch(input, init);
    };
})();
