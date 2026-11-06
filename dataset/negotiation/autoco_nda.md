# AutoCo NDA (Meridian Law) — negotiation timeline
Rounds: 6 turns over 13 days (Oct 22, 2026 first draft → Nov 4, 2026 counsel engagement put on hold; AutoCo's own form still in AutoCo legal review, unsigned).

| Turn | Date | Version (anonymized filename, or "not in set") | Side | What changed (paraphrase) | Answers which earlier ask or turn |
|---|---|---|---|---|---|
| 0 | Oct 20 | not in set (video call) | AuditCo + counterparty | Proof-of-concept call. AutoCo raised model-training risk as its reason for wanting an NDA, asked how AI tooling is isolated, and offered to host AuditCo's models on its own GPU servers. | — |
| 1 | Oct 22 | `originals/AuditCo_ChipCo_NDA_ready_to_sign.docx` (base form) + `originals/AuditCo - AutoCo Mutual NDA (draft).docx` | AuditCo | AuditCo copied a mutual NDA it had used with another counterparty (Korean law, Seoul court, 3-year term), added a "Use with AI Systems" section (purpose-only training, no third-party AI services, vulnerability non-disclosure, agreed processing environment) under a single email-consent override, and sent both files to its counsel asking to stay close to the base form. | Turn 0 (call); internal pre-review (term, start date, signer) |
| 2 | Oct 23 | not in set | AuditCo → AuditCo counsel | Answered counsel's intake questions: legal names and addresses; only AutoCo's vehicle security team receives information for now; [AutoCo US affiliate] and a US plant may join later, preferably without a new NDA. | Counsel's intake request |
| 3 | Oct 27 | `AuditCo - AutoCo Mutual NDA (2026.10.26 AUDITCO DRAFT).docx` | AuditCo counsel | Kept base structure, law and forum. Moved the consent override so only the third-party-AI item can be waived by consent, and limited that consent to non-retaining, non-training providers. Added: GPU-server deployment to the Purpose; analyses and results as Confidential Information; equivalent-obligation requirement for Representatives; vehicle-security-team access limit and affiliate joinder (§2.3, §12.3); "legally required" standard for compelled disclosure; return/destruction of trained models (§8); a firmware reverse-engineering authorization that "does not extend to the Company’s models" (§9). | Turns 1–2 |
| 4 | Oct 28 | not in set (clean copy dated 10.27) | AuditCo → counterparty | Sent counsel's version as a clean draft and asked whether AutoCo would rather use its own standard NDA, plus legal name and signer. | Turn 3; internal reviewer's earlier advice |
| 5 | Oct 29 | not in set (AutoCo standard form) | Counterparty | AutoCo asked to proceed on its own standard Korean-language NDA to move faster and supplied entity and signer details. Counsel's draft is abandoned here. | Turn 4 question |
| 6a | Oct 29 | not in set (internal markup) | AuditCo (internal) | Marked up AutoCo's form with the earlier AI protections, a pre-existing-IP carve-out from the improvements article, a mutual marking rule, deletion of the one-sided penalty, and a definition of the project. | Internal risk review of AutoCo's form |
| 6b | Oct 30 | not in set (AutoCo form, filled in) | AuditCo → counterparty | Pared back to a fill-in-only version: party details completed and the optional one-sided penalty paragraph removed; the other protective edits were dropped. Sent to AutoCo. | Turn 5; speed over terms |
| 7 | Nov 2 | not in set | Counterparty | AutoCo said its internal legal review must finish before signature. | Turn 6b |
| — | Nov 3–4 | not in set | AuditCo counsel ↔ AuditCo | Counsel checked in; AuditCo put counsel's work on hold because AutoCo's own form was being used. | Turn 5 |

## Internal asks → did they land?
| Ask (paraphrased) | Origin | Landed? | Where (version + §) |
|---|---|---|---|
| No training on the other side's information except a model used only for the Purpose | Call (AutoCo raised training risk); the purpose-only exception is AuditCo's wording | yes — strengthened: no longer waivable by consent | 2026.10.26 redline §3(a) |
| No submission to third-party AI models, APIs or cloud without consent | Partly call; partly an earlier email from AutoCo's US affiliate about cloud limits; "prior written consent" is AuditCo's wording | yes — tightened (consent limited to non-retaining, non-training providers) | 2026.10.26 redline §3(b) |
| No disclosure of found vulnerabilities to vendors, bug bounties or public databases without written agreement | AuditCo's own ask (not raised on the call) | yes | 2026.10.26 redline §3(c) |
| Process PoC data only in a jointly agreed environment, possibly AutoCo's own infrastructure | Call (AutoCo offered its GPU servers) | yes | 2026.10.26 redline §3(d) |
| Protect AuditCo's models when deployed on AutoCo servers (ownership, no copying, deletion) | AuditCo's own ask (deployment was discussed on the call, protections were not); not included in the request sent to counsel | partly — counsel added deployment to the Purpose, excluded AuditCo's models from the reverse-engineering permission and added trained models to return/destruction, but there is no express ownership, no-copy or deletion clause for AuditCo's models | 2026.10.26 redline recital, §8, §9 |
| Let affiliates join later without a new NDA | Email to counsel | yes | 2026.10.26 redline §2.3, §12.3 |
| Ask AutoCo whether it has its own NDA before drafting | Internal chat (pre-review) | no — asked only after counsel's draft (Turn 4); the prediction came true | Turns 4–5 |
| 2–3 year term | Internal chat (pre-review) | yes (3 years, carried from the base form) | 2026.10.26 redline §7 |
| Cover disclosures made before signing | Internal chat (pre-review) | yes (definition covers information provided before the Effective Date) | 2026.10.26 redline §1 |
| Drop "log and email analysis" from the Purpose to avoid personal data | Internal chat (pre-review) | no — still in the Purpose | 2026.10.26 redline recital (b) |
| AutoCo form: exclude pre-existing models, tools and know-how from the improvements hand-over | Internal review of AutoCo's form | no — drafted in 6a, dropped from the version sent | not in set (Turn 6b) |
| AutoCo form: make the "must be marked confidential" rule mutual | Internal review of AutoCo's form | no — drafted in 6a, dropped | not in set (Turn 6b) |
| AutoCo form: delete the penalty that binds only AuditCo | Internal review of AutoCo's form | yes — removed in the version sent | not in set (Turn 6b) |
| AutoCo form: define the undefined "project" | Internal review of AutoCo's form | no — drafted in 6a, dropped | not in set (Turn 6b) |

## What triggered extra rounds
- Drafting on AuditCo's paper before asking whether AutoCo had its own NDA. The internal pre-review had predicted the switch; counsel's full turn (Turn 3) was discarded and three more turns (4, 5, 6b) followed on AutoCo's form.
- Counsel's intake round (Turn 2): editable files, entity names and the affiliate question were not in the first request.
- On AutoCo's form, AuditCo traded terms for speed: the protective markup (6a) was withdrawn before sending, so no counter-turn from AutoCo was needed, but three of the four flagged risks in AutoCo's form, and all of the AI protections, are absent from the document now under AutoCo's legal review.
