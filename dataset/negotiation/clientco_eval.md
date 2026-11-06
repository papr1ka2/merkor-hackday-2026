# ClientCo Evaluation Agreement (Harbor Law) — negotiation timeline
Rounds: 5 turns over 19 days (January 22, 2026 first draft → February 10, 2026 signed). Turns 3 and 5 are not separate files in this set; their content is visible as accepted text and margin notes in the ClientCo 2.6.26 file and in the parties' later turns.

| Turn | Date | Version (anonymized filename) | Side | What changed (paraphrase) | Answers which earlier ask or turn |
|---|---|---|---|---|---|
| 1 | Jan 22 | `Evaluation Agreement - Pen Testing.docx` | AuditCo counsel | Free two-month evaluation in AuditCo's non-production environment; findings sent over a private GitHub channel; all Inputs, Outputs and Feedback owned by AuditCo and treated as AuditCo's Confidential Information; broad release of AuditCo; at the end ClientCo returns AuditCo materials and AuditCo keeps all Inputs, Outputs and Feedback. | AuditCo CEO's asks to counsel (own the client's inputs; protection from liability) and his answers to counsel's six intake questions. |
| 2 | Jan 28–29 | `originals/ClientCo - AuditCo Evaluation Agreement (Crest LLP 1.29.26).docx` | Counterparty counsel | Agreed AuditCo owns Outputs but deleted AuditCo's ownership of Inputs and Feedback; deleted the release; replaced the one-way confidentiality clause with a mutual one; added a survival list. | Turn 1. |
| 3 | Jan 30 – Feb 3 | (redline not in set; reflected in the 2.6.26 file) | AuditCo counsel | Refused the release deletion and reinserted it; proposed a compromise: ClientCo owns Inputs and Feedback, AuditCo receives a perpetual, irrevocable, royalty-free license to use them for its business and product; added a Derivative Works definition; accepted mutual confidentiality with edits. | Turn 2 (ownership and release deletions). |
| 4 | Feb 6 | `originals/ClientCo - AuditCo Evaluation Agreement (ClientCo 2.6.26).docx` | Counterparty counsel (sent by ClientCo) | Accepted the license compromise but tightened the statement that ClientCo owns Inputs and Feedback; carved AuditCo's gross negligence or willful misconduct out of the release; removed the requirement to show supporting documentation for the confidentiality exceptions. | Turn 3. |
| 5 | Feb 9 | (redline not in set) | AuditCo counsel | Accepted most of turn 4; held firm on two points: the documentation requirement for the confidentiality exceptions, and no carve-out from the release. | Turn 4. |
| — | Feb 10 | (no new file) | Counterparty | Accepted all of AuditCo's last revisions; signed the same day. | Turn 5. |

## Internal asks → did they land?
| Ask (paraphrased) | Origin | Landed? | Where (version + §) |
|---|---|---|---|
| AuditCo should own the IP in the client's inputs (client said it was comfortable with that) | email to counsel | changed | Turn 1 §2/§4: AuditCo owns all Inputs, Outputs, Feedback; from the 2.6.26 version: ClientCo owns Inputs and Feedback, AuditCo gets a perpetual, irrevocable license, §4(c); AuditCo keeps Outputs |
| Protection from liability if the analysis misses something | email to counsel | yes (after two rounds) | Release in turn 1 (§6); deleted in 1.29.26; reinserted by AuditCo counsel; ClientCo's gross-negligence carve-out in 2.6.26 was rejected in turn 5 and ClientCo accepted |
| Testing only in a sandbox, never on live systems | intake answers to counsel | yes | Turn 1 onward: download to AuditCo's "non-production test environment" |
| Findings shared only through a private GitHub channel | intake answers to counsel | yes | Turn 1 onward: notice "via a secure and private communications channel established by the Parties through Github" |
| No notice deadline for findings | intake answers to counsel | yes | No timing requirement on Security Incident notices in any version |
| No destruction of the client's (open-source) code at the end | intake answers to counsel | partly | Turn 1: no destruction duty on AuditCo; 2.6.26 version adds a mutual duty to return or delete the other Party's Confidential Information, while AuditCo keeps Inputs and Feedback under its license |

## What triggered extra rounds
- Turn 1 claimed ownership of Inputs and Feedback, which ClientCo's counsel had not been told was the deal → turn 2 struck it → turn 3 traded ownership for a perpetual license.
- Turn 2 deleted the release → turn 3 reinserted it → turn 4 narrowed it with a gross-negligence carve-out → turn 5 rejected the carve-out; only then did ClientCo accept.
- Turn 4's removal of the documentation requirement for confidentiality exceptions added a second open point to turn 5.
