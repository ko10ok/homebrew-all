# Homebrew All

Custom Homebrew tap with Python package formulas.

## For Users: Installing Packages

### Add this tap to Homebrew

```bash
brew tap ko10ok/all https://github.com/ko10ok/homebrew-all
```

### Install packages from this tap

```bash
brew install ko10ok/all/doque
```

Or after tapping, simply:

```bash
brew install doque
```

## For Maintainers: Updating Formulas

### Quick Start

```bash
# Setup (first time only)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Update all formulas
source venv/bin/activate
python update.py -r
```

### Update Script Usage

```bash
# Update package versions only
python update.py

# Update versions + resolve all dependencies (recommended)
python update.py -r
```

### What the script does

- 📥 Fetches latest versions from PyPI
- 🔄 Resolves transitive dependencies (with `-r`)
- ✅ Updates URLs and SHA256 checksums
- 📦 Generates Homebrew resource blocks

---

**Available Packages:**
- `doque` - CLI LLM client for querying AI models
