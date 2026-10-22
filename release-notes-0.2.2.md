Fix the CLI entrypoint in automated npm releases.

Pack from the JavaScript package directory, install the exact tarball in an isolated directory, and execute the installed micker command before publishing that verified artifact. Version 0.2.1 exposed a workspace publishing issue that removed bin metadata. SDK APIs remain unchanged.

Validation: JS/Python tests and quickstarts, packaging checks, and CI installed CLI smoke.
