# Sources

## documents/anonymized-demo-contracts/: team redlines

Anonymized contracts and counsel redlines provided by the team. Party, people, firm and place
names are pseudonyms; commercial figures are randomized but internally consistent. Questions
A–AC in `questions.yaml` come from the team's actual legal interactions on these contracts.

## documents/cuad/: CUAD v1

The 510 contract PDFs from the **Contract Understanding Atticus Dataset (CUAD) v1** by
The Atticus Project, Inc., https://zenodo.org/records/4595826, licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Hendrycks, Burns, Chen and Ball, "CUAD: An Expert-Annotated NLP Dataset for Legal Contract
Review", NeurIPS 2021. https://arxiv.org/abs/2103.06268

Changes: only the PDFs are included, placed at `cuad/<CUAD category folder>/<contract name>/r01__<original
filename>` (the `Part_I`/`Part_II`/`Part_III` level is dropped). CUAD's clause labels (JSON, CSV, XLSX)
and its extracted text files are not included. Questions CUAD-A–D were written by the team on demo
day after reviewing each contract with legal expertise (no answers yet). Questions ADV-A–D, adversarial stress tests from a team member,
reuse four of these PDFs with hypothetical facts.
