import base64
import json
from typing import cast

from cryptography.fernet import Fernet
from langchain_core.tools import tool
from langchain_sandbox import PyodideSandboxTool
from openevals.code.pyright import create_pyright_evaluator
from openevals.types import EvaluatorResult
from pydantic import BaseModel, Field


class DecryptFernetPayloadInput(BaseModel):
    key: str = Field(description="decryption key for the corresponding payload")
    payload: str = Field(description="the payload to decrypt")


@tool(args_schema=DecryptFernetPayloadInput)
def decrypt_fernet_payload(
    key: str,
    payload: str,
) -> str:
    """Decrypt Fernet-encrypted payloads.
    Runtime decryption of malicious payload is done in the following format: `Fernet(b'key').decrypt(b'payload')`
    If you encounter the format above, this tool will decrypt it for you.
    When decryption fails, the error message will be shown to you.

    Args:
        key (str): a key to decrypt the payload with
        payload (str): a payload encrypted using the key

    Returns:
        str: Decrypted content or error message with forensic details

    Example success:
        "exec(__import__('zlib').decompress(...))"
    """
    try:
        decoded = Fernet(key.encode()).decrypt(payload.encode()).decode()
    except Exception as e:
        return (
            f"Failed to decrypt the payload. Error message is the following: {e} "
            "This could be due to incorrect key or payload, but also consider the possibility that this could be a random string and may not be a fernet-encoded string."
        )
    else:
        return decoded


class DecodeBase64PayloadInput(BaseModel):
    payload: str = Field(description="A payload to decode")


@tool(args_schema=DecodeBase64PayloadInput)
def decode_base64_payload(payload: str) -> str:
    """Decode base64-encoded strings.
    Runtime decoding of base64 data is done using the `base64.b64decode()` function.
    If you encounter base64-encoded data, this tool will decode it for you.
    When decoding fails, the error message will be shown to you.

    Args:
        payload (str): a string encoded in base64 format

    Returns:
        str: Decoded content or error message with forensic details

    Example success:
        "Hello, World!" (when decoding "SGVsbG8sIFdvcmxkIQ==")
    """
    try:
        decoded = base64.b64decode(payload.encode()).decode().replace("\0", "")
    except Exception as e:
        return (
            f"Failed to decode the base64 string. Error message is the following: {e}. "
            "This could be due to incorrect payload, but also consider the possibility that this could be a random string and may not be a base64 string."
        )
    else:
        return decoded


class DecodeHexPayloadInput(BaseModel):
    payload: str = Field(description="A payload to decode from hexadecimal format")


@tool(args_schema=DecodeHexPayloadInput)
def decode_hex_payload(payload: str) -> str:
    """Decode hexadecimal-encoded strings.
    Runtime decoding of hex data is done using the `bytes.fromhex()` function.
    If you encounter hexadecimal-encoded data, this tool will decode it for you.
    When decoding fails, the error message will be shown to you.

    Args:
        payload (str): a string encoded in hexadecimal format

    Returns:
        str: Decoded content or error message with forensic details

    Example success:
        "Hello, World!" (when decoding "48656c6c6f2c20576f726c6421")
    """
    try:
        # Remove any whitespace and common hex prefixes
        cleaned_payload = payload.strip().replace("0x", "").replace("\\x", "")
        decoded = bytes.fromhex(cleaned_payload).decode().replace("\0", "")
    except Exception as e:
        return (
            f"Failed to decode the hexadecimal string. Error message is the following: {e}. "
            "This could be due to incorrect payload, but also consider the possibility that this could be a random string and may not be a hex-encoded string."
        )
    else:
        return decoded


class ExecutePythonCodeInput(BaseModel):
    code: str = Field(
        description="Python code that MUST include print() statements to output results to stdout."
    )


@tool(
    PyodideSandboxTool().name,
    description=PyodideSandboxTool().description,
    args_schema=ExecutePythonCodeInput,
)
def execute_python_code(code: str) -> str:
    pyright_evaluator = create_pyright_evaluator(
        pyright_cli_args=["--ignore-rule", "reportUnusedCoroutine"]
    )

    # check if the given code is in correct syntax
    result = cast(EvaluatorResult, pyright_evaluator(outputs=code))
    if (not result["score"]) and result["comment"]:
        try:
            return "Pyright checked your code and found following:\n" + json.dumps(
                json.loads(result["comment"]), indent=4
            )
        except Exception:
            pass

    return PyodideSandboxTool(allow_net=True).invoke(code)
