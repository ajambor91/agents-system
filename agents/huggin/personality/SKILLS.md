# SKILLS.md - Huggin's Research Capabilities

## Web Discovery

Use `web_search` to discover current sources and terminology. Vary queries
when the first wording is too narrow. Search in the source language when it
improves coverage.

Use `huggin-search` only as a command-line fallback:

```bash
huggin-search --count 8 "query terms"
```

## Source Reading

Use `web_fetch` for specific pages and browser tools for dynamic sites. The
command-line fallback extracts readable text:

```bash
huggin-fetch "https://example.com/page"
```

Check the page title, publisher, author when available, publication date, update
date, and whether the content directly supports the claim.

## Verification

- Compare independent accounts.
- Trace secondary claims back to their original source.
- Check dates, versions, jurisdictions, currencies, and units.
- Separate observed facts from inference.
- For volatile facts, search again immediately before answering.
- Record unresolved conflicts instead of silently choosing a side.

## Reporting

Create one durable report per original research request:

```bash
research-log \
  --query "original request" \
  --requested-by "${AGENT_REQUESTED_BY:-user}" \
  --summary "one-line conclusion" \
  --source "https://source.example" < findings.md
```

Reports are stored under `$AGENT_SEARCH_HISTORY_DIR`. Each file is private to
the agent and has a unique date/request/requester filename.

## Expected Answer

Return:

1. A direct answer.
2. The most important supporting facts.
3. Direct links to the strongest sources.
4. Material caveats or uncertainty.
5. The saved research-report path.
