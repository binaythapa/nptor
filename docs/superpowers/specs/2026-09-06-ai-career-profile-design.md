# AI Career Profile Design

## Goal
Make the CV area AI-first by letting a user build one reusable Master Career Profile from an existing CV upload, a guided AI career interview, or manual editing.

## Product flow

```text
Career Profile entry
  ├─ Upload existing CV (PDF/DOCX)
  ├─ AI Career Interview
  └─ Edit manually
          ↓
  Proposed career facts
          ↓
  User confirmation
          ↓
  Master Career Profile
          ↓
  CV builder / ATS / tailoring / future cover letters
```

## Design decisions

1. The Master Career Profile remains the source of truth. AI never writes unconfirmed facts directly into it.
2. Existing CV import remains deterministic for extraction and stores unconfirmed `ImportedField` records. The user confirms or edits fields before they become trusted profile data.
3. The AI interview uses the existing `AIConversation`, `AIMessage`, and `AIExtraction` models. Conversations may be independent of a CV (`cv=NULL`).
4. Interview responses are persisted as messages and AI-produced structured facts are persisted as unconfirmed extractions.
5. The interview provider must be conservative: it may organize and ask about user-provided information, but must not invent employers, dates, qualifications, metrics, technologies, or achievements.
6. The first UI milestone is a Career Profile hub that exposes all three entry points and makes the existing CV upload discoverable. The interview UI supports a simple turn-by-turn flow and confirmation of extracted facts.
7. PDF/DOCX upload is limited to the existing 10 MB boundary and format validation. Uploaded files remain owner-scoped.

## AI interview contract

The provider returns JSON:

```json
{
  "reply": "string",
  "complete": false,
  "extractions": [
    {
      "section": "experience",
      "field_name": "job_title",
      "proposed_value": "string or object"
    }
  ]
}
```

`reply` is shown to the user. `extractions` become `AIExtraction` rows with `confirmed=false`. `complete=true` is only advisory and never bypasses confirmation.

## Confirmation

The user explicitly confirms individual interview extractions. Confirmed facts are applied only to safe, known Career Profile fields. Complex child records are represented as structured JSON until a later dedicated profile editor maps them into child models.

## Error handling

- Missing AI configuration produces a user-facing provider error without losing the user's message.
- Invalid provider JSON is rejected and not persisted as an extraction.
- Cross-user conversation or extraction access is rejected.
- Unsupported or malformed CV files are rejected before persistence.

## Testing

Cover:
- upload entry point is reachable from the career profile hub;
- CV upload creates only unconfirmed import facts;
- interview conversation creation is owner-scoped;
- interview provider response creates unconfirmed extractions;
- invalid provider output does not create trusted profile data;
- confirming an extraction records the user and timestamp;
- another user cannot confirm or inspect someone else's interview extraction;
- the existing CV import regression suite remains green.
