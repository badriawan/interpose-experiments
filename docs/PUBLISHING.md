# Publish this prepared repository

Target: **`badriawan/interpose-experiments`**, public visibility. The preparation machine has an isolated local Git repository with `main` and the HTTPS `origin` set. Public GitHub creation/push has not completed: the target was not found, no GitHub CLI/token/helper was available, and browser access was unavailable.

## Finish authentication and repository creation

1. Sign in to the intended GitHub account through your normal browser. Create the public repository named `interpose-experiments` at [GitHub's new repository page](https://github.com/new). Leave README, license, and `.gitignore` initialization unchecked; the local repository already contains them.
2. Authenticate Git on the machine that will push. If you use GitHub CLI, install it through GitHub's official instructions first, then use `gh auth login` and `gh auth setup-git`. The CLI was not installed during package preparation. Alternatively, use your existing Git HTTPS credential helper or SSH setup. Keep authentication local; credentials do not belong in this repository or chat.
3. From this repository root, inspect the remote and push:

```bash
git remote -v
git status --short
git push -u origin main
```

Do not force-push to a repository containing work. If the name is already occupied, inspect it before choosing a different target or integrating histories. For SSH authentication, explicitly change only this repository's origin to the corresponding `git@github.com:badriawan/interpose-experiments.git` URL after verifying your normal SSH access.

## Release boundary

The intended public content includes source, English documentation, two source patches, license notices, observed environment inventories, tests, and the original synthetic waypoint video/poster. `.local/`, real floorlamp previews, licensed assets, checkpoints, environments and generated runs remain excluded. The original project is unchanged.

The local source ZIP is generated from the committed tree under ignored `.local/`. It contains the same public files, including the synthetic video. Importing or uploading that archive does not automatically establish authentication or create a GitHub repository.
