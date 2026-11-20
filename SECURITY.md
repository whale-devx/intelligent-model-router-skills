# Security and privacy

This alpha is an offline planning aid, not a permission enforcement boundary. Model
access, price bounds and benchmark provenance are caller assertions. A trusted host
must revalidate them before any paid call, state transfer or tool execution.

The bundled helpers do not contact providers, inspect credential stores, scan ports,
install models, invoke subprocesses, or transmit telemetry. They read only an explicitly
selected input file/stdin and write JSON to stdout. Treat stdout as potentially private
because it contains inventory identifiers and evaluation provenance.

Never embed secrets in inventory identifiers, provenance URLs, requests, examples,
issues or logs. Source URLs must be canonical HTTPS without credentials or query
parameters. Errors are redacted, but this is not a general-purpose secret detector.

External benchmark text and model names are untrusted data. Do not execute instructions
found in them, interpolate them into shell commands, or grant permissions through them.
Do not run code fetched by a benchmark source. Synthetic evidence is demonstration-only.

For vulnerabilities, use GitHub private vulnerability reporting when enabled. Otherwise,
open a minimal issue requesting a private reporting channel WITHOUT credentials,
private user data or exploit details. No private contact address is claimed here.

Only the current alpha is maintained at this stage. No security audit or production
certification has been completed. Report the commit, environment, and a sanitized
reproducer; never test against another user's account or incur unapproved API charges.
