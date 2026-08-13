# Discourse container cache comparison

This branch runs Discourse's own image factory in `boringcache/discourse_docker`.
It keeps the upstream target-by-target Bake order and uses native GitHub-hosted
runners: `ubuntu-24.04` for AMD64 and `ubuntu-24.04-arm` for ARM64.

Every architecture builds the same Dockerfiles through three isolated lanes:

1. GitHub Actions layer cache.
2. BoringCache layer cache.
3. BoringCache layer cache plus ccache tool cache and BuildKit mountcache.

The shared Dockerfile owns the ccache 4.13.6 compiler launchers. Only the third
lane injects BoringCache's remote ccache settings. The Bundler mount contains
the complete installed bundle, not only downloaded gem archives. Each build
materializes it into `vendor/bundle`, runs a normal `bundle install` there to
repair or install anything missing, and then uses `bundle check` as a final
verification. The pnpm mounts cover its complete writable home. Ownership is
set inside each mounted `RUN`; putting `uid`/`gid` on the mount creates BuildKit
initialization entries that prevent an empty mount from being hydrated.

The seed uses Discourse commit
`eedf0ac2344c37d66a2c9ab05dc8a83bf3efd9bb`. The rebuild uses its immediate
child, `763655f6faf47b088afee1a59e2d97cec5886c97`. Their dependency manifests
are identical, while the date transition exercises Discourse's native base
image refresh and the changed source ref exercises Bundler and pnpm mounts.

The benchmark keeps the Mozilla signing-key correction from
`a68d4b8707fd653697e8b6b27b336d093dbed5e4` and runs the upstream image specs
outside the timed build with `CI=true`.
