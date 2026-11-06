# ClientCo MSA (Harbor Law) — negotiation timeline
Rounds: 6 turns over 17 days (March 2, 2026 first draft → March 19, 2026 signed; Effective Date set to March 23, 2026).

| Turn | Date | Version (anonymized filename) | Side | What changed (paraphrase) | Answers which earlier ask or turn |
|---|---|---|---|---|---|
| 1 | Mar 2 | `ClientCo - AUDITCO MSA - (HL Draft 3.2.26).docx` | AuditCo counsel | First MSA, built from the earlier evaluation agreement. Annual Fee $222,000 billed $18,500/month, net 30; $140 per Request over the monthly limit; one-year term with automatic renewal plus a unilateral AuditCo right to raise fees at renewal; 90-day termination for convenience; 10-day cure for payment default; broad release of AuditCo; liability cap = fees paid in the 12 months before the incident; no indemnity clause; Exhibit A states no monthly Request number. | AuditCo CEO's list of verbally agreed deal terms sent to counsel the same day. |
| 2 | Mar 10 | `originals/ClientCo - AUDITCO MSA (Crest LLP comments 3.10.26).docx` | Counterparty counsel | Governing law moved to Delaware; MSA supersedes the evaluation agreement; Unavailability narrowed to ClientCo's own maintenance; AuditCo's renewal fee-increase right deleted; payment-default cure 10 → 20 days; release of AuditCo deleted; AuditCo indemnity added (IP infringement, breach) and carved out of the cap; "Maximum Requests per month: 160" inserted into Exhibit A. | Turn 1. |
| 3 | Mar 12 | `ClientCo - AUDITCO MSA (Crest LLP comments 3.10.26)(HL Draft 3.12.26).docx` | AuditCo counsel | Accepted the 20-day cure and Delaware; made Unavailability mutual (either Party's scheduled maintenance, third-party-controlled infrastructure); in margin notes, offered to drop the release if those claims are treated as capped direct damages, asked to keep a (capped) fee-increase right, and asked for a mutual, capped indemnity. | Turn 2 (release deletion, fee-right deletion, uncapped indemnity, one-sided Unavailability). |
| 4 | Mar 12–13 | `originals/ClientCo - AUDITCO MSA (3.13.26).docx` | AuditCo (edits drafted by its counsel, sent by AuditCo) | Automatic renewal replaced by renewal only on mutual agreement, with renewal fees to be discussed; release replaced by a clause deeming claims from Unavailability or the Services to be capped direct damages; the separate uncapped-damages category narrowed to ownership, IP and confidentiality breaches; ClientCo indemnity added (misuse of Deliverables, misrepresentations to third parties); AuditCo's indemnity narrowed to claims brought as a direct result of its breach; internal-use, no-guarantee and no-third-party-warranty language added, with a carve-out for joint promotions approved in advance. | Turn 2 (fee-right and release deletions); AuditCo CEO's suggestion to switch to mutual renewal; CEO's concern that the no-warranty language could block a joint blog post. |
| 5 | Mar 17 | `originals/ClientCo - AUDITCO MSA (ClientCo comments 3.17.26).docx` | Counterparty (via its counsel) | Single insertion: each Party's liability for indemnification obligations is uncapped. | Turn 4 (indemnity had fallen back under the general cap). |
| 6 | Mar 18 | `ClientCo - AUDITCO MSA (ClientCo comments 3.17.26) (HL Draft 3.18.26).docx` | AuditCo counsel | "Uncapped" replaced with a super cap of $1,750,000 on each Party's indemnification obligations; margin note proposes that both Parties carry liability and E&O coverage instead of writing an insurance clause. | Turn 5; AuditCo CEO's ask to size the indemnity cap to the insurance AuditCo could actually buy. |
| — | Mar 19 | (no new file; final = HL Draft 3.18.26) | Counterparty counsel | Accepted the 3.18.26 version with the super cap; signed the same day. | Turn 6. |

## Internal asks → did they land?
| Ask (paraphrased) | Origin | Landed? | Where (version + §) |
|---|---|---|---|
| Annual Fee $222,000, billed monthly | email to counsel | yes | HL Draft 3.18.26, Exhibit A ($18,500/month) |
| 90-day opt-out | email to counsel | yes | HL Draft 3.18.26, Termination for Convenience (unchanged since 3.2.26) |
| 160 scans/month, $140 per extra scan | email to counsel | partly → yes | HL Draft 3.2.26 Exhibit A had the $140 overage but no monthly number; counterparty counsel inserted 160 in 3.10.26; present in 3.18.26 Exhibit A |
| Findings delivered as GitHub issues, no formal audit report | email to counsel | yes | HL Draft 3.18.26, Deliverables definition ("not individual audit reports") |
| Scope limited to ClientCo's monorepo | email to counsel | yes | HL Draft 3.18.26, Evaluation Scope / Services |
| No guarantee all bugs are found; AuditCo not liable for misses | email to counsel | changed | Warranty disclaimer kept; the broad release was deleted (3.10.26) and replaced by "deemed direct damages" under the 12-month-fee cap (3.13.26 onward), §12 |
| Unused scans roll over | email to counsel | partly (narrowed) | From HL Draft 3.2.26 onward, carry-over applies only to Requests lost to Unavailability, and only into the next month, §1(c); Unavailability made mutual in 3.12.26 |
| Liability capped at total fees paid up to the incident | email to counsel | partly | Implemented as fees paid in the 12 months preceding the incident (mutual), §12(b), every version |
| AuditCo excluded from ClientCo's bug bounties / audit contests | email to counsel | yes | HL Draft 3.18.26, AuditCo restrictions |
| No use of ClientCo's name/logo without written consent | email to counsel | yes | HL Draft 3.18.26, AuditCo restrictions |
| No public disclosure of findings without consent | email to counsel | yes | HL Draft 3.18.26, Vulnerabilities treated as Confidential Information |
| Keep a right to raise fees at renewal | internal discussion with counsel | changed | Deleted by counterparty counsel (3.10.26); replaced by mutual-agreement renewal with fees renegotiated (3.13.26 onward), §4(a) |
| Cap the indemnity; both sides are small | email to counsel | yes (after an extra round) | Super cap $1,750,000, HL Draft 3.18.26 §12(b) |
| Allow a joint blog post / reasonable endorsement | email to counsel | yes | 3.13.26 onward: no third-party warranties "except for joint promotions, joint public statements, or comments approved by AuditCo in advance" |

## What triggered extra rounds
- Turn 1 included a unilateral fee-increase right that was not part of the founders' deal → counterparty counsel deleted it in turn 2 → AuditCo's answer in turn 4 rewrote the whole Term clause into mutual-agreement renewal.
- Turn 1 had no indemnity and a broad release → turn 2 deleted the release and added an uncapped AuditCo indemnity → turns 3–4 rebuilt the liability section (deemed direct damages, mutual indemnities).
- Turn 4 put indemnities back under the general cap → turn 5 inserted "uncapped" → turn 6 settled on the $1,750,000 super cap; accepted the next day.
- Turn 1 left the agreed monthly Request number out of Exhibit A → counterparty counsel supplied it in turn 2 (no extra round, but the fix came from the other side).
