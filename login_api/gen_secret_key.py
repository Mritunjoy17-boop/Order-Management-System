import secrets
from pathlib import Path

ENV_FILE = '.env.prod'

def generate_secret_key():
    new_secret = secrets.token_hex(32)
    env_path = Path(ENV_FILE)

    lines = env_path.read_text().splitlines()
    updated_lines = []
    found = False

    for line in lines:
        if line.startswith("SECRET_KEY="):
            updated_lines.append(f"SECRET_KEY={new_secret}")
            found = True
        else:
            updated_lines.append(line)

    if not found:
        updated_lines.append(f"SECRET_KEY={new_secret}")

    env_path.write_text("\n".join(updated_lines) + "\n")

    print(f"New secret key : {new_secret}")

if __name__ == '__main__':
    generate_secret_key()