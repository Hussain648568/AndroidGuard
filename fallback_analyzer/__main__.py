import argparse
import json
import dataclasses
import sys
import logging

from fallback_analyzer import Analyzer

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        elif isinstance(o, set):
            return list(o)
        return super().default(o)

def main():
    parser = argparse.ArgumentParser(description="Fallback Static Analyzer for Android APKs")
    parser.add_argument("apk", help="Path to the APK file to analyze")
    parser.add_argument("--sources", required=True, help="Path to SuSi sources list")
    parser.add_argument("--sinks", required=True, help="Path to SuSi sinks list")
    parser.add_argument("--out", help="Path to write JSON report (default: stdout)")

    args = parser.parse_args()

    logger.info(f"Analyzing {args.apk}...")
    analyzer = Analyzer(args.apk, args.sources, args.sinks)
    report = analyzer.analyze()

    report_json = json.dumps(report, cls=EnhancedJSONEncoder, indent=2)

    if args.out:
        with open(args.out, "w") as f:
            f.write(report_json)
        logger.info(f"Report written to {args.out}")
    else:
        print(report_json)

if __name__ == "__main__":
    main()
