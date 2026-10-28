"""Local ELT demo: CSV ingestion -> SQLite raw -> star schema -> AI-ready features.

Data and monitoring are synthetic. 15-minute windows are replayed in one run;
there is no real stream broker or scheduler. The mart is rebuilt from the
raw history to accommodate late data (not a production incremental strategy).
"""
from __future__ import annotations
import csv
import json
import math
import sqlite3
import time
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SOURCES = {
 'customers': ('customers.csv', 'customer_id'),
 'prepaid': ('prepaid_transactions.csv', 'transaction_id'),
 'postpaid': ('postpaid_billing.csv', 'invoice_id'),
 'usage': ('app_usage.csv', 'event_id'),
}


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def date_key(day: date) -> int:
    return int(day.strftime('%Y%m%d'))


def make_date(conn: sqlite3.Connection, day: date) -> int:
    dk = date_key(day)
    conn.execute('INSERT OR IGNORE INTO dim_date VALUES (?,?,?,?,?)',
                 (dk,day.isoformat(),day.year,day.month,day.day))
    return dk


def parse_day(value: str) -> date:
    return date.fromisoformat(str(value))


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(str(value))


def int_money(value: str) -> int:
    # No silent truncation or rounding of source monetary values.
    if value is None or str(value).strip() == '':
        raise ValueError('missing money amount')
    val = float(value)
    if not math.isfinite(val) or val < 0 or not val.is_integer():
        raise ValueError('money must be a nonnegative whole IDR number')
    return int(val)


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute('PRAGMA foreign_keys=ON')
    schema = Path(__file__).resolve().parents[1]/'sql'/'schema.sql'
    conn.executescript(schema.read_text(encoding='utf-8'))
    conn.commit()


def ingest(conn: sqlite3.Connection, base: Path) -> dict:
    inserted, duplicates, total, batches = 0, 0, 0, 0
    by_source = {}
    now = iso_now()
    for source,(filename,id_col) in SOURCES.items():
        path = base/filename
        with path.open(newline='', encoding='utf-8') as fp:
            rows = list(csv.DictReader(fp))
        added = skipped = 0
        # A 15-minute window is simulated by ordering usage events into time buckets.
        # Historical files are replayed instantly. No streaming service is claimed.
        if source == 'usage':
            partitions: dict[str,list[tuple[str,dict]]] = defaultdict(list)
            for i,row in enumerate(rows, 2):
                try:
                    ts = parse_datetime(row['event_time'])
                    bucket = ts.strftime('%Y-%m-%dT%H:') + f'{(ts.minute//15)*15:02d}'
                except (ValueError, KeyError, TypeError):
                    bucket = 'INVALID_TIMESTAMP'
                partitions[bucket].append((str(i),row))
            chunks = [partitions[k] for k in sorted(partitions)]
            batches += len(chunks)
        else:
            chunks = [[(str(i),row) for i,row in enumerate(rows, 2)]]
            batches += 1
        for chunk in chunks:
            for line_number,row in chunk:
                key = str(row.get(id_col,'') or f'BAD_KEY_LINE_{line_number}')
                result = conn.execute('''INSERT OR IGNORE INTO raw_events
                   (source,record_key,payload_json,source_file,loaded_at) VALUES (?,?,?,?,?)''',
                   (source,key,json.dumps(row,ensure_ascii=False,sort_keys=True),filename,now))
                if result.rowcount: added += 1
                else: skipped += 1
        by_source[source] = {'read':len(rows),'new_raw':added,'duplicate_or_replay':skipped}
        inserted += added; duplicates += skipped; total += len(rows)
    conn.commit()
    return {'input_rows':total,'inserted_raw':inserted,'duplicate_raw':duplicates,
            'simulated_microbatch_windows_and_batch_jobs':batches,'sources':by_source}


def transform(conn: sqlite3.Connection, cutoff: date) -> dict:
    issues = Counter()
    invalid_keys: set[tuple[str,str]] = set()
    def reject(source: str, key: str, typ: str, details: str) -> None:
        issues[typ] += 1
        invalid_keys.add((source,key))
        conn.execute('''INSERT OR IGNORE INTO data_quality_issues
             (source,record_key,issue_type,issue_detail,first_seen_at)
             VALUES (?,?,?,?,?)''', (source,key,typ,details[:220],iso_now()))
    rows_by_source: dict[str,list[tuple[str,dict]]] = {}
    for source in SOURCES:
        rows_by_source[source] = [(rec['record_key'],json.loads(rec['payload_json'])) for rec in
          conn.execute('SELECT record_key,payload_json FROM raw_events WHERE source=? ORDER BY record_key',(source,))]
    # Dimensions upsert: natural customer ID is synthetic and source-specific.
    for key,row in rows_by_source['customers']:
        try:
            cid = row['customer_id'].strip()
            if not cid: raise ValueError('missing customer_id')
            plan = row['plan_type'].strip().upper()
            if plan not in ('PREPAID','POSTPAID'):raise ValueError('invalid plan_type')
            joined = parse_day(row['join_date'])
            if joined > cutoff: raise ValueError('join_date after cutoff')
            region = row['region'].strip().upper()
            if not region:raise ValueError('missing region')
            segment = row['segment'].strip().upper() or 'UNKNOWN'
            conn.execute('''INSERT INTO dim_customer
             (customer_id,plan_type,region,join_date,segment) VALUES(?,?,?,?,?)
             ON CONFLICT(customer_id) DO UPDATE SET plan_type=excluded.plan_type,
               region=excluded.region,join_date=excluded.join_date,segment=excluded.segment''',
               (cid,plan,region,joined.isoformat(),segment))
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            reject('customers',key,'INVALID_CUSTOMER',str(e))
    customer_map = {r['customer_id']:(r['customer_key'],r['plan_type']) for r in
                    conn.execute('SELECT customer_id,customer_key,plan_type FROM dim_customer')}

    for key,row in rows_by_source['prepaid']:
        try:
            cid = row['customer_id'].strip()
            if cid not in customer_map:raise ValueError('unknown customer')
            ck,plan = customer_map[cid]
            if plan != 'PREPAID':raise ValueError('not prepaid customer')
            ts = parse_datetime(row['transaction_ts'])
            if ts.date() > cutoff:raise ValueError('future transaction')
            amount = int_money(row['amount_idr'])
            status = row['status'].upper().strip()
            if status not in ('SUCCESS','FAILED'):raise ValueError('invalid status')
            dk = make_date(conn,ts.date())
            conn.execute('''INSERT INTO fact_prepaid VALUES(?,?,?,?,?) ON CONFLICT(transaction_id)
              DO UPDATE SET customer_key=excluded.customer_key,date_key=excluded.date_key,
              amount_idr=excluded.amount_idr,status=excluded.status''', (key,ck,dk,amount,status))
        except (ValueError,KeyError,TypeError,AttributeError) as e:
            reject('prepaid',key,'INVALID_PREPAID',str(e))

    for key,row in rows_by_source['postpaid']:
        try:
            cid = row['customer_id'].strip()
            if cid not in customer_map:raise ValueError('unknown customer')
            ck,plan = customer_map[cid]
            if plan != 'POSTPAID':raise ValueError('not postpaid customer')
            due = parse_day(row['due_date'])
            if due > cutoff + timedelta(days=40):raise ValueError('due date too far in future')
            billing_month = row['billing_month']
            bm = date.fromisoformat(billing_month+'-01')
            if bm > cutoff.replace(day=1):raise ValueError('billing_month in future')
            paid_date = parse_day(row['paid_date']) if row['paid_date'].strip() else None
            if paid_date and paid_date > cutoff:raise ValueError('paid_date after cutoff')
            amount = int_money(row['amount_due_idr']); paid = int_money(row['paid_amount_idr'])
            if paid > amount:raise ValueError('paid more than due')
            dk = make_date(conn,bm)
            conn.execute('''INSERT INTO fact_postpaid VALUES(?,?,?,?,?,?,?,?)
              ON CONFLICT(invoice_id) DO UPDATE SET customer_key=excluded.customer_key,
              date_key=excluded.date_key,billing_month=excluded.billing_month,
              due_date=excluded.due_date,amount_due_idr=excluded.amount_due_idr,
              paid_amount_idr=excluded.paid_amount_idr,paid_date=excluded.paid_date''',
              (key,ck,dk,billing_month,due.isoformat(),amount,paid,paid_date.isoformat() if paid_date else None))
        except (ValueError,KeyError,TypeError,AttributeError) as e:
            reject('postpaid',key,'INVALID_POSTPAID',str(e))

    daily: dict[tuple[int,int,str],list[float]] = defaultdict(lambda:[0.0,0.0,0.0])
    latest_ts: datetime | None = None
    valid_events = 0
    for key,row in rows_by_source['usage']:
        try:
            cid = row['customer_id'].strip()
            if not cid:raise ValueError('missing customer_id')
            if cid not in customer_map:raise ValueError('unknown customer')
            ck,_ = customer_map[cid]
            ts = parse_datetime(row['event_time'])
            if ts.date() > cutoff:raise ValueError('event after cutoff')
            mb = float(row['mb_used']); sess = int(row['sessions'])
            if not math.isfinite(mb) or mb < 0:raise ValueError('mb_used must be finite and >= 0')
            if sess < 0:raise ValueError('negative sessions')
            category = row['app_category'].strip().upper() or 'UNKNOWN'
            dk = make_date(conn,ts.date())
            stat = daily[(ck,dk,category)]
            stat[0] += mb; stat[1] += sess; stat[2] += 1
            latest_ts = max(latest_ts,ts) if latest_ts else ts
            valid_events += 1
        except (ValueError,KeyError,TypeError,AttributeError,OverflowError) as e:
            reject('usage',key,'INVALID_USAGE',str(e))
    # Snapshot rebuild from the raw event history; allows correction of the
    # affected day after delayed arrivals, but is NOT streaming and NOT optimized.
    conn.execute('DELETE FROM fact_usage_daily')
    for category in sorted({x[2] for x in daily}):
        conn.execute('INSERT OR IGNORE INTO dim_app(app_category) VALUES(?)',(category,))
    app_keys = {r['app_category']:r['app_key'] for r in conn.execute('SELECT * FROM dim_app')}
    for (ck,dk,category),(mb,sess,count) in sorted(daily.items()):
        conn.execute('INSERT INTO fact_usage_daily VALUES (?,?,?,?,?,?)',
                     (ck,dk,app_keys[category],round(mb,4),int(sess),int(count)))
    conn.commit()
    return {'invalid_distinct_raw_records':len(invalid_keys), 'issues_new_or_existing':dict(issues),
            'valid_usage_events':valid_events, 'fact_usage_daily_rows':len(daily),
            'latest_valid_usage':latest_ts.isoformat() if latest_ts else None}


def scalar(conn: sqlite3.Connection,query: str,params: tuple = ()) -> int | float:
    return conn.execute(query,params).fetchone()[0]


def features(conn: sqlite3.Connection, cutoff: date, path: Path) -> dict:
    start7 = date_key(cutoff-timedelta(days=6)); prev14 = date_key(cutoff-timedelta(days=13))
    prev7 = date_key(cutoff-timedelta(days=7)); start30 = date_key(cutoff-timedelta(days=29))
    endkey = date_key(cutoff)
    # SQL aggregation at equal customer grain avoids fanout between fact tables.
    usage = defaultdict(lambda:{'recent':0.0,'previous':0.0,'sessions':0,'last_date':None})
    for row in conn.execute('''SELECT customer_key,date_key,SUM(mb_used) mb,SUM(sessions) sessions
           FROM fact_usage_daily WHERE date_key BETWEEN ? AND ?
           GROUP BY customer_key,date_key''',(start30,endkey)):
        rec=usage[row['customer_key']]; dk=row['date_key']
        rec['last_date'] = max(rec['last_date'],dk) if rec['last_date'] else dk
        if dk >= start7:
            rec['recent']+=row['mb'];rec['sessions']+=row['sessions']
        elif prev14 <= dk <= prev7:rec['previous']+=row['mb']
    tops = {}
    for row in conn.execute('''SELECT customer_key,SUM(amount_idr) amt,COUNT(*) cnt FROM fact_prepaid
            WHERE status='SUCCESS' AND date_key BETWEEN ? AND ? GROUP BY customer_key''',(start30,endkey)):
        tops[row['customer_key']] = (row['amt'],row['cnt'])
    bills = {}
    for row in conn.execute('''SELECT customer_key,SUM(amount_due_idr) due,SUM(paid_amount_idr) paid,
                COUNT(*) cnt FROM fact_postpaid
                WHERE date_key BETWEEN ? AND ? GROUP BY customer_key''',
                (date_key(cutoff.replace(day=1)),endkey)):
        bills[row['customer_key']] = (row['due'],row['paid'],row['cnt'])
    fields=['as_of_date','customer_id','is_postpaid','tenure_days','usage_mb_7d',
            'usage_mb_previous_7d','usage_trend_pct','has_previous_usage',
            'sessions_7d','days_since_last_usage','topup_amount_30d','topup_count_30d',
            'topup_applicable','bill_paid_ratio','bill_outstanding_idr','bill_applicable']
    records=[]
    for cust in conn.execute('SELECT * FROM dim_customer ORDER BY customer_id'):
        ck=cust['customer_key']; u=usage[ck]
        p=cust['plan_type']=='PREPAID'; recent=u['recent']; prev=u['previous']
        # Zero for non-applicable field is accompanied by an applicability indicator.
        amt,cnt=tops.get(ck,(0,0));due,paid,_=bills.get(ck,(0,0,0))
        lastdate=datetime.strptime(str(u['last_date']),'%Y%m%d').date() if u['last_date'] else None
        records.append({'as_of_date':cutoff.isoformat(),'customer_id':cust['customer_id'],
          'is_postpaid':int(not p),'tenure_days':(cutoff-parse_day(cust['join_date'])).days,
          'usage_mb_7d':round(recent,2),'usage_mb_previous_7d':round(prev,2),
          'usage_trend_pct':round((recent-prev)/prev*100,2) if prev else 0,
          'has_previous_usage':int(prev>0),'sessions_7d':u['sessions'],
          'days_since_last_usage':(cutoff-lastdate).days if lastdate else 30,
          'topup_amount_30d':amt if p else 0,'topup_count_30d':cnt if p else 0,
          'topup_applicable':int(p),'bill_paid_ratio':round(paid/due,4) if due and not p else 0,
          'bill_outstanding_idr':due-paid if not p else 0,'bill_applicable':int(not p)})
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as fp:
        writer=csv.DictWriter(fp,fieldnames=fields);writer.writeheader();writer.writerows(records)
    return {'rows':len(records),'feature_columns':len(fields)-2,'file':path.name,
            'supervised_churn_labels_included':False}


def verify_db(conn: sqlite3.Connection) -> dict:
    fk=conn.execute('PRAGMA foreign_key_check').fetchall()
    if fk: raise RuntimeError(f'foreign-key violations: {len(fk)}')
    facts={'dim_customer':scalar(conn,'SELECT COUNT(*) FROM dim_customer'),
      'fact_prepaid':scalar(conn,'SELECT COUNT(*) FROM fact_prepaid'),
      'fact_postpaid':scalar(conn,'SELECT COUNT(*) FROM fact_postpaid'),
      'fact_usage_daily':scalar(conn,'SELECT COUNT(*) FROM fact_usage_daily')}
    if facts['dim_customer']==0 or facts['fact_usage_daily']==0:raise RuntimeError('empty key outputs')
    return facts


def run_pipeline(input_dir: str | Path, db_path: str | Path, output_dir: str | Path,
                 run_date: str ='2026-10-24') -> dict:
    cutoff = date.fromisoformat(run_date)
    path = Path(db_path);path.parent.mkdir(parents=True,exist_ok=True)
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    run_id=uuid.uuid4().hex[:12]
    started=iso_now();start_ns=time.perf_counter_ns()
    conn = sqlite3.connect(path);conn.row_factory=sqlite3.Row
    init_db(conn)
    status='SUCCESS';error='';ingest_result={};quality={};mart={};feat={}
    try:
        ingest_result=ingest(conn,Path(input_dir))
        quality=transform(conn,cutoff)
        mart=verify_db(conn)
        feat=features(conn,cutoff,out/'customer_features.csv')
        # A warning is different from pipeline failure. Small quarantines are expected in the demo.
    except Exception as exc:
        status='FAILED';error=f'{type(exc).__name__}: {exc}'
    duration_ms=round((time.perf_counter_ns()-start_ns)/1e6)
    invalid=quality.get('invalid_distinct_raw_records',0)
    conn.execute('''INSERT INTO pipeline_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(
       run_id,run_date,started,iso_now(),status,duration_ms,
       ingest_result.get('input_rows',0),ingest_result.get('inserted_raw',0),
       ingest_result.get('duplicate_raw',0),invalid,mart.get('fact_usage_daily',0),error or None))
    rate=100*invalid/max(1,scalar(conn,'SELECT COUNT(*) FROM raw_events'))
    freshness_min=None
    if quality.get('latest_valid_usage'):
        last=parse_datetime(quality['latest_valid_usage'])
        freshness_min=round(((datetime.combine(cutoff+timedelta(days=1),datetime.min.time())-last).total_seconds()/60),1)
    alerts=[]
    if status=='FAILED':alerts.append(('CRITICAL','PIPELINE_FAILURE',error))
    if status=='SUCCESS' and invalid>0:alerts.append(('WARNING','QUARANTINED_INPUT',f'{invalid} distinct invalid source records quarantined'))
    if rate>1: alerts.append(('CRITICAL','QUALITY_THRESHOLD',f'invalid raw record rate {rate:.2f}% > 1% threshold'))
    if freshness_min is not None and freshness_min>120:
        alerts.append(('WARNING','FRESHNESS_LIMIT',f'usage last event {freshness_min} simulated minutes before cutoff'))
    for level,code,msg in alerts:
        conn.execute('INSERT OR IGNORE INTO alerts(run_id,level,code,message) VALUES (?,?,?,?)',
                     (run_id,level,code,msg))
    conn.commit()
    runs=scalar(conn,'SELECT COUNT(*) FROM pipeline_runs')
    succ=scalar(conn,"SELECT COUNT(*) FROM pipeline_runs WHERE status='SUCCESS'")
    record_counts={s:scalar(conn,'SELECT COUNT(*) FROM raw_events WHERE source=?',(s,)) for s in SOURCES}
    report={
      'project':'Telco Data Engineering Pipeline (synthetic local demo)',
      'run_id':run_id,'as_of_date':run_date,'status':status,'duration_ms':duration_ms,
      'pipeline_success_rate_pct':round(succ/runs*100,2),'pipeline_runs_observed':runs,
      'ingestion':ingest_result,'raw_unique_rows':record_counts,
      'data_quality':{**quality,'invalid_record_rate_pct':round(rate,3),
                      'foreign_key_check':'PASS' if status=='SUCCESS' else 'NOT_VERIFIED'},
      'data_warehouse':mart, 'features':feat,
      'simulated_freshness_lag_minutes':freshness_min,
      'alerts':[{'level':x[0],'code':x[1],'message':x[2]} for x in alerts],
      'business_indicators':{
        'successful_topup_value_idr':scalar(conn,"SELECT COALESCE(SUM(amount_idr),0) FROM fact_prepaid WHERE status='SUCCESS'"),
        'total_amount_billed_idr':scalar(conn,'SELECT COALESCE(SUM(amount_due_idr),0) FROM fact_postpaid'),
        'total_usage_mb':round(scalar(conn,'SELECT COALESCE(SUM(mb_used),0) FROM fact_usage_daily'),2),
        'warning':'Top-up and billed amounts are not accounting revenue.'},
      'implementation_scope': 'CSV replay; 15-minute simulated buckets; SQLite raw/stars; snapshot usage aggregation; no orchestrator, actual stream broker or trained ML model.',
    }
    (out/'run_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    conn.close()
    if status=='FAILED':raise RuntimeError(error)
    return report
