"""Generate a VAPID keypair for Web Push and print the SSM commands to store it.

This script never touches AWS. It only prints the two `aws ssm put-parameter`
commands; run them yourself (or hand them to the controller) after reviewing.
Nothing sensitive is written to disk.

Both keys are stored as raw base64url (not PEM): pywebpush's
`Vapid.from_string()` -- what `webpush(vapid_private_key=...)` uses on a
plain string -- only understands raw/DER base64url, not PEM headers, and
browsers' `PushManager.subscribe({applicationServerKey})` wants the public
key in this same raw-point base64url form.

Usage:
    python scripts/make_vapid.py
"""
from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid01
from py_vapid.utils import b64urlencode

REGION = "ap-south-1"
PRIVATE_PARAM = "/aftercare/vapid/private"
PUBLIC_PARAM = "/aftercare/vapid/public"


def main():
    v = Vapid01()
    v.generate_keys()

    private_raw = v.private_key.private_numbers().private_value.to_bytes(32, "big")
    private_b64 = b64urlencode(private_raw)
    public_raw = v.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    public_b64 = b64urlencode(public_raw)

    print("# Private key: SecureString, decrypted only by the Lambda roles "
          "(see infra/aftercare_stack.py)")
    print('aws ssm put-parameter --name "%s" --type SecureString --overwrite --region %s '
          '--value "%s"' % (PRIVATE_PARAM, REGION, private_b64))
    print()
    print("# Public key: not secret, the browser needs it to subscribe")
    print('aws ssm put-parameter --name "%s" --type String --overwrite --region %s --value "%s"'
          % (PUBLIC_PARAM, REGION, public_b64))


if __name__ == "__main__":
    main()
