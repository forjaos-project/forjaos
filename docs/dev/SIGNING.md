# Signing the ForjaOS image (ADR-030)

The image is signed with a **cosign key pair**. The public key is `cosign.pub` at the repo root; the private key lives only in the repository secret `SIGNING_SECRET` and in the maintainer's password-manager backup. Agents never generate or handle the private key (ADR-030 §4).

## 1. Generate the key pair (maintainer, once)

On a trusted machine with [cosign](https://docs.sigstore.dev/cosign/system_config/installation/) installed, in an empty folder **outside** the repository:

```bash
COSIGN_PASSWORD="" cosign generate-key-pair
# creates cosign.key (private) and cosign.pub (public)
```

The empty password matches the Universal Blue convention; the key is protected by GitHub's secret encryption and by the backup below.

## 2. Register the secret

GitHub → `forjaos-project/forjaos` → Settings → Secrets and variables → Actions → **New repository secret**:

- Name: `SIGNING_SECRET`
- Value: the full contents of `cosign.key` (including the `BEGIN`/`END` lines)

## 3. Back up and remove the private key

Store `cosign.key` in your password manager (secure note). Then delete the local file. Never commit it; `.gitignore` blocks `cosign.key` and `cosign.private`.

## 4. Commit the public key

Send `cosign.pub` to the agent or commit it at the repo root via PR. The `signing-preflight` workflow runs on that PR and fails if `SIGNING_SECRET` does not match `cosign.pub`.

## Verify an image manually

```bash
cosign verify --key cosign.pub ghcr.io/forjaos-project/<image>:testing
```

## Rotation

On suspected leak or lost backup: generate a new pair, replace `SIGNING_SECRET` and `cosign.pub` in the same PR, and publish a new image. Images signed with the old key stop verifying against the new `cosign.pub`.
