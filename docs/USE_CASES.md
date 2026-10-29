# Use cases and non-goals

## Good fits

- Text-heavy dashboards, settings pages, forms, terminals and browser chrome.
- Researching how much spatial text helps a fast text-only model navigate UI screenshots.
- Comparing encoder backends while holding the downstream chat interface constant.
- Extracting screen text/geometry without any hosted language-model call through `/v1/ocr`.

## Cautions

Tiny, rotated, low-contrast or decorative text can be missed. OCR cannot determine the purpose of an unlabeled icon, prove a button is enabled, read image semantics or infer a hidden application state. Geometric reading order is not a semantic layout graph. A coordinate center is not a guaranteed actionable target.

Treat screenshot text as untrusted data. Agent frameworks must maintain their own instruction hierarchy, action authorization, tool policy and recovery logic. Do not authorize a sensitive action just because screenshot text says to do so.

Do not use this experimental baseline as the sole input for safety-critical, financial, medical or irreversible UI actions. Measure task success, false clicks and recovery, not only token speed. Review screenshot privacy before sending extracted content to a hosted provider.
