#!/usr/bin/env python3
import sys
import os

# Add scripts dir to path if running directly
if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from scripts.observability import HealthCheck
except ImportError:
    try:
        from observability import HealthCheck
    except ImportError:
        # Fallback if running from root
        from scripts.observability import HealthCheck

def main():
    print("Running System Health Checks...")
    print("-" * 30)

    # Check DB
    db_ok, db_msg = HealthCheck.check_db()
    print(f"Database: {'✅' if db_ok else '❌'} {db_msg}")

    # Check OpenClaw
    oc_ok, oc_msg = HealthCheck.check_openclaw()
    print(f"OpenClaw: {'✅' if oc_ok else '❌'} {oc_msg}")

    print("-" * 30)
    if db_ok and oc_ok:
        print("System Healthy")
        sys.exit(0)
    else:
        print("System Unhealthy")
        sys.exit(1)

if __name__ == "__main__":
    main()
