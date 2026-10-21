# Security

## Reporting a vulnerability

Report it privately through GitHub's
[private vulnerability reporting](https://github.com/AtomGraph/Web-Algebra/security/advisories/new),
not in a public issue.

## Supported versions

Fixes are made on the latest release.

## Credentials

Web Algebra authenticates to LinkedDataHub with a client certificate, given in
`CERT_PEM_PATH` and `CERT_PASSWORD`. Keep the password out of files under version
control and out of command lines; read it from a file into the variable.
