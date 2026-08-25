# Publishing this project to GitHub

## 1. Create the repository

1. Sign in to GitHub.
2. Select **New repository**.
3. Set the repository name to `upstate-ny-hyperspectral-mapping`.
4. Choose **Public**.
5. Do not initialize a second README; this project already includes one.
6. Select **Create repository**.

## 2. Upload the project

From Terminal on macOS, open the extracted project folder and run:

```bash
cd ~/Downloads/upstate-ny-hyperspectral-mapping
git init
git add .
git commit -m "Add upstate New York hyperspectral mapping project"
git branch -M main
git remote add origin https://github.com/carolinekamal/upstate-ny-hyperspectral-mapping.git
git push -u origin main
```

GitHub may ask you to authenticate. Use GitHub's normal browser-based sign-in or GitHub Desktop; do not put a password or token in the repository.

## 3. Set the GitHub description

Suggested repository description:

> Interpretable hyperspectral mapping of upstate New York using NASA EMIT-compatible workflows, PCA, k-means, and exposed-surface spectral proxies.

Suggested topics:

```text
hyperspectral-imaging
materials-science
machine-learning
remote-sensing
nasa-emit
crystallography
geospatial-analysis
python
pca
kmeans-clustering
finger-lakes
spectroscopy
```

## 4. Add it to the GitHub profile README

```markdown
### Featured project: Upstate New York Hyperspectral Surface Mapping

An interpretable machine-learning workflow for hyperspectral landscape analysis across the Finger Lakes and Lake Erie grape belt. Includes NASA EMIT scene discovery, orthorectification, PCA, k-means clustering, and responsibly masked surface-spectral proxies.

[Explore the repository](https://github.com/carolinekamal/upstate-ny-hyperspectral-mapping)
```

## 5. Add it to a portfolio or CV

**Portfolio title:** Hyperspectral Surface Mapping Across Upstate New York

**Portfolio description:** Built a reproducible Python workflow for NASA EMIT-compatible imaging spectroscopy across the Finger Lakes and Lake Erie regions, integrating spectral preprocessing, NDVI/NDWI masking, PCA, k-means clustering, and exploratory mineral-related absorption proxies.

**CV bullet:** Developed an interpretable hyperspectral-analysis pipeline using Python, PCA, k-means, spectral indices, and NASA EMIT-compatible geospatial workflows to characterize upstate New York landscapes.

Keep the distinction clear: bundled demonstration figures are synthetic, while NASA discovery and observed-data processing are separate capabilities that require actual scene availability.
