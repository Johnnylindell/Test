# GitHub Pages publicering

Jag förberedde sajten för GitHub Pages med workflow:

```text
.github/workflows/pages.yml
```

## Publicera när GitHub-token/login finns

Eftersom `gh` inte är installerat och ingen `GITHUB_TOKEN`/git credential finns på maskinen kan jag inte skapa GitHub-repo autonomt härifrån just nu.

När GitHub är autentiserat kan detta köras från projektmappen:

```bash
cd /home/johnn/smart-family-affiliate-site
git init
git branch -M main
git add .
git commit -m "Initial Smart Familj Hemma affiliate site"
```

Skapa repo på GitHub, till exempel `smart-familj-hemma`, och pusha:

```bash
git remote add origin https://github.com/<DIN_GITHUB_USER>/smart-familj-hemma.git
git push -u origin main
```

Aktivera sedan Pages i GitHub:

- Settings → Pages
- Source: GitHub Actions

Workflowen bygger `site/` och publicerar som GitHub Pages.

## Alternativ: Cloudflare Pages

1. Skapa nytt Cloudflare Pages-projekt.
2. Koppla GitHub-repot.
3. Build command: `python3 scripts/build_site.py`
4. Output directory: `site`

## Affiliate efter publicering

När URL:en finns kan du använda den i affiliate-ansökningar. Se `docs-affiliate-plan.md`.
