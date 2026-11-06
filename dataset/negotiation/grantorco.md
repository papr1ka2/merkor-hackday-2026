# GrantorCo Foundation grant (Summit LLP) — negotiation timeline
Rounds: 6 turns over 86 days (2026-03-11 grant letter from GF → 2026-06-05 executed vendor services agreement), across two tracks: the main agreement and a separate NDA. The main agreement restarted once: grant letter → vendor services agreement.

| Turn | Date | Version (anonymized filename, or "not in set") | Side | What changed (paraphrase) | Answers which earlier ask or turn |
|---|---|---|---|---|---|
| 1 | 2026-03-11 | GF's original grant letter (not in set) | counterparty | Standard grant letter for US$172,000 in six tranches, plus Addendum I terms. Clause F requires funded software to be released under an open-source licence, with a full refund if breached. | — (opening draft, after a February scoping meeting) |
| — | 2026-03-19 → 03-26 | no draft | AuditCo counsel (Harbor Law) | Review only. Counsel flagged that the letter as written would require AuditCo to share essentially all funded work. | AuditCo's question on IP ownership under the grant |
| — | 2026-04-06 → 04-09 | no draft | AuditCo ↔ AuditCo counsel (Summit LLP) | AuditCo proposed splitting the code into deliverable packages ("grantor_modules", licensed in source) and private modules (binary only, licensed only as needed to run the deliverables). Counsel confirmed the narrower private-module licence is workable. | AuditCo's internal asks (see below) |
| 2 | 2026-04-10 (sent 04-13) | `GR-0001 SpecAgent - Grant Agreement (SL 4.10.26).docx`; `AuditCo - GF - Non-Disclosure Agreement (SL 4.10.26).docx` | AuditCo counsel | Inserted a licence limited to grantor_modules for GF's non-commercial internal use. Other AuditCo IP is licensed "solely as required" to use it. New Section C expressly supersedes the open-source/refund clause F. AuditCo may announce the grant publicly. Also offered a short one-way NDA protecting AuditCo. | Turn 1 (clause F); the module-split ask |
| 3 | 2026-04-24 (received ~04-27) | `originals/GAPL Vendor Services Agreement (AuditCo, Inc.) 20260424 (Draft).pdf` | counterparty | **Restart.** GF dropped the grant letter for a vendor services agreement with its Asia-Pacific entity (GAPL), under Singapore law. Its licence to GF overrode the deliverable/private split. The NDA became a GAPL-protective form in Schedule 2. Technical annex (redacted). | Turn 2: replaced it rather than marking it up |
| — | 2026-04-28 → 05-01 | no draft | AuditCo → AuditCo counsel; counsel issue list | AuditCo asked to narrow the licence and keep the core platform out; for a mutual NDA; for a liability cap tied to fees with mutual indemnity; and to fix how the relationship may be described publicly (GF as a "client"). Counsel's issue list covered the same points plus milestone specificity. | Turn 3 |
| 4 | 2026-05-07 / 05-08 | `AuditCo - Mutual Non-Disclosure Agreement (GF) (SL 5.7.26).docx`; `GAPL Vendor Services Agreement (AuditCo, Inc.) 20260424 (SL 5.8.26).docx` | AuditCo counsel | Heavy markup (≈190 tracked changes). All Engagement IP is owned by AuditCo and licensed to GAPL only for non-commercial internal use, with use restrictions (no open-sourcing, no third-party sublicensing without approval, no competing product). Also added: Background IP excluded, an as-is disclaimer, mutual indemnity, a liability limitation protecting only the Vendor, and a customer-reference/logo right. Payment changed to 30 days from the invoice date. The NDA became mutual with 5-year survival. | Turn 3; the 04-28 asks |
| 5 | 2026-05-28 | `… (SL 5.8.26) (GF edits).docx`; `AuditCo - Mutual Non-Disclosure Agreement (GF) (SL 5.7.26) (GF edits).docx` | counterparty | Accepted most of turn 4. Made the liability limitation mutual: no indirect damages, direct damages capped at fees paid in the prior 12 months, except breaches of §6 and §7.3. Put payment back to 30 days from receipt. Struck the customer-reference/logo carve-out. Deleted the indemnitor's defence-control sentence. Cut NDA survival from 5 to 2 years. | Turn 4 |
| 6 | 2026-05-29 → 06-04 | clean copy (not in set) | counterparty → AuditCo | Clean copy circulated. AuditCo accepted it without further changes. | Turn 5 |
| — | 2026-06-05 | executed agreement (not in set) | both | Signed. | — |
| — | 2026-06-10 / 06-15 | no draft | counterparty / AuditCo (internal) | After signing, GF asked AuditCo to describe the relationship as an engagement rather than a grant. Internally, AuditCo noted the deliverables would require handing over source code it had hoped to keep back. | Aftermath of turns 4–5 |

## Internal asks → did they land?
| Ask (paraphrased) | Origin | Landed? | Where (version + §) |
|---|---|---|---|
| AuditCo keeps full ownership of everything it builds | meeting notes (with counsel) | yes | SL 5.8.26 / GF edits §7.1: Engagement IP "owned solely by the Vendor"; Background IP stays with the Vendor |
| GF may run and modify the software but may not open-source or sublicense it | meeting notes | yes | GF edits §7.2: non-commercial internal licence, sublicensing only to Affiliates (others need Vendor approval); §7.3(a): no distribution "as open source or otherwise" |
| Licence limited to deliverable packages; private modules only "as required" to run them | email to counsel | changed | Landed in SL 4.10.26 grant letter §C. Lost in the restart: the VSA licenses all Engagement IP, with no module split |
| Neutralize the open-source-plus-full-refund clause | counsel review | yes, then moot | SL 4.10.26 §C supersedes Addendum I clause F; the grant letter was then abandoned |
| Core delivered as binaries only | meeting notes | no | Not in any VSA version; AuditCo noted after signing that source would have to be handed over |
| Mutual NDA instead of a GAPL-protective one | email to counsel | yes, shortened | SL 5.7.26 mutual NDA §5; GF edits cut survival from 5 to 2 years |
| Liability cap tied to fees, mutual indemnity with an overall cap | email to counsel | partly | GF edits: mutual limitation with a 12-month-fees cap on direct damages; indemnity is mutual but has no overall cap |
| Fix public positioning: call GF a "client", logo right | email to counsel | no | SL 5.8.26 Publicity carve-out struck in GF edits; wording dictated by GF after signing |

## What triggered extra rounds
- GF replaced the grant letter with a vendor services agreement from a different entity, under different governing law. That discarded turn 2 and added three more turns (3–5).
- The module split that turn 2 had won was overridden by GF's VSA licence. Licence scope had to be renegotiated from scratch in turn 4.
- AuditCo's request for a lightweight NDA opened a separate NDA track: one-way (4.10) → mutual (5.7) → GF's 2-year edit (5.28).
- AuditCo counsel's one-sided liability limitation (protecting only the Vendor) drew GF's mutualizing edit in turn 5.
- The customer-reference right AuditCo counsel inserted was struck by GF. The positioning issue came back after signing as a wording request.
