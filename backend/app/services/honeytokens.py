from pathlib import Path

TOKEN_REFERENCE = "ptk-novapay-env-prod-001"


def write_first_honeytoken(destination: str = "../deception/fake_source/payment-service/.env.production") -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# NovaPay Payment Service — production deployment configuration\n"
        "AWS_ACCESS_KEY_ID=FAKEPIKATRAPDEMO001\n"
        "AWS_SECRET_ACCESS_KEY=pikatrap_safe_nonfunctional_secret\n"
        "PROD_BUCKET=prod-customer-backups\n"
        f"PIKATRAP_CANARY_ID={TOKEN_REFERENCE}\n",
        encoding="utf-8",
    )
    return path
