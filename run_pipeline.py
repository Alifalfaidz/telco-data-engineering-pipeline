"""Entry point. Python 3.10+; no third-party packages required."""
from __future__ import annotations
import argparse
import json
from telco_pipeline.generator import generate_data
from telco_pipeline.pipeline import run_pipeline


def main() -> None:
    p=argparse.ArgumentParser(description='Telco pipeline portfolio (synthetic data only)')
    sub=p.add_subparsers(dest='command',required=True)
    g=sub.add_parser('generate',help='Generate deterministic synthetic sources')
    g.add_argument('--output-dir',default='data/synthetic')
    g.add_argument('--seed',type=int,default=42)
    g.add_argument('--customers',type=int,default=240)
    g.add_argument('--run-date',default='2026-10-24')
    r=sub.add_parser('run',help='Run ingestion, DWH transformation, features and checks')
    r.add_argument('--input-dir',default='data/synthetic')
    r.add_argument('--db-path',default='outputs/telco_dwh.sqlite')
    r.add_argument('--output-dir',default='outputs')
    r.add_argument('--run-date',default='2026-10-24')
    args=p.parse_args()
    if args.command=='generate':
        result=generate_data(args.output_dir,args.run_date,args.seed,args.customers)
    else:
        result=run_pipeline(args.input_dir,args.db_path,args.output_dir,args.run_date)
    print(json.dumps(result,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
