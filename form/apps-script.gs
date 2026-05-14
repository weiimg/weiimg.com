/**
 * weiimg.com /form 的後端接收程式
 * 部署在 Google Apps Script 作為 Web App。
 *
 * === 部署步驟 ===
 * 1. 開一份新的 Google Sheet（自訂名稱，例如「客戶報價資訊」）
 * 2. Sheet 上方選單 → 擴充功能 (Extensions) → Apps Script
 * 3. 把整份 apps-script.gs 內容貼到編輯器（取代預設 myFunction）
 * 4. 改下方 NOTIFY_EMAIL 為你要收通知信的 email
 * 5. 點右上角「部署 (Deploy)」→「新增部署作業 (New deployment)」
 *    - 類型：網頁應用程式 (Web app)
 *    - 執行身分：我 (Me)
 *    - 存取權：所有人 (Anyone)
 *    - 按部署，第一次會要求授權（允許）
 *    - 複製產出的 Web App URL（會像 https://script.google.com/macros/s/AKfy.../exec）
 * 6. 把該 URL 貼到 form/index.html 的 <form action="..."> 欄位
 *
 * === 之後想改 ===
 * - 修改這份 .gs 後在 Apps Script 編輯器點「部署 → 管理部署作業 → ✏️ 編輯」
 *   選新版本後重新部署。URL 保持不變。
 */

const NOTIFY_EMAIL = 'weiimg.img@gmail.com';

// Sheet 欄位順序（也決定 header row 內容）
const COLUMNS = [
    '時間',
    '聯絡人姓名',
    '聯絡電話',
    'Email',
    '發票類型',
    '公司抬頭',
    '統一編號',
    '發票寄送地址',
    '發票備註',
];

function doPost(e) {
    try {
        const data = e.parameter || {};

        // Honeypot：bot 會填、真人看不到
        if ((data['_gotcha'] || '').toString().trim()) {
            return jsonOut({ ok: true });
        }

        // 必填檢查
        const required = ['聯絡人姓名', '聯絡電話', 'Email', '發票類型', '發票寄送地址'];
        for (const f of required) {
            if (!data[f] || !data[f].toString().trim()) {
                return jsonOut({ ok: false, error: 'missing_' + f });
            }
        }

        const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];

        // 第一次執行時自動建立 header row
        if (sheet.getLastRow() === 0) {
            sheet.appendRow(COLUMNS);
            sheet.getRange(1, 1, 1, COLUMNS.length)
                 .setFontWeight('bold')
                 .setBackground('#f3f4f6');
            sheet.setFrozenRows(1);
        }

        // 寫入 row
        sheet.appendRow([
            new Date(),
            data['聯絡人姓名'] || '',
            data['聯絡電話']   || '',
            data['Email']      || '',
            data['發票類型']   || '',
            data['公司抬頭']   || '',
            data['統一編號']   || '',
            data['發票寄送地址'] || '',
            data['發票備註']   || '',
        ]);

        // 通知信（reply-to = 客戶 email，方便直接回覆對話）
        MailApp.sendEmail({
            to:       NOTIFY_EMAIL,
            replyTo:  data['Email'] || NOTIFY_EMAIL,
            subject:  '[新報價請求] ' + (data['聯絡人姓名'] || '') +
                      (data['公司抬頭'] ? ' — ' + data['公司抬頭'] : ''),
            htmlBody: buildNotificationHtml(data),
        });

        return jsonOut({ ok: true });
    } catch (err) {
        console.error(err);
        return jsonOut({ ok: false, error: 'server_error' });
    }
}

// 提供 GET 給瀏覽器直接打開時的健康檢查（避免顯示空白）
function doGet() {
    return jsonOut({ ok: true, note: 'This endpoint accepts POST only.' });
}

function jsonOut(obj) {
    return ContentService
        .createTextOutput(JSON.stringify(obj))
        .setMimeType(ContentService.MimeType.JSON);
}

function buildNotificationHtml(data) {
    const rows = [
        ['聯絡人姓名', data['聯絡人姓名']],
        ['聯絡電話',   data['聯絡電話']],
        ['Email',     data['Email']],
        ['發票類型',   data['發票類型']],
    ];
    if (data['公司抬頭'])     rows.push(['公司抬頭',     data['公司抬頭']]);
    if (data['統一編號'])     rows.push(['統一編號',     data['統一編號']]);
    if (data['發票寄送地址']) rows.push(['發票寄送地址', data['發票寄送地址']]);
    if (data['發票備註'])     rows.push(['發票備註',     data['發票備註']]);

    const tableRows = rows.map(function(pair) {
        return '<tr>' +
            '<td style="padding:8px 12px;color:#777;border-bottom:1px solid #eee;width:32%;">' +
                escapeHtml(pair[0]) + '</td>' +
            '<td style="padding:8px 12px;border-bottom:1px solid #eee;color:#2D2D2D;"><b>' +
                escapeHtml(pair[1]) + '</b></td>' +
        '</tr>';
    }).join('');

    return '<!doctype html><html><body style="margin:0;font-family:-apple-system,\'Segoe UI\',sans-serif;background:#f0f0f0;padding:24px;">' +
        '<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;padding:28px 32px;">' +
            '<h2 style="margin:0 0 20px;color:#2D2D2D;font-size:20px;letter-spacing:-0.02em;">新的客戶報價請求</h2>' +
            '<table style="width:100%;border-collapse:collapse;font-size:14px;">' + tableRows + '</table>' +
            '<p style="margin-top:24px;font-size:12px;color:#999;">— 經由 weiimg.com/form 自動寄送，回覆此信可直接聯絡客戶</p>' +
        '</div>' +
    '</body></html>';
}

function escapeHtml(s) {
    return String(s == null ? '' : s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
