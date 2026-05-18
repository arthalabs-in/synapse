# Slide export

The deck source is `slides.md`, written in [Marp](https://marp.app/) markdown.

## Export to PDF

```bash
# Install Marp CLI once
npm install -g @marp-team/marp-cli

# From the submission/slides/ directory
marp slides.md --pdf --allow-local-files
```

## Export to HTML (for quick preview)

```bash
marp slides.md --html --allow-local-files
```

## Export to PPTX

```bash
marp slides.md --pptx --allow-local-files
```

The final PDF should be committed as `slides.pdf` next to `slides.md` before
submission so judges don't need Marp installed.
