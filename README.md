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

# Update all formulas with dependencies
source venv/bin/activate
python update.py
```

### What the script does

- 📥 Fetches latest versions from PyPI
- 📄 **Respects version pinning from `requirements.txt` in GitHub repo**
- 🔄 Resolves all transitive dependencies automatically
- ✅ Updates URLs and SHA256 checksums
- 📦 Generates Homebrew resource blocks

**Note:** The script automatically fetches the `requirements.txt` from the package's GitHub repository (if available) and uses pinned versions (e.g., `jiter==0.7.1`) instead of latest versions.

---

**Available Packages:**
- `doque` - CLI LLM client for querying AI models
