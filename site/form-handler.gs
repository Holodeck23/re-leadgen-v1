/**
 * Google Apps Script — receives form submissions from the landing page
 * and writes them to a Google Sheet.
 *
 * SETUP:
 * 1. Create a Google Sheet with these column headers in row 1:
 *    timestamp | name | email | phone | interest | budget | timeline | message | source | score | status | notes | follow_up_date
 * 2. Go to Extensions > Apps Script
 * 3. Paste this code
 * 4. Deploy > New Deployment > Web App
 *    - Execute as: Me
 *    - Who has access: Anyone
 * 5. Copy the deployment URL into site/index.html (replace YOUR_GOOGLE_APPS_SCRIPT_URL)
 */

function doPost(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = JSON.parse(e.postData.contents);

  sheet.appendRow([
    data.timestamp || new Date().toISOString(),
    data.name || '',
    data.email || '',
    data.phone || '',
    data.interest || '',
    data.budget || '',
    data.timeline || '',
    data.message || '',
    data.source || 'direct',
    '',        // score — filled by lead scorer agent
    'new',     // status
    '',        // notes — filled by agent
    ''         // follow_up_date — filled by agent
  ]);

  return ContentService
    .createTextOutput(JSON.stringify({ status: 'ok' }))
    .setMimeType(ContentService.MimeType.JSON);
}

function doGet(e) {
  return ContentService
    .createTextOutput(JSON.stringify({ status: 'ready' }))
    .setMimeType(ContentService.MimeType.JSON);
}
