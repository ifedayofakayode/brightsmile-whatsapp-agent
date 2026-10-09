# Setup guide

This guide takes you from an empty n8n account to a working BrightSmile WhatsApp assistant. Allow 60 to 90 minutes the first time.

> **Demo project.** BrightSmile is a fictional dental clinic. All prices, policies and addresses in the sample data are invented. Use only fake customer data while testing.

When you finish you will have:

- an n8n workflow that receives WhatsApp messages and replies,
- a Google Sheet that holds approved prices, FAQ answers, settings, leads, escalations and logs,
- a Google Calendar that receives bookings,
- Slack alerts for anything that needs a human,
- a second flow that sends a human's approved answer back to the customer.

After setup, run the checks in [`test-cases.md`](test-cases.md).

---

## 1. What you need

| Service | Used for | Notes |
|---|---|---|
| **n8n** (Cloud or self-hosted) | Runs the workflows | Must be reachable over **public HTTPS** so the WhatsApp gateway can call it |
| **Wassenger** | WhatsApp gateway | Links a WhatsApp number to an API. Check their current pricing and trial terms |
| **A spare WhatsApp number** | The assistant's number | Do not use your personal number (see Security notes) |
| **A second phone** | Playing the customer | You cannot message the assistant from its own number |
| **OpenAI account** | Intent classification (`gpt-4o-mini`) | Needs an API key with billing enabled |
| **Google account** | Sheets (data + CRM) and Calendar | Plus a Google Cloud project for OAuth |
| **Slack workspace** | Human alerts | A free workspace is enough |

---

## 2. Get the files

Clone or download this repository. You will use:

- `data/BrightSmile_Demo_Data.xlsx` for the sample data
- `workflows/*.json` for the n8n workflows
- `docs/test-cases.md` for the test plan

---

## 3. Prepare the Google Sheet

1. In Google Drive choose **New → Google Sheets**, then **File → Import → Upload** and select `BrightSmile_Demo_Data.xlsx`. Choose **Replace spreadsheet**.
2. Rename the spreadsheet `BrightSmile Demo DB`.
3. Check the tabs exist: `README`, `Pricing`, `FAQ`, `Business_Info`, `Prompt_Keys`, `Test_Messages`, `Leads`, `Escalations`, `Logs`.
4. **Delete row 2 (the grey EXAMPLE row)** in `Leads`, `Escalations` and `Logs`. Keep the header row.
5. **Keep phone numbers as text.** In `Leads`, `Escalations` and `Logs`, select the `phone` column and use **Format → Number → Plain text**. Otherwise Google turns `+2348...` into a plain number and lookups stop matching.
6. **Keep dates as text.** In `Pricing` and `FAQ`, the `last_updated` column holds text like `2026-10-06`. It should be left-aligned. If Google converted it to a date, set the column to Plain text and retype the values.
7. **Refresh the price dates.** The workflow refuses to quote a price older than `price_staleness_days` (30 by default, set in `Business_Info`). Set `last_updated` on every `Pricing` row to a date within the last 30 days, **except `clear_aligners`**, which is deliberately old so you can demo the stale-price check.
8. Leave the `premium_package` price blank. That is demo failure #1.
9. Review `Business_Info`: opening days and hours, timezone, minimum booking notice and the human response time all feed the replies.

Do not rename columns or tabs. The workflow reads them by name.

---

## 4. Connect Google

You will create one Google Cloud project and use it for three n8n credentials (Sheets, Sheets Trigger, Calendar).

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a project.
2. **APIs & Services → Library**: enable the **Google Sheets API** and the **Google Calendar API**.
3. **OAuth consent screen**: choose **External**, fill in the app name and your email, and add your Google account under **Test users**.
4. **Credentials → Create credentials → OAuth client ID → Web application**.
5. In n8n, open **Credentials → Create credential → Google Sheets OAuth2 API**. Copy the **OAuth Redirect URL** shown there into the client's **Authorized redirect URIs** in Google Cloud, then save.
6. Paste the **Client ID** and **Client Secret** into the n8n credential and click **Sign in with Google**.
7. Repeat for **Google Sheets Trigger OAuth2 API** and **Google Calendar OAuth2 API**, reusing the same client ID and secret.

> While the consent screen is in **Testing** mode, Google may expire the connection after about 7 days. If Sheets or Calendar suddenly fail, open the credential and sign in again.

**Create the demo calendar.** In Google Calendar create a new calendar called `BrightSmile Demo`, so the demo never touches your personal calendar. In its settings set the **time zone** to match your business (the sample uses Africa/Lagos).

---

## 5. Connect WhatsApp (Wassenger)

1. Create an account at [wassenger.com](https://www.wassenger.com), then link your **spare WhatsApp number** by scanning the QR code from the WhatsApp app (**Linked devices**).
2. Create an **API token** in the Wassenger dashboard and keep it private.
3. In n8n install the community node: **Settings → Community nodes → Install**, and enter `n8n-nodes-wassenger`. (On n8n Cloud, community node availability depends on your plan.)
4. Create a **Wassenger API** credential in n8n and paste the token.

The Wassenger Trigger registers its own webhook when you activate the workflow, so you do not configure URLs by hand.

---

## 6. Connect OpenAI

1. Create an API key at [platform.openai.com](https://platform.openai.com/api-keys) and make sure the account has billing credit.
2. In n8n create an **OpenAI API** credential and paste the key.

The workflow uses `gpt-4o-mini` at temperature 0. Classification calls are short and inexpensive.

---

## 7. Connect Slack

1. Go to [api.slack.com/apps](https://api.slack.com/apps), choose **Create New App → From scratch**, and pick your workspace.
2. Under **OAuth & Permissions → Bot Token Scopes** add `chat:write`.
3. Click **Install to Workspace** and copy the **Bot User OAuth Token** (it starts with `xoxb-`).
4. In n8n create a **Slack API** credential and paste the token.
5. Create two channels, for example `#support-escalations` and `#automation-errors`, and invite the app to both by typing `/invite @YourAppName` in each. Without this, Slack returns `not_in_channel`.

---

## 8. Import the workflows

1. In n8n choose **Workflows → ⋯ → Import from file** and import every file in `workflows/`.
2. If a node shows as "not installed", install the Wassenger community node (Step 5) and reopen the workflow.
3. Rename the imported workflows if you like. Nothing depends on the names, except the error workflow selection in Step 11.

The exported files contain **no credentials and no real IDs**. You reconnect everything below.

---

## 9. Connect credentials to the nodes

Open each workflow and select your credential on every node that shows a warning:

| Node type | Credential |
|---|---|
| Wassenger Trigger, both Wassenger send nodes | Wassenger API |
| OpenAI Chat Model | OpenAI API |
| All Google Sheets nodes | Google Sheets OAuth2 API |
| Google Sheets Trigger | Google Sheets Trigger OAuth2 API |
| Check Calendar, Create an event | Google Calendar OAuth2 API |
| Alert Human | Slack API |

---

## 10. Replace the placeholders

The export uses placeholders where your own IDs belong. In each node, open the field and choose your item **From list**:

| Placeholder | Where to set it |
|---|---|
| `YOUR_GOOGLE_SHEET_ID` | **Document** on every Google Sheets node and on the Google Sheets Trigger. Choose `BrightSmile Demo DB`, then reselect the **Sheet** (tab) on each node. |
| `YOUR_CALENDAR_ID` | **Calendar** on `Check Calendar` and `Create an event`. Choose `BrightSmile Demo`. |
| `YOUR_SLACK_CHANNEL_ID` | **Channel** on `Alert Human`. Choose your escalations channel. |
| `YOUR_WASSENGER_DEVICE_ID` | **Device** on the Wassenger Trigger and both send nodes. Choose your linked number. |

Tab names each node should point at:

| Node | Sheet tab |
|---|---|
| Load Config | `Business_Info` |
| Lookup Price, Lookup Duration | `Pricing` |
| Lookup FAQ | `FAQ` |
| Lookup Lead, Save Lead | `Leads` |
| Add Escalation, Google Sheets Trigger, both "Update row" nodes | `Escalations` |
| Write Log | `Logs` |

After saving, any node still showing a red warning triangle needs a credential or a selection.

---

## 11. Workflow settings

In the main workflow open **⋯ → Settings**:

1. **Timezone:** set it to your business timezone (the sample uses `Africa/Lagos`). This also makes the "Today is..." line in the AI prompt correct.
2. **Error Workflow:** after you create the error handler (below), select it here.

> The booking logic in the `Booking Check` node assumes **UTC+1 with no daylight saving** (Lagos). If your business is in another timezone, change the `3600000` offset values and the `+01:00` text in that node.

**Create the error handler (recommended).** Make a new workflow named `Global Error Handler` with an **Error Trigger** followed by a **Slack** message to your errors channel:

```
🚨 *n8n workflow failed*
*Workflow:* {{ $json.workflow?.name ?? 'unknown' }}
*Failed node:* {{ $json.execution?.lastNodeExecuted ?? 'unknown' }}
*Error:* {{ String($json.execution?.error?.message ?? 'no message').slice(0, 500) }}
*Open the run:* {{ $json.execution?.url ?? 'no link' }}
```

Save it, then select it under **Error Workflow** in every other workflow. It only fires for **production** runs, not manual test runs.

---

## 12. Check the AI prompt lists

The AI can only pick service and FAQ keys that exist in your data. The lists live in the **AI Agent → System Message**, and the system message field must be in **Expression** mode so `{{ $now ... }}` is evaluated.

If you change services or FAQs, regenerate the lists:

1. Open the `Prompt_Keys` tab.
2. Copy the generated text into the matching places in the system message (service key options, service key meanings, FAQ key options, FAQ key meanings).
3. If Google adds stray quotation marks around the copied lists, delete them.

---

## 13. Turn it on and run the first test

1. Make sure **only one copy** of each workflow is active. Two copies on the same trigger send double replies.
2. **Activate** the workflows (the toggle, called **Publish** in newer n8n versions).
3. From your **second phone**, message the assistant's number: `How much is teeth cleaning?`
4. You should receive: *"Thanks {name}! Scale & polish (teeth cleaning) is ₦25,000. Would you like to book a visit?"*
5. In n8n open **Executions**: the run should be green. In the sheet, `Logs` should have a new row.

If it works, continue with [`test-cases.md`](test-cases.md).

> **Testing with pinned data:** if you pin the trigger's sample data and re-run, **Remove Duplicates** will skip the message because it has already seen that ID. Unpin the data, or send a fresh message from your phone.

---

## 14. Optional: a switch to demo a calendar failure on demand

Failing the calendar live is clumsy. Add a row to `Business_Info` with key `simulate_calendar_failure` and value `no`. In the **Check Calendar** node set **Start Time** to this expression:

```
{{ $('Validate AI JSON').first().json.config.simulate_calendar_failure === 'yes' ? 'not-a-date' : $json.start }}
```

Setting the cell to `yes` should make the calendar call fail so the workflow takes the error path. Test it before relying on it, and set it back to `no` afterwards.

---

## 15. Changing the data later

- **New or changed prices:** edit `Pricing`, and update `last_updated` to today. Stale or blank prices escalate by design.
- **New service:** add a `Pricing` row with a unique `service_key`, then regenerate the AI prompt lists (Step 12).
- **New FAQ:** add a `FAQ` row (keep prices out of FAQ answers so `Pricing` stays the single source of truth), then regenerate the lists.
- Do not rename headers or tabs.

---

## 16. Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| No message reaches n8n | Workflow not active, the number is disconnected in Wassenger (scan the QR again), or you are messaging from the assistant's own number |
| Run stops at a lookup, customer gets no reply | **Always Output Data** is off. Turn it on in **Settings** of `Lookup Price`, `Lookup FAQ`, `Lookup Lead` and `Lookup Duration` |
| New customers never get a reply | Same cause as above (a new customer has no row in `Leads`) |
| Returning customers are not recognised, or duplicate rows appear | The `phone` column is not Plain text |
| Every price is escalated as stale | `last_updated` is older than 30 days, or Google converted it to a real date |
| Bookings appear one hour off | Calendar time zone is UTC. Set the Google Calendar and `BrightSmile Demo` time zones to your business timezone |
| `not_in_channel` from Slack | Invite the app to the channel with `/invite @YourAppName` |
| Sheets or Calendar stop working after about a week | The Google consent screen is in Testing mode. Sign in to the credential again |
| Double replies | Two active copies of the workflow |
| The assistant answers its own messages | The trigger is receiving outbound events. Keep **Events** set to `message:in:new` only |
| Human reply never arrives | The follow-up flow is inactive, or the row does not meet the conditions: `status` = `resolved`, `approved_reply` filled, `sent_at` empty. The trigger checks about once a minute |
| Error alerts never arrive | **Error Workflow** is not set, or the failing run was a manual test |
| A node says it is not installed | Install the Wassenger community node (Step 5) |

---

## 17. Security notes

- **Use a spare number.** Unofficial WhatsApp gateways link a normal account. That is fine for a demo, but it can conflict with WhatsApp's terms and put a number at risk. Do not use your main number.
- **Never commit credentials.** Keep raw n8n exports outside the repository and publish only sanitized files (`scripts/sanitize_workflow.py`). Pinned test data contains real phone numbers and must be removed.
- **Rotate keys** (OpenAI, Slack, Wassenger) after recording a public demo.
- **Use fake customer data** and a separate, throwaway Google Sheet for testing.
- Keep the Slack app's scopes minimal, and keep the Google consent screen restricted to test users.
