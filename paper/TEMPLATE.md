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

## Template details (from the template exported as HTML, 2026-11-07)

**Page and type:**
- US Letter, 1 in margins (468 pt text width), one column.
- Body: 11 pt Old Standard TT (serif). Headings: bold 14 pt. Title: 20 pt, centred.

**Sections in the template:**
- Title, then six author / affiliation slots, then "With Apart Research".
- Abstract (150-250 words), then 1 Introduction, 2 Related Work, 3 Methods, 4 Results.
- 5 Discussion and Limitations, with "Limitations" and "Future Work" subsections.
- 6 Conclusion.
- Code and Data; Author Contributions (optional); References; Appendix (optional).
- LLM Usage Statement.

**Length.** The template's own guidance recommends **4 pages excluding references and appendix**: about 1 page for intro and related work, 2.5 for methods and results, and 0.5 for discussion. The sprint page's hard limit is 8 pages. We target ≤ 8.

**LLM Usage Statement.** The template asks how LLM assistance was used and for confirmation that every claim was verified. It also "strongly encourage[s] that the final version of the submission is primarily written by your team." **The team must write this statement**, and should decide how much of the draft to rewrite in its own words. `draft.md` has a placeholder.

**Other instructions.** Delete all italic guidance text and the info box. Number every figure and table, give each a caption that stands alone, and place it near its first reference.

## Preview build and page check

```bash
cd ~/projects/swarm_hackathon && python3 paper/build_preview.py   # writes paper/preview.pdf
```

The build does the following:
- **Formatting:** approximates the template with Chrome print CSS, using the real Old Standard TT from Google Fonts.
- **Clean-up:** strips the drafting box and other drafting notes.
- **Figures:** inlines `plan/figs/paperfig*.png` at the widths set in `WIDTHS`.
- **Pagination:** starts References on a new page.
- **Report:** prints the main-body page count, meaning the pages before References.
- **Caveat:** Google Docs will paginate somewhat differently. Leave at least half a page of slack, and recheck after pasting.

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
   - **Cuts already applied** (first pass: 8 main pages):
     - the Discussion bullets, the 3.1 action and observation lists, and the 5.1 and 5.4 bullets are now prose;
     - the qualitative traces are in Appendix C;
     - the power table, the grid table (Table E2) and the board table (Table E3) moved to Appendix E, with their key numbers kept in the text;
     - the g02 network figure moved to Appendix C (Figure C1).
   - After the behavioural (SOCIAL_DYNAMICS) paragraph was added, 3.5 (agents and logging) and the Section 4 health-check and invariant paragraphs moved to Appendix B (B.1, B.2). The preview is again 8 main pages, with page 8 about 92% full.
   - The coordination-game wording then pushed page 8 to 97%. To make room for the network results and the author block, these moved too:
     - Table 1 (grid cells) went to Appendix E as Table E1, and the other appendix tables were renumbered E2-E5;
     - Figure 2b was shrunk to 65% width and Figure 3 to 58%;
     - Related Work was condensed, with every citation kept.
   - Result: page 8 is about 44% full.
   - **Next cuts if needed:** move Figure 4 (divergence) or Figure 1 to an appendix; turn the Section 4 Power paragraph into an appendix pointer; shorten Section 3.2 God.
9. **Export.** File → Download → PDF document. Open the PDF and check:
   - the abstract is 150 to 250 words;
   - no `[RESULT` or `[CHECK` strings remain;
   - the figures are legible.
