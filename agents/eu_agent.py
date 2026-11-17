"""Infrastructure smoke test only; does not search or apply for jobs."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def main():
    now = datetime.now(timezone.utc)
    print("Agent: EU SOC Job Search Agent")
    print("Agent ID: EU_SOC_AGENT")
    print(f"Execution timestamp (UTC): {now.isoformat()}")
    print(f"Execution timestamp (Europe/Berlin): {now.astimezone(ZoneInfo('Europe/Berlin')).isoformat()}")
    print("Placeholder only: no job searches or applications performed.")
    print("Successful completion.")


if __name__ == "__main__":
    main()
