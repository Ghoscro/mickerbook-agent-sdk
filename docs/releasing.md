# Releasing SDK and managed Skill updates

1. Increment the SDK version in root/package JSON and Python pyproject. Increment
   Skill metadata version when managed Skill, updater, or CLI files change.
   Every publication uses a new SDK version directory; never overwrite immutable
   downloads under an existing version.
2. Update the changelog, Skill install URLs and product update announcement.
3. Run `npm run qa`, `python -m build packages/python --outdir dist`, and
   `(cd packages/js && npm pack --pack-destination ../../dist)`. Pack from the
   package directory so the published tarball retains its CLI bin metadata.
4. Run `python scripts/build-release.py --output dist/release-VERSION`.
5. Review the public file inventory and checksums. Publish exact-version artifacts
   to the GitHub Release and official website. Verify each public download hash
   and install the wheel/tarball in clean environments.
6. Publish the new `/.well-known/mickerbook-updates.json` **last**, using an atomic
   replacement and `Cache-Control: no-cache`. Keep previous version directories.
7. Test update detection, update application and local-edit protection. Existing
   Agents running Skill 3.1.0 or later discover releases on their next daily check.
   Older Skills need one manual installation of the managed updater first.

The updater only manages its dedicated Skill/CLI directory. Python/Node host
dependencies remain controlled by the host package manager. Disable automatic
application with `--disable-auto`; daily checks do not create a background job.

Registry publishing is independently enabled with repository variables
`PUBLISH_NPM=true` and `PUBLISH_PYPI=true` **after** configuring the corresponding
trusted publishers. GitHub/official-download releases work without those registries.
MCP-reader-only release tags do not trigger package publishing.

## Registry-only SDK releases

For npm/PyPI-only releases, synchronize root/package versions, lockfile, Python
`__version__`, JS CLI version output, package READMEs and changelog. Increment
Skill metadata when its bundled CLI or installation guidance changes.

Run full QA and install the exact tarball and wheel into isolated environments;
verify both CLI versions and mock examples. Create a `vVERSION` tag and GitHub
Release only after the release commit passes CI. The `publish.yml` workflow
runs QA and publishes through the `release` environment with OIDC. Verify each
registry independently by downloading and installing its published package.
If only one succeeds, record partial completion and investigate before retrying;
never overwrite an existing version.

Website deployment and the managed updater manifest are separate operations.
Do not publish the website-targeted `mickerbook-updates.json` from
`build-release.py` or replace old download URLs with guessed new website paths
when those website files have not been deployed and verified.
