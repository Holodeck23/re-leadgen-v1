/**
 * Google Apps Script — receives landing-page form submissions and writes
 * them to the lead sheet. Dedupes, validates, fires a server-side CAPI
 * Lead event, and alerts on high-intent interests.
 *
 * SETUP:
 *   1. Open the lead sheet. Headers in row 1 must be:
 *      timestamp | name | email | phone | interest | budget | timeline |
 *      message | source | score | status | notes | follow_up_date
 *   2. Extensions > Apps Script, paste this file.
 *   3. Script Properties (File > Project properties > Script properties):
 *        META_PIXEL_ID           (Meta Pixel numeric ID)
 *        META_CAPI_TOKEN         (Conversions API access token)
 *        META_TEST_EVENT_CODE    (optional; for Test Events panel)
 *        HOT_LEAD_WEBHOOK_URL    (optional; POSTed to on high-intent submits)
 *        HOT_LEAD_WEBHOOK_TOKEN  (optional; sent as Bearer token)
 *   4. Deploy > New Deployment > Web app
 *        Execute as: Me
 *        Who has access: Anyone
 *   5. Copy the /exec URL into site/index.html and site/thank-you.html
 *      (replacing REPLACE_WITH_DEPLOYED_APPS_SCRIPT_URL).
 *
 * The form payload fields (from site/index.html):
 *   name, phone, interest, source (pipe-delimited UTM string),
 *   referrer, return_visitor ("true"/"false"), submitted_at (ISO),
 *   event_id (UUID for Pixel/CAPI dedup), user_agent, page,
 *   adset_id (optional; Meta ad set ID from ?adset_id= URL param)
 *
 * The thank-you page sends a second request with action: "progressive_email"
 * containing { lead_id, event_id, email, interest }.
 */

var DEDUP_WINDOW_DAYS = 30;
var HOT_INTERESTS = ['lot', 'unit', 'investment'];

var COL = {
  timestamp: 1,
  name: 2,
  email: 3,
  phone: 4,
  interest: 5,
  budget: 6,
  timeline: 7,
  message: 8,
  source: 9,
  score: 10,
  status: 11,
  notes: 12,
  follow_up_date: 13
};

function doPost(e) {
  try {
    var payload = JSON.parse(e.postData.contents);
    var action = String(payload.action || 'new_lead');
    if (action === 'progressive_email') {
      return handleProgressiveEmail_(payload);
    }
    return handleNewLead_(payload);
  } catch (err) {
    return json_({ status: 'error', error: String(err) });
  }
}

function doGet(e) {
  return json_({ status: 'ready' });
}

/* ---------------- new_lead flow ---------------- */

function handleNewLead_(payload) {
  var cleaned = validate_(payload);
  if (cleaned.error) {
    return json_({ status: 'error', error: cleaned.error });
  }

  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var isDup = isDuplicate_(sheet, cleaned);
  var status = isDup ? 'duplicate' : 'new';
  // Canonical row id = the event_id the browser already generated for Pixel/CAPI dedup.
  // Keeping them equal means thank-you.html's `?lead_id=<event_id>` redirect lets
  // handleProgressiveEmail_ find the row without a round-trip to read the response.
  var leadId = cleaned.event_id || Utilities.getUuid();
  var timestamp = cleaned.submitted_at || new Date().toISOString();

  sheet.appendRow([
    timestamp,
    cleaned.name,
    '',                    // email — captured via progressive disclosure on thank-you page
    cleaned.phone,
    cleaned.interest,
    '',                    // budget — captured later
    '',                    // timeline — captured later
    '',                    // message — captured later
    cleaned.source,
    '',                    // score — filled by lead-scorer agent
    status,
    buildNotes_(leadId, cleaned),
    ''                     // follow_up_date — filled by follow-up skill
  ]);

  if (!isDup) {
    fireCapiLead_(cleaned, leadId, timestamp);
    if (isHotInterest_(cleaned.interest)) {
      fireHotLeadWebhook_({
        lead_id: leadId,
        event_id: cleaned.event_id,
        name: cleaned.name,
        phone: cleaned.phone,
        interest: cleaned.interest,
        source: cleaned.source,
        adset_id: cleaned.adset_id,
        referrer: cleaned.referrer,
        return_visitor: cleaned.return_visitor,
        submitted_at: timestamp
      });
    }
  }

  return json_({ status: status, lead_id: leadId, event_id: cleaned.event_id });
}

function buildNotes_(leadId, cleaned) {
  var parts = [
    'lead_id=' + leadId,
    'event_id=' + cleaned.event_id,
    'return_visitor=' + cleaned.return_visitor
  ];
  if (cleaned.adset_id) parts.push('adset_id=' + cleaned.adset_id);
  return parts.join('; ');
}

/* ---------------- progressive_email flow ---------------- */

function handleProgressiveEmail_(payload) {
  var leadId = String(payload.lead_id || '').trim();
  var email = String(payload.email || '').trim().toLowerCase();
  var eventId = String(payload.event_id || '').trim();
  if (!isValidEmail_(email)) return json_({ status: 'error', error: 'email_invalid' });
  if (!leadId)                return json_({ status: 'error', error: 'missing_lead_id' });

  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var row = findRowByLeadId_(sheet, leadId);
  if (row === -1) return json_({ status: 'error', error: 'lead_not_found' });

  // Write email into the email column; append a progressive-disclosure note.
  sheet.getRange(row, COL.email).setValue(email);
  var notesCell = sheet.getRange(row, COL.notes);
  var existing = String(notesCell.getValue() || '');
  var addition = 'email_source=progressive_disclosure; email_captured_at=' + new Date().toISOString();
  notesCell.setValue(existing ? existing + '; ' + addition : addition);

  fireCapiCompleteRegistration_(email, eventId, leadId);
  return json_({ status: 'ok', lead_id: leadId });
}

function findRowByLeadId_(sheet, leadId) {
  var last = sheet.getLastRow();
  if (last < 2) return -1;
  var notes = sheet.getRange(2, COL.notes, last - 1, 1).getValues();
  var target = 'lead_id=' + leadId;
  for (var i = 0; i < notes.length; i++) {
    if (String(notes[i][0] || '').indexOf(target) !== -1) return i + 2;
  }
  return -1;
}

/* ---------------- validation + dedup ---------------- */

function validate_(p) {
  var name = String(p.name || '').trim();
  var phone = String(p.phone || '').trim();
  var interest = String(p.interest || '').trim().toLowerCase();

  if (name.length < 2) return { error: 'name_too_short' };
  if (/https?:\/\//i.test(name)) return { error: 'name_contains_url' };

  var digits = phone.replace(/\D+/g, '');
  if (digits.length < 8) return { error: 'phone_invalid' };

  var validInterests = ['lot', 'unit', 'investment', 'visit', 'info'];
  if (validInterests.indexOf(interest) === -1) interest = 'info';

  return {
    name: name.slice(0, 120),
    phone: phone.slice(0, 40),
    phone_digits: digits,
    interest: interest,
    source: String(p.source || 'direct').slice(0, 500),
    referrer: String(p.referrer || '').slice(0, 500),
    return_visitor: String(p.return_visitor || 'false'),
    submitted_at: String(p.submitted_at || '').slice(0, 40),
    event_id: String(p.event_id || Utilities.getUuid()).slice(0, 64),
    adset_id: String(p.adset_id || '').slice(0, 40),
    user_agent: String(p.user_agent || '').slice(0, 500),
    page: String(p.page || '').slice(0, 500)
  };
}

function isDuplicate_(sheet, cleaned) {
  var last = sheet.getLastRow();
  if (last < 2) return false;

  var rows = sheet.getRange(2, 1, last - 1, COL.status).getValues();
  var cutoffMs = Date.now() - DEDUP_WINDOW_DAYS * 24 * 60 * 60 * 1000;

  for (var i = 0; i < rows.length; i++) {
    var r = rows[i];
    var ts = parseTimestamp_(r[COL.timestamp - 1]);
    if (ts === null || ts < cutoffMs) continue;
    var rowPhone = String(r[COL.phone - 1] || '').replace(/\D+/g, '');
    var rowStatus = String(r[COL.status - 1] || '').toLowerCase();
    if (rowPhone && rowPhone === cleaned.phone_digits && rowStatus !== 'closed' && rowStatus !== 'lost') {
      return true;
    }
  }
  return false;
}

function parseTimestamp_(value) {
  if (value instanceof Date) return value.getTime();
  if (!value) return null;
  var t = new Date(String(value)).getTime();
  return isNaN(t) ? null : t;
}

function isHotInterest_(interest) {
  return HOT_INTERESTS.indexOf(interest) !== -1;
}

function isValidEmail_(v) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
}

/* ---------------- Meta CAPI (server-side events) ---------------- */

function fireCapiLead_(cleaned, leadId, timestamp) {
  var user = {
    ph: [sha256_(cleaned.phone_digits)],
    client_ip_address: getRemoteIp_(),
    client_user_agent: cleaned.user_agent,
    external_id: [sha256_(leadId)]
  };
  var customData = {
    content_name: 'landing_form_submit',
    content_category: cleaned.interest,
    lead_event_source: 'landing_page'
  };
  sendCapiEvent_('Lead', cleaned.event_id, timestamp, user, customData, cleaned.page);
}

function fireCapiCompleteRegistration_(email, eventId, leadId) {
  if (!eventId) return;
  var user = {
    em: [sha256_(email)],
    external_id: [sha256_(leadId)]
  };
  var customData = {
    content_name: 'email_capture',
    lead_event_source: 'thank_you_page'
  };
  sendCapiEvent_('CompleteRegistration', eventId, new Date().toISOString(), user, customData, null);
}

function sendCapiEvent_(eventName, eventId, eventTimeIso, userData, customData, eventSourceUrl) {
  var props = PropertiesService.getScriptProperties();
  var pixelId = props.getProperty('META_PIXEL_ID');
  var token = props.getProperty('META_CAPI_TOKEN');
  if (!pixelId || !token) return; // Silently skip if CAPI not configured

  var body = {
    data: [{
      event_name: eventName,
      event_time: Math.floor(new Date(eventTimeIso).getTime() / 1000) || Math.floor(Date.now() / 1000),
      event_id: eventId,
      action_source: 'website',
      event_source_url: eventSourceUrl || undefined,
      user_data: userData,
      custom_data: customData
    }]
  };
  var testCode = props.getProperty('META_TEST_EVENT_CODE');
  if (testCode) body.test_event_code = testCode;

  var url = 'https://graph.facebook.com/v20.0/' + pixelId + '/events?access_token=' + encodeURIComponent(token);
  try {
    UrlFetchApp.fetch(url, {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(body),
      muteHttpExceptions: true
    });
  } catch (err) {
    console.error('capi_failed: ' + eventName + ' ' + err);
  }
}

function sha256_(value) {
  if (!value) return '';
  var bytes = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, String(value).trim().toLowerCase());
  return bytes.map(function (b) {
    var s = (b < 0 ? b + 256 : b).toString(16);
    return s.length === 1 ? '0' + s : s;
  }).join('');
}

function getRemoteIp_() {
  // Apps Script does not expose the client IP directly. Leave blank; EMQ
  // still benefits from hashed phone + external_id + user agent.
  return '';
}

/* ---------------- hot-lead webhook ---------------- */

function fireHotLeadWebhook_(body) {
  var props = PropertiesService.getScriptProperties();
  var url = props.getProperty('HOT_LEAD_WEBHOOK_URL');
  if (!url) return;
  var token = props.getProperty('HOT_LEAD_WEBHOOK_TOKEN');
  var headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = 'Bearer ' + token;
  try {
    UrlFetchApp.fetch(url, {
      method: 'post',
      contentType: 'application/json',
      headers: headers,
      payload: JSON.stringify(body),
      muteHttpExceptions: true
    });
  } catch (err) {
    console.error('hot_lead_webhook_failed: ' + err);
  }
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
