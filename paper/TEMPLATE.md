# Official submission template and how to convert `draft.md`

## Where the template is (checked 2026-11-07 on the sprint page)

- Sprint page: https://apartresearch.com/sprints/swarm-alignment-2026 (Guidelines tab).
- **Official template, Google Docs (the only one listed):**
  https://docs.google.com/document/d/1_1_27EyZriMlc8n8EBE2YScaeyMjm-8xjR097nmHXAE/copy?usp=sharing
  - Opening this link makes a private copy in your own Drive.
  - The page lists **no Overleaf or LaTeX template**.
  - The page also says that "the template in any acceptance email may be older". Use the link above, not one from an email.

## Requirements from the sprint page

- Research report as a **PDF** made from the official template.
- At most **8 pages, not counting references and appendices**.
- Title, plus an **abstract of 150 to 250 words**.
- Author names and affiliations.
- **Required appendix: "Limitations and Dual-Use / Ethical Considerations"** (draft.md Appendix A).
- Recommended section order: Introduction, Related Work, Methodology, Results, Discussion, Limitations and Dual-Use / Ethical Considerations, References. draft.md follows this order: its "Environment and Method" and "Experimental Setup" sections together form "Methodology".
- Optional: a public GitHub repo and a 3 to 5 minute video demo. The network-evolution video, `swarm/viz/animate.py`, is a candidate for the demo.
- Judging scores three things from 1 to 5: Impact Potential & Innovation, Execution Quality, and Presentation & Clarity.
- **Made-up results or references can disqualify a project.** Every `[RESULT: ...]` and `[CHECK: ...]` must be resolved from run data, or the sentence removed, before export.
- Deadline: Sun 2026-11-08, 23:59 AoE. Team target: 18:00 AoE.

## Conversion steps (Markdown to Google Docs to PDF)

1. **Make a team copy.** One person opens the copy link and shares the copy with the team (edit access).
2. **Resolve placeholders first, in Markdown.** Run this from the repo root; it must print nothing:
   `grep -n 'RESULT:\|CHECK:' paper/draft.md`
   Also delete the "Drafting rules" box at the top of draft.md.
3. **Convert the body.** Choose one option:
   - **(a) Recommended: paste section by section.** Paste each section's prose into the template under its heading. Then apply the template's own heading and body styles: select the text, then Format → Paragraph styles. This keeps the template's look exactly.
   - **(b) Convert with pandoc.** If pandoc is installed:
     `pandoc paper/draft.md -o /tmp/draft.docx`
     Then open the .docx in Google Docs (File → Open → Upload) and copy the sections into the template copy.
     - Do not submit the pandoc output directly: it does not carry the template's styles.
     - pandoc is not known to be installed in the `swarm` env; check with `pandoc --version`.
4. **Tables.** Recreate Tables 1 to 4 with Insert → Table. Pasted Markdown pipes do not become tables.
5. **Figures.** Export PNGs at 200 dpi or more. Insert each one with Insert → Image, inline, with a caption below it that names its source run id. Figure sources are listed in `paper/outline.md`.
6. **References.** Paste the numbered reference list as it is. Each entry carries its arXiv id. Keep the bracket numbering [n] used in the body.
7. **Appendices.** Put Appendix A, "Limitations and Dual-Use / Ethical Considerations", after the references, as the sprint page puts it. Appendix B (configs, prompts, health table) follows it.
8. **Check the length.** The body, Introduction through Conclusion including figures, must fit in 8 pages.
   - At about 4,000 words of body plus 4 figures, expect it to be tight.
   - Cut in this order: Discussion bullets, Section 5.5 qualitative traces (move them to an appendix), the Section 3.1 observation list.
9. **Export.** File → Download → PDF document. Open the PDF and check:
   - the abstract is 150 to 250 words;
   - no `[RESULT` or `[CHECK` strings remain;
   - the figures are legible.
