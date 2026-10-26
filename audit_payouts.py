"""Read-only audit of RDG wallet settlements. Run: python audit_payouts.py"""
import sqlite3
import sys
from pathlib import Path


def main():
    db = Path(__file__).resolve().parent / 'football.sqlite3'
    if not db.is_file():
        print('База football.sqlite3 не найдена рядом со скриптом. Ничего не изменено.')
        return 1
    con = sqlite3.connect(db.as_uri() + '?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    try:
        integrity = con.execute('PRAGMA quick_check').fetchone()[0]
        print('RDG — проверка выплат (только чтение)')
        print('Целостность SQLite:', integrity)
        print('Купоны:', dict(con.execute('SELECT status,COUNT(*) n FROM slips GROUP BY status').fetchall()) if False else ', '.join(f"{r['status']}: {r['n']}" for r in con.execute('SELECT status, COUNT(*) n FROM slips GROUP BY status ORDER BY status')))
        missing = list(con.execute('''SELECT s.id,s.status,s.payout FROM slips s
            LEFT JOIN ledger l ON l.ref='settle:'||s.id
            WHERE s.status IN ('won','void') AND s.payout>0 AND l.id IS NULL'''))
        wrong = list(con.execute('''SELECT s.id,s.payout,l.amount FROM slips s
            JOIN ledger l ON l.ref='settle:'||s.id WHERE s.status IN ('won','void') AND l.amount!=s.payout'''))
        stray = list(con.execute('''SELECT s.id,s.status,l.amount FROM slips s
            JOIN ledger l ON l.ref='settle:'||s.id WHERE s.status NOT IN ('won','void')'''))
        due = list(con.execute('''SELECT s.id FROM slips s WHERE s.status='pending' AND
            NOT EXISTS(SELECT 1 FROM legs l JOIN matches m ON m.id=l.match_id WHERE l.slip_id=s.id AND m.status NOT IN ('FINISHED','CANCELLED','POSTPONED','SUSPENDED'))
            AND EXISTS(SELECT 1 FROM legs WHERE slip_id=s.id)'''))
        nolegs = list(con.execute('''SELECT s.id FROM slips s WHERE NOT EXISTS(SELECT 1 FROM legs l WHERE l.slip_id=s.id)'''))
        negatives = list(con.execute('SELECT id FROM users WHERE balance<0'))
        for label,rows in [('Выплаты без записи в журнале',missing),('Несовпадение выплаченной суммы',wrong),('Выплата при неверном статусе',stray),('Купоны, которые уже можно рассчитать',due),('Купоны без исходов',nolegs),('Отрицательные балансы',negatives)]:
            print(f'{label}: {len(rows)}'+(' (ID: '+', '.join(str(r['id']) for r in rows[:12])+('…' if len(rows)>12 else '')+')' if rows else ''))
        print('Важно: этот скрипт ничего не исправляет и не списывает/начисляет монеты.')
        return 0 if integrity=='ok' and not (missing or wrong or stray or nolegs or negatives) else 2
    finally:
        con.close()

if __name__=='__main__':
    sys.exit(main())
