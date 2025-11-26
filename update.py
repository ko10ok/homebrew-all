#!/usr/bin/env python3
"""
Script to update all Python package formulas in Formula/ directory.
Fetches the latest versions from PyPI, resolves all transitive dependencies,
and updates the .rb files with resource blocks.
"""

import re
import argparse
import requests
from pathlib import Path
from typing import Optional, Tuple, Dict, Set
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet


def normalize_package_name(name: str) -> str:
    """Normalize package name (convert underscores/hyphens)."""
    return re.sub(r'[-_.]+', '-', name).lower()


def fetch_github_requirements(formula_content: str) -> Dict[str, str]:
    """
    Fetch requirements.txt from GitHub repository if homepage is a GitHub URL.
    Returns dict mapping package name to pinned version (or None for no constraint).
    """
    # Extract homepage from formula
    homepage_match = re.search(r'homepage\s+"([^"]+)"', formula_content)
    if not homepage_match:
        return {}

    homepage = homepage_match.group(1)

    # Check if it's a GitHub URL
    github_match = re.match(r'https://github\.com/([^/]+)/([^/]+)', homepage)
    if not github_match:
        return {}

    owner, repo = github_match.groups()

    # Try to fetch requirements.txt from master/main branch
    requirements = {}
    for branch in ['master', 'main']:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/requirements.txt"
        try:
            response = requests.get(url, timeout=5)
            if response.ok:
                print(f"  📄 Found requirements.txt in GitHub repo ({branch} branch)")
                # Parse requirements.txt
                for line in response.text.splitlines():
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue

                    # Parse requirement
                    try:
                        req = Requirement(line)
                        pkg_name = normalize_package_name(req.name)

                        # Extract exact version if pinned with ==
                        if req.specifier:
                            for spec in req.specifier:
                                if spec.operator == '==':
                                    requirements[pkg_name] = spec.version
                                    print(f"    📌 Pinned: {req.name} == {spec.version}")
                                    break
                    except Exception:
                        continue

                return requirements
        except Exception:
            continue

    return {}


def get_pypi_package_info(package_name: str, version: Optional[str] = None) -> Optional[dict]:
    """
    Fetch package info from PyPI.
    Returns dict with version, url, sha256, requires_dist.
    """
    try:
        # Always fetch the general info first to get releases
        response = requests.get(f"https://pypi.org/pypi/{package_name}/json")
        response.raise_for_status()
        data = response.json()

        info = data['info']

        # If specific version requested, use it; otherwise use latest
        if version:
            version_str = version
            if version_str not in data['releases']:
                print(f"    ⚠️  Version {version} not found for {package_name}")
                return None
        else:
            version_str = info['version']

        releases = data['releases'][version_str]

        # Find the source distribution (tar.gz or .zip)
        sdist_info = None
        for release in releases:
            if release['packagetype'] == 'sdist':
                sdist_info = release
                break

        if not sdist_info:
            return None

        # If we need specific version info, fetch it separately
        if version:
            version_response = requests.get(f"https://pypi.org/pypi/{package_name}/{version}/json")
            if version_response.ok:
                version_data = version_response.json()
                info = version_data['info']

        return {
            'name': info['name'],
            'version': version_str,
            'url': sdist_info['url'],
            'sha256': sdist_info['digests']['sha256'],
            'filename': sdist_info['filename'],
            'requires_dist': info.get('requires_dist', []) or []
        }

    except Exception as e:
        print(f"    ⚠️  Error fetching PyPI data for {package_name}: {e}")
        return None


def parse_requirement(req_string: str) -> Optional[Tuple[str, SpecifierSet, Optional[str]]]:
    """
    Parse a requirement string.
    Returns (package_name, version_specifier, environment_marker) or None.
    """
    try:
        req = Requirement(req_string)
        return (normalize_package_name(req.name), req.specifier, req.marker)
    except Exception:
        return None


def resolve_dependencies(
    package_name: str,
    package_version: str,
    resolved: Dict[str, dict],
    visited: Set[str],
    pinned_versions: Dict[str, str],
    depth: int = 0
) -> None:
    """
    Recursively resolve all dependencies of a package.
    Updates the resolved dict with all transitive dependencies.
    """
    if depth > 20:  # Prevent infinite recursion
        return

    normalized_name = normalize_package_name(package_name)
    key = f"{normalized_name}=={package_version}"

    if key in visited:
        return

    visited.add(key)

    indent = "    " * (depth + 1)
    print(f"{indent}📦 Resolving {package_name} {package_version}")

    # Get package info
    pkg_info = get_pypi_package_info(package_name, package_version)
    if not pkg_info:
        return

    # Store in resolved (use canonical name from PyPI)
    canonical_name = normalize_package_name(pkg_info['name'])
    if canonical_name not in resolved:
        resolved[canonical_name] = pkg_info

    # Process dependencies
    requires_dist = pkg_info.get('requires_dist', [])
    if not requires_dist:
        return

    for req_string in requires_dist:
        parsed = parse_requirement(req_string)
        if not parsed:
            continue

        dep_name, specifier, marker = parsed

        # Skip optional dependencies with environment markers
        if marker and 'extra' in str(marker):
            continue

        # Skip dependencies that are already resolved
        if dep_name in resolved:
            continue

        # Check if version is pinned in requirements.txt
        if dep_name in pinned_versions:
            dep_version = pinned_versions[dep_name]
            print(f"{indent}  📌 Using pinned version: {dep_name} == {dep_version}")
        else:
            # Get the latest version that matches the specifier
            dep_info = get_pypi_package_info(dep_name)
            if not dep_info:
                continue

            dep_version = dep_info['version']

            # Check if version satisfies specifier
            if specifier and not specifier.contains(dep_version):
                # Try to find a compatible version (simplified - just use latest)
                print(f"{indent}  ⚠️  Version {dep_version} may not satisfy {specifier}")

        # Recursively resolve
        resolve_dependencies(dep_name, dep_version, resolved, visited, pinned_versions, depth + 1)


def extract_package_info(formula_content: str) -> Optional[Tuple[str, str, str, str]]:
    """
    Extract package name, current version, URL, and SHA256 from formula.
    Returns (package_name, version, url, sha256) or None.
    """
    # Extract URL
    url_match = re.search(r'url\s+"([^"]+)"', formula_content)
    if not url_match:
        return None

    url = url_match.group(1)

    # Extract SHA256
    sha256_match = re.search(r'sha256\s+"([^"]+)"', formula_content)
    if not sha256_match:
        return None

    sha256 = sha256_match.group(1)

    # Extract package name from URL
    filename = url.split('/')[-1]

    # Try to extract package name and version
    name_version_match = re.match(r'^(.+?)-([\d.]+(?:(?:a|b|rc|dev|post)[\d]+)?)\.(tar\.gz|zip)$', filename)
    if name_version_match:
        package_name = name_version_match.group(1)
        version = name_version_match.group(2)
        return (package_name, version, url, sha256)

    return None


def generate_resource_blocks(dependencies: Dict[str, dict], main_package: str) -> str:
    """
    Generate Ruby resource blocks for all dependencies.
    """
    if not dependencies:
        return ""

    resource_blocks = []

    for pkg_name, pkg_info in sorted(dependencies.items()):
        if normalize_package_name(pkg_name) == normalize_package_name(main_package):
            continue

        block = f'''  resource "{pkg_info['name']}" do
    url "{pkg_info['url']}"
    sha256 "{pkg_info['sha256']}"
  end'''
        resource_blocks.append(block)

    return "\n\n" + "\n\n".join(resource_blocks) if resource_blocks else ""


def update_formula_file(filepath: Path, new_info: dict, dependencies: Dict[str, dict]) -> bool:
    """
    Update the formula file with new version info and dependencies.
    Returns True if updated, False otherwise.
    """
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        # Extract current info
        current_info = extract_package_info(content)
        if not current_info:
            print(f"  ⚠️  Could not extract package info from {filepath.name}")
            return False

        package_name, current_version, current_url, current_sha256 = current_info

        # Update URL
        new_content = content.replace(
            f'url "{current_url}"',
            f'url "{new_info["url"]}"'
        )

        # Update SHA256
        new_content = new_content.replace(
            f'sha256 "{current_sha256}"',
            f'sha256 "{new_info["sha256"]}"'
        )

        # Remove old resource blocks
        # Find and remove everything between depends_on and def install
        resource_pattern = r'(\n\n  depends_on[^\n]+)(.*?)(\n\n  def install)'
        match = re.search(resource_pattern, new_content, re.DOTALL)

        if match:
            # Check if there are existing resources
            existing_resources = match.group(2)
            if 'resource' in existing_resources:
                # Remove old resources
                new_content = re.sub(
                    resource_pattern,
                    r'\1\3',
                    new_content,
                    flags=re.DOTALL
                )

        # Add new resource blocks
        resource_blocks = generate_resource_blocks(dependencies, package_name)
        if resource_blocks:
            # Insert resources after depends_on lines
            depends_pattern = r'(depends_on[^\n]+(?:\n  depends_on[^\n]+)*)'
            new_content = re.sub(
                depends_pattern,
                r'\1' + resource_blocks,
                new_content
            )

        # Write back
        with open(filepath, 'w') as f:
            f.write(new_content)

        version_changed = current_version != new_info['version']
        if version_changed:
            print(f"  ✓ Updated: {current_version} → {new_info['version']}")
        else:
            print(f"  ✓ Version unchanged: {current_version}")

        dep_count = len([d for d in dependencies if normalize_package_name(d) != normalize_package_name(package_name)])
        if dep_count > 0:
            print(f"  ✓ Added {dep_count} dependencies")

        return True

    except Exception as e:
        print(f"  ✗ Error updating {filepath.name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function to update all formulas."""
    formula_dir = Path(__file__).parent / "Formula"

    if not formula_dir.exists():
        print(f"Error: Formula directory not found at {formula_dir}")
        return

    # Find all .rb files
    formula_files = list(formula_dir.glob("*.rb"))

    if not formula_files:
        print("No formula files found in Formula/ directory")
        return

    print(f"Found {len(formula_files)} formula file(s)")
    print("🔄 Resolving all transitive dependencies\n")

    updated_count = 0

    for formula_file in sorted(formula_files):
        print(f"Processing {formula_file.name}...")

        # Read and extract package info
        with open(formula_file, 'r') as f:
            content = f.read()

        info = extract_package_info(content)
        if not info:
            print(f"  ⚠️  Skipping - could not extract package info")
            continue

        package_name, current_version, _, _ = info
        print(f"  Current: {package_name} {current_version}")

        # Fetch latest version from PyPI
        print(f"  📡 Fetching latest version from PyPI...")
        latest_info = get_pypi_package_info(package_name)
        if not latest_info:
            print(f"  ✗ Could not fetch latest version from PyPI")
            continue

        print(f"  Latest: {latest_info['version']}")

        # Fetch pinned versions from requirements.txt if available
        pinned_versions = fetch_github_requirements(content)

        # Resolve all dependencies
        print(f"  🔍 Resolving dependencies...")
        dependencies = {}
        visited = set()
        resolve_dependencies(
            package_name,
            latest_info['version'],
            dependencies,
            visited,
            pinned_versions
        )
        print(f"  Found {len(dependencies)} total packages (including main)")

        # Update formula
        if update_formula_file(formula_file, latest_info, dependencies):
            updated_count += 1

        print()

    print(f"\n{'='*50}")
    print(f"Summary: Updated {updated_count} of {len(formula_files)} formula(s)")
    print(f"{'='*50}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Update Python package formulas in Formula/ directory with all dependencies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Example:
  python update.py           # Update versions and resolve all dependencies
        '''
    )

    args = parser.parse_args()
    main()
