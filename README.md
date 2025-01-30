# LinkedDataHub DSL operations

# Architecture

* GPT [system prompt](prompts/system.md)
  * operation definitions
  * JSON format specification ([JSON examples](examples))
* [`Operation` interface](src/operation.py)
  * JSON intepreter
* [Operation implementations](src/operations)

ChatGPT thread: https://chatgpt.com/c/679abd11-cc00-8009-8039-cecc0dd526e7

## Usage

1. Run LinkedDataHub (ideally v5 from the `develop` branch)
2. Execute `src/main.py`, it expects the path to your LDH's owner certificate and its password as arguments. For example:

```bash
python src/main.py --cert_pem_path ~/WebRoot/AtomGraph/LinkedDataHub/ssl/owner/cert.pem --cert_password ******
```
3. Enter instruction (see [examples](examples.md))
