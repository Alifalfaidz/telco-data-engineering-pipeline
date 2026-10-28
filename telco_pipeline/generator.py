"""Deterministic synthetic telecom datasets; no real customer data."""
from __future__ import annotations
import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def generate_data(output_dir: str | Path, run_date: str = '2026-10-24', seed: int = 42, customers: int = 240) -> dict:
    """Make date-limited, reproducible input CSVs and a few intentional anomalies."""
    if customers < 20:
        raise ValueError('customers must be >= 20')
    end = date.fromisoformat(run_date)
    r = random.Random(seed)
    out = Path(output_dir)
    customer_rows, prepaid_rows, billing_rows, usage_rows = [], [], [], []
    plans = ('PREPAID', 'POSTPAID')
    regions = ('BANDUNG', 'JAKARTA', 'SURABAYA', 'MEDAN')
    categories = ('MESSAGING', 'VIDEO', 'SOCIAL', 'MUSIC')
    prepaid_idx = billing_idx = usage_idx = 0
    for n in range(1, customers + 1):
        cid = f'SYN{n:05d}'
        plan = plans[0] if n <= int(customers * 0.65) else plans[1]
        join = end - timedelta(days=r.randint(60, 1300))
        customer_rows.append({'customer_id':cid,'plan_type':plan,'region':r.choice(regions),
                              'join_date':join.isoformat(),'segment':r.choice(('REGULAR','PLUS'))})
        if plan == 'PREPAID':
            for day in range(30):
                cur = end - timedelta(days=day)
                if r.random() < 0.24:
                    prepaid_idx += 1
                    prepaid_rows.append({'transaction_id':f'T{prepaid_idx:07d}', 'customer_id':cid,
                            'transaction_ts':f'{cur.isoformat()}T{r.randint(7,22):02d}:{r.randint(0,59):02d}:00',
                            'amount_idr':r.choice((10000,25000,50000,100000)), 'status':'SUCCESS'})
        else:
            billing_idx += 1
            amount = r.choice((50000,75000,100000,150000,200000))
            due = end - timedelta(days=8)
            paid = r.random() < .78
            paid_amount = amount if paid else (0 if r.random() < .75 else int(amount * .4))
            pdate = (due + timedelta(days=r.randint(-5,6))).isoformat() if paid else ''
            billing_rows.append({'invoice_id':f'B{billing_idx:06d}','customer_id':cid,
                  'billing_month':end.strftime('%Y-%m'),'due_date':due.isoformat(),
                  'amount_due_idr':amount,'paid_amount_idr':paid_amount,'paid_date':pdate})
        # Sparse customer-day usage; latest day has events in a 15-minute window.
        for day in range(30):
            cur = end - timedelta(days=day)
            active = r.random() < (0.70 if plan == 'PREPAID' else 0.80)
            if active:
                for _ in range(r.randint(1,3)):
                    usage_idx += 1
                    hour = r.randint(6,22) if day else 23
                    minute = r.randint(0,59) if day else r.randint(30,55)
                    usage_rows.append({'event_id':f'U{usage_idx:08d}', 'customer_id':cid,
                        'event_time':f'{cur.isoformat()}T{hour:02d}:{minute:02d}:00',
                        'mb_used':round(r.uniform(2,550),2),'sessions':r.randint(1,5),
                        'app_category':r.choice(categories)})
    # Explicit quality test cases. Never use sensitive or live data.
    if prepaid_rows:
        prepaid_rows.append(dict(prepaid_rows[0]))  # duplicate natural key
    if billing_rows:
        billing_rows.append(dict(billing_rows[0]))  # duplicate natural key
    bad = dict(usage_rows[0]); bad['event_id']='U_BAD_NEG';bad['mb_used']='-18';usage_rows.append(bad)
    bad = dict(usage_rows[1]); bad['event_id']='U_BAD_CUSTOMER';bad['customer_id']='SYN_UNKNOWN';usage_rows.append(bad)
    bad = dict(usage_rows[2]); bad['event_id']='U_BAD_DATE';bad['event_time']='not-a-date';usage_rows.append(bad)
    bad = dict(usage_rows[3]); bad['event_id']='U_BAD_MISSING';bad['customer_id']='';usage_rows.append(bad)
    write_csv(out/'customers.csv',['customer_id','plan_type','region','join_date','segment'],customer_rows)
    write_csv(out/'prepaid_transactions.csv',['transaction_id','customer_id','transaction_ts','amount_idr','status'],prepaid_rows)
    write_csv(out/'postpaid_billing.csv',['invoice_id','customer_id','billing_month','due_date','amount_due_idr','paid_amount_idr','paid_date'],billing_rows)
    write_csv(out/'app_usage.csv',['event_id','customer_id','event_time','mb_used','sessions','app_category'],usage_rows)
    return {k:len(v) for k,v in [('customers',customer_rows),('prepaid_transactions',prepaid_rows),('postpaid_billing',billing_rows),('app_usage',usage_rows)]}
