# Releasing TelePlay

This document describes how to create releases for TelePlay.

## Android TV & Mobile APK Releases

APK builds are automated via GitHub Actions. When you push a version tag, the workflow automatically:

1. Builds release APKs (split by CPU architecture)
2. Builds a debug APK
3. Creates a GitHub Release with all APKs attached

### Quick Release

```bash
# Tag a new release
git tag v1.0.0
git push origin v1.0.0
```

The GitHub Action will handle the rest!

### Manual Build

You can also trigger a build manually:

1. Go to **Actions** → **Build Android TV APK**
2. Click **Run workflow**
3. Optionally specify a version name
4. Download artifacts when complete

## Setting Up APK Signing

For signed release APKs, configure these GitHub Secrets:

### Required Secrets

| Secret              | Description                  |
| ------------------- | ---------------------------- |
| `KEYSTORE_BASE64`   | Base64-encoded keystore file |
| `KEYSTORE_PASSWORD` | Keystore password            |
| `KEY_ALIAS`         | Key alias in the keystore    |
| `KEY_PASSWORD`      | Key password                 |

### Creating a Keystore

```bash
# Generate a new keystore
keytool -genkey -v -keystore release.jks -keyalg RSA -keysize 2048 -validity 10000 -alias teleplay

# Encode to base64 for GitHub Secret
base64 -w 0 release.jks > keystore-base64.txt
```

### Adding Secrets to GitHub

1. Go to your repository → **Settings** → **Secrets and variables** → **Actions**
2. Add each secret:
   - `KEYSTORE_BASE64`: Contents of `keystore-base64.txt`
   - `KEYSTORE_PASSWORD`: Password you used when creating keystore
   - `KEY_ALIAS`: `teleplay` (or whatever alias you used)
   - `KEY_PASSWORD`: Key password (same as keystore password if you used the same)

### Without Signing

If you don't add the signing secrets, the workflow will still build APKs - they just won't be signed. Users can still install them by enabling "Install from unknown sources" on their devices.

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- `v1.0.0` - Stable release
- `v1.1.0-beta` - Beta release
- `v1.1.0-alpha` - Alpha release

Beta and alpha releases are automatically marked as pre-releases on GitHub.

## APK Variants

The build produces multiple APKs optimized for different architectures:

| APK           | Size  | Target Devices                                 |
| ------------- | ----- | ---------------------------------------------- |
| `arm64-v8a`   | ~25MB | Modern Android TV boxes, NVIDIA Shield, Phones |
| `armeabi-v7a` | ~20MB | Older 32-bit ARM devices                       |
| `x86_64`      | ~25MB | Intel-based Android devices                    |
| `x86`         | ~20MB | Older Intel Android devices                    |
| `universal`   | ~80MB | Any device (includes all architectures)        |

Most users should download `arm64-v8a` for modern devices or `universal` if unsure.
