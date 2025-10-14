# Git Hooks för Tobbes v2

## Pre-commit Hook (Auto-increment)

Pre-commit hooken **ökar automatiskt versionen** vid varje commit och synkroniserar till alla filer.

**Versionsstrategi:** `1.12 → 1.13 → 1.14 → 1.15` (automatisk ökning)

### Installation

Kopiera hooken till din lokala `.git/hooks` mapp:

```bash
cp .githooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### Vad gör hooken?

1. **Auto-increment:** Ökar versionen automatiskt (1.12 → 1.13)
2. **Synkronisering:** Uppdaterar `build/assets/version.txt` med:
   - Ny version
   - Build-datum
   - Git commit hash
   - Git branch
3. **Auto-add:** Lägger automatiskt till ändrade filer till committen

### Användning

Efter installation körs hooken automatiskt vid varje commit:

```bash
# Gör dina ändringar
vim ui/wizard.py

# Commita som vanligt - versionen ökar automatiskt!
git add .
git commit -m "Add new feature"

# Hooken kör automatiskt:
# ✓ Version incremented: 1.12 → 1.13
# ✓ Version synchronized: 1.13
# ✓ Files added to commit
```

### Exempel på versionsflöde

```
Commit 1: Fix bug         → 1.12 → 1.13
Commit 2: Add feature     → 1.13 → 1.14
Commit 3: Update UI       → 1.14 → 1.15
Commit 4: Performance     → 1.15 → 1.16
```

### Manuell versionskontroll

Om du vill sätta en specifik version (t.ex. major release):

```bash
# 1. Skippa hooken temporärt
git commit --no-verify -m "Prepare for v2.0"

# 2. Ändra version manuellt
vim config/constants.py  # APP_VERSION = "2.0"

# 3. Nästa commit fortsätter från 2.0 → 2.01 → 2.02
```

### Avaktivera temporärt

Om du behöver skippa hooken (t.ex. för README-ändringar):

```bash
git commit --no-verify -m "Update documentation"
```

### Testa hooken manuellt

Testa version-synkronisering utan increment:

```bash
python build/sync_version.py
```
