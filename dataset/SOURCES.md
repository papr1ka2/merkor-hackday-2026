# Sources

## documents/ (top level): team redlines

Anonymized contracts and counsel redlines provided by the team. Party, people, firm and place
names are pseudonyms; commercial figures are randomized but internally consistent. The questions
in `questions.yaml` with `source: expert` are written over these documents.

## documents/cuad/: CUAD v1

The 510 contract PDFs from the **Contract Understanding Atticus Dataset (CUAD) v1** by
The Atticus Project, Inc., https://zenodo.org/records/4595826, licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Hendrycks, Burns, Chen and Ball, "CUAD: An Expert-Annotated NLP Dataset for Legal Contract
Review", NeurIPS 2021. https://arxiv.org/abs/2103.06268

Changes: only the PDFs are included, placed at `cuad/<CUAD category folder>/<contract name>/r01__<original
filename>` (the `Part_I`/`Part_II`/`Part_III` level is dropped). CUAD's clause labels (JSON, CSV, XLSX)
and its extracted text files are not included. No questions have been written over these yet.
