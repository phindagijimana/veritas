import argparse
import jwt
from app.core.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sub", required=True)
    parser.add_argument("--roles", default="researcher")
    args = parser.parse_args()

    settings = get_settings()
    token = jwt.encode(
        {
            "sub": args.sub,
            "roles": [r.strip() for r in args.roles.split(",") if r.strip()],
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        },
        settings.dev_bearer_secret,
        algorithm="HS256",
    )
    print(token)


if __name__ == "__main__":
    main()
