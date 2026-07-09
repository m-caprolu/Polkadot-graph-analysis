This migration solves wrongly generated multisig addresses nested inside proxy calls.

### Details:
- Proxy.proxy could have a nested multisig.as_multi call, the problem is that we add the proxy account address for generating the multisig account address while the proxied account is the correct address to be added.
